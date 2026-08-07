"""Tests for the public :func:`basal_area_larger` (BAL) helper."""

import pytest

from pyforestry.base.helpers import basal_area_larger


def test_basal_area_larger_ties_share_strictly_larger_sum():
    # sizes 30, 20, 20, 10 with basal areas 3, 2, 2, 1.
    # BAL(30) = 0; both 20s see only the 30 -> 3 each (ties share); 10 sees 3+2+2 = 7.
    assert basal_area_larger([30, 20, 20, 10], [3, 2, 2, 1]) == [0.0, 3.0, 3.0, 7.0]


def test_basal_area_larger_preserves_input_order():
    # Unsorted input; the result is aligned to the input positions.
    # largest 30 -> 0; 20 -> 3; 10 -> 3 + 2 = 5.
    assert basal_area_larger([10, 30, 20], [1, 3, 2]) == [5.0, 0.0, 3.0]


def test_basal_area_larger_all_distinct_is_cumulative():
    assert basal_area_larger([1, 2, 3, 4], [1, 1, 1, 1]) == [3.0, 2.0, 1.0, 0.0]


def test_basal_area_larger_empty():
    assert basal_area_larger([], []) == []


def test_basal_area_larger_length_mismatch_raises():
    with pytest.raises(ValueError):
        basal_area_larger([1.0, 2.0], [1.0])
