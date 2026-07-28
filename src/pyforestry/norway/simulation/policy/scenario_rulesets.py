"""Scenario-factor rulesets for Norway scenario configurations."""

from __future__ import annotations

from pyforestry.simulation.policy import ScenarioFactors, lookup_scenario

__all__ = ["scenario_factors", "supported_scenarios"]

#: Scenario overlays applied on top of the published models. Every entry here is
#: neutral -- growth and disturbance factors of 1.0, which leave the models'
#: own predictions untouched.
#:
#: There was a ``climate_rcp45`` entry carrying ``{growth 1.05, disturbance 1.2}``.
#: It arrived in this package's first commit with no source, anywhere, and the
#: name asserts one: RCP4.5 is a specific IPCC Representative Concentration
#: Pathway, so a scenario called that reads as "these are the multipliers RCP4.5
#: implies for Norwegian Scots pine". They were placeholders. Sweden had already
#: deleted a ``storm_risk_high`` for exactly this, and the rule is now enforced
#: rather than remembered: :class:`~pyforestry.simulation.policy.ScenarioFactors`
#: refuses a non-neutral overlay without a SourceReference.
#:
#: A real climate scenario belongs here as soon as its factors have a paper
#: behind them. Until then the runtime carries the mechanism and no claim.
_SCENARIO_FACTORS: dict[str, ScenarioFactors] = {
    "baseline": ScenarioFactors(),
    "intensive": ScenarioFactors(),
    "extensive": ScenarioFactors(),
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
