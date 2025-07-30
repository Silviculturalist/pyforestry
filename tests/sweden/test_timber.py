import types

import pytest

from pyforestry.base.timber import Timber
from pyforestry.sweden.timber import SweTimber


def test_timber_valid_instance():
    # Create a basic Timber instance with valid parameters.
    timber = Timber(
        species="pinus sylvestris",
        diameter_cm=30,
        height_m=20,
        double_bark_mm=1,
        crown_base_height_m=10,
        over_bark=True,
    )
    # Check that properties are set correctly.
    assert timber.species == "pinus sylvestris"
    assert timber.height_m > 0


def test_timber_invalid_diameter():
    # Ensure that a negative diameter raises an error.
    with pytest.raises(ValueError):
        Timber(species="pinus sylvestris", diameter_cm=-5, height_m=20)


def test_swetimber_volume_small_tree():
    # Create a SweTimber instance that should use a small tree model.
    swetimber = SweTimber(
        species="betula",
        diameter_cm=4.0,  # small diameter (<5 cm)
        height_m=10.0,
        double_bark_mm=1,
        crown_base_height_m=3,
        over_bark=True,
        region="southern",
        latitude=58,
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
        latitude=58,
    )
    vol = swetimber.getvolume()
    assert isinstance(vol, float)
    # Check that the computed volume is in a reasonable range (example threshold)
    assert vol > 0


def make_site():
    return types.SimpleNamespace(
        latitude=60.0,
        altitude=100.0,
        field_layer=types.SimpleNamespace(code=1),
    )


def test_getvolume_pine_small(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.andersson_1954_volume_small_trees_pine",
        lambda *_: 1.0,
    )
    tree = SweTimber(species="pinus sylvestris", diameter_cm=3, height_m=6)
    assert tree.getvolume() == 1.0


def test_getvolume_spruce_site(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.BrandelVolume.get_volume",
        lambda **_: 2.0,
    )
    tree = SweTimber(
        species="picea abies",
        diameter_cm=20,
        height_m=20,
        swedish_site=make_site(),
    )
    assert tree.getvolume() == 2.0


def test_getvolume_birch_small_height(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.andersson_1954_volume_small_trees_birch_height_above_4_m",
        lambda *_: 3.0,
    )
    tree = SweTimber(species="betula", diameter_cm=3, height_m=5)
    assert tree.getvolume() == 3.0


def test_getvolume_larch_large(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.BrandelVolume.get_volume",
        lambda **_: 4.0,
    )
    tree = SweTimber(species="betula", diameter_cm=60, height_m=20)
    tree.species = "larix sibirica"
    assert tree.getvolume() == 4.0


def test_getvolume_default_fallback(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.BrandelVolume.get_volume",
        lambda **_: 5.0,
    )
    tree = SweTimber(species="betula", diameter_cm=30, height_m=20)
    tree.species = "unknown"
    assert tree.getvolume() == 5.0


def test_invalid_region():
    with pytest.raises(ValueError):
        SweTimber(species="betula", diameter_cm=10, height_m=10, region="central")


def test_invalid_species():
    with pytest.raises(ValueError):
        SweTimber(species="invalid", diameter_cm=10, height_m=10)
