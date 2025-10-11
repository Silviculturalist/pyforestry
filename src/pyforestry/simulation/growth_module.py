"""Growth module coordinating staged stand management operations."""

from __future__ import annotations

from dataclasses import dataclass
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

from pyforestry.simulation.stand_composite import (
    DispatchRecord,
    DispatchResult,
    StandAction,
    StandComposite,
    StandPart,
)

CapabilityRequirement = Sequence[str]


Ruleset = Callable[[StandPart, Tuple["StageAction", ...]], Iterable[Union["StageAction", str]]]
RulesetMapping = Mapping[str, Ruleset]


@dataclass
class StageAction:
    """Bind a :class:`StandAction` to the stage that declared it."""

    stage: "ActionStage"
    action: StandAction
    requires_capabilities: Tuple[str, ...] = ()

    @property
    def name(self) -> str:
        """Return the friendly action name."""

        return self.action.name


class Stage:
    """Base class for all growth module stages."""

    name: str = "stage"
    order: int = 0

    def __init__(self, *, name: Optional[str] = None, order: Optional[int] = None) -> None:
        if name is not None:
            self.name = name
        if order is not None:
            self.order = order

    def setup(self, module: "GrowthModule") -> None:
        """Hook executed once the stage is registered with a module."""

    def run(self, part: StandPart, module: "GrowthModule") -> None:
        """Execute the stage for ``part``.

        The default implementation does nothing. Sub-classes that do not
        participate in the affordance/management handshake can override this
        method directly.
        """


class ActionStage(Stage):
    """Stages that expose actions for potential execution."""

    managed: bool = True

    def build_actions(self, part: StandPart, module: "GrowthModule") -> Iterable[StandAction]:
        """Yield :class:`StandAction` objects available for ``part``."""

        raise NotImplementedError

    def discover_affordances(
        self, part: StandPart, module: "GrowthModule"
    ) -> Tuple[StageAction, ...]:
        """Return the filtered actions that ``part`` can execute."""

        affordances: List[StageAction] = []
        for action in self.build_actions(part, module):
            requires_raw = getattr(action, "requires_capabilities", ())
            requires = tuple(str(item) for item in requires_raw) if requires_raw else ()
            if requires and not module.supports_capabilities(part.model_view, requires):
                continue
            affordances.append(
                StageAction(stage=self, action=action, requires_capabilities=requires)
            )
        return tuple(affordances)

    def apply(
        self, part: StandPart, actions: Sequence[StageAction], module: "GrowthModule"
    ) -> List[DispatchRecord]:
        """Execute ``actions`` for ``part`` and return dispatch records."""

        records: List[DispatchRecord] = []
        for affordance in actions:
            if affordance.stage is not self:
                raise ValueError("Cannot execute an action for a different stage.")
            record = self.perform_action(part, affordance, module)
            if record is not None:
                records.append(record)
        return records

    def perform_action(
        self, part: StandPart, affordance: StageAction, module: "GrowthModule"
    ) -> Optional[DispatchRecord]:
        """Execute ``affordance`` for ``part``.

        Sub-classes can override this to implement custom dispatch behaviour.
        The default implementation delegates to :meth:`StandPart.apply_action`.
        """

        return part.apply_action(affordance.action)

    def _coerce_action(self, raw_action: Any) -> StandAction:
        """Normalize ``raw_action`` into a :class:`StandAction` instance."""

        if isinstance(raw_action, StandAction):
            return raw_action
        if isinstance(raw_action, tuple) and len(raw_action) == 2:
            action, requires = raw_action
            if not isinstance(action, StandAction):
                raise TypeError("Tuples must contain a StandAction instance as the first element.")
            action.requires_capabilities = tuple(requires)
            return action
        if isinstance(raw_action, Mapping):
            data = dict(raw_action)
            requires = tuple(data.pop("requires_capabilities", ()))
            try:
                name = data.pop("name")
                handler = data.pop("handler")
            except KeyError as exc:  # pragma: no cover - defensive
                raise KeyError("Action mappings must define 'name' and 'handler'.") from exc
            cost = data.pop("cost", 0.0)
            harvest = data.pop("harvest", 0.0)
            target_parts = data.pop("target_parts", None)
            action = StandAction(
                name=name,
                handler=handler,
                cost=cost,
                harvest=harvest,
                target_parts=target_parts,
            )
            action.requires_capabilities = requires
            return action
        raise TypeError("Unsupported action specification.")


