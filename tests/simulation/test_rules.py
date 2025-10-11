"""Unit tests for the rule engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from pyforestry.simulation.rules import Rule, RuleAction, RuleDecision, RuleSet
from pyforestry.simulation.state import PlotState, StandState


@dataclass
class StubManager:
    calls: List[str]


def build_state() -> StandState:
    plot = PlotState(
        id="p1",
        area_m2=100.0,
        radius_m=5.0,
        occlusion=0.0,
        position=(0.0, 0.0),
        site=None,
        tree_uids=("t1", "t2"),
    )
    return StandState(
        site=None,
        area_ha=1.0,
        top_height_definition=None,
        attrs={"management": "baseline"},
        metric_estimates={"Stems": {"TOTAL": 2}},
        use_angle_count=False,
        plots=(plot,),
    )


def test_ruleset_executes_first_matching_rule() -> None:
    manager = StubManager(calls=[])
    action = RuleAction(
        name="record",
        callback=lambda mgr, stand_id, state: mgr.calls.append(stand_id),
    )
    rule = Rule(name="apply", predicate=lambda s: True, actions=[action], priority=10)
    ruleset = RuleSet(name="rs", rules=[rule], scope={"stands": ["stand-A"]})

    decisions = ruleset.evaluate(manager, "stand-A", build_state())

    assert decisions == [RuleDecision(rule=rule, actions_executed=("record",))]
    assert manager.calls == ["stand-A"]


def test_ruleset_respects_scope_tags() -> None:
    manager = StubManager(calls=[])
    action = RuleAction(
        name="record",
        callback=lambda mgr, stand_id, state: mgr.calls.append(stand_id),
    )
    rule = Rule(name="tagged", predicate=lambda s: True, actions=[action])
    ruleset = RuleSet(name="rs", rules=[rule], scope={"tags": ["priority"]})

    assert ruleset.evaluate(manager, "stand-B", build_state(), stand_tags=["priority"])
    assert manager.calls == ["stand-B"]

    manager.calls.clear()
    assert ruleset.evaluate(manager, "stand-C", build_state(), stand_tags=["other"]) == []
    assert manager.calls == []
