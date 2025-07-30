"""Objects describing a collection of trees recorded on a plot."""

from math import pi, sqrt
from typing import List, Optional, Union

from pyforestry.base.helpers import (
    AngleCount,
    Position,
    SiteBase,
    Tree,
)

# ------------------------------------------------------------------------------
# Plot: a set of representation trees over a circular or known-area region
# ------------------------------------------------------------------------------


class CircularPlot:
    """
    Contains information from a (usually) circular plot in a stand.

    Attributes:
    -----------
    id : int | str
        An identifier for this plot.
    position : Position | None
        The location of the plot center (if known).
    radius_m : float | None
        The radius of the circular plot in meters (if known).
    occlusion : float
        Portion [0-1] of the stand to be adjusted for being outside of the stand. Adjustment is
    area_m2 : float | None
        The area of the plot in m² (if known). Must supply either radius_m or area_m2.
    site : SiteBase | None
        Reference to a site object, if any.
    trees : list[Tree]
        The trees recorded on this plot (each possibly representing multiple stems).
    """

    def __init__(
        self,
        id: Union[int, str],
        occlusion: float = 0.0,
        position: Optional[Position] = None,
        radius_m: Optional[float] = None,
        area_m2: Optional[float] = None,
        site: Optional[SiteBase] = None,
        AngleCount: Optional[List[AngleCount]] = None,
        trees: Optional[List[Tree]] = None,
    ):
        """Create a new :class:`CircularPlot` instance.

        Parameters
        ----------
        id
            Identifier for the plot.
        occlusion
            Portion ``[0,1)`` of the plot that lies outside the stand.
        position
            Coordinates of the plot centre if known.
        radius_m
            Radius of the plot in metres.
        area_m2
            Plot area in square metres.
        site
            Optional reference to a :class:`SiteBase` object.
        AngleCount
            Optional list of :class:`AngleCount` tally objects.
        trees
            Collection of :class:`Tree` objects describing the
            recorded trees.
        """
        if id is None:
            raise ValueError("Plot must be given an ID (integer or string).")

        self.id = id
        self.position = position
        self.site = site

        if not 0 <= occlusion < 1:
            raise ValueError("Plot must have [0,0.99] occlusion!")
        self.occlusion = occlusion

        self.AngleCount = AngleCount if AngleCount is not None else []

        self.trees = trees if trees is not None else []

        # Must have either radius or area
        if radius_m is None and area_m2 is None:
            raise ValueError("Plot cannot be created without either a radius_m or an area_m2!")

        if radius_m is not None:
            self.radius_m = radius_m

        if area_m2 is not None:
            self.area_m2 = area_m2

        if radius_m is not None and area_m2 is None:
            self.area_m2 = pi * (radius_m**2)
        else:
            self.radius_m = sqrt(self.area_m2 / pi)

        # If both were given, verify consistency
        if radius_m is not None and area_m2 is not None:
            # Check the difference
            correct_area = pi * (radius_m**2)
            if abs(correct_area - area_m2) > 1e-6:
                raise ValueError(
                    f"Mismatch: given radius {radius_m} => area {correct_area:.6f}, "
                    f"but you specified {area_m2:.6f}."
                )

    @property
    def area_ha(self) -> float:
        """
        Returns the plot area in hectares.
        """
        return self.area_m2 / 10_000.0

    def __repr__(self):
        """Return a concise string representation of the plot."""
        return (
            f"Plot(id={self.id}, radius_m={getattr(self, 'radius_m', None)}, "
            f"area_m2={self.area_m2:.2f}, #trees={len(self.trees)})"
        )
