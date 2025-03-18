from shapely.geometry import Point
import geopandas as gpd
from pyproj import Transformer
from importlib.resources import files

class RetrieveGeoCode:

    @staticmethod
    def getDistanceToCoast(lon, lat, epsg=4326):
        """
        Calculate the distance from a given point (lon, lat in the input CRS) 
        to the nearest coastline point. Internally, the calculation is done 
        in the metric projection EPSG:3857.
        
        Parameters:
            lon (float): Longitude (in the input CRS).
            lat (float): Latitude (in the input CRS).
            epsg (int): EPSG code for the input coordinates (default: 4326).
            
        Returns:
            float: Distance in kilometers to the nearest coastline.
        """
        # Load the coastline shapefile
        coast_gdf = gpd.read_file(files("Munin.Geo.Coastline").joinpath("SwedishCoastLine_NE_medium_clipped.shp"))
        
        # Ensure coastline data is in EPSG:4326 for consistency
        if coast_gdf.crs is None or coast_gdf.crs.to_epsg() != 4326:
            coast_gdf = coast_gdf.to_crs(epsg=4326)
        
        # Transform the input coordinates from the provided epsg to the internal metric CRS (EPSG:3857)
        transformer = Transformer.from_crs(epsg, 3857, always_xy=True)
        lon_metric, lat_metric = transformer.transform(float(lon), float(lat))
        point_metric = Point(lon_metric, lat_metric)
        
        # Reproject coastline data to EPSG:3857 for accurate metric calculations
        coast_gdf_metric = coast_gdf.to_crs(epsg=3857)
        
        # Calculate the minimum distance (in meters) from the point to the coastline
        distances = coast_gdf_metric.geometry.distance(point_metric)
        nearest_distance = distances.min()
        
        return nearest_distance / 1000  # Convert meters to kilometers


    @staticmethod
    def getClimateCode(lon, lat, epsg=4326):
        """
        Retrieve the climate zone code for a given coordinate (in the input CRS)
        by performing a spatial intersection in EPSG:3006.
        
        Parameters:
            lon (float): Longitude (in the input CRS).
            lat (float): Latitude (in the input CRS).
            epsg (int): EPSG code for the input coordinates (default: 4326).
        
        Returns:
            str or int: The climate zone label or 0 if no matching zone is found.
        """
        # Load the climate shapefile and reproject to EPSG:3006
        klimat_gdf = gpd.read_file(files('Munin.Geo.Climate').joinpath("Klimat.shp")).to_crs(epsg=3006)
        
        # Transform the input coordinates from the provided epsg to EPSG:3006
        transformer = Transformer.from_crs(epsg, 3006, always_xy=True)
        lon_proj, lat_proj = transformer.transform(float(lon), float(lat))
        point_proj = Point(lon_proj, lat_proj)
        
        # Mapping of climate zone codes to labels
        klimzon_mapping = {
            1: "M1",  # Maritime, West coast
            2: "M2",  # Maritime, East coast
            3: "M3",  # Maritime, Mountain range
            4: "K1",  # Continental, Middle Sweden
            5: "K2",  # Continental, Northern Sweden
            6: "K3"   # Continental, Southern Sweden
        }
        
        # Find the polygon that contains the transformed point
        klimat_polygon = klimat_gdf[klimat_gdf.contains(point_proj)]
        if klimat_polygon.empty:
            return 0
        else:
            return klimzon_mapping.get(klimat_polygon.iloc[0]['KLIMZON_'], 0)


    @staticmethod
    def getCountyCode(lon, lat, epsg=4326):
        """
        Retrieve the county code for a given coordinate (in the input CRS)
        by performing a spatial intersection in EPSG:3006.
        
        Parameters:
            lon (float): Longitude (in the input CRS).
            lat (float): Latitude (in the input CRS).
            epsg (int): EPSG code for the input coordinates (default: 4326).
        
        Returns:
            str or int: The county label or 0 if no matching county is found.
        """
        # Load the county shapefile and reproject to EPSG:3006
        dlanskod_gdf = gpd.read_file(files('Munin.Geo.Counties').joinpath('RT_Dlanskod.shp')).to_crs(epsg=3006)
        
        # Transform the input coordinates from the provided epsg to EPSG:3006
        transformer = Transformer.from_crs(epsg, 3006, always_xy=True)
        lon_proj, lat_proj = transformer.transform(float(lon), float(lat))
        point_proj = Point(lon_proj, lat_proj)
        
        # Mapping of county codes to labels
        county_mapping = {
            1: "Norrbottens lappmark (BD lappm)",
            2: "Norrbottens kustland (BD kust)",
            3: "Västerbottens lappmark (AC lappm)",
            4: "Västerbottens kustland (AC kust)",
            5: "Jämtland - Jämtlands landskap (Z)",
            6: "Jämtland - Härjedalens landskap (Z Härjed)",
            7: "Västernorrland - Ångermanlands landskap (Y Ångerm)",
            8: "Västernorrland - Medelpads landskap (Y Medelp)",
            9: "Gävleborg - Hälsinglands landskap (X Hälsingl)",
            10: "Gävleborg, övriga (X övr)",
            11: "Kopparberg (Dalarna), Sälen - Idre (W)",
            12: "Kopparberg (Dalarna), övriga (W övr)",
            13: "Värmland (S)",
            14: "Örebro (T)",
            15: "Västmanland (U)",
            16: "Uppsala (C)",
            17: "Stockholm (AB)",
            18: "Södermanland (D)",
            19: "Östergötland (E)",
            20: "Skaraborg (R)",
            21: "Älvsborg, Dalslands landskap (P)",
            22: "Älvsborg, Västergötlands landskap (P)",
            23: "Jönköping (F)",
            24: "Kronoberg (G)",
            25: "Kalmar (H)",
            26: "Västra Götalands (Göteborg - Bohuslän) (O)",
            27: "Halland (N)",
            28: "Kristianstad (L)",
            29: "Malmöhus (M)",
            30: "Blekinge (K)",
            31: "Gotland (I)"
        }
        
        # Find the polygon that contains the transformed point
        dlanskod_polygon = dlanskod_gdf[dlanskod_gdf.contains(point_proj)]
        if dlanskod_polygon.empty:
            return 0
        else:
            return county_mapping.get(dlanskod_polygon.iloc[0]['DLANSKOD'], 0)
