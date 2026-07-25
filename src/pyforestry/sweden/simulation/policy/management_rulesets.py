"""Management-side policy rulesets for Sweden simulation presets."""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

_MANAGEMENT_INTENSITY = {
    "baseline": 0.20,
}


def management_intensity(scenario_id: str) -> float:
    """Return harvest intensity for the selected scenario."""
    try:
        return float(_MANAGEMENT_INTENSITY[scenario_id])
    except KeyError as exc:
        raise ValueError(f"Unsupported scenario_id: {scenario_id!r}") from exc


def management_plan(scenario_id: str) -> Mapping[str, float]:
    """Return a small deterministic management-policy payload."""
    thinning_ratio = management_intensity(scenario_id)
    return MappingProxyType({"thinning_ratio": thinning_ratio})
