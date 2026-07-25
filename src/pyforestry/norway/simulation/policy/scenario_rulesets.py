"""Scenario factor rulesets for Norwegian scenario presets."""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

_SCENARIO_FACTORS: dict[str, dict[str, float]] = {
    "baseline": {"growth_factor": 1.0, "disturbance_factor": 1.0},
    "climate_rcp45": {"growth_factor": 1.05, "disturbance_factor": 1.2},
}


def scenario_factors(scenario_id: str) -> Mapping[str, float]:
    """Return growth and disturbance multipliers for the given scenario.

    Args:
        scenario_id: Scenario identifier (e.g. 'baseline').

    Returns:
        Immutable mapping of scenario factors.
    """
    factors = _SCENARIO_FACTORS.get(scenario_id, _SCENARIO_FACTORS["baseline"])
    return MappingProxyType(dict(factors))
