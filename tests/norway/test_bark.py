import math

import pytest

from pyforestry.base.helpers.primitives import Diameter_cm
from pyforestry.norway.bark import (
    braastad_1966_birch_norway_bark_thickness,
    brantseg_1967_scots_pine_norway_bark_thickness,
    hansen_2023_birch_norway_bark_thickness,
    hansen_2023_norway_spruce_norway_bark_thickness,
    hansen_2023_scots_pine_norway_bark_thickness,
    vestjordet_1967_norway_spruce_norway_bark_thickness,
)


def test_hansen_bark_equations_numeric():
    spruce = hansen_2023_norway_spruce_norway_bark_thickness(25.0, 20.0)
    pine = hansen_2023_scots_pine_norway_bark_thickness(25.0, 20.0)
    birch = hansen_2023_birch_norway_bark_thickness(25.0, 20.0)
    assert spruce == pytest.approx(0.2324 + 0.0068 * 25.0 + 0.0399 * 20.0)
    assert pine == pytest.approx(0.2931 - 0.0405 * 25.0 + 0.1213 * 20.0)
    assert birch == pytest.approx(-0.0483 + 0.0050 * 25.0 + 0.0846 * 20.0)


def test_hansen_diameter_cm_validation_and_warnings():
    with pytest.warns(UserWarning):
        value = hansen_2023_birch_norway_bark_thickness(
            Diameter_cm(20.0, over_bark=True, measurement_height_m=1.0), 10.0
        )
    assert value > 0
    with pytest.raises(ValueError):
        hansen_2023_birch_norway_bark_thickness(Diameter_cm(20.0, over_bark=False), 10.0)
    with pytest.raises(TypeError):
        hansen_2023_birch_norway_bark_thickness("20", 10.0)  # type: ignore[arg-type]
    assert hansen_2023_birch_norway_bark_thickness(0.0, 10.0) == 0.0


def test_brantseg_bark_equation_behaviour():
    assert brantseg_1967_scots_pine_norway_bark_thickness(10.0, 0.0) == 0.0
    with pytest.raises(ValueError):
        brantseg_1967_scots_pine_norway_bark_thickness(-1.0, 20.0)
    with pytest.raises(TypeError):
        brantseg_1967_scots_pine_norway_bark_thickness(None, 20.0)  # type: ignore[arg-type]
    with pytest.warns(UserWarning):
        value = brantseg_1967_scots_pine_norway_bark_thickness(
            Diameter_cm(20.0, measurement_height_m=2.0),
            20.0,
        )
    assert value > 0.0


def test_vestjordet_bark_equation_behaviour():
    assert vestjordet_1967_norway_spruce_norway_bark_thickness(10.0, 0.0) == 0.0
    with pytest.raises(ValueError):
        vestjordet_1967_norway_spruce_norway_bark_thickness(-1.0, 20.0)
    with pytest.raises(ValueError):
        vestjordet_1967_norway_spruce_norway_bark_thickness(
            Diameter_cm(20.0, over_bark=False),
            20.0,
        )
    with pytest.raises(TypeError):
        vestjordet_1967_norway_spruce_norway_bark_thickness(None, 20.0)  # type: ignore[arg-type]
    with pytest.warns(UserWarning):
        value_warn = vestjordet_1967_norway_spruce_norway_bark_thickness(
            Diameter_cm(20.0, measurement_height_m=2.0),
            20.0,
        )
    assert value_warn >= 0.0
    value = vestjordet_1967_norway_spruce_norway_bark_thickness(20.0, 25.0)
    assert math.isfinite(value)
    assert value >= 0.0


def test_vestjordet_bark_value_and_minimum_floor():
    """Pin Vestjordet double bark and its 5%-of-diameter floor (guards a 10x floor bug).

    The minimum double bark is a numerical safeguard of ``0.05 * dbh_cm`` mm (not
    from Vestjordet 1967); an earlier ``* 10.0`` made it ``0.5 * dbh_cm`` mm and
    inflated thin/tall trees tenfold.
    """
    # d=20, h=25: polynomial (9.2883 mm -> 0.92883 cm) sits above the floor.
    d, h = 20.0, 25.0
    poly_mm = (
        -0.34 + 0.831648 * d - 0.002832 * d * d - 0.010112 * h * h + 0.700203 * d * d / (h * h)
    )
    assert vestjordet_1967_norway_spruce_norway_bark_thickness(d, h) == pytest.approx(
        poly_mm / 10.0
    )
    # d=5, h=25: polynomial is negative, so the floor applies: 0.05*5 mm = 0.025 cm
    # (the 10x-inflated floor would have returned 0.25 cm).
    assert vestjordet_1967_norway_spruce_norway_bark_thickness(5.0, 25.0) == pytest.approx(0.025)


def test_braastad_bark_equation_behaviour():
    with pytest.raises(ValueError):
        braastad_1966_birch_norway_bark_thickness(10.0, -1.0)
    with pytest.raises(ValueError):
        braastad_1966_birch_norway_bark_thickness(-1.0, 10.0)
    with pytest.raises(ValueError):
        braastad_1966_birch_norway_bark_thickness(Diameter_cm(10.0, over_bark=False), 10.0)
    with pytest.raises(TypeError):
        braastad_1966_birch_norway_bark_thickness(None, 10.0)  # type: ignore[arg-type]
    with pytest.warns(UserWarning):
        value = braastad_1966_birch_norway_bark_thickness(
            Diameter_cm(20.0, over_bark=True, measurement_height_m=2.0),
            20.0,
        )
    assert value > 0.0
    assert braastad_1966_birch_norway_bark_thickness(20.0, 20.0) > 0.0


def test_hansen_bark_target_diameter_validation_and_zero_paths():
    with pytest.raises(TypeError):
        hansen_2023_norway_spruce_norway_bark_thickness(20.0, "10.0")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        hansen_2023_norway_spruce_norway_bark_thickness(20.0, -1.0)
    with pytest.raises(ValueError):
        hansen_2023_scots_pine_norway_bark_thickness(-1.0, 10.0)

    assert hansen_2023_norway_spruce_norway_bark_thickness(20.0, 0.0) == 0.0
    assert hansen_2023_scots_pine_norway_bark_thickness(20.0, 0.0) == 0.0
