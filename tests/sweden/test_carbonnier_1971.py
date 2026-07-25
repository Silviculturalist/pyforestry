import pytest

from pyforestry.base.helpers import Age, SiteIndexValue
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.siteindex.carbonnier_1971 import CarbonnierHeightModel


@pytest.fixture
def carbonnier_model():
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
