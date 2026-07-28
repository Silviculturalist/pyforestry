"""Management-side policy rulesets for Norway scenario configurations."""

from __future__ import annotations

from pyforestry.simulation.policy import ManagementPlan, lookup_scenario

__all__ = ["management_intensity", "management_plan", "supported_management_scenarios"]

#: Fraction of standing stems removed at a thinning, by scenario.
#:
#: These were ``{"baseline": 1.0, "intensive": 1.2, "extensive": 0.7}`` returned
#: under the key ``thinning_ratio`` -- so a run configured for "intensive" read as
#: thinning 120% of the stand. They were intensity *multipliers* on a base ratio
#: Norway never stated. The multipliers are kept and applied to Sweden's stated
#: base of 0.20, because there is no Norwegian base to apply them to; if a
#: Norwegian thinning guide gives one, it belongs here.
_BASE_THINNING_RATIO = 0.20
_INTENSITY_MULTIPLIER: dict[str, float] = {
    "baseline": 1.0,
    "intensive": 1.2,
    "extensive": 0.7,
}

_THINNING_RATIO: dict[str, float] = {
    scenario: _BASE_THINNING_RATIO * multiplier
    for scenario, multiplier in _INTENSITY_MULTIPLIER.items()
}


def supported_management_scenarios() -> tuple[str, ...]:
    """Return the scenario ids this ruleset covers."""
    return tuple(sorted(_THINNING_RATIO))


def management_intensity(scenario_id: str) -> float:
    """Return the fraction of stems a thinning removes under this scenario.

    Raises:
        ValueError: If the scenario id is unknown.
    """
    return float(lookup_scenario(_THINNING_RATIO, scenario_id, what="Norway management"))


def management_plan(scenario_id: str) -> ManagementPlan:
    """Return the management plan for the given scenario.

    Raises:
        ValueError: If the scenario id is unknown. It used to return the baseline
            plan for any unrecognised id, so a typo produced a full run under a
            scenario nobody chose.
    """
    return ManagementPlan(thinning_ratio=management_intensity(scenario_id))
