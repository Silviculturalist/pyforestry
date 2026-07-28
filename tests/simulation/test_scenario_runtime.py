"""A scenario configuration is executed, not merely recorded.

``ScenarioConfig`` declared a seed strategy, an ordered list of stage names,
rulesets and a guard policy, and nothing ran any of them: the only consumer
filled the artifacts with a seeded random walk and stamped every file
``synthetic: true``. These tests assert that all four are now executed, and that
the manifest says truthfully how the run was constructed -- which is the reason
the artifacts exist.
"""

from __future__ import annotations

import json

import pytest

from pyforestry.base.contracts import SourceReference
from pyforestry.base.helpers.primitives import StandBasalArea, Stems
from pyforestry.base.helpers.stand import Stand
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.base.simulation.core import SimulationContext
from pyforestry.base.simulation.growth_model import GrowthModel, Requirements
from pyforestry.simulation.artifacts import (
    MANIFEST_REQUIRED_KEYS,
    QUALITY_REPORT_REQUIRED_KEYS,
    REQUIRED_ARTIFACTS,
    SCENARIO_SUMMARY_COLUMNS,
    check_volume_balance,
    load_scenario_summary,
    validate_artifact_contract,
)
from pyforestry.simulation.policy import ManagementPlan, ScenarioFactors
from pyforestry.simulation.presets import ScenarioConfig
from pyforestry.simulation.scenario import StandUnit, run_scenario
from pyforestry.simulation.stages import StageContext, build_pipeline, known_stages

SPECIES = TreeSpecies.Sweden.picea_abies


class _DoublingModel(GrowthModel):
    """Adds a fixed basal-area increment per year, and reports a volume for it.

    Not science: a model whose arithmetic is obvious by inspection, so a test can
    say what the run's numbers must be.
    """

    VOLUME_PER_BA = 10.0
    BA_PER_YEAR = 0.5

    @property
    def component_id(self) -> str:
        return "test_doubling_model"

    @property
    def source(self) -> SourceReference:
        return SourceReference(author="(none)", year=0, title="Test fixture, not a model")

    def requirements(self) -> Requirements:
        return Requirements(inventory="aggregate", native_step_years=5.0)

    def update_step(self, ctx: SimulationContext, dt: float) -> None:
        ba = float(ctx.metrics["BasalArea"]["TOTAL"]) + self.BA_PER_YEAR * dt
        stems = float(ctx.metrics["Stems"]["TOTAL"])
        ctx.set_aggregate_metrics(ba_total=ba, stems_total=stems)


def _volume(ctx: SimulationContext) -> float:
    """Volume as a fixed multiple of the *current* basal area."""
    return float(ctx.metrics["BasalArea"]["TOTAL"]) * _DoublingModel.VOLUME_PER_BA


class _Config(ScenarioConfig):
    """A configuration whose stages and rulesets the test controls."""

    def stages(self):
        return ("management", "disturbance", "growth")

    def rulesets(self):
        return {
            "management": lambda: ManagementPlan(thinning_ratio=0.25),
            "scenario": lambda: ScenarioFactors(growth_factor=1.0, disturbance_factor=1.0),
        }


def _config(**kwargs) -> _Config:
    base = {
        "preset_id": "test",
        "scenario_id": "baseline",
        "region": "Testland",
        "required_artifacts_": REQUIRED_ARTIFACTS,
    }
    base.update(kwargs)
    return _Config(**base)


def _stands(n: int, *, ba: float = 20.0, stems: float = 1000.0) -> list[StandUnit]:
    return [
        StandUnit(
            stand_id=i,
            stand=Stand.from_aggregate_metrics(
                {
                    "BasalArea": {"TOTAL": StandBasalArea(ba, species=SPECIES)},
                    "Stems": {"TOTAL": Stems(stems, species=SPECIES)},
                },
                area_ha=1.0,
            ),
        )
        for i in range(1, n + 1)
    ]


