import types

import pytest

from pyforestry.sweden.timber.swe_timber import SweTimber


def make_site():
    return types.SimpleNamespace(
        latitude=60.0,
        altitude=100.0,
        field_layer=types.SimpleNamespace(code=1),
    )


def create_tree(species, **kwargs):
    params = dict(diameter_cm=30, height_m=20, region="southern", over_bark=True)
    params.update(kwargs)
    tree = SweTimber(species="betula", **params)
    tree.species = species
    return tree


def test_invalid_latitude_region():
    with pytest.raises(ValueError):
        SweTimber(species="betula", diameter_cm=10, height_m=10, region="central")


def test_validate_negative_diameter():
    with pytest.raises(ValueError):
        SweTimber(species="betula", diameter_cm=-1, height_m=10)


def test_validate_crown_base_height():
    with pytest.raises(ValueError):
        SweTimber(species="betula", diameter_cm=10, height_m=5, crown_base_height_m=6)


def test_getvolume_negative_returns_zero():
    tree = create_tree("betula")
    tree.diameter_cm = -5
    assert tree.getvolume() == 0


def test_getvolume_larch_large_site(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.BrandelVolume.get_volume", lambda **_: 1
    )
    tree = create_tree("larix sibirica", diameter_cm=60, swedish_site=make_site())
    assert tree.getvolume() == 1


def test_getvolume_larch_large_no_site(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.BrandelVolume.get_volume", lambda **_: 2
    )
    tree = create_tree("larix sibirica", diameter_cm=55)
    assert tree.getvolume() == 2


def test_getvolume_pine_small_tree(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.andersson_1954_volume_small_trees_pine",
        lambda *_: 3,
    )
    tree = create_tree("pinus sylvestris", diameter_cm=4, height_m=6)
    assert tree.getvolume() == 3


def test_getvolume_pine_site(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.BrandelVolume.get_volume", lambda **_: 4
    )
    tree = create_tree("pinus sylvestris", swedish_site=make_site())
    assert tree.getvolume() == 4


def test_getvolume_spruce_small_tree(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.andersson_1954_volume_small_trees_spruce",
        lambda *_: 5,
    )
    tree = create_tree("picea abies", diameter_cm=4, height_m=6)
    assert tree.getvolume() == 5


def test_getvolume_spruce_site(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.BrandelVolume.get_volume", lambda **_: 6
    )
    tree = create_tree("picea abies", swedish_site=make_site())
    assert tree.getvolume() == 6


def test_getvolume_birch_small_under(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.andersson_1954_volume_small_trees_birch_under_diameter_5_cm",
        lambda *_: 7,
    )
    tree = create_tree("betula", diameter_cm=3, height_m=4)
    assert tree.getvolume() == 7


def test_getvolume_birch_small_above(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.andersson_1954_volume_small_trees_birch_height_above_4_m",
        lambda *_: 8,
    )
    tree = create_tree("betula", diameter_cm=3, height_m=6)
    assert tree.getvolume() == 8


def test_getvolume_birch_site(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.BrandelVolume.get_volume", lambda **_: 9
    )
    tree = create_tree("betula", swedish_site=make_site())
    assert tree.getvolume() == 9


def test_getvolume_aspen(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.Eriksson_1973_volume_aspen_Sweden",
        lambda *_: 10,
    )
    tree = create_tree("populus tremula")
    assert tree.getvolume() == 10


def test_getvolume_lodgepole_small(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.andersson_1954_volume_small_trees_pine",
        lambda *_: 11,
    )
    tree = create_tree("pinus contorta", diameter_cm=4)
    assert tree.getvolume() == 11


def test_getvolume_lodgepole_large(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.Eriksson_1973_volume_lodgepole_pine_Sweden",
        lambda *_: 12,
    )
    tree = create_tree("pinus contorta")
    assert tree.getvolume() == 12


def test_getvolume_beech(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.matern_1975_volume_sweden_beech",
        lambda *_: 13,
    )
    tree = create_tree("fagus sylvatica")
    assert tree.getvolume() == 13


def test_getvolume_oak(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.matern_1975_volume_sweden_oak",
        lambda *_: 14,
    )
    tree = create_tree("quercus robur")
    assert tree.getvolume() == 14


def test_getvolume_default_small(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.andersson_1954_volume_small_trees_birch_height_above_4_m",
        lambda *_: 15,
    )
    tree = create_tree("betula", diameter_cm=3, height_m=5)
    tree.species = "unknown"
    assert tree.getvolume() == 15


def test_getvolume_default_site(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.BrandelVolume.get_volume", lambda **_: 16
    )
    tree = create_tree("betula", swedish_site=make_site())
    tree.species = "unknown"
    assert tree.getvolume() == 16


def test_getvolume_default_small_under(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.andersson_1954_volume_small_trees_birch_under_diameter_5_cm",
        lambda *_: 17,
    )
    tree = create_tree("betula", diameter_cm=3, height_m=4)
    tree.species = "unknown"
    assert tree.getvolume() == 17


def test_getvolume_default_no_site(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.BrandelVolume.get_volume", lambda **_: 18
    )
    tree = create_tree("betula")
    tree.species = "unknown"
    assert tree.getvolume() == 18


def test_validate_region_after_change():
    tree = create_tree("betula")
    tree.region = "central"
    with pytest.raises(ValueError):
        tree.validate()


def test_validate_species_after_change():
    tree = create_tree("betula")
    tree.species = "invalid"
    with pytest.raises(ValueError):
        tree.validate()
