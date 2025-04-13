from Munin.Helpers.Base import *
from Munin.Helpers.TreeSpecies import TreeSpecies, TreeName, parse_tree_species
from Munin.SiteIndex.sweden.Eriksson_1997 import eriksson_1997_height_trajectory_sweden_birch
import pytest

# --- Add these new fixtures ---
@pytest.fixture
def sample_species_set() -> set[TreeName]:
    """Provides a sample set containing one TreeName."""
    return {TreeSpecies.Sweden.betula_pendula}

@pytest.fixture
def sample_species_set_multi() -> set[TreeName]:
    """Provides a sample set containing multiple TreeNames."""
    return {TreeSpecies.Sweden.betula_pendula, TreeSpecies.Sweden.betula_pubescens}

@pytest.fixture
def sample_age_measurement() -> AgeMeasurement:
    """Provides a sample AgeMeasurement."""
    return Age.TOTAL(100) # Or Age.DBH(100), adjust as needed for tests

# --- Add these new test functions ---

def test_site_index_value_creation_set(sample_age_measurement, sample_species_set, sample_fn):
    """Test successful creation of SiteIndexValue with a set of TreeName."""
    si_val = 30.5
    siv = SiteIndexValue(si_val, reference_age=sample_age_measurement, species=sample_species_set, fn=sample_fn)
    assert float(siv) == si_val
    assert siv.reference_age == sample_age_measurement
    assert siv.species == sample_species_set # Check the set itself
    assert siv.fn == sample_fn

def test_site_index_value_creation_set_multi(sample_age_measurement, sample_species_set_multi, sample_fn):
    """Test successful creation with multiple species in the set."""
    si_val = 28.0
    siv = SiteIndexValue(si_val, reference_age=sample_age_measurement, species=sample_species_set_multi, fn=sample_fn)
    assert float(siv) == si_val
    assert siv.species == sample_species_set_multi

def test_site_index_value_creation_species_not_set(sample_age_measurement, sample_species, sample_fn):
    """Test TypeError if species is not a set."""
    with pytest.raises(TypeError, match="species must be a set"):
        # Passing a single TreeName instead of a set
        SiteIndexValue(30.0, reference_age=sample_age_measurement, species=sample_species, fn=sample_fn)

def test_site_index_value_creation_species_set_empty(sample_age_measurement, sample_fn):
    """Test ValueError if species set is empty."""
    with pytest.raises(ValueError, match="species set cannot be empty."):
        SiteIndexValue(30.0, reference_age=sample_age_measurement, species=set(), fn=sample_fn)

def test_site_index_value_creation_species_set_wrong_type(sample_age_measurement, sample_species, sample_fn):
    """Test TypeError if species set contains non-TreeName items."""
    with pytest.raises(TypeError, match="All items in the species set must be TreeName objects"):
        SiteIndexValue(30.0, reference_age=sample_age_measurement, species={sample_species, "not_a_tree_name"}, fn=sample_fn)

def test_site_index_value_repr_set(sample_age_measurement, sample_species_set_multi, sample_fn):
    """Test the __repr__ output with a species set."""
    siv = SiteIndexValue(25.0, reference_age=sample_age_measurement, species=sample_species_set_multi, fn=sample_fn)
    siv_repr = repr(siv)
    assert "SiteIndexValue(25.0" in siv_repr
    assert repr(sample_age_measurement) in siv_repr
    # Check for the specific representation of the set
    # Note: The order within the set representation might vary, so check for elements
    assert repr(TreeSpecies.Sweden.betula_pendula) in siv_repr
    assert repr(TreeSpecies.Sweden.betula_pubescens) in siv_repr
    assert "species={" in siv_repr # Check the general set format
    assert "}" in siv_repr
    fn_name = sample_fn.__name__ if hasattr(sample_fn, '__name__') else str(sample_fn)
    assert f"fn={fn_name}" in siv_repr

# --- Fixtures for common objects ---
@pytest.fixture
def sample_species() -> TreeName:
    """Provides a sample TreeName instance."""
    return parse_tree_species('betula pendula')

@pytest.fixture
def sample_fn() -> callable:
    """Provides the sample site index function."""
    return eriksson_1997_height_trajectory_sweden_birch

@pytest.fixture
def age_total_100() -> AgeMeasurement:
    """Provides AgeMeasurement(100, Age.TOTAL.value)"""
    return AgeMeasurement(100.0, Age.TOTAL.value)

@pytest.fixture
def age_dbh_100() -> AgeMeasurement:
    """Provides AgeMeasurement(100, Age.DBH.value)"""
    return AgeMeasurement(100.0, Age.DBH.value)

# --- Tests for AgeMeasurement ---

def test_age_measurement_creation():
    """Test successful creation of AgeMeasurement."""
    age_t = AgeMeasurement(50.5, Age.TOTAL.value)
    assert float(age_t) == 50.5
    assert age_t.value == 50.5
    assert age_t.code == Age.TOTAL.value

    age_d = AgeMeasurement(25, Age.DBH.value) # Test with int
    assert float(age_d) == 25.0
    assert age_d.value == 25.0
    assert age_d.code == Age.DBH.value

def test_age_measurement_creation_negative_value():
    """Test ValueError on negative age."""
    with pytest.raises(ValueError, match="Age must be non-negative."):
        AgeMeasurement(-10.0, Age.TOTAL.value)

