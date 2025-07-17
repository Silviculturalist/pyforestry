# Tegnhammar Site Index corrections for Hägglund Site Index for Swedish Spruce.
from __future__ import annotations

from math import exp
from typing import TYPE_CHECKING

from pyforestry.base.helpers import Age, SiteIndexValue, TreeSpecies, enum_code
from pyforestry.sweden.geo import eriksson_1986_humidity
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970

if TYPE_CHECKING:  # pragma: no cover - for type checking only
    from pyforestry.sweden.site.enums import Sweden


def tegnhammar_1992_adjusted_spruce_si_by_stand_variables(
    latitude: float,
    longitude: float,
    altitude: float,
    vegetation: int | Sweden.FieldLayer,
    ground_layer: int | Sweden.BottomLayer,
    aspect_main: int,
    soil_moisture: int | Sweden.SoilMoistureEnum,
    soil_depth: int | Sweden.SoilDepth,
    soil_texture: int | Sweden.SoilTextureTill | Sweden.SoilTextureSediment,
    humidity: float | None = None,
    ditched: bool = False,
    lateral_water: int | Sweden.SoilWater = 1,
    peat_humification: int | Sweden.PeatHumification = Sweden.PeatHumification.MEDIUM,
    epsg: str = "EPSG:4326",
) -> SiteIndexValue:
    """
    Calculate Tegnhammar's adjusted Site Index from stand variables.

    Source: Tegnhammar, L. (1992). "Om skattningen av ståndortsindex för gran".
    Report 53. Dept. of Forest Survey. Swedish University of Agricultural Sciences. Umeå.

    Args:
        latitude (float): Decimal degrees. Default WGS84, see parameter ``epsg``.
        longitude (float): Decimal degrees. Default WGS84, see parameter ``epsg``.
        altitude (float): Metres above sea level.
        vegetation (int | Sweden.FieldLayer): Vegetation type.
        ground_layer (int | Sweden.BottomLayer): Ground layer type.
        aspect_main (int): Aspect code. Use 0 if slope is below 5%.
        soil_moisture (int | Sweden.SoilMoistureEnum): Soil moisture 1-5.
        soil_depth (int | Sweden.SoilDepth): Soil depth class.
        soil_texture (
            int | Sweden.SoilTextureTill | Sweden.SoilTextureSediment
        ): Soil texture code.
        humidity (float | None, optional): Humidity during the vegetation period in mm.
            If ``None`` it will be calculated.
        ditched (bool): True if affected by ditching.
        lateral_water (int | Sweden.SoilWater): Water availability code.
        peat_humification (int | Sweden.PeatHumification): Peat decomposition level.
        epsg (str): Coordinate system (default is WGS84: ``"EPSG:4326"``).

    Returns:
        SiteIndexValue: Tegnhammar's adjusted SI in metres.
    """

    if humidity is None:
        humidity = eriksson_1986_humidity(longitude=longitude, latitude=latitude)

    # convert enums to numeric codes if needed
    vegetation = enum_code(vegetation)
    ground_layer = enum_code(ground_layer)
    soil_moisture = enum_code(soil_moisture)
    soil_depth = enum_code(soil_depth)
    soil_texture = enum_code(soil_texture)
    lateral_water = enum_code(lateral_water)
    peat_humification = enum_code(peat_humification)

    # Determine if site is north or south of Limes Norrlandicus
    # (Placeholder logic; replace with actual spatial analysis if required.)
    limes_n = latitude > 60.0  # Example condition; adjust as needed.
    lat_n = limes_n
    lat_s = not limes_n

    altitude_s_south_sweden = altitude if lat_s else 0
    altitude_n_north_sweden = altitude if lat_n else 0

    humidity_south_sweden_dry = humidity if lat_s and soil_moisture in [1, 2] else 0
    humidity_north_sweden = humidity if lat_n else 0
    humidity_north_sweden_lat_n = humidity_north_sweden * lat_n

    shallow = 1 if soil_depth != 1 else 0
    dry = 1 if soil_moisture == 1 else 0
    moist = 1 if soil_moisture == 4 else 0
    peat = 1 if soil_texture == 9 else 0

    if ditched and peat == 0 and moist == 0:
        print("Ditched only defined for peat or moist soils! Setting ditched to 0.")
        ditched = 0

    lateral_water_longer_periods = 1 if lateral_water == 4 else 0
    lateral_water_shorter_periods = 1 if lateral_water == 3 else 0
    coarse = 1 if soil_texture in [1, 2, 3] else 0
    fine = 1 if soil_texture in [7, 8] else 0

    # Defaults
    peat_humification_low, peat_humification_medium, peat_humification_high = 0, 0, 0

    if peat == 1:
        peat_humification_low = 1 if peat_humification == 1 else 0
        peat_humification_medium = 1 if peat_humification == 2 else 0
        peat_humification_high = 1 if peat_humification == 3 else 0

    aspect_east_south_east_incline = 1 if aspect_main in [6, 7] else 0
    extremely_cold = max(altitude + (130 * latitude) - 8900, 0)

    # Use pyforestry.Geo.Geo.RetrieveGeoCode.getDistanceToCoast
    from pyforestry.geo.geo import RetrieveGeoCode

    distance_to_swedish_coast = (
        RetrieveGeoCode().getDistanceToCoast(longitude, latitude) / 1000
    )  # m to km
    distance_to_swedish_coast_2 = (
        exp(-distance_to_swedish_coast / 5) if soil_moisture in [1, 2] else 0
    )

    # Vegetation types
    rich_herb_no_shrub = 1 if vegetation == 1 else 0
    low_herb_no_shrub = 1 if vegetation == 3 else 0
    herb_with_shrub = 1 if vegetation in [2, 3, 5, 6] else 0
    no_field_layer = 1 if vegetation == 7 else 0
    broadleaved_grass = 1 if vegetation == 8 else 0
    thinleaved_grass = 1 if vegetation == 9 else 0
    carex_or_equisetum = 1 if vegetation in range(10, 13) else 0
    lingonberry = 1 if vegetation == 14 else 0
    crowberry_or_worse = 1 if vegetation >= 15 else 0

    # Ground layer
    sphagnum = 1 if ground_layer == 4 else 0
    polytrichum = 1 if ground_layer == 5 else 0

    # Calculation
    sih_just = (
        1210.813605
        - 14.969124 * lat_n
        - 15.444848 * lat_s
        - 1.308729 * altitude_n_north_sweden
        - 0.000062709 * (altitude_n_north_sweden**2)
        - 0.048787 * altitude_n_north_sweden * moist
        + 0.000099984 * (altitude_n_north_sweden**2) * moist
        - 2.396754 * altitude_s_south_sweden
        - 0.000326 * (altitude_s_south_sweden**2)
        + 0.019672 * lat_n * altitude_n_north_sweden
        + 0.042405 * lat_s * altitude_s_south_sweden
        + 4.084904 * humidity_north_sweden
        - 0.064359 * humidity_north_sweden_lat_n
        - 0.085390 * humidity_north_sweden * moist
        + 0.026421 * humidity_south_sweden_dry
        - 22.492215 * distance_to_swedish_coast_2
        - 6.494468 * dry
        + 3.284251 * moist
        + 8.004164 * lateral_water_shorter_periods
        + 12.557257 * lateral_water_longer_periods
        + 7.162013 * ditched
        - 2.241642 * fine
        - 3.944443 * coarse
        - 22.450707 * peat_humification_low
        - 10.735284 * peat_humification_medium
        - 2.872332 * peat_humification_high
        - 12.206813 * shallow
        + 5.792854 * shallow * moist
        + 36.421502 * rich_herb_no_shrub
        + 31.110677 * low_herb_no_shrub
        + 20.906555 * herb_with_shrub
        + 22.879371 * no_field_layer
        + 11.623366 * broadleaved_grass
        + 13.542164 * thinleaved_grass
        - 6.635013 * carex_or_equisetum
        - 10.954260 * lingonberry
        - 19.853882 * crowberry_or_worse
        - 15.615067 * sphagnum
        - 5.950684 * polytrichum
        - 0.062692 * extremely_cold
        + 5.299670 * aspect_east_south_east_incline
    )

    SIS = sih_just / 10
    fn = (
        Hagglund_1970.height_trajectory.picea_abies.northern_sweden
        if latitude >= 60
        else Hagglund_1970.height_trajectory.picea_abies.southern_sweden
    )
    return SiteIndexValue(
        SIS,
        reference_age=Age.TOTAL(100),
        species={TreeSpecies.Sweden.picea_abies},
        fn=fn,
    )


def tegnhammar_1992_adjusted_si_spruce(sih, dominant_age, latitude):
    """
    Tegnhammar's correction for SI 1992.

    Args:
        sih (float): Site index in metres.
        dominant_age (float): Arithmetic mean of the age at breast height of the dominant trees.
        latitude (float): Latitude in degrees.

    Returns:
        float: Adjusted SIH in metres.
    """
    return ((sih * 10) + (3.89 - 0.0498 * latitude) * (dominant_age - 15)) / 10
