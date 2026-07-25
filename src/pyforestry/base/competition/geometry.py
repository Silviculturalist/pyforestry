"""Circle geometry shared by the influence-zone indices and the edge correction.

Two operations are needed repeatedly:

* the area two overlapping circles share (crown/influence-zone overlap, ``O_ij``);
* the fraction of a circle that lies inside another circle (the proportional-area
  edge weight for a subject tree whose competition zone extends past the plot
  boundary).

Both are closed-form; no numerical integration is involved.
"""

from math import acos, isclose, pi, sin, sqrt

__all__ = [
    "circle_intersection_area",
    "circle_overlap_length",
    "fraction_of_circle_inside_circle",
]


def circle_intersection_area(radius_a_m: float, radius_b_m: float, distance_m: float) -> float:
    """Area shared by two circles (m^2).

    The standard circular-segment result: for centres ``d`` apart and radii
    ``r_a``, ``r_b`` the lens area is the sum of the two circular segments cut off
    by the radical line.

    Args:
        radius_a_m: Radius of the first circle (m).
        radius_b_m: Radius of the second circle (m).
        distance_m: Distance between the two centres (m).

    Returns:
        The shared area in m^2: ``0.0`` when the circles are disjoint, and the
        area of the smaller circle when one contains the other.

    Raises:
        ValueError: If a radius or the distance is negative.
    """
    if radius_a_m < 0 or radius_b_m < 0:
        raise ValueError("Radii must be non-negative.")
    if distance_m < 0:
        raise ValueError("Distance must be non-negative.")

    r_a, r_b, d = float(radius_a_m), float(radius_b_m), float(distance_m)
    if r_a == 0.0 or r_b == 0.0:
        return 0.0
    if d >= r_a + r_b:  # disjoint (or externally tangent)
        return 0.0
    if d <= abs(r_a - r_b):  # one circle sits wholly inside the other
        return pi * min(r_a, r_b) ** 2

    # Half-angles subtended at each centre by the radical line.
    alpha = acos((d * d + r_a * r_a - r_b * r_b) / (2.0 * d * r_a))
    beta = acos((d * d + r_b * r_b - r_a * r_a) / (2.0 * d * r_b))
    # Each term is a circular segment: sector area minus triangle area.
    segment_a = r_a * r_a * (alpha - 0.5 * sin(2.0 * alpha))
    segment_b = r_b * r_b * (beta - 0.5 * sin(2.0 * beta))
    return segment_a + segment_b


def circle_overlap_length(radius_a_m: float, radius_b_m: float, distance_m: float) -> float:
    """Linear overlap of two circles along the line joining their centres (m).

    ``r_a + r_b - d``, clamped at zero. This is the quantity Staebler (1951)
    sums: the length by which a competitor's influence zone reaches into the
    subject tree's zone.

    Args:
        radius_a_m: Radius of the subject tree's influence zone (m).
        radius_b_m: Radius of the competitor's influence zone (m).
        distance_m: Distance between the two stems (m).

    Returns:
        The overlap length in m, or ``0.0`` when the zones do not meet.
    """
    return max(0.0, float(radius_a_m) + float(radius_b_m) - float(distance_m))


def fraction_of_circle_inside_circle(
    centre_offset_m: float,
    circle_radius_m: float,
    boundary_radius_m: float,
) -> float:
    """Fraction of a circle that falls inside a bounding circle.

    Used for proportional-area edge weighting on a circular plot: the subject
    tree sits ``centre_offset_m`` from the plot centre and carries a competition
    zone of ``circle_radius_m``; the plot has radius ``boundary_radius_m``. The
    returned fraction is the share of that competition zone that was actually
    observable.

    Args:
        centre_offset_m: Distance from the plot centre to the subject tree (m).
        circle_radius_m: Radius of the subject tree's competition zone (m).
        boundary_radius_m: Radius of the plot (m).

    Returns:
        A fraction in ``(0, 1]``. ``1.0`` when the zone lies wholly inside the
        plot. Never returns ``0.0``: a competition zone is centred on a tree that
        is itself in the plot, so some of it is always inside.

    Raises:
        ValueError: If any argument is negative, or the zone radius is zero.
    """
    if centre_offset_m < 0 or circle_radius_m < 0 or boundary_radius_m < 0:
        raise ValueError("Offsets and radii must be non-negative.")
    if circle_radius_m == 0:
        raise ValueError("A competition zone of zero radius has no area to weight.")
    inside = circle_intersection_area(circle_radius_m, boundary_radius_m, centre_offset_m)
    fraction = inside / (pi * circle_radius_m**2)
    # Guard against float drift just above 1.0 for a wholly-contained zone.
    if fraction > 1.0 and isclose(fraction, 1.0, rel_tol=1e-9):
        return 1.0
    return fraction


def mean_spacing_m(stems_per_ha: float) -> float:
    """Mean distance between neighbouring stems (m) for a given density.

    ``sqrt(10000 / N)``, the square-spacing equivalent used by Lee & Gadow (1997)
    to scale a dynamic competition-zone radius.

    Args:
        stems_per_ha: Stem density (trees/ha). Must be positive.

    Returns:
        Mean spacing in metres.

    Raises:
        ValueError: If ``stems_per_ha`` is not positive.
    """
    if stems_per_ha <= 0:
        raise ValueError("stems_per_ha must be positive.")
    return sqrt(10000.0 / float(stems_per_ha))
