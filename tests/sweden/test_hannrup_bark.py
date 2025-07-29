import warnings

import pytest

from pyforestry.base.helpers.primitives import Diameter_cm
from pyforestry.sweden.bark.hannrup_2004 import (
    Hannrup_2004_bark_picea_abies_sweden,
    Hannrup_2004_bark_pinus_sylvestris_sweden,
)


def test_pine_bark_valid_and_errors():
    d = Diameter_cm(30, over_bark=True, measurement_height_m=1.3)
    assert Hannrup_2004_bark_pinus_sylvestris_sweden(d, 60, 100) > 2

    with pytest.raises(ValueError):
        Hannrup_2004_bark_pinus_sylvestris_sweden(
            Diameter_cm(30, over_bark=False, measurement_height_m=1.3), 60, 100
        )

    with pytest.raises(TypeError):
        Hannrup_2004_bark_pinus_sylvestris_sweden(object(), 60, 100)

    with pytest.raises(ValueError):
        Hannrup_2004_bark_pinus_sylvestris_sweden(300, 60, -1)

    with pytest.raises(ValueError):
        Hannrup_2004_bark_pinus_sylvestris_sweden(-10, 60, 100)

    # ensure branch for h > htg
    assert Hannrup_2004_bark_pinus_sylvestris_sweden(50, 70, 600) > 2

    with warnings.catch_warnings(record=True) as rec:
        Hannrup_2004_bark_pinus_sylvestris_sweden(300, 50, 100)
        assert any("Latitude" in str(w.message) for w in rec)

    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        Hannrup_2004_bark_pinus_sylvestris_sweden(
            Diameter_cm(30, over_bark=True, measurement_height_m=1.5), 60, 100
        )
        assert any("measurementheight" in str(w.message) for w in rec)

    # term_lat <= 0 triggers early return
    assert Hannrup_2004_bark_pinus_sylvestris_sweden(300, 200, 150) == 2.0


def test_spruce_bark_valid_and_errors():
    assert Hannrup_2004_bark_picea_abies_sweden(250, 300) > 2
    with pytest.raises(ValueError):
        Hannrup_2004_bark_picea_abies_sweden(-1, 300)
    with pytest.raises(ValueError):
        Hannrup_2004_bark_picea_abies_sweden(250, 0)
    with pytest.raises(TypeError):
        Hannrup_2004_bark_picea_abies_sweden("bad", 300)

    with pytest.raises(ValueError):
        Hannrup_2004_bark_picea_abies_sweden(
            250,
            Diameter_cm(30, over_bark=False, measurement_height_m=1.3),
        )

    with pytest.raises(TypeError):
        Hannrup_2004_bark_picea_abies_sweden(250, object())

    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        Hannrup_2004_bark_picea_abies_sweden(
            250,
            Diameter_cm(30, over_bark=True, measurement_height_m=1.5),
        )
        assert any("measurement height" in str(w.message) for w in rec)
