"""Composite helpers for coordinating multi-part stand simulations."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
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
    EventCategory,
    EventRecord,
    EventSnapshotter,
    EventStore,
    KeyedRNG,
    RandomBundle,
    TelemetryPublisher,
)

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
        self._handler_accepts_rng_keyword: Optional[bool] = None
        self._handler_accepts_rng_positional: Optional[bool] = None

    def cost_for(self, part: "StandPart") -> float:
        """Resolve the cost for ``part``."""

        cost = self.cost(part) if callable(self.cost) else self.cost
        return float(cost)

    def harvest_for(self, part: "StandPart") -> float:
        """Resolve the harvested volume for ``part``."""

        harvest = self.harvest(part) if callable(self.harvest) else self.harvest
        return float(harvest)

    def _analyse_handler(self) -> None:
        signature = inspect.signature(self.handler)
        params = list(signature.parameters.values())
        remaining = params
        if remaining and remaining[0].kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            remaining = remaining[1:]
        accepts_keyword = False
        accepts_positional = False
        for parameter in remaining:
            if parameter.kind == inspect.Parameter.VAR_KEYWORD:
                accepts_keyword = True
                break
            if parameter.kind == inspect.Parameter.VAR_POSITIONAL:
                accepts_positional = True
                continue
            if parameter.name == "rng" and parameter.kind in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            ):
                accepts_keyword = True
                continue
            if parameter.kind in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            ):
                accepts_positional = True
        self._handler_accepts_rng_keyword = accepts_keyword
        self._handler_accepts_rng_positional = accepts_positional

    def execute(self, part: "StandPart", rng: Optional[KeyedRNG]) -> Any:
        """Execute the underlying handler for ``part`` using ``rng`` when accepted."""

        if rng is None:
            return self.handler(part)
        if self._handler_accepts_rng_keyword is None:
            self._analyse_handler()
        if self._handler_accepts_rng_keyword:
            return self.handler(part, rng=rng)
        if self._handler_accepts_rng_positional:
            return self.handler(part, rng)
        return self.handler(part)

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
        if not self.name:
            raise ValueError("Stand parts require a non-empty name.")
        if not isinstance(self.context, Mapping):
            raise TypeError("Context must implement the mapping protocol.")
        self.context = dict(self.context)
        self.growth_overrides = dict(self.growth_overrides or {})
        self.disturbance_overrides = dict(self.disturbance_overrides or {})

    def _metric_from_model(self, attr_name: str, metric_name: str, default: float) -> float:
        """Attempt to resolve ``metric_name`` from the attached model view."""

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
        context_value = None
        if isinstance(self.context, Mapping):
            context_value = self.context.get(attr_name, default)
        return float(context_value if context_value is not None else default)

    @property
    def basal_area(self) -> float:
        """Basal area contributed by this part."""

        return self._metric_from_model("basal_area", "BasalArea", 0.0)

    @property
    def stems(self) -> float:
        """Stem count contributed by this part."""

        return self._metric_from_model("stems", "Stems", 0.0)

    @property
    def cash(self) -> float:
        """Cash contribution for this part."""

        return self._metric_from_model("cash", "Cash", 0.0)

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
    ) -> DispatchRecord:
        """Execute ``action`` against this part and return a dispatch record."""

        resolved_cost = action.cost_for(self) if cost is None else float(cost)
        resolved_harvest = action.harvest_for(self) if harvest is None else float(harvest)
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
        event_store: Optional[EventStore] = None,
    ) -> None:
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
        self.event_store = event_store or EventStore(
            model_id=self.model_id,
            seed=self.seed,
        )
        self._checkpoint_serializer = CheckpointSerializer()
        self._event_snapshotter = EventSnapshotter(self.event_store, self._checkpoint_serializer)
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

        return self._event_snapshotter.capture(self)

    def restore(self, memento: CompositeMemento) -> None:
        """Restore state from ``memento`` created by :meth:`snapshot`."""

        self._event_snapshotter.restore(self, memento)

    def iter_event_records(
        self,
        *,
        category: Optional[Union[str, EventCategory]] = None,
        kind: Optional[str] = None,
        start_index: Optional[int] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> Tuple[EventRecord, ...]:
        """Return events emitted by the composite with optional filtering."""

        return self.event_store.iter_records(
            category=category,
            kind=kind,
            start_index=start_index,
            metadata=metadata,
            limit=limit,
        )
