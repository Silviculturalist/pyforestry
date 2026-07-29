"""The artifacts a scenario run emits, and what has to be in them.

These three files are how a run is read back without rerunning it:

* ``run_manifest.json`` -- **how the run was constructed**: which configuration
  and scenario, which models with which citations, the ordered stages, the
  rulesets that were applied and their values, the guard policy, the seeds, and
  the git revision. This is the artifact's reason to exist. A number in the
  summary is only interpretable against the manifest that says what produced it.
* ``scenario_summary.parquet`` -- one row per stand: the volume balance, and what
  it was worth.
* ``quality_report.json`` -- what was checked, and the determinism hash that lets
  two runs of the same configuration be compared without diffing floats.

The schema was Sweden's (``sweden/simulation/data/schema.py``) and is region-
agnostic; Norway had none, which is one reason it had no runbook of its own.

Every field in the summary closes an identity::

    net_volume_m3 == initial_volume_m3 + gross_growth_m3
                     - disturbance_loss_m3 - harvested_m3

    valued is False  =>  nominal_revenue == 0 and net_present_value == 0
    harvested_m3 == 0  =>  nominal_revenue == 0

:func:`validate_artifact_contract` checks both per row, so a run whose bookkeeping
does not add up fails at the point of writing rather than in whatever reads it.

**Why ``valued`` is a column and not a null.** Not every run prices what it cuts:
a configuration without a ``"valuation"`` stage removes wood and never asks what
it fetched. Writing ``0`` for such a run beside a non-zero ``harvested_m3`` reads
as *sold forty cubic metres for nothing*, and writing null leaves a reader unable
to tell "earned nothing" from "never asked" without going to the manifest -- which
defeats the summary's purpose. The flag makes the three states distinguishable
from the row alone: ``(False, 0)`` was not priced, ``(True, 0)`` was priced and
earned nothing, ``(True, x)`` earned ``x``.

**What the money is in** is recorded rather than assumed.
``valuation.price_list`` names the list a run priced against, states the currency
its prices are quoted in and carries its publisher's citation -- read off the
:class:`~pyforestry.base.pricelist.PricelistIdentity` that price list declares --
while ``valuation.discount_rate`` and ``valuation.base_year`` say how that money
was moved in time. Two runs' figures are comparable when those blocks agree, which
a reader can now check: until a price list had an identity to record, the summary
carried sums in an unnamed currency against prices from nowhere. A run priced
against the analyst's own table says that here too, in the ``(none)``/year-0 form
the rest of the package uses for anything authored rather than published.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Any, Mapping, Sequence

__all__ = [
    "MANIFEST_REQUIRED_KEYS",
    "QUALITY_REPORT_FILENAME",
    "QUALITY_REPORT_REQUIRED_KEYS",
    "QUALITY_REPORT_SCHEMA_VERSION",
    "REQUIRED_ARTIFACTS",
    "RUN_MANIFEST_FILENAME",
    "RUN_MANIFEST_SCHEMA_VERSION",
    "SCENARIO_SUMMARY_COLUMNS",
    "SCENARIO_SUMMARY_FILENAME",
    "ScenarioArtifacts",
    "check_value_consistency",
    "check_volume_balance",
    "determinism_hash",
    "git_revision",
    "load_scenario_summary",
    "validate_artifact_contract",
    "write_artifacts",
]

#: Both bumped from ``"2.0"`` when the summary grew the three money columns and
#: the manifest grew the ``valuation`` block that makes them readable. Adding a
#: column is a break here by construction: :func:`load_scenario_summary` validates
#: the column tuple exactly, so a 2.0 artifact does not load under 3.x and is not
#: made to. These files are the output of a run, not a store -- regenerating one
#: costs a rerun, and a migration path would be a promise about numbers whose
#: construction has changed. What 3.x does owe a reader is a diagnosis rather than
#: two tuples to diff, which is what the loader gives.
#:
#: ``"3.1"`` added ``valuation.price_list``: the manifest now records which list
#: produced the money columns and what currency they are in. A minor bump because
#: the summary is untouched -- 3.0's columns are 3.1's, and a 3.0 file still loads
#: -- while a 3.0 *manifest* is missing a block rather than unreadable, and the
#: version is how a reader tells the two apart instead of guessing from an absent
#: key.
RUN_MANIFEST_SCHEMA_VERSION = "3.1"
QUALITY_REPORT_SCHEMA_VERSION = "3.1"

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
    # Whether a valuation stage priced this run's removals at all. See the module
    # docstring: it is what keeps "earned nothing" apart from "never asked".
    "valued",
    # The revenue as earned, each period in the money of its own year -- a PRICE
    # forcing, if the run declared one, is already in it. The currency is the one
    # the manifest's ``valuation.price_list`` names.
    "nominal_revenue",
    # The same revenue discounted to the manifest's ``valuation.base_year``, which
    # is the run's first year.
    "net_present_value",
)

#: The 2.0 columns, kept so that a reader holding a summary written before the
#: money columns is told what it is holding.
_SCHEMA_2_0_COLUMNS = SCENARIO_SUMMARY_COLUMNS[:8]

#: Version 1.0 carried ``synthetic``, because the only writer produced a random
#: walk. It is gone: a run emits these artifacts or it does not run.
#: ``models_run``, ``rulesets_applied``, ``forcings_applied`` and ``guard_policy``
#: are required because they are what makes the summary interpretable. A forcing
#: record carries its own citation, so a reader can see not just that growth was
#: scaled but by whom it was said to be. ``valuation`` is required for the same
#: reason the others are: a net present value without the price list it was earned
#: against, the rate it was discounted at and the year it is expressed in is not a
#: number anyone can use.
MANIFEST_REQUIRED_KEYS = (
    "schema_version",
    "preset_id",
    "scenario_id",
    "region",
    "global_seed",
    "scenario_seed",
    "processes",
    "n_steps",
    "step_years",
    "n_stands",
    "scenario_summary_encoding",
    "required_artifacts",
    "stages",
    "rulesets_applied",
    "forcings_applied",
    "guard_policy",
    "valuation",
    "models_run",
    "provenance",
)

QUALITY_REPORT_REQUIRED_KEYS = (
    "schema_version",
    "required_artifacts",
    "artifacts_present",
    "row_count",
    "columns",
    "determinism_hash",
    "volume_balance_checked",
    "value_consistency_checked",
)

#: Absolute m³/ha tolerance when checking the summary's volume identity.
VOLUME_BALANCE_TOLERANCE_M3 = 1e-6


@dataclass(frozen=True)
class ScenarioArtifacts:
    """Resolved paths for the artifacts a scenario run produced."""

    run_manifest_path: Path
    scenario_summary_path: Path
    quality_report_path: Path

    @property
    def output_dir(self) -> Path:
        """The directory the three artifacts were written into."""
        return self.run_manifest_path.parent


def git_revision() -> str:
    """Return the short git revision, or ``"unknown"`` outside a repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:  # pragma: no cover - git absent or not a repo
        return "unknown"


