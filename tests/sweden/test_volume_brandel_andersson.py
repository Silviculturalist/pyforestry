import importlib

import pytest

from pyforestry.sweden.volume import andersson_1954, brandel_1990

# -- Tests for andersson_1954 -------------------------------------------------


def test_andersson_1954_all_functions():
    assert pytest.approx(0.0059904746, rel=1e-6) == (
        andersson_1954.andersson_1954_volume_small_trees_birch_height_above_4_m(4.0, 10.0)
    )
    assert pytest.approx(0.002047568, rel=1e-6) == (
        andersson_1954.andersson_1954_volume_small_trees_birch_under_diameter_5_cm(3.0, 4.0)
    )
    assert pytest.approx(0.0044363, rel=1e-6) == (
        andersson_1954.andersson_1954_volume_small_trees_pine(4.0, 5.0)
    )
    assert pytest.approx(0.0042177, rel=1e-6) == (
        andersson_1954.andersson_1954_volume_small_trees_spruce(4.0, 5.0)
    )


# -- Tests for brandel_1990 ---------------------------------------------------


def test_get_coefficients_south_under_bark():
    coeffs = brandel_1990.BrandelVolume.get_coefficients(
        part_of_sweden="south",
        latitude=55,
        altitude=None,
        fieldlayer_type=None,
        over_bark=False,
    )
    assert coeffs["Pine"] == brandel_1990.BrandelVolume.SouthPineUbCoeff
    assert coeffs["Spruce"] == brandel_1990.BrandelVolume.SouthSpruceUbCoeff
    assert coeffs["Birch"] == brandel_1990.BrandelVolume.SouthBirchUbCoeff


def test_get_coefficients_south_detailed_object_fieldlayer():
    class Dummy:
        code = 20

    coeffs = brandel_1990.BrandelVolume.get_coefficients(
        part_of_sweden="south",
        latitude=56,
        altitude=150,
        fieldlayer_type=Dummy(),
        over_bark=True,
    )
    assert coeffs["Birch"][0] == brandel_1990.BrandelVolume.BirchSouthWithLatitudeConstant[0]
    assert coeffs["Pine"][0] == brandel_1990.BrandelVolume.PineSouthWithLatitudeConstant[0]
    assert (
        coeffs["Spruce"][0] == brandel_1990.BrandelVolume.SpruceSouthWithfieldlayerTypeConstant[0]
    )


def test_get_coefficients_north_detailed_under_bark():
    coeffs = brandel_1990.BrandelVolume.get_coefficients(
        part_of_sweden="north",
        latitude=66,
        altitude=300,
        fieldlayer_type=1,
        over_bark=False,
    )
    assert coeffs["Pine"] == brandel_1990.BrandelVolume.SouthPineUbCoeff
    assert coeffs["Spruce"] == brandel_1990.BrandelVolume.SouthSpruceUbCoeff
    assert coeffs["Birch"] == brandel_1990.BrandelVolume.NorthBirchUbCoeff


def test_get_coefficients_south_lat_index_2_no_code():
    coeffs = brandel_1990.BrandelVolume.get_coefficients(
        part_of_sweden="south",
        latitude=59,
        altitude=200,
        fieldlayer_type=object(),
        over_bark=True,
    )
    assert coeffs["Pine"][0] == brandel_1990.BrandelVolume.PineSouthWithLatitudeConstant[2]


def test_get_coefficients_north_altitude_edges():
    coeffs_low = brandel_1990.BrandelVolume.get_coefficients(
        part_of_sweden="north",
        latitude=62,
        altitude=100,
        fieldlayer_type=1,
        over_bark=True,
    )
    assert coeffs_low["Pine"][0] == brandel_1990.BrandelVolume.PineNorthWithLatitudeConstant[0]

    coeffs_high = brandel_1990.BrandelVolume.get_coefficients(
        part_of_sweden="north",
        latitude=68,
        altitude=600,
        fieldlayer_type=1,
        over_bark=True,
    )
    assert (
        coeffs_high["Spruce"][0]
        == brandel_1990.BrandelVolume.SpruceNorthWithLatitudeAndAltitudeConstant[2][3]
    )


def test_get_coefficients_north_lat_index_one():
    coeffs = brandel_1990.BrandelVolume.get_coefficients(
        part_of_sweden="north",
        latitude=64,
        altitude=250,
        fieldlayer_type=1,
        over_bark=True,
    )
    assert coeffs["Pine"][0] == brandel_1990.BrandelVolume.PineNorthWithLatitudeConstant[1]


def test_internal_get_tree_volume_branches(monkeypatch):
    monkeypatch.setattr(brandel_1990.BrandelVolume, "get_volume_log", lambda *_, **__: 100)
    coeff = {"Pine": [], "Spruce": [], "Birch": []}
    assert brandel_1990.BrandelVolume._internal_get_tree_volume(
        10,
        5,
        "pinus sylvestris",
        coeff,
    ) == pytest.approx(0.1)
    assert brandel_1990.BrandelVolume._internal_get_tree_volume(
        10,
        5,
        "picea abies",
        coeff,
    ) == pytest.approx(0.1)
    assert brandel_1990.BrandelVolume._internal_get_tree_volume(
        10,
        5,
        "betula pendula",
        coeff,
    ) == pytest.approx(0.1)
    with pytest.raises(ValueError):
        brandel_1990.BrandelVolume._internal_get_tree_volume(10, 4, "pine", coeff)
    with pytest.raises(ValueError):
        brandel_1990.BrandelVolume._internal_get_tree_volume(10, 5, "unknown", coeff)


def test_get_volume_wrapper(monkeypatch):
    coeffs = {"Pine": [], "Spruce": [], "Birch": []}
    monkeypatch.setattr(
        brandel_1990.BrandelVolume,
        "get_coefficients",
        lambda *args, **kwargs: coeffs,
    )
    monkeypatch.setattr(
        brandel_1990.BrandelVolume,
        "_internal_get_tree_volume",
        lambda *a, **k: 0.5,
    )
    result = brandel_1990.BrandelVolume.get_volume(
        species="pine",
        diameter_cm=10,
        height_m=15,
        latitude=56,
        altitude=100,
        field_layer=1,
        over_bark=True,
    )
    assert result == 0.5


def test_get_volume_north_branch(monkeypatch):
    monkeypatch.setattr(
        brandel_1990.BrandelVolume,
        "get_coefficients",
        lambda *args, **kwargs: {"Pine": [], "Spruce": [], "Birch": []},
    )
    monkeypatch.setattr(
        brandel_1990.BrandelVolume,
        "_internal_get_tree_volume",
        lambda *a, **k: 1.0,
    )
    result = brandel_1990.BrandelVolume.get_volume(
        species="pine",
        diameter_cm=10,
        height_m=15,
        latitude=65,
        altitude=None,
        field_layer=None,
        over_bark=True,
    )
    assert result == 1.0


# -- Tests for volume package __init__ ---------------------------------------


def test_volume_module_lazy_loading_and_dir():
    volume = importlib.reload(importlib.import_module("pyforestry.sweden.volume"))
    from pyforestry.sweden.volume.naslund_1947 import NaslundVolume

    assert volume.__dir__() == sorted(volume.__all__)
    assert volume.NaslundVolume is NaslundVolume
    with pytest.raises(AttributeError):
        volume.does_not_exist  # noqa: B018
