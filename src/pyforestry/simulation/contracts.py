"""Simulation-runtime contracts: stages, presets, parity, and execution.

The provenance/introspection vocabulary (:class:`SourceReference`,
:class:`Describable`, :class:`FormulaModuleDescriptor`) lives at the base level
in :mod:`pyforestry.base.contracts` because formula modules across every region
expose it. It is re-exported here so existing ``pyforestry.simulation.contracts``
imports keep working and the simulation tier offers a single contracts surface.

Source:
    Internal pyforestry simulation architecture and runtime contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Callable, FrozenSet, Mapping, Optional, Protocol, Sequence

from pyforestry.base.contracts import Describable, FormulaModuleDescriptor, SourceReference

# ---------------------------------------------------------------------------
# Retained data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StageContract:
    """Describe the interfaces and side effects offered by a stage."""

    type_metadata: Mapping[str, Any] = field(default_factory=dict)
    units: Mapping[str, str] = field(default_factory=dict)
    crs: Optional[str] = None
    effects: FrozenSet[str] = field(default_factory=lambda: frozenset({"rng"}))

    def __post_init__(self) -> None:
        """Freeze the mapping and set fields to immutable views.

        Source:
            Internal pyforestry simulation architecture and runtime contracts.
        """
        object.__setattr__(self, "type_metadata", MappingProxyType(dict(self.type_metadata)))
        object.__setattr__(self, "units", MappingProxyType(dict(self.units)))
        object.__setattr__(self, "effects", frozenset(self.effects))


@dataclass(frozen=True)
class ActionEvent:
    """Scenario-policy event describing one requested action."""

    action: str
    params: Mapping[str, Any] = field(default_factory=dict)
    phase: Optional[str] = None


@dataclass(frozen=True)
class AssertionResult:
    """Parity-case assertion result payload."""

    passed: bool
    details: str = ""


# ---------------------------------------------------------------------------
# Execution tier (runtime contracts)
# ---------------------------------------------------------------------------


class SimulationPreset(Protocol):
    """Contract for runnable scenario preset bundles.

    Source:
        Internal pyforestry simulation architecture and runtime contracts.
    """

    preset_id: str

    def seed_strategy(self, **kwargs: Any) -> int:
        """Return a deterministic seed for a run."""

    def stages(self) -> Sequence[str]:
        """Return the ordered stage identifiers for execution."""

    def rulesets(self) -> Mapping[str, Callable[..., Any]]:
        """Return scenario rulesets keyed by scenario id."""

    def guard_policy(self) -> Mapping[str, object]:
        """Return runtime guard settings."""

    def required_artifacts(self) -> Sequence[str]:
        """Return artifact ids that must be emitted by this preset."""


class ParityCase(Protocol):
    """Contract for reproducible parity fixtures.

    Source:
        Internal pyforestry simulation architecture and runtime contracts.
    """

    case_id: str
    inputs: Mapping[str, Any]
    expected: Mapping[str, Any]
    tolerances: Mapping[str, float]

    def assert_case(self, actual: Mapping[str, Any]) -> AssertionResult:
        """Compare actual outputs with expected values and tolerances."""


__all__ = [
    # Data types
    "ActionEvent",
    "AssertionResult",
    "StageContract",
    # Introspection tier (re-exported from pyforestry.base.contracts)
    "Describable",
    "FormulaModuleDescriptor",
    "SourceReference",
    # Execution tier
    "ParityCase",
    "SimulationPreset",
]
