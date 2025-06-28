import geopandas as gpd
from shapely.geometry import Point
from importlib.resources import files, as_file

def eriksson_1986_humidity(longitude : float,
                           latitude : float,
                           epsg : int=4326):
    """
    Estimate humidity during the vegetation period for Swedish sites.

    Source: Eriksson, B. (1986). "Nederbörds- och humiditetsklimatet i Sverige under vegetationsperiod."
            Sveriges Meteorologiska och Hydrologiska Institut (SMHI), rapporter i meteorologi och klimatologi (RMK) 46.

    Args:
        latitude (float): Latitude in degrees.
        longitude (float): Longitude in degrees.
        epsg (int): Reference system. Default is 4326 (WGS84). For SWEREF99TM, use 3006.

    Returns:
        float: Humidity during the vegetation period (mm).
    """
    # Validate input for SWEREF99TM
    if epsg == 3006 and longitude > 1e6:
        raise ValueError("Latitude and Longitude appear to be mixed up.")

    # Locate the humidity shapefile using importlib.resources in a context manager
    # This is the corrected section
    with as_file(files("Munin.Geo.Humidity").joinpath("humidity.shp")) as humidity_shapefile_path:
        # Load the humidity shapefile
        humidity_gdf = gpd.read_file(humidity_shapefile_path)

    #Explicitly set input crs
    humidity_gdf = humidity_gdf.set_crs(epsg=3006)

    # Create a GeoDataFrame with the input point
    point = gpd.GeoDataFrame(
        geometry=[Point(longitude, latitude)],
        crs=f"EPSG:{epsg}"
    )

    # Reproject the point to match the shapefile CRS if needed
    if epsg != 4326:
        point = point.to_crs(epsg=4326)

    # Ensure the humidity shapefile is in the same CRS
    if humidity_gdf.crs != point.crs:
        humidity_gdf = humidity_gdf.to_crs(epsg=4326)

    # Perform spatial join to extract humidity value
    joined = gpd.sjoin(point, humidity_gdf, how="left", predicate="intersects")

    # Extract the humidity value
    if "humiditet" in joined.columns:
        return joined.iloc[0]['humiditet']
    else:
        raise ValueError("Humidity value could not be determined for the given location.")
