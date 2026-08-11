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

#: Columns compared at a looser relative tolerance, and why.
#:
#: Every physical column -- volumes, diameters, heights, stem counts, shares --
#: reproduces bit-for-bit on every interpreter, and is held to ``rel=1e-9``.
#: The money columns do not, because they are the end of the longest accumulation
#: in the table: a value is summed over the log sections the Näsberg (1985)
#: bucking optimiser chose, and that optimiser runs on NumPy, whose pairwise
#: summation depends on library version and SIMD width. The observed spread
#: between CPython 3.11 and 3.12 is about 4e-9 relative -- roughly 0.15 SEK on
#: 50,000 -- which ``rel=1e-9`` fails and no modelling change would produce.
#:
#: ``1e-6`` is still four orders of magnitude tighter than the smallest real
#: change any phase makes to a value, so this loosens the arithmetic and not the
#: net: a phase that actually moves the money still fails here.
_MONEY_COLUMNS = frozenset({"standing_value_sek_per_ha", "value_per_m3sk_sek"})

#: Relative tolerance for the physical columns: unchanged, and exact in practice.
_EXACT_REL = 1e-9
#: Relative tolerance for the money columns. See :data:`_MONEY_COLUMNS`.
_MONEY_REL = 1e-6


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
        rel = _MONEY_REL if column in _MONEY_COLUMNS else _EXACT_REL
        for row, (got, want) in enumerate(zip(observed_values, expected_values, strict=True)):
            assert got == pytest.approx(want, rel=rel, abs=1e-9), (
                f"{name}.{column}[{row}]: {got!r} != pinned {want!r}"
            )
