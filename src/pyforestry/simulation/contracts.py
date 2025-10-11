"""Contracts describing the capabilities exposed by simulation stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, FrozenSet, Mapping, Optional


@dataclass(frozen=True)
class StageContract:
    """Describe the interfaces and side effects offered by a stage."""

    type_metadata: Mapping[str, Any] = field(default_factory=dict)
    units: Mapping[str, str] = field(default_factory=dict)
    crs: Optional[str] = None
    effects: FrozenSet[str] = field(default_factory=lambda: frozenset({"rng"}))

    def __post_init__(self) -> None:
        object.__setattr__(self, "type_metadata", MappingProxyType(dict(self.type_metadata)))
        object.__setattr__(self, "units", MappingProxyType(dict(self.units)))
        object.__setattr__(self, "effects", frozenset(self.effects))
