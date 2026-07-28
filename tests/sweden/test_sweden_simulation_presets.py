from __future__ import annotations

import json
import sys
import types

import pytest

import pyforestry.sweden.simulation.orchestration.runbook as runbook_module
from pyforestry.sweden.simulation import (
    build_baseline_scenario_config,
    emit_scenario_artifact_contract,
    load_scenario_summary,
    validate_artifact_contract,
)
from pyforestry.sweden.simulation.data import (
    QUALITY_REPORT_FILENAME,
    REQUIRED_ARTIFACTS,
    RUN_MANIFEST_FILENAME,
    SCENARIO_SUMMARY_COLUMNS,
    SCENARIO_SUMMARY_FILENAME,
    stand_id_series,
)
from pyforestry.sweden.simulation.policy import (
    management_intensity,
    management_plan,
    scenario_factors,
    supported_scenarios,
)
from pyforestry.sweden.simulation.presets import get_pipeline, get_scenario_config


def test_sweden_preset_replay_is_deterministic_across_process_counts(tmp_path) -> None:
    preset = build_baseline_scenario_config()
    run_one = tmp_path / "run_p1"
    run_two = tmp_path / "run_p4"

    result_one = emit_scenario_artifact_contract(
        preset=preset,
        global_seed=20260212,
        output_dir=run_one,
        n_steps=18,
        n_stands=6,
        processes=1,
    )
    result_two = emit_scenario_artifact_contract(
        preset=preset,
        global_seed=20260212,
        output_dir=run_two,
        n_steps=18,
        n_stands=6,
        processes=4,
    )

    summary_one = load_scenario_summary(result_one.scenario_summary_path)
    summary_two = load_scenario_summary(result_two.scenario_summary_path)
    assert set(summary_one[0]) == set(SCENARIO_SUMMARY_COLUMNS)
    assert summary_one == summary_two

    quality_one = json.loads(result_one.quality_report_path.read_text(encoding="utf-8"))
    quality_two = json.loads(result_two.quality_report_path.read_text(encoding="utf-8"))
    assert quality_one["determinism_hash"] == quality_two["determinism_hash"]


def test_sweden_preset_writes_required_artifacts_and_schema(tmp_path) -> None:
    preset = build_baseline_scenario_config()
    output_dir = tmp_path / "artifact_run"
    result = emit_scenario_artifact_contract(
        preset=preset,
        global_seed=20260212,
        output_dir=output_dir,
        n_steps=20,
        n_stands=5,
        processes=2,
    )

    validate_artifact_contract(output_dir)

    for artifact in REQUIRED_ARTIFACTS:
        assert (output_dir / artifact).exists()

    manifest = json.loads(result.run_manifest_path.read_text(encoding="utf-8"))
    assert manifest["scenario_id"] == "baseline"
    assert manifest["required_artifacts"] == list(REQUIRED_ARTIFACTS)

    summary = load_scenario_summary(output_dir / SCENARIO_SUMMARY_FILENAME)
    assert set(summary[0]) == set(SCENARIO_SUMMARY_COLUMNS)
    assert len(summary) == 5

    quality = json.loads((output_dir / QUALITY_REPORT_FILENAME).read_text(encoding="utf-8"))
    assert quality["required_artifacts"] == list(REQUIRED_ARTIFACTS)
    assert quality["artifacts_present"][RUN_MANIFEST_FILENAME]
    assert quality["artifacts_present"][SCENARIO_SUMMARY_FILENAME]
    assert quality["artifacts_present"][QUALITY_REPORT_FILENAME]


def test_policy_and_preset_lookups_cover_error_paths() -> None:
    assert stand_id_series(3) == [1, 2, 3]
    assert management_intensity("baseline") == pytest.approx(0.20)
    assert management_plan("baseline").thinning_ratio == pytest.approx(0.20)
    assert supported_scenarios() == ("baseline",)
    assert scenario_factors("baseline").disturbance_factor == pytest.approx(1.0)
    assert get_scenario_config("baseline").scenario_id == "baseline"

    with pytest.raises(ValueError, match="Unsupported scenario_id"):
        management_intensity("unknown")
    with pytest.raises(ValueError, match="Unsupported scenario_id"):
        scenario_factors("unknown")

    # The storm-risk scenario was removed: its growth and disturbance multipliers
    # were invented, with no source behind them. It must not resolve anywhere.
    for lookup in (management_intensity, scenario_factors, get_scenario_config):
        with pytest.raises(ValueError, match="Unsupported scenario_id"):
            lookup("storm_risk_high")
    with pytest.raises(ValueError, match="Unsupported scenario_id"):
        get_scenario_config("unknown")
    with pytest.raises(ValueError, match="n_stands must be > 0"):
        stand_id_series(0)


