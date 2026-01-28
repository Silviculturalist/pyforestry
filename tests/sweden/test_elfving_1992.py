import math

import pytest

from pyforestry.sweden.models.elfving_1992 import elfving_1992_regeneration
from pyforestry.sweden.site.enums import Sweden


def test_slh_natural_basic():
    lat = 60.0
    alt = 100.0
    age_years = 12.0
    n_full = 2500.0
    prop_cultivated = 0.1
    seed_trees = 50.0
    regen_area = 1.5
    jonsbon = 4.0

    asinslh, slh_est, slh_corr = elfving_1992_regeneration.slh_natural(
        latitude_deg=lat,
        altitude_m=alt,
        county=None,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        jonsbon=jonsbon,
        age_years=age_years,
        n_full=n_full,
        prop_cultivated=prop_cultivated,
        seed_trees_per_ha=seed_trees,
        regen_area_ha=regen_area,
        scarified=True,
    )

    age_f = 2.0 * (1.0 / (1.0 + math.exp(-0.3 * age_years))) ** -0.5
    map_number = (lat * 111.1 - 6050.0) / 50.0
    invarea = 1.0 / regen_area
    north = 1
    dry = 0
    moist = 0
    scarif_coeff = 0.30

    n_full_thousands = n_full / 1000.0
    expected_lp = (
        1.7413
        + (-0.0163) * (alt / 100.0) ** 2 * north
        + 0.6863 * age_f
        + 0.6663 * prop_cultivated
        + (-0.1500) * n_full_thousands
        + 0.0218 * map_number * dry
        + 0.2702 * moist
        + scarif_coeff * 1
        + 0.1596 * seed_trees
        + (-0.0379) * jonsbon
        + 0.1888 * invarea
        + 0.1075 * north
        + (-0.00619) * map_number
    )
    expected_slh_est = math.sin(expected_lp / 2.0) ** 2
    expected_slh_corr = 0.056 + 0.887 * expected_slh_est
    expected_slh_corr = max(0.0, min(1.0, expected_slh_corr))

    assert math.isclose(asinslh, expected_lp, rel_tol=1e-9)
    assert math.isclose(slh_est, expected_slh_est, rel_tol=1e-9)
    assert math.isclose(slh_corr, expected_slh_corr, rel_tol=1e-9)


def test_slh_natural_scarif_adjustment():
    base_kwargs = dict(
        latitude_deg=60.0,
        altitude_m=100.0,
        county=None,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        jonsbon=4.0,
        scarified=True,
    )

    lp_adjusted = elfving_1992_regeneration.slh_natural(**base_kwargs)[0]
    lp_original = elfving_1992_regeneration.slh_natural(
        **base_kwargs, use_adjusted_coeffs=False
    )[0]

    assert math.isclose(lp_adjusted - lp_original, 0.30 - 0.2692, rel_tol=1e-9)


def test_slh_natural_requires_jonson_input():
    with pytest.raises(ValueError):
        elfving_1992_regeneration.slh_natural(
            latitude_deg=60.0,
            altitude_m=100.0,
            county=None,
            soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        )


def test_slh_cultivated_basic():
    lat = 58.0
    alt = 200.0
    jonsbon = 3.0
    age_years = 12.0
    n_full = 2500.0
    spacing = 2.0

    asinslh, slh_est, slh_corr = elfving_1992_regeneration.slh_cultivated(
        latitude_deg=lat,
        altitude_m=alt,
        county=Sweden.County.OREBRO,
        jonsbon=jonsbon,
        age_years=age_years,
        n_full=n_full,
        spacing_m=spacing,
        scarified=True,
        sown=True,
    )

    map_number = (lat * 111.1 - 6050.0) / 50.0
    invmap = 1.0 / map_number
    invage = 1.0 / age_years
    north = 0

    n_full_thousands = n_full / 1000.0
    expected_lp = (
        3.0707
        + 0.4358 * invage
        + (-0.0614) * jonsbon
        + (-0.3591) * spacing
        + 0.2 * 1
        + (-0.0675) * 1
        + 4.7901 * invmap
        + 0.2178 * 1
        + (-0.1500) * n_full_thousands
    )

    expected_slh_est = math.sin(expected_lp / 2.0) ** 2
    expected_slh_corr = 0.037 + 0.926 * expected_slh_est
    expected_slh_corr = max(0.0, min(1.0, expected_slh_corr))

    assert math.isclose(asinslh, expected_lp, rel_tol=1e-9)
    assert math.isclose(slh_est, expected_slh_est, rel_tol=1e-9)
    assert math.isclose(slh_corr, expected_slh_corr, rel_tol=1e-9)


def test_slh_cultivated_spacing_from_plants():
    base_kwargs = dict(
        latitude_deg=58.0,
        altitude_m=200.0,
        county=Sweden.County.OREBRO,
        jonsbon=3.0,
        age_years=12.0,
        n_full=2.5,
        scarified=True,
    )

    lp_spacing = elfving_1992_regeneration.slh_cultivated(
        **base_kwargs,
        spacing_m=2.0,
    )[0]
    lp_plants = elfving_1992_regeneration.slh_cultivated(
        **base_kwargs,
        spacing_m=None,
        no_of_plants=2500.0,
    )[0]

    assert math.isclose(lp_spacing, lp_plants, rel_tol=1e-9)


def test_slh_cultivated_requires_spacing():
    with pytest.raises(ValueError):
        elfving_1992_regeneration.slh_cultivated(
            latitude_deg=58.0,
            altitude_m=200.0,
            county=Sweden.County.OREBRO,
            jonsbon=3.0,
        )
