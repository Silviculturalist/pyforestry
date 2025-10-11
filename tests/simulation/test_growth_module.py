"""Tests covering the growth model protocol and module factory."""

from __future__ import annotations

import numpy as np
import pytest

from pyforestry.simulation.growth import GrowthModule, ModelResult
from pyforestry.simulation.state import StandState, TreeState


class DummyTreeModel:
    level = "tree"
    time_step = 0.5
    requires_checkpoint = False
    required_tree_fields = ("diameter_cm",)
    required_stand_fields = ("area_ha",)

    def __init__(self, factor: float = 1.0) -> None:
        self.factor = factor
        self.initialised = False

    def validate_inputs(self, stand_state: StandState, tree_states) -> None:  # noqa: D401
        assert stand_state.area_ha is not None
        for tree in tree_states:
            assert tree.diameter_cm is not None

    def initialize(self, context=None) -> None:  # noqa: D401
        self.initialised = True

    def step(self, years, rng, stand_state, tree_states):  # noqa: D401
        assert self.initialised
        increments = {tree.uid: {"diameter_cm": self.factor * years} for tree in tree_states}
        return ModelResult(tree_deltas=increments)

    def finalize(self) -> None:  # noqa: D401
        self.initialised = False


def build_tree_state(value: float) -> TreeState:
    return TreeState(
        uid="tree-1",
        species="picea abies",
        age=10.0,
        diameter_cm=value,
        height_m=15.0,
        weight_n=1.0,
        position=(0.0, 0.0),
        plot_id="plot-1",
    )


def build_stand_state() -> StandState:
    return StandState(
        site=None,
        area_ha=1.0,
        top_height_definition=None,
        attrs={},
        metric_estimates={"BasalArea": {"TOTAL": 20.0}},
        use_angle_count=False,
        plots=(),
    )


def test_growth_module_metadata_and_schema() -> None:
    module = GrowthModule(DummyTreeModel, config={"factor": 2.0})
    meta = module.metadata()
    assert meta["level"] == "tree"
    assert meta["time_step"] == pytest.approx(0.5)
    schema = module.schema()
    assert "factor" in schema


def test_growth_module_validates_required_fields() -> None:
    module = GrowthModule(DummyTreeModel)
    stand_state = build_stand_state()
    tree_states = [build_tree_state(25.0)]
    instance = module.instantiate()
    module.validate_inputs(stand_state, tree_states, instance=instance)
    instance.initialize({})
    result = instance.step(1.0, np.random.default_rng(1), stand_state, tree_states)
    assert result.tree_deltas["tree-1"]["diameter_cm"] == pytest.approx(1.0)


def test_growth_module_rejects_missing_fields() -> None:
    module = GrowthModule(DummyTreeModel)
    stand_state = build_stand_state()
    invalid_tree = TreeState(
        uid="tree-1",
        species="picea abies",
        age=10.0,
        diameter_cm=None,
        height_m=15.0,
        weight_n=1.0,
        position=(0.0, 0.0),
        plot_id="plot-1",
    )
    instance = module.instantiate()
    with pytest.raises(ValueError):
        module.validate_inputs(stand_state, [invalid_tree], instance=instance)


def test_growth_module_rejects_unknown_config_keys() -> None:
    with pytest.raises(TypeError):
        GrowthModule(DummyTreeModel, config={"unknown": 1})
