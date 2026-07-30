"""Sweden's scenario ruleset: which scenarios it covers, and what they force.

Norway's twin has these tests; Sweden's had only its happy path, so the refusal
of an unknown id -- the branch that keeps an unshipped scenario from silently
running as the baseline -- was never exercised.
"""

from __future__ import annotations

import pytest

from pyforestry.simulation.forcing import ForcingSet
from pyforestry.sweden.simulation.policy.scenario_rulesets import (
    scenario_forcings,
    supported_scenarios,
)


def test_the_baseline_is_the_only_scenario_shipped() -> None:
    assert supported_scenarios() == ("baseline",)


def test_no_shipped_scenario_forces_anything() -> None:
    """The mechanism exists; what it must not do is arrive preloaded.

    A forcing is a claim about the world, and this package ships none for Sweden
    -- a growth or price multiplier with no publication behind it would read as a
    finding nobody has made.
    """
    for scenario_id in supported_scenarios():
        assert scenario_forcings(scenario_id) == ForcingSet(), scenario_id


def test_an_unknown_scenario_is_refused_rather_than_treated_as_the_baseline() -> None:
    """Silently returning an empty set would run a storm scenario as fair weather."""
    with pytest.raises(ValueError, match="Unsupported scenario_id"):
        scenario_forcings("climate_rcp45")
    with pytest.raises(ValueError, match="Unsupported scenario_id"):
        scenario_forcings("")
