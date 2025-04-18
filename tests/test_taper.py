import pytest
import math
from Munin.Timber.SweTimber import SweTimber
from Munin.Taper.sweden.EdgrenNylinder1949 import EdgrenNylinder1949

# Fixture: a valid Timber instance.
@pytest.fixture
def valid_timber():
    # Create a valid Timber object.
    # Adjust these parameters as appropriate for your model.
    return SweTimber(
        species="pinus sylvestris",
        diameter_cm=40,
        height_m=30,
        double_bark_mm=1,
        crown_base_height_m=10,
        over_bark=True
    )

# Fixture: instantiate the taper (EdgrenNylinder1949) with the valid timber.
@pytest.fixture
def taper_instance(valid_timber):
    # EdgrenNylinder1949 should validate the Timber internally.
    return EdgrenNylinder1949(valid_timber)

def test_taper_instance_creation(taper_instance, valid_timber):
    # Check that the taper instance holds the Timber and that it is of the expected type.
    from Munin.Taper.Taper import Taper
    assert isinstance(taper_instance, Taper)
    # Verify that the stored timber has the expected height.
    assert math.isclose(taper_instance.timber.height_m, valid_timber.height_m)

def test_get_diameter_at_height(valid_timber, taper_instance):
    # Test the (static) get_diameter method.
    # We assume get_diameter returns the diameter at a specified height.
    test_height = 10.0  # meters above ground
    diameter = EdgrenNylinder1949.get_diameter_at_height(valid_timber, test_height)
    assert isinstance(diameter, float)
    # You might expect the diameter to be less than the base diameter:
    base_diam = EdgrenNylinder1949.get_base_diameter(valid_timber)
    assert diameter < base_diam

def test_get_relative_diameter(valid_timber):
    # Test the relative diameter function.
    # For a given relative height (e.g., 0.5 = mid-height), the relative diameter should be positive.
    rel_height = 0.5
    relative_diam = EdgrenNylinder1949.get_relative_diameter(rel_height, valid_timber)
    assert isinstance(relative_diam, float)
    assert relative_diam > 0

def test_volume_section(taper_instance):
    # Test the volume_section method from the base Taper.
    # We assume that integrating volume from a lower to a higher height returns a non-negative volume.
    # Note: volume_under_bark is implemented in the Taper base class.
    vol = taper_instance.volume_section(2.0, 10.0)
    assert isinstance(vol, float)
    # Even if zero volume is possible, typically for a valid tree we expect > 0.
    assert vol >= 0
