"""Telemetry publishing helpers for simulation events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Mapping, Optional


@dataclass
class TelemetryEvent:
    """Record emitted by :class:`TelemetryPublisher`."""

    type: str
    payload: Mapping[str, object]


class TelemetryPublisher:
    """Publish telemetry events, enriching payloads with provenance metadata."""

    def __init__(
        self,
        *,
        model_id: Optional[str],
        seed: int,
        sink: Optional[Callable[[TelemetryEvent], None]] = None,
    ) -> None:
        self.model_id = model_id or "unknown"
        self.seed = int(seed)
        self._events: List[TelemetryEvent] = []
        self._sink = sink

    def publish(self, event_type: str, payload: Mapping[str, object]) -> None:
        """Emit a telemetry event augmented with provenance metadata."""

        enriched: Dict[str, object] = {
            "metadata": {"model_id": self.model_id, "seed": self.seed},
            **dict(payload),
        }
        event = TelemetryEvent(type=event_type, payload=enriched)
        self._events.append(event)
        if self._sink is not None:
            self._sink(event)

    @property
    def events(self) -> List[TelemetryEvent]:
        """Return a copy of the recorded events."""

        return list(self._events)

    def clear(self) -> None:
        """Discard buffered events."""

        self._events.clear()
