"""Sweden simulation presets."""

from ._common import SwedenScenarioPreset
from .baseline import build_baseline_preset
from .elfving_2010_composite import (
    Elfving2010CompositePreset,
    Elfving2010CompositePresetConfig,
    build_elfving_2010_composite_preset,
)
from .soderberg_1986_composite import (
    Soderberg1986CompositePreset,
    Soderberg1986CompositePresetConfig,
    build_soderberg_1986_composite_preset,
)


def get_preset(scenario_id: str) -> SwedenScenarioPreset:
    """Build a preset for a supported scenario id."""
    if scenario_id == "baseline":
        return build_baseline_preset()
    raise ValueError(f"Unsupported scenario_id: {scenario_id!r}")


__all__ = [
    "SwedenScenarioPreset",
    "build_baseline_preset",
    "Elfving2010CompositePresetConfig",
    "Elfving2010CompositePreset",
    "build_elfving_2010_composite_preset",
    "Soderberg1986CompositePresetConfig",
    "Soderberg1986CompositePreset",
    "build_soderberg_1986_composite_preset",
    "get_preset",
]
