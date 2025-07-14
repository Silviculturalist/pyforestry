import pytest
import math
import numpy as np
from pyforestry.sweden.timber.swe_timber import SweTimber
from pyforestry.sweden.taper import EdgrenNylinder1949

# Fixture: a valid Timber instance for testing.
@pytest.fixture
def valid_timber():
    """
    Creates a valid SweTimber object for use in tests.
    The region is set to 'southern', which is required by the taper model.
    """
    return SweTimber(
        species="pinus sylvestris",
        diameter_cm=40,
        height_m=30,
        double_bark_mm=1,
        crown_base_height_m=10,
        over_bark=True,
        region="southern"  # Added required region attribute
    )

# Fixture: instantiate the taper model with the valid timber.
@pytest.fixture
def taper_instance(valid_timber):
    """
    Instantiates the EdgrenNylinder1949 taper model.
    This is now a stateful object with pre-calculated parameters.
    """
    return EdgrenNylinder1949(valid_timber)

def test_taper_instance_creation(taper_instance, valid_timber):
    """
    Tests that the taper instance is created correctly, holds the timber object,
    and is of the expected type.
    """
    from pyforestry.base.taper.taper import Taper
    assert isinstance(taper_instance, Taper)
    assert taper_instance.timber is valid_timber
    assert math.isclose(taper_instance.timber.height_m, 30)

def test_stateful_attributes_on_init(taper_instance):
    """
    Tests that the stateful attributes (base_diameter, inflexion_point, etc.)
    are calculated and stored on the instance during initialization.
    """
    assert hasattr(taper_instance, 'base_diameter')
    assert isinstance(taper_instance.base_diameter, float)
    assert taper_instance.base_diameter > 0

    assert hasattr(taper_instance, 'inflexion_point')
    assert isinstance(taper_instance.inflexion_point, float)
    assert taper_instance.inflexion_point > 0

    assert hasattr(taper_instance, 'constants')
    assert isinstance(taper_instance.constants, np.ndarray)

def test_get_diameter_at_height_instance_method(taper_instance):
    """
    Tests the get_diameter_at_height instance method.
    The method now uses the pre-calculated state of the instance.
    """
    test_height = 10.0  # meters above ground
    diameter = taper_instance.get_diameter_at_height(test_height)
    assert isinstance(diameter, float)
    assert diameter > 0

def test_get_relative_diameter_instance_method(taper_instance):
    """
    Tests the get_relative_diameter instance method.
    """
    rel_height = 0.5  # Relative height (mid-height)
    relative_diam = taper_instance.get_relative_diameter(rel_height)
    assert isinstance(relative_diam, float)
    assert relative_diam > 0

def test_get_height_at_diameter(taper_instance):
    """
    Tests the get_height_at_diameter method to find the height
    for a given diameter.
    """
    # Use a diameter that is smaller than breast-height diameter but > 0
    test_diameter = 20.0
    height = taper_instance.get_height_at_diameter(test_diameter)
    assert isinstance(height, float)
    assert 0 < height < taper_instance.timber.height_m

    # Test that the diameter at the returned height is close to the input diameter
    calculated_diameter = taper_instance.get_diameter_at_height(height)
    assert math.isclose(calculated_diameter, test_diameter, rel_tol=1e-3)

def test_volume_section(taper_instance):
    """
    Tests the volume_section method from the base Taper class,
    which relies on the instance's get_diameter_at_height method.
    """
    vol = taper_instance.volume_section(2.0, 10.0)
    assert isinstance(vol, float)
    assert vol >= 0

def test_invalid_timber_raises_error():
    """
    Tests that the constructor raises a ValueError when provided with
    an invalid timber object (e.g., height <= 0).
    """
    with pytest.raises(ValueError, match="Height must be larger than 0 m: {self.height_m}"):
        invalid_timber = SweTimber(
            species="picea abies",
            diameter_cm=30,
            height_m=0,  # Invalid height
            region="northern"
        )
        EdgrenNylinder1949(invalid_timber)