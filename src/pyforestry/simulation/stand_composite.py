"""Composite helpers for coordinating multi-part stand simulations."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    FrozenSet,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from pyforestry.simulation.services import (
    CheckpointSerializer,
    CompositeMemento,
    KeyedRNG,
    RandomBundle,
    TelemetryPublisher,
)

if TYPE_CHECKING:  # pragma: no cover - typing helper
    from .stage_runtime import Stage

MetricSource = Union[str, Iterable[str], None]
PolicySelector = Union[
    str,
    Callable[["StandAction", Tuple["StandPart", ...]], Sequence["StandPart"]],
]


def _call_or_value(value: Any) -> Any:
    """Return ``value`` or call it if it is callable."""

    if callable(value):
        return value()
    return value


@dataclass
class StandAction:
    """Represent an action that can be dispatched to one or more stand parts."""

    name: str
    handler: Callable[["StandPart"], Any]
    cost: Union[float, Callable[["StandPart"], float]] = 0.0
    harvest: Union[float, Callable[["StandPart"], float]] = 0.0
    target_parts: MetricSource = None

    def __post_init__(self) -> None:
        """Defer handler signature inspection until something actually needs it."""
        self._handler_accepts_rng: Optional[bool] = None
        self._handler_accepts_io: Optional[bool] = None

    def cost_for(self, part: "StandPart") -> float:
        """Resolve the cost for ``part``."""

        cost = self.cost(part) if callable(self.cost) else self.cost
        return float(cost)

    def harvest_for(self, part: "StandPart") -> float:
        """Resolve the harvested volume for ``part``."""

        harvest = self.harvest(part) if callable(self.harvest) else self.harvest
        return float(harvest)

    def _analyse_handler(self) -> None:
        """Record whether the handler can accept ``rng`` and ``io`` injection.

        Detection is by parameter **name**, never by position. A handler's second
        positional parameter is its own business -- a thinning intensity, a target
        species -- and treating any such parameter as the RNG slot meant
        ``def thin(part, intensity=0.25)`` silently received a ``KeyedRNG`` object
        in ``intensity``, and was additionally rejected by the effect check for
        "requiring RNG access" it had never asked for.

        A ``**kwargs`` catch-all still counts: it can absorb ``rng=``/``io=``
        harmlessly, and handlers written against it read them by name. A bare
        ``*args`` does not, for the same reason positional inference does not.
        """
        try:
            params = list(inspect.signature(self.handler).parameters.values())
        except (TypeError, ValueError):  # pragma: no cover - C callables
            self._handler_accepts_rng = False
            self._handler_accepts_io = False
            return
        # The first positional parameter is the StandPart itself.
        if params and params[0].kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            params = params[1:]

        named = {
            parameter.name
            for parameter in params
            if parameter.kind
            in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
        }
        catch_all = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params)
        self._handler_accepts_rng = "rng" in named or catch_all
        self._handler_accepts_io = "io" in named or catch_all

    def _ensure_handler_analysis(self) -> None:
        """Inspect the handler signature once, on first use."""
        if self._handler_accepts_rng is None:
            self._analyse_handler()

    def execute(self, part: "StandPart", rng: Optional[KeyedRNG]) -> Any:
        """Execute the underlying handler for ``part``, passing ``rng`` if it asked."""

        if rng is None:
            return self.handler(part)
        self._ensure_handler_analysis()
        if self._handler_accepts_rng:
            return self.handler(part, rng=rng)
        return self.handler(part)

    @property
    def requests_rng(self) -> bool:
        """Whether the handler declares an ``rng`` parameter (or a ``**kwargs`` catch-all)."""

        self._ensure_handler_analysis()
        return bool(self._handler_accepts_rng)

    @property
    def requests_io(self) -> bool:
        """Whether the handler declares an ``io`` parameter (or a ``**kwargs`` catch-all)."""

        self._ensure_handler_analysis()
        return bool(self._handler_accepts_io)

    def iter_targets(self) -> Tuple[str, ...]:
        """Return a normalized tuple of target part identifiers."""

        if self.target_parts is None:
            return ()
        if isinstance(self.target_parts, str):
            return (self.target_parts,)
        return tuple(self.target_parts)


@dataclass
class DispatchRecord:
    """Track the result of sending an action to a specific stand part."""

    part: str
    action: str
    cost: float
    harvest: float
    result: Any


@dataclass
class DispatchResult:
    """Aggregate the outcome of a dispatch cycle."""

    records: List[DispatchRecord] = field(default_factory=list)

    @property
    def spent(self) -> float:
        """Return the total spend incurred by the dispatch."""

        return float(sum(record.cost for record in self.records))

    @property
    def harvested(self) -> float:
        """Return the total harvested amount incurred by the dispatch."""

        return float(sum(record.harvest for record in self.records))

    def by_part(self) -> Dict[str, List[DispatchRecord]]:
        """Group dispatch records by part identifier."""

        grouped: Dict[str, List[DispatchRecord]] = {}
        for record in self.records:
            grouped.setdefault(record.part, []).append(record)
        return grouped


@dataclass
class StandPart:
    """Container binding a model view, context and override parameters."""

    name: str
    model_view: Any
    context: Mapping[str, Any] = field(default_factory=dict)
    growth_overrides: Optional[Mapping[str, Any]] = None
    disturbance_overrides: Optional[Mapping[str, Any]] = None

    def __post_init__(self) -> None:
        """Copy the mappings in, and reject a part with no name."""
        if not self.name:
            raise ValueError("Stand parts require a non-empty name.")
        if not isinstance(self.context, Mapping):
            raise TypeError("Context must implement the mapping protocol.")
        self.context = dict(self.context)
        self.growth_overrides = dict(self.growth_overrides or {})
        self.disturbance_overrides = dict(self.disturbance_overrides or {})

    def _metric_from_model(
        self,
        attr_name: str,
        metric_name: str,
        default: Optional[float] = None,
    ) -> float:
        """Resolve ``metric_name`` from the model view, or from this part's context.

        Four sources are tried in order: a ``basal_area``-style attribute on the
        view, the ``BasalArea``-style metric name, a ``view.total(metric_name)``
        accessor, and finally ``context[attr_name]``. Each may be a value or a
        callable returning one.

        Args:
            attr_name: Snake-case attribute/context key, e.g. ``"basal_area"``.
            metric_name: Metric name as the stand layer spells it, e.g. ``"BasalArea"``.
            default: Value to use when nothing supplies the metric. ``None`` means
                the metric is required and an unresolvable view is an error.

        Returns:
            The resolved value.

        Raises:
            AttributeError: If nothing supplies a required metric. Returning ``0.0``
                instead -- as this did -- let a view that implements none of the
                four conventions read as an empty stand, and
                :meth:`StandComposite.dispatch` enforces its budget and harvest cap
                against exactly these numbers.
        """
        view = self.model_view

        if hasattr(view, attr_name):
            value = getattr(view, attr_name)
            try:
                return float(_call_or_value(value))
            except TypeError:
                pass
        if hasattr(view, metric_name):
            metric_value = getattr(view, metric_name)
            try:
                return float(_call_or_value(metric_value))
            except TypeError:
                pass
        total_method = getattr(view, "total", None)
        if callable(total_method):
            try:
                return float(total_method(metric_name))
            except (KeyError, TypeError):
                pass
        if isinstance(self.context, Mapping):
            context_value = self.context.get(attr_name)
            if context_value is not None:
                return float(context_value)
        if default is not None:
            return float(default)
        raise AttributeError(
            f"Stand part {self.name!r} cannot report {attr_name!r}: its model view "
            f"({type(view).__name__}) exposes no {attr_name!r} or {metric_name!r} "
            f"attribute and no total({metric_name!r}) accessor, and the part's "
            f"context does not supply {attr_name!r} either."
        )

    @property
    def basal_area(self) -> float:
        """Basal area contributed by this part."""

        return self._metric_from_model("basal_area", "BasalArea")

    @property
    def stems(self) -> float:
        """Stem count contributed by this part."""

        return self._metric_from_model("stems", "Stems")

    @property
    def cash(self) -> float:
        """Cash contribution for this part.

        Unlike the state metrics this is an accumulator: a part that has not been
        valued yet legitimately holds nothing, so an absent value means zero
        rather than a broken view.
        """

        return self._metric_from_model("cash", "Cash", default=0.0)

    @property
    def growth_parameters(self) -> Mapping[str, Any]:
        """Return the resolved growth parameters for the part."""

        base: MutableMapping[str, Any] = dict(self.context.get("growth", {}))
        base.update(self.growth_overrides)
        return dict(base)

    @property
    def disturbance_parameters(self) -> Mapping[str, Any]:
        """Return the resolved disturbance parameters for the part."""

        base: MutableMapping[str, Any] = dict(self.context.get("disturbance", {}))
        base.update(self.disturbance_overrides)
        return dict(base)

    def apply_action(
        self,
        action: StandAction,
        *,
        cost: Optional[float] = None,
        harvest: Optional[float] = None,
        rng: Optional[KeyedRNG] = None,
        effects: Optional[FrozenSet[str]] = None,
        stage: Optional["Stage"] = None,
    ) -> DispatchRecord:
        """Execute ``action`` against this part and return a dispatch record."""

        resolved_cost = action.cost_for(self) if cost is None else float(cost)
        resolved_harvest = action.harvest_for(self) if harvest is None else float(harvest)
        effect_set = frozenset(effects) if effects is not None else None
        stage_label = stage.name if stage is not None else "unknown"
        if effect_set is not None:
            if "rng" not in effect_set:
                if action.requests_rng:
                    message = (
                        f"Action '{action.name}' requires RNG access but stage "
                        f"'{stage_label}' does not expose the 'rng' effect."
                    )
                    raise RuntimeError(message)
                rng = None
            if "io" not in effect_set and action.requests_io:
                message = (
                    f"Action '{action.name}' requests I/O but stage "
                    f"'{stage_label}' does not expose the 'io' effect."
                )
                raise RuntimeError(message)
        result = action.execute(self, rng)
        return DispatchRecord(
            part=self.name,
            action=action.name,
            cost=resolved_cost,
            harvest=resolved_harvest,
            result=result,
        )


class StandComposite:
    """Coordinate actions and shared constraints across multiple stand parts."""

    def __init__(
        self,
        parts: Optional[Iterable[StandPart]] = None,
        *,
        budget: Optional[float] = None,
        harvest_cap: Optional[float] = None,
        seed: int = 0,
        model_id: Optional[str] = None,
        telemetry: Optional[TelemetryPublisher] = None,
    ) -> None:
        """Create a composite with shared constraints, RNG and telemetry.

        ``budget`` and ``harvest_cap`` are enforced across the whole composite
        during :meth:`dispatch`, and ``seed`` roots the keyed RNG every part
        draws from.
        """
        self._parts: Dict[str, StandPart] = {}
        self.budget = budget
        self.harvest_cap = harvest_cap
        self.seed = int(seed)
        self.model_id = model_id or "stand"
        self.random_bundle = RandomBundle(self.seed)
        self.telemetry = telemetry or TelemetryPublisher(
            model_id=self.model_id,
            seed=self.seed,
        )
        self._checkpoint_serializer = CheckpointSerializer()
        for part in parts or ():
            self.add_part(part)

    @property
    def parts(self) -> Tuple[StandPart, ...]:
        """Return the registered stand parts."""

        return tuple(self._parts.values())

    def add_part(self, part: StandPart) -> None:
        """Register ``part`` with the composite."""

        if part.name in self._parts:
            raise ValueError(f"Duplicate stand part name: {part.name}")
        self._parts[part.name] = part

    def get_part(self, name: str) -> StandPart:
        """Return the :class:`StandPart` registered under ``name``."""

        try:
            return self._parts[name]
        except KeyError as exc:  # pragma: no cover - defensive
            raise KeyError(f"Unknown stand part: {name}") from exc

    @property
    def total_basal_area(self) -> float:
        """Aggregate basal area across all parts."""

        return float(sum(part.basal_area for part in self._parts.values()))

    @property
    def total_stems(self) -> float:
        """Aggregate stem counts across all parts."""

        return float(sum(part.stems for part in self._parts.values()))

    @property
    def total_cash(self) -> float:
        """Aggregate cash contributions across all parts."""

        return float(sum(part.cash for part in self._parts.values()))

    def _select_parts(
        self,
        action: StandAction,
        policy: PolicySelector,
    ) -> Tuple[StandPart, ...]:
        """Select stand parts that should receive ``action``."""

        available_parts = self.parts
        if callable(policy):
            selected = tuple(policy(action, available_parts))
            if not selected:
                return ()
            return selected
        if policy == "broadcast":
            return available_parts
        if policy == "target":
            targets = action.iter_targets()
            if not targets:
                raise ValueError("Targeted dispatch requires actions to declare target parts.")
            return tuple(self.get_part(name) for name in targets)
        if policy == "largest_first":
            if not available_parts:
                return ()
            largest = max(available_parts, key=lambda item: item.basal_area)
            return (largest,)
        raise ValueError(f"Unknown dispatch policy: {policy}")

    def dispatch(
        self,
        actions: Iterable[StandAction],
        *,
        policy: PolicySelector = "target",
    ) -> DispatchResult:
        """Dispatch ``actions`` to selected parts while enforcing constraints."""

        result = DispatchResult()
        for action in actions:
            parts = self._select_parts(action, policy)
            if not parts:
                continue
            for part in parts:
                cost = action.cost_for(part)
                harvest = action.harvest_for(part)
                projected_spend = result.spent + cost
                projected_harvest = result.harvested + harvest
                if self.budget is not None and projected_spend - self.budget > 1e-9:
                    raise RuntimeError(
                        f"Dispatching action '{action.name}' would exceed the shared budget."
                    )
                if self.harvest_cap is not None and projected_harvest - self.harvest_cap > 1e-9:
                    raise RuntimeError(
                        f"Dispatching action '{action.name}' would exceed the harvest cap."
                    )
                rng = self.random_bundle.rng_for("composite", action.name, part.name)
                record = part.apply_action(action, cost=cost, harvest=harvest, rng=rng)
                result.records.append(record)
                self.telemetry.publish(
                    "stand.action_dispatch",
                    {
                        "part": part.name,
                        "action": action.name,
                        "cost": cost,
                        "harvest": harvest,
                        "part_model_id": getattr(part.model_view, "model_id", None),
                    },
                )
        return result

    def snapshot(self) -> CompositeMemento:
        """Return a checkpoint capturing the composite state."""

        return self._checkpoint_serializer.capture(self)

    def restore(self, memento: CompositeMemento) -> None:
        """Restore state from ``memento`` created by :meth:`snapshot`."""

        self._checkpoint_serializer.restore(self, memento)
