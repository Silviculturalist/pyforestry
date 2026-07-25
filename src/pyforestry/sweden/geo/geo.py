"""Simple geographic utilities using Swedish shapefiles."""

from importlib.resources import as_file, files
from typing import Optional

import geopandas as gpd
from pyproj import Transformer
from shapely.geometry import Point

from pyforestry.sweden.site import Sweden


class RetrieveGeoCode:
    """Helper methods for querying Swedish geographic data."""

    @staticmethod
    def get_distance_to_coast_km(longitude: float, latitude: float, epsg: int = 4326) -> float:
        """
        Calculate the distance from a given point (lon/lat in the input CRS)
        to the nearest coastline point. Internally, the calculation is done
        in the metric projection EPSG:3857.

        Parameters:
            longitude (float): Longitude (in the input CRS).
            latitude (float): Latitude (in the input CRS).
            epsg (int): EPSG code for the input coordinates (default: 4326).

        Returns:
            float: Distance in kilometers to the nearest coastline.
        """
        # Load the coastline shapefile
        with as_file(
            files("pyforestry.sweden.geo.coastline").joinpath(
                "swedishcoastline_ne_medium_clipped.shp"
            )
        ) as coastline_path:
            coast_gdf = gpd.read_file(coastline_path)

        # Ensure coastline data is in EPSG:4326 for consistency
        if coast_gdf.crs is None or coast_gdf.crs.to_epsg() != 4326:
            coast_gdf = coast_gdf.to_crs(epsg=4326)

        # Transform the input coordinates from the provided
        # epsg to the internal metric CRS (EPSG:3857)
        transformer = Transformer.from_crs(epsg, 3857, always_xy=True)
        longitude_metric, latitude_metric = transformer.transform(
            float(longitude),
            float(latitude),
        )
        point_metric = Point(longitude_metric, latitude_metric)

        # Reproject coastline data to EPSG:3857 for accurate metric calculations
        coast_gdf_metric = coast_gdf.to_crs(epsg=3857)

        # Calculate the minimum distance (in meters) from the point to the coastline
        distances = coast_gdf_metric.geometry.distance(point_metric)
        nearest_distance = distances.min()

        return nearest_distance / 1000  # Convert meters to kilometers

    @staticmethod
    def get_climate_code(
        longitude: float,
        latitude: float,
        epsg: int = 4326,
    ) -> Optional[Sweden.ClimateZone]:
        """
        Retrieve the climate zone enum member for a given coordinate.

        Parameters:
            longitude (float): Longitude (in the input CRS).
            latitude (float): Latitude (in the input CRS).
            epsg (int): EPSG code for the input coordinates (default: 4326).

        Returns:
            Sweden.ClimateZone | None: The climate zone enum member or None if not found.
        """

        # Load the climate shapefile and reproject to EPSG:3006
        with as_file(
            files("pyforestry.sweden.geo.climate").joinpath("klimat.shp")
        ) as climatezone_path:
            klimat_gdf = gpd.read_file(climatezone_path).to_crs(epsg=3006)

        # Transform the input coordinates from the provided epsg to EPSG:3006
        transformer = Transformer.from_crs(epsg, 3006, always_xy=True)
        longitude_projected, latitude_projected = transformer.transform(
            float(longitude),
            float(latitude),
        )
        point_proj = Point(longitude_projected, latitude_projected)

        # Find the polygon that contains the transformed point
        klimat_polygon = klimat_gdf[klimat_gdf.contains(point_proj)]
        if klimat_polygon.empty:
            return None  # Return None if no matching zone is found
        else:
            climate_zone_code_int = klimat_polygon.iloc[0]["KLIMZON_"]
            # Lookup and return the enum member using the code (runtime use)
            return Sweden.ClimateZone.from_code(climate_zone_code_int)

    @staticmethod
    def get_county_code(
        longitude: float,
        latitude: float,
        epsg: int = 4326,
    ) -> Optional[Sweden.County]:
        """
        Retrieve the county enum member for a given coordinate.

        Parameters:
            longitude (float): Longitude (in the input CRS).
            latitude (float): Latitude (in the input CRS).
            epsg (int): EPSG code for the input coordinates (default: 4326).

        Returns:
            SwedenCounty | None: The corresponding SwedenCounty enum member or None if not found.
        """

        # Load the county shapefile and reproject to EPSG:3006
        with as_file(
            files("pyforestry.sweden.geo.counties").joinpath("rt_dlanskod.shp")
        ) as dlanskod_path:
            dlanskod_gdf = gpd.read_file(dlanskod_path).to_crs(epsg=3006)

        # Transform the input coordinates from the provided epsg to EPSG:3006
        transformer = Transformer.from_crs(epsg, 3006, always_xy=True)
        longitude_projected, latitude_projected = transformer.transform(
            float(longitude),
            float(latitude),
        )
        point_proj = Point(longitude_projected, latitude_projected)

        # Find the polygon that contains the transformed point
        dlanskod_polygon = dlanskod_gdf[dlanskod_gdf.contains(point_proj)]
        if dlanskod_polygon.empty:
            return None  # Return None if no matching polygon
        else:
            county_code_int = dlanskod_polygon.iloc[0]["DLANSKOD"]
            # Lookup and return the enum member using the code (runtime use)
            return Sweden.County.from_code(county_code_int)

    @staticmethod
    def getDistanceToCoast(lon, lat, epsg=4326):
        """Backward-compatible alias for :meth:`get_distance_to_coast_km`."""
        return RetrieveGeoCode.get_distance_to_coast_km(lon, lat, epsg)

    @staticmethod
    def getClimateCode(lon, lat, epsg=4326) -> Optional[Sweden.ClimateZone]:
        """Backward-compatible alias for :meth:`get_climate_code`."""
        return RetrieveGeoCode.get_climate_code(lon, lat, epsg)

    @staticmethod
    def getCountyCode(lon, lat, epsg=4326) -> Optional[Sweden.County]:
        """Backward-compatible alias for :meth:`get_county_code`."""
        return RetrieveGeoCode.get_county_code(lon, lat, epsg)
