def eko_pm_2008_estimate_si_birch(altitude, latitude, vegetation, ground_layer, lateral_water, soil_moisture):
    """
    Estimate SIH50 (Site Index for Birch H50) with stand factors based on Ekö et al. (2008).

    This function calculates the Site Index for Birch based on altitude, latitude, vegetation, 
    ground layer, lateral water presence, and soil moisture type. The model is derived 
    from empirical relationships provided in Ekö et al. (2008).

    Parameters:
        altitude (float): Altitude in meters above sea level.
        latitude (float): Latitude in degrees.
        vegetation (int): Vegetation type (1-18) as per Swedish National Forest Inventory (NFI). 
            Vegetation types:
                1  = Rich-herb without shrubs
                2  = Rich-herb with shrubs/bilberry
                3  = Rich-herb with shrubs/lingonberry
                4  = Low-herb without shrubs
                5  = Low-herb with shrubs/bilberry
                6  = Low-herb with shrubs/lingonberry
                7  = No field layer
                8  = Broadleaved grass
                9  = Thinleaved grass
                10 = Sedge, high
                11 = Sedge, low
                12 = Horsetail (Equisetum ssp.)
                13 = Bilberry
                14 = Lingonberry
                15 = Crowberry
                16 = Poor shrub
                17 = Lichen, frequent occurrence
                18 = Lichen, dominating.
        ground_layer (int): Ground layer type (1-6) as per Swedish NFI.
            Ground layer types:
                1 = Lichen type (>50% of existing ground layer).
                2 = Lichen-rich bogmoss type (>25% lichen + >50% Sphagnum).
                3 = Lichen rich (>25% lichen, not >50% Sphagnum).
                4 = Bogmoss type (Sphagnum >50% of existing ground layer).
                5 = Swamp moss type (e.g., Polytrichum commune, P. gracile, P. strictum).
                6 = Fresh moss type (e.g., Hylocomium splendens, Ptilium crista-castrensis).
        lateral_water (int): Type of lateral water flow:
            1 = "Missing",
            2 = "Seldom",
            3 = "Shorter periods",
            4 = "Longer periods",
            5 = "Slope".
        soil_moisture (int): Soil moisture type:
            1 = "Dry",
            2 = "Mesic",
            3 = "Mesic-moist",
            4 = "Moist",
            5 = "Wet".

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

    # Derived binary variables
    grasses = 1 if vegetation in [8, 9] else 0
    low_herbs = 1 if 4 <= vegetation <= 6 else 0
    tall_herbs = 1 if vegetation < 4 else 0
    herb = 1 if vegetation < 7 else 0
    polytrichum = 1 if ground_layer == 5 else 0
    mesic_soil_mosses = 1 if ground_layer == 6 else 0
    mesic = 1 if soil_moisture == 2 else 0
    moist = 1 if soil_moisture > 3 else 0
    lateral_frequent = 1 if lateral_water == 4 else 0
    northern = 1 if latitude > 60 else 0

    # Conditions for Northern Sweden, Mesic
    if northern == 1 and mesic == 1:
        return (
            88.469 - (0.00869 * altitude) - (1.112 * latitude) +
            (1.397 * herb) + (2.216 * lateral_frequent)
        )

    # Conditions for Northern Sweden, Moist
    elif northern == 1 and moist == 1:
        return (
            77.862 - (0.0103 * altitude) - (0.976 * latitude) +
            (0.732 * herb) + (1.372 * polytrichum) +
            (1.914 * mesic_soil_mosses) + (1.304 * lateral_frequent)
        )

    # Conditions for Southern Sweden, Mesic
    elif northern == 0 and mesic == 1:
        return (
            -9.910 + (0.467 * latitude) + (2.956 * grasses) +
            (4.671 * low_herbs) + (5.526 * tall_herbs) +
            (1.711 * lateral_frequent)
        )

    # Conditions for Southern Sweden, Moist
    elif northern == 0 and moist == 1:
        return (
            0.259 - (0.00729 * altitude) + (0.287 * latitude) +
            (1.601 * grasses) + (2.991 * low_herbs) +
            (2.173 * tall_herbs) + (1.224 * polytrichum) +
            (2.213 * mesic_soil_mosses) + (1.978 * lateral_frequent)
        )

    # Error if soil moisture type is not valid
    else:
        raise ValueError("Can only choose between 'moist' (soil_moisture==4) or 'mesic' (soil_moisture==2) soil moistures.")
