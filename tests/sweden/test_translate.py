import math

import pytest

from pyforestry.sweden.siteindex.translate import (
    Leijon_Pine_to_Spruce,
    Leijon_Spruce_to_Pine,
    agestam_1985_si_translation_pine_to_birch,
    agestam_1985_si_translation_spruce_to_birch,
)


def test_leijon_pine_to_spruce_basic():
    result = Leijon_Pine_to_Spruce(15)
    expected = math.exp(-0.9596 * math.log(150) + 0.01171 * 150 + 7.9209) / 10
    assert math.isclose(result, expected, rel_tol=1e-6)


def test_leijon_pine_to_spruce_warning():
    with pytest.warns(UserWarning):
        Leijon_Pine_to_Spruce(5)


def test_leijon_spruce_to_pine_basic():
    result = Leijon_Spruce_to_Pine(20)
    expected = math.exp(1.6967 * math.log(200) - 0.005179 * 200 - 2.5397) / 10
    assert math.isclose(result, expected, rel_tol=1e-6)


def test_leijon_spruce_to_pine_warning():
    with pytest.warns(UserWarning):
        Leijon_Spruce_to_Pine(40)


def test_agestam_translations():
    assert math.isclose(
        agestam_1985_si_translation_pine_to_birch(20),
        ((0.736 * (20 * 10)) - 21.1) / 10,
        rel_tol=1e-6,
    )
    assert math.isclose(
        agestam_1985_si_translation_spruce_to_birch(20),
        ((0.382 * (20 * 10)) + 75.8) / 10,
        rel_tol=1e-6,
    )
