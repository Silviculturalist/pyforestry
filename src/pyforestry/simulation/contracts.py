"""Simulation-runtime contracts.

This module holds only what the *runtime* defines. The provenance/introspection
vocabulary (:class:`~pyforestry.base.contracts.SourceReference`,
:class:`~pyforestry.base.contracts.Describable`,
:class:`~pyforestry.base.contracts.FormulaModuleDescriptor`) lives in
:mod:`pyforestry.base.contracts` and is *not* re-exported here: formula and domain
modules across every region expose that vocabulary, and nothing above ``base``
should have to import from the simulation tier to obtain it. Import it from
:mod:`pyforestry.base.contracts` directly.

``ParityCase`` and ``AssertionResult`` were removed rather than kept: a Protocol
for reproducible parity fixtures with no implementer and no caller, exported from
two ``__all__``s, reads as a contract something honours.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Protocol, Sequence


class SimulationPreset(Protocol):
    """Contract for a regional scenario configuration.

    Implemented by :class:`pyforestry.simulation.presets.ScenarioConfig`. Note
    what this is *not*: nothing executes a ``SimulationPreset``. ``stages()`` is
    recorded into a manifest, ``rulesets()`` and ``guard_policy()`` have no
    runtime caller, and the harness that consumes the result fills it with
    synthetic numbers. The runnable things are the composite pipelines under
    ``<region>/simulation/presets/`` and :func:`pyforestry.project`.
    """

    preset_id: str

    def seed_strategy(self, **kwargs: Any) -> int:
        """Return a deterministic seed for a run."""

    def stages(self) -> Sequence[str]:
        """Return the ordered stage identifiers for execution."""

    def rulesets(self) -> Mapping[str, Callable[..., Any]]:
        """Return scenario rulesets keyed by concern."""

    def guard_policy(self) -> Mapping[str, object]:
        """Return runtime guard settings."""

    def required_artifacts(self) -> Sequence[str]:
        """Return artifact ids that must be emitted under this configuration."""


__all__ = ["SimulationPreset"]
