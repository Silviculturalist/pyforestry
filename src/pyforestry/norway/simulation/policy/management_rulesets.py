"""Management-side policy rulesets for Norway scenario configurations.

What is Norwegian here is the table. The accessors around it --
``supported_management_scenarios``, ``management_intensity``, ``management_plan``
-- are :class:`~pyforestry.simulation.policy.ManagementRuleset`'s, because they
were identical to Sweden's apart from this table and the label in the error a bad
scenario id raises.
"""

from __future__ import annotations

from pyforestry.simulation.policy import ManagementRuleset

__all__ = ["management_intensity", "management_plan", "supported_management_scenarios"]

#: Fraction of standing stems removed at a thinning, by scenario.
#:
#: These were ``{"baseline": 1.0, "intensive": 1.2, "extensive": 0.7}`` returned
#: under the key ``thinning_ratio`` -- so a run configured for "intensive" read as
#: thinning 120% of the stand. They were intensity *multipliers* on a base ratio
#: Norway never stated. The multipliers are kept and applied to Sweden's stated
#: base of 0.20, because there is no Norwegian base to apply them to; if a
#: Norwegian thinning guide gives one, it belongs here.
#: A scenario id names a *combination* -- a management intensity and a climate --
#: so every id has to appear in both this table and the scenario-factor table.
#:
#: These are management *choices*, not predictions: how hard the analyst thins is
#: a decision, and "intensive" and "extensive" describe it rather than asserting
#: a finding about the world. That is why they need no citation where a growth
#: multiplier does. What they do need is a base, and Norway states none -- so
#: Sweden's 0.20 stands in, and a Norwegian thinning guide replaces it.
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

_RULESET = ManagementRuleset(_THINNING_RATIO, what="Norway management")

#: Return the scenario ids this ruleset covers.
supported_management_scenarios = _RULESET.supported
#: Return the fraction of stems a thinning removes under a scenario.
#: Raises ``ValueError`` if the scenario id is unknown -- it used to return the
#: baseline plan for any unrecognised id, so a typo produced a full run under a
#: scenario nobody chose.
management_intensity = _RULESET.lookup
#: Return the :class:`~pyforestry.simulation.policy.ManagementPlan` for a scenario.
#: Raises ``ValueError`` if the scenario id is unknown.
management_plan = _RULESET.plan
