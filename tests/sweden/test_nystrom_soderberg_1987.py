import math

import pytest

from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.systems.nystrom_soderberg_1987 import NystromSoderberg1987


def test_age_at_breast_height_pine():
    height_dm = 30.0
    mean_height_dm = 25.0
    site_index_dm = 200.0

    expected = (
        2.548 * math.log(height_dm - 12.0)
        + 68.228 * (height_dm / site_index_dm) ** 2
        + -2.609e-03 * height_dm * site_index_dm / 10.0
        + 24.540 * (mean_height_dm / site_index_dm) ** 2
        + 0.572 * (height_dm - mean_height_dm) / mean_height_dm
        + -1.000
    )
    expected = max(expected, 0.5)

    result = NystromSoderberg1987.age_at_breast_height(
        height_dm=height_dm,
        mean_height_dm=mean_height_dm,
        site_index_dm=site_index_dm,
        species=TreeSpecies.Sweden.pinus_sylvestris,
    )
    assert math.isclose(result, expected, rel_tol=1e-9)


def test_dbh_from_height_pine():
    height_dm = 30.0
    total_height_sqr_m2_per_100m2 = 50.0
    broadleaf_height_sqr_share = 0.2
    natural_regeneration = 1
    cleaning_indicator = 1
    years_since_cleaning = 5
    altitude_m = 100.0
    latitude_deg = 60.0
    shrubs = 0
    herb_grass = 1
    near_coast = 0
    site_index_pine_m = 20.0
    h_max_m = 3.0

    height_diff_dm = max(1.0, h_max_m * 10.0 - height_dm)
    sqr_diam = (
        math.exp(
            1.251
            + 2.098 * math.log(height_dm - 10.0)
            + -1.473e-04 * total_height_sqr_m2_per_100m2
            + -0.176 * math.log(total_height_sqr_m2_per_100m2 + 100.0)
            + -0.098
            * math.log(1.0 + height_diff_dm * (total_height_sqr_m2_per_100m2 + 100.0) * 0.001)
            + 0.136 * math.sin(broadleaf_height_sqr_share * 1.5708)
            + -0.312 * natural_regeneration
            + 0.0244 * natural_regeneration * math.sqrt(height_dm)
            + -0.171 * cleaning_indicator * (1.0 / (1.0 + years_since_cleaning))
            + 0.022 * cleaning_indicator * math.log(10.0 + years_since_cleaning)
            + 0.014 * latitude_deg
            + -4.660e-04 * altitude_m
            + 1.260e-04 * (altitude_m / 10.0) ** 2
            + 0.088 * herb_grass
            + 0.096 * near_coast
        )
        * 1.070
    )
    expected = math.sqrt(sqr_diam) * 0.1

    result = NystromSoderberg1987.dbh_from_height(
        height_dm=height_dm,
        species=TreeSpecies.Sweden.pinus_sylvestris,
        total_height_sqr_m2_per_100m2=total_height_sqr_m2_per_100m2,
        broadleaf_height_sqr_share=broadleaf_height_sqr_share,
        natural_regeneration=natural_regeneration,
        cleaning_indicator=cleaning_indicator,
        years_since_cleaning=years_since_cleaning,
        altitude_m=altitude_m,
        latitude_deg=latitude_deg,
        shrubs=shrubs,
        herb_grass=herb_grass,
        near_coast=near_coast,
        site_index_pine_m=site_index_pine_m,
        h_max_m=h_max_m,
    )
    assert math.isclose(result, expected, rel_tol=1e-9)


def test_age_at_breast_height_short_tree_returns_minus_one() -> None:
    assert (
        NystromSoderberg1987.age_at_breast_height(
            height_dm=11.5,
            mean_height_dm=20.0,
            site_index_dm=180.0,
            species=TreeSpecies.Sweden.picea_abies,
        )
        == -1.0
    )


@pytest.mark.parametrize(
    "species",
    [TreeSpecies.Sweden.picea_abies, TreeSpecies.Sweden.betula_pendula],
)
def test_age_at_breast_height_other_species_groups(species) -> None:
    age = NystromSoderberg1987.age_at_breast_height(
        height_dm=35.0,
        mean_height_dm=28.0,
        site_index_dm=200.0,
        species=species,
        stub_indicator=1.0,
    )
    assert age > 0.5


def test_dbh_from_height_returns_zero_below_threshold() -> None:
    assert (
        NystromSoderberg1987.dbh_from_height(
            height_dm=12.5,
            species=TreeSpecies.Sweden.betula_pendula,
            total_height_sqr_m2_per_100m2=60.0,
            broadleaf_height_sqr_share=0.3,
            natural_regeneration=1,
            cleaning_indicator=0,
            years_since_cleaning=0,
            altitude_m=120.0,
            latitude_deg=63.0,
            shrubs=1,
            herb_grass=0,
            near_coast=0,
            site_index_pine_m=18.0,
            h_max_m=2.0,
        )
        == 0.0
    )


@pytest.mark.parametrize(
    "species",
    [TreeSpecies.Sweden.picea_abies, TreeSpecies.Sweden.betula_pendula],
)
def test_dbh_from_height_spruce_and_birch_branches(species) -> None:
    dbh_cm = NystromSoderberg1987.dbh_from_height(
        height_dm=42.0,
        species=species,
        total_height_sqr_m2_per_100m2=75.0,
        broadleaf_height_sqr_share=0.4,
        natural_regeneration=0,
        cleaning_indicator=1,
        years_since_cleaning=10,
        altitude_m=200.0,
        latitude_deg=60.0,
        shrubs=1,
        herb_grass=1,
        near_coast=1,
        site_index_pine_m=20.0,
        h_max_m=4.8,
        veg=1,
    )
    assert dbh_cm > 0.0
