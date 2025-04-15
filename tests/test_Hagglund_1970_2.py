# test_Hagglund_1970.py

import pytest
import math

# Import the main classes and specific model classes from both versions
from Munin.SiteIndex.sweden.Hagglund_1970 import (
    Hagglund_1970 as H70_v1_Class,
    HagglundSpruceModel as H70_v1_SpruceModel,
    HagglundPineModel as H70_v1_PineModel,
    HagglundPineRegeneration as H70_v1_Regeneration # Import enum too
)
from Munin.SiteIndex.sweden.Hagglund_1970_2 import (
    Hagglund_1970 as H70_v2_Class,
    HagglundSpruceModel as H70_v2_SpruceModel,
    HagglundPineModel as H70_v2_PineModel,
    HagglundPineRegeneration as H70_v2_Regeneration # Import enum too
)

from Munin.Helpers.Base import Age, AgeMeasurement, SiteIndexValue
from Munin.Helpers.TreeSpecies import TreeSpecies # Assuming TreeSpecies is needed

# --- Test Data ---

DOMINANT_HEIGHT_SPRUCE_N = 20.0
AGE_DBH_SPRUCE_N = 70
AGE_TOTAL_SPRUCE_N = 100
LATITUDE_SPRUCE_N = 64.0
CULTURE_SPRUCE_N = True

DOMINANT_HEIGHT_SPRUCE_S = 28.0
AGE_DBH_SPRUCE_S = 60
AGE_TOTAL_SPRUCE_S = 80

DOMINANT_HEIGHT_PINE = 22.0
AGE_DBH_PINE = 85
AGE_TOTAL_PINE = 120
# Use the specific enum from v1 for tests comparing against v1 results
REGENERATION_CULTURE_PINE_V1 = H70_v1_Regeneration.CULTURE
REGENERATION_NATURAL_PINE_V1 = H70_v1_Regeneration.NATURAL
# Use the specific enum from v2 for tests comparing against v2 results (assuming they are compatible)
REGENERATION_CULTURE_PINE_V2 = H70_v2_Regeneration.CULTURE
REGENERATION_NATURAL_PINE_V2 = H70_v2_Regeneration.NATURAL


# --- Original Type Safety Tests (Corrected Access) ---

# Test Spruce Northern Sweden Age Types (v1)
def test_v1_spruce_north_age_type_safety_correct():
    """Test v1 Spruce N. Sweden accepts correct AgeMeasurement types."""
    try:
        # Access model directly via its imported name
        H70_v1_SpruceModel.northern_sweden(
            dominant_height=DOMINANT_HEIGHT_SPRUCE_N,
            age=Age.DBH(AGE_DBH_SPRUCE_N),
            age2=Age.TOTAL(AGE_TOTAL_SPRUCE_N),
            latitude=LATITUDE_SPRUCE_N,
            culture=CULTURE_SPRUCE_N
        )
    except TypeError:
        pytest.fail("v1 TypeError raised unexpectedly with correct AgeMeasurement types.")

def test_v1_spruce_north_age_type_safety_incorrect_age():
    """Test v1 Spruce N. Sweden rejects incorrect AgeMeasurement type for 'age'."""
    with pytest.raises(TypeError, match="Parameter 'age' must be a float/int or an instance of Age.DBH."):
        H70_v1_SpruceModel.northern_sweden(
            dominant_height=DOMINANT_HEIGHT_SPRUCE_N,
            age=Age.TOTAL(AGE_DBH_SPRUCE_N), # Incorrect
            age2=Age.TOTAL(AGE_TOTAL_SPRUCE_N),
            latitude=LATITUDE_SPRUCE_N,
            culture=CULTURE_SPRUCE_N
        )

def test_v1_spruce_north_age_type_safety_incorrect_age2():
    """Test v1 Spruce N. Sweden rejects incorrect AgeMeasurement type for 'age2'."""
    with pytest.raises(TypeError, match="Parameter 'age2' must be a float/int or an instance of Age.TOTAL."):
        H70_v1_SpruceModel.northern_sweden(
            dominant_height=DOMINANT_HEIGHT_SPRUCE_N,
            age=Age.DBH(AGE_DBH_SPRUCE_N),
            age2=Age.DBH(AGE_TOTAL_SPRUCE_N), # Incorrect
            latitude=LATITUDE_SPRUCE_N,
            culture=CULTURE_SPRUCE_N
        )

