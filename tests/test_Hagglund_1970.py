# test_hagglund_1970.py

import pytest
import math
from Munin.SiteIndex.sweden.Hagglund_1970 import Hagglund_1970, HagglundPineModel, HagglundSpruceModel
from Munin.SiteIndex.sweden.Hagglund_1972_1973 import (
    Hagglund1972SpruceHeightTrajectoryNorthernSweden,
    Hagglund_1973_southern_Sweden_Height_trajectories_Spruce)
from Munin.SiteIndex.sweden.Hagglund_1974 import hagglund_1974_sweden_height_trajectories_pine
from Munin.Helpers.Base import Age, SiteIndexValue
from Munin.Helpers.TreeSpecies import TreeSpecies # Assuming TreeSpecies is needed for context if not directly used

# --- Test Data ---

# Shared values for tests where applicable
DOMINANT_HEIGHT = 25.0
AGE_DBH = 80
AGE_TOTAL = 100 # Target age for prediction
LATITUDE = 64.0 # Northern Sweden
REGENERATION_CULTURE = Hagglund_1970.regeneration.CULTURE
REGENERATION_NATURAL = Hagglund_1970.regeneration.NATURAL


# --- Numerical Consistency Tests ---

def test_spruce_northern_sweden_consistency():
    """Compare Hagglund_1970 Spruce N. Sweden with Hagglund_1972 original."""
    # Original function call
    original_h_age2, original_t13 = Hagglund1972SpruceHeightTrajectoryNorthernSweden(
        dominantHeight=DOMINANT_HEIGHT,
        age=AGE_DBH,
        age2=AGE_TOTAL,
        latitude=LATITUDE,
        culture=True
    )

    # Refactored function calls
    refactored_si_value, refactored_t13 = HagglundSpruceModel.northern_sweden(
        dominant_height=DOMINANT_HEIGHT,
        age=Age.DBH(AGE_DBH), # Use AgeMeasurement
        age2=Age.TOTAL(AGE_TOTAL), # Use AgeMeasurement
        latitude=LATITUDE,
        culture=True
    )

    # Check direct T13 return value
    assert refactored_t13 == pytest.approx(original_t13)

    # Check height from SiteIndexValue
    assert refactored_si_value == pytest.approx(original_h_age2)

    # Check wrappers
    refactored_h_wrapper = Hagglund_1970.height_trajectory.picea_abies.northern_sweden(
         dominant_height=DOMINANT_HEIGHT,
         age=Age.DBH(AGE_DBH),
         age2=Age.TOTAL(AGE_TOTAL),
         latitude=LATITUDE,
         culture=True
    )
    refactored_t13_wrapper = Hagglund_1970.time_to_breast_height.picea_abies.northern_sweden(
         dominant_height=DOMINANT_HEIGHT,
         age=Age.DBH(AGE_DBH),
         age2=Age.TOTAL(AGE_TOTAL),
         latitude=LATITUDE,
         culture=True
    )

    assert isinstance(refactored_h_wrapper, SiteIndexValue)
    assert refactored_h_wrapper == pytest.approx(original_h_age2)
    assert refactored_t13_wrapper == pytest.approx(original_t13)


def test_spruce_southern_sweden_consistency():
    """Compare Hagglund_1970 Spruce S. Sweden with Hagglund_1973 original."""
    # Original function call
    original_h_age2, original_t13 = Hagglund_1973_southern_Sweden_Height_trajectories_Spruce(
        dominantHeight=DOMINANT_HEIGHT,
        age=AGE_DBH,
        age2=AGE_TOTAL
    )

    # Refactored function calls
    refactored_si_value, refactored_t13 = HagglundSpruceModel.southern_sweden(
        dominant_height=DOMINANT_HEIGHT,
        age=Age.DBH(AGE_DBH),
        age2=Age.TOTAL(AGE_TOTAL)
    )

    # Check direct T13 return value
    assert refactored_t13 == pytest.approx(original_t13)

    # Check height from SiteIndexValue
    assert refactored_si_value == pytest.approx(original_h_age2)

     # Check wrappers
    refactored_h_wrapper = Hagglund_1970.height_trajectory.picea_abies.southern_sweden(
         dominant_height=DOMINANT_HEIGHT,
         age=Age.DBH(AGE_DBH),
         age2=Age.TOTAL(AGE_TOTAL)
    )
    refactored_t13_wrapper = Hagglund_1970.time_to_breast_height.picea_abies.southern_sweden(
         dominant_height=DOMINANT_HEIGHT,
         age=Age.DBH(AGE_DBH),
         age2=Age.TOTAL(AGE_TOTAL)
    )

    assert isinstance(refactored_h_wrapper, SiteIndexValue)
    assert refactored_h_wrapper == pytest.approx(original_h_age2)
    assert refactored_t13_wrapper == pytest.approx(original_t13)


