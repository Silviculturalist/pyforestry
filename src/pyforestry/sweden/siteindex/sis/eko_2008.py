from ...site.enums import (
    SwedenBottomLayer,
    SwedenFieldLayer,
    SwedenSoilMoisture,
    SwedenSoilWater,
)


def eko_pm_2008_estimate_si_birch(
    altitude: float,
    latitude: float,
    vegetation: SwedenFieldLayer,
    ground_layer: SwedenBottomLayer,
    lateral_water: SwedenSoilWater,
    soil_moisture: SwedenSoilMoisture,
) -> float:
    """
    Estimate SIH50 (Site Index for Birch H50) with stand factors based on Ekö et al. (2008).

    This function calculates the Site Index for Birch based on altitude, latitude, vegetation,
    ground layer, lateral water presence, and soil moisture type. The model is derived
    from empirical relationships provided in Ekö et al. (2008).

    Parameters:
        altitude (float): Altitude in meters above sea level.
        latitude (float): Latitude in degrees.
        vegetation (SwedenFieldLayer): Vegetation type.
        ground_layer (SwedenBottomLayer): Ground layer type.
        lateral_water (SwedenSoilWater): Degree of lateral water flow.
        soil_moisture (SwedenSoilMoisture): Soil moisture class.

    Returns:
        float: Site Index (H50) for Birch.

    Raises:
        ValueError: If the soil moisture type is not "mesic" (2) or "moist" (4).

    References:
        Ekö, P.-M., Johansson, U., Petersson, N., Bergqvist, J., Elfving, B., Frisk, J. (2008).
        Current growth differences of Norway spruce (Picea abies), Scots Pine (Pinus sylvestris)
        and birch (Betula pendula and Betula pubescens) in different regions in Sweden.
        Scandinavian Journal of Forest Research, Vol. 23:4, pp. 307-318.
        DOI: https://doi.org/10.1080/02827580802249126
    """

    veg_code = vegetation.value.code
    gl_code = ground_layer.value.code
    lw_code = lateral_water.value.code
    sm_code = soil_moisture.value.code

    # Derived binary variables
    grasses = 1 if veg_code in [8, 9] else 0
    low_herbs = 1 if 4 <= veg_code <= 6 else 0
    tall_herbs = 1 if veg_code < 4 else 0
    herb = 1 if veg_code < 7 else 0
    polytrichum = 1 if gl_code == 5 else 0
    mesic_soil_mosses = 1 if gl_code == 6 else 0
    mesic = 1 if sm_code == 2 else 0
    moist = 1 if sm_code > 3 else 0
    lateral_frequent = 1 if lw_code == 4 else 0
    northern = 1 if latitude > 60 else 0

    # Conditions for Northern Sweden, Mesic
    if northern == 1 and mesic == 1:
        return (
            88.469
            - (0.00869 * altitude)
            - (1.112 * latitude)
            + (1.397 * herb)
            + (2.216 * lateral_frequent)
        )

    # Conditions for Northern Sweden, Moist
    elif northern == 1 and moist == 1:
        return (
            77.862
            - (0.0103 * altitude)
            - (0.976 * latitude)
            + (0.732 * herb)
            + (1.372 * polytrichum)
            + (1.914 * mesic_soil_mosses)
            + (1.304 * lateral_frequent)
        )

    # Conditions for Southern Sweden, Mesic
    elif northern == 0 and mesic == 1:
        return (
            -9.910
            + (0.467 * latitude)
            + (2.956 * grasses)
            + (4.671 * low_herbs)
            + (5.526 * tall_herbs)
            + (1.711 * lateral_frequent)
        )

    # Conditions for Southern Sweden, Moist
    elif northern == 0 and moist == 1:
        return (
            0.259
            - (0.00729 * altitude)
            + (0.287 * latitude)
            + (1.601 * grasses)
            + (2.991 * low_herbs)
            + (2.173 * tall_herbs)
            + (1.224 * polytrichum)
            + (2.213 * mesic_soil_mosses)
            + (1.978 * lateral_frequent)
        )

    # Error if soil moisture type is not valid
    else:
        raise ValueError(
            "Can only choose between SwedenSoilMoisture.MOIST or " "SwedenSoilMoisture.MESIC."
        )
