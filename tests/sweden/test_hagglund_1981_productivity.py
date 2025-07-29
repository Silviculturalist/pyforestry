import math

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


def test_valid_productivity_spruce():
    si = _make_si(28)
    prod = hagglund_1981_SI_to_productivity(
        si,
        TreeSpecies.Sweden.picea_abies,
        Sweden.FieldLayer.BILBERRY,
        100,
        Sweden.County.VASTERBOTTENS_LAPPMARK,
    )
    assert math.isclose(prod, 10.019285878153845, rel_tol=1e-12)


def test_valid_productivity_pine():
    si = SiteIndexValue(22, Age.TOTAL(100), {TreeSpecies.Sweden.pinus_sylvestris}, lambda: None)
    prod = hagglund_1981_SI_to_productivity(
        si,
        TreeSpecies.Sweden.pinus_sylvestris,
        Sweden.FieldLayer.LINGONBERRY,
        210,
        Sweden.County.NORRBOTTENS_KUSTLAND,
    )
    assert math.isclose(prod, 5.071651248, rel_tol=1e-12)


def test_reference_age_not_h100_raises():
    si = _make_si(25, ref_age=90)
    with pytest.raises(ValueError):
        hagglund_1981_SI_to_productivity(
            si,
            TreeSpecies.Sweden.picea_abies,
            Sweden.FieldLayer.BILBERRY,
            100,
            Sweden.County.VASTERBOTTENS_LAPPMARK,
        )


def test_zero_h100_raises():
    si = _make_si(0)
    with pytest.raises(ValueError):
        hagglund_1981_SI_to_productivity(
            si,
            TreeSpecies.Sweden.picea_abies,
            Sweden.FieldLayer.BILBERRY,
            100,
            Sweden.County.VASTERBOTTENS_LAPPMARK,
        )
