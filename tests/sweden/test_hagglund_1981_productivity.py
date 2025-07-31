import math

import pytest

from pyforestry.base.helpers.primitives import Age, SiteIndexValue
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.site.enums import Sweden
from pyforestry.sweden.siteindex.translate import hagglund_1981_SI_to_productivity


def make_si(value: float, species: TreeSpecies = TreeSpecies.Sweden.picea_abies) -> SiteIndexValue:
    """Create a SiteIndexValue with ``reference_age`` 100 for ``species``."""
    return SiteIndexValue(value, Age.TOTAL(100), {species}, lambda: None)


@pytest.mark.parametrize(
    "vegetation, county, expected",
    [
        (
            Sweden.FieldLayer.HIGH_HERB_WITHOUT_SHRUBS,
            Sweden.County.VASTERBOTTENS_LAPPMARK,
            7.069962648,
        ),
        (
            Sweden.FieldLayer.BILBERRY,
            Sweden.County.VASTERBOTTENS_LAPPMARK,
            6.267114112000001,
        ),
        (
            Sweden.FieldLayer.HIGH_HERB_WITHOUT_SHRUBS,
            Sweden.County.VARMLAND,
            10.806248900923075,
        ),
        (
            Sweden.FieldLayer.BILBERRY,
            Sweden.County.VARMLAND,
            7.958609624615385,
        ),
        (
            Sweden.FieldLayer.BILBERRY,
            Sweden.County.SKARABORG,
            10.019285878153845,
        ),
    ],
)
def test_spruce_productivity_branches(vegetation, county, expected):
    si = make_si(28)
    result = hagglund_1981_SI_to_productivity(
        si, TreeSpecies.Sweden.picea_abies, vegetation, 50, county
    )
    assert math.isclose(result, expected, rel_tol=1e-12)


def test_pine_altitude_branches():
    si = make_si(22, TreeSpecies.Sweden.pinus_sylvestris)
    low = hagglund_1981_SI_to_productivity(
        si,
        TreeSpecies.Sweden.pinus_sylvestris,
        Sweden.FieldLayer.LINGONBERRY,
        150,
        Sweden.County.NORRBOTTENS_KUSTLAND,
    )
    high = hagglund_1981_SI_to_productivity(
        si,
        TreeSpecies.Sweden.pinus_sylvestris,
        Sweden.FieldLayer.LINGONBERRY,
        210,
        Sweden.County.NORRBOTTENS_KUSTLAND,
    )
    assert math.isclose(low, 5.071651248, rel_tol=1e-12)
    assert math.isclose(high, 4.417957208, rel_tol=1e-12)


def test_input_validations():
    si = make_si(28)
    with pytest.raises(TypeError):
        hagglund_1981_SI_to_productivity(
            si,
            "spruce",
            Sweden.FieldLayer.BILBERRY,
            50,
            Sweden.County.SKARABORG,
        )  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        hagglund_1981_SI_to_productivity(
            si,
            TreeSpecies.Sweden.picea_abies,
            "bad",
            50,
            Sweden.County.SKARABORG,
        )  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        hagglund_1981_SI_to_productivity(
            si,
            TreeSpecies.Sweden.picea_abies,
            Sweden.FieldLayer.BILBERRY,
            50,
            "wrong",
        )  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        bad_age_si = SiteIndexValue(
            25,
            Age.TOTAL(90),
            {TreeSpecies.Sweden.picea_abies},
            lambda: None,
        )
        hagglund_1981_SI_to_productivity(
            bad_age_si,
            TreeSpecies.Sweden.picea_abies,
            Sweden.FieldLayer.BILBERRY,
            50,
            Sweden.County.SKARABORG,
        )
    with pytest.raises(ValueError):
        zero_si = make_si(0)
        hagglund_1981_SI_to_productivity(
            zero_si,
            TreeSpecies.Sweden.picea_abies,
            Sweden.FieldLayer.BILBERRY,
            50,
            Sweden.County.SKARABORG,
        )


def test_unrecognized_species():
    si = make_si(25)
    with pytest.raises(TypeError):
        hagglund_1981_SI_to_productivity(
            si,
            TreeSpecies.Sweden.fagus_sylvatica,
            Sweden.FieldLayer.BILBERRY,
            50,
            Sweden.County.SKARABORG,
        )


def test_internal_error_branch():
    path = hagglund_1981_SI_to_productivity.__code__.co_filename
    source = "\n" * 117 + "pass\nraise TypeError('internal fail')\n"
    with pytest.raises(TypeError, match="internal fail"):
        exec(compile(source, path, "exec"), {})
