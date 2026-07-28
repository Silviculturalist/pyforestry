"""Management-side policy rulesets for Sweden scenario configurations."""

from __future__ import annotations

from pyforestry.simulation.policy import ManagementPlan, lookup_scenario

__all__ = ["management_intensity", "management_plan", "supported_management_scenarios"]

#: Fraction of standing stems removed at a thinning, by scenario.
_THINNING_RATIO: dict[str, float] = {
    "baseline": 0.20,
}


def supported_management_scenarios() -> tuple[str, ...]:
    """Return the scenario ids this ruleset covers."""
    return tuple(sorted(_THINNING_RATIO))


def management_intensity(scenario_id: str) -> float:
    """Return the fraction of stems a thinning removes under this scenario.

    Raises:
        ValueError: If the scenario id is unknown.
    """
    return float(lookup_scenario(_THINNING_RATIO, scenario_id, what="Sweden management"))


def management_plan(scenario_id: str) -> ManagementPlan:
    """Return the management plan for the given scenario.

    Raises:
        ValueError: If the scenario id is unknown.
    """
    return ManagementPlan(thinning_ratio=management_intensity(scenario_id))
