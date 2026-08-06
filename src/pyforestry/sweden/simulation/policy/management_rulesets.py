"""Management-side policy rulesets for Sweden scenario configurations.

What is Swedish here is the table. The accessors around it --
``supported_management_scenarios``, ``management_intensity``, ``management_plan``
-- are :class:`~pyforestry.simulation.policy.ManagementRuleset`'s, because they
were identical to Norway's apart from this table and the label in the error a bad
scenario id raises.
"""

from __future__ import annotations

from pyforestry.simulation.policy import ManagementRuleset

__all__ = ["management_intensity", "management_plan", "supported_management_scenarios"]

#: Fraction of standing stems removed at a thinning, by scenario.
_THINNING_RATIO: dict[str, float] = {
    "baseline": 0.20,
}

_RULESET = ManagementRuleset(_THINNING_RATIO, what="Sweden management")

#: Return the scenario ids this ruleset covers.
supported_management_scenarios = _RULESET.supported
#: Return the fraction of stems a thinning removes under a scenario.
#: Raises ``ValueError`` if the scenario id is unknown.
management_intensity = _RULESET.lookup
#: Return the :class:`~pyforestry.simulation.policy.ManagementPlan` for a scenario.
#: Raises ``ValueError`` if the scenario id is unknown.
management_plan = _RULESET.plan
