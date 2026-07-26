"""Simulation-runtime contracts: stages, presets, parity, and execution.

This module holds only what the *runtime* defines. The provenance/introspection
vocabulary (:class:`~pyforestry.base.contracts.SourceReference`,
:class:`~pyforestry.base.contracts.Describable`,
:class:`~pyforestry.base.contracts.FormulaModuleDescriptor`) lives in
:mod:`pyforestry.base.contracts` and is *not* re-exported here: formula and domain
modules across every region expose that vocabulary, and nothing above ``base``
should have to import from the simulation tier to obtain it. Import it from
:mod:`pyforestry.base.contracts` directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Callable, FrozenSet, Mapping, Optional, Protocol, Sequence

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
        """Freeze the mapping and set fields to immutable views."""
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
    """Contract for runnable scenario preset bundles."""

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
    """Contract for reproducible parity fixtures."""

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
    # Execution tier
    "ParityCase",
    "SimulationPreset",
]
