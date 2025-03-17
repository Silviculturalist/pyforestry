from shapely.geometry import Point
import geopandas as gpd
from pyproj import Transformer
from importlib.resources import files

class RetrieveGeoCode:

    @staticmethod
    def getDistanceToCoast(lon, lat): 
        """
        Calculate the distance from a given point (lon, lat) to the nearest point on a coastline.

        Parameters:
        lon (float): Longitude of the point.
        lat (float): Latitude of the point.
        coast_path (str): Path to the shapefile containing the coastline.

        Returns:
        float: Distance in kilometers from the point to the nearest point on the coastline.
        """
        # Load the coastline shapefile
        coast_gdf = gpd.read_file(files("Munin.Geo.Coastline").joinpath("SwedishCoastLine_NE_medium_clipped.shp"))

        # Ensure the CRS is WGS 84
        if coast_gdf.crs is None or coast_gdf.crs.to_string() != 'EPSG:4326':
            coast_gdf = coast_gdf.to_crs(epsg=4326)

        # Create a Shapely Point object for the input coordinates
        point = Point(lon, lat)

        # Reproject the data to a metric CRS for accurate distance measurement
        metric_crs = 'EPSG:3857'  # Web Mercator projection
        coast_gdf_metric = coast_gdf.to_crs(metric_crs)
        point_metric = gpd.GeoSeries([point], crs='EPSG:4326').to_crs(metric_crs).iloc[0]

        # Calculate the distance to the nearest point on the coastline
        distances = coast_gdf_metric.geometry.apply(lambda line: line.distance(point_metric))
        nearest_distance = distances.min()

        return nearest_distance/1000





    @staticmethod
    def getClimateCode(lon,lat):
        klimat_gdf = gpd.read_file(files('Munin.Geo.Climate').joinpath("Klimat.shp")).to_crs("EPSG:3006")

        #Transformer
        transformer = Transformer.from_crs('EPSG:4326','EPSG:3006',always_xy=True)
        lon, lat = transformer.transform(lon,lat)

        # Create a point geometry
        point = Point(lon, lat)
        # Mapping of KLIMZON_ codes to their labels
        klimzon_mapping = {
            1: "M1",  # Maritime, West coast
            2: "M2",  # Maritime, East coast
            3: "M3",  # Maritime, Mountain range
            4: "K1",  # Continental, Middle Sweden
            5: "K2",  # Continental, Northern Sweden
            6: "K3"   # Continental, Southern Sweden
        }

        # Find the containing polygon in Klimat
        klimat_polygon = klimat_gdf[klimat_gdf.contains(point)]
        if klimat_polygon.empty:
            return 0
        else:
            return klimzon_mapping.get(klimat_polygon.iloc[0]['KLIMZON_'],0)

                                      
    def getCountyCode(lon,lat):
        # Load shapefiles
        dlanskod_gdf = gpd.read_file(files('Munin.Geo.Counties').joinpath('RT_Dlanskod.shp')).to_crs("EPSG:3006")

        #Transformer
        transformer = Transformer.from_crs('EPSG:4326','EPSG:3006',always_xy=True)
        lon, lat = transformer.transform(lon,lat)

        # Create a point geometry
        point = Point(lon, lat)

        #Mapping of DLANSKOD codes to their labels.
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

        # Find the containing polygon in RT_Dlanskod
        dlanskod_polygon = dlanskod_gdf[dlanskod_gdf.contains(point)]
        if dlanskod_polygon.empty:
            return 0
        else:
            return county_mapping.get(dlanskod_polygon.iloc[0]['DLANSKOD'],0)