class ManagementStage(Stage):
    """Select actions exposed by upstream :class:`ActionStage` instances."""

    name = "management"
    order = 20

    def __init__(
        self,
        *,
        rulesets: Optional[RulesetMapping] = None,
    ) -> None:
        super().__init__()
        self._rulesets: Dict[str, Ruleset] = {}
        if rulesets:
            self.update_rulesets(rulesets)

    def update_rulesets(
        self,
        rulesets: Mapping[str, Ruleset],
    ) -> None:
        """Merge ``rulesets`` into the stage."""

        self._rulesets.update(rulesets)

    def select_actions(
        self,
        part: StandPart,
        affordances_by_stage: Mapping["ActionStage", Tuple[StageAction, ...]],
    ) -> Dict["ActionStage", Tuple[StageAction, ...]]:
        """Return the actions that should be executed for ``part``."""

        selected: Dict[ActionStage, Tuple[StageAction, ...]] = {}
        for stage, affordances in affordances_by_stage.items():
            if not affordances:
                continue
            selector = self._rulesets.get(stage.name) or self._rulesets.get("default")
            if selector is None:
                selected[stage] = affordances
                continue
            chosen_raw = selector(part, affordances)
            normalized = self._normalize_selection(stage, affordances, chosen_raw)
            selected[stage] = normalized
        return selected

    def dispatch_selected(
        self,
        part: StandPart,
        selection: Mapping["ActionStage", Tuple[StageAction, ...]],
        module: "GrowthModule",
    ) -> List[DispatchRecord]:
        """Execute the actions chosen in :meth:`select_actions`."""

        records: List[DispatchRecord] = []
        for stage, affordances in selection.items():
            if not affordances:
                continue
            records.extend(stage.apply(part, affordances, module))
        return records

    @staticmethod
    def _normalize_selection(
        stage: "ActionStage",
        affordances: Tuple[StageAction, ...],
        chosen: Optional[Iterable[Union[StageAction, str]]],
    ) -> Tuple[StageAction, ...]:
        if chosen is None:
            return ()
        mapping = {affordance.name: affordance for affordance in affordances}
        normalized: List[StageAction] = []
        for item in chosen:
            if isinstance(item, StageAction):
                if item.stage is not stage:
                    raise ValueError(
                        "Rulesets must return actions originating from the same stage."
                    )
                normalized.append(item)
                continue
            try:
                normalized.append(mapping[str(item)])
            except KeyError as exc:
                raise KeyError(f"Unknown action '{item}' returned by management ruleset.") from exc
        return tuple(normalized)


class GrowthStage(ActionStage):
    """Stage exposing growth-related actions."""

    name = "growth"
    order = 10
    managed = True

    def build_actions(self, part: StandPart, module: "GrowthModule") -> Iterable[StandAction]:
        parameters = part.growth_parameters
        raw_actions = parameters.get("actions", ())
        for raw in raw_actions:
            yield self._coerce_action(raw)


class DisturbanceStage(ActionStage):
    """Stage exposing disturbance actions."""

    name = "disturbance"
    order = 30
    managed = False

    def build_actions(self, part: StandPart, module: "GrowthModule") -> Iterable[StandAction]:
        parameters = part.disturbance_parameters
        raw_actions = parameters.get("actions", ())
        for raw in raw_actions:
            yield self._coerce_action(raw)


