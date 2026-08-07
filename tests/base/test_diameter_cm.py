import math

import pytest

from pyforestry.base.helpers.primitives import (
    basal_area_cm2_to_diameter_cm,
    basal_area_growth_cm2_to_diameter_growth_cm,
    diameter_growth_to_basal_area_growth_cm2,
    diameter_to_basal_area_cm2,
)


def test_diameter_to_basal_area_and_back():
    ba = diameter_to_basal_area_cm2(20.0)
    assert ba == pytest.approx(math.pi / 4.0 * 400.0)
    d = basal_area_cm2_to_diameter_cm(ba)
    assert d == pytest.approx(20.0)


def test_growth_conversions_round_trip():
    d = 25.0
    inc = 2.5
    ba_growth = diameter_growth_to_basal_area_growth_cm2(d, inc)
    inc_back = basal_area_growth_cm2_to_diameter_growth_cm(d, ba_growth)
    assert inc_back == pytest.approx(inc)


@pytest.mark.parametrize("diameter_cm", [-1.0, -0.01])
def test_negative_diameter_raises(diameter_cm):
    with pytest.raises(ValueError):
        diameter_to_basal_area_cm2(diameter_cm)


@pytest.mark.parametrize("basal_area_cm2", [-1.0, -0.01])
def test_negative_basal_area_raises(basal_area_cm2):
    with pytest.raises(ValueError):
        basal_area_cm2_to_diameter_cm(basal_area_cm2)


@pytest.mark.parametrize(
    ("diameter_cm", "diameter_growth_cm"),
    [(-1.0, 0.1), (10.0, -0.1)],
)
def test_negative_inputs_for_diameter_growth_raise(diameter_cm, diameter_growth_cm):
    with pytest.raises(ValueError):
        diameter_growth_to_basal_area_growth_cm2(diameter_cm, diameter_growth_cm)


@pytest.mark.parametrize(
    ("diameter_cm", "basal_area_growth_cm2"),
    [(-1.0, 1.0), (10.0, -1.0)],
)
def test_negative_inputs_for_basal_area_growth_raise(diameter_cm, basal_area_growth_cm2):
    with pytest.raises(ValueError):
        basal_area_growth_cm2_to_diameter_growth_cm(diameter_cm, basal_area_growth_cm2)
