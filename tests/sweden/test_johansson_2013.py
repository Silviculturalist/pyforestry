import pytest

from pyforestry.base.helpers import Age, SiteIndexValue
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.siteindex.johansson_2013 import (
    johansson_2013_height_trajectory_sweden_beech,
    johansson_2013_height_trajectory_sweden_larch,
)


@pytest.mark.parametrize(
    "fn,age,age2,species",
    [
        (
            johansson_2013_height_trajectory_sweden_beech,
            15,
            30,
            TreeSpecies.Sweden.fagus_sylvatica,
        ),
        (
            johansson_2013_height_trajectory_sweden_beech,
            30,
            160,
            TreeSpecies.Sweden.fagus_sylvatica,
        ),
        (
            johansson_2013_height_trajectory_sweden_larch,
            5,
            30,
            TreeSpecies.Sweden.larix_sibirica,
        ),
        (
            johansson_2013_height_trajectory_sweden_larch,
            50,
            110,
            TreeSpecies.Sweden.larix_sibirica,
        ),
    ],
)
def test_johansson_2013_models_warn_and_species(fn, age, age2, species):
    """Verify warnings outside recommended ages and returned species."""
    with pytest.warns(UserWarning):
        result = fn(15.0, Age.TOTAL(age), Age.TOTAL(age2))
    assert isinstance(result, SiteIndexValue)
    assert result.species == {species}
    assert result.reference_age == Age.TOTAL(age2)
    assert float(result) > 0
