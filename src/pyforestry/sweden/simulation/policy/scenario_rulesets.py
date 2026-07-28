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
from pyforestry.simulation.policy import lookup_scenario

__all__ = ["scenario_forcings", "supported_scenarios"]

_SCENARIO_FORCINGS: dict[str, ForcingSet] = {
    "baseline": ForcingSet(),
}


def supported_scenarios() -> tuple[str, ...]:
    """Return scenario ids this ruleset covers."""
    return tuple(sorted(_SCENARIO_FORCINGS))


def scenario_forcings(scenario_id: str) -> ForcingSet:
    """Return the forcings this scenario declares.

    Raises:
        ValueError: If the scenario id is unknown.
    """
    return lookup_scenario(_SCENARIO_FORCINGS, scenario_id, what="Sweden scenario forcings")
