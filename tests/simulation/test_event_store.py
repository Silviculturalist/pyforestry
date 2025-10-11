"""Tests for the event store and snapshotting helpers."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from pyforestry.simulation import (
    EventCategory,
    EventStore,
    GrowthModule,
    StandAction,
    StandComposite,
    StandPart,
)


@dataclass
class _StaticModelView:
    """Minimal view exposing capabilities for testing."""

    capabilities: tuple[str, ...] = ("grow",)
    model_id: str = "model-1"

    def has_capability(self, capability: str) -> bool:
        return capability in self.capabilities


def _growth_action() -> StandAction:
    def handler(part: StandPart) -> str:
        part.context.setdefault("calls", 0)
        part.context["calls"] += 1
        return part.name

    action = StandAction(name="grow", handler=handler, cost=2.5, harvest=1.2)
    action.requires_capabilities = ("grow",)
    return action


def test_event_store_generates_content_addressed_ids() -> None:
    store = EventStore(model_id="test", seed=7)
    payload = {"stage": "growth", "phase": "apply", "part": "alpha", "records": ()}
    first = store.record_biological("growth.apply", payload)
    second = store.record_biological("growth.apply", payload)

    assert first.id == second.id
    assert first.index == 0
    assert second.index == 1
    assert store.iter_records(category="biological")[-1].metadata["model_id"] == "test"

    store.prune_through(first.index)
    assert tuple(record.index for record in store.iter_records()) == (second.index,)
    store.prune_through(second.index)
    assert store.iter_records() == ()


def test_iter_records_filtering_and_index_validation() -> None:
    store = EventStore(model_id="filter", seed=9)
    first = store.record_biological("growth.apply", {"index": 0})
    store.record_management("management.apply", {"index": 1})
    store.record_biological("growth.run", {"index": 2}, metadata={"part": "alpha"})

    selected = store.iter_records(
        category=EventCategory.BIOLOGICAL,
        kind="growth.run",
        start_index=first.index + 1,
        metadata={"part": "alpha"},
    )

    assert [record.kind for record in selected] == ["growth.run"]

    store.prune_through(first.index)
    with pytest.raises(ValueError):
        store.iter_records(start_index=first.index)


def test_iter_records_supports_metadata_filters_and_limits() -> None:
    store = EventStore(model_id="filters", seed=4)
    store.record_management(
        "management.apply",
        {"index": 0},
        metadata={"stage": "management", "part": "alpha"},
    )
    second = store.record_management(
        "management.apply",
        {"index": 1},
        metadata={"stage": "management", "part": "beta"},
    )

    filtered = store.iter_records(metadata={"part": "beta"})
    assert [record.index for record in filtered] == [second.index]

    limited = store.iter_records(metadata={"stage": "management"}, limit=1)
    assert len(limited) == 1

    assert store.iter_records(metadata={"stage": "management"}, limit=0) == ()

    with pytest.raises(TypeError):
        store.iter_records(metadata=("invalid",))  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        store.iter_records(limit=-1)


def test_event_store_requires_mapping_inputs() -> None:
    store = EventStore()
    with pytest.raises(TypeError):
        store.record_biological("invalid", 1)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        store.record_management(
            "invalid",
            {"ok": True},
            metadata=("not", "a", "mapping"),  # type: ignore[arg-type]
        )


def test_event_snapshotter_prunes_and_allows_deterministic_replay() -> None:
    view = _StaticModelView()
    part = StandPart("alpha", view, context={})
    part.growth_overrides = {"actions": (_growth_action(),)}
    composite = StandComposite((part,), seed=11, model_id="snapshot")
    module = GrowthModule(composite)

    baseline = composite.snapshot()
    module.run_cycle()
    first_records = composite.iter_event_records()
    first_ids = [record.id for record in first_records]
    first_indices = [record.index for record in first_records]
    assert first_records
    first_kind = first_records[0].kind

    filtered_records = composite.iter_event_records(
        kind=first_kind,
        metadata={"part": part.name},
        limit=1,
    )
    assert filtered_records
    assert filtered_records[0].kind == first_kind

    composite.snapshot()
    assert composite.iter_event_records() == ()

    composite.restore(baseline)
    module = GrowthModule(composite)
    module.run_cycle()
    replayed_records = composite.iter_event_records()

    assert [record.id for record in replayed_records] == first_ids
    assert [record.index for record in replayed_records] == first_indices
