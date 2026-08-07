import pytest

from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.height.soderberg_1992 import (
    soderberg_1992_height_stand_age_m,
    soderberg_1992_height_tree_age_m,
)


@pytest.mark.parametrize(
    ("species", "part_of_sweden", "expected", "kwargs"),
    [
        (
            TreeSpecies.Sweden.pinus_sylvestris,
            "north",
            21.12210818718463,
            dict(
                diameter_cm=25.0,
                max_diameter_cm=40.0,
                mean_age_total_years=80.0,
                site_index_pine_m=20.0,
                latitude_deg=60.0,
                altitude_m=100.0,
                prop_pine=0.6,
                prop_spruce=0.3,
                prop_birch=0.1,
            ),
        ),
        (
            TreeSpecies.Sweden.picea_abies,
            "middle",
            21.88838974211726,
            dict(
                diameter_cm=30.0,
                max_diameter_cm=45.0,
                mean_age_total_years=70.0,
                site_index_pine_m=22.0,
                latitude_deg=59.0,
                altitude_m=150.0,
                prop_pine=0.2,
                prop_spruce=0.7,
                prop_birch=0.1,
                near_coast=True,
            ),
        ),
        (
            TreeSpecies.Sweden.betula_pendula,
            "south",
            16.482520167538905,
            dict(
                diameter_cm=20.0,
                max_diameter_cm=35.0,
                mean_age_total_years=60.0,
                site_index_pine_m=18.0,
                latitude_deg=56.5,
                altitude_m=50.0,
                prop_pine=0.3,
                prop_spruce=0.2,
                prop_birch=0.5,
                south_east=True,
            ),
        ),
    ],
)
def test_soderberg_1992_height_stand_age_cases(species, part_of_sweden, expected, kwargs):
    out = soderberg_1992_height_stand_age_m(
        species=species, part_of_sweden=part_of_sweden, **kwargs
    )
    assert out == pytest.approx(expected, rel=1e-6)


@pytest.mark.parametrize(
    ("species", "part_of_sweden", "expected", "kwargs"),
    [
        (
            TreeSpecies.Sweden.pinus_sylvestris,
            "north",
            13.05522367022596,
            dict(
                diameter_cm=22.0,
                tree_age_bh_years=30.0,
                max_diameter_cm=40.0,
                stand_basal_area_m2_ha=25.0,
                dominant_species=TreeSpecies.Sweden.pinus_sylvestris,
                site_index_dominant_m=20.0,
                latitude_deg=60.0,
                altitude_m=100.0,
                prop_pine=0.6,
                prop_spruce=0.3,
                prop_birch=0.1,
                prop_beech=0.0,
            ),
        ),
        (
            TreeSpecies.Sweden.pinus_contorta,
            "north",
            13.621022004139869,
            dict(
                diameter_cm=22.0,
                tree_age_bh_years=30.0,
                max_diameter_cm=40.0,
                stand_basal_area_m2_ha=25.0,
                dominant_species=TreeSpecies.Sweden.pinus_sylvestris,
                site_index_dominant_m=20.0,
                latitude_deg=60.0,
                altitude_m=100.0,
                prop_pine=0.6,
                prop_spruce=0.3,
                prop_birch=0.1,
                prop_beech=0.0,
            ),
        ),
        (
            TreeSpecies.Sweden.picea_abies,
            "middle",
            18.70751866820671,
            dict(
                diameter_cm=25.0,
                tree_age_bh_years=35.0,
                max_diameter_cm=45.0,
                stand_basal_area_m2_ha=30.0,
                dominant_species=TreeSpecies.Sweden.picea_abies,
                site_index_dominant_m=24.0,
                latitude_deg=58.5,
                altitude_m=120.0,
                prop_pine=0.2,
                prop_spruce=0.7,
                prop_birch=0.1,
                prop_beech=0.0,
                near_coast=True,
                continental=True,
            ),
        ),
    ],
)
def test_soderberg_1992_height_tree_age_cases(species, part_of_sweden, expected, kwargs):
    out = soderberg_1992_height_tree_age_m(
        species=species, part_of_sweden=part_of_sweden, **kwargs
    )
    assert out == pytest.approx(expected, rel=1e-6)


def test_soderberg_1992_height_stand_age_ratio_clamp():
    base_kwargs = dict(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        diameter_cm=25.0,
        mean_age_total_years=80.0,
        site_index_pine_m=20.0,
        latitude_deg=60.0,
        altitude_m=100.0,
        prop_pine=0.6,
        prop_spruce=0.3,
        prop_birch=0.1,
        part_of_sweden="north",
    )
    out_clamped = soderberg_1992_height_stand_age_m(**base_kwargs, max_diameter_cm=20.0)
    out_equal = soderberg_1992_height_stand_age_m(**base_kwargs, max_diameter_cm=25.0)
    assert out_clamped == pytest.approx(out_equal, rel=1e-12)


def test_soderberg_1992_height_tree_age_age_clamp():
    base_kwargs = dict(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        diameter_cm=22.0,
        max_diameter_cm=40.0,
        stand_basal_area_m2_ha=25.0,
        dominant_species=TreeSpecies.Sweden.pinus_sylvestris,
        site_index_dominant_m=20.0,
        latitude_deg=60.0,
        altitude_m=100.0,
        prop_pine=0.6,
        prop_spruce=0.3,
        prop_birch=0.1,
        prop_beech=0.0,
        part_of_sweden="north",
    )
    out_age1 = soderberg_1992_height_tree_age_m(**base_kwargs, tree_age_bh_years=1.0)
    out_age2 = soderberg_1992_height_tree_age_m(**base_kwargs, tree_age_bh_years=2.0)
    assert out_age1 == pytest.approx(out_age2, rel=1e-12)