# Test Spruce Southern Sweden Age Types (v1)
def test_v1_spruce_south_age_type_safety_correct():
    try:
        H70_v1_SpruceModel.southern_sweden(
            dominant_height=DOMINANT_HEIGHT_SPRUCE_S,
            age=Age.DBH(AGE_DBH_SPRUCE_S),
            age2=Age.TOTAL(AGE_TOTAL_SPRUCE_S)
        )
    except TypeError:
        pytest.fail("v1 TypeError raised unexpectedly.")

def test_v1_spruce_south_age_type_safety_incorrect_age():
    with pytest.raises(TypeError, match="Parameter 'age' must be a float/int or an instance of Age.DBH."):
         H70_v1_SpruceModel.southern_sweden(
            dominant_height=DOMINANT_HEIGHT_SPRUCE_S,
            age=Age.TOTAL(AGE_DBH_SPRUCE_S), # Incorrect
            age2=Age.TOTAL(AGE_TOTAL_SPRUCE_S)
        )

def test_v1_spruce_south_age_type_safety_incorrect_age2():
    with pytest.raises(TypeError, match="Parameter 'age2' must be a float/int or an instance of Age.TOTAL."):
         H70_v1_SpruceModel.southern_sweden(
            dominant_height=DOMINANT_HEIGHT_SPRUCE_S,
            age=Age.DBH(AGE_DBH_SPRUCE_S),
            age2=Age.DBH(AGE_TOTAL_SPRUCE_S) # Incorrect
        )

# Test Pine Sweden Age Types (v1)
def test_v1_pine_sweden_age_type_safety_correct():
    try:
        H70_v1_PineModel.sweden(
            dominant_height_m=DOMINANT_HEIGHT_PINE,
            age=Age.DBH(AGE_DBH_PINE),
            age2=Age.TOTAL(AGE_TOTAL_PINE),
            regeneration=REGENERATION_CULTURE_PINE_V1
        )
    except TypeError:
        pytest.fail("v1 TypeError raised unexpectedly.")

def test_v1_pine_sweden_age_type_safety_incorrect_age():
    with pytest.raises(TypeError, match="Parameter 'age' must be a float/int or an instance of Age.DBH."):
         H70_v1_PineModel.sweden(
            dominant_height_m=DOMINANT_HEIGHT_PINE,
            age=Age.TOTAL(AGE_DBH_PINE), # Incorrect
            age2=Age.TOTAL(AGE_TOTAL_PINE),
            regeneration=REGENERATION_CULTURE_PINE_V1
        )

def test_v1_pine_sweden_age_type_safety_incorrect_age2():
    with pytest.raises(TypeError, match="Parameter 'age2' must be a float/int or an instance of Age.TOTAL."):
        H70_v1_PineModel.sweden(
            dominant_height_m=DOMINANT_HEIGHT_PINE,
            age=Age.DBH(AGE_DBH_PINE),
            age2=Age.DBH(AGE_TOTAL_PINE), # Incorrect
            regeneration=REGENERATION_CULTURE_PINE_V1
        )

# Test Pine Sweden Regeneration Enum (v1)
def test_v1_pine_sweden_regeneration_type_safety():
     # Check invalid string (should raise TypeError based on v1 code annotation)
     with pytest.raises(TypeError, match="Parameter 'regeneration' must be a Hagglund_1970.regeneration Enum."):
        H70_v1_PineModel.sweden(
            dominant_height_m=DOMINANT_HEIGHT_PINE,
            age=Age.DBH(AGE_DBH_PINE),
            age2=Age.TOTAL(AGE_TOTAL_PINE),
            regeneration="invalid_string" # Invalid string
        )
     # Check invalid type (e.g., integer) - v1 raises TypeError here too
     with pytest.raises(TypeError):
        H70_v1_PineModel.sweden(
            dominant_height_m=DOMINANT_HEIGHT_PINE,
            age=Age.DBH(AGE_DBH_PINE),
            age2=Age.TOTAL(AGE_TOTAL_PINE),
            regeneration=123 # Invalid type
        )


