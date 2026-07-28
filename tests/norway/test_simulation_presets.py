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

from pyforestry.base.contracts import SourceReference
from pyforestry.norway.simulation.orchestration import (
    build_kuehne_stands,
    kuehne_stand_volume,
    run_norway_scenario,
)
from pyforestry.norway.simulation.policy import (
    management_intensity,
    scenario_forcings,
    supported_scenarios,
)
from pyforestry.norway.simulation.presets import ScenarioConfig, build_baseline_scenario_config
from pyforestry.norway.simulation.presets._common import REQUIRED_ARTIFACTS
from pyforestry.simulation.artifacts import load_scenario_summary, validate_artifact_contract
from pyforestry.simulation.forcing import (
    DISTURBANCE,
    GROWTH,
    AnnualForcing,
    ConstantForcing,
    ForcingSet,
)
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
    assert set(config.rulesets()) == {"management"}
    assert config.forcings() == ForcingSet(), "this package ships no forcings"


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


def test_the_fabricated_climate_scenario_does_not_resolve() -> None:
    """``climate_rcp45`` is gone, like Sweden's ``storm_risk_high`` before it.

    It carried ``{growth 1.05, disturbance 1.2}`` from this package's first
    commit with no source anywhere, under a name that asserts one -- RCP4.5 is a
    specific IPCC pathway, so the scenario read as a finding about Norwegian
    Scots pine that nobody had made.
    """
    with pytest.raises(ValueError, match="Unsupported scenario_id"):
        management_intensity("climate_rcp45")
    with pytest.raises(ValueError, match="Unsupported scenario_id"):
        scenario_forcings("climate_rcp45")


def test_no_shipped_scenario_forces_anything() -> None:
    """The mechanism exists and is exercised below; what it must not do is arrive
    preloaded with numbers that have no paper behind them.
    """
    for scenario_id in supported_scenarios():
        assert scenario_forcings(scenario_id) == ForcingSet(), scenario_id


def test_a_cited_forcing_raises_growth_and_disturbance(tmp_path) -> None:
    """The forcing mechanism works -- for values that say where they come from."""
    source = SourceReference(
        author="Test fixture",
        year=2026,
        title="Forcings invented by this test, and saying so",
    )
    forcings = ForcingSet(
        [
            ConstantForcing(GROWTH, 1.05, source=source),
            ConstantForcing(DISTURBANCE, 1.2, source=source),
        ]
    )

    baseline = run_norway_scenario(
        global_seed=1,
        output_dir=tmp_path / "base",
        n_stands=1,
        n_steps=6,
        start_year=2020,
        disturbance_rate_per_year=0.004,
    )
    forced = run_norway_scenario(
        global_seed=1,
        output_dir=tmp_path / "forced",
        n_stands=1,
        n_steps=6,
        start_year=2020,
        disturbance_rate_per_year=0.004,
        forcings=forcings,
    )

    assert forced.rows[0]["gross_growth_m3"] > baseline.rows[0]["gross_growth_m3"]
    assert forced.rows[0]["disturbance_loss_m3"] > baseline.rows[0]["disturbance_loss_m3"]

    manifest = json.loads(forced.artifacts.run_manifest_path.read_text(encoding="utf-8"))
    applied = {entry["name"]: entry for entry in manifest["forcings_applied"]}
    assert applied[GROWTH]["value"] == 1.05
    # The citation travels with the number into the manifest, which is the point.
    assert applied[GROWTH]["source"]["year"] == 2026


def test_a_year_by_year_forcing_varies_across_the_run(tmp_path) -> None:
    """A weather correction is a series, not one number for the projection."""
    source = SourceReference(author="Test fixture", year=2026, title="A series, and saying so")
    weather = AnnualForcing(
        GROWTH,
        {2020: 1.04, 2025: 1.02, 2030: 0.98, 2035: 0.67},
        outside_series="hold",
        source=source,
    )

    flat = run_norway_scenario(
        global_seed=1,
        output_dir=tmp_path / "flat",
        n_stands=1,
        n_steps=4,
        start_year=2020,
        forcings=ForcingSet([ConstantForcing(GROWTH, 1.04, source=source)]),
    )
    varying = run_norway_scenario(
        global_seed=1,
        output_dir=tmp_path / "varying",
        n_stands=1,
        n_steps=4,
        start_year=2020,
        forcings=ForcingSet([weather]),
    )

    # Same first period, different afterwards: the series is read per period.
    assert varying.rows[0]["gross_growth_m3"] != flat.rows[0]["gross_growth_m3"]

    manifest = json.loads(varying.artifacts.run_manifest_path.read_text(encoding="utf-8"))
    entry = manifest["forcings_applied"][0]
    assert entry["resolution"] == "annual"
    assert entry["series"]["2035"] == 0.67
    assert manifest["start_year"] == 2020.0


def test_an_uncited_forcing_is_refused() -> None:
    """A value that changes a published model must say where it comes from."""
    with pytest.raises(ValueError, match="where it comes from"):
        ConstantForcing(GROWTH, 1.05)


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
