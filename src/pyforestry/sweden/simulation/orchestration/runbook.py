"""Artifact-contract harness for Sweden scenario presets.

**This module runs no forest model.** It exists to exercise the artifact contract
-- that a preset run emits ``run_manifest.json``, ``scenario_summary.parquet`` and
``quality_report.json``, with the required keys, reproducibly from a seed -- and
it fills those artifacts with a synthetic random walk (see
:func:`_synthetic_summary_rows`). No :class:`~pyforestry.base.helpers.stand.Stand`,
no :class:`~pyforestry.base.simulation.GrowthModel` and no stage runtime is
involved, and the preset's ``stages()``, ``rulesets()`` and ``guard_policy()`` are
recorded rather than executed.

The numbers it emits are plausible-looking cubic metres per hectare, so every
artifact it writes is stamped ``"synthetic": true`` and
:func:`emit_scenario_artifact_contract` warns when called. Until a preset is wired
to a model, treat its output as a schema fixture and nothing else.
"""

from __future__ import annotations

import json
import random
import subprocess
import warnings
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pyforestry.sweden.simulation.data import (
    MANIFEST_REQUIRED_KEYS,
    QUALITY_REPORT_FILENAME,
    QUALITY_REPORT_REQUIRED_KEYS,
    QUALITY_REPORT_SCHEMA_VERSION,
    REQUIRED_ARTIFACTS,
    RUN_MANIFEST_FILENAME,
    RUN_MANIFEST_SCHEMA_VERSION,
    SCENARIO_SUMMARY_COLUMNS,
    SCENARIO_SUMMARY_FILENAME,
    stand_id_series,
)
from pyforestry.sweden.simulation.policy import management_intensity, scenario_factors
from pyforestry.sweden.simulation.presets import SwedenScenarioPreset

if TYPE_CHECKING:  # pragma: no cover
    pass


@dataclass(frozen=True)
class PresetRunResult:
    """Resolved paths for artifacts produced by a preset run."""

    run_manifest_path: Path
    scenario_summary_path: Path
    quality_report_path: Path


def _parquet_engine_available() -> bool:
    """Return whether a parquet backend is importable in this runtime."""
    try:
        import pyarrow  # noqa: F401
    except ImportError:
        try:
            import fastparquet  # noqa: F401
        except ImportError:
            return False
    return True


def _stand_seed(*, preset_seed: int, stand_id: int) -> int:
    """Derive a deterministic per-stand seed from preset seed and stand id."""
    token = f"{preset_seed}:{stand_id}"
    return int(sha256(token.encode("utf-8")).hexdigest()[:16], 16) & 0x7FFFFFFF


def _determinism_hash(rows: list[dict[str, Any]]) -> str:
    """Compute a stable hash for summary rows used in replay checks."""
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _synthetic_summary_rows(
    *,
    preset: SwedenScenarioPreset,
    global_seed: int,
    n_steps: int,
    n_stands: int,
) -> list[dict[str, Any]]:
    """Generate synthetic stand-level summary rows to populate the artifact schema.

    These volumes are a seeded random walk, not a projection: no stand, no growth
    model and no equation is involved. They exist so the artifact contract can be
    exercised end to end, and they are deterministic in the seed so the
    determinism check is meaningful about the *harness*, not about any model.
    """
    preset_seed = preset.seed_strategy(global_seed=global_seed)
    factors = scenario_factors(preset.scenario_id)
    thinning_ratio = management_intensity(preset.scenario_id)

    rows: list[dict[str, Any]] = []
    for stand_id in stand_id_series(n_stands):
        seed = _stand_seed(preset_seed=preset_seed, stand_id=stand_id)
        rng = random.Random(seed)

        initial_volume = 120.0 + rng.random() * 80.0
        growth_per_step = 1.8 + rng.random() * 1.7
        gross_growth = growth_per_step * n_steps * factors["growth_factor"]
        disturbance_ratio = (0.03 + rng.random() * 0.07) * factors["disturbance_factor"]
        disturbance_loss = gross_growth * disturbance_ratio
        harvested_volume = (initial_volume + gross_growth) * thinning_ratio * 0.1
        net_volume = max(0.0, initial_volume + gross_growth - disturbance_loss - harvested_volume)

        rows.append(
            {
                "stand_id": stand_id,
                "scenario_id": preset.scenario_id,
                "stand_seed": seed,
                "initial_volume_m3": round(initial_volume, 6),
                "gross_growth_m3": round(gross_growth, 6),
                "disturbance_loss_m3": round(disturbance_loss, 6),
                "harvested_m3": round(harvested_volume, 6),
                "net_volume_m3": round(net_volume, 6),
            }
        )
    return rows


