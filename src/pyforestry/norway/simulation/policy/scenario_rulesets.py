"""Scenario forcings for Norway configurations: none, by design.

A forcing is an external factor imposed on a projection -- a weather correction,
a disturbance rate, a price index -- and every one is a claim about the world.
This package has no basis for such a number in Norway, so it ships none, and
:class:`~pyforestry.simulation.forcing.ConstantForcing` refuses to be built with
a non-neutral value and no source.

There was a ``climate_rcp45`` entry here carrying ``{growth 1.05, disturbance
1.2}``. It arrived in this package's first commit with no source anywhere, and
the name asserts one: RCP4.5 is a specific IPCC Representative Concentration
Pathway, so a scenario called that reads as "these are the multipliers RCP4.5
implies for Norwegian Scots pine". They were placeholders. Sweden had already
deleted a ``storm_risk_high`` for exactly this.

A caller supplies forcings to :func:`~pyforestry.simulation.scenario.run_scenario`
directly, and they are recorded in the run manifest with their citations. When a
Norwegian climate or damage series has a paper behind it, it belongs here.
"""

from __future__ import annotations

from pyforestry.simulation.forcing import ForcingSet
from pyforestry.simulation.policy import lookup_scenario

__all__ = ["scenario_forcings", "supported_scenarios"]

#: Every scenario this region defines, and the forcings it carries. All empty:
#: the scenarios differ in their management, not in anything imposed from outside.
_SCENARIO_FORCINGS: dict[str, ForcingSet] = {
    "baseline": ForcingSet(),
    "intensive": ForcingSet(),
    "extensive": ForcingSet(),
}


def supported_scenarios() -> tuple[str, ...]:
    """Return scenario ids this ruleset covers."""
    return tuple(sorted(_SCENARIO_FORCINGS))


def scenario_forcings(scenario_id: str) -> ForcingSet:
    """Return the forcings this scenario declares.

    Raises:
        ValueError: If the scenario id is unknown. It used to fall back to the
            baseline, so a typo produced a full run of baseline numbers labelled
            with the scenario that was asked for.
    """
    return lookup_scenario(_SCENARIO_FORCINGS, scenario_id, what="Norway scenario forcings")