def _run(tmp_path, **kwargs):
    params = {
        "build_model": _DoublingModel,
        "stands": _stands(2),
        "volume": _volume,
        "global_seed": 20260728,
        "n_steps": 4,
        "step_years": 5.0,
        "output_dir": tmp_path / "run",
    }
    config = params.pop("config", None) or kwargs.pop("config", None) or _config()
    params.update(kwargs)
    return run_scenario(config, **params)


# --- the stages actually run -------------------------------------------------


def test_growth_runs_and_produces_the_model_s_numbers(tmp_path) -> None:
    """No random walk: the summary is the model's arithmetic."""
    result = _run(tmp_path)
    row = result.rows[0]
    # 20 m2/ha + 0.5 per year over 20 years = 30 m2/ha, at 10 m3 per m2.
    assert row["initial_volume_m3"] == pytest.approx(200.0)
    assert row["net_volume_m3"] == pytest.approx(300.0)
    assert row["gross_growth_m3"] == pytest.approx(100.0)


def test_management_stage_thins_and_is_reported_apart_from_growth(tmp_path) -> None:
    result = _run(tmp_path, thin_at_years=[10.0])
    row = result.rows[0]
    assert row["harvested_m3"] > 0.0
    assert row["disturbance_loss_m3"] == pytest.approx(0.0)
    assert row["net_volume_m3"] < 300.0


def test_disturbance_stage_removes_and_is_reported_apart_from_harvest(tmp_path) -> None:
    result = _run(tmp_path, disturbance_rate_per_year=0.01)
    row = result.rows[0]
    assert row["disturbance_loss_m3"] > 0.0
    assert row["harvested_m3"] == pytest.approx(0.0)


def test_scenario_growth_factor_scales_the_increment(tmp_path) -> None:
    """The overlay is applied, and only to the increment."""

    class _Warmer(_Config):
        def rulesets(self):
            return {
                "management": lambda: ManagementPlan(thinning_ratio=0.25),
                "scenario": lambda: ScenarioFactors(growth_factor=1.5),
            }

    baseline = _run(tmp_path / "a", config=_config())
    warmer = _run(tmp_path / "b", config=_Warmer(**_config().__dict__))

    assert warmer.rows[0]["gross_growth_m3"] == pytest.approx(
        baseline.rows[0]["gross_growth_m3"] * 1.5
    )
    assert warmer.rows[0]["initial_volume_m3"] == baseline.rows[0]["initial_volume_m3"]


def test_growth_factor_refuses_a_representation_it_cannot_scale() -> None:
    """Scaling 'the increment' is only defined for aggregate metrics."""
    from pyforestry.base.helpers.plot import CircularPlot
    from pyforestry.base.helpers.tree import Tree
    from pyforestry.base.simulation.growth_model import ExampleStandGeneralModel
    from pyforestry.simulation.stages import ScenarioGrowthStep

    stand = Stand(
        area_ha=1.0,
        plots=[
            CircularPlot(
                id=1,
                area_m2=10_000.0,
                trees=[Tree(species=SPECIES, diameter_cm=20.0, height_m=15.0, weight_n=1.0)],
            )
        ],
    )
    ctx = ExampleStandGeneralModel().build_context(stand, mode_hint="tree_list")
    with pytest.raises(ValueError, match="growth_factor"):
        ScenarioGrowthStep(growth_factor=1.2).run(ctx, 5.0)


# --- the manifest says how the run was constructed ---------------------------


def test_manifest_records_the_construction(tmp_path) -> None:
    """The artifact's reason to exist: reading a run back without rerunning it."""
    result = _run(tmp_path, thin_at_years=[10.0], disturbance_rate_per_year=0.02)
    manifest = json.loads(result.artifacts.run_manifest_path.read_text(encoding="utf-8"))

    for key in MANIFEST_REQUIRED_KEYS:
        assert key in manifest, key

    assert manifest["stages"] == ["management", "disturbance", "growth"]
    assert manifest["rulesets_applied"]["management"] == {"thinning_ratio": 0.25}
    assert manifest["rulesets_applied"]["scenario"]["growth_factor"] == 1.0
    assert manifest["guard_policy"]["clamp_net_volume_to_zero"] is True
    assert manifest["thin_at_years"] == [10.0]
    assert manifest["disturbance_rate_per_year"] == pytest.approx(0.02)
    assert manifest["scenario_seed"] != manifest["global_seed"]
    assert "synthetic" not in manifest, "nothing here is synthetic any more"