class GrowthModule:
    """Coordinate stand management stages and their interactions."""

    def __init__(
        self,
        composite: StandComposite,
        *,
        stages: Optional[Sequence[Stage]] = None,
        management_rulesets: Optional[RulesetMapping] = None,
    ) -> None:
        self.composite = composite
        if stages is None:
            management_stage = ManagementStage(rulesets=management_rulesets)
            stages = (GrowthStage(), management_stage, DisturbanceStage())
        else:
            stages = tuple(stages)
            if management_rulesets:
                for stage in stages:
                    if isinstance(stage, ManagementStage):
                        stage.update_rulesets(management_rulesets)
                        break
        for stage in stages:
            stage.setup(self)
        self.stages: Tuple[Stage, ...] = tuple(sorted(stages, key=lambda item: item.order))
        self._management_stage: Optional[ManagementStage] = next(
            (stage for stage in self.stages if isinstance(stage, ManagementStage)),
            None,
        )

    @property
    def stage_names(self) -> Tuple[str, ...]:
        """Return the ordered stage names."""

        return tuple(stage.name for stage in self.stages)

    def supports_capabilities(self, model_view: Any, capabilities: CapabilityRequirement) -> bool:
        """Return ``True`` when ``model_view`` satisfies ``capabilities``."""

        if not capabilities:
            return True
        if model_view is None:
            return False
        capability_set: MutableMapping[str, bool] = {}
        available = getattr(model_view, "capabilities", None)
        if callable(available):
            available = available()
        if isinstance(available, Iterable) and not isinstance(available, (str, bytes)):
            capability_set.update({str(cap): True for cap in available})
        has_capability = getattr(model_view, "has_capability", None)
        for capability in capabilities:
            if callable(has_capability):
                if not bool(has_capability(capability)):
                    return False
                continue
            if capability not in capability_set:
                return False
        return True

    def discover_affordances(self, part: StandPart) -> Dict[ActionStage, Tuple[StageAction, ...]]:
        """Return the action affordances available to ``part`` by stage."""

        affordances: Dict[ActionStage, Tuple[StageAction, ...]] = {}
        for stage in self.stages:
            if isinstance(stage, ActionStage):
                actions = stage.discover_affordances(part, self)
                affordances[stage] = actions
        return affordances

    def _apply_without_management(
        self,
        part: StandPart,
        pending: Mapping[ActionStage, Tuple[StageAction, ...]],
    ) -> List[DispatchRecord]:
        """Execute ``pending`` actions when no management stage is present."""

        records: List[DispatchRecord] = []
        for stage, affordances in pending.items():
            if not affordances:
                continue
            records.extend(stage.apply(part, affordances, self))
        return records

    def _run_part(self, part: StandPart) -> List[DispatchRecord]:
        """Execute a full stage cycle for ``part``."""

        records: List[DispatchRecord] = []
        pending: Dict[ActionStage, Tuple[StageAction, ...]] = {}
        for stage in self.stages:
            if isinstance(stage, ActionStage):
                affordances = stage.discover_affordances(part, self)
                if not affordances:
                    continue
                if stage.managed and self._management_stage is not None:
                    pending[stage] = affordances
                    continue
                records.extend(stage.apply(part, affordances, self))
            elif isinstance(stage, ManagementStage):
                if not pending:
                    continue
                selection = stage.select_actions(part, pending)
                records.extend(stage.dispatch_selected(part, selection, self))
                pending.clear()
            else:
                stage.run(part, self)
        if pending:
            records.extend(self._apply_without_management(part, pending))
        return records

    def run_cycle(self, parts: Optional[Iterable[StandPart]] = None) -> DispatchResult:
        """Run a complete cycle across ``parts`` (defaults to all in composite)."""

        result = DispatchResult()
        target_parts = tuple(parts) if parts is not None else self.composite.parts
        for part in target_parts:
            records = self._run_part(part)
            result.records.extend(records)
        return result