# --- Numerical Consistency Tests (Corrected Access) ---

# Spruce Northern Sweden - Height Trajectory
def test_numerical_spruce_north_height():
    """Compare height trajectory output for Spruce N. Sweden between v1 and v2."""
    # Access via Class.attribute.species.method
    si_v1 = H70_v1_Class.height_trajectory.picea_abies.northern_sweden(
        dominant_height=DOMINANT_HEIGHT_SPRUCE_N,
        age=float(AGE_DBH_SPRUCE_N),
        age2=float(AGE_TOTAL_SPRUCE_N),
        latitude=LATITUDE_SPRUCE_N,
        culture=CULTURE_SPRUCE_N
    )
    si_v2 = H70_v2_Class.height_trajectory.picea_abies.northern_sweden(
        dominant_height=DOMINANT_HEIGHT_SPRUCE_N,
        age=float(AGE_DBH_SPRUCE_N),
        age2=float(AGE_TOTAL_SPRUCE_N),
        latitude=LATITUDE_SPRUCE_N,
        culture=CULTURE_SPRUCE_N
    )
    assert float(si_v1) == pytest.approx(float(si_v2))
    assert si_v1.reference_age == si_v2.reference_age
    assert si_v1.species == si_v2.species

    # Using AgeMeasurement objects
    si_v1_age = H70_v1_Class.height_trajectory.picea_abies.northern_sweden(
        dominant_height=DOMINANT_HEIGHT_SPRUCE_N,
        age=Age.DBH(AGE_DBH_SPRUCE_N),
        age2=Age.TOTAL(AGE_TOTAL_SPRUCE_N),
        latitude=LATITUDE_SPRUCE_N,
        culture=CULTURE_SPRUCE_N
    )
    si_v2_age = H70_v2_Class.height_trajectory.picea_abies.northern_sweden(
        dominant_height=DOMINANT_HEIGHT_SPRUCE_N,
        age=Age.DBH(AGE_DBH_SPRUCE_N),
        age2=Age.TOTAL(AGE_TOTAL_SPRUCE_N),
        latitude=LATITUDE_SPRUCE_N,
        culture=CULTURE_SPRUCE_N
    )
    assert float(si_v1_age) == pytest.approx(float(si_v2_age))
    assert si_v1_age.reference_age == si_v2_age.reference_age
    assert si_v1_age.species == si_v2_age.species


# Spruce Northern Sweden - Time to Breast Height (T13)
def test_numerical_spruce_north_t13():
    """Compare T13 output for Spruce N. Sweden between v1 and v2."""
    t13_v1 = H70_v1_Class.time_to_breast_height.picea_abies.northern_sweden(
        dominant_height=DOMINANT_HEIGHT_SPRUCE_N,
        age=float(AGE_DBH_SPRUCE_N),
        age2=float(AGE_TOTAL_SPRUCE_N), # age2 is technically unused for T13 calc but required
        latitude=LATITUDE_SPRUCE_N,
        culture=CULTURE_SPRUCE_N
    )
    t13_v2 = H70_v2_Class.time_to_breast_height.picea_abies.northern_sweden(
        dominant_height=DOMINANT_HEIGHT_SPRUCE_N,
        age=float(AGE_DBH_SPRUCE_N),
        age2=float(AGE_TOTAL_SPRUCE_N),
        latitude=LATITUDE_SPRUCE_N,
        culture=CULTURE_SPRUCE_N
    )
    assert t13_v1 == pytest.approx(t13_v2)

# Spruce Southern Sweden - Height Trajectory
def test_numerical_spruce_south_height():
    """Compare height trajectory output for Spruce S. Sweden between v1 and v2."""
    si_v1 = H70_v1_Class.height_trajectory.picea_abies.southern_sweden(
        dominant_height=DOMINANT_HEIGHT_SPRUCE_S,
        age=float(AGE_DBH_SPRUCE_S),
        age2=float(AGE_TOTAL_SPRUCE_S)
    )
    si_v2 = H70_v2_Class.height_trajectory.picea_abies.southern_sweden(
        dominant_height=DOMINANT_HEIGHT_SPRUCE_S,
        age=float(AGE_DBH_SPRUCE_S),
        age2=float(AGE_TOTAL_SPRUCE_S)
    )
    assert float(si_v1) == pytest.approx(float(si_v2))
    assert si_v1.reference_age == si_v2.reference_age
    assert si_v1.species == si_v2.species

