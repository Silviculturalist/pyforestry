"""Module for cartesian coordinate operations.

This module provides the Position class for handling 2D/3D coordinates,
including construction from cartesian or polar inputs, optional CRS support,
and utility methods for representation and input standardization.
"""

from math import cos, sin
from typing import Optional, Union

from pyproj import CRS


class Position:
    """Container for an (X, Y, Z) coordinate with optional CRS.

    Attributes:
        X (float): X-coordinate (easting) in specified CRS or local units.
        Y (float): Y-coordinate (northing) in specified CRS or local units.
        Z (float): Elevation or third dimension value; defaults to 0.0.
        crs (Optional[CRS]): Coordinate Reference System for interpreting coordinates.
        coordinate_system (str): Underlying coordinate system type, always 'cartesian'.
    """

    def __init__(self, X: float, Y: float, Z: Optional[float] = 0.0, crs: Optional[CRS] = None):
        """Initialize a Position.

        Args:
            X (float): X-coordinate value.
            Y (float): Y-coordinate value.
            Z (Optional[float], optional): Z-coordinate or elevation; defaults to 0.0.
            crs (Optional[CRS], optional): Coordinate reference system; defaults to None.
        """
        self.X = X
        self.Y = Y
        self.Z = Z
        self.crs = crs
        self.coordinate_system = "cartesian"

    @classmethod
    def from_polar(cls, r: float, theta: float, z: Optional[float] = 0.0):
        """Create a Position from polar coordinates.

        Converts radial distance and angle to cartesian X/Y.

        Args:
            r (float): Radial distance from origin.
            theta (float): Angle in radians from X-axis.
            z (Optional[float], optional): Z-coordinate; defaults to 0.0.

        Returns:
            Position: New Position instance in cartesian space.
        """
        x = r * cos(theta)
        y = r * sin(theta)
        obj = cls(x, y, z, crs=None)

        return obj

    def __repr__(self):
        """Return unambiguous string representation of Position.

        Returns:
            str: Formatted string including X, Y, Z, and CRS.
        """
        return f"Position(X={self.X}, Y={self.Y}, Z={self.Z}, crs={self.crs})"

    @staticmethod
    def _set_position(
        pos_in: Union["Position", tuple[float, float], tuple[float, float, float], None] = None,
    ) -> Optional["Position"]:
        """Standardize input into a Position or return None.

        Args:
            pos_in (Union[Position, tuple, None]): Position instance or coordinate tuple.

        Returns:
            Optional[Position]: Input as Position, constructed if tuple, or None.
        Raises:
            ValueError: If tuple length is not 2 or 3.
            TypeError: If input type is unsupported.
        """
        if pos_in is None:
            return None

        if isinstance(pos_in, Position):
            return pos_in

        if isinstance(pos_in, tuple):
            if len(pos_in) == 2:
                return Position(X=pos_in[0], Y=pos_in[1], Z=0.0)
            elif len(pos_in) == 3:
                return Position(X=pos_in[0], Y=pos_in[1], Z=pos_in[2])
            else:
                raise ValueError("Position tuple must be length 2 or 3 (x, y, [z]).")

        raise TypeError("Position must be a Position or a tuple of floats (x, y, [z]).")
