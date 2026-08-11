"""Sweden's scenario configuration: what it declares that the shared base does not."""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Mapping, Sequence

from pyforestry.simulation.forcing import ForcingSet
from pyforestry.simulation.presets import RulesetFn
from pyforestry.simulation.presets import ScenarioConfig as _ScenarioConfig
from pyforestry.sweden.simulation.policy import management_plan, scenario_forcings

__all__ = ["ScenarioConfig"]


@dataclass(frozen=True)
class ScenarioConfig(_ScenarioConfig):
    """Sweden's scenario configuration.

    Declares the stage order and the rulesets; the seed derivation, guard flags,
    artifact accessor, identity and provenance are
    :class:`pyforestry.simulation.presets.ScenarioConfig`'s, which is what Sweden
    and Norway used to keep separate near-copies of.

    Executed by :func:`~pyforestry.simulation.scenario.run_scenario`, through
    :func:`~pyforestry.sweden.simulation.orchestration.run_sweden_scenario` --
    see the base class.
    """

    region: str = "Sweden"

    def stages(self) -> Sequence[str]:
        """Return the default ordered stage sequence for Sweden configurations.

        Management, disturbance, growth, then valuation: thin the stand you have,
        take the scenario's losses off what remains, grow the survivors, and price
        what came out. Management and disturbance are exact no-ops unless the run
        configures a thinning schedule or a disturbance rate.

        ``"management"`` was absent while nothing executed any of these, so the
        valuation stage had nothing to price even in principle.
        """
        return ("management", "disturbance", "growth", "valuation")

    def rulesets(self) -> Mapping[str, RulesetFn]:
        """Return bound management/scenario ruleset callables for this configuration."""
        return {
            "management": partial(management_plan, self.scenario_id),
        }

    def forcings(self) -> ForcingSet:
        """Return the forcings this scenario declares -- none, in this package.

        A forcing is imposed from outside the models, so it is a claim about the
        world; a caller supplies its own to ``run_scenario`` and the manifest
        records them with their citations.
        """
        return scenario_forcings(self.scenario_id)
