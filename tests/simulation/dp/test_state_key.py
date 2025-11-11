"""Tests for the dynamic-programming state key utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pyforestry.simulation.dp import (
    SimulationProvenance,
    decode_model_views,
    encode_model_views,
    simulate_one_step_pure,
)


@dataclass(eq=True)
class DummyView:
    """Simple view used for property-based testing."""

    value: int
    label: str


class SimpleAdapter:
    """Deterministic adapter whose transitions depend only on the inputs."""

    def __init__(self, adapter_id: str, base_shift: int) -> None:
        self.adapter_id = adapter_id
        self._base_shift = base_shift

    def delta(self, *, part: str, action: str, view: DummyView) -> int:
        """Return the deterministic increment applied to ``view``."""

        return self._base_shift + len(part) + len(action) + len(view.label)

    def apply(self, *, part: str, action: str, model_view: DummyView):
        shift = self.delta(part=part, action=action, view=model_view)
        new_label = f"{model_view.label}:{action}" if model_view.label else action
        updated_view = DummyView(value=model_view.value + shift, label=new_label)
        return updated_view, float(updated_view.value)


lower_alpha = st.characters(min_codepoint=97, max_codepoint=122)
part_names = st.text(min_size=1, max_size=5, alphabet=lower_alpha)
labels = st.text(min_size=0, max_size=5, alphabet=lower_alpha)
views = st.builds(DummyView, value=st.integers(-50, 50), label=labels)


@given(
    parts=st.dictionaries(part_names, views, min_size=1, max_size=4),
)
def test_encode_decode_round_trip(parts: Dict[str, DummyView]) -> None:
    """Encoding a view mapping should be reversible and namespace aware."""

    provenance = SimulationProvenance(
        connector_id="connector-test",
        bucking_id="bucker-test",
        adapter_ids={name: f"adapter-{index}" for index, name in enumerate(parts, start=1)},
    )
    state_key = encode_model_views(parts, provenance)
    decoded = decode_model_views(state_key)

    assert decoded == parts
    assert state_key.namespace == provenance.namespace
    cache_namespace, _ = state_key.as_cache_key()
    assert cache_namespace == state_key.namespace
    assert provenance.connector_id in state_key.namespace
    assert provenance.bucking_id in state_key.namespace
    for adapter_id in provenance.adapter_ids.values():
        assert adapter_id in state_key.namespace


@given(
    parts=st.dictionaries(part_names, views, min_size=1, max_size=4),
    action=st.text(min_size=1, max_size=4, alphabet=lower_alpha),
    connector=st.text(min_size=1, max_size=4, alphabet=lower_alpha),
    bucking=st.text(min_size=1, max_size=4, alphabet=lower_alpha),
)
def test_simulate_one_step_pure_is_deterministic(
    parts: Dict[str, DummyView],
    action: str,
    connector: str,
    bucking: str,
) -> None:
    """Transitions derived from identical inputs should match exactly."""

    adapters = {
        part: SimpleAdapter(adapter_id=f"adapter-{index}", base_shift=index)
        for index, part in enumerate(sorted(parts), start=1)
    }
    provenance = SimulationProvenance.from_adapters(
        connector_id=connector,
        bucking_id=bucking,
        adapters=adapters,
    )
    state_key = encode_model_views(parts, provenance)

    next_key, reward = simulate_one_step_pure(
        state_key,
        action=action,
        adapters=adapters,
        provenance=provenance,
    )
    second_key, second_reward = simulate_one_step_pure(
        state_key,
        action=action,
        adapters=adapters,
        provenance=provenance,
    )

    assert next_key == second_key
    assert reward == second_reward

    decoded_next = decode_model_views(next_key)
    expected_reward = 0.0
    for part, updated in decoded_next.items():
        original = parts[part]
        shift = adapters[part].delta(part=part, action=action, view=original)
        assert updated.value == original.value + shift
        assert updated.label.endswith(action)
        expected_reward += float(updated.value)
    assert reward == expected_reward


def test_namespace_mismatch_rejected() -> None:
    """simulate_one_step_pure refuses to combine incompatible provenance."""

    parts = {"north": DummyView(value=5, label="seed")}
    adapters = {"north": SimpleAdapter(adapter_id="adapter-1", base_shift=1)}
    provenance = SimulationProvenance.from_adapters(
        connector_id="conn-a",
        bucking_id="buck-a",
        adapters=adapters,
    )
    state_key = encode_model_views(parts, provenance)
    mismatched = SimulationProvenance(
        connector_id="conn-b",
        bucking_id="buck-a",
        adapter_ids={"north": "adapter-1"},
    )

    with pytest.raises(ValueError):
        simulate_one_step_pure(
            state_key,
            action="grow",
            adapters=adapters,
            provenance=mismatched,
        )
