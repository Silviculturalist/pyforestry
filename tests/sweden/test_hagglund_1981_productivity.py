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


def test_branch_selection_middle_low_veg():
    si = _make_si(30)
    prod = hagglund_1981_SI_to_productivity(
        si,
        TreeSpecies.Sweden.picea_abies,
        Sweden.FieldLayer.THINLEAVED_GRASS,
        50,
        Sweden.County.VARMLAND,
    )
    assert math.isclose(prod, 11.795708953846153, rel_tol=1e-12)


def test_branch_selection_middle_high_veg():
    si = _make_si(25)
    prod = hagglund_1981_SI_to_productivity(
        si,
        TreeSpecies.Sweden.picea_abies,
        Sweden.FieldLayer.BILBERRY,
        50,
        Sweden.County.VARMLAND,
    )
    assert math.isclose(prod, 6.543171123076923, rel_tol=1e-12)


def test_branch_selection_north_low_veg():
    si = _make_si(28)
    prod = hagglund_1981_SI_to_productivity(
        si,
        TreeSpecies.Sweden.picea_abies,
        Sweden.FieldLayer.BROADLEAVED_GRASS,
        50,
        Sweden.County.VASTERBOTTENS_LAPPMARK,
    )
    assert math.isclose(prod, 7.069962648, rel_tol=1e-12)


def test_branch_selection_southern():
    si = _make_si(28)
    prod = hagglund_1981_SI_to_productivity(
        si,
        TreeSpecies.Sweden.picea_abies,
        Sweden.FieldLayer.BILBERRY,
        50,
        Sweden.County.SKARABORG,
    )
    assert math.isclose(prod, 10.019285878153845, rel_tol=1e-12)


def test_pine_low_altitude():
    si = SiteIndexValue(22, Age.TOTAL(100), {TreeSpecies.Sweden.pinus_sylvestris}, lambda: None)
    prod = hagglund_1981_SI_to_productivity(
        si,
        TreeSpecies.Sweden.pinus_sylvestris,
        Sweden.FieldLayer.LINGONBERRY,
        150,
        Sweden.County.NORRBOTTENS_KUSTLAND,
    )
    assert math.isclose(prod, 5.071651248, rel_tol=1e-12)


def test_invalid_types_raise():
    si = _make_si(28)
    with pytest.raises(TypeError):
        hagglund_1981_SI_to_productivity(
            si,
            "spruce",  # type: ignore[arg-type]
            Sweden.FieldLayer.BILBERRY,
            100,
            Sweden.County.VASTERBOTTENS_LAPPMARK,
        )
    with pytest.raises(TypeError):
        hagglund_1981_SI_to_productivity(
            si,
            TreeSpecies.Sweden.picea_abies,
            "bad",  # type: ignore[arg-type]
            100,
            Sweden.County.VASTERBOTTENS_LAPPMARK,
        )
    with pytest.raises(TypeError):
        hagglund_1981_SI_to_productivity(
            si,
            TreeSpecies.Sweden.picea_abies,
            Sweden.FieldLayer.BILBERRY,
            100,
            "nope",  # type: ignore[arg-type]
        )


def test_unrecognized_species_raises():
    si = _make_si(25)
    with pytest.raises(TypeError):
        hagglund_1981_SI_to_productivity(
            si,
            TreeSpecies.Sweden.fagus_sylvatica,
            Sweden.FieldLayer.BILBERRY,
            50,
            Sweden.County.SKARABORG,
        )
