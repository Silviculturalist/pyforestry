"""Sweden's scenario configuration: what it declares that the shared base does not."""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Mapping, Sequence

from pyforestry.simulation.presets import RulesetFn
from pyforestry.simulation.presets import ScenarioConfig as _ScenarioConfig
from pyforestry.sweden.simulation.policy import management_plan, scenario_factors

__all__ = ["ScenarioConfig"]


@dataclass(frozen=True)
class ScenarioConfig(_ScenarioConfig):
    """Sweden's scenario configuration.

    Declares the stage order and the rulesets; the seed derivation, guard flags,
    artifact accessor, identity and provenance are
    :class:`pyforestry.simulation.presets.ScenarioConfig`'s, which is what Sweden
    and Norway used to keep separate near-copies of.

    Runs nothing -- see the base class.
    """

    region: str = "Sweden"

    def stages(self) -> Sequence[str]:
        """Return the default ordered stage sequence for Sweden configurations."""
        return ("growth", "disturbance", "valuation")

    def rulesets(self) -> Mapping[str, RulesetFn]:
        """Return bound management/scenario ruleset callables for this configuration."""
        return {
            "management": partial(management_plan, self.scenario_id),
            "scenario": partial(scenario_factors, self.scenario_id),
        }
