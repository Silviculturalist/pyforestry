import math

import pytest

import pyforestry.norway.siteindex.kuehne_2022 as kuehne_module
import pyforestry.norway.siteindex.sharma_2011 as sharma_module
from pyforestry.base.helpers.primitives import Age
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.norway.siteindex import (
    Kuehne2022,
    Sharma2011,
    Tveite,
    kuehne_2022_height_trajectory_and_si_scots_pine_norway,
    kuehne_2022_height_trajectory_scots_pine_norway,
    kuehne_2022_site_index_h100_scots_pine_norway,
    sharma_2011_height_trajectory_norway_spruce_norway,
    sharma_2011_height_trajectory_scots_pine_norway,
    tveite_1967_loreys_height_norway_spruce,
    tveite_1967_loreys_height_scots_pine,
    tveite_1977_height_trajectory_norway_spruce_norway,
    tveite_height_trajectory_scots_pine_norway,
)


def test_sharma_trajectory_functions_and_wrappers():
    spruce = sharma_2011_height_trajectory_norway_spruce_norway(20.0, Age.DBH(40), Age.DBH(60))
    pine = sharma_2011_height_trajectory_scots_pine_norway(20.0, Age.DBH(40), Age.DBH(60))
    via_wrapper = Sharma2011.height_trajectory.picea_abies(20.0, Age.DBH(40), Age.DBH(60))

    assert spruce.reference_age == Age.DBH(60)
    assert TreeSpecies.Norway.picea_abies in spruce.species
    assert TreeSpecies.Norway.pinus_sylvestris in pine.species
    assert float(via_wrapper) == pytest.approx(float(spruce))

    with pytest.raises(TypeError):
        sharma_2011_height_trajectory_norway_spruce_norway(20.0, Age.TOTAL(40), Age.DBH(60))
    with pytest.raises(ValueError):
        sharma_2011_height_trajectory_scots_pine_norway(1.0, Age.DBH(40), Age.DBH(60))


def test_tveite_trajectory_and_loreys_height():
    spruce = tveite_1977_height_trajectory_norway_spruce_norway(18.0, Age.DBH(35), Age.DBH(60))
    pine = tveite_height_trajectory_scots_pine_norway(18.0, Age.DBH(35), Age.DBH(60))
    assert TreeSpecies.Norway.picea_abies in spruce.species
    assert TreeSpecies.Norway.pinus_sylvestris in pine.species

    assert tveite_1967_loreys_height_norway_spruce(20.0, 1000.0, 25.0, 20.0) > 0
    assert tveite_1967_loreys_height_scots_pine(20.0, 1000.0, 25.0, 20.0) > 0

    assert Tveite.height_trajectory.picea_abies(18.0, Age.DBH(35), Age.DBH(60)) == pytest.approx(
        spruce
    )
    assert Tveite.HL.pinus_sylvestris(20.0, 1000.0, 25.0, 20.0) > 0

    with pytest.warns(UserWarning):
        tveite_1977_height_trajectory_norway_spruce_norway(18.0, Age.DBH(10), Age.DBH(60))
    with pytest.raises(TypeError):
        tveite_height_trajectory_scots_pine_norway(18.0, Age.TOTAL(35), Age.DBH(60))


def test_kuehne_trajectory_and_site_index():
    h_value = kuehne_2022_height_trajectory_scots_pine_norway(18.0, Age.TOTAL(40), Age.TOTAL(60))
    si_h100 = kuehne_2022_site_index_h100_scots_pine_norway(18.0, Age.TOTAL(40))
    both = kuehne_2022_height_trajectory_and_si_scots_pine_norway(
        18.0,
        Age.TOTAL(40),
        Age.TOTAL(60),
        output="both",
    )
    assert TreeSpecies.Norway.pinus_sylvestris in h_value.species
    assert si_h100.reference_age == Age.TOTAL(100.0)
    assert both[1] == pytest.approx(float(si_h100), rel=1e-6)

    via_wrapper = Kuehne2022.height_trajectory.pinus_sylvestris(18.0, Age.TOTAL(40), Age.TOTAL(60))
    assert float(via_wrapper) == pytest.approx(float(h_value))

    with pytest.raises(TypeError):
        kuehne_2022_height_trajectory_scots_pine_norway(18.0, Age.DBH(40), Age.TOTAL(60))
    with pytest.raises(ValueError):
        kuehne_2022_height_trajectory_and_si_scots_pine_norway(
            18.0,
            Age.TOTAL(40),
            Age.TOTAL(60),
            output="invalid",
        )


def test_kuehne_additional_validation_and_output_modes():
    with pytest.raises(ValueError):
        kuehne_2022_height_trajectory_scots_pine_norway(18.0, Age.TOTAL(0.0), Age.TOTAL(60.0))
    with pytest.raises(ValueError):
        kuehne_module._kuehne_height_and_h100(0.0, 60.0, 18.0)

    height_only = kuehne_2022_height_trajectory_and_si_scots_pine_norway(
        18.0,
        Age.TOTAL(40),
        Age.TOTAL(60),
        output="height",
    )
    assert height_only.reference_age == Age.TOTAL(60.0)

    si = kuehne_2022_height_trajectory_and_si_scots_pine_norway(
        18.0,
        Age.TOTAL(40),
        Age.TOTAL(60),
        output="sih100",
    )
    assert si.reference_age == Age.TOTAL(100.0)


def test_sharma_internal_branch_warnings() -> None:
    with pytest.raises(ValueError):
        sharma_2011_height_trajectory_scots_pine_norway(20.0, Age.DBH(0.0), Age.DBH(60.0))

    with pytest.warns(UserWarning, match="Negative square-root argument"):
        out_negative_sqrt = sharma_module._sharma_height(
            dominant_height_m=2.0,
            age_dbh=10.0,
            age2_dbh=20.0,
            b1=0.7,
            b2=-10.0,
            b3=1.0,
        )
    assert math.isnan(out_negative_sqrt)

    with pytest.warns(UserWarning, match="Near-zero intermediate x term"):
        out_near_zero_x = sharma_module._sharma_height(
            dominant_height_m=2.0,
            age_dbh=20.0,
            age2_dbh=60.0,
            b1=2.0,
            b2=0.0,
            b3=1.0,
        )
    assert math.isnan(out_near_zero_x)

    with pytest.warns(UserWarning, match="Near-zero denominator"):
        out_near_zero_denom = sharma_module._sharma_height(
            dominant_height_m=2.0,
            age_dbh=1.0,
            age2_dbh=0.10819418755438782,
            b1=-0.3,
            b2=-0.1,
            b3=1.0,
        )
    assert math.isnan(out_near_zero_denom)
