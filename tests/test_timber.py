import pytest
from Munin.Timber.Timber import Timber
from Munin.Timber.SweTimber import SweTimber
from Munin.Volume import BrandelVolume

def test_timber_valid_instance():
    # Create a basic Timber instance with valid parameters.
    timber = Timber(
        species="pinus sylvestris",
        diameter_cm=30,
        height_m=20,
        double_bark_mm=1,
        crown_base_height_m=10,
        over_bark=True
    )
    # Check that properties are set correctly.
    assert timber.species == "pinus sylvestris"
    assert timber.height_m > 0

def test_timber_invalid_diameter():
    # Ensure that a negative diameter raises an error.
    with pytest.raises(ValueError):
        Timber(
            species="pinus sylvestris",
            diameter_cm=-5,
            height_m=20
        )

def test_swetimber_volume_small_tree():
    # Create a SweTimber instance that should use a small tree model.
    swetimber = SweTimber(
        species="betula",
        diameter_cm=4.0,    # small diameter (<5 cm)
        height_m=10.0,
        double_bark_mm=1,
        crown_base_height_m=3,
        over_bark=True,
        region="southern",
        latitude=58
    )
    vol = swetimber.getvolume()
    assert isinstance(vol, float)
    # Expected volume for a small tree should be > 0 (adjust threshold if needed)
    assert vol > 0

def test_swetimber_volume_large_tree():
    # Create a SweTimber instance that forces a larger tree volume calculation
    swetimber = SweTimber(
        species="pinus sylvestris",
        diameter_cm=55,
        height_m=30.0,
        double_bark_mm=1,
        crown_base_height_m=15,
        over_bark=True,
        region="southern",
        latitude=58
    )
    vol = swetimber.getvolume()
    assert isinstance(vol, float)
    # Check that the computed volume is in a reasonable range (example threshold)
    assert vol > 0


# Example site data:
latitude: float = 56.5
altitude: float = 150
# Example fieldlayer object with a "code" attribute:
class fieldlayer:
    def __init__(self, code: int) -> None:
        self.code = code

fieldlayer = fieldlayer(2)  # For example, fieldlayer code 2

# Tree parameters:
diameter_cm: float = 35
height_m: float = 12.0  # 12.0 m
species: str = "Pinus sylvestris"  # Example species name

# Calculate volume (in dm³)
volume_dm3: float = BrandelVolume.get_volume(species, diameter_cm, height_m,
                                    latitude, altitude, fieldlayer,
                                    over_bark=True)
# Convert dm³ to m³ (1 m³ = 1000 dm³)
volume_m3: float = volume_dm3 / 1000
print(f"Calculated volume: {volume_m3:.3f} m³")