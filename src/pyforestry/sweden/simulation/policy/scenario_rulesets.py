"""Scenario-specific policy rulesets for Sweden simulation presets."""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

_SCENARIO_FACTORS = {
    "baseline": {
        "growth_factor": 1.0,
        "disturbance_factor": 1.0,
    },
}


def supported_scenarios() -> tuple[str, ...]:
    """Return scenario ids supported by the preset package."""
    return tuple(_SCENARIO_FACTORS)


def scenario_factors(scenario_id: str) -> Mapping[str, float]:
    """Return growth/disturbance multipliers for the selected scenario."""
    try:
        factors = _SCENARIO_FACTORS[scenario_id]
    except KeyError as exc:
        raise ValueError(f"Unsupported scenario_id: {scenario_id!r}") from exc
    return MappingProxyType(dict(factors))
