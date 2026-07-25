"""Tests for stand composite coordination helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

import pytest

from pyforestry.simulation import (
    DispatchResult,
    StandAction,
    StandComposite,
    StandPart,
)


@dataclass
class DummyModelView:
    """Simple view exposing stand-level metrics for tests."""

    basal_area: float
    stems: float
    cash: float

    def total(self, metric_name: str) -> float:
        values = {"BasalArea": self.basal_area, "Stems": self.stems, "Cash": self.cash}
        return float(values[metric_name])


def _tracking_handler(history: List[str], action_name: str) -> Any:
    """Create a handler that records the part name before returning."""

    def handler(part: StandPart) -> str:
        history.append(f"{part.name}:{action_name}")
        return f"handled:{part.name}:{action_name}"

    return handler


def test_composite_aggregates_metrics_and_context() -> None:
    """Basal area, stems and cash are aggregated across all parts."""

    north = StandPart(
        "north",
        model_view=DummyModelView(10.5, 120, 45.0),
        context={"growth": {"target_ba": 12.0}},
        growth_overrides={"target_ba": 15.0},
    )
    south = StandPart(
        "south",
        model_view=DummyModelView(7.0, 90, 30.0),
        context={"disturbance": {"fire": 0.1}},
        disturbance_overrides={"fire": 0.2},
    )
    unmanaged = StandPart(
        "reserve",
        model_view=object(),
        context={"basal_area": 2.5, "stems": 40, "cash": 12.0},
    )
    composite = StandComposite([north, south, unmanaged])

    assert composite.total_basal_area == pytest.approx(20.0)
    assert composite.total_stems == pytest.approx(250.0)
    assert composite.total_cash == pytest.approx(87.0)
    assert north.growth_parameters == {"target_ba": 15.0}
    assert south.disturbance_parameters == {"fire": 0.2}


def test_dispatch_enforces_budget_and_harvest_caps() -> None:
    """Dispatch stops when the shared constraints would be exceeded."""

    composite = StandComposite(
        [
            StandPart("north", DummyModelView(5.0, 50, 10.0)),
            StandPart("south", DummyModelView(3.0, 40, 8.0)),
        ],
        budget=100.0,
        harvest_cap=5.0,
    )

    history: List[str] = []
    actions = [
        StandAction(
            "thin-north",
            _tracking_handler(history, "thin"),
            cost=40.0,
            harvest=2.0,
            target_parts="north",
        ),
        StandAction(
            "thin-south",
            _tracking_handler(history, "thin"),
            cost=35.0,
            harvest=1.5,
            target_parts="south",
        ),
        StandAction(
            "extra",
            _tracking_handler(history, "extra"),
            cost=30.0,
            harvest=1.0,
            target_parts="north",
        ),
    ]
    with pytest.raises(RuntimeError, match="budget"):
        composite.dispatch(actions, policy="target")
    # Only the first two actions should have executed.
    assert history == ["north:thin", "south:thin"]

    harvest_history: List[str] = []
    harvest_actions = [
        StandAction(
            "first",
            _tracking_handler(harvest_history, "harvest"),
            cost=10.0,
            harvest=3.0,
            target_parts="north",
        ),
        StandAction(
            "second",
            _tracking_handler(harvest_history, "harvest"),
            cost=15.0,
            harvest=3.0,
            target_parts="south",
        ),
    ]
    with pytest.raises(RuntimeError, match="harvest cap"):
        composite.dispatch(harvest_actions, policy="target")
    assert harvest_history == ["north:harvest"]


def test_dispatch_policies_route_to_expected_parts() -> None:
    """Built-in and custom policies determine which parts receive actions."""

    parts = [
        StandPart("north", DummyModelView(12.0, 110, 50.0), context={"region": "north"}),
        StandPart("south", DummyModelView(8.0, 90, 40.0), context={"region": "south"}),
        StandPart("central", DummyModelView(5.0, 80, 30.0), context={"region": "central"}),
    ]
    composite = StandComposite(parts)

    # Targeted dispatch.
    history: List[str] = []
    result = composite.dispatch(
        [StandAction("tend", _tracking_handler(history, "tend"), target_parts="north")],
        policy="target",
    )
    assert isinstance(result, DispatchResult)
    assert [(record.part, record.action) for record in result.records] == [("north", "tend")]

    # Broadcast dispatch hits every part.
    history.clear()
    result = composite.dispatch(
        [StandAction("fertilize", _tracking_handler(history, "fert"))],
        policy="broadcast",
    )
    assert sorted((record.part, record.action) for record in result.records) == [
        ("central", "fertilize"),
        ("north", "fertilize"),
        ("south", "fertilize"),
    ]

    # Largest-first dispatch picks the part with the largest basal area.
    history.clear()
    result = composite.dispatch(
        [StandAction("thin", _tracking_handler(history, "thin"))],
        policy="largest_first",
    )
    assert [(record.part, record.action) for record in result.records] == [("north", "thin")]

    # Custom policy selecting parts by region flag.
    def north_and_central(action: StandAction, available: tuple[StandPart, ...]):
        return tuple(
            part for part in available if part.context.get("region") in {"north", "central"}
        )

    history.clear()
    result = composite.dispatch(
        [StandAction("survey", _tracking_handler(history, "survey"))],
        policy=north_and_central,
    )
    assert sorted((record.part, record.action) for record in result.records) == [
        ("central", "survey"),
        ("north", "survey"),
    ]


def test_composite_snapshot_and_restore_resets_state() -> None:
    part = StandPart(
        "alpha",
        DummyModelView(0.0, 0.0, 0.0),
        context={"values": []},
    )
    composite = StandComposite([part], seed=99, model_id="snapshot")
    rng = composite.random_bundle.rng_for("checkpoint", part.name)

    first = rng.random()
    part.context["values"].append(first)
    snapshot = composite.snapshot()

    second = rng.random()
    part.context["values"].append(second)
    composite.restore(snapshot)

    assert part.context["values"] == [first]
    restored_rng = composite.random_bundle.rng_for("checkpoint", part.name)
    assert restored_rng.random() == pytest.approx(second)


def test_stand_action_handler_analysis_variants():
    part = StandPart("alpha", DummyModelView(1.0, 1.0, 1.0))
    dummy_rng = object()

    def handler_kwargs(part: StandPart, **kwargs):
        return kwargs.get("rng")

    action_kwargs = StandAction("kw", handler_kwargs)
    assert action_kwargs.requests_rng
    assert action_kwargs.requests_io
    assert action_kwargs.execute(part, rng=dummy_rng) is dummy_rng
    assert action_kwargs.execute(part, rng=None) is None

    def handler_args(part: StandPart, *args):
        return args

    action_args = StandAction("args", handler_args)
    assert action_args.requests_rng
    assert action_args.execute(part, rng=dummy_rng) == (dummy_rng,)

    def handler_extra(part: StandPart, extra):
        return extra

    action_extra = StandAction("extra", handler_extra)
    assert action_extra.requests_rng
    assert action_extra.execute(part, rng=dummy_rng) is dummy_rng


def test_stand_action_iter_targets():
    action = StandAction("noop", handler=lambda part: None)
    assert action.iter_targets() == ()

    action = StandAction("north", handler=lambda part: None, target_parts="north")
    assert action.iter_targets() == ("north",)

    action = StandAction("multi", handler=lambda part: None, target_parts=("a", "b"))
    assert action.iter_targets() == ("a", "b")


def test_dispatch_result_by_part_groups_records():
    action = StandAction("noop", handler=lambda part: "ok")
    record_north = StandPart("north", DummyModelView(1.0, 1.0, 1.0)).apply_action(action)
    record_south = StandPart("south", DummyModelView(1.0, 1.0, 1.0)).apply_action(action)
    result = DispatchResult(records=[record_north, record_south])
    grouped = result.by_part()
    assert set(grouped) == {"north", "south"}


def test_stand_part_validation_and_metric_fallbacks():
    with pytest.raises(ValueError):
        StandPart("", DummyModelView(1.0, 1.0, 1.0))
    with pytest.raises(TypeError):
        StandPart("bad", DummyModelView(1.0, 1.0, 1.0), context=[])

    class CallableView:
        def basal_area(self):
            return 3.0

    part = StandPart("callable", CallableView(), context={"basal_area": 1.0})
    assert part.basal_area == pytest.approx(3.0)

    class WeirdView:
        basal_area = object()
        BasalArea = object()

        def total(self, metric_name: str) -> float:
            raise KeyError(metric_name)

    fallback = StandPart("fallback", WeirdView(), context={"basal_area": 2.5})
    assert fallback.basal_area == pytest.approx(2.5)


def test_stand_part_apply_action_effects():
    part = StandPart("alpha", DummyModelView(1.0, 1.0, 1.0))
    action = StandAction("noop", handler=lambda part: "ok")
    record = part.apply_action(action, effects=frozenset({"io"}))
    assert record.action == "noop"


def test_composite_duplicate_part_name_raises():
    part = StandPart("dup", DummyModelView(1.0, 1.0, 1.0))
    composite = StandComposite([part])
    with pytest.raises(ValueError, match="Duplicate"):
        composite.add_part(part)


def test_composite_select_parts_edge_cases():
    part = StandPart("alpha", DummyModelView(1.0, 1.0, 1.0))
    composite = StandComposite([part])
    action = StandAction("noop", handler=lambda part: None)

    selected = composite._select_parts(action, policy=lambda action, parts: ())
    assert selected == ()

    with pytest.raises(ValueError, match="target parts"):
        composite._select_parts(action, policy="target")

    empty_composite = StandComposite([])
    assert empty_composite._select_parts(action, policy="largest_first") == ()

    with pytest.raises(ValueError, match="Unknown dispatch policy"):
        composite._select_parts(action, policy="unknown")


def test_composite_dispatch_skips_empty_selection():
    part = StandPart("alpha", DummyModelView(1.0, 1.0, 1.0))
    composite = StandComposite([part])
    action = StandAction("noop", handler=lambda part: None)
    result = composite.dispatch([action], policy=lambda action, parts: ())
    assert result.records == []
