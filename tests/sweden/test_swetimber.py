import pytest

from pyforestry.sweden.timber.swe_timber import SweTimber


def create_tree(species, **kwargs):
    params = dict(diameter_cm=30, height_m=20, region="southern", over_bark=True)
    params.update(kwargs)
    tree = SweTimber(species="betula", **params)
    tree.species = species  # bypass strict validation for testing branches
    return tree


@pytest.mark.parametrize(
    "species,expected",
    [
        ("larix sibirica", 1.0),
        ("pinus sylvestris", 2.0),
        ("picea abies", 3.0),
        ("betula", 4.0),
        ("populus tremula", 5.0),
        ("pinus contorta", 6.0),
        ("fagus sylvatica", 7.0),
        ("quercus robur", 8.0),
    ],
)
def test_getvolume_branches(monkeypatch, species, expected):
    def fake_brandel(**_):
        return expected

    def fake_larch(*_):
        return expected

    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.BrandelVolume.get_volume", fake_brandel
    )
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.carbonnier_1954_volume_larch",
        fake_larch,
    )
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.Eriksson_1973_volume_aspen_Sweden",
        lambda *_: expected,
    )
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.Eriksson_1973_volume_lodgepole_pine_Sweden",
        lambda *_: expected,
    )
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.andersson_1954_volume_small_trees_pine",
        lambda *_: expected,
    )
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.andersson_1954_volume_small_trees_spruce",
        lambda *_: expected,
    )
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.andersson_1954_volume_small_trees_birch_height_above_4_m",
        lambda *_: expected,
    )
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.andersson_1954_volume_small_trees_birch_under_diameter_5_cm",
        lambda *_: expected,
    )
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.matern_1975_volume_sweden_beech",
        lambda *_: expected,
    )
    monkeypatch.setattr(
        "pyforestry.sweden.timber.swe_timber.matern_1975_volume_sweden_oak",
        lambda *_: expected,
    )
    tree = create_tree(species)
    vol = tree.getvolume()
    assert vol == expected


def test_invalid_region():
    with pytest.raises(ValueError):
        SweTimber(species="pinus sylvestris", diameter_cm=10, height_m=10, region="central")
