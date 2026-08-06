"""Scenario forcings for Sweden configurations: none, by design.

A forcing is an external factor imposed on a projection -- a weather correction,
a disturbance rate, a price index -- and every one is a claim about the world.
This package has no basis for such a number, so it ships none; a caller supplies
them to :func:`~pyforestry.simulation.scenario.run_scenario` and they are
recorded in the run manifest with their citations.

A ``storm_risk_high`` scenario was deleted from here for carrying growth and
disturbance multipliers that were invented, with no source behind them.
:mod:`pyforestry.simulation.forcing` now enforces what that removal established.
"""

from __future__ import annotations

from pyforestry.simulation.forcing import ForcingSet
from pyforestry.simulation.policy import ScenarioTable

__all__ = ["scenario_forcings", "supported_scenarios"]

_SCENARIO_FORCINGS: dict[str, ForcingSet] = {
    "baseline": ForcingSet(),
}

_RULESET: ScenarioTable[ForcingSet] = ScenarioTable(
    _SCENARIO_FORCINGS, what="Sweden scenario forcings"
)

#: Return the scenario ids this ruleset covers.
supported_scenarios = _RULESET.supported
#: Return the forcings a scenario declares.
#: Raises ``ValueError`` if the scenario id is unknown -- it used to fall back to
#: the baseline, so a typo produced a full run of baseline numbers labelled with
#: the scenario that was asked for.
scenario_forcings = _RULESET.lookup
