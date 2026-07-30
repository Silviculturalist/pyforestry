"""The refusals and the degenerate cases of the competition geometry.

Two circles that do not overlap, one that sits wholly inside the other, a radius
of nought, a negative distance: each is a branch these functions already have,
and each answers a real question about a plot -- an edge-correction weight is
meaningless if the zone has no area, and a negative distance is a caller bug
rather than a stand.
"""

from __future__ import annotations

from math import acos, pi, sqrt

import pytest

from pyforestry.base.competition.geometry import (
    circle_intersection_area,
    fraction_of_circle_inside_circle,
)


class TestCircleIntersection:
    def test_disjoint_circles_share_nothing(self) -> None:
        assert circle_intersection_area(2.0, 3.0, 5.0) == 0.0  # externally tangent
        assert circle_intersection_area(2.0, 3.0, 9.0) == 0.0

    def test_a_contained_circle_shares_all_of_itself(self) -> None:
        """The smaller circle's whole area, including when they are concentric."""
        assert circle_intersection_area(1.0, 4.0, 0.0) == pytest.approx(pi)
        assert circle_intersection_area(4.0, 1.0, 2.5) == pytest.approx(pi)

    def test_a_circle_of_no_radius_shares_nothing(self) -> None:
        assert circle_intersection_area(0.0, 3.0, 1.0) == 0.0
        assert circle_intersection_area(3.0, 0.0, 1.0) == 0.0

    def test_overlapping_circles_share_the_closed_form_lens(self) -> None:
        """Two equal circles of radius r, centres d apart:

        ``A = 2 r^2 acos(d / 2r) - (d / 2) sqrt(4 r^2 - d^2)``.
        """
        radius, distance = 2.0, 2.0
        expected = 2 * radius**2 * acos(distance / (2 * radius)) - (distance / 2) * sqrt(
            4 * radius**2 - distance**2
        )

        shared = circle_intersection_area(radius, radius, distance)

        assert shared == pytest.approx(expected)
        assert 0.0 < shared < pi * radius**2

    def test_negative_geometry_is_refused(self) -> None:
        with pytest.raises(ValueError, match="Radii must be non-negative"):
            circle_intersection_area(-1.0, 2.0, 1.0)
        with pytest.raises(ValueError, match="Radii must be non-negative"):
            circle_intersection_area(1.0, -2.0, 1.0)
        with pytest.raises(ValueError, match="Distance must be non-negative"):
            circle_intersection_area(1.0, 2.0, -1.0)


class TestFractionInsideBoundary:
    def test_a_zone_wholly_inside_the_plot_is_all_of_it(self) -> None:
        assert fraction_of_circle_inside_circle(
            centre_offset_m=0.0, circle_radius_m=1.0, boundary_radius_m=10.0
        ) == pytest.approx(1.0)

    def test_a_zone_hanging_over_the_edge_is_part_of_it(self) -> None:
        fraction = fraction_of_circle_inside_circle(
            centre_offset_m=10.0, circle_radius_m=3.0, boundary_radius_m=10.0
        )
        assert 0.0 < fraction < 1.0

    def test_a_zone_wholly_outside_the_plot_is_none_of_it(self) -> None:
        assert (
            fraction_of_circle_inside_circle(
                centre_offset_m=20.0, circle_radius_m=2.0, boundary_radius_m=10.0
            )
            == 0.0
        )

    def test_a_zone_with_no_area_cannot_be_weighted(self) -> None:
        """Not zero: a weight is a share of the zone, and there is no zone."""
        with pytest.raises(ValueError, match="no area to weight"):
            fraction_of_circle_inside_circle(
                centre_offset_m=1.0, circle_radius_m=0.0, boundary_radius_m=10.0
            )

    def test_negative_geometry_is_refused(self) -> None:
        with pytest.raises(ValueError, match="must be non-negative"):
            fraction_of_circle_inside_circle(
                centre_offset_m=-1.0, circle_radius_m=1.0, boundary_radius_m=10.0
            )
        with pytest.raises(ValueError, match="must be non-negative"):
            fraction_of_circle_inside_circle(
                centre_offset_m=1.0, circle_radius_m=1.0, boundary_radius_m=-10.0
            )
