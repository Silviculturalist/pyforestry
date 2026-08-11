import math

import pytest

from pyforestry.base.helpers import Age, SiteIndexValue
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.misc import age_to_breast_height_elfving_years, dominant_mean_diameter_cm
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970


def test_age_to_bh_spruce_formula():
    age = age_to_breast_height_elfving_years(
        site_index_m=20.0,
        latitude_deg=60.0,
        species=TreeSpecies.Sweden.picea_abies,
    )
    expected = 37.0 - 0.605 * 60.0 - 1121.0 / 20.0 + 21.92 * 60.0 / 20.0 + 29.5 * 1.0 / 20.0
    assert age == pytest.approx(expected)


def test_age_to_bh_broadleaf_uses_150_over_si():
    age = age_to_breast_height_elfving_years(
        site_index_m=18.0,
        latitude_deg=60.0,
        species=TreeSpecies.Sweden.betula_pendula,
    )
    assert age == pytest.approx(150.0 / 18.0)


def test_age_to_bh_contorta_adjusts_site_index():
    age = age_to_breast_height_elfving_years(
        site_index_m=20.0,
        latitude_deg=60.0,
        species=TreeSpecies.Sweden.pinus_contorta,
    )
    expected = 37.0 - 0.605 * 60.0 - 1121.0 / 23.0 + 21.92 * 60.0 / 23.0 + 29.5 * 0.0 / 23.0
    assert age == pytest.approx(expected)


def test_age_to_bh_accepts_site_index_value():
    pine_site_index = SiteIndexValue(
        20.0,
        reference_age=Age.TOTAL(100),
        species={TreeSpecies.Sweden.pinus_sylvestris},
        fn=Hagglund_1970.height_trajectory.pinus_sylvestris.sweden,
    )
    age = age_to_breast_height_elfving_years(
        site_index_m=pine_site_index,
        latitude_deg=60.0,
        species=TreeSpecies.Sweden.picea_abies,
    )
    expected = 37.0 - 0.605 * 60.0 - 1121.0 / 20.0 + 21.92 * 60.0 / 20.0 + 29.5 * 1.0 / 20.0
    assert age == pytest.approx(expected)


def test_age_to_bh_rejects_non_hagglund_site_index_value():
    invalid_site_index = SiteIndexValue(
        20.0,
        reference_age=Age.TOTAL(100),
        species={TreeSpecies.Sweden.pinus_sylvestris},
        fn=lambda *_: None,
    )
    with pytest.raises(ValueError, match="site_index_m\\.fn"):
        age_to_breast_height_elfving_years(
            site_index_m=invalid_site_index,
            latitude_deg=60.0,
            species=TreeSpecies.Sweden.picea_abies,
        )


def test_dominant_mean_diameter():
    dm = dominant_mean_diameter_cm(
        mean_age_total_years=50.0,
        field_estimated_basal_area_m2_ha=20.0,
        site_index_m=25.0,
    )
    expected = math.exp(
        -0.92313
        + 1.00322 * math.log(50.0)
        + -0.00701 * 50.0
        + -4.00529 * (1.0 / 25.0)
        + 0.01859 * 25.0
        + -1.88177 * (1.0 / (1.0 + 20.0))
        + 0.036
    )
    assert dm == pytest.approx(expected)
