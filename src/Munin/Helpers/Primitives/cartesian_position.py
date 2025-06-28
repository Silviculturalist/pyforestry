# ------------------------------------------------------------------------------
# Position: a small data container for location with optional CRS
# ------------------------------------------------------------------------------

from typing import Optional, Union
from math import cos, sin
from pyproj import CRS

class Position:
    """
    Represents an (X, Y, Z) coordinate with an optional CRS.
    
    If crs is None, the coordinate system is assumed to be non-geographic.
        
    """
    def __init__(self,
                 X: float,
                 Y: float,
                 Z: Optional[float] = 0.0,
                 crs: Optional[CRS] = None):
        self.X = X
        self.Y = Y
        self.Z = Z
        self.crs = crs
        self.coordinate_system = 'cartesian'

    @classmethod
    def from_polar(cls, r: float, theta: float, z: Optional[float] = 0.0):
        """
        Create a Position using polar coordinates.

        Theta is assumed to be in radians.
        The resulting Position has no CRS.
        """
        x = r * cos(theta)
        y = r * sin(theta)
        obj = cls(x, y, z, crs=None)
        
        return obj

    def __repr__(self):
        return f"Position(X={self.X}, Y={self.Y}, Z={self.Z}, crs={self.crs})"


    @staticmethod
    def _set_position(pos_in: Union['Position',
                                    tuple[float, float],
                                    tuple[float, float, float],
                                    None] = None) -> Optional['Position']:
        """
        Internal helper to standardize a user-provided position or tuple
        into a Position instance, or return None if no valid position is given.
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
