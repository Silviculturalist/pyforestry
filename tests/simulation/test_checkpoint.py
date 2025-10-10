"""Tests for simulation checkpoint primitives."""

from __future__ import annotations

from datetime import datetime

import pytest

from pyforestry.base.helpers import CircularPlot, Stand, Tree
from pyforestry.base.helpers.primitives.cartesian_position import Position
from pyforestry.simulation.checkpoint import SimulationCheckpoint, TreeCheckpointer


@pytest.fixture
def sample_stand() -> Stand:
    trees = [
        Tree(uid="t1", species="picea abies", diameter_cm=30.0, height_m=18.0, age=40.0),
        Tree(uid="t2", species="pinus sylvestris", diameter_cm=25.0, height_m=15.0, age=35.0),
    ]
    plot = CircularPlot(id="p1", radius_m=5.0, position=Position(0, 0), trees=trees)
    stand = Stand(area_ha=1.0, plots=[plot])
    return stand


def test_tree_state_capture_contains_expected_fields(sample_stand: Stand) -> None:
    checkpointer = TreeCheckpointer()
    tree_states = checkpointer.capture_tree_states(sample_stand)
    assert len(tree_states) == 2
    first = tree_states[0]
    assert first.uid == "t1"
    assert first.diameter_cm == pytest.approx(30.0)
    assert first.plot_id == "p1"
    assert first.deltas == {}
    assert first.extras == {}


def test_tree_state_capture_preserves_custom_metadata(sample_stand: Stand) -> None:
    tree = sample_stand.plots[0].trees[0]
    tree.deltas = {"age": 0.5, "height_m": 1}
    tree.extras = {"source": "model", "notes": ["baseline"]}

    checkpointer = TreeCheckpointer()
    tree_states = checkpointer.capture_tree_states(sample_stand)

    captured = next(state for state in tree_states if state.uid == tree.uid)
    assert captured.deltas["age"] == pytest.approx(0.5)
    assert captured.deltas["height_m"] == pytest.approx(1.0)
    assert captured.extras["source"] == "model"
    assert captured.extras["notes"] == ["baseline"]


def test_checkpoint_roundtrip_restores_metrics(sample_stand: Stand) -> None:
    checkpointer = TreeCheckpointer()
    first_tree = sample_stand.plots[0].trees[0]
    first_tree.deltas = {"age": 1.0}
    first_tree.extras = {"note": "original"}
    baseline = checkpointer.create_checkpoint(
        sample_stand,
        seed_state={"seed": 7},
        active_modules=["dummy"],
        timestamp=datetime(2024, 1, 1),
    )
    original_basal_area = float(sample_stand.BasalArea)

    new_tree = Tree(uid="t3", species="picea abies", diameter_cm=20.0, height_m=12.0)
    new_plot = CircularPlot(id="p2", radius_m=4.0, position=Position(10, 0), trees=[new_tree])
    sample_stand.append_plot(new_plot)
    sample_stand.thin_trees(uids=["t1"])

    checkpointer.restore(sample_stand, baseline)

    assert len(sample_stand.plots) == 1
    restored_tree_uids = {tree.uid for plot in sample_stand.plots for tree in plot.trees}
    assert restored_tree_uids == {"t1", "t2"}
    assert float(sample_stand.BasalArea) == pytest.approx(original_basal_area)

    restored_first = next(
        tree for plot in sample_stand.plots for tree in plot.trees if tree.uid == "t1"
    )
    assert restored_first.deltas == {"age": 1.0}
    assert restored_first.extras == {"note": "original"}


def test_checkpoint_serialisation_roundtrip(sample_stand: Stand) -> None:
    checkpointer = TreeCheckpointer()
    checkpoint = checkpointer.create_checkpoint(sample_stand, seed_state={"seed": 99})
    payload = checkpoint.to_dict()
    rebuilt = SimulationCheckpoint.from_dict(payload)
    assert rebuilt.seed_state["seed"] == 99
    assert len(rebuilt.tree_states) == len(checkpoint.tree_states)
    assert rebuilt.stand_state.area_ha == pytest.approx(sample_stand.area_ha)