def _git_revision() -> str:
    """Return the short git revision hash, or 'unknown' if not in a repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _provenance_metadata(preset: SwedenScenarioPreset) -> dict[str, Any]:
    """Build provenance metadata from a preset's Describable properties."""
    provenance: dict[str, Any] = {"git_revision": _git_revision()}
    if hasattr(preset, "component_id") and hasattr(preset, "source"):
        src = preset.source
        provenance["component_id"] = preset.component_id
        provenance["source"] = {
            "author": src.author,
            "year": src.year,
            "title": src.title,
        }
    components = []
    for c in getattr(preset, "components", ()):
        if hasattr(c, "component_id") and hasattr(c, "source"):
            components.append(
                {
                    "component_id": c.component_id,
                    "author": c.source.author,
                    "year": c.source.year,
                }
            )
        else:
            components.append({"class": type(c).__name__})
    if components:
        provenance["components"] = components
    return provenance


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a JSON payload with stable formatting."""
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_summary_artifact(path: Path, rows: list[dict[str, Any]]) -> str:
    """Write summary rows as parquet when available, otherwise JSON fallback."""
    if _parquet_engine_available():
        import pandas as pd

        summary_df = pd.DataFrame.from_records(rows, columns=SCENARIO_SUMMARY_COLUMNS)
        summary_df.to_parquet(path, index=False)
        return "parquet"

    _write_json(
        path,
        {
            "format": "pseudo_parquet_json_v1",
            "columns": list(SCENARIO_SUMMARY_COLUMNS),
            "rows": rows,
        },
    )
    return "pseudo_parquet_json_v1"


def load_scenario_summary(path: Path) -> list[dict[str, Any]]:
    """Load scenario-summary rows from a parquet artifact or fallback payload."""
    if _parquet_engine_available():
        import pandas as pd

        summary_df = pd.read_parquet(path)
        if tuple(summary_df.columns) != SCENARIO_SUMMARY_COLUMNS:
            raise ValueError(
                "scenario_summary.parquet columns mismatch: "
                f"expected {SCENARIO_SUMMARY_COLUMNS}, got {tuple(summary_df.columns)}"
            )
        return summary_df.to_dict(orient="records")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if tuple(payload.get("columns", ())) != SCENARIO_SUMMARY_COLUMNS:
        raise ValueError(
            "scenario_summary.parquet fallback columns mismatch: "
            f"expected {SCENARIO_SUMMARY_COLUMNS}, got {tuple(payload.get('columns', ()))}"
        )
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("scenario_summary.parquet fallback rows must be a list")
    return rows


def validate_artifact_contract(output_dir: Path) -> None:
    """Validate required artifacts and minimal schema contracts."""
    for name in REQUIRED_ARTIFACTS:
        if not (output_dir / name).exists():
            raise ValueError(f"Missing required artifact: {name}")

    manifest = json.loads((output_dir / RUN_MANIFEST_FILENAME).read_text(encoding="utf-8"))
    missing_manifest_keys = [key for key in MANIFEST_REQUIRED_KEYS if key not in manifest]
    if missing_manifest_keys:
        raise ValueError(f"run_manifest.json missing keys: {missing_manifest_keys}")

    quality = json.loads((output_dir / QUALITY_REPORT_FILENAME).read_text(encoding="utf-8"))
    missing_quality_keys = [key for key in QUALITY_REPORT_REQUIRED_KEYS if key not in quality]
    if missing_quality_keys:
        raise ValueError(f"quality_report.json missing keys: {missing_quality_keys}")

    load_scenario_summary(output_dir / SCENARIO_SUMMARY_FILENAME)


def emit_scenario_artifact_contract(
    *,
    preset: SwedenScenarioPreset,
    global_seed: int,
    output_dir: Path,
    n_steps: int = 20,
    n_stands: int = 8,
    processes: int = 1,
) -> PresetRunResult:
    """Emit a preset's artifact contract, filled with synthetic numbers.

    This is a schema harness, **not** a simulation: see the module docstring. The
    volumes in ``scenario_summary.parquet`` come from a seeded random walk, and
    every artifact is stamped ``"synthetic": true`` so a downstream reader can
    tell. To project a real stand, use a model adapter
    (:class:`~pyforestry.sweden.blocks.elfving_2010.Elfving2010Model` and friends)
    or one of the composite pipelines in
    :mod:`pyforestry.sweden.simulation.presets`.

    Args:
        preset: The scenario preset whose identity, seed strategy, stages and
            required artifacts are recorded into the manifest.
        global_seed: Seed the preset derives its own from.
        output_dir: Directory to write the three artifacts into; created if absent.
        n_steps: Number of synthetic growth periods per stand.
        n_stands: Number of synthetic stands.
        processes: Recorded in the manifest; the harness is single-process.

    Returns:
        The resolved paths of the three artifacts.

    Raises:
        ValueError: If ``n_steps``, ``n_stands`` or ``processes`` is not positive.
    """
    if n_steps <= 0:
        raise ValueError("n_steps must be > 0")
    if n_stands <= 0:
        raise ValueError("n_stands must be > 0")
    if processes <= 0:
        raise ValueError("processes must be > 0")

    warnings.warn(
        "emit_scenario_artifact_contract writes an artifact-contract fixture: the "
        "volumes it reports are a seeded random walk, not a projection. No stand, "
        "growth model or stage runtime is involved, and the preset's stages(), "
        "rulesets() and guard_policy() are recorded rather than executed.",
        stacklevel=2,
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    rows = _synthetic_summary_rows(
        preset=preset,
        global_seed=global_seed,
        n_steps=n_steps,
        n_stands=n_stands,
    )
    determinism_hash = _determinism_hash(rows)

    summary_path = output_dir / SCENARIO_SUMMARY_FILENAME
    summary_encoding = _write_summary_artifact(summary_path, rows)

    manifest_path = output_dir / RUN_MANIFEST_FILENAME
    _write_json(
        manifest_path,
        {
            "schema_version": RUN_MANIFEST_SCHEMA_VERSION,
            # No model produced these numbers. Stamped into the artifact itself so
            # a consumer that never reads this module still knows.
            "synthetic": True,
            "models_run": [],
            "preset_id": preset.preset_id,
            "scenario_id": preset.scenario_id,
            "global_seed": int(global_seed),
            "processes": int(processes),
            "n_steps": int(n_steps),
            "n_stands": int(n_stands),
            "scenario_summary_encoding": summary_encoding,
            "required_artifacts": list(preset.required_artifacts()),
            "stages": list(preset.stages()),
            "provenance": _provenance_metadata(preset),
        },
    )

    quality_path = output_dir / QUALITY_REPORT_FILENAME
    artifacts_present = {name: (output_dir / name).exists() for name in REQUIRED_ARTIFACTS}
    artifacts_present[QUALITY_REPORT_FILENAME] = True
    _write_json(
        quality_path,
        {
            "schema_version": QUALITY_REPORT_SCHEMA_VERSION,
            "synthetic": True,
            "required_artifacts": list(REQUIRED_ARTIFACTS),
            "artifacts_present": artifacts_present,
            "row_count": int(len(rows)),
            "columns": list(SCENARIO_SUMMARY_COLUMNS),
            # Reproducibility of the harness, not of any model.
            "determinism_hash": determinism_hash,
        },
    )

    validate_artifact_contract(output_dir)
    return PresetRunResult(
        run_manifest_path=manifest_path,
        scenario_summary_path=summary_path,
        quality_report_path=quality_path,
    )
