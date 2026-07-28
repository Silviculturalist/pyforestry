"""Norway's scenario tier: a configuration, and a runtime that executes it.

Norway had the configuration, the rulesets and the preset, and nothing that ran
any of them -- the whole tier was a mirror of Sweden's scaffolding added in the
same initial commit, before either region had a runtime. Its four published
models were reachable through ``pyforestry.project`` all along; what was missing
was the scenario runtime around them. These tests cover both halves.
"""

from __future__ import annotations

import json

import pytest

from pyforestry.norway.simulation.orchestration import (
    build_kuehne_stands,
    kuehne_stand_volume,
    run_norway_scenario,
)
from pyforestry.norway.simulation.presets import ScenarioConfig, build_baseline_scenario_config
from pyforestry.norway.simulation.presets._common import REQUIRED_ARTIFACTS
from pyforestry.simulation.artifacts import load_scenario_summary, validate_artifact_contract
from pyforestry.simulation.presets import ScenarioConfig as SharedScenarioConfig

# --- the configuration -------------------------------------------------------


def test_baseline_configuration_conforms_and_has_a_stable_identity() -> None:
    config = build_baseline_scenario_config()
    assert isinstance(config, ScenarioConfig)
    assert isinstance(config, SharedScenarioConfig)
    assert config.component_id == "norway_kuehne/baseline"
    assert tuple(config.required_artifacts()) == REQUIRED_ARTIFACTS
    assert config.components == ()


def test_stages_are_the_period_the_runtime_executes() -> None:
    """``("growth",)`` was not Norway having nothing else to run."""
    assert build_baseline_scenario_config().stages() == (
        "management",
        "disturbance",
        "growth",
    )


def test_seed_strategy_is_deterministic_and_global_seed_sensitive() -> None:
    config = build_baseline_scenario_config()
    assert config.seed_strategy(global_seed=7) == config.seed_strategy(global_seed=7)
    assert config.seed_strategy(global_seed=7) != config.seed_strategy(global_seed=8)


def test_guard_policy_and_rulesets_are_exposed() -> None:
    config = build_baseline_scenario_config()
    assert config.guard_policy() == {
        "clamp_net_volume_to_zero": True,
        "reject_negative_inputs": True,
    }
    assert set(config.rulesets()) == {"management", "scenario"}


def test_source_declares_that_it_is_not_a_publication() -> None:
    """A configuration must not name an author a reader would take for a citation."""
    source = build_baseline_scenario_config().source
    assert "Norway" in source.title
    assert source.author == "(none)"
    assert source.year == 0
    assert "not a publication" in source.note


# --- the runtime -------------------------------------------------------------


def test_baseline_run_projects_real_kuehne_stands(tmp_path) -> None:
    result = run_norway_scenario(
        global_seed=20260728, output_dir=tmp_path / "run", n_stands=2, n_steps=6
    )

    validate_artifact_contract(result.artifacts.output_dir)
    row = result.rows[0]
    assert row["initial_volume_m3"] > 0.0
    assert row["gross_growth_m3"] > 0.0
    assert row["net_volume_m3"] > row["initial_volume_m3"]

    manifest = json.loads(result.artifacts.run_manifest_path.read_text(encoding="utf-8"))
    assert manifest["region"] == "Norway"
    assert "synthetic" not in manifest
    assert [entry["component_id"] for entry in manifest["models_run"]] == ["kuehne_2022_pine"]
    assert manifest["models_run"][0]["year"] == 2022


def test_thinning_and_disturbance_are_reported_apart(tmp_path) -> None:
    thinned = run_norway_scenario(
        global_seed=1,
        output_dir=tmp_path / "thin",
        n_stands=1,
        n_steps=6,
        thin_at_years=[60.0],
    )
    disturbed = run_norway_scenario(
        global_seed=1,
        output_dir=tmp_path / "dist",
        n_stands=1,
        n_steps=6,
        disturbance_rate_per_year=0.004,
    )

    assert thinned.rows[0]["harvested_m3"] > 0.0
    assert thinned.rows[0]["disturbance_loss_m3"] == pytest.approx(0.0)
    assert disturbed.rows[0]["disturbance_loss_m3"] > 0.0
    assert disturbed.rows[0]["harvested_m3"] == pytest.approx(0.0)


def test_the_climate_scenario_raises_growth_and_disturbance(tmp_path) -> None:
    """``climate_rcp45`` is a real scenario the runtime applies, not a table entry.

    It was configured in the scenario-factor table and absent from the management
    table, so building it raised the moment anything resolved rulesets for real.
    """
    baseline = run_norway_scenario(
        global_seed=1,
        output_dir=tmp_path / "base",
        n_stands=1,
        n_steps=6,
        disturbance_rate_per_year=0.004,
    )
    rcp = run_norway_scenario(
        global_seed=1,
        output_dir=tmp_path / "rcp",
        n_stands=1,
        n_steps=6,
        disturbance_rate_per_year=0.004,
        config=ScenarioConfig(preset_id="norway_kuehne", scenario_id="climate_rcp45"),
    )

    assert rcp.rows[0]["gross_growth_m3"] > baseline.rows[0]["gross_growth_m3"]
    assert rcp.rows[0]["disturbance_loss_m3"] > baseline.rows[0]["disturbance_loss_m3"]

    manifest = json.loads(rcp.artifacts.run_manifest_path.read_text(encoding="utf-8"))
    assert manifest["rulesets_applied"]["scenario"] == {
        "growth_factor": 1.05,
        "disturbance_factor": 1.2,
    }


def test_the_volume_reporter_is_a_function_of_the_current_stand(tmp_path) -> None:
    """Not the value the model cached at its last step, which a thinning leaves stale."""
    result = run_norway_scenario(global_seed=1, output_dir=tmp_path / "run", n_stands=1, n_steps=2)
    ctx = result.contexts[0]
    before = kuehne_stand_volume(ctx)
    ctx.scale_stems(0.5)
    assert kuehne_stand_volume(ctx) < before


def test_summary_is_loadable_and_keyed_by_stand(tmp_path) -> None:
    result = run_norway_scenario(
        global_seed=20260728, output_dir=tmp_path / "run", n_stands=3, n_steps=2
    )
    rows = load_scenario_summary(result.artifacts.scenario_summary_path)
    assert [row["stand_id"] for row in rows] == [1, 2, 3]


def test_build_kuehne_stands_rejects_an_empty_run() -> None:
    with pytest.raises(ValueError, match="n_stands must be > 0"):
        build_kuehne_stands(0)
