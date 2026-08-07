"""Regenerate the pinned Elfving/Söderberg composite projection tables.

The composite pipelines run eight phases in an order that carries scientific
coupling -- mortality is predicted before growth so the Elfving stand calibration
targets survived rather than gross basal area -- and most of that ordering is not
visible from any single unit test. This script freezes what the pipelines actually
produce, column by column and row by row, so a change that was meant to be a pure
refactor can be checked against numbers rather than against intent.

Run it only when a change is *meant* to move the numbers, and say in the commit
message which phase moved and why::

    python scripts/pin_elfving_2010_baseline.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "tests" / "sweden"))
sys.path.insert(0, str(_REPO_ROOT / "src"))

from _elfving_2010_baseline_scenarios import SCENARIOS, run_scenario  # noqa: E402

_FIXTURE = _REPO_ROOT / "tests" / "sweden" / "fixtures" / "elfving_2010_pipeline_baseline.json"


def main() -> int:
    """Write every scenario's projection table to the fixture file."""
    payload = {}
    for name, kind, overrides, n_steps in SCENARIOS:
        print(f"running {name} ({kind}, {n_steps} steps)...", flush=True)
        payload[name] = run_scenario(kind, overrides, n_steps)
    _FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    _FIXTURE.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {_FIXTURE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
