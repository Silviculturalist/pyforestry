import pytest
from munin.volume.sweden import (
    BrandelVolume,
    andersson_1954_volume_small_trees_birch_height_above_4_m, 
    carbonnier_1954_volume_larch,
    matern_1975_volume_sweden_beech,
    Eriksson_1973_volume_aspen_Sweden,
    Eriksson_1973_volume_lodgepole_pine_Sweden
)

def test_brandel_volume_log():
    # Example coefficients for southern pine (adjust based on your model)
    coeff = [-1.38903, 1.84493, 0.06563, 2.02122, -1.01095]
    diameter_cm = 40
    height_m = 25
    volume = BrandelVolume.get_volume_log(coeff, diameter_cm, height_m)
    assert isinstance(volume, float)
    assert volume > 0

def test_andersson_1954_volume_birch():
    # Use Andersson_1954 for a small birch tree; expected value range is illustrative.
    vol = andersson_1954_volume_small_trees_birch_height_above_4_m(4.0, 10.0)
    assert isinstance(vol, float)
    # Adjust the tolerance or expected range based on your model.
    assert 0.0 < vol < 10.0

def test_carbonnier_1954_volume_larch():
    vol = carbonnier_1954_volume_larch(30, 20)
    assert isinstance(vol, float)
    assert vol > 0

def test_matern_1975_volume_beech():
    vol = matern_1975_volume_sweden_beech(35, 25)
    assert isinstance(vol, float)
    assert vol > 0

def test_eriksson_1973_volume_aspen():
    vol = Eriksson_1973_volume_aspen_Sweden(30, 20)
    assert isinstance(vol, float)
    assert vol > 0


def test_eriksson_1973_volume_lodgepole():
    vol = Eriksson_1973_volume_lodgepole_pine_Sweden(30, 20)
    assert isinstance(vol, float)
    assert vol > 0