def test_pine_sweden_consistency():
    """Compare Hagglund_1970 Pine Sweden with Hagglund_1974 original."""
     # Original function call
    original_h_age2, original_t13 = hagglund_1974_sweden_height_trajectories_pine(
        dominant_height=DOMINANT_HEIGHT,
        age=AGE_DBH,
        age2=AGE_TOTAL,
        regeneration=str(REGENERATION_CULTURE) # Original expects string
    )

    # Refactored function calls
    refactored_si_value, refactored_t13 = HagglundPineModel.sweden(
        dominant_height_m=DOMINANT_HEIGHT,
        age=Age.DBH(AGE_DBH),
        age2=Age.TOTAL(AGE_TOTAL),
        regeneration=REGENERATION_CULTURE # Refactored expects Enum
    )

     # Check direct T13 return value
    assert refactored_t13 == pytest.approx(original_t13)

    # Check height from SiteIndexValue
    assert refactored_si_value == pytest.approx(original_h_age2)

    # Check wrappers
    refactored_h_wrapper = Hagglund_1970.height_trajectory.pinus_sylvestris.sweden(
        dominant_height_m=DOMINANT_HEIGHT,
        age=Age.DBH(AGE_DBH),
        age2=Age.TOTAL(AGE_TOTAL),
        regeneration=REGENERATION_CULTURE
    )
    refactored_t13_wrapper = Hagglund_1970.time_to_breast_height.pinus_sylvestris.sweden(
        dominant_height_m=DOMINANT_HEIGHT,
        age=Age.DBH(AGE_DBH),
        age2=Age.TOTAL(AGE_TOTAL),
        regeneration=REGENERATION_CULTURE
    )

    assert isinstance(refactored_h_wrapper, SiteIndexValue)
    assert refactored_h_wrapper == pytest.approx(original_h_age2)
    assert refactored_t13_wrapper == pytest.approx(original_t13)


# --- Type Safety Tests ---

# Test Spruce Northern Sweden Age Types
def test_spruce_north_age_type_safety_correct():
    """Test Spruce N. Sweden accepts correct AgeMeasurement types."""
    try:
        HagglundSpruceModel.northern_sweden(
            dominant_height=DOMINANT_HEIGHT,
            age=Age.DBH(AGE_DBH), # Correct type for age
            age2=Age.TOTAL(AGE_TOTAL), # Correct type for age2
            latitude=LATITUDE,
            culture=True
        )
    except TypeError:
        pytest.fail("TypeError raised unexpectedly with correct AgeMeasurement types.")

def test_spruce_north_age_type_safety_incorrect_age():
    """Test Spruce N. Sweden rejects incorrect AgeMeasurement type for 'age'."""
    with pytest.raises(TypeError, match="Parameter 'age' must be a float/int or an instance of Age.DBH."):
        HagglundSpruceModel.northern_sweden(
            dominant_height=DOMINANT_HEIGHT,
            age=Age.TOTAL(AGE_DBH), # Incorrect type for age
            age2=Age.TOTAL(AGE_TOTAL),
            latitude=LATITUDE,
            culture=True
        )

def test_spruce_north_age_type_safety_incorrect_age2():
    """Test Spruce N. Sweden rejects incorrect AgeMeasurement type for 'age2'."""
    with pytest.raises(TypeError, match="Parameter 'age2' must be a float/int or an instance of Age.TOTAL."):
        HagglundSpruceModel.northern_sweden(
            dominant_height=DOMINANT_HEIGHT,
            age=Age.DBH(AGE_DBH),
            age2=Age.DBH(AGE_TOTAL), # Incorrect type for age2
            latitude=LATITUDE,
            culture=True
        )

