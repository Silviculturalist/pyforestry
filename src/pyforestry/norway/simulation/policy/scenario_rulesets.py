"""Scenario-factor rulesets for Norway scenario configurations."""

from __future__ import annotations

from pyforestry.simulation.policy import ScenarioFactors, lookup_scenario

__all__ = ["scenario_factors", "supported_scenarios"]

#: Scenario overlays applied on top of the published models. Both default to 1.0,
#: which is an exact no-op; see :class:`~pyforestry.simulation.policy.ScenarioFactors`.
_SCENARIO_FACTORS: dict[str, ScenarioFactors] = {
    "baseline": ScenarioFactors(growth_factor=1.0, disturbance_factor=1.0),
    "climate_rcp45": ScenarioFactors(growth_factor=1.05, disturbance_factor=1.2),
}


def supported_scenarios() -> tuple[str, ...]:
    """Return scenario ids this ruleset covers."""
    return tuple(sorted(_SCENARIO_FACTORS))


def scenario_factors(scenario_id: str) -> ScenarioFactors:
    """Return the growth and disturbance overlays for the selected scenario.

    Raises:
        ValueError: If the scenario id is unknown. It used to fall back to the
            baseline factors, so a typo produced a full run of baseline numbers
            labelled with the scenario that was asked for.
    """
    return lookup_scenario(_SCENARIO_FACTORS, scenario_id, what="Norway scenario factors")
