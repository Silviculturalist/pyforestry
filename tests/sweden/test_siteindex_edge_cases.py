from decimal import Decimal

import pytest

from pyforestry.base.helpers.primitives import Age
from pyforestry.sweden.siteindex import (
    elfving_kiviste_1997_height_trajectory_sweden_pine,
    eriksson_1997_height_trajectory_sweden_birch,
    hagglund_remrod_1977_height_trajectories_lodgepole_pine,
    johansson_1996_height_trajectory_sweden_aspen,
    johansson_1999_height_trajectory_sweden_alnus_glutinosa,
    johansson_1999_height_trajectory_sweden_alnus_incana,
    johansson_2011_height_trajectory_sweden_poplar,
    johansson_2013_height_trajectory_sweden_beech,
    johansson_2013_height_trajectory_sweden_hybrid_aspen,
    johansson_2013_height_trajectory_sweden_larch,
    johansson_2013_height_trajectory_sweden_oak,
)

INVALID_TYPE_CASES = [
    (elfving_kiviste_1997_height_trajectory_sweden_pine, Age.TOTAL, "bad"),
    (eriksson_1997_height_trajectory_sweden_birch, Age.DBH, "bad"),
    (
        hagglund_remrod_1977_height_trajectories_lodgepole_pine,
        Age.DBH,
        Decimal("10"),
    ),
    (johansson_1996_height_trajectory_sweden_aspen, Age.TOTAL, "bad"),
    (johansson_1999_height_trajectory_sweden_alnus_glutinosa, Age.TOTAL, "bad"),
    (johansson_1999_height_trajectory_sweden_alnus_incana, Age.TOTAL, "bad"),
    (johansson_2011_height_trajectory_sweden_poplar, Age.TOTAL, "bad"),
    (johansson_2013_height_trajectory_sweden_beech, Age.TOTAL, "bad"),
    (johansson_2013_height_trajectory_sweden_hybrid_aspen, Age.TOTAL, "bad"),
    (johansson_2013_height_trajectory_sweden_larch, Age.TOTAL, "bad"),
    (johansson_2013_height_trajectory_sweden_oak, Age.TOTAL, "bad"),
]

INVALID_AGE2_CASES = [
    (elfving_kiviste_1997_height_trajectory_sweden_pine, Age.TOTAL, Age.DBH),
    (eriksson_1997_height_trajectory_sweden_birch, Age.DBH, Age.TOTAL),
    (hagglund_remrod_1977_height_trajectories_lodgepole_pine, Age.DBH, Age.TOTAL),
    (johansson_1996_height_trajectory_sweden_aspen, Age.TOTAL, Age.DBH),
    (johansson_1999_height_trajectory_sweden_alnus_glutinosa, Age.TOTAL, Age.DBH),
    (johansson_1999_height_trajectory_sweden_alnus_incana, Age.TOTAL, Age.DBH),
    (johansson_2011_height_trajectory_sweden_poplar, Age.TOTAL, Age.DBH),
    (johansson_2013_height_trajectory_sweden_beech, Age.TOTAL, Age.DBH),
    (johansson_2013_height_trajectory_sweden_hybrid_aspen, Age.TOTAL, Age.DBH),
    (johansson_2013_height_trajectory_sweden_larch, Age.TOTAL, Age.DBH),
    (johansson_2013_height_trajectory_sweden_oak, Age.TOTAL, Age.DBH),
]


@pytest.mark.parametrize("fn,agecls,bad", INVALID_TYPE_CASES)
def test_invalid_type_inputs(fn, agecls, bad):
    with pytest.raises(TypeError):
        fn(10.0, bad, agecls(20))
    with pytest.raises(TypeError):
        fn(10.0, agecls(20), bad)


@pytest.mark.parametrize("fn,agecls,wrongcls", INVALID_AGE2_CASES)
def test_invalid_age2_code(fn, agecls, wrongcls):
    with pytest.raises(TypeError):
        fn(10.0, agecls(20), wrongcls(30))


HIGH_AGE_CASES = [
    (elfving_kiviste_1997_height_trajectory_sweden_pine, Age.TOTAL, 85, 90),
    (eriksson_1997_height_trajectory_sweden_birch, Age.DBH, 95, 96),
    (hagglund_remrod_1977_height_trajectories_lodgepole_pine, Age.DBH, 70, 80),
    (johansson_1996_height_trajectory_sweden_aspen, Age.TOTAL, 70, 70),
    (johansson_1999_height_trajectory_sweden_alnus_glutinosa, Age.TOTAL, 101, 105),
    (johansson_1999_height_trajectory_sweden_alnus_incana, Age.TOTAL, 71, 75),
    (johansson_2011_height_trajectory_sweden_poplar, Age.TOTAL, 70, 70),
    (johansson_2013_height_trajectory_sweden_beech, Age.TOTAL, 160, 160),
    (johansson_2013_height_trajectory_sweden_hybrid_aspen, Age.TOTAL, 55, 55),
    (johansson_2013_height_trajectory_sweden_larch, Age.TOTAL, 110, 110),
    (johansson_2013_height_trajectory_sweden_oak, Age.TOTAL, 160, 160),
]


@pytest.mark.parametrize("fn,agecls,a1,a2", HIGH_AGE_CASES)
def test_high_age_warnings(fn, agecls, a1, a2):
    with pytest.warns(UserWarning):
        res = fn(15.0, agecls(a1), agecls(a2))
    assert float(res) > 0


def test_hagglund_low_productivity_warning():
    with pytest.warns(UserWarning):
        hagglund_remrod_1977_height_trajectories_lodgepole_pine(5.0, Age.DBH(20), Age.DBH(40))


def test_johansson_1996_model1_branch():
    res = johansson_1996_height_trajectory_sweden_aspen(
        15.0, Age.TOTAL(20), Age.TOTAL(40), model1=True
    )
    assert float(res) > 0


def test_eriksson_float_inputs():
    res = eriksson_1997_height_trajectory_sweden_birch(15.0, 40.0, 60.0)
    assert float(res) > 0