def test_manifest_carries_the_citation_of_every_model_that_ran(tmp_path) -> None:
    result = _run(tmp_path)
    manifest = json.loads(result.artifacts.run_manifest_path.read_text(encoding="utf-8"))
    ids = {entry["component_id"] for entry in manifest["models_run"]}
    assert ids == {"test_doubling_model"}
    assert all("author" in entry and "year" in entry for entry in manifest["models_run"])


def test_quality_report_and_contract(tmp_path) -> None:
    result = _run(tmp_path)
    validate_artifact_contract(result.artifacts.output_dir)
    quality = json.loads(result.artifacts.quality_report_path.read_text(encoding="utf-8"))
    for key in QUALITY_REPORT_REQUIRED_KEYS:
        assert key in quality
    assert quality["volume_balance_checked"] is True
    assert quality["row_count"] == 2


# --- the numbers are self-consistent and reproducible ------------------------


def test_volume_balance_closes_for_every_row(tmp_path) -> None:
    result = _run(tmp_path, thin_at_years=[10.0], disturbance_rate_per_year=0.01)
    check_volume_balance(result.rows)  # raises if it does not


def test_a_row_whose_balance_does_not_close_is_rejected() -> None:
    with pytest.raises(ValueError, match="Volume balance"):
        check_volume_balance(
            [
                {
                    "stand_id": 1,
                    "initial_volume_m3": 100.0,
                    "gross_growth_m3": 10.0,
                    "disturbance_loss_m3": 0.0,
                    "harvested_m3": 0.0,
                    "net_volume_m3": 999.0,
                }
            ]
        )


def test_the_run_is_reproducible_from_its_seed(tmp_path) -> None:
    one = _run(tmp_path / "one")
    two = _run(tmp_path / "two")
    assert one.rows == two.rows

    quality_one = json.loads(one.artifacts.quality_report_path.read_text(encoding="utf-8"))
    quality_two = json.loads(two.artifacts.quality_report_path.read_text(encoding="utf-8"))
    assert quality_one["determinism_hash"] == quality_two["determinism_hash"]


def test_each_stand_s_seed_derives_from_the_scenario_s(tmp_path) -> None:
    """Stand order cannot change a stand's numbers."""
    forwards = _run(tmp_path / "fwd", stands=_stands(3))
    backwards = _run(tmp_path / "rev", stands=list(reversed(_stands(3))))
    by_id = {row["stand_id"]: row for row in backwards.rows}
    for row in forwards.rows:
        assert by_id[row["stand_id"]]["stand_seed"] == row["stand_seed"]


def test_summary_columns_are_the_schema_s(tmp_path) -> None:
    result = _run(tmp_path)
    rows = load_scenario_summary(result.artifacts.scenario_summary_path)
    assert set(rows[0]) == set(SCENARIO_SUMMARY_COLUMNS)


# --- failure modes -----------------------------------------------------------


def test_an_unknown_stage_is_named_rather_than_skipped() -> None:
    with pytest.raises(ValueError, match="Unknown stage"):
        build_pipeline(("growth", "teleport"), StageContext(volume=_volume))


def test_known_stages_are_the_registry_s() -> None:
    assert known_stages() == ("disturbance", "growth", "management", "valuation")


def test_a_valuation_stage_without_settings_is_an_error() -> None:
    """Skipping it would report a run as having valued its removals at nothing."""
    with pytest.raises(ValueError, match="ValuationSettings"):
        build_pipeline(("valuation",), StageContext(volume=_volume))


def test_a_run_needs_stands_and_periods(tmp_path) -> None:
    with pytest.raises(ValueError, match="n_steps must be > 0"):
        _run(tmp_path, n_steps=0)
    with pytest.raises(ValueError, match="at least one stand"):
        _run(tmp_path, stands=[])
