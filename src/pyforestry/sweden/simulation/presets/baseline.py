"""Baseline Sweden scenario configuration."""

from __future__ import annotations

from pyforestry.sweden.simulation.data import REQUIRED_ARTIFACTS
from pyforestry.sweden.simulation.presets._common import ScenarioConfig


def build_baseline_scenario_config() -> ScenarioConfig:
    """Build the baseline scenario configuration."""
    return ScenarioConfig(
        preset_id="sweden_minimal",
        scenario_id="baseline",
        required_artifacts_=REQUIRED_ARTIFACTS,
    )
