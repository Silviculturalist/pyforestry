# test_Tveite1976.py

import pytest
import math
from Munin.SiteIndex.norway.Tveite_1976 import Tveite1976
from Munin.Helpers.Base import Age, AgeMeasurement, SiteIndexValue
from Munin.SiteIndex.norway.Tveite_1976 import TveiteSpruceModel, TveitePineModel

# Define expected values from the R code examples (approximately)
EXPECTED_SPRUCE_H_AT_20 = 8.930776
EXPECTED_PINE_H_AT_20 = 10.1717
EXPECTED_SPRUCE_LOREY_H = 20.430252
EXPECTED_PINE_LOREY_H = 18.70385

# --- Height Trajectory Tests ---

def test_spruce_height_trajectory_example():
    """ Tests Tveite 1977 Spruce height trajectory (callable species). """
    # *** UPDATED CALL ***
    result = Tveite1976.height_trajectory.picea_abies(
        dominant_height_m=17.0,
        age=Age.DBH(40),
        age2=Age.DBH(20)
    )
    assert isinstance(result, SiteIndexValue)
    assert float(result) == pytest.approx(EXPECTED_SPRUCE_H_AT_20, abs=1e-4)
    assert result.reference_age == Age.DBH(20)
    assert result.species == TveiteSpruceModel.SPECIES
    # Check that the stored function is the callable wrapper instance
    assert result.fn is Tveite1976.height_trajectory.picea_abies

def test_pine_height_trajectory_example():
    """ Tests Tveite 1976 Pine height trajectory (callable species). """
    # *** UPDATED CALL ***
    result = Tveite1976.height_trajectory.pinus_sylvestris(
        dominant_height_m=17.0,
        age=Age.DBH(40),
        age2=Age.DBH(20)
    )
    assert isinstance(result, SiteIndexValue)
    assert float(result) == pytest.approx(EXPECTED_PINE_H_AT_20, abs=1e-4)
    assert result.reference_age == Age.DBH(20)
    assert result.species == TveitePineModel.SPECIES
    assert result.fn is Tveite1976.height_trajectory.pinus_sylvestris


def test_height_trajectory_requires_dbh():
    """ Tests TypeError if Age.TOTAL is provided (callable species). """
    with pytest.raises(TypeError, match="must be specified as Age.DBH"):
        # *** UPDATED CALL ***
        Tveite1976.height_trajectory.picea_abies(
            dominant_height_m=17.0,
            age=Age.TOTAL(50), # Incorrect type
            age2=Age.DBH(20)
        )
    with pytest.raises(TypeError, match="must be specified as Age.DBH"):
         # *** UPDATED CALL ***
        Tveite1976.height_trajectory.pinus_sylvestris(
            dominant_height_m=17.0,
            age=Age.DBH(40),
            age2=Age.TOTAL(30) # Incorrect type
        )

def test_height_trajectory_requires_positive_age():
    """ Tests ValueError for non-positive ages (callable species). """
    with pytest.raises(ValueError, match="Ages must be positive"):
         # *** UPDATED CALL ***
        Tveite1976.height_trajectory.picea_abies(
            dominant_height_m=17.0,
            age=Age.DBH(0),
            age2=Age.DBH(20)
        )
    with pytest.raises(ValueError, match="Ages must be positive"):
         # *** UPDATED CALL ***
        Tveite1976.height_trajectory.pinus_sylvestris(
            dominant_height_m=17.0,
            age=Age.DBH(40),
            age2=Age.DBH(-5)
        )


# --- Lorey's Height (HL) Tests ---

def test_spruce_loreys_height_example():
    """ Tests Tveite 1967 Spruce Lorey's height (callable species). """
     # *** UPDATED CALL ***
    result = Tveite1976.HL.picea_abies(
        dominant_height_m=22.0,
        stems_per_ha=1200.0,
        basal_area_m2_ha=30.0,
        qmd_cm=19.5
    )
    assert isinstance(result, float)
    assert result == pytest.approx(EXPECTED_SPRUCE_LOREY_H, abs=1e-4)

def test_pine_loreys_height_example():
    """ Tests Tveite 1967 Pine Lorey's height (callable species). """
     # *** UPDATED CALL ***
    result = Tveite1976.HL.pinus_sylvestris(
        dominant_height_m=20.0,
        stems_per_ha=900.0,
        basal_area_m2_ha=28.0,
        diameter_mean_ba_stem_cm=21.0 # Value from example usage block
    )
    assert isinstance(result, float)
    assert result == pytest.approx(EXPECTED_PINE_LOREY_H, abs=1e-4)