# Spruce Southern Sweden - Time to Breast Height (T13)
def test_numerical_spruce_south_t13():
    """Compare T13 output for Spruce S. Sweden between v1 and v2."""
    t13_v1 = H70_v1_Class.time_to_breast_height.picea_abies.southern_sweden(
        dominant_height=DOMINANT_HEIGHT_SPRUCE_S,
        age=float(AGE_DBH_SPRUCE_S),
        age2=float(AGE_TOTAL_SPRUCE_S) # age2 is technically unused for T13 calc
    )
    t13_v2 = H70_v2_Class.time_to_breast_height.picea_abies.southern_sweden(
        dominant_height=DOMINANT_HEIGHT_SPRUCE_S,
        age=float(AGE_DBH_SPRUCE_S),
        age2=float(AGE_TOTAL_SPRUCE_S)
    )
    assert t13_v1 == pytest.approx(t13_v2)


# Pine Sweden - Height Trajectory (Culture)
def test_numerical_pine_sweden_height_culture():
    """Compare height trajectory output for Pine Sweden (Culture) between v1 and v2."""
    si_v1 = H70_v1_Class.height_trajectory.pinus_sylvestris.sweden(
        dominant_height_m=DOMINANT_HEIGHT_PINE,
        age=float(AGE_DBH_PINE),
        age2=float(AGE_TOTAL_PINE),
        regeneration=REGENERATION_CULTURE_PINE_V1 # Use V1 enum for V1 call
    )
    si_v2 = H70_v2_Class.height_trajectory.pinus_sylvestris.sweden(
        dominant_height_m=DOMINANT_HEIGHT_PINE,
        age=float(AGE_DBH_PINE),
        age2=float(AGE_TOTAL_PINE),
        regeneration=REGENERATION_CULTURE_PINE_V2 # Use V2 enum for V2 call
    )
    assert float(si_v1) == pytest.approx(float(si_v2))
    assert si_v1.reference_age == si_v2.reference_age
    assert si_v1.species == si_v2.species

# Pine Sweden - Time to Breast Height (T13) (Culture)
def test_numerical_pine_sweden_t13_culture():
    """Compare T13 output for Pine Sweden (Culture) between v1 and v2."""
    t13_v1 = H70_v1_Class.time_to_breast_height.pinus_sylvestris.sweden(
        dominant_height_m=DOMINANT_HEIGHT_PINE,
        age=float(AGE_DBH_PINE),
        age2=float(AGE_TOTAL_PINE), # age2 is unused
        regeneration=REGENERATION_CULTURE_PINE_V1 # Use V1 enum
    )
    t13_v2 = H70_v2_Class.time_to_breast_height.pinus_sylvestris.sweden(
        dominant_height_m=DOMINANT_HEIGHT_PINE,
        age=float(AGE_DBH_PINE),
        age2=float(AGE_TOTAL_PINE),
        regeneration=REGENERATION_CULTURE_PINE_V2 # Use V2 enum
    )
    assert t13_v1 == pytest.approx(t13_v2)

# Pine Sweden - Height Trajectory (Natural)
def test_numerical_pine_sweden_height_natural():
    """Compare height trajectory output for Pine Sweden (Natural) between v1 and v2."""
    si_v1 = H70_v1_Class.height_trajectory.pinus_sylvestris.sweden(
        dominant_height_m=DOMINANT_HEIGHT_PINE,
        age=float(AGE_DBH_PINE),
        age2=float(AGE_TOTAL_PINE),
        regeneration=REGENERATION_NATURAL_PINE_V1 # Use V1 enum
    )
    si_v2 = H70_v2_Class.height_trajectory.pinus_sylvestris.sweden(
        dominant_height_m=DOMINANT_HEIGHT_PINE,
        age=float(AGE_DBH_PINE),
        age2=float(AGE_TOTAL_PINE),
        regeneration=REGENERATION_NATURAL_PINE_V2 # Use V2 enum
    )
    assert float(si_v1) == pytest.approx(float(si_v2))
    assert si_v1.reference_age == si_v2.reference_age
    assert si_v1.species == si_v2.species

