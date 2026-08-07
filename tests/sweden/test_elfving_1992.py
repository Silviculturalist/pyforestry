import math

import pytest

from pyforestry.base.helpers import Age, SiteIndexValue, TreeSpecies
from pyforestry.sweden.regeneration.elfving_1992 import Elfving1992Regeneration
from pyforestry.sweden.site.enums import Sweden
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970


def test_slh_natural_basic():
    lat = 60.0
    alt = 100.0
    age_years = 12.0
    n_full = 2500.0
    prop_cultivated = 0.1
    seed_trees = 50.0
    regen_area = 1.5
    jonson_index = 4.0

    asinslh, slh_est, slh_corr = Elfving1992Regeneration.slh_natural(
        latitude_deg=lat,
        altitude_m=alt,
        county=None,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        jonson_index=jonson_index,
        age_years=age_years,
        n_full=n_full,
        prop_cultivated=prop_cultivated,
        seed_trees_per_ha=seed_trees,
        regen_area_ha=regen_area,
        scarified=True,
    )

    age_f = 2.0 * (1.0 / (1.0 + math.exp(-0.3 * age_years)) - 0.5)  # = tanh(0.15 * age)
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
        + 0.1596 * (seed_trees / 100.0)
        + (-0.0379) * jonson_index
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
        jonson_index=4.0,
        scarified=True,
    )

    lp_adjusted = Elfving1992Regeneration.slh_natural(**base_kwargs)[0]
    lp_original = Elfving1992Regeneration.slh_natural(**base_kwargs, use_adjusted_coeffs=False)[0]

    assert math.isclose(lp_adjusted - lp_original, 0.30 - 0.2692, rel_tol=1e-9)


def test_slh_natural_requires_jonson_input():
    with pytest.raises(ValueError):
        Elfving1992Regeneration.slh_natural(
            latitude_deg=60.0,
            altitude_m=100.0,
            county=None,
            soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        )


def test_slh_natural_rejects_non_hagglund_h100_input():
    invalid_h100 = SiteIndexValue(
        20.0,
        reference_age=Age.TOTAL(100),
        species={TreeSpecies.Sweden.pinus_sylvestris},
        fn=lambda *_: None,
    )
    with pytest.raises(ValueError, match="h100_input\\.fn"):
        Elfving1992Regeneration.slh_natural(
            latitude_deg=60.0,
            altitude_m=100.0,
            county=Sweden.County.VARMLAND,
            soil_moisture=Sweden.SoilMoistureEnum.MESIC,
            h100_input=invalid_h100,
            main_species=TreeSpecies.Sweden.pinus_sylvestris,
            vegetation=Sweden.FieldLayer.BILBERRY,
        )


def test_slh_cultivated_basic():
    lat = 58.0
    alt = 200.0
    jonson_index = 3.0
    age_years = 12.0
    n_full = 2500.0
    spacing = 2.0

    asinslh, slh_est, slh_corr = Elfving1992Regeneration.slh_cultivated(
        latitude_deg=lat,
        altitude_m=alt,
        county=Sweden.County.OREBRO,
        jonson_index=jonson_index,
        age_years=age_years,
        n_full=n_full,
        spacing_m=spacing,
        scarified=True,
        sown=True,
    )

    map_number = (lat * 111.1 - 6050.0) / 50.0
    invmap = 1.0 / map_number
    invage = 1.0 / age_years

    n_full_thousands = n_full / 1000.0
    expected_lp = (
        3.0707
        + 0.4358 * invage
        + (-0.0614) * jonson_index
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
        jonson_index=3.0,
        age_years=12.0,
        n_full=2.5,
        scarified=True,
    )

    lp_spacing = Elfving1992Regeneration.slh_cultivated(
        **base_kwargs,
        spacing_m=2.0,
    )[0]
    lp_plants = Elfving1992Regeneration.slh_cultivated(
        **base_kwargs,
        spacing_m=None,
        plant_count_per_ha=2500.0,
    )[0]

    assert math.isclose(lp_spacing, lp_plants, rel_tol=1e-9)


