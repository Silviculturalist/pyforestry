import math

from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.blocks.elfving_1982 import (
    HuginCropTreeProbability,
    HuginMeanHeightModel,
    NyskogReconstruction,
    RegenerationType,
)


def test_hugin_mean_height_pine():
    age = 10.0
    site_index_pine = 20.0
    site_index_spruce = 24.0
    species = TreeSpecies.Sweden.pinus_sylvestris

    b0 = 7.0
    b1 = -0.57 + -0.05 * site_index_pine
    b2 = -0.28 + 0.0094 * site_index_pine
    ln_age = math.log(age)
    power = b0 + b1 * ln_age + b2 * ln_age**2
    expected = site_index_pine / (math.exp(power) + 1.0)
    expected = max(0.3, expected)

    result = HuginMeanHeightModel.mean_height(
        age_years=age,
        species=species,
        site_index_pine_m=site_index_pine,
        site_index_spruce_m=site_index_spruce,
    )

    assert math.isclose(result, expected, rel_tol=1e-9)


def test_hugin_mean_age_inverse():
    age = 15.0
    site_index_pine = 22.0
    site_index_spruce = 24.0
    species = TreeSpecies.Sweden.pinus_sylvestris
    height = HuginMeanHeightModel.mean_height(
        age_years=age,
        species=species,
        site_index_pine_m=site_index_pine,
        site_index_spruce_m=site_index_spruce,
    )
    age_back = HuginMeanHeightModel.mean_age(
        mean_height_m=height,
        species=species,
        site_index_pine_m=site_index_pine,
        site_index_spruce_m=site_index_spruce,
    )
    assert math.isclose(age_back, age, rel_tol=1e-6)


def test_crop_tree_probability_conifer():
    height = 2.0
    mean_height = 1.5
    conifer_per_100m2 = 10.0
    rec_stems = 1600.0

    hrel = height / mean_height
    hrel2 = hrel**2
    corr = math.sqrt(conifer_per_100m2 * (1600.0 / rec_stems))
    s = (
        0.7433
        + 1.4339 * hrel
        + -0.4902 * hrel2
        + -0.1070 * corr
        + -0.1097 * corr * hrel
        + 0.0587 * corr * hrel2
    )
    expected = math.sin(s) ** 2

    result = HuginCropTreeProbability.crop_tree_probability(
        height_m=height,
        mean_height_m=mean_height,
        conifer_stems_per_100m2=conifer_per_100m2,
        rec_stems_per_ha=rec_stems,
        coniferous=True,
    )
    assert math.isclose(result, expected, rel_tol=1e-9)


def test_nyskog_total_stems_step1():
    mean_height = 2.0
    q = 50.0
    ln_q = math.log(q)
    ln_si = math.log(20.0)
    under_dimension_prob = 0.5
    height_indicator_dm = max(15.0, 10.0 * mean_height)

    temp = (
        4.3328
        + -0.0076 * q
        + 1.2245 * ln_q
        + 0.0 * (mean_height * 10.0)
        + -0.2822 * math.log(mean_height * 10.0)
        + 0.0 * (q / height_indicator_dm)
        + 0.0 * ln_si
        + 0.1693 * 0
        + -0.1295 * 0
        + 0.1969 * (under_dimension_prob * ln_q)
    )
    expected = math.exp(temp) * 1.093 - 1.0

    result = NyskogReconstruction.total_stems(
        regeneration_type=RegenerationType.NATURAL,
        mean_height_main_m=mean_height,
        q=q,
        ln_q=ln_q,
        ln_si=ln_si,
        under_dimension_prob=under_dimension_prob,
        wet=0,
        dry=0,
        height_indicator_dm=height_indicator_dm,
        deterministic=True,
    )
    assert math.isclose(result, expected, rel_tol=1e-9)


def test_young_stand_quality_asinw_natural_matches_report():
    """Elfving 1982: W = sin^2(-0.11 + 1.671*asinslh - 0.583*asinslh^2), natural."""
    stocking_arcsine_radians = 2.4  # SLH linear predictor (= 2*asinslh)
    asinslh = 0.5 * stocking_arcsine_radians
    expected_asinw = -0.11 + 1.671 * asinslh + -0.583 * asinslh**2

    asinw = NyskogReconstruction.young_stand_quality_asinw(
        stocking_arcsine_radians=stocking_arcsine_radians,
        regeneration_type=RegenerationType.NATURAL,
    )
    assert math.isclose(asinw, expected_asinw, rel_tol=1e-12)

    # q = 100 * W, W = sin^2(asinw): straight from the report, no /200 round-trip.
    q = NyskogReconstruction.production_potential_q(asinw)
    assert math.isclose(q, 100.0 * math.sin(expected_asinw) ** 2, rel_tol=1e-12)


def test_young_stand_quality_asinw_cultivation_matches_report():
    """Elfving 1982 cultivation W, incl. the deterministic -0.031*NS latitude dummy."""
    stocking_arcsine_radians = 2.4
    asinslh = 0.5 * stocking_arcsine_radians
    base = -0.058 + 1.380 * asinslh + -0.315 * asinslh**2

    # NS = 0 for latitude <= 60 N.
    south = NyskogReconstruction.young_stand_quality_asinw(
        stocking_arcsine_radians=stocking_arcsine_radians,
        regeneration_type=RegenerationType.SPRUCE_PLANTATION,
        latitude_deg=59.0,
    )
    assert math.isclose(south, base, rel_tol=1e-12)

    # NS = 1 for latitude > 60 N applies the -0.031 term.
    north = NyskogReconstruction.young_stand_quality_asinw(
        stocking_arcsine_radians=stocking_arcsine_radians,
        regeneration_type=RegenerationType.SPRUCE_PLANTATION,
        latitude_deg=61.0,
    )
    assert math.isclose(north, base + -0.031, rel_tol=1e-12)

    # Natural regeneration has no NS term regardless of latitude.
    natural_south = NyskogReconstruction.young_stand_quality_asinw(
        stocking_arcsine_radians=stocking_arcsine_radians,
        regeneration_type=RegenerationType.NATURAL,
        latitude_deg=59.0,
    )
    natural_north = NyskogReconstruction.young_stand_quality_asinw(
        stocking_arcsine_radians=stocking_arcsine_radians,
        regeneration_type=RegenerationType.NATURAL,
        latitude_deg=61.0,
    )
    assert math.isclose(natural_south, natural_north, rel_tol=1e-12)


def test_production_potential_q_is_unscaled_arcsine():
    """q must be 100*sin^2(asinw) directly (guards against the old *200 / /200)."""
    for asinw in (0.2, 0.8, 1.2):
        assert math.isclose(
            NyskogReconstruction.production_potential_q(asinw),
            100.0 * math.sin(asinw) ** 2,
            rel_tol=1e-12,
        )
