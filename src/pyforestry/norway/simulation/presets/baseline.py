"""Baseline Norway preset using Kuehne (2022) pine trajectory model."""

from __future__ import annotations

from ._common import NorwayScenarioPreset


def build_baseline_scenario_config() -> NorwayScenarioPreset:
    """Return a baseline Norway scenario preset for Kuehne pine trajectories."""
    return NorwayScenarioPreset(
        preset_id="norway_kuehne",
        scenario_id="baseline",
    )