def test_runbook_validation_and_fallback_summary_paths(tmp_path, monkeypatch) -> None:
    with pytest.raises(ValueError, match="n_steps must be > 0"):
        emit_scenario_artifact_contract(
            preset=build_baseline_scenario_config(),
            global_seed=1,
            output_dir=tmp_path / "bad-steps",
            n_steps=0,
        )
    with pytest.raises(ValueError, match="n_stands must be > 0"):
        emit_scenario_artifact_contract(
            preset=build_baseline_scenario_config(),
            global_seed=1,
            output_dir=tmp_path / "bad-stands",
            n_stands=0,
        )
    with pytest.raises(ValueError, match="processes must be > 0"):
        emit_scenario_artifact_contract(
            preset=build_baseline_scenario_config(),
            global_seed=1,
            output_dir=tmp_path / "bad-procs",
            processes=0,
        )

    missing_dir = tmp_path / "missing"
    missing_dir.mkdir()
    with pytest.raises(ValueError, match="Missing required artifact"):
        validate_artifact_contract(missing_dir)

    summary_path = tmp_path / "scenario_summary.parquet"
    summary_path.write_text(
        json.dumps({"columns": ["bad"], "rows": []}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(runbook_module, "_parquet_engine_available", lambda: False)
    with pytest.raises(ValueError, match="fallback columns mismatch"):
        runbook_module.load_scenario_summary(summary_path)

    summary_path.write_text(
        json.dumps({"columns": list(SCENARIO_SUMMARY_COLUMNS), "rows": {}}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="fallback rows must be a list"):
        runbook_module.load_scenario_summary(summary_path)


def test_runbook_parquet_paths_and_schema_key_errors(tmp_path, monkeypatch) -> None:
    class _DummyDataFrame:
        def __init__(self, rows, columns):
            self._rows = rows
            self.columns = tuple(columns)

        def to_parquet(self, path, index=False):
            payload = {"columns": list(self.columns), "rows": self._rows, "index": index}
            path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

        def to_dict(self, orient="records"):
            assert orient == "records"
            return list(self._rows)

    class _DummyDataFrameFactory:
        @staticmethod
        def from_records(rows, columns):
            return _DummyDataFrame(rows, columns)

    class _DummyPandas:
        DataFrame = _DummyDataFrameFactory

        @staticmethod
        def read_parquet(path):
            payload = json.loads(path.read_text(encoding="utf-8"))
            return _DummyDataFrame(payload["rows"], payload["columns"])

    monkeypatch.setattr(runbook_module, "_parquet_engine_available", lambda: True)
    monkeypatch.setitem(sys.modules, "pandas", _DummyPandas)
    monkeypatch.setitem(sys.modules, "pyarrow", types.SimpleNamespace())

    rows = [
        {
            "stand_id": 1,
            "scenario_id": "baseline",
            "stand_seed": 123,
            "initial_volume_m3": 100.0,
            "gross_growth_m3": 10.0,
            "disturbance_loss_m3": 1.0,
            "harvested_m3": 2.0,
            "net_volume_m3": 107.0,
        }
    ]
    summary_path = tmp_path / "summary.parquet"
    encoding = runbook_module._write_summary_artifact(summary_path, rows)
    assert encoding == "parquet"
    loaded = runbook_module.load_scenario_summary(summary_path)
    assert loaded == rows

    wrong_columns = tmp_path / "wrong_columns.parquet"
    wrong_columns.write_text(
        json.dumps({"columns": ["bad"], "rows": rows}, sort_keys=True),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="columns mismatch"):
        runbook_module.load_scenario_summary(wrong_columns)

    out = tmp_path / "schema-errors"
    out.mkdir()
    (out / SCENARIO_SUMMARY_FILENAME).write_text(
        json.dumps({"columns": list(SCENARIO_SUMMARY_COLUMNS), "rows": rows}, sort_keys=True),
        encoding="utf-8",
    )
    (out / RUN_MANIFEST_FILENAME).write_text(json.dumps({"schema_version": 1}, sort_keys=True))
    (out / QUALITY_REPORT_FILENAME).write_text(
        json.dumps(
            {"schema_version": 1, "required_artifacts": [], "artifacts_present": {}},
            sort_keys=True,
        )
    )
    with pytest.raises(ValueError, match="run_manifest.json missing keys"):
        runbook_module.validate_artifact_contract(out)

    manifest_ok = {
        "schema_version": 1,
        "preset_id": "x",
        "scenario_id": "baseline",
        "global_seed": 1,
        "processes": 1,
        "n_steps": 1,
        "n_stands": 1,
        "scenario_summary_encoding": "pseudo_parquet_json_v1",
        "required_artifacts": [],
        "stages": [],
        "provenance": {"git_revision": "test"},
    }
    (out / RUN_MANIFEST_FILENAME).write_text(
        json.dumps(manifest_ok, sort_keys=True), encoding="utf-8"
    )
    (out / QUALITY_REPORT_FILENAME).write_text(
        json.dumps({"schema_version": 1, "required_artifacts": []}, sort_keys=True),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="quality_report.json missing keys"):
        runbook_module.validate_artifact_contract(out)


def test_artifact_contract_output_is_labelled_synthetic(tmp_path):
    """The harness runs no model, and its artifacts must say so.

    These are plausible-looking cubic metres produced by a seeded random walk. A
    consumer reading only the artifacts -- which is the point of an artifact
    contract -- has no other way to tell them apart from a projection.
    """
    preset = build_baseline_scenario_config()
    with pytest.warns(UserWarning, match="not a projection"):
        result = emit_scenario_artifact_contract(
            preset=preset,
            global_seed=7,
            output_dir=tmp_path,
            n_steps=3,
            n_stands=2,
        )

    manifest = json.loads(result.run_manifest_path.read_text(encoding="utf-8"))
    assert manifest["synthetic"] is True
    assert manifest["models_run"] == []

    quality = json.loads(result.quality_report_path.read_text(encoding="utf-8"))
    assert quality["synthetic"] is True


def test_get_pipeline_reaches_the_real_simulators() -> None:
    """The lookup that ``get_preset`` could not be.

    It was typed ``-> SwedenScenarioPreset`` and knew only ``"baseline"``, so the
    one discovery entrypoint the package had returned the scenario configuration
    and could reach neither of the two simulators.
    """
    from pyforestry.sweden.simulation.presets import (
        Elfving2010Pipeline,
        Soderberg1986Pipeline,
    )

    assert isinstance(get_pipeline("elfving_2010_composite"), Elfving2010Pipeline)
    assert isinstance(get_pipeline("soderberg_1986_composite"), Soderberg1986Pipeline)


def test_get_pipeline_names_the_alternatives_when_asked_for_an_unknown_one() -> None:
    with pytest.raises(
        ValueError, match="Known pipelines: elfving_2010_composite, soderberg_1986_composite"
    ):
        get_pipeline("not_a_pipeline")


def test_the_pipeline_and_the_growth_model_no_longer_share_a_name() -> None:
    """One string used to name two very different things through two front doors.

    ``project(model="elfving_2010")`` steps trees the caller supplies with the
    Elfving (2010) single-tree model. ``get_pipeline("elfving_2010")`` used to
    reconstruct a stand with NYSKOG and run nine more published models around it.
    Same key, different science, and nothing said so.
    """
    import pyforestry as pf

    assert "elfving_2010" in pf.available_models()
    assert "elfving_2010" not in pf.available_pipelines()
    assert "elfving_2010_composite" in pf.available_pipelines()
    assert "elfving_2010_composite" not in pf.available_models()

    with pytest.raises(ValueError, match="elfving_2010_composite"):
        get_pipeline("elfving_2010")


def test_project_points_at_get_pipeline_for_a_composite() -> None:
    """A pipeline builds its own stand, so project() cannot drive one -- and says so."""
    import pyforestry as pf

    with pytest.raises(ValueError, match="get_pipeline"):
        pf.project(object(), model="elfving_2010_composite", years=5)
