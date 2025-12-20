from __future__ import annotations

from typing import Iterable

import pytest

from pyforestry.simulation.contracts import StageContract
from pyforestry.simulation.growth_module import (
    ActionStage,
    GrowthModule,
    ManagementStage,
    Stage,
    StageAction,
    ValuationStage,
)
from pyforestry.simulation.stand_composite import StandAction, StandComposite, StandPart
from pyforestry.simulation.valuation import StandRemovalLedger


class DummyModelView:
    def __init__(self, capabilities: Iterable[str] = ()):
        self._capabilities = tuple(capabilities)

    def capabilities(self):
        return self._capabilities


def _make_part(name: str = "p1", capabilities: Iterable[str] = ()):
    return StandPart(name=name, model_view=DummyModelView(capabilities), context={})


class DummyActionStage(ActionStage):
    name = "dummy"
    order = 1
    managed = True

    def build_actions(self, part, module, rng):  # type: ignore[override]
        return (StandAction(name="noop", handler=lambda p: None),)


def test_action_stage_apply_rejects_foreign_stage():
    stage = DummyActionStage()
    part = _make_part()
    module = GrowthModule(StandComposite((part,)))
    action = StandAction(name="noop", handler=lambda p: None)
    foreign = StageAction(stage=Stage(), action=action)
    with pytest.raises(ValueError, match="different stage"):
        stage.apply(part, [foreign], module)


def test_action_stage_coerce_action_tuple_type_error():
    stage = DummyActionStage()
    with pytest.raises(TypeError):
        stage._coerce_action(("bad", ("cap",)))  # type: ignore[arg-type]


def test_action_stage_build_actions_not_implemented():
    stage = ActionStage()
    part = _make_part()
    module = GrowthModule(StandComposite((part,)))
    with pytest.raises(NotImplementedError):
        stage.build_actions(part, module, None)


def test_management_stage_normalize_selection_errors():
    stage = DummyActionStage()
    action = StandAction(name="noop", handler=lambda p: None)
    affordance = StageAction(stage=stage, action=action)
    management = ManagementStage()
    assert management._normalize_selection(stage, (affordance,), None) == ()

    with pytest.raises(KeyError, match="Unknown action"):
        management._normalize_selection(stage, (affordance,), ("missing",))

    with pytest.raises(ValueError, match="same stage"):
        management._normalize_selection(stage, (affordance,), (StageAction(Stage(), action),))


def test_management_stage_handles_empty_affordances():
    stage = DummyActionStage()
    management = ManagementStage()
    part = _make_part()
    module = GrowthModule(StandComposite((part,)))
    selected = management.select_actions(part, {stage: ()}, module)
    assert selected == {}
    dispatched = management.dispatch_selected(part, {stage: ()}, module)
    assert dispatched == []


def test_growth_module_supports_capabilities_basic_cases():
    module = GrowthModule(StandComposite())
    assert module.supports_capabilities(DummyModelView(()), ())
    assert not module.supports_capabilities(None, ("grow",))


def test_growth_module_rng_for_requires_effect():
    part = _make_part()
    composite = StandComposite((part,))
    module = GrowthModule(composite)
    stage = Stage(contract=StageContract(effects=frozenset()))
    with pytest.raises(RuntimeError, match="does not declare the 'rng' effect"):
        module.rng_for(stage, part)


def test_apply_without_management_executes_pending_actions():
    part = _make_part()
    composite = StandComposite((part,))
    module = GrowthModule(composite, stages=(DummyActionStage(),))
    stage = module.stages[0]
    assert isinstance(stage, DummyActionStage)
    affordance = StageAction(stage=stage, action=StandAction("noop", handler=lambda p: None))
    records = module._apply_without_management(part, {stage: (affordance,)})
    assert records


def test_growth_module_management_ruleset_update_for_existing_stage():
    management = ManagementStage()
    composite = StandComposite()
    module = GrowthModule(
        composite,
        stages=(management, DummyActionStage()),
        management_rulesets={"dummy": lambda part, actions: actions},
    )
    assert "dummy" in management._rulesets
    assert module.stage_names


def test_valuation_stage_locates_ledger_from_getter_and_context():
    ledger = StandRemovalLedger()

    class GetterView(DummyModelView):
        def get_removal_ledger(self):
            return ledger

    part = StandPart(name="p1", model_view=GetterView(), context={})
    stage = ValuationStage()
    assert stage._locate_ledger(part) is ledger

    part_ctx = StandPart(name="p2", model_view=DummyModelView(), context={"valuation": {}})
    part_ctx.context["valuation"]["ledger"] = ledger
    assert stage._locate_ledger(part_ctx) is ledger

    part_direct = StandPart(
        name="p3", model_view=DummyModelView(), context={"removal_ledger": ledger}
    )
    assert stage._locate_ledger(part_direct) is ledger


def test_run_part_triggers_apply_without_management():
    part = _make_part()
    module = GrowthModule(StandComposite((part,)), stages=(DummyActionStage(),))
    module._management_stage = object()  # type: ignore[assignment]
    records = module._run_part(part)
    assert records


def test_apply_without_management_skips_empty_affordances():
    part = _make_part()
    module = GrowthModule(StandComposite((part,)), stages=(DummyActionStage(),))
    stage = module.stages[0]
    assert module._apply_without_management(part, {stage: ()}) == []