def test_slh_cultivated_requires_spacing():
    with pytest.raises(ValueError):
        Elfving1992Regeneration.slh_cultivated(
            latitude_deg=58.0,
            altitude_m=200.0,
            county=Sweden.County.OREBRO,
            jonson_index=3.0,
        )


def test_slh_natural_validates_range_inputs() -> None:
    kwargs = dict(
        latitude_deg=60.0,
        altitude_m=100.0,
        county=Sweden.County.VARMLAND,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        jonson_index=4.0,
    )
    with pytest.raises(ValueError, match="prop_cultivated"):
        Elfving1992Regeneration.slh_natural(**kwargs, prop_cultivated=1.1)
    with pytest.raises(ValueError, match="seed_trees_per_ha"):
        Elfving1992Regeneration.slh_natural(**kwargs, seed_trees_per_ha=-1.0)
    with pytest.raises(ValueError, match="n_full must be >= 0"):
        Elfving1992Regeneration.slh_natural(**kwargs, n_full=-0.1)


def test_slh_natural_can_derive_jonson_index_from_h100() -> None:
    h100_input = SiteIndexValue(
        20.0,
        reference_age=Age.TOTAL(100),
        species={TreeSpecies.Sweden.pinus_sylvestris},
        fn=Hagglund_1970.height_trajectory.pinus_sylvestris.sweden,
    )
    asinslh, slh_est, slh_corr = Elfving1992Regeneration.slh_natural(
        latitude_deg=60.0,
        altitude_m=120.0,
        county=Sweden.County.VARMLAND,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        h100_input=h100_input,
        main_species=TreeSpecies.Sweden.pinus_sylvestris,
        vegetation=Sweden.FieldLayer.BILBERRY,
    )
    assert asinslh > 0.0
    assert 0.0 <= slh_est <= 1.0
    assert 0.0 <= slh_corr <= 1.0


def test_slh_cultivated_handles_invmap_zero_and_negative_nfull() -> None:
    with pytest.raises(ValueError, match="n_full must be >= 0"):
        Elfving1992Regeneration.slh_cultivated(
            latitude_deg=58.0,
            altitude_m=150.0,
            county=Sweden.County.OREBRO,
            jonson_index=3.0,
            spacing_m=2.2,
            n_full=-1.0,
        )

    asinslh, slh_est, slh_corr = Elfving1992Regeneration.slh_cultivated(
        latitude_deg=6050.0 / 111.1,
        altitude_m=150.0,
        county=Sweden.County.OREBRO,
        jonson_index=3.0,
        plant_count_per_ha=2500.0,
    )
    assert asinslh > 0.0
    assert 0.0 <= slh_est <= 1.0
    assert 0.0 <= slh_corr <= 1.0


def test_slh_natural_gotland_is_negative() -> None:
    """Gotland is a negative indicator in Table 1 (coefficient -0.7552).

    Regression against a sign that had drifted to +0.7552 in the (now removed)
    Appendix-2 duplicate: being on Gotland must lower the arcsine stocking by
    exactly the coefficient (Gotland is outside the SYZ and T-area groups).
    """
    common = dict(
        latitude_deg=57.5,
        altitude_m=30.0,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        jonson_index=4.0,
    )
    on_gotland = Elfving1992Regeneration.slh_natural(county=Sweden.County.GOTLAND, **common)[0]
    off_gotland = Elfving1992Regeneration.slh_natural(county=None, **common)[0]
    assert math.isclose(on_gotland - off_gotland, -0.7552, rel_tol=1e-9)
    on_est = Elfving1992Regeneration.slh_natural(county=Sweden.County.GOTLAND, **common)[1]
    off_est = Elfving1992Regeneration.slh_natural(county=None, **common)[1]
    assert on_est < off_est
