"""Tests for the growth module stage orchestration."""

from __future__ import annotations

from typing import Iterable, Sequence

import pytest

from pyforestry.simulation.contracts import StageContract
from pyforestry.simulation.services import KeyedRNG, RandomBundle, TelemetryPublisher
from pyforestry.simulation.stage_runtime import (
    ActionStage,
    DisturbanceStage,
    GrowthStage,
    ManagementStage,
    Stage,
    StageAction,
    StageRuntime,
    ValuationStage,
)
from pyforestry.simulation.stand_composite import StandAction, StandComposite, StandPart
from pyforestry.simulation.valuation import StandRemovalLedger


class RandomStage(Stage):
    """Stage that records RNG draws for reproducibility tests."""

    name = "random"
    order = 5

    def run(self, part: StandPart, module: StageRuntime, rng) -> None:  # type: ignore[override]
        draws = part.context.setdefault("stage_draws", [])
        draws.append(rng.random())


class RandomActionStage(ActionStage):
    """Action stage producing deterministic RNG-driven actions."""

    name = "random_action"
    order = 15
    managed = False

    def build_actions(self, part: StandPart, module: StageRuntime, rng) -> Iterable[StandAction]:  # type: ignore[override]
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
    module = StageRuntime(
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

    module = StageRuntime(StandComposite((part,)))
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
    module = StageRuntime(StandComposite((part,)), management_rulesets=rulesets)

    result = module.run_cycle()

    assert executed == ["central:thin"]
    assert [record.action for record in result.records] == ["thin"]


def test_stage_initialisation_allows_name_and_order_override() -> None:
    stage = Stage(name="custom", order=7)
    assert stage.name == "custom"
    assert stage.order == 7


def test_stage_init_contract_override() -> None:
    contract = StageContract(effects=frozenset({"rng"}))
    stage = Stage(contract=contract)
    assert stage.contract is contract


def test_action_stage_build_actions_not_implemented() -> None:
    stage = ActionStage()
    part = _make_part("simple", capabilities=())
    module = StageRuntime(StandComposite((part,)), stages=(stage,))
    with pytest.raises(NotImplementedError):
        stage.build_actions(part, module, None)


def test_action_stage_apply_rejects_mismatched_stage() -> None:
    stage = GrowthStage()
    other = DisturbanceStage()
    part = _make_part("mismatch", capabilities=())
    module = StageRuntime(StandComposite((part,)), stages=(stage, other))
    affordance = StageAction(
        stage=other,
        action=StandAction(name="noop", handler=lambda part: None),
    )
    with pytest.raises(ValueError, match="different stage"):
        stage.apply(part, (affordance,), module)


def test_management_stage_selection_empty_affordances() -> None:
    part = _make_part("empty", capabilities=())
    module = StageRuntime(StandComposite((part,)))
    stage = GrowthStage()
    management = ManagementStage()

    selected = management.select_actions(part, {stage: ()}, module)
    assert selected == {}


def test_management_stage_normalize_none_and_unknown() -> None:
    stage = GrowthStage()
    management = ManagementStage()
    affordance = StageAction(stage=stage, action=StandAction("thin", handler=lambda part: None))

    assert management._normalize_selection(stage, (affordance,), None) == ()

    with pytest.raises(KeyError, match="Unknown action"):
        management._normalize_selection(stage, (affordance,), ("missing",))


def test_management_stage_dispatch_selected_skips_empty() -> None:
    part = _make_part("dispatch", capabilities=())
    module = StageRuntime(StandComposite((part,)))
    stage = GrowthStage()
    management = ManagementStage()
    records = management.dispatch_selected(part, {stage: ()}, module)
    assert records == []


def test_valuation_stage_locates_ledger_sources() -> None:
    ledger = StandRemovalLedger("stand")

    class ViewWithGetter:
        def get_removal_ledger(self):
            return ledger

    part_getter = StandPart("getter", model_view=ViewWithGetter(), context={})
    stage = ValuationStage()
    assert stage._locate_ledger(part_getter) is ledger

    part_ctx = StandPart("ctx", model_view=object(), context={"valuation": {"ledger": ledger}})
    assert stage._locate_ledger(part_ctx) is ledger


def test_growth_module_management_rulesets_update() -> None:
    part = _make_part("rules", capabilities=())
    rulesets = {"growth": lambda part, actions: ()}
    management = ManagementStage()
    module = StageRuntime(
        StandComposite((part,)),
        stages=(management,),
        management_rulesets=rulesets,
    )
    assert module._management_stage is management
    assert management._rulesets["growth"] is rulesets["growth"]


def test_growth_module_supports_empty_capabilities() -> None:
    module = StageRuntime(StandComposite())
    assert module.supports_capabilities(None, ())


def test_growth_module_rng_for_with_keys() -> None:
    part = _make_part("rng", capabilities=())

    class RNGStage(Stage):
        name = "rng"
        order = 1
        contract = StageContract(effects=frozenset({"rng"}))

    stage = RNGStage()
    module = StageRuntime(StandComposite((part,)), stages=(stage,))
    rng = module.rng_for(stage, part, "extra")
    assert isinstance(rng, KeyedRNG)


def test_growth_module_pending_actions_apply_without_management() -> None:
    class LateStage(ActionStage):
        name = "late"
        order = 30

        def build_actions(self, part: StandPart, module: StageRuntime, rng):  # type: ignore[override]
            def handler(part: StandPart) -> int:
                part.context["hits"] = part.context.get("hits", 0) + 1
                return part.context["hits"]

            return (StandAction(name="late_action", handler=handler),)

    part = _make_part("late", capabilities=())
    management = ManagementStage()
    management.order = 5
    module = StageRuntime(StandComposite((part,)), stages=(management, LateStage()))

    module.run_cycle()
    assert part.context["hits"] == 1


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

    with pytest.raises(TypeError):
        stage._coerce_action(("not-action", ("thin",)))


def test_management_stage_selection_defaults_and_name_matching() -> None:
    part = _make_part("selection", capabilities=("grow", "thin"))
    thin = StandAction(name="thin", handler=lambda part: None)
    thin.requires_capabilities = ()
    grow = StandAction(name="grow", handler=lambda part: None)
    part.growth_overrides = {"actions": (thin, grow)}

    module = StageRuntime(StandComposite((part,)))
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

    module = StageRuntime(StandComposite())
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

    module = StageRuntime(
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
    module = StageRuntime(composite, stages=(stage,))
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


def test_stage_contract_blocks_rng_requests() -> None:
    class NoRNGStage(ActionStage):
        name = "no_rng"
        managed = False
        contract = StageContract(effects=frozenset())

        def build_actions(self, part: StandPart, module: StageRuntime, rng):  # type: ignore[override]
            def handler(part: StandPart, *, rng):
                return rng.random()

            return (StandAction(name="needs_rng", handler=handler),)

    part = _make_part("limited", capabilities=())
    module = StageRuntime(StandComposite((part,)), stages=(NoRNGStage(),))

    with pytest.raises(RuntimeError, match="rng"):
        module.run_cycle()


def test_stage_contract_blocks_io_requests() -> None:
    class IOStage(ActionStage):
        name = "io_only"
        managed = False
        contract = StageContract()

        def build_actions(self, part: StandPart, module: StageRuntime, rng):  # type: ignore[override]
            def handler(part: StandPart, *, io):
                return io

            return (StandAction(name="needs_io", handler=handler),)

    part = _make_part("io", capabilities=())
    module = StageRuntime(StandComposite((part,)), stages=(IOStage(),))

    with pytest.raises(RuntimeError, match="io"):
        module.run_cycle()


def test_growth_module_rng_for_respects_contract() -> None:
    class PassiveStage(ActionStage):
        name = "passive"
        managed = False
        contract = StageContract(effects=frozenset())

        def build_actions(self, part: StandPart, module: StageRuntime, rng):  # type: ignore[override]
            return ()

    part = _make_part("passive", capabilities=())
    stage = PassiveStage()
    module = StageRuntime(StandComposite((part,)), stages=(stage,))

    with pytest.raises(RuntimeError, match="rng"):
        module.rng_for(stage, part)


def test_keyed_rng_helpers_and_child():
    bundle = RandomBundle(123)
    rng = bundle.rng_for("alpha")
    assert 0.0 <= rng.random() < 1.0
    assert isinstance(rng.randint(1, 2), int)
    assert 0.0 <= rng.uniform(0.0, 1.0) <= 1.0

    child = rng.child("beta", ("gamma", "delta"))
    assert isinstance(child, KeyedRNG)

    state = rng.state
    rng.jumpahead(2)
    rng.state = state


def test_telemetry_publisher_sink_and_clear():
    events = []

    def sink(event):
        events.append(event)

    publisher = TelemetryPublisher(model_id=None, seed=7, sink=sink)
    publisher.publish("unit", {"value": 1.0})

    assert events
    assert publisher.events
    publisher.clear()
    assert publisher.events == []
