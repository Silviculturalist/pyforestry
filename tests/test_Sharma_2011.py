# test_Sharma2011.py

import pytest
import math
from Munin.SiteIndex.norway.Sharma_2011 import Sharma2011, SharmaSpruceModel, SharmaPineModel
from Munin.Helpers.Primitives import Age, AgeMeasurement, SiteIndexValue

# Expected values calculated manually based on the example input H=17@40 -> H@20
EXPECTED_SPRUCE_H_AT_20_SHARMA = 8.790
EXPECTED_PINE_H_AT_20_SHARMA = 9.300

def test_sharma_spruce_height_trajectory():
    """ Tests Sharma 2011 Spruce height trajectory (callable species). """
     # *** UPDATED CALL ***
    result = Sharma2011.height_trajectory.picea_abies(
        dominant_height_m=17.0,
        age=Age.DBH(40),
        age2=Age.DBH(20)
    )
    assert isinstance(result, SiteIndexValue)
    assert not math.isnan(float(result)), "Calculation resulted in NaN"
    assert float(result) == pytest.approx(EXPECTED_SPRUCE_H_AT_20_SHARMA, abs=1e-3)
    assert result.reference_age == Age.DBH(20)
    assert result.species == SharmaSpruceModel.SPECIES
    # Check that the stored function is the callable wrapper instance
    assert result.fn is Sharma2011.height_trajectory.picea_abies


def test_sharma_pine_height_trajectory():
    """ Tests Sharma 2011 Pine height trajectory (callable species). """
     # *** UPDATED CALL ***
    result = Sharma2011.height_trajectory.pinus_sylvestris(
        dominant_height_m=17.0,
        age=Age.DBH(40),
        age2=Age.DBH(20)
    )
    assert isinstance(result, SiteIndexValue)
    assert not math.isnan(float(result)), "Calculation resulted in NaN"
    assert float(result) == pytest.approx(EXPECTED_PINE_H_AT_20_SHARMA, abs=1e-3)
    assert result.reference_age == Age.DBH(20)
    assert result.species == SharmaPineModel.SPECIES
    assert result.fn is Sharma2011.height_trajectory.pinus_sylvestris


def test_sharma_height_trajectory_requires_dbh():
    """ Tests TypeError if Age.TOTAL is provided (callable species). """
    with pytest.raises(TypeError, match="must be specified as Age.DBH"):
         # *** UPDATED CALL ***
        Sharma2011.height_trajectory.picea_abies(
            dominant_height_m=17.0,
            age=Age.TOTAL(50), # Incorrect type
            age2=Age.DBH(20)
        )
    with pytest.raises(TypeError, match="must be specified as Age.DBH"):
         # *** UPDATED CALL ***
        Sharma2011.height_trajectory.pinus_sylvestris(
            dominant_height_m=17.0,
            age=Age.DBH(40),
            age2=Age.TOTAL(30) # Incorrect type
        )

def test_sharma_height_trajectory_requires_positive_age():
    """ Tests ValueError for non-positive ages (callable species). """
    with pytest.raises(ValueError, match="Ages must be positive"):
         # *** UPDATED CALL ***
        Sharma2011.height_trajectory.picea_abies(
            dominant_height_m=17.0,
            age=Age.DBH(0),
            age2=Age.DBH(20)
        )
    with pytest.raises(ValueError, match="Ages must be positive"):
         # *** UPDATED CALL ***
        Sharma2011.height_trajectory.pinus_sylvestris(
            dominant_height_m=17.0,
            age=Age.DBH(40),
            age2=Age.DBH(-5)
        )

def test_sharma_height_trajectory_requires_height_gt_13():
    """ Tests ValueError for height <= 1.3m (callable species). """
    with pytest.raises(ValueError, match="Dominant height must be > 1.3m"):
         # *** UPDATED CALL ***
        Sharma2011.height_trajectory.picea_abies(
            dominant_height_m=1.3,
            age=Age.DBH(40),
            age2=Age.DBH(20)
        )
    with pytest.raises(ValueError, match="Dominant height must be > 1.3m"):
         # *** UPDATED CALL ***
        Sharma2011.height_trajectory.pinus_sylvestris(
            dominant_height_m=1.0,
            age=Age.DBH(40),
            age2=Age.DBH(20)
        )