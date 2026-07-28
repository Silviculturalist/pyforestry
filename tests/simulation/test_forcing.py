"""Forcings are the general tool, and the package ships no instances of it.

A forcing is a named value a run reads for the period it is in. It replaced a
frozen pair of ``growth_factor`` and ``disturbance_factor`` fields -- two
instances of one idea, hard-coded, with no way to express a third, or a value
that changes year by year, or one that differs by species.
"""

from __future__ import annotations

import pytest

from pyforestry.base.contracts import SourceReference
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.simulation.forcing import (
    GROWTH,
    PRICE,
    AnnualForcing,
    ConstantForcing,
    ForcingSet,
    is_neutral_value,
)

CITED = SourceReference(author="Test fixture", year=2026, title="Invented here, and saying so")
SPRUCE = TreeSpecies.Sweden.picea_abies
PINE = TreeSpecies.Sweden.pinus_sylvestris


# --- resolution in time ------------------------------------------------------


def test_a_constant_forcing_holds_for_the_whole_run() -> None:
    forcing = ConstantForcing(GROWTH, 1.05, source=CITED)
    assert forcing.at(2014) == 1.05
    assert forcing.at(2099) == 1.05


def test_an_annual_forcing_is_read_per_year() -> None:
    """The weather-correction case the whole type exists for."""
    weather = AnnualForcing(GROWTH, {2014: 1.04, 2015: 1.02, 2016: 0.98, 2019: 0.67}, source=CITED)
    assert weather.at(2014) == 1.04
    assert weather.at(2016) == 0.98
    assert weather.at(2019) == 0.67


def test_a_year_outside_the_series_raises_by_default() -> None:
    """A run past the end of a weather series is asking what the series cannot say."""
    weather = AnnualForcing(GROWTH, {2014: 1.04, 2015: 1.02}, source=CITED)
    with pytest.raises(KeyError, match="2020"):
        weather.at(2020)


@pytest.mark.parametrize(
    ("outside", "year", "expected"),
    [
        ("hold", 2020, 1.02),
        ("hold", 2000, 1.04),
        ("neutral", 2020, 1.0),
    ],
)
def test_the_rule_outside_the_series_is_declared(outside, year, expected) -> None:
    weather = AnnualForcing(GROWTH, {2014: 1.04, 2015: 1.02}, outside_series=outside, source=CITED)
    assert weather.at(year) == expected


def test_an_empty_series_points_at_the_constant_form() -> None:
    with pytest.raises(ValueError, match="ConstantForcing"):
        AnnualForcing(GROWTH, {}, source=CITED)


# --- type ---------------------------------------------------------------------


def test_a_forcing_can_vary_by_species_as_well_as_year() -> None:
    """The value at a year is whatever you put there -- here, a mapping per species."""
    weather = AnnualForcing(
        GROWTH,
        {
            2014: {SPRUCE: 1.06, PINE: 1.01},
            2015: {SPRUCE: 0.98, PINE: 1.03},
        },
        source=CITED,
    )
    forcings = ForcingSet([weather])

    assert forcings.multiplier(GROWTH, 2014, key=SPRUCE) == pytest.approx(1.06)
    assert forcings.multiplier(GROWTH, 2014, key=PINE) == pytest.approx(1.01)
    assert forcings.multiplier(GROWTH, 2015, key=SPRUCE) == pytest.approx(0.98)


def test_a_species_the_mapping_does_not_name_is_unforced() -> None:
    """A forcing that names only spruce leaves everything else exactly as modelled."""
    forcings = ForcingSet([AnnualForcing(GROWTH, {2014: {SPRUCE: 1.06}}, source=CITED)])
    assert forcings.multiplier(GROWTH, 2014, key=PINE) == 1.0


def test_a_value_that_is_not_a_number_is_read_not_multiplied() -> None:
    """Not every forcing is a multiplier; some are data a step interprets."""
    regime = ConstantForcing("harvest_regime", "clearfell_only", source=CITED)
    forcings = ForcingSet([regime])

    assert forcings.value("harvest_regime", 2014) == "clearfell_only"
    with pytest.raises(TypeError, match="cannot be multiplied"):
        forcings.multiplier("harvest_regime", 2014)


def test_a_missing_name_reads_as_the_default_and_multiplies_by_one() -> None:
    empty = ForcingSet()
    assert empty.value("nothing", 2014, default="fallback") == "fallback"
    assert empty.multiplier(GROWTH, 2014) == 1.0


# --- composition --------------------------------------------------------------


def test_forcings_on_one_name_compose_by_multiplication() -> None:
    """A weather correction and a nitrogen response both act on growth."""
    forcings = ForcingSet(
        [
            ConstantForcing(GROWTH, 1.1, source=CITED),
            ConstantForcing(GROWTH, 1.2, source=CITED),
        ]
    )
    assert forcings.multiplier(GROWTH, 2014) == pytest.approx(1.32)


def test_merge_keeps_both_sets_in_order() -> None:
    a = ForcingSet([ConstantForcing(GROWTH, 1.1, source=CITED)])
    b = ForcingSet([ConstantForcing(PRICE, 1.02, source=CITED)])
    merged = a.merge(b)
    assert merged.names() == {GROWTH, PRICE}
    assert len(merged) == 2


# --- the citation rule ---------------------------------------------------------


def test_a_neutral_forcing_needs_no_source() -> None:
    """1.0 changes nothing, so there is nothing to cite."""
    assert ConstantForcing(GROWTH).at(2014) == 1.0
    assert AnnualForcing(GROWTH, {2014: 1.0, 2015: 1.0}).at(2014) == 1.0


@pytest.mark.parametrize(
    "build",
    [
        lambda: ConstantForcing(GROWTH, 1.05),
        lambda: AnnualForcing(GROWTH, {2014: 1.04}),
        lambda: AnnualForcing(GROWTH, {2014: {SPRUCE: 1.06}}),
        lambda: ConstantForcing("harvest_regime", "clearfell_only"),
    ],
    ids=["constant", "annual", "per-species", "non-numeric"],
)
def test_anything_that_is_not_neutral_must_be_cited(build) -> None:
    """The rule that removed ``climate_rcp45``, enforced rather than remembered."""
    with pytest.raises(ValueError, match="where it comes from"):
        build()


@pytest.mark.parametrize(
    ("value", "neutral"),
    [
        (1.0, True),
        (1, True),
        ({SPRUCE: 1.0, PINE: 1.0}, True),
        (1.05, False),
        ({SPRUCE: 1.0, PINE: 0.9}, False),
        ("clearfell_only", False),
        (True, False),
    ],
)
def test_what_counts_as_neutral(value, neutral) -> None:
    assert is_neutral_value(value) is neutral


# --- the manifest --------------------------------------------------------------


def test_a_forcing_renders_itself_with_its_citation() -> None:
    """A reader of the manifest sees not just that growth was scaled but by whose word."""
    record = AnnualForcing(GROWTH, {2014: 1.04, 2015: 1.02}, source=CITED).as_manifest()
    assert record["name"] == GROWTH
    assert record["resolution"] == "annual"
    assert record["series"] == {"2014": 1.04, "2015": 1.02}
    assert record["source"]["author"] == "Test fixture"


def test_a_per_species_forcing_renders_its_keys_as_strings() -> None:
    record = ConstantForcing(GROWTH, {SPRUCE: 1.06}, source=CITED).as_manifest()
    assert list(record["value"]) == [str(SPRUCE)]