def test_age_measurement_creation_invalid_code():
    """Test ValueError on invalid age code."""
    with pytest.raises(ValueError, match="Invalid age code: 99"):
        AgeMeasurement(10.0, 99)

def test_age_measurement_repr(age_total_100):
    """Test the __repr__ output."""
    assert repr(age_total_100) == "AgeMeasurement(100.0, code=1 [TOTAL])"
    age_d = AgeMeasurement(50, Age.DBH.value)
    assert repr(age_d) == "AgeMeasurement(50.0, code=2 [DBH])"

def test_age_measurement_equality(age_total_100, age_dbh_100):
    """Test the __eq__ and __ne__ methods."""
    # Identical objects
    assert age_total_100 == AgeMeasurement(100.0, Age.TOTAL.value)
    assert not (age_total_100 != AgeMeasurement(100.0, Age.TOTAL.value))

    # Same value, different code
    assert age_total_100 != age_dbh_100
    assert not (age_total_100 == age_dbh_100)

    # Different value, same code
    age_total_50 = AgeMeasurement(50.0, Age.TOTAL.value)
    assert age_total_100 != age_total_50
    assert not (age_total_100 == age_total_50)

    # Comparison with float/int (only value matters)
    assert age_total_100 == 100.0
    assert age_total_100 == 100
    assert age_total_100 != 100.1
    assert age_total_100 != 99

    # Comparison behaves symmetrically (float == AgeMeasurement)
    assert 100.0 == age_total_100
    assert 100 == age_total_100
    assert 100.1 != age_total_100

    # Comparison with unrelated type
    assert age_total_100 != "100"
    assert "100" != age_total_100

# --- Tests for Age Enum ---

def test_age_enum_values():
    """Test the underlying values of Age enum members."""
    assert Age.TOTAL.value == 1
    assert Age.DBH.value == 2

def test_age_enum_call(age_total_100, age_dbh_100):
    """Test calling Age members creates correct AgeMeasurement objects."""
    # Using the __eq__ of AgeMeasurement to verify
    assert Age.TOTAL(100.0) == age_total_100
    assert Age.DBH(100.0) == age_dbh_100
    assert Age.TOTAL(50) == AgeMeasurement(50.0, Age.TOTAL.value)

    # Check inequality based on code
    assert Age.TOTAL(100) != Age.DBH(100)
    # Check inequality based on value
    assert Age.TOTAL(100) != Age.TOTAL(50)

# --- Tests for SiteIndexValue ---

def test_site_index_value_creation(age_total_100, sample_species, sample_fn):
    """Test successful creation of SiteIndexValue."""
    si_val = 30.5
    siv = SiteIndexValue(si_val, reference_age=age_total_100, species={sample_species}, fn=sample_fn)

    assert float(siv) == si_val
    assert siv.reference_age == age_total_100 # Checks both value and code
    assert siv.species == {sample_species}
    assert siv.fn == sample_fn

def test_site_index_value_creation_negative_value(age_total_100, sample_species, sample_fn):
    """Test ValueError on negative site index value."""
    with pytest.raises(ValueError, match="Site index value must be non-negative."):
        SiteIndexValue(-5.0, reference_age=age_total_100, species={sample_species}, fn=sample_fn)

def test_site_index_value_creation_wrong_ref_age_type(sample_species, sample_fn):
    """Test TypeError if reference_age is not AgeMeasurement."""
    with pytest.raises(TypeError, match="reference_age must be an AgeMeasurement object"):
        # Passing a float instead of AgeMeasurement
        SiteIndexValue(30.0, reference_age=100.0, species={sample_species}, fn=sample_fn)


def test_site_index_value_repr(age_total_100, sample_species, sample_fn):
    """Test the __repr__ output of SiteIndexValue."""
    siv = SiteIndexValue(30.0, reference_age=age_total_100, species={sample_species}, fn=sample_fn)
    siv_repr = repr(siv)

    # --- Replace the old assertion with these checks: ---
    assert "SiteIndexValue(30.0" in siv_repr
    # Check that AgeMeasurement's repr is included
    assert repr(age_total_100) in siv_repr
    # Check that the actual species repr is included
    assert repr(sample_species) in siv_repr
    # Check that the actual function name is included
    fn_name = sample_fn.__name__ if hasattr(sample_fn, '__name__') else str(sample_fn)
    assert f"fn={fn_name}" in siv_repr

def test_site_index_reference_age_comparison(sample_species, sample_fn, age_total_100, age_dbh_100):
    """Test comparisons involving siv.reference_age, checking value and code."""
    siv_total = SiteIndexValue(30.0, reference_age=age_total_100, species={sample_species}, fn=sample_fn)
    siv_dbh = SiteIndexValue(28.0, reference_age=age_dbh_100, species={sample_species}, fn=sample_fn)

    # Compare reference age to AgeMeasurement created via Age enum call
    # Case 1: Correct value and code
    assert siv_total.reference_age == Age.TOTAL(100)

    # Case 2: Correct value, wrong code
    assert siv_dbh.reference_age != Age.TOTAL(100)
    assert siv_dbh.reference_age == Age.DBH(100) # Check it matches DBH

    # Case 3: Wrong value, correct code
    assert siv_total.reference_age != Age.TOTAL(50)

    # Compare reference age directly to fixtures (other AgeMeasurement instances)
    assert siv_total.reference_age == age_total_100
    assert siv_total.reference_age != age_dbh_100
    assert siv_dbh.reference_age == age_dbh_100
    assert siv_dbh.reference_age != age_total_100