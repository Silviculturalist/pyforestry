"""Checkpoint helpers for serialising and restoring simulation state."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, Mapping, Tuple

if False:  # pragma: no cover - typing aid
    from pyforestry.simulation.stand_composite import StandComposite


@dataclass
class CompositeMemento:
    """Serializable snapshot of a stand composite."""

    seed: int
    contexts: Dict[str, Mapping[str, object]]
    growth_overrides: Dict[str, Mapping[str, object]]
    disturbance_overrides: Dict[str, Mapping[str, object]]
    rng_states: Dict[Tuple[str, ...], object]
    event_index: int = -1


class CheckpointSerializer:
    """Capture and restore composite level state."""

    def capture(self, composite: "StandComposite") -> CompositeMemento:
        """Return a :class:`CompositeMemento` representing ``composite``."""

        contexts: Dict[str, Mapping[str, object]] = {}
        growth_overrides: Dict[str, Mapping[str, object]] = {}
        disturbance_overrides: Dict[str, Mapping[str, object]] = {}
        for name, part in composite._parts.items():  # noqa: SLF001 - serializer needs internals
            contexts[name] = deepcopy(part.context)
            growth_overrides[name] = deepcopy(part.growth_overrides or {})
            disturbance_overrides[name] = deepcopy(part.disturbance_overrides or {})
        rng_states = composite.random_bundle.snapshot()
        return CompositeMemento(
            seed=composite.seed,
            contexts=contexts,
            growth_overrides=growth_overrides,
            disturbance_overrides=disturbance_overrides,
            rng_states=rng_states,
        )

    def restore(self, composite: "StandComposite", memento: CompositeMemento) -> None:
        """Restore ``composite`` state from ``memento``."""

        composite.seed = memento.seed
        composite.random_bundle.seed = memento.seed
        composite.telemetry.seed = memento.seed
        for name, part in composite._parts.items():  # noqa: SLF001 - serializer needs internals
            if name in memento.contexts:
                part.context = deepcopy(memento.contexts[name])
            if name in memento.growth_overrides:
                part.growth_overrides = deepcopy(memento.growth_overrides[name])
            if name in memento.disturbance_overrides:
                part.disturbance_overrides = deepcopy(memento.disturbance_overrides[name])
        composite.random_bundle.restore(memento.rng_states)