def determinism_hash(rows: Sequence[Mapping[str, Any]]) -> str:
    """Return a stable hash of the summary rows, for replay comparison."""
    payload = json.dumps([dict(row) for row in rows], sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


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


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Write a JSON payload with stable formatting."""
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_summary(path: Path, rows: Sequence[Mapping[str, Any]]) -> str:
    """Write summary rows as parquet where a backend exists, else as JSON.

    Returns:
        The encoding used, which the manifest records so a reader knows which of
        the two it is holding.
    """
    if _parquet_engine_available():
        import pandas as pd

        frame = pd.DataFrame.from_records(list(rows), columns=SCENARIO_SUMMARY_COLUMNS)
        frame.to_parquet(path, index=False)
        return "parquet"

    _write_json(
        path,
        {
            "format": "pseudo_parquet_json_v1",
            "columns": list(SCENARIO_SUMMARY_COLUMNS),
            "rows": [dict(row) for row in rows],
        },
    )
    return "pseudo_parquet_json_v1"


def _columns_error(name: str, found: tuple[str, ...]) -> ValueError:
    """Explain a column mismatch, naming the older schema where that is what it is.

    An artifact written before the money columns fails this check, and "expected
    these eleven, got these eight" leaves the reader to work out which eight.
    """
    if found == _SCHEMA_2_0_COLUMNS:
        return ValueError(
            f"{name} is a schema 2.0 summary: it was written before the run recorded "
            "what it earned, so it carries the volume balance and nothing else. "
            f"Schema {RUN_MANIFEST_SCHEMA_VERSION} adds {list(SCENARIO_SUMMARY_COLUMNS[8:])}. "
            "There is no migration -- the missing columns are not derivable from the "
            "row, only from the run. Rerun the scenario, or read this file with the "
            "version of pyforestry that wrote it."
        )
    return ValueError(f"{name} columns mismatch: expected {SCENARIO_SUMMARY_COLUMNS}, got {found}")


def load_scenario_summary(path: Path) -> list[dict[str, Any]]:
    """Load summary rows from a parquet artifact or its JSON fallback.

    Raises:
        ValueError: If the columns are not the schema's, or the fallback payload
            is malformed.
    """
    if _parquet_engine_available():
        import pandas as pd

        frame = pd.read_parquet(path)
        if tuple(frame.columns) != SCENARIO_SUMMARY_COLUMNS:
            raise _columns_error(path.name, tuple(frame.columns))
        return frame.to_dict(orient="records")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if tuple(payload.get("columns", ())) != SCENARIO_SUMMARY_COLUMNS:
        raise _columns_error(path.name, tuple(payload.get("columns", ())))
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError(f"{path.name} fallback rows must be a list")
    return rows


def check_volume_balance(rows: Sequence[Mapping[str, Any]]) -> None:
    """Check that every summary row's volume components add up.

    Raises:
        ValueError: If a row's ``net_volume_m3`` does not equal
            ``initial + gross_growth - disturbance_loss - harvested``. Its purpose
            is to catch a run whose bookkeeping lost volume somewhere between the
            steps that removed it and the row that reports it.
    """
    for row in rows:
        expected = (
            float(row["initial_volume_m3"])
            + float(row["gross_growth_m3"])
            - float(row["disturbance_loss_m3"])
            - float(row["harvested_m3"])
        )
        actual = float(row["net_volume_m3"])
        if abs(expected - actual) > VOLUME_BALANCE_TOLERANCE_M3:
            raise ValueError(
                f"Volume balance does not close for stand {row.get('stand_id')!r}: "
                f"initial + growth - disturbance - harvested = {expected:.9f} m3/ha but "
                f"net_volume_m3 = {actual:.9f} m3/ha."
            )


def check_value_consistency(rows: Sequence[Mapping[str, Any]]) -> None:
    """Check that every summary row's money says the same thing as the rest of it.

    Two things are definitionally true of the schema, and both are checked:

    * A row that was never valued reports no revenue. ``valued`` is False exactly
      when the configuration declared no ``"valuation"`` stage, and then nothing
      priced anything, so a non-zero figure beside it could only have come from
      somewhere it should not have.
    * A row that harvested nothing earned nothing. Revenue reaches a run through
      the removal ledger, which only a merchantable removal writes to -- a storm
      is a loss, not a sale. The converse is deliberately *not* required: a
      thinning of stems too small to buck harvests volume and earns nothing.

    Raises:
        ValueError: If either fails, or a money figure is not a finite number.
    """
    for row in rows:
        stand = row.get("stand_id")
        valued = bool(row["valued"])
        nominal = float(row["nominal_revenue"])
        npv = float(row["net_present_value"])

        if not (isfinite(nominal) and isfinite(npv)):
            raise ValueError(
                f"Stand {stand!r} reports a revenue of {nominal!r} and a net present "
                f"value of {npv!r}; both must be finite numbers."
            )
        if not valued and (nominal != 0.0 or npv != 0.0):
            raise ValueError(
                f"Stand {stand!r} is marked as not valued -- its scenario declares no "
                f"'valuation' stage -- but reports a revenue of {nominal:.9g} and a net "
                f"present value of {npv:.9g}. Nothing priced its removals, so there is "
                "nowhere for either figure to have come from."
            )
        if float(row["harvested_m3"]) == 0.0 and nominal != 0.0:
            raise ValueError(
                f"Stand {stand!r} harvested nothing but reports a revenue of "
                f"{nominal:.9g}. Only a merchantable removal reaches the valuation "
                "ledger, so revenue without harvest means something else wrote to it."
            )


def validate_artifact_contract(output_dir: Path) -> None:
    """Check that a run's output directory satisfies the artifact contract.

    Raises:
        ValueError: If an artifact is missing, a required key is absent, the
            summary columns are wrong, or a row's volume balance or money does
            not add up.
    """
    for name in REQUIRED_ARTIFACTS:
        if not (output_dir / name).exists():
            raise ValueError(f"Missing required artifact: {name}")

    manifest = json.loads((output_dir / RUN_MANIFEST_FILENAME).read_text(encoding="utf-8"))
    missing = [key for key in MANIFEST_REQUIRED_KEYS if key not in manifest]
    if missing:
        raise ValueError(f"{RUN_MANIFEST_FILENAME} missing keys: {missing}")

    quality = json.loads((output_dir / QUALITY_REPORT_FILENAME).read_text(encoding="utf-8"))
    missing = [key for key in QUALITY_REPORT_REQUIRED_KEYS if key not in quality]
    if missing:
        raise ValueError(f"{QUALITY_REPORT_FILENAME} missing keys: {missing}")

    rows = load_scenario_summary(output_dir / SCENARIO_SUMMARY_FILENAME)
    check_volume_balance(rows)
    check_value_consistency(rows)


def write_artifacts(
    *,
    output_dir: Path,
    manifest: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
) -> ScenarioArtifacts:
    """Write the three artifacts and validate them before returning.

    Args:
        output_dir: Directory to write into; created if absent.
        manifest: Everything about how the run was constructed. The encoding and
            schema version are filled in here.
        rows: One summary row per stand.

    Returns:
        The resolved artifact paths.

    Raises:
        ValueError: If the artifacts do not satisfy the contract -- which is
            checked here rather than left to the reader.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = output_dir / SCENARIO_SUMMARY_FILENAME
    encoding = _write_summary(summary_path, rows)

    manifest_path = output_dir / RUN_MANIFEST_FILENAME
    _write_json(
        manifest_path,
        {
            **dict(manifest),
            "schema_version": RUN_MANIFEST_SCHEMA_VERSION,
            "scenario_summary_encoding": encoding,
        },
    )

    quality_path = output_dir / QUALITY_REPORT_FILENAME
    present = {name: (output_dir / name).exists() for name in REQUIRED_ARTIFACTS}
    present[QUALITY_REPORT_FILENAME] = True
    _write_json(
        quality_path,
        {
            "schema_version": QUALITY_REPORT_SCHEMA_VERSION,
            "required_artifacts": list(REQUIRED_ARTIFACTS),
            "artifacts_present": present,
            "row_count": len(rows),
            "columns": list(SCENARIO_SUMMARY_COLUMNS),
            "determinism_hash": determinism_hash(rows),
            "volume_balance_checked": True,
            "value_consistency_checked": True,
        },
    )

    validate_artifact_contract(output_dir)
    return ScenarioArtifacts(
        run_manifest_path=manifest_path,
        scenario_summary_path=summary_path,
        quality_report_path=quality_path,
    )
