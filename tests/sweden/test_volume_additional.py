import pytest

from pyforestry.sweden.timber.swe_timber import SweTimber
from pyforestry.sweden.volume.johnsson_1953 import johnsson_1953_volume_hybrid_aspen
from pyforestry.sweden.volume.naslund_1947 import NaslundFormFactor, NaslundVolume


def test_johnsson_1953_volume():
    vol = johnsson_1953_volume_hybrid_aspen(20, 15)
    assert pytest.approx(0.211354, rel=1e-6) == vol


def test_naslund_form_factor_invalid_region():
    with pytest.raises(ValueError):
        NaslundFormFactor.calculate(
            species="pinus sylvestris",
            height_m=20,
            diameter_cm=10,
            region="central",
        )


def test_naslund_volume_northern_birch():
    timber = SweTimber(
        species="betula",
        diameter_cm=25,
        height_m=20,
        region="northern",
        over_bark=True,
    )
    vol = NaslundVolume.calculate(timber)
    assert vol > 0
