"""Lorey's mean height as a primitive: a float that carries its precision.

The type was reached only through the aggregation that produces it, so its own
contract -- the refusal of a negative height, the precision surviving arithmetic
comparisons, the ``value`` accessor -- had never been stated.
"""

from __future__ import annotations

import copy

import pytest

from pyforestry.base.helpers.primitives import LoreysMeanHeight


def test_it_is_a_height_in_metres_that_behaves_like_a_float() -> None:
    height = LoreysMeanHeight(18.4, precision=0.6)

    assert height == pytest.approx(18.4)
    assert height.value == pytest.approx(18.4)
    assert height + 1.0 == pytest.approx(19.4)
    assert height > LoreysMeanHeight(12.0)


def test_the_precision_rides_along_and_defaults_to_none_claimed() -> None:
    """Zero means "no precision stated", which is what a bare value has."""
    assert LoreysMeanHeight(18.4).precision == 0.0
    assert LoreysMeanHeight(18.4, precision=0.6).precision == pytest.approx(0.6)


def test_a_negative_height_is_refused() -> None:
    """A basal-area weighted mean of non-negative heights cannot be negative."""
    with pytest.raises(ValueError, match="must be non-negative"):
        LoreysMeanHeight(-0.1)


def test_a_stand_with_no_measured_height_is_zero_not_an_error() -> None:
    """Nought is a real answer here -- no tree carried a height to weight."""
    assert LoreysMeanHeight(0.0) == 0.0


def test_it_survives_being_copied() -> None:
    """It rides inside a stand's metrics, and a checkpoint deep-copies those."""
    height = LoreysMeanHeight(18.4, precision=0.6)
    clone = copy.deepcopy(height)

    assert clone == pytest.approx(18.4)
    assert clone.precision == pytest.approx(0.6)
