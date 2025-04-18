# test_hagglund_1970.py

import pytest
import math
# Assuming the new V2 classes are now the primary imports
from Munin.SiteIndex.sweden.Hagglund_1970 import Hagglund_1970, HagglundPineModel, HagglundSpruceModel
from Munin.Helpers.Primitives import Age


# --- Test Data ---

# Shared values for tests where applicable
DOMINANT_HEIGHT_S_SPRUCE = 15.0
AGE_DBH_S_SPRUCE = 40
AGE_TOTAL_S_SPRUCE = 90 # Example prediction age

DOMINANT_HEIGHT_N_SPRUCE = 12.0
AGE_DBH_N_SPRUCE = 35
AGE_TOTAL_N_SPRUCE = 100 # Example prediction age
LATITUDE_N_SPRUCE = 64.0
CULTURE_N_SPRUCE = True

DOMINANT_HEIGHT_PINE = 18.0
AGE_DBH_PINE = 50
AGE_TOTAL_PINE = 110 # Example prediction age
REGENERATION_CULTURE_PINE = Hagglund_1970.regeneration.CULTURE
REGENERATION_NATURAL_PINE = Hagglund_1970.regeneration.NATURAL

# --- Type Safety & Input Validation Tests ---

# --- Spruce Northern Sweden ---

def test_valid_input_types_spruce_north():
    """Test Spruce N. Sweden accepts various valid input types without error."""
    try:
        # Test with AgeMeasurement
        HagglundSpruceModel.northern_sweden(
            dominant_height=DOMINANT_HEIGHT_N_SPRUCE,
            age=Age.DBH(AGE_DBH_N_SPRUCE),
            age2=Age.TOTAL(AGE_TOTAL_N_SPRUCE),
            latitude=LATITUDE_N_SPRUCE, culture=CULTURE_N_SPRUCE
        )
        HagglundSpruceModel.northern_sweden(
            dominant_height=DOMINANT_HEIGHT_N_SPRUCE,
            age=Age.TOTAL(AGE_TOTAL_N_SPRUCE), # V2 accepts Total age
            age2=Age.DBH(AGE_DBH_N_SPRUCE),   # V2 accepts DBH age2
            latitude=LATITUDE_N_SPRUCE, culture=CULTURE_N_SPRUCE
        )
        # Test with float/int (defaults should apply)
        HagglundSpruceModel.northern_sweden(
            dominant_height=DOMINANT_HEIGHT_N_SPRUCE,
            age=float(AGE_DBH_N_SPRUCE),
            age2=float(AGE_TOTAL_N_SPRUCE),
            latitude=LATITUDE_N_SPRUCE, culture=CULTURE_N_SPRUCE
        )
    except Exception as e: # Catch broader exceptions for debugging if needed
        pytest.fail(f"Spruce North: Error raised unexpectedly with valid input types: {e}")

def test_invalid_data_types_spruce_north():
    """Test Spruce N. Sweden rejects invalid data types for age/age2."""
    # Passing a non-numeric string to float() raises ValueError
    with pytest.raises(ValueError, match="could not convert string to float"):
        HagglundSpruceModel.northern_sweden(
            dominant_height=DOMINANT_HEIGHT_N_SPRUCE,
            age="eighty", # Invalid string for age -> float() fails
            age2=AGE_TOTAL_N_SPRUCE,
            latitude=LATITUDE_N_SPRUCE, culture=CULTURE_N_SPRUCE
        )
    # Passing other incompatible types might raise TypeError before/during float()
    with pytest.raises(TypeError):
        HagglundSpruceModel.northern_sweden(
            dominant_height=DOMINANT_HEIGHT_N_SPRUCE,
            age=AGE_DBH_N_SPRUCE,
            age2=[100, 110], # Invalid list for age2
            latitude=LATITUDE_N_SPRUCE, culture=CULTURE_N_SPRUCE
        )
    # Check parameter types other than age/age2
    with pytest.raises(TypeError):
         HagglundSpruceModel.northern_sweden(
            dominant_height=DOMINANT_HEIGHT_N_SPRUCE,
            age=AGE_DBH_N_SPRUCE,
            age2=AGE_TOTAL_N_SPRUCE,
            latitude="north", # Invalid string for latitude
            culture=CULTURE_N_SPRUCE
        )

# --- Spruce Southern Sweden ---

