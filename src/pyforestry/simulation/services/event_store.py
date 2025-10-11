"""Event storage with content-addressable record identifiers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Dict, Mapping, Optional, Tuple, Union

__all__ = ["EventCategory", "EventRecord", "EventStore", "EventSnapshotter"]


class EventCategory(Enum):
    """Enumerate the event categories tracked by the store."""

    BIOLOGICAL = "biological"
    MANAGEMENT = "management"
    ECONOMIC = "economic"

    def __str__(self) -> str:  # pragma: no cover - convenience
        return self.value


@dataclass(frozen=True)
class EventRecord:
    """Immutable record captured by :class:`EventStore`."""

    id: str
    category: str
    kind: str
    payload: Mapping[str, object]
    metadata: Mapping[str, object]
    index: int

    def as_mapping(self) -> Mapping[str, object]:
        """Return a serialisable representation of the record."""

        return {
            "id": self.id,
            "category": self.category,
            "kind": self.kind,
            "payload": _convert_to_builtin(self.payload),
            "metadata": _convert_to_builtin(self.metadata),
            "index": self.index,
        }


def _convert_to_builtin(value: Any) -> Any:
    """Convert ``value`` into basic Python containers."""

    if isinstance(value, Mapping):
        return {str(key): _convert_to_builtin(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_convert_to_builtin(item) for item in value]
    if isinstance(value, set):
        return sorted(_convert_to_builtin(item) for item in value)
    if isinstance(value, Enum):
        return value.name
    if is_dataclass(value):
        return _convert_to_builtin(asdict(value))
    if hasattr(value, "as_mapping") and callable(value.as_mapping):
        return _convert_to_builtin(value.as_mapping())
    return value


def _canonicalise(value: Any) -> Any:
    """Return a canonically ordered representation of ``value``."""

    converted = _convert_to_builtin(value)
    if isinstance(converted, Mapping):
        return {key: _canonicalise(converted[key]) for key in sorted(converted)}
    if isinstance(converted, list):
        return [_canonicalise(item) for item in converted]
    return converted


class EventStore:
    """Append-only store that assigns content-addressed identifiers."""

    def __init__(self, *, model_id: Optional[str] = None, seed: int = 0) -> None:
        self.model_id = model_id or "stand"
        self.seed = int(seed)
        self._events: list[EventRecord] = []
        self._next_index = 0
        self._pruned_index = -1

    @staticmethod
    def _normalise_mapping(data: Mapping[str, Any]) -> Dict[str, Any]:
        return {str(key): _convert_to_builtin(value) for key, value in data.items()}

    @staticmethod
    def _coerce_category(category: Union[str, EventCategory]) -> str:
        if isinstance(category, EventCategory):
            return category.value
        return str(category)

    @staticmethod
    def _ensure_mapping(name: str, value: Mapping[str, Any]) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise TypeError(f"{name} must be a mapping")
        return value

    def _append(
        self,
        category: Union[str, EventCategory],
        kind: str,
        payload: Mapping[str, Any],
        *,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> EventRecord:
        base_metadata: Dict[str, Any] = {"model_id": self.model_id, "seed": self.seed}
        payload = self._ensure_mapping("payload", payload)
        if metadata is not None:
            metadata = self._ensure_mapping("metadata", metadata)
            base_metadata.update(self._normalise_mapping(metadata))
        payload_dict = self._normalise_mapping(payload)
        metadata_dict = base_metadata
        canonical = {
            "category": self._coerce_category(category),
            "kind": kind,
            "payload": _canonicalise(payload_dict),
            "metadata": _canonicalise(metadata_dict),
        }
        encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        identifier = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        index = self._next_index
        self._next_index += 1
        record = EventRecord(
            id=identifier,
            category=self._coerce_category(category),
            kind=kind,
            payload=MappingProxyType(payload_dict),
            metadata=MappingProxyType(metadata_dict),
            index=index,
        )
        self._events.append(record)
        return record

    def record_biological(
        self,
        kind: str,
        payload: Mapping[str, Any],
        *,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> EventRecord:
        """Append a biological event record."""

        return self._append(EventCategory.BIOLOGICAL, kind, payload, metadata=metadata)

    def record_management(
        self,
        kind: str,
        payload: Mapping[str, Any],
        *,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> EventRecord:
        """Append a management-related event record."""

        return self._append(EventCategory.MANAGEMENT, kind, payload, metadata=metadata)

    def record_economic(
        self,
        kind: str,
        payload: Mapping[str, Any],
        *,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> EventRecord:
        """Append an economic event record."""

        return self._append(EventCategory.ECONOMIC, kind, payload, metadata=metadata)

    def iter_records(
        self,
        *,
        category: Optional[Union[str, EventCategory]] = None,
        kind: Optional[str] = None,
        start_index: Optional[int] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> Tuple[EventRecord, ...]:
        """Return recorded events filtered by category, kind, metadata and index.

        Args:
            category: Restrict results to a particular event category.
            kind: Restrict results to events with the given ``kind`` identifier.
            start_index: When provided, exclude events whose ``index`` is strictly
                less than ``start_index``. The value must be greater than the most
                recently pruned index otherwise a :class:`ValueError` is raised.
            metadata: Restrict results to events that contain the provided
                metadata key/value pairs.
            limit: Restrict the number of records returned. ``None`` keeps all
                matches while non-negative integers cap the result length.
        """

        if start_index is not None and start_index <= self._pruned_index:
            raise ValueError(
                "start_index must be greater than the pruned watermark to ensure "
                "pruned events are not referenced",
            )
        if limit is not None and limit < 0:
            raise ValueError("limit must be greater than or equal to zero")
        if limit == 0:
            return ()

        category_value = self._coerce_category(category) if category is not None else None
        metadata_filters: Optional[Tuple[Tuple[str, Any], ...]] = None
        if metadata is not None:
            normalised = self._normalise_mapping(self._ensure_mapping("metadata", metadata))
            metadata_filters = tuple(normalised.items())

        selected: list[EventRecord] = []
        for record in self._events:
            if start_index is not None and record.index < start_index:
                continue
            if category_value is not None and record.category != category_value:
                continue
            if kind is not None and record.kind != kind:
                continue
            if metadata_filters is not None and any(
                record.metadata.get(key) != value for key, value in metadata_filters
            ):
                continue
            selected.append(record)
            if limit is not None and len(selected) >= limit:
                break
        return tuple(selected)

    @property
    def last_index(self) -> int:
        """Return the index of the most recently appended record."""

        return self._next_index - 1

    @property
    def pruned_index(self) -> int:
        """Return the highest index pruned from the store."""

        return self._pruned_index

    def prune_through(self, index: int) -> None:
        """Discard records whose indices are ``<= index``."""

        if index <= self._pruned_index:
            return
        self._events = [record for record in self._events if record.index > index]
        self._pruned_index = index

    def clear(self) -> None:
        """Remove all recorded events without altering the next index."""

        self._events.clear()

    def reset(self, next_index: int = 0) -> None:
        """Reset the store to ``next_index`` clearing buffered events."""

        if next_index < 0:
            raise ValueError("next_index must be non-negative")
        self._events.clear()
        self._next_index = next_index
        self._pruned_index = next_index - 1

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._events)


class EventSnapshotter:
    """Fold event streams into checkpoint snapshots."""

    def __init__(self, store: EventStore, serializer: "CheckpointSerializer") -> None:
        self._store = store
        self._serializer = serializer

    def capture(self, composite: "StandComposite") -> "CompositeMemento":
        """Return a snapshot capturing the composite and event watermark."""

        memento = self._serializer.capture(composite)
        memento.event_index = self._store.last_index
        if memento.event_index >= 0:
            self._store.prune_through(memento.event_index)
        return memento

    def restore(self, composite: "StandComposite", memento: "CompositeMemento") -> None:
        """Restore ``composite`` and reset the store watermark."""

        self._serializer.restore(composite, memento)
        self._store.reset(memento.event_index + 1)


if False:  # pragma: no cover - typing aid
    from pyforestry.simulation.stand_composite import StandComposite

    from .checkpoint import CheckpointSerializer, CompositeMemento
