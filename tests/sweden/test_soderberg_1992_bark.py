import warnings

import pytest

from pyforestry.base.helpers import Age, SiteIndexValue
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.bark.soderberg_1992 import soderberg_1992_bark_thickness_bh_mm
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970


@pytest.mark.parametrize(
    ("species", "part_of_sweden", "latitude_deg", "expected"),
    [
        (
            TreeSpecies.Sweden.pinus_sylvestris,
            "north",
            60.0,
            29.221847707621034,
        ),
        (
            TreeSpecies.Sweden.picea_abies,
            "middle",
            60.0,
            16.257247640484316,
        ),
        (
            TreeSpecies.Sweden.betula_pubescens,
            "south",
            57.0,
            29.38990743311758,
        ),
    ],
)
def test_soderberg_1992_bark_thickness_cases(species, part_of_sweden, latitude_deg, expected):
    out = soderberg_1992_bark_thickness_bh_mm(
        species=species,
        diameter_cm=25.0,
        max_diameter_cm=40.0,
        mean_age_total_years=80.0,
        site_index_pine_m=20.0,
        latitude_deg=latitude_deg,
        altitude_m=100.0,
        prop_pine=0.6,
        prop_spruce=0.3,
        prop_birch=0.1,
        part_of_sweden=part_of_sweden,
    )
    assert out == pytest.approx(expected, rel=1e-6)


def test_soderberg_1992_bark_warnings():
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        soderberg_1992_bark_thickness_bh_mm(
            species=TreeSpecies.Sweden.pinus_sylvestris,
            diameter_cm=25.0,
            max_diameter_cm=40.0,
            mean_age_total_years=80.0,
            site_index_pine_m=20.0,
            latitude_deg=75.0,
            altitude_m=100.0,
            prop_pine=1.2,
            prop_spruce=-0.1,
            prop_birch=0.5,
            part_of_sweden="north",
        )
    messages = [str(w.message) for w in rec]
    assert any("latitude_deg" in msg for msg in messages)
    assert any("prop_pine" in msg for msg in messages)
    assert any("prop_spruce" in msg for msg in messages)


def test_soderberg_1992_bark_invalid_inputs():
    base_kwargs = dict(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        diameter_cm=25.0,
        max_diameter_cm=40.0,
        mean_age_total_years=80.0,
        site_index_pine_m=20.0,
        latitude_deg=60.0,
        altitude_m=100.0,
        prop_pine=0.6,
        prop_spruce=0.3,
        prop_birch=0.1,
        part_of_sweden="north",
    )
    with pytest.raises(ValueError):
        soderberg_1992_bark_thickness_bh_mm(**{**base_kwargs, "diameter_cm": -1.0})
    with pytest.raises(ValueError):
        soderberg_1992_bark_thickness_bh_mm(**{**base_kwargs, "max_diameter_cm": 0.0})


def test_soderberg_1992_bark_accepts_site_index_value():
    pine_site_index = SiteIndexValue(
        20.0,
        reference_age=Age.TOTAL(100),
        species={TreeSpecies.Sweden.pinus_sylvestris},
        fn=Hagglund_1970.height_trajectory.pinus_sylvestris.sweden,
    )
    out = soderberg_1992_bark_thickness_bh_mm(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        diameter_cm=25.0,
        max_diameter_cm=40.0,
        mean_age_total_years=80.0,
        site_index_pine_m=pine_site_index,
        latitude_deg=60.0,
        altitude_m=100.0,
        prop_pine=0.6,
        prop_spruce=0.3,
        prop_birch=0.1,
        part_of_sweden="north",
    )
    assert out == pytest.approx(29.221847707621034, rel=1e-6)


def test_soderberg_1992_bark_rejects_non_pine_site_index_value():
    spruce_site_index = SiteIndexValue(
        20.0,
        reference_age=Age.TOTAL(100),
        species={TreeSpecies.Sweden.picea_abies},
        fn=Hagglund_1970.height_trajectory.picea_abies.northern_sweden,
    )
    with pytest.raises(ValueError, match="site_index_pine_m\\.species"):
        soderberg_1992_bark_thickness_bh_mm(
            species=TreeSpecies.Sweden.pinus_sylvestris,
            diameter_cm=25.0,
            max_diameter_cm=40.0,
            mean_age_total_years=80.0,
            site_index_pine_m=spruce_site_index,
            latitude_deg=60.0,
            altitude_m=100.0,
            prop_pine=0.6,
            prop_spruce=0.3,
            prop_birch=0.1,
            part_of_sweden="north",
        )
