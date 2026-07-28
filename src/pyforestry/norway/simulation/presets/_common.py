"""Norway's scenario configuration: what it declares that the shared base does not."""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Mapping, Sequence

from pyforestry.norway.simulation.policy import management_plan, scenario_forcings
from pyforestry.simulation.artifacts import REQUIRED_ARTIFACTS as SHARED_REQUIRED_ARTIFACTS
from pyforestry.simulation.forcing import ForcingSet
from pyforestry.simulation.presets import RulesetFn
from pyforestry.simulation.presets import ScenarioConfig as _ScenarioConfig

__all__ = ["REQUIRED_ARTIFACTS", "ScenarioConfig"]

#: Norway emits the same three artifacts Sweden does, now that the same runner
#: writes both. It used to name two, one of them ``scenario_summary.json`` --
#: a file no writer produced, because Norway had no writer.
REQUIRED_ARTIFACTS = SHARED_REQUIRED_ARTIFACTS


@dataclass(frozen=True)
class ScenarioConfig(_ScenarioConfig):
    """Norway's scenario configuration.

    Declares the stage order and the rulesets; the seed derivation, guard flags,
    artifact accessor, identity and provenance are
    :class:`pyforestry.simulation.presets.ScenarioConfig`'s.

    This was ``NorwayScenarioPreset`` -- the rename that separated "configuration"
    (this) from "pipeline" (a simulator) reached Sweden and stopped there, so the
    two regions called one concept two things. Runs nothing; see the base class.
    """

    region: str = "Norway"
    required_artifacts_: tuple[str, ...] = REQUIRED_ARTIFACTS

    def stages(self) -> Sequence[str]:
        """Return the ordered stage identifiers for execution.

        Management, disturbance, growth, then valuation: thin the stand you
        have, take the scenario's losses off what remains, grow the survivors,
        and price what came out. The first two are exact no-ops unless the run
        configures a thinning schedule or a disturbance rate.

        The same period Sweden runs. It was ``("growth",)`` while nothing ran any
        of it, and then ``("management", "disturbance", "growth")`` while
        valuation could not work here: Norway's models are aggregate, and the
        removal ledger could only hold stems, so there was nothing for a
        valuation to price. It records bulk volume now.

        Norway ships no price list, so a run that reaches this stage must supply
        one -- see :func:`~pyforestry.norway.simulation.orchestration.run_norway_scenario`.
        """
        return ("management", "disturbance", "growth", "valuation")

    def rulesets(self) -> Mapping[str, RulesetFn]:
        """Return scenario rulesets keyed by concern."""
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
