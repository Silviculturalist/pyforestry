"""Tests for the growth module stage orchestration."""

from __future__ import annotations

from typing import Iterable, Sequence

import pytest

from pyforestry.simulation.growth_module import (
    DisturbanceStage,
    GrowthModule,
    GrowthStage,
    ManagementStage,
    Stage,
    StageAction,
)
from pyforestry.simulation.stand_composite import StandAction, StandComposite, StandPart


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
    selected = management.select_actions(part, {growth_stage: affordances[growth_stage]})
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
