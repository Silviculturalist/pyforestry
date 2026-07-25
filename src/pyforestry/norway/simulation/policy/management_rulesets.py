"""Management rulesets for Norwegian scenario presets."""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

_MANAGEMENT_INTENSITY: dict[str, float] = {
    "baseline": 1.0,
    "intensive": 1.2,
    "extensive": 0.7,
}


def management_plan(scenario_id: str) -> Mapping[str, float]:
    """Return management parameters for the given scenario.

    Args:
        scenario_id: Scenario identifier (e.g. 'baseline').

    Returns:
        Immutable mapping of management parameters.
    """
    thinning_ratio = _MANAGEMENT_INTENSITY.get(scenario_id, 1.0)
    return MappingProxyType({"thinning_ratio": thinning_ratio})
