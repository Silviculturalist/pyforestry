"""Shared scaffolding for regional scenario presets.

Regional preset bundles (Sweden, Norway, ...) share an identical guard policy,
required-artifact accessor, and identity scheme, while differing in their seed
derivation, stage ordering, rulesets, and provenance. :class:`ScenarioConfigBase`
captures the shared behaviour so each region only declares its own fields and
region-specific logic.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from pyforestry.base.contracts import Describable
from pyforestry.simulation.contracts import SimulationPreset


class ScenarioConfigBase(SimulationPreset):
    """Shared :class:`SimulationPreset` behaviour for regional scenario presets.

    Concrete subclasses are expected to be frozen dataclasses that declare the
    ``preset_id``, ``scenario_id`` and ``_required_artifacts`` fields and that
    provide the region-specific ``seed_strategy``, ``stages``, ``rulesets`` and
    ``source`` members.
    """

    def guard_policy(self) -> Mapping[str, object]:
        """Return non-formula guard policy flags applied at runtime."""
        return {
            "clamp_net_volume_to_zero": True,
            "reject_negative_inputs": True,
        }

    def required_artifacts(self) -> Sequence[str]:
        """Return the artifact names required by this preset contract."""
        return self._required_artifacts

    @property
    def component_id(self) -> str:
        """Stable identifier for this preset (``<preset_id>/<scenario_id>``)."""
        return f"{self.preset_id}/{self.scenario_id}"

    @property
    def components(self) -> Sequence[Describable]:
        """Describable components composed by this preset."""
        return ()