# Test Spruce Southern Sweden Age Types (similar structure)
def test_spruce_south_age_type_safety_correct():
    """Test Spruce S. Sweden accepts correct AgeMeasurement types."""
    try:
        HagglundSpruceModel.southern_sweden(
            dominant_height=DOMINANT_HEIGHT,
            age=Age.DBH(AGE_DBH), # Correct type for age
            age2=Age.TOTAL(AGE_TOTAL) # Correct type for age2
        )
    except TypeError:
        pytest.fail("TypeError raised unexpectedly with correct AgeMeasurement types.")


def test_spruce_south_age_type_safety_incorrect_age():
    """Test Spruce S. Sweden rejects incorrect AgeMeasurement type for 'age'."""
    with pytest.raises(TypeError, match="Parameter 'age' must be a float/int or an instance of Age.DBH."):
         HagglundSpruceModel.southern_sweden(
            dominant_height=DOMINANT_HEIGHT,
            age=Age.TOTAL(AGE_DBH), # Incorrect type for age
            age2=Age.TOTAL(AGE_TOTAL)
        )

def test_spruce_south_age_type_safety_incorrect_age2():
    """Test Spruce S. Sweden rejects incorrect AgeMeasurement type for 'age2'."""
    with pytest.raises(TypeError, match="Parameter 'age2' must be a float/int or an instance of Age.TOTAL."):
         HagglundSpruceModel.southern_sweden(
            dominant_height=DOMINANT_HEIGHT,
            age=Age.DBH(AGE_DBH),
            age2=Age.DBH(AGE_TOTAL) # Incorrect type for age2
        )

# Test Pine Sweden Age Types (similar structure)
def test_pine_sweden_age_type_safety_correct():
    """Test Pine Sweden accepts correct AgeMeasurement types."""
    try:
        HagglundPineModel.sweden(
            dominant_height_m=DOMINANT_HEIGHT,
            age=Age.DBH(AGE_DBH), # Correct type for age
            age2=Age.TOTAL(AGE_TOTAL), # Correct type for age2
            regeneration=REGENERATION_CULTURE
        )
    except TypeError:
        pytest.fail("TypeError raised unexpectedly with correct AgeMeasurement types.")

def test_pine_sweden_age_type_safety_incorrect_age():
    """Test Pine Sweden rejects incorrect AgeMeasurement type for 'age'."""
    with pytest.raises(TypeError, match="Parameter 'age' must be a float/int or an instance of Age.DBH."):
         HagglundPineModel.sweden(
            dominant_height_m=DOMINANT_HEIGHT,
            age=Age.TOTAL(AGE_DBH), # Incorrect type for age
            age2=Age.TOTAL(AGE_TOTAL),
            regeneration=REGENERATION_CULTURE
        )

def test_pine_sweden_age_type_safety_incorrect_age2():
    """Test Pine Sweden rejects incorrect AgeMeasurement type for 'age2'."""
    with pytest.raises(TypeError, match="Parameter 'age2' must be a float/int or an instance of Age.TOTAL."):
        HagglundPineModel.sweden(
            dominant_height_m=DOMINANT_HEIGHT,
            age=Age.DBH(AGE_DBH),
            age2=Age.DBH(AGE_TOTAL), # Incorrect type for age2
            regeneration=REGENERATION_CULTURE
        )

# --- Optional: Test Regeneration Enum for Pine ---
def test_pine_sweden_regeneration_type_safety():
     """Test Pine Sweden rejects invalid regeneration types."""
     # Check invalid string
     with pytest.raises(TypeError, match="Parameter 'regeneration' must be a Hagglund_1970.regeneration Enum."):
        HagglundPineModel.sweden(
            dominant_height_m=DOMINANT_HEIGHT,
            age=Age.DBH(AGE_DBH),
            age2=Age.TOTAL(AGE_TOTAL),
            regeneration="invalid_string" # Invalid string
        )
     # Check invalid type (e.g., integer) - This might raise TypeError earlier depending on implementation
     with pytest.raises((ValueError, TypeError)): # Catch either if type check happens before value check
        HagglundPineModel.sweden(
            dominant_height_m=DOMINANT_HEIGHT,
            age=Age.DBH(AGE_DBH),
            age2=Age.TOTAL(AGE_TOTAL),
            regeneration=123 # Invalid type
        )