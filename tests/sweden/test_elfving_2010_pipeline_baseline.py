"""The composite pipelines still produce the numbers they produced.

``Elfving2010Pipeline.step()`` runs eight phases whose *order* is part of the model:
mortality is predicted before growth so the Elfving stand calibration targets
survived rather than gross basal area, the phase-over blend needs the young-phase
DBH from before the mature step overwrote it, and the height/bark refresh has to see
the ages the age step just advanced. None of that is visible in a unit test of any
one phase, so this compares whole projection tables -- every column, every row --
against values pinned from a known-good tree.

Regenerate with ``python scripts/pin_elfving_2010_baseline.py`` *only* when a change
is meant to move the numbers, and say in the commit message which phase moved and
why. A refactor that moves them has found something, not fixed something.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Resolved through the sys.path entry this directory's conftest adds.
from _elfving_2010_baseline_scenarios import SCENARIOS, run_scenario

_FIXTURE = Path(__file__).with_name("fixtures") / "elfving_2010_pipeline_baseline.json"


def _baseline() -> dict:
    """Load the pinned projection tables."""
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("name", "kind", "overrides", "n_steps"),
    SCENARIOS,
    ids=[scenario[0] for scenario in SCENARIOS],
)
def test_projection_reproduces_pinned_table(
    name: str,
    kind: str,
    overrides: dict,
    n_steps: int,
) -> None:
    """Every column of every pinned scenario still comes out identical."""
    expected = _baseline()[name]
    observed = run_scenario(kind, overrides, n_steps)

    assert sorted(observed) == sorted(expected), f"{name}: columns changed"
    for column, expected_values in expected.items():
        observed_values = observed[column]
        assert len(observed_values) == len(expected_values), f"{name}.{column}: row count changed"
        for row, (got, want) in enumerate(zip(observed_values, expected_values, strict=True)):
            assert got == pytest.approx(want, rel=1e-9, abs=1e-9), (
                f"{name}.{column}[{row}]: {got!r} != pinned {want!r}"
            )
