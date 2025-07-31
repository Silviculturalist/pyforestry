import pytest

from pyforestry.base.helpers import Age, SiteIndexValue, TreeSpecies
from pyforestry.sweden.siteindex.elfving_kiviste_1997 import (
    elfving_kiviste_1997_height_trajectory_sweden_pine,
)
from pyforestry.sweden.siteindex.eriksson_1997 import (
    eriksson_1997_height_trajectory_sweden_birch,
)
from pyforestry.sweden.siteindex.hagglund_remrod_1977 import (
    hagglund_remrod_1977_height_trajectories_lodgepole_pine,
)
from pyforestry.sweden.siteindex.johansson_1996 import (
    johansson_1996_height_trajectory_sweden_aspen,
)
from pyforestry.sweden.siteindex.johansson_1999 import (
    johansson_1999_height_trajectory_sweden_alnus_glutinosa,
    johansson_1999_height_trajectory_sweden_alnus_incana,
)
from pyforestry.sweden.siteindex.johansson_2011 import (
    johansson_2011_height_trajectory_sweden_poplar,
)
from pyforestry.sweden.siteindex.johansson_2013 import (
    johansson_2013_height_trajectory_sweden_beech,
    johansson_2013_height_trajectory_sweden_hybrid_aspen,
    johansson_2013_height_trajectory_sweden_larch,
    johansson_2013_height_trajectory_sweden_oak,
)

# Functions grouped by required Age code
TOTAL_FUNCS = [
    elfving_kiviste_1997_height_trajectory_sweden_pine,
    johansson_1996_height_trajectory_sweden_aspen,
    johansson_1999_height_trajectory_sweden_alnus_glutinosa,
    johansson_1999_height_trajectory_sweden_alnus_incana,
    johansson_2011_height_trajectory_sweden_poplar,
    johansson_2013_height_trajectory_sweden_beech,
    johansson_2013_height_trajectory_sweden_hybrid_aspen,
    johansson_2013_height_trajectory_sweden_larch,
    johansson_2013_height_trajectory_sweden_oak,
]
DBH_FUNCS = [
    eriksson_1997_height_trajectory_sweden_birch,
    hagglund_remrod_1977_height_trajectories_lodgepole_pine,
]


@pytest.mark.parametrize(
    "fn,correct", [(f, Age.TOTAL) for f in TOTAL_FUNCS] + [(f, Age.DBH) for f in DBH_FUNCS]
)
def test_invalid_age_type(fn, correct):
    wrong = Age.DBH if correct is Age.TOTAL else Age.TOTAL
    with pytest.raises(TypeError):
        fn(15.0, wrong(20), wrong(40))


@pytest.mark.parametrize(
    "fn,age,age2",
    [
        (elfving_kiviste_1997_height_trajectory_sweden_pine, Age.TOTAL(5), Age.TOTAL(20)),
        (eriksson_1997_height_trajectory_sweden_birch, Age.DBH(5), Age.DBH(20)),
        (hagglund_remrod_1977_height_trajectories_lodgepole_pine, Age.DBH(14), Age.DBH(30)),
        (johansson_1996_height_trajectory_sweden_aspen, Age.TOTAL(70), Age.TOTAL(80)),
        (johansson_1999_height_trajectory_sweden_alnus_glutinosa, Age.TOTAL(101), Age.TOTAL(105)),
        (johansson_1999_height_trajectory_sweden_alnus_incana, Age.TOTAL(71), Age.TOTAL(80)),
        (johansson_2011_height_trajectory_sweden_poplar, Age.TOTAL(70), Age.TOTAL(80)),
        (johansson_2013_height_trajectory_sweden_beech, Age.TOTAL(10), Age.TOTAL(160)),
        (johansson_2013_height_trajectory_sweden_hybrid_aspen, Age.TOTAL(55), Age.TOTAL(60)),
        (johansson_2013_height_trajectory_sweden_larch, Age.TOTAL(5), Age.TOTAL(110)),
        (johansson_2013_height_trajectory_sweden_oak, Age.TOTAL(15), Age.TOTAL(160)),
    ],
)
def test_warning_out_of_range(fn, age, age2):
    with pytest.warns(UserWarning):
        res = fn(15.0, age, age2)
    assert float(res) > 0


def test_eriksson_type_errors():
    """Verify type checks for DBH ages."""
    with pytest.raises(TypeError):
        eriksson_1997_height_trajectory_sweden_birch(15.0, Age.TOTAL(20), Age.DBH(40))
    with pytest.raises(TypeError):
        eriksson_1997_height_trajectory_sweden_birch(15.0, Age.DBH(20), Age.TOTAL(40))


@pytest.mark.parametrize(
    "age,age2",
    [
        (Age.DBH(5), Age.DBH(20)),
        (Age.DBH(20), Age.DBH(95)),
    ],
)
def test_eriksson_warning_age_range(age, age2):
    with pytest.warns(UserWarning):
        res = eriksson_1997_height_trajectory_sweden_birch(15.0, age, age2)
    assert float(res) > 0


def test_eriksson_siteindexvalue_contents():
    result = eriksson_1997_height_trajectory_sweden_birch(
        18.0,
        Age.DBH(40),
        Age.DBH(60),
    )

    assert isinstance(result, SiteIndexValue)
    assert float(result) == pytest.approx(21.8470492, rel=1e-7)
    assert result.reference_age == Age.DBH(60)
    assert result.species == {
        TreeSpecies.Sweden.betula_pendula,
        TreeSpecies.Sweden.betula_pubescens,
    }
    assert result.fn is eriksson_1997_height_trajectory_sweden_birch
