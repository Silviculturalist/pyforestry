"""Artifact and table schemas for Sweden simulation preset outputs."""

from __future__ import annotations

RUN_MANIFEST_SCHEMA_VERSION = "1.0"
QUALITY_REPORT_SCHEMA_VERSION = "1.0"

RUN_MANIFEST_FILENAME = "run_manifest.json"
SCENARIO_SUMMARY_FILENAME = "scenario_summary.parquet"
QUALITY_REPORT_FILENAME = "quality_report.json"

REQUIRED_ARTIFACTS = (
    RUN_MANIFEST_FILENAME,
    SCENARIO_SUMMARY_FILENAME,
    QUALITY_REPORT_FILENAME,
)

SCENARIO_SUMMARY_COLUMNS = (
    "stand_id",
    "scenario_id",
    "stand_seed",
    "initial_volume_m3",
    "gross_growth_m3",
    "disturbance_loss_m3",
    "harvested_m3",
    "net_volume_m3",
)

MANIFEST_REQUIRED_KEYS = (
    "schema_version",
    "preset_id",
    "scenario_id",
    "global_seed",
    "processes",
    "n_steps",
    "n_stands",
    "scenario_summary_encoding",
    "required_artifacts",
    "stages",
    "provenance",
)

QUALITY_REPORT_REQUIRED_KEYS = (
    "schema_version",
    "required_artifacts",
    "artifacts_present",
    "row_count",
    "columns",
    "determinism_hash",
)
