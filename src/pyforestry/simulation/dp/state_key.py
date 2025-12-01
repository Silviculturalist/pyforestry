"""Utilities for encoding model views into deterministic cache keys."""

from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, MutableMapping, Protocol, Tuple


class DeterministicAdapter(Protocol):
    """Protocol describing deterministic state transition adapters."""

    adapter_id: str

    def apply(self, *, part: str, action: str, model_view: Any) -> Tuple[Any, float]:
        """Return the next model view for ``part`` and the reward for ``action``."""


@dataclass(frozen=True)
class SimulationProvenance:
    """Identify the provenance of cached simulation results."""

    connector_id: str
    bucking_id: str
    adapter_ids: Mapping[str, str]
    _adapter_ids: Tuple[Tuple[str, str], ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.connector_id:
            raise ValueError("connector_id must be a non-empty string.")
        if not self.bucking_id:
            raise ValueError("bucking_id must be a non-empty string.")
        adapter_pairs = tuple(
            sorted((str(part), str(adapter)) for part, adapter in dict(self.adapter_ids).items())
        )
        object.__setattr__(self, "adapter_ids", dict(adapter_pairs))
        object.__setattr__(self, "_adapter_ids", adapter_pairs)

    @property
    def adapter_signature(self) -> Tuple[Tuple[str, str], ...]:
        """Return a normalized tuple describing the adapters used."""

        return self._adapter_ids

    @property
    def namespace(self) -> str:
        """Return a cache namespace that encodes the full provenance."""

        adapter_segment = ",".join(f"{part}={adapter}" for part, adapter in self.adapter_signature)
        return (
            f"connector={self.connector_id}|bucking={self.bucking_id}|adapters={adapter_segment}"
        )

    @classmethod
    def from_adapters(
        cls,
        *,
        connector_id: str,
        bucking_id: str,
        adapters: Mapping[str, DeterministicAdapter],
    ) -> "SimulationProvenance":
        """Build provenance information from the supplied ``adapters``."""

        adapter_ids: Dict[str, str] = {}
        for part, adapter in adapters.items():
            adapter_ids[str(part)] = getattr(adapter, "adapter_id", adapter.__class__.__qualname__)
        return cls(connector_id=connector_id, bucking_id=bucking_id, adapter_ids=adapter_ids)


@dataclass(frozen=True)
class PartKey:
    """Encoded representation of a single model view."""

    part: str
    view_type: str
    payload_hex: str


@dataclass(frozen=True)
class ModelViewStateKey:
    """Cache-ready encoding of model views grouped by stand part."""

    namespace: str
    parts: Tuple[PartKey, ...]

    def as_cache_key(self) -> Tuple[str, Tuple[Tuple[str, str, str], ...]]:
        """Return a tuple suitable for use as a cache dictionary key."""

        return (
            self.namespace,
            tuple((part.part, part.view_type, part.payload_hex) for part in self.parts),
        )


def _pickle_view(model_view: Any) -> str:
    try:
        payload = pickle.dumps(model_view, protocol=pickle.HIGHEST_PROTOCOL)
    except pickle.PicklingError as exc:  # pragma: no cover - defensive guard
        raise TypeError("Model view must be serialisable with pickle.") from exc
    return payload.hex()


def _unpickle_view(payload_hex: str) -> Any:
    payload = bytes.fromhex(payload_hex)
    return pickle.loads(payload)


def encode_model_views(
    model_views: Mapping[str, Any],
    provenance: SimulationProvenance,
) -> ModelViewStateKey:
    """Encode ``model_views`` into a :class:`ModelViewStateKey`."""

    encoded_parts = []
    for part, view in sorted(model_views.items(), key=lambda item: item[0]):
        view_type = f"{view.__class__.__module__}:{view.__class__.__qualname__}"
        encoded_parts.append(
            PartKey(
                part=str(part),
                view_type=view_type,
                payload_hex=_pickle_view(view),
            )
        )
    return ModelViewStateKey(namespace=provenance.namespace, parts=tuple(encoded_parts))


def decode_model_views(state_key: ModelViewStateKey) -> Dict[str, Any]:
    """Return the decoded model views for ``state_key``."""

    decoded: Dict[str, Any] = {}
    for part in state_key.parts:
        decoded[part.part] = _unpickle_view(part.payload_hex)
    return decoded


def simulate_one_step_pure(
    state_key: ModelViewStateKey,
    *,
    action: str,
    adapters: Mapping[str, DeterministicAdapter],
    provenance: SimulationProvenance,
) -> Tuple[ModelViewStateKey, float]:
    """Advance ``state_key`` by one action using deterministic ``adapters``."""

    if state_key.namespace != provenance.namespace:
        raise ValueError(
            "State key namespace does not match the supplied provenance; the cache "
            "entry was produced by incompatible connectors or adapters."
        )
    current_views = decode_model_views(state_key)
    next_views: MutableMapping[str, Any] = {}
    total_reward = 0.0
    for part_name, current_view in current_views.items():
        try:
            adapter = adapters[part_name]
        except KeyError as exc:  # pragma: no cover - defensive
            raise KeyError(f"Missing deterministic adapter for part '{part_name}'.") from exc
        next_view, reward = adapter.apply(part=part_name, action=action, model_view=current_view)
        next_views[part_name] = next_view
        total_reward += float(reward)
    next_key = encode_model_views(next_views, provenance)
    return next_key, total_reward


__all__ = [
    "DeterministicAdapter",
    "ModelViewStateKey",
    "PartKey",
    "SimulationProvenance",
    "decode_model_views",
    "encode_model_views",
    "simulate_one_step_pure",
]
