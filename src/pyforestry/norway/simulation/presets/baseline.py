"""Baseline Norway scenario configuration for Kuehne (2022) pine trajectories."""

from __future__ import annotations

from ._common import ScenarioConfig


def build_baseline_scenario_config() -> ScenarioConfig:
    """Return the baseline Norway scenario configuration."""
    return ScenarioConfig(
        preset_id="norway_kuehne",
        scenario_id="baseline",
    )