# Pine Sweden - Time to Breast Height (T13) (Natural)
def test_numerical_pine_sweden_t13_natural():
    """Compare T13 output for Pine Sweden (Natural) between v1 and v2."""
    t13_v1 = H70_v1_Class.time_to_breast_height.pinus_sylvestris.sweden(
        dominant_height_m=DOMINANT_HEIGHT_PINE,
        age=float(AGE_DBH_PINE),
        age2=float(AGE_TOTAL_PINE), # age2 is unused
        regeneration=REGENERATION_NATURAL_PINE_V1 # Use V1 enum
    )
    t13_v2 = H70_v2_Class.time_to_breast_height.pinus_sylvestris.sweden(
        dominant_height_m=DOMINANT_HEIGHT_PINE,
        age=float(AGE_DBH_PINE),
        age2=float(AGE_TOTAL_PINE),
        regeneration=REGENERATION_NATURAL_PINE_V2 # Use V2 enum
    )
    assert t13_v1 == pytest.approx(t13_v2)



# ------------------------------------------------------------------------------
# Test for Spruce Southern Sweden
# ------------------------------------------------------------------------------
def test_spruce_southern_age_conversion_consistency():
    total_age = 100.0
    dominant_height = 12.0
    age_at_breast = 35.0

    # Compute using Age.TOTAL for age2.
    si_total, T13_total = H70_v2_SpruceModel.southern_sweden(
        dominant_height=dominant_height,
        age=Age.DBH(age_at_breast),
        age2=Age.TOTAL(total_age)
    )
    height_total = float(si_total)
    
    # Compute using DBH for age2.
    si_dbh, T13_dbh = H70_v2_SpruceModel.southern_sweden(
        dominant_height=height_total,
        age=Age.TOTAL(total_age),
        age2=Age.DBH(age_at_breast)
    )
    height_dbh = float(si_dbh)
    # The model should now return the original dominant height if the age conversion is correct.
    assert dominant_height == pytest.approx(height_dbh, rel=0.05)

# ------------------------------------------------------------------------------
# Test for Spruce Northern Sweden
# ------------------------------------------------------------------------------
def test_spruce_northern_age_conversion_consistency():
    total_age = 100.0
    dominant_height = 12.0
    age_at_breast = 35.0
    latitude = 64.0
    culture = True

    # Compute using Age.TOTAL for age2.
    si_total, T13_total = H70_v2_SpruceModel.northern_sweden(
        dominant_height=dominant_height,
        age=Age.DBH(age_at_breast),
        age2=Age.TOTAL(total_age),
        latitude=latitude,
        culture=culture
    )
    height_total = float(si_total)
    
    # Compute using DBH for age2.
    si_dbh, T13_dbh = H70_v2_SpruceModel.northern_sweden(
        dominant_height=height_total,
        age=Age.TOTAL(total_age),
        age2=Age.DBH(age_at_breast),
        latitude=latitude,
        culture=culture
    )
    height_dbh = float(si_dbh)
    # Check for consistency: the computed height (from DBH age2) should equal the original dominant height.
    assert dominant_height == pytest.approx(height_dbh, rel=0.05)

# ------------------------------------------------------------------------------
# Test for Pine Sweden
# ------------------------------------------------------------------------------
def test_pine_age_conversion_consistency():
    total_age = 100.0
    dominant_height = 12.0
    age_at_breast = 35.0
    regeneration = H70_v2_Regeneration.CULTURE

    # Compute using Age.TOTAL for age2.
    si_total, T13_total = H70_v2_PineModel.sweden(
        dominant_height_m=dominant_height,
        age=Age.DBH(age_at_breast),
        age2=Age.TOTAL(total_age),
        regeneration=regeneration
    )
    height_total = float(si_total)
    
    # Compute using DBH for age2.
    si_dbh, T13_dbh = H70_v2_PineModel.sweden(
        dominant_height_m=height_total,
        age=Age.TOTAL(total_age),
        age2=Age.DBH(age_at_breast),
        regeneration=regeneration
    )
    height_dbh = float(si_dbh)
    # Assert that the computed height remains consistent.
    assert dominant_height == pytest.approx(height_dbh, rel=0.05)