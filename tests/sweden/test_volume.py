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