def test_valid_input_types_spruce_south():
    """Test Spruce S. Sweden accepts various valid input types without error."""
    try:
        # Test with AgeMeasurement
        HagglundSpruceModel.southern_sweden(
            dominant_height=DOMINANT_HEIGHT_S_SPRUCE,
            age=Age.DBH(AGE_DBH_S_SPRUCE),
            age2=Age.TOTAL(AGE_TOTAL_S_SPRUCE)
        )
        HagglundSpruceModel.southern_sweden(
            dominant_height=DOMINANT_HEIGHT_S_SPRUCE,
            age=Age.TOTAL(AGE_TOTAL_S_SPRUCE), # V2 accepts Total age
            age2=Age.DBH(AGE_DBH_S_SPRUCE)   # V2 accepts DBH age2
        )
        # Test with float/int (defaults should apply)
        HagglundSpruceModel.southern_sweden(
            dominant_height=DOMINANT_HEIGHT_S_SPRUCE,
            age=float(AGE_DBH_S_SPRUCE),
            age2=float(AGE_TOTAL_S_SPRUCE)
        )
    except Exception as e:
        pytest.fail(f"Spruce South: Error raised unexpectedly with valid input types: {e}")

def test_invalid_data_types_spruce_south():
    """Test Spruce S. Sweden rejects invalid data types for age/age2."""
    # Passing a non-numeric string to float() raises ValueError
    with pytest.raises(ValueError, match="could not convert string to float"):
        HagglundSpruceModel.southern_sweden(
            dominant_height=DOMINANT_HEIGHT_S_SPRUCE,
            age="forty", # Invalid string for age -> float() fails
            age2=AGE_TOTAL_S_SPRUCE
        )
    # Passing other incompatible types might raise TypeError before/during float()
    with pytest.raises(TypeError):
        HagglundSpruceModel.southern_sweden(
            dominant_height=DOMINANT_HEIGHT_S_SPRUCE,
            age=AGE_DBH_S_SPRUCE,
            age2={"age": 90} # Invalid dict for age2
        )
    # Check parameter types other than age/age2
    with pytest.raises(TypeError):
         HagglundSpruceModel.southern_sweden(
            dominant_height="fifteen", # Invalid string for height
            age=AGE_DBH_S_SPRUCE,
            age2=AGE_TOTAL_S_SPRUCE
        )


# --- Pine Sweden ---

def test_valid_input_types_pine():
    """Test Pine Sweden accepts various valid input types without error."""
    try:
        # Test with AgeMeasurement
        HagglundPineModel.sweden(
            dominant_height_m=DOMINANT_HEIGHT_PINE,
            age=Age.DBH(AGE_DBH_PINE),
            age2=Age.TOTAL(AGE_TOTAL_PINE),
            regeneration=REGENERATION_CULTURE_PINE
        )
        HagglundPineModel.sweden(
            dominant_height_m=DOMINANT_HEIGHT_PINE,
            age=Age.TOTAL(AGE_TOTAL_PINE), # V2 accepts Total age
            age2=Age.DBH(AGE_DBH_PINE),   # V2 accepts DBH age2
            regeneration=REGENERATION_NATURAL_PINE
        )
        # Test with float/int (defaults should apply)
        HagglundPineModel.sweden(
            dominant_height_m=DOMINANT_HEIGHT_PINE,
            age=float(AGE_DBH_PINE),
            age2=float(AGE_TOTAL_PINE),
            regeneration=REGENERATION_CULTURE_PINE
        )
    except Exception as e:
        pytest.fail(f"Pine Sweden: Error raised unexpectedly with valid input types: {e}")

def test_invalid_data_types_pine():
    """Test Pine Sweden rejects invalid data types for age/age2."""
    # Passing incompatible types might raise TypeError before/during float()
    with pytest.raises(TypeError):
        HagglundPineModel.sweden(
            dominant_height_m=DOMINANT_HEIGHT_PINE,
            age=("fifty",), # Invalid tuple for age
            age2=AGE_TOTAL_PINE,
            regeneration=REGENERATION_CULTURE_PINE
        )
    with pytest.raises(TypeError):
        HagglundPineModel.sweden(
            dominant_height_m=DOMINANT_HEIGHT_PINE,
            age=AGE_DBH_PINE,
            age2=None, # Invalid None for age2 -> float() fails with TypeError
            regeneration=REGENERATION_NATURAL_PINE
        )
    # Check parameter types other than age/age2
    with pytest.raises(TypeError):
         HagglundPineModel.sweden(
            dominant_height_m = {"height": 18.0}, # Invalid dict for height
            age=AGE_DBH_PINE,
            age2=AGE_TOTAL_PINE,
            regeneration=REGENERATION_CULTURE_PINE
        )

