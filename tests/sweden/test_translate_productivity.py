import pytest

from pyforestry.base.helpers.primitives import Age, SiteIndexValue
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.site.enums import Sweden
from pyforestry.sweden.siteindex.translate import hagglund_1981_SI_to_productivity


def _make_si(value: float, ref_age: int = 100) -> SiteIndexValue:
    return SiteIndexValue(
        value,
        Age.TOTAL(ref_age),
        {TreeSpecies.Sweden.picea_abies},
        lambda: None,
    )


def test_invalid_reference_age():
    si = _make_si(25, ref_age=50)
    with pytest.raises(ValueError):
        hagglund_1981_SI_to_productivity(
            si,
            TreeSpecies.Sweden.picea_abies,
            Sweden.FieldLayer.BILBERRY,
            100,
            Sweden.County.GOTLAND,
        )


@pytest.mark.parametrize(
    "main_species, vegetation, county",
    [
        ("spruce", Sweden.FieldLayer.BILBERRY, Sweden.County.GOTLAND),
        (TreeSpecies.Sweden.picea_abies, "bad", Sweden.County.GOTLAND),
        (TreeSpecies.Sweden.picea_abies, Sweden.FieldLayer.BILBERRY, "bad"),
    ],
)
def test_input_type_errors(main_species, vegetation, county):
    si = _make_si(28)
    with pytest.raises(TypeError):
        hagglund_1981_SI_to_productivity(si, main_species, vegetation, 100, county)


def test_valid_productivity_positive():
    si = _make_si(28)
    prod = hagglund_1981_SI_to_productivity(
        si,
        TreeSpecies.Sweden.picea_abies,
        Sweden.FieldLayer.BILBERRY,
        100,
        Sweden.County.GOTLAND,
    )
    assert isinstance(prod, float) and prod > 0
