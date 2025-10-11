"""Tests for the growth module stage orchestration."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Iterable, Sequence

import pytest

from pyforestry.base.helpers.bucking import QualityType
from pyforestry.simulation.growth_module import (
    ActionStage,
    DisturbanceStage,
    GrowthModule,
    GrowthStage,
    ManagementStage,
    Stage,
    StageAction,
    ValuationStage,
)
from pyforestry.simulation.stand_composite import StandAction, StandComposite, StandPart
from pyforestry.simulation.valuation import StandRemovalLedger, VolumeDescriptor, VolumeResult


class RandomStage(Stage):
    """Stage that records RNG draws for reproducibility tests."""

    name = "random"
    order = 5

    def run(self, part: StandPart, module: GrowthModule, rng) -> None:  # type: ignore[override]
        draws = part.context.setdefault("stage_draws", [])
        draws.append(rng.random())


class RandomActionStage(ActionStage):
    """Action stage producing deterministic RNG-driven actions."""

    name = "random_action"
    order = 15
    managed = False

    def build_actions(self, part: StandPart, module: GrowthModule, rng) -> Iterable[StandAction]:  # type: ignore[override]
        def handler(part: StandPart, *, rng):
            value = rng.random()
            part.context.setdefault("action_draws", []).append(value)
            return value

        return (StandAction(name="draw", handler=handler),)


class DummyModelView:
    """Minimal model view exposing capability information for tests."""

    def __init__(self, capabilities: Iterable[str]) -> None:
        self._capabilities = frozenset(capabilities)

    def has_capability(self, capability: str) -> bool:
        return capability in self._capabilities

    def capabilities(self) -> Sequence[str]:
        return tuple(self._capabilities)


def _make_part(name: str, capabilities: Iterable[str]) -> StandPart:
    view = DummyModelView(capabilities)
    return StandPart(name=name, model_view=view, context={})


def test_growth_module_orders_stages_by_priority() -> None:
    composite = StandComposite()
    # Intentionally provide stages out of order to confirm automatic sorting.
    module = GrowthModule(
        composite,
        stages=(DisturbanceStage(), ManagementStage(), GrowthStage()),
    )
    assert module.stage_names == ("growth", "management", "disturbance")


def test_affordances_filtered_by_model_capabilities() -> None:
    part = _make_part("north", capabilities=("grow",))
    allowed = StandAction(
        name="grow_increment",
        handler=lambda stand_part: stand_part.context.setdefault("growth_calls", 0) + 1,
    )
    allowed.requires_capabilities = ("grow",)
    blocked = StandAction(name="thin", handler=lambda stand_part: None)
    blocked.requires_capabilities = ("thin",)
    part.growth_overrides = {"actions": (allowed, blocked)}

    module = GrowthModule(StandComposite((part,)))
    affordances = module.discover_affordances(part)
    growth_actions = affordances[next(stage for stage in affordances if stage.name == "growth")]

    assert [action.name for action in growth_actions] == ["grow_increment"]


def test_management_ruleset_routes_actions_to_declaring_stage() -> None:
    executed: list[str] = []

    def record_action(part: StandPart, *, label: str) -> str:
        executed.append(f"{part.name}:{label}")
        return label

    part = _make_part("central", capabilities=("thin", "grow"))
    thin = StandAction(name="thin", handler=lambda part: record_action(part, label="thin"))
    thin.requires_capabilities = ("thin",)
    prune = StandAction(name="prune", handler=lambda part: record_action(part, label="prune"))
    prune.requires_capabilities = ("prune",)
    part.growth_overrides = {"actions": (thin, prune)}

    rulesets = {
        "growth": lambda part, actions: [action for action in actions if action.name == "thin"]
    }
    module = GrowthModule(StandComposite((part,)), management_rulesets=rulesets)

    result = module.run_cycle()

    assert executed == ["central:thin"]
    assert [record.action for record in result.records] == ["thin"]


def test_stage_initialisation_allows_name_and_order_override() -> None:
    stage = Stage(name="custom", order=7)
    assert stage.name == "custom"
    assert stage.order == 7


def test_action_stage_coerce_action_from_tuple_and_mapping() -> None:
    stage = GrowthStage()
    base = StandAction(name="tuple", handler=lambda part: None)
    coerced_tuple = stage._coerce_action((base, ("thin",)))
    assert coerced_tuple is base
    assert coerced_tuple.requires_capabilities == ("thin",)

    mapping_action = stage._coerce_action(
        {
            "name": "map",
            "handler": lambda part: None,
            "requires_capabilities": ("grow",),
            "cost": 2.5,
            "harvest": 1.1,
        }
    )
    assert mapping_action.name == "map"
    assert mapping_action.requires_capabilities == ("grow",)

    with pytest.raises(TypeError):
        stage._coerce_action(123)


def test_management_stage_selection_defaults_and_name_matching() -> None:
    part = _make_part("selection", capabilities=("grow", "thin"))
    thin = StandAction(name="thin", handler=lambda part: None)
    thin.requires_capabilities = ()
    grow = StandAction(name="grow", handler=lambda part: None)
    part.growth_overrides = {"actions": (thin, grow)}

    module = GrowthModule(StandComposite((part,)))
    affordances = module.discover_affordances(part)
    growth_stage = next(stage for stage in affordances if stage.name == "growth")
    management = ManagementStage()

    # When no rules are registered, all actions are selected unchanged.
    selected = management.select_actions(
        part,
        {growth_stage: affordances[growth_stage]},
        module,
    )
    assert selected[growth_stage] == affordances[growth_stage]

    normalized = management._normalize_selection(
        growth_stage, affordances[growth_stage], ("thin",)
    )
    assert [action.name for action in normalized] == ["thin"]

    other_stage = DisturbanceStage()
    alien_action = StageAction(stage=other_stage, action=thin)
    with pytest.raises(ValueError):
        management._normalize_selection(growth_stage, affordances[growth_stage], (alien_action,))


def test_growth_module_supports_capabilities_attribute_only() -> None:
    class AttrView:
        capabilities = ("thin",)

    module = GrowthModule(StandComposite())
    assert module.supports_capabilities(AttrView(), ("thin",))
    assert not module.supports_capabilities(AttrView(), ("grow",))
    assert not module.supports_capabilities(None, ("thin",))


def test_growth_module_executes_without_management_stage() -> None:
    executed: list[str] = []

    def mark(part: StandPart, label: str) -> str:
        executed.append(f"{part.name}:{label}")
        return label

    part = _make_part("fallback", capabilities=("grow", "disturb"))
    growth_action = StandAction(
        name="grow",
        handler=lambda part: mark(part, "grow"),
    )
    part.growth_overrides = {"actions": (growth_action,)}

    disturbance_action = StandAction(
        name="storm",
        handler=lambda part: mark(part, "storm"),
    )
    part.disturbance_overrides = {"actions": (disturbance_action,)}

    module = GrowthModule(
        StandComposite((part,)),
        stages=(GrowthStage(), DisturbanceStage()),
    )

    result = module.run_cycle()

    assert executed == ["fallback:grow", "fallback:storm"]
    assert [record.action for record in result.records] == ["grow", "storm"]


def _run_random_stage_cycle(seed: int, stage: Stage) -> tuple[list[float], StandComposite]:
    view = DummyModelView(())
    view.model_id = "rng-model"
    part = StandPart("alpha", view, context={})
    composite = StandComposite((part,), seed=seed, model_id="rng-suite")
    module = GrowthModule(composite, stages=(stage,))
    module.run_cycle()
    return part.context.get("stage_draws", part.context.get("action_draws", [])), composite


def test_growth_module_rng_draws_are_deterministic() -> None:
    draws1, _ = _run_random_stage_cycle(21, RandomStage())
    draws2, _ = _run_random_stage_cycle(21, RandomStage())
    draws3, _ = _run_random_stage_cycle(22, RandomStage())

    assert draws1 == draws2
    assert draws1 != draws3


def test_growth_module_action_rng_is_deterministic() -> None:
    draws1, _ = _run_random_stage_cycle(33, RandomActionStage())
    draws2, _ = _run_random_stage_cycle(33, RandomActionStage())
    draws3, _ = _run_random_stage_cycle(34, RandomActionStage())

    assert draws1 and draws1 == draws2
    assert draws1 != draws3


def test_growth_module_emits_stage_telemetry_with_metadata() -> None:
    draws, composite = _run_random_stage_cycle(44, RandomActionStage())
    assert draws  # ensure the stage executed
    events = composite.telemetry.events
    assert events
    last_event = events[-1]
    assert last_event.type == "growth.stage"
    payload = last_event.payload
    assert payload["metadata"]["seed"] == composite.seed
    assert payload["metadata"]["model_id"] == composite.model_id
    assert payload["stage"] == "random_action"
    assert payload["records"]
    assert payload["records"][0]["action"] == "draw"


def test_stage_events_are_captured_in_event_store() -> None:
    part = _make_part("alpha", capabilities=("grow",))
    action = StandAction(name="grow", handler=lambda part: None, cost=5.0, harvest=2.5)
    action.requires_capabilities = ("grow",)
    part.growth_overrides = {"actions": (action,)}
    composite = StandComposite((part,), seed=21, model_id="events")
    module = GrowthModule(composite, stages=(GrowthStage(),))

    module.run_cycle()

    events = composite.iter_event_records(category="biological")
    growth_events = [event for event in events if event.kind == "growth.apply"]
    assert growth_events, "Expected growth.apply event in biological records"
    event = growth_events[0]
    assert event.payload["part"] == "alpha"
    assert event.payload["records"][0]["action"] == "grow"
    assert event.metadata["part"] == "alpha"


def test_valuation_stage_records_economic_event_and_telemetry() -> None:
    ledger = StandRemovalLedger(stand_id="valuation", metadata={"region": "north"})
    ledger.cohorts["dummy"] = SimpleNamespace(tree_count=1)

    class StubConnector:
        def connect(self, model_view, removal_ledger):
            descriptor = VolumeDescriptor(ledger=removal_ledger)
            volume_by_quality = {quality: 0.0 for quality in QualityType}
            volume_by_quality[QualityType.Undefined] = 3.5
            return VolumeResult(
                descriptor=descriptor,
                pieces=(),
                total_value=125.0,
                volume_by_quality=volume_by_quality,
                metadata={"note": "stub"},
            )

    part = _make_part("valuation", capabilities=("grow",))
    part.context["valuation"] = {"ledger": ledger}
    composite = StandComposite((part,), seed=3, model_id="valuation")
    module = GrowthModule(composite, stages=(ValuationStage(connector=StubConnector()),))

    module.run_cycle()

    events = composite.iter_event_records(category="economic")
    result_events = [event for event in events if event.kind == "valuation.result"]
    assert len(result_events) == 1
    event = result_events[0]
    assert event.kind == "valuation.result"
    assert event.payload["total_value"] == 125.0
    telemetry_types = [event.type for event in composite.telemetry.events]
    assert "valuation.result" in telemetry_types