# Test Regeneration Enum for Pine
def test_pine_sweden_regeneration_type_safety():
     """Test Pine Sweden rejects invalid regeneration types."""
     # Check invalid string - causes UnboundLocalError due to no match in T13 calc
     with pytest.raises(TypeError):
         HagglundPineModel.sweden(
             dominant_height_m=DOMINANT_HEIGHT_PINE,
             age=AGE_DBH_PINE,
             age2=AGE_TOTAL_PINE,
             regeneration="invalid_string" # Invalid string -> no T13_local assignment
         )
     # Check invalid type (e.g., integer) - also causes UnboundLocalError
     with pytest.raises(TypeError):
         HagglundPineModel.sweden(
             dominant_height_m=DOMINANT_HEIGHT_PINE,
             age=AGE_DBH_PINE,
             age2=AGE_TOTAL_PINE,
             regeneration=123 
         )

# --- Age Conversion Consistency Tests (Reversibility) ---
# These tests are crucial for V2 and should be kept as they were.

# Test for Spruce Southern Sweden
def test_spruce_southern_age_conversion_consistency():
    """Test V2 Spruce S. Sweden age conversion is reversible."""
    total_age = 100.0
    dominant_height = 12.0
    age_at_breast = 35.0

    # Compute using Age.TOTAL for age2.
    si_total, T13_total = HagglundSpruceModel.southern_sweden(
        dominant_height=dominant_height,
        age=Age.DBH(age_at_breast),
        age2=Age.TOTAL(total_age)
    )
    height_total = float(si_total)

    # Compute using DBH for age2.
    si_dbh, T13_dbh = HagglundSpruceModel.southern_sweden(
        dominant_height=height_total,
        age=Age.TOTAL(total_age),
        age2=Age.DBH(age_at_breast)
    )
    height_dbh = float(si_dbh)
    assert dominant_height == pytest.approx(height_dbh, rel=0.01) # Relative tolerance 1%

# Test for Spruce Northern Sweden
def test_spruce_northern_age_conversion_consistency():
    """Test V2 Spruce N. Sweden age conversion is reversible."""
    total_age = 100.0
    dominant_height = 12.0
    age_at_breast = 35.0
    latitude = 64.0
    culture = True

    # Compute using Age.TOTAL for age2.
    si_total, T13_total = HagglundSpruceModel.northern_sweden(
        dominant_height=dominant_height,
        age=Age.DBH(age_at_breast),
        age2=Age.TOTAL(total_age),
        latitude=latitude,
        culture=culture
    )
    height_total = float(si_total)

    # Compute using DBH for age2.
    si_dbh, T13_dbh = HagglundSpruceModel.northern_sweden(
        dominant_height=height_total,
        age=Age.TOTAL(total_age),
        age2=Age.DBH(age_at_breast),
        latitude=latitude,
        culture=culture
    )
    height_dbh = float(si_dbh)
    assert dominant_height == pytest.approx(height_dbh, rel=0.01) # Relative tolerance 1%

# Test for Pine Sweden
def test_pine_age_conversion_consistency():
    """Test V2 Pine Sweden age conversion is reversible."""
    total_age = 100.0
    dominant_height = 12.0
    age_at_breast = 35.0
    regeneration = Hagglund_1970.regeneration.CULTURE

    # Compute using Age.TOTAL for age2.
    si_total, T13_total = HagglundPineModel.sweden(
        dominant_height_m=dominant_height,
        age=Age.DBH(age_at_breast),
        age2=Age.TOTAL(total_age),
        regeneration=regeneration
    )
    height_total = float(si_total)

    # Compute using DBH for age2.
    si_dbh, T13_dbh = HagglundPineModel.sweden(
        dominant_height_m=height_total,
        age=Age.TOTAL(total_age),
        age2=Age.DBH(age_at_breast),
        regeneration=regeneration
    )
    height_dbh = float(si_dbh)
    assert dominant_height == pytest.approx(height_dbh, rel=0.01) # Relative tolerance 1%