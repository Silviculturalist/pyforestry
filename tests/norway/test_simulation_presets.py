"""Smoke tests for the Norway simulation preset contract."""

from __future__ import annotations

from pyforestry.norway.simulation.presets import build_baseline_preset
from pyforestry.norway.simulation.presets._common import (
    REQUIRED_ARTIFACTS,
    NorwayScenarioPreset,
)
from pyforestry.simulation.presets import ScenarioPresetBase


def test_baseline_preset_builds_and_conforms() -> None:
    """The baseline Norway preset is a ScenarioPresetBase with stable identity."""
    preset = build_baseline_preset()
    assert isinstance(preset, NorwayScenarioPreset)
    assert isinstance(preset, ScenarioPresetBase)
    assert preset.component_id == "norway_kuehne/baseline"
    assert preset.stages() == ("growth",)
    assert tuple(preset.required_artifacts()) == REQUIRED_ARTIFACTS
    assert preset.components == ()


def test_seed_strategy_is_deterministic() -> None:
    """Seed derivation is deterministic and global-seed sensitive."""
    preset = build_baseline_preset()
    seed_a = preset.seed_strategy(global_seed=7)
    seed_b = preset.seed_strategy(global_seed=7)
    seed_c = preset.seed_strategy(global_seed=8)
    assert seed_a == seed_b
    assert seed_a != seed_c
    assert isinstance(seed_a, int)


def test_guard_policy_and_rulesets() -> None:
    """Shared guard policy and bound rulesets are exposed as expected."""
    preset = build_baseline_preset()
    guard = preset.guard_policy()
    assert guard == {"clamp_net_volume_to_zero": True, "reject_negative_inputs": True}
    rulesets = preset.rulesets()
    assert set(rulesets) == {"management", "scenario"}
    assert all(callable(fn) for fn in rulesets.values())


def test_source_provenance() -> None:
    """A scenario preset declares that it has no bibliographic provenance.

    It is a configuration, not a publication, so it must not name an author or a
    year that a reader would take for a citation; the models it drives carry the
    science and their own references.
    """
    preset = build_baseline_preset()
    source = preset.source
    assert "Norway" in source.title
    assert source.author == "(none)"
    assert source.year == 0
    assert "not a publication" in source.note
