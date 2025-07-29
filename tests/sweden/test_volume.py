import math

import pytest

from pyforestry.sweden.timber import SweTimber
from pyforestry.sweden.volume import (
    BrandelVolume,
    Eriksson_1973_volume_aspen_Sweden,
    Eriksson_1973_volume_lodgepole_pine_Sweden,
    NaslundFormFactor,
    NaslundVolume,
    andersson_1954_volume_small_trees_birch_height_above_4_m,
    carbonnier_1954_volume_larch,
    matern_1975_volume_sweden_beech,
    matern_1975_volume_sweden_oak,
)


def test_naslund_volume_southern_pine():
    timber = SweTimber(
        species="pinus sylvestris",
        diameter_cm=25,
        height_m=20,
        region="southern",
        over_bark=True,
    )
    vol = NaslundVolume.calculate(timber)
    assert isinstance(vol, float)
    assert vol > 0


def test_naslund_form_factor_invalid_diameter():
    with pytest.raises(ValueError):
        NaslundFormFactor.calculate(
            species="pinus sylvestris",
            height_m=20,
            diameter_cm=3,
        )


def test_naslund_form_factor_southern_birch():
    ff = NaslundFormFactor.calculate(
        species="betula",
        height_m=20,
        diameter_cm=25,
        over_bark=True,
    )
    assert 0 < ff < 1


def test_brandel_volume_log():
    # Example coefficients for southern pine (adjust based on your model)
    coeff = [-1.38903, 1.84493, 0.06563, 2.02122, -1.01095]
    diameter_cm = 40
    height_m = 25
    volume = BrandelVolume.get_volume_log(coeff, diameter_cm, height_m)
    assert isinstance(volume, float)
    assert volume > 0


def test_get_volume_log_invalid_height():
    coeff = [-1.38903, 1.84493, 0.06563, 2.02122, -1.01095]
    with pytest.raises(ValueError):
        BrandelVolume.get_volume_log(coeff, 30, 1.0)


def test_get_coefficients_north_over_bark():
    coeffs = BrandelVolume.get_coefficients(
        part_of_sweden="north",
        latitude=61.0,
        altitude=None,
        fieldlayer_type=None,
        over_bark=True,
    )
    assert coeffs["Pine"] == BrandelVolume.NorthPineCoeff
    assert coeffs["Spruce"] == BrandelVolume.NorthSpruceCoeff
    assert coeffs["Birch"] == BrandelVolume.NorthBirchCoeff


def test_get_volume_with_site():
    vol = BrandelVolume.get_volume(
        species="pinus sylvestris",
        diameter_cm=30,
        height_m=20,
        latitude=58.0,
        altitude=100,
        field_layer=1,
        over_bark=True,
    )
    assert isinstance(vol, float)
    assert vol > 0


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


def test_matern_1975_oak_large_tree():
    diameter = 35
    height = 15
    expected = (
        0.03522 * diameter**2 * height + 0.08772 * diameter * height - 0.04905 * diameter**2
    ) / 1000
    result = matern_1975_volume_sweden_oak(diameter, height)
    assert math.isclose(result, expected, rel_tol=1e-9)


def test_matern_1975_oak_small_tree():
    diameter = 35
    height = 8
    expected = (
        0.03522 * diameter**2 * height
        + 0.08772 * diameter * height
        - 0.04905 * diameter**2
        + ((1 - (height / 10)) ** 2)
        * (
            0.01682 * diameter**2 * height
            + 0.01108 * diameter * height
            - 0.02167 * diameter * (height**2)
            + 0.04905 * diameter**2
        )
    ) / 1000
    result = matern_1975_volume_sweden_oak(diameter, height)
    assert math.isclose(result, expected, rel_tol=1e-9)


def test_matern_1975_beech_exact():
    diameter = 35
    height = 25
    expected = (
        0.01275 * diameter**2 * height
        + 0.12368 * diameter**2
        + 0.0004701 * diameter**2 * height**2
        + 0.00622 * diameter * height**2
    ) / 1000
    result = matern_1975_volume_sweden_beech(diameter, height)
    assert math.isclose(result, expected, rel_tol=1e-9)
