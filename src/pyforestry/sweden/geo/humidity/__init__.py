"""Interface for humidity lookups used by Swedish site models."""

import os

from .eriksson_1986 import eriksson_1986_humidity

shapefile_path = os.path.join(os.path.dirname(__file__), "humidity.shp")

__all__ = ["eriksson_1986_humidity", "shapefile_path"]
