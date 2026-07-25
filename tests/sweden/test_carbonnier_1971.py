import pytest

from pyforestry.base.helpers import Age, SiteIndexValue
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.siteindex.carbonnier_1971 import (
    CARBONNIER_1971_BEECH_HEIGHT_TABLE,
    CARBONNIER_1971_MAX_TOTAL_AGE,
    CarbonnierHeightModel,
    carbonnier_1971_beech_height_model,
)


@pytest.fixture
def carbonnier_model():
    """Synthetic coefficients, for exercising the class mechanics only.

    Round numbers keep the interpolation/validation assertions readable. The
    published Carbonnier (1971) coefficients are asserted separately below.
    """
    return CarbonnierHeightModel(
        ages=[10, 20, 30],
        a_vals=[5.0, 7.0, 9.0],
        b_vals=[1.0, 1.2, 1.5],
    )


def test_height_from_site_index_with_primitives(carbonnier_model):
    site_index = SiteIndexValue(
        10.0,
        reference_age=Age.TOTAL(20),
        species={TreeSpecies.Sweden.fagus_sylvatica},
        fn=lambda *_: None,
    )

    result = carbonnier_model.height_from_SI(Age.TOTAL(15), site_index, si_age=Age.TOTAL(20))

    assert isinstance(result, SiteIndexValue)
    assert result.reference_age == Age.TOTAL(15)
    assert result.species == {TreeSpecies.Sweden.fagus_sylvatica}
    assert pytest.approx(float(result)) == 8.75


def test_site_index_from_height_roundtrip(carbonnier_model):
    site_index = carbonnier_model.site_index_from_height(
        height=8.75,
        measurement_age=Age.TOTAL(15),
        si_age=Age.TOTAL(20),
    )

    assert isinstance(site_index, SiteIndexValue)
    assert site_index.reference_age == Age.TOTAL(20)
    assert pytest.approx(float(site_index)) == 10.0


def test_height_from_site_index_requires_total_age(carbonnier_model):
    with pytest.raises(TypeError):
        carbonnier_model.height_from_SI(Age.DBH(15), 10.0, si_age=Age.TOTAL(20))


def test_height_from_site_index_outside_range(carbonnier_model):
    with pytest.raises(ValueError):
        carbonnier_model.height_from_SI(5, 10.0, si_age=Age.TOTAL(20), interpolate=False)


def test_height_from_site_index_negative_age(carbonnier_model):
    with pytest.raises(ValueError):
        carbonnier_model.height_from_SI(-1, 10.0, si_age=Age.TOTAL(20))


def test_site_index_reference_age_mismatch(carbonnier_model):
    site_index = SiteIndexValue(
        10.0,
        reference_age=Age.TOTAL(25),
        species={TreeSpecies.Sweden.fagus_sylvatica},
        fn=lambda *_: None,
    )

    with pytest.raises(ValueError):
        carbonnier_model.height_from_SI(15, site_index, si_age=Age.TOTAL(20))


# ---------------------------------------------------------------------------
# Published coefficients: Carbonnier (1971) Appendix IV, Table IV.1
# ---------------------------------------------------------------------------


def test_table_iv1_shape_and_endpoints():
    """The table is the published 5-year grid from 10 to 135 years."""
    ages = [age for age, _, _ in CARBONNIER_1971_BEECH_HEIGHT_TABLE]
    assert ages == [float(a) for a in range(10, 140, 5)]
    assert len(CARBONNIER_1971_BEECH_HEIGHT_TABLE) == 26
    assert ages[-1] == CARBONNIER_1971_MAX_TOTAL_AGE

    # First and last rows, straight off Table IV.1.
    assert CARBONNIER_1971_BEECH_HEIGHT_TABLE[0] == (10.0, 1.4027, 0.0115)
    assert CARBONNIER_1971_BEECH_HEIGHT_TABLE[-1] == (135.0, 29.8202, 0.2015)


def test_table_iv1_is_monotone_in_both_sequences():
    """Both {a_j} and {b_j} increase with age throughout the published range."""
    a_vals = [a for _, a, _ in CARBONNIER_1971_BEECH_HEIGHT_TABLE]
    b_vals = [b for _, _, b in CARBONNIER_1971_BEECH_HEIGHT_TABLE]
    assert a_vals == sorted(a_vals)
    assert b_vals == sorted(b_vals)


def test_reference_row_at_age_100():
    """Age 100 is the site-index reference row and must match the paper exactly."""
    row = next(r for r in CARBONNIER_1971_BEECH_HEIGHT_TABLE if r[0] == 100.0)
    assert row == (100.0, 27.4955, 0.1861)


def test_tau_zero_reproduces_the_mean_curve():
    """tau = 0 is Matern's average height development, i.e. h_j == a_j."""
    model = carbonnier_1971_beech_height_model()
    for age, a_val, _ in CARBONNIER_1971_BEECH_HEIGHT_TABLE:
        height = model.site_index_from_height(
            height=27.4955,  # h100 == a100 => tau == 0
            measurement_age=Age.TOTAL(100),
            si_age=Age.TOTAL(age),
        )
        assert float(height) == pytest.approx(a_val)


def test_published_model_roundtrip_bok_28():
    """A Bok 28 stand read at age 50 returns to H100 = 28 m.

    tau = (28 - 27.4955) / 0.1861 = 2.71091, so
    h50 = 16.5755 + 2.71091 * 0.1131 = 16.8821 m.
    """
    model = carbonnier_1971_beech_height_model()
    tau = (28.0 - 27.4955) / 0.1861
    h50 = 16.5755 + tau * 0.1131
    assert h50 == pytest.approx(16.8821, abs=1e-4)

    site_index = model.site_index_from_height(
        height=h50,
        measurement_age=Age.TOTAL(50),
        si_age=Age.TOTAL(100),
    )
    assert float(site_index) == pytest.approx(28.0)
    assert site_index.species == {TreeSpecies.Sweden.fagus_sylvatica}


def test_published_model_refuses_extrapolation_past_135_years():
    """Appendix IV: the curves must never be extrapolated above 135 years."""
    model = carbonnier_1971_beech_height_model()
    with pytest.raises(ValueError, match="outside coefficient range"):
        model.site_index_from_height(
            height=16.8821,
            measurement_age=Age.TOTAL(50),
            si_age=Age.TOTAL(CARBONNIER_1971_MAX_TOTAL_AGE + 5),
        )


def test_site_classes_stay_ordered_across_the_age_range():
    """Bok 16/20/24/28/32 keep their ordering at every tabulated age."""
    model = carbonnier_1971_beech_height_model()
    for age, _, _ in CARBONNIER_1971_BEECH_HEIGHT_TABLE:
        heights = [
            float(
                model.site_index_from_height(
                    height=float(si),
                    measurement_age=Age.TOTAL(100),
                    si_age=Age.TOTAL(age),
                )
            )
            for si in (16, 20, 24, 28, 32)
        ]
        assert heights == sorted(heights)
