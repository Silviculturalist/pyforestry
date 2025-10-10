"""Integration tests for the simulation manager."""

from __future__ import annotations

from typing import Any

import pytest

from pyforestry.base.helpers import CircularPlot, Stand, Tree
from pyforestry.base.helpers.primitives.cartesian_position import Position
from pyforestry.simulation import (
    FixedSeedPolicy,
    GrowthModule,
    ModelResult,
    Rule,
    RuleAction,
    RuleSet,
    SimulationManager,
    StandState,
)


class IncrementAgeModel:
    level = "tree"
    time_step = 1.0
    requires_checkpoint = False
    required_tree_fields = ("age",)
    required_stand_fields = ()

    def __init__(self, increment: float = 1.0) -> None:
        self.increment = increment
        self.initialised = False

    def validate_inputs(self, stand_state: StandState, tree_states) -> None:  # noqa: D401
        for tree in tree_states:
            assert tree.age is not None

    def initialize(self, context: dict[str, Any] | None = None) -> None:  # noqa: D401
        self.initialised = True

    def step(self, years, rng, stand_state, tree_states):  # noqa: D401
        assert self.initialised
        deltas = {tree.uid: {"age": self.increment * years} for tree in tree_states}
        stand_delta = {"years_simulated": years}
        return ModelResult(tree_deltas=deltas, stand_deltas=stand_delta)

    def finalize(self) -> None:  # noqa: D401
        self.initialised = False


@pytest.fixture
def simple_stand() -> Stand:
    tree = Tree(uid="t1", species="picea abies", age=10.0, diameter_cm=30.0, height_m=18.0)
    plot = CircularPlot(id="p1", radius_m=5.0, position=Position(0, 0), trees=[tree])
    return Stand(area_ha=1.0, plots=[plot])


def test_manager_runs_modules_and_updates_state(simple_stand: Stand) -> None:
    module = GrowthModule(IncrementAgeModel, config={"increment": 2.0})
    manager = SimulationManager(seed_policy=FixedSeedPolicy(42))
    manager.register_stand("stand-1", simple_stand, modules=[module])
    manager.start_run()
    manager.run(years=1.0, stand_ids=["stand-1"])

    tree = simple_stand.plots[0].trees[0]
    assert tree.age == pytest.approx(12.0)
    assert simple_stand.attrs["years_simulated"] == pytest.approx(1.0)
    history = manager.get_history("stand-1")
    assert len(history) >= 2
    checkpoint = manager.get_latest_checkpoint("stand-1")
    assert checkpoint is not None
    assert checkpoint.metadata["module"] == module.name

    tree.age = 0.0
    manager.restore_from_checkpoint("stand-1", checkpoint)
    assert simple_stand.plots[0].trees[0].age == pytest.approx(12.0)


def test_manager_applies_rules(simple_stand: Stand) -> None:
    module = GrowthModule(IncrementAgeModel)
    manager = SimulationManager(seed_policy=FixedSeedPolicy(12))
    manager.register_stand("stand-2", simple_stand, modules=[module], tags=["managed"])

    def predicate(state: StandState) -> bool:
        stems = state.metric_estimates["Stems"]["TOTAL"]
        return stems >= 1

    def thin_first(manager: SimulationManager, stand_id: str, state: StandState) -> None:
        record = manager._require_stand(stand_id)  # noqa: SLF001 - test helper usage
        first_uid = state.plots[0].tree_uids[0]
        record.stand.thin_trees(uids=[first_uid])

    rule = Rule(
        name="thin-first",
        predicate=predicate,
        actions=[RuleAction(name="thin", callback=thin_first)],
    )
    manager.register_ruleset(
        "default", RuleSet(name="rs", rules=[rule], scope={"tags": ["managed"]})
    )

    manager.start_run()
    manager.run(years=1.0, stand_ids=["stand-2"])

    assert len(simple_stand.plots[0].trees) == 0
