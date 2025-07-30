# Version 0.90 2024-06-17
from __future__ import annotations

# Estimate Site Index H100 for Spruce in Sweden by stand factors.
# Canonical Source:
# Corrected functions from Appendix II for estimation of site index
# by site factors according to Hägglund and Lundmark (1977), in
# Hägglund, B. (1979) Ett system för bonitering av skogsmark - analys,
# kontroll och diskussion inför praktisk tillämpning. Rapport 14, Projekt
# HUGIN. Skogsvetenskapliga fakulteten, Sveriges Lantbruksuniversitet.
# Umeå. Sweden.
#
# Hägglund, B., Lundmark, J-E. (1977) Skattning av höjdboniteten med
# ståndortsfaktorer: Tall och gran i Sverige. Research Notes nr. 28. Dept.
# Forest Ecology & Forest Soils. Royal College of Forestry. Stockholm. Sweden.
# Author: Carl Vigren, Dept. Forest Resource Management, SLU Umeå.
# Written to match results to SIS NFI routine.
from math import exp
from typing import TYPE_CHECKING, Union

import numpy as np
from pandas import isna as pdisna

from pyforestry.base.helpers import (
    Age,
    SiteIndexValue,
    TreeSpecies,
    enum_code,
)
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970

if TYPE_CHECKING:
    from pyforestry.sweden.site.enums import Sweden


def NFI_SIS_SPRUCE(**kwargs) -> float:
    """
    Estimate Site Index H100 for Spruce in Sweden by stand factors.

    Source:
    Corrected functions from Appendix II for estimation of site index
    by site factors according to Hägglund and Lundmark (1977), in
    Hägglund, B. (1979) Ett system för bonitering av skogsmark - analys,
    kontroll och diskussion inför praktisk tillämpning. Rapport 14, Projekt
    HUGIN. Skogsvetenskapliga fakulteten, Sveriges Lantbruksuniversitet.
    Umeå. Sweden.

    Hägglund, B., Lundmark, J-E. (1977) Skattning av höjdboniteten med
    ståndortsfaktorer: Tall och gran i Sverige. Research Notes nr. 28. Dept.
    Forest Ecology & Forest Soils. Royal College of Forestry. Stockholm. Sweden.

    Details:
    Uses corrected functions from appendix II in Hägglund & Lundmark
    1979, except for when used on peat soils, in which case functions f. 8.1
    & f. 8.2. pages 138-139 from Hägglund & Lundmark (1977) is used.



    Args:
        vegetation (int | Sweden.FieldLayer): Integer 1-18 or enum member.
        groundLayer (int | Sweden.BottomLayer): Integer 1-6 or enum member.
        latitude (float): Decimal WGS84.
        altitude (float): Meters above sea level.
        aspect (int): Main aspect of the site. int 0-360.
        incline_percent (float): Incline of slope, in percent. Default == 0.
        soil_moisture (int | Sweden.SoilMoistureEnum):
            Integer 1-5 or enum member. 1: Dry, 2: Mesic, 3: Mesic-Moist, 4: Moist, 5: Wet
        soil_texture (int | Sweden.SoilTextureTill | Sweden.SoilTextureSediment):
            Integer 1-9 or enum member.
        soil_depth (int | Sweden.SoilDepth):
            Integer 1-5 or enum member. 1: Deep >70 cm, 2: Rather shallow 20-70 cm,
            3: Shallow < 20 cm, 4: Varying. 5: New nfi designation 'häll', en: 'outcrop'.
        lateral_water (int | Sweden.SoilWater):
            Integer 1-3 or enum member. 1: Seldom/never, 2: Shorter periods, 3: Longer periods.
        ditched (bool): FALSE (default) if plot affected by ditching.
        climate_code (str | Sweden.ClimateZone):
            One of: NA (default), 'M1', 'M2', 'K1', 'K2', 'K3' or enum member.
        coast (bool): FALSE (default) if plot is closer to coast than 50km.
        limes_norrlandicus (bool):
            FALSE (default) if plot is north of Sernanders Limes Norrlandicus
            (used for Peat soils only.)
        gotland (bool): FALSE (default) if plot is located in Gotland.
        nfi_adjustments (bool):
            TRUE (default) if adjustments based on NFI should be applied.
            N.B. This applies coastal correction n. of Limes norrlandicus always.
        dlan (int | Sweden.County): Optional. None (default). 1-31 according to NFI ID.

    Returns:
        SiteIndexValue: H100 site index estimate.
        Will return NA & issue a warning message if no method was found.
    """
    latitude = kwargs.get("latitude")
    altitude = kwargs.get("altitude")
    soil_moisture = enum_code(kwargs.get("soil_moisture"))
    ground_layer = enum_code(kwargs.get("ground_layer"))
    vegetation = enum_code(kwargs.get("vegetation"))
    soil_texture = enum_code(kwargs.get("soil_texture"))
    climate_code = enum_code(kwargs.get("climate_code"))
    lateral_water = enum_code(kwargs.get("lateral_water"))
    soil_depth = enum_code(kwargs.get("soil_depth"))
    incline_percent = kwargs.get("incline_percent")
    aspect = kwargs.get("aspect")
    ditched = kwargs.get("ditched")
    peat = kwargs.get("peat")
    gotland = kwargs.get("gotland")
    dlan = enum_code(kwargs.get("dlan"))
    limes_norrlandicus = kwargs.get("limes_norrlandicus")
    coast = kwargs.get("coast")
    nfi_adjustments = kwargs.get("nfi_adjustments")

    Adjustment = 1.00
    changeToPine = False

    # helpers
    deepsoil = 1
    rshallow = 2
    shallow = 3

    New_SoilMoisture = soil_moisture
    New_GroundLayer = ground_layer
    New_Vegetation = vegetation
    New_SoilTexture = soil_texture
    New_LateralWater = lateral_water
    New_SoilDepth = soil_depth

    # nfi-code for missing soil (0). Replace with shallow, stony soil
    if not peat:
        if New_SoilTexture == 0:
            New_SoilDepth = shallow
            New_SoilTexture = 1

    # if dry soil and swamp-mosses, set soil_moisture to mesic.
    if New_SoilMoisture == 1 and New_GroundLayer in [2, 4, 5]:
        New_SoilMoisture = 2

    # Spruce cannot be placed on dry soil, switch to mesic.
    if New_SoilMoisture == 1:
        print("Warning: No coverage for Spruce on dry soils, switching to mesic.")
        New_SoilMoisture = 2

    # moist-wet mineral soils with lichen-dominated ground layer: set vegetation
    # to horsetail and ground-layer to swamp-mosses.
    if not peat and New_SoilMoisture in [3, 4] and New_GroundLayer == 1:
        New_Vegetation = 12
        New_GroundLayer = 5

    # If shallow or varying (3,4) or stony soil + not under longer periods
    # groundwater feeding: set soil moisture to dry.
    # reduce coefficient 10 percent.
    # change to Pine.
    if not peat:
        if (New_SoilDepth >= shallow or New_SoilTexture == 1) and New_LateralWater < 3:
            New_SoilMoisture = 1
            Adjustment = 0.90
            changeToPine = True

    # If lichen groundlayer and Spruce, reduce by 20 percent.
    if New_GroundLayer in [1, 2, 3] and not changeToPine:
        Adjustment *= 0.80

    # If shallow or stony soil.
    # If lateral groundwater feeding is not longer periods, reclass soil depth to rather shallow.
    # Otherwise, set texture to gravel (2)
    if not peat:
        if New_SoilDepth >= shallow or New_SoilTexture == 1:
            if New_LateralWater < 3:
                New_SoilDepth = rshallow
            if New_LateralWater == 3:
                New_SoilTexture = 2

    # if wet with no lateral water movement..
    if New_SoilMoisture == 5 and New_LateralWater == 1:
        New_GroundLayer = 5  # groundlayer will be swamp-moss.
        Adjustment *= 0.70  # reduce SI by 30%.
        New_LateralWater = 3  # lateralwater movement is longer periods.

    # if wet with lateral water movement.
    if New_SoilMoisture == 5 and New_LateralWater == 3:
        New_GroundLayer = 5  # groundlayer will be swamp moss.
        New_LateralWater = 3  # this is superfluous.

    # if wet class soil moisture to moist...
    if New_SoilMoisture == 5:
        New_SoilMoisture = 4

    # SoilTextureIndex = 2.265 - 0.204 * soilTexture + 2.94 / soilTexture
    # Set to 2.2 if New_SoilTexture not found.
    SoilTextureIndex = {
        0: 5.0,
        1: 5.0,
        2: 3.5,
        3: 2.7,
        4: 2.2,
        5: 1.8,
        6: 1.4,
        7: 1.2,
        8: 1.0,
        9: 2.0,
    }.get(New_SoilTexture, 2.2)

    # This cannot exist, check with NFI
    # First clause is changeToPine and peat, which are set together.
    # Later clauses check changeToPine and combinations of New_soil_Moisture which **is not**  1, which is also set at the same time.
    # if changeToPine and peat:
    #    FGRAN = 5.03077 - 0.03627 * (latitude - 60.0)
    #    if nfi_adjustments:  # Always apply close to coast and norrland for same as NFI results.
    #        FGRAN -= 0.000000901 * (altitude**2)
    #    else:
    #        FGRAN -= (
    #            0.000000901 * (altitude**2) * ~coast * limes_norrlandicus
    #        )  # Ordinary routine. No effect near coast north of Limes Norrlandicus.
    #    if New_LateralWater == 3:
    #        FGRAN += 0.09195
    #    if ditched:
    #        FGRAN += 0.13622
    #    if 2 <= New_GroundLayer <= 5:  # Lichen-rich types, sphagnum and swamp-mosses.
    #        FGRAN -= 0.1497
    #    if New_Vegetation < 7:  # herb type.
    #        FGRAN += 0.22273
    #    if New_Vegetation == 13:  # bilberry type
    #        FGRAN += 0.13997
    #    if New_Vegetation in [7, 8, 9, 14]:  # no field layer, grasses and cowberry.
    #        FGRAN += 0.13377

    #    elif changeToPine and New_SoilMoisture == 2 and New_Vegetation > 9 and New_GroundLayer > 3:
    #        FGRAN = (
    #            5.30943
    #            - 0.01716 * (latitude - 60.0 + abs(latitude - 60.0))
    #            - 0.0039 * (latitude - 60.0 - abs(latitude - 60.0))
    #            - 0.000000678 * (altitude**2)
    #            - 0.01243 * (SoilTextureIndex**2)
    #        )
    #        if New_LateralWater == 3:
    #            FGRAN += 0.0488
    #        if New_Vegetation == 13:  # bilberry
    #            FGRAN += 0.09429
    #        if New_Vegetation == 14:  # cowberry
    #            FGRAN += 0.06167
    #        if New_SoilDepth == deepsoil:
    #            FGRAN += 0.1158
    #        if New_Vegetation == 16:  # poor shrubs..
    #            FGRAN -= 0.07775
    #
    #    elif changeToPine and New_SoilMoisture == 2 and New_Vegetation > 9 and New_GroundLayer <= 3:
    #        FGRAN = 5.21803 - 0.01193 * (latitude - 60.0 + abs(latitude - 60.0))
    #        if New_LateralWater in [1, 2]:
    #            FGRAN -= 0.000000593 * (altitude**2)
    #        if New_LateralWater == 3:
    #            FGRAN -= 0.000000355 * (altitude**2)
    #        if New_SoilDepth == deepsoil:
    #            FGRAN += 0.12454
    #        if (
    #            incline_percent <= 10.0 and New_LateralWater == 1
    #        ):  # if incline and seldom/never lateral groundwater..
    #            FGRAN -= 0.06329
    #        if (
    #            altitude >= 350
    #            and incline_percent > 10.0
    #            and (aspect in range(0, 113) or aspect > 337)
    #        ):
    #            FGRAN -= 0.07189
    #        if New_GroundLayer == 1:
    #            FGRAN -= 0.06842
    #
    #    elif changeToPine and New_SoilMoisture == 2 and New_Vegetation <= 9:
    #        FGRAN = (
    #            5.34912
    #            - 0.02037 * (latitude - 60.0 + abs(latitude - 60.0))
    #            - 0.000000481 * (altitude**2)
    #        )
    #        if New_SoilDepth == deepsoil:
    #            FGRAN += 0.11574
    #        if climate_code == "M2":  # and 14 <= Dlan <= 31: # S. sv.
    #            FGRAN -= 0.16403
    #        if New_Vegetation in [4, 5, 8, 9]:
    #            FGRAN += 0.08376
    #        if New_Vegetation in [1, 2]:
    #            FGRAN += 0.12296

    if changeToPine and New_SoilMoisture == 1:
        FGRAN = (
            5.44789
            - 0.01566 * (latitude - 60.0 + abs(latitude - 60.0))
            - 0.00000102 * (altitude**2)
            - 0.0417 * SoilTextureIndex
        )
        if New_SoilDepth == deepsoil:
            FGRAN += 0.09162
        if climate_code == "K3":
            FGRAN += 0.12
        if New_GroundLayer == 1:
            FGRAN -= 0.19805
        if New_GroundLayer in [2, 3]:
            FGRAN -= 0.1381
        if New_GroundLayer >= 4 and New_Vegetation in [1, 2, 3, 4, 5, 6, 8]:
            FGRAN += 0.0953
        if New_GroundLayer >= 4 and New_Vegetation in [7, 9, 13]:
            FGRAN += 0.0488

    # elif changeToPine and New_SoilMoisture in [3, 4, 5]:
    #    FGRAN = (
    #        5.46782
    #        - 0.02013 * (latitude - 60.0 + abs(latitude - 60.0))
    #        - 0.01074 * (SoilTextureIndex**2)
    #    )
    #    if New_LateralWater in [1, 2]:
    #        FGRAN -= 0.01517 * 0.0001 * (altitude**2)
    #    if New_LateralWater == 3:
    #        FGRAN -= 0.00747 * 0.0001 * (altitude**2)
    #    if New_Vegetation <= 6:
    #        FGRAN += 0.11585
    #    if New_Vegetation in [10, 11, 12]:
    #        FGRAN -= 0.22358
    #    if New_Vegetation in [7, 8, 9, 13, 14]:
    #        FGRAN += 0.0770
    #    if New_Vegetation in [15, 16]:
    #        FGRAN -= 0.0726
    #    if ground_layer in [2, 3, 4, 5]:
    #        FGRAN -= 0.0730

    elif peat:
        FGRAN = (
            5.51735
            - 0.03958 * (latitude - 60.0 + abs(latitude - 60.0))
            - 0.02466 * (latitude - 60.0 - abs(latitude - 60.0))
        )
        if (
            New_LateralWater in [1, 2] and nfi_adjustments
        ):  # Always apply close to coast and norrland for same as NFI results.
            # HL1979 removed coast limitation for altitude expression for MINERAL soils.
            FGRAN -= 0.000001174 * (altitude**2)
        elif New_LateralWater in [1, 2]:
            FGRAN -= (
                0.000001174 * (altitude**2) * ~coast * limes_norrlandicus
            )  # Ordinary routine. No effect near coast north of Limes Norrlandicus.
        if New_LateralWater == 3 and nfi_adjustments:
            FGRAN -= 0.000000899 * (altitude**2)
        elif New_LateralWater == 3:
            FGRAN -= (
                0.000000899 * (altitude**2) * ~coast * limes_norrlandicus
            )  # Ordinary routine. No effect near coast north of Limes Norrlandicus.
        if New_LateralWater == 2:
            FGRAN += 0.04577
        if New_LateralWater == 3:
            FGRAN += 0.063
        if ditched:
            FGRAN += 0.04428
        if 2 <= New_GroundLayer <= 5:
            FGRAN -= 0.20935
        if New_Vegetation in [1, 4, 7]:
            FGRAN += 0.09517
        if New_Vegetation in [2, 3, 5, 6, 13, 14]:
            FGRAN -= 0.04868
        if New_Vegetation in [10, 11, 12, 15, 16]:
            FGRAN -= 0.12545

    elif New_SoilMoisture in [1, 2] and New_Vegetation > 9:
        FGRAN = (
            5.51876
            - 0.04342 * (latitude - 60.0 + abs(latitude - 60.0))
            - 0.01837 * (latitude - 60.0 - abs(latitude - 60.0))
        )
        if New_LateralWater in [1, 2]:
            FGRAN -= 0.000001095 * (altitude**2)
        if New_LateralWater == 3:
            FGRAN -= 0.000000716 * (altitude**2)
        if New_LateralWater == 2:
            FGRAN += 0.03361
        if New_LateralWater == 3:
            FGRAN += 0.04605
        if 2 <= New_GroundLayer <= 5:
            FGRAN -= 0.073
        if New_Vegetation == 13:
            FGRAN += 0.07842

    elif New_SoilMoisture in [1, 2] and New_Vegetation <= 9:
        FGRAN = (
            5.68205
            - 0.03423 * (latitude - 60.0 + abs(latitude - 60.0))
            - 0.02122 * (latitude - 60.0 - abs(latitude - 60.0))
            - 0.000000691 * (altitude**2)
        )
        if New_LateralWater == 2:
            FGRAN += 0.03247
        if New_LateralWater == 3:
            FGRAN += 0.05097
        if climate_code == "M2":
            if dlan is not None:
                if 14 <= dlan <= 31:  # S. sv.?
                    FGRAN -= 0.10806
            else:
                FGRAN -= 0.10806
        if New_Vegetation in [2, 3, 5, 6, 7, 10, 11, 12, 13, 14, 15, 16]:
            FGRAN -= 0.02991
        if New_Vegetation in [8, 9]:
            FGRAN -= 0.06787
        if New_Vegetation == 1:
            FGRAN += 0.039
        if 2 <= New_GroundLayer <= 5:
            FGRAN -= 0.073

    elif New_SoilMoisture in [3, 4, 5]:
        FGRAN = (
            5.59884
            - 0.03722 * (latitude - 60.0 + abs(latitude - 60.0))
            - 0.02499 * (latitude - 60.0 - abs(latitude - 60.0))
        )
        if New_LateralWater in [1, 2]:
            FGRAN -= 0.000001206 * (altitude**2)
        if New_LateralWater == 3:
            FGRAN -= 0.000000937 * (altitude**2)
        if New_LateralWater == 2:
            FGRAN += 0.04766
        if New_LateralWater == 3:
            FGRAN += 0.05939
        if ditched:
            FGRAN += 0.02383
        if New_Vegetation == 1:
            FGRAN += 0.012
        if New_Vegetation == 7:
            FGRAN += 0.08075
        if New_Vegetation == 4:
            FGRAN += 0.05342
        if New_Vegetation in [13, 14]:
            FGRAN -= 0.05889
        if New_Vegetation in [10, 11, 12, 15, 16]:
            FGRAN -= 0.16425
        if 2 <= New_GroundLayer <= 5:
            FGRAN -= 0.073

    else:
        raise ValueError("No SIS method found.")

    if gotland:
        Adjustment *= 0.80

    # 0.1 converts dm to m.
    SIS = 0.1 * exp(FGRAN) * Adjustment

    if SIS < 0.0:
        raise ValueError("SIS estimated < 0.")
    if SIS > 50.0:
        raise ValueError("SIS estimated > 50")

    return SIS


def NFI_SIS_PINE(**kwargs) -> float:
    """
    Estimate Site Index H100 for Pine in Sweden by stand factors.

    Source:
    Corrected functions from Appendix II for estimation of site index
    by site factors according to Hägglund and Lundmark (1977), in
    Hägglund, B. (1979) Ett system för bonitering av skogsmark - analys,
    kontroll och diskussion inför praktisk tillämpning. Rapport 14, Projekt
    HUGIN. Skogsvetenskapliga fakulteten, Sveriges Lantbruksuniversitet.
    Umeå. Sweden.

    Hägglund, B., Lundmark, J-E. (1977) Skattning av höjdboniteten med
    ståndortsfaktorer: Tall och gran i Sverige. Research Notes nr. 28. Dept.
    Forest Ecology & Forest Soils. Royal College of Forestry. Stockholm. Sweden.

    Details:
    Uses corrected functions from appendix II in Hägglund & Lundmark
    1979, except for when used on peat soils, in which case functions f. 8.1
    & f. 8.2. pages 138-139 from Hägglund & Lundmark (1977) is used.



    Args:
        vegetation (int | Sweden.FieldLayer): Integer 1-18 or enum member.
        groundLayer (int | Sweden.BottomLayer): Integer 1-6 or enum member.
        latitude (float): Decimal WGS84.
        altitude (float): Meters above sea level.
        aspect (int): Main aspect of the site. int 0-360.
        incline_percent (float): Incline of slope, in percent. Default == 0.
        soil_moisture (int | Sweden.SoilMoistureEnum):
            Integer 1-5 or enum member. 1: Dry, 2: Mesic, 3: Mesic-Moist, 4: Moist, 5: Wet
        soil_texture (int | Sweden.SoilTextureTill | Sweden.SoilTextureSediment):
            Integer 1-9 or enum member.
        soil_depth (int | Sweden.SoilDepth):
            Integer 1-5 or enum member. 1: Deep >70 cm, 2: Rather shallow 20-70 cm,
            3: Shallow < 20 cm, 4: Varying. 5: New nfi designation 'häll', en: 'outcrop'.
        lateral_water (int | Sweden.SoilWater):
            Integer 1-3 or enum member. 1: Seldom/never, 2: Shorter periods, 3: Longer periods.
        ditched (bool): FALSE (default) if plot affected by ditching.
        climate_code (str | Sweden.ClimateZone):
            One of: NA (default), 'M1', 'M2', 'K1', 'K2', 'K3' or enum member.
        coast (bool): FALSE (default) if plot is closer to coast than 50km.
        limes_norrlandicus (bool):
            FALSE (default) if plot is north of Sernanders Limes Norrlandicus
            (used for Peat soils only.)
        gotland (bool): FALSE (default) if plot is located in Gotland.
        nfi_adjustments (bool):
            TRUE (default) if adjustments based on NFI should be applied.
            N.B. This applies coastal correction n. of Limes norrlandicus always.

    Returns:
        float: Site Index H100 (meters).
        Will return NA & issue a warning message if no method was found.
    """
    latitude = kwargs.get("latitude")
    altitude = kwargs.get("altitude")
    soil_moisture = enum_code(kwargs.get("soil_moisture"))
    ground_layer = enum_code(kwargs.get("ground_layer"))
    vegetation = enum_code(kwargs.get("vegetation"))
    soil_texture = enum_code(kwargs.get("soil_texture"))
    climate_code = enum_code(kwargs.get("climate_code"))
    lateral_water = enum_code(kwargs.get("lateral_water"))
    soil_depth = enum_code(kwargs.get("soil_depth"))
    incline_percent = kwargs.get("incline_percent")
    aspect = kwargs.get("aspect")
    ditched = kwargs.get("ditched")
    peat = kwargs.get("peat")
    gotland = kwargs.get("gotland")
    dlan = enum_code(kwargs.get("dlan"))
    limes_norrlandicus = kwargs.get("limes_norrlandicus")
    coast = kwargs.get("coast")
    nfi_adjustments = kwargs.get("nfi_adjustments")

    Adjustment = 1.00

    # helpers
    deepsoil = 1
    rshallow = 2
    shallow = 3

    New_SoilMoisture = soil_moisture
    New_GroundLayer = ground_layer
    New_Vegetation = vegetation
    New_SoilTexture = soil_texture
    New_LateralWater = lateral_water
    New_SoilDepth = soil_depth

    # nfi-code for missing soil (0). Replace with shallow, stony soil
    if not peat:
        if New_SoilTexture == 0:
            New_SoilDepth = shallow
            New_SoilTexture = 1

    # if dry soil and swamp-mosses, set soil_moisture to mesic.
    if New_SoilMoisture == 1 and New_GroundLayer in [2, 4, 5]:
        New_SoilMoisture = 2

    # moist-wet mineral soils with lichen-dominated ground layer: set vegetation
    # to horsetail and ground-layer to swamp-mosses.
    if not peat and New_SoilMoisture in [3, 4] and New_GroundLayer == 1:
        New_Vegetation = 12
        New_GroundLayer = 5

    # If shallow or varying (3,4) or stony soil + not under longer periods
    # groundwater feeding: set soil moisture to dry.
    # reduce coefficient 10 percent.
    if not peat:
        if (New_SoilDepth >= shallow or New_SoilTexture == 1) and New_LateralWater < 3:
            New_SoilMoisture = 1
            Adjustment = 0.90

    # If shallow or stony soil.
    # If lateral groundwater feeding is not longer periods, reclass soil depth to rather shallow.
    # Otherwise, set texture to gravel (2)
    if not peat:
        if New_SoilDepth >= shallow or New_SoilTexture == 1:
            if New_LateralWater < 3:
                New_SoilDepth = rshallow
            if New_LateralWater == 3:
                New_SoilTexture = 2

    # if wet with no lateral water movement..
    if New_SoilMoisture == 5 and New_LateralWater == 1:
        New_GroundLayer = 5  # groundlayer will be swamp-moss.
        Adjustment *= 0.70  # reduce SI by 30%.
        New_LateralWater = 3  # lateralwater movement is longer periods.

    # if wet with lateral water movement.
    if New_SoilMoisture == 5 and New_LateralWater == 3:
        New_GroundLayer = 5  # groundlayer will be swamp moss.
        New_LateralWater = 3  # this is superfluous.

    # if wet class soil moisture to moist...
    if New_SoilMoisture == 5:
        New_SoilMoisture = 4

    # SoilTextureIndex = 2.265 - 0.204 * soilTexture + 2.94 / soilTexture
    # Set to 2.2 if New_SoilTexture not found.
    SoilTextureIndex = {
        0: 5.0,
        1: 5.0,
        2: 3.5,
        3: 2.7,
        4: 2.2,
        5: 1.8,
        6: 1.4,
        7: 1.2,
        8: 1.0,
        9: 2.0,
    }.get(New_SoilTexture, 2.2)

    if peat:
        FTALL = 5.03077 - 0.03627 * (latitude - 60.0)
        if nfi_adjustments:  # Always apply close to coast and norrland for same as NFI results.
            # HL1979 removed coast limitation for altitude expression for MINERAL soils.
            FTALL -= 0.000000901 * (altitude**2)
        else:
            FTALL -= (
                0.000000901 * (altitude**2) * ~coast * limes_norrlandicus
            )  # Ordinary routine, no effect near coast north of Limes Norrlandicus.
        if New_LateralWater == 3:
            FTALL += 0.09195
        if ditched:
            FTALL += 0.13622
        if 2 <= New_GroundLayer <= 5:
            FTALL -= 0.1497
        if New_Vegetation < 7:
            FTALL += 0.22273
        if New_Vegetation == 13:
            FTALL += 0.13997
        if New_Vegetation in [7, 8, 9, 14]:
            FTALL += 0.13377

        G1 = 0
        G2 = 0

    else:
        FTALL = None
        G1 = 0
        G2 = 0
        if New_SoilMoisture == 2 and New_Vegetation > 9 and New_GroundLayer > 3:
            FTALL = (
                5.30943
                - 0.01716 * (latitude - 60.0 + abs(latitude - 60.0))
                - 0.0039 * (latitude - 60.0 - abs(latitude - 60.0))
                - 0.000000678 * (altitude**2)
                - 0.01243 * (SoilTextureIndex**2)
            )
            if New_LateralWater == 3:
                FTALL += 0.0488
            if New_Vegetation == 13:
                FTALL += 0.09429
            if New_Vegetation == 14:
                FTALL += 0.06167
            if New_SoilDepth == deepsoil:
                FTALL += 0.1158
            if New_Vegetation == 16:
                FTALL -= 0.07775

            G1 = 1 if New_Vegetation in [13, 14] else 0
            G2 = 1 if New_Vegetation in [15, 16] else 0
        elif New_SoilMoisture == 2 and New_Vegetation > 9 and New_GroundLayer <= 3:
            FTALL = 5.21803 - 0.01193 * (latitude - 60.0 + abs(latitude - 60.0))
            if New_LateralWater in [1, 2]:
                FTALL -= 0.000000593 * (altitude**2)
            if New_LateralWater == 3:
                FTALL -= 0.000000355 * (altitude**2)
            if New_SoilDepth == deepsoil:
                FTALL += 0.12454
            if incline_percent <= 10.0 and New_LateralWater == 1:
                FTALL -= 0.06329
            if incline_percent > 10.0 and altitude >= 350 and (0 <= aspect <= 112 or aspect > 337):
                FTALL -= 0.07189
            if New_GroundLayer == 1:
                FTALL -= 0.06842

            G1 = 0
            G2 = 1

            # OK
        elif New_SoilMoisture == 2 and New_Vegetation <= 9:
            FTALL = (
                5.34912
                - 0.02037 * (latitude - 60.0 + abs(latitude - 60.0))
                - 0.00481 * (altitude**2) / 10000
            )
            if New_SoilDepth == deepsoil:
                FTALL += 0.11574
            if climate_code == "M2":
                if dlan is not None:
                    if 14 <= dlan <= 31:
                        FTALL -= 0.16403
                else:
                    FTALL -= 0.16403
            if New_Vegetation in [4, 5, 8, 9]:
                FTALL += 0.08376
            if New_Vegetation in [1, 2]:
                FTALL += 0.12296

            G1 = 1 if 1 <= New_Vegetation <= 9 else 0  # Can be just <= 9 ?
            G2 = 0
        elif New_SoilMoisture == 1:
            FTALL = (
                5.44789
                - 0.01566 * (latitude - 60.0 + abs(latitude - 60.0))
                - 0.00000102 * (altitude**2)
                - 0.0417 * SoilTextureIndex
            )
            if New_SoilDepth == deepsoil:
                FTALL += 0.09162
            if (
                climate_code == "K3"
            ):  # Should be K2 according to Elfving notes? HL1977 code and HL1979 use K3.
                FTALL += 0.12
            if New_GroundLayer == 1:  # If veg == 18 ?
                FTALL -= 0.19805
            if New_GroundLayer in [2, 3]:  # If veg == 17?
                FTALL -= 0.1381
            if New_GroundLayer >= 4 and New_Vegetation in [
                1,
                2,
                3,
                4,
                5,
                6,
                8,
            ]:  # GroundLayer requirement necessary?
                FTALL += 0.0953
            if New_GroundLayer >= 4 and New_Vegetation in [7, 9, 13]:  # Groundlayer requirement?
                FTALL += 0.0488

            G1 = (
                1
                if New_GroundLayer >= 4 and New_Vegetation in [1, 2, 3, 4, 5, 6, 7, 8, 9, 13]
                else 0
            )  # Groundlayer requirement?
            G2 = (
                1
                if New_GroundLayer in [1, 2, 3]
                else (1 if New_GroundLayer >= 4 and New_Vegetation >= 14 else 0)
            )  # Groundlayer requirement?

            # OK.
        elif New_SoilMoisture in [3, 4, 5]:  # Pine on 5? Only 3, 4?
            FTALL = (
                5.46782
                - 0.02013 * (latitude - 60.0 + abs(latitude - 60.0))
                - 0.01074 * (SoilTextureIndex**2)
            )
            if New_LateralWater in [1, 2]:
                FTALL -= 0.01517 * 0.0001 * (altitude**2)
            if New_LateralWater == 3:
                FTALL -= 0.00747 * 0.0001 * (altitude**2)
            if New_Vegetation <= 6:
                FTALL += 0.11585
            if New_Vegetation in [10, 11, 12]:
                FTALL -= 0.22358
            if New_Vegetation in [7, 8, 9, 13, 14]:
                FTALL += 0.0770
            if New_Vegetation in [15, 16]:
                FTALL -= 0.0726
            if New_GroundLayer in [2, 3, 4, 5]:
                FTALL -= 0.0730

            G1 = 1 if New_Vegetation in [1, 2, 3, 4, 5, 6, 7, 8, 9, 13, 14] else 0
            G2 = 1 if New_Vegetation in [10, 11, 12, 15, 16] else 0
        else:
            raise ValueError("No SIS method found.")

    # Final adjustments
    D = altitude + 130.0 * latitude - 8900.0
    if G1 == 1 and D < -60.0:
        D = -60.0
    if G2 == 1 and D >= 60.0:
        D = 60.0
    if G1 == 1 and D < 0.0:
        Adjustment *= 1.0 - 0.00083333333 * D
    if G2 == 1 and D > 0.0:
        Adjustment *= 1.0 - 0.00166666667 * D

    if gotland:
        Adjustment *= 0.80

    # 0.1 converts dm to m.
    SIS = 0.1 * exp(FTALL) * Adjustment

    if SIS < 0.0:
        raise ValueError("SIS estimated < 0.")
    if SIS > 50.0:
        raise ValueError("SIS estimated > 50")

    return SIS


def Hagglund_Lundmark_1979_SIS(
    latitude: float,
    altitude: float,
    soil_moisture: Union[int, Sweden.SoilMoistureEnum],
    ground_layer: Union[int, Sweden.BottomLayer],
    vegetation: Union[int, Sweden.FieldLayer],
    soil_texture: Union[int, Sweden.SoilTextureTill, Sweden.SoilTextureSediment],
    climate_code: Union[float, str, Sweden.ClimateZone],
    lateral_water: Union[int, Sweden.SoilWater],
    soil_depth: Union[int, Sweden.SoilDepth],
    incline_percent: float,
    aspect: float,
    ditched: bool = False,
    peat: bool = False,
    gotland: bool = False,
    coast: bool = False,
    limes_norrlandicus: bool = False,
    nfi_adjustments: bool = True,
    species: str = "Picea abies",
    dlan: Union[int, Sweden.County, None] = None,
) -> float:
    """
    Estimate Site Index H100 for Scots Pine or Norway Spruce in Sweden by stand factors.

    Source:
    Corrected functions from Appendix II for estimation of site index
    by site factors according to Hägglund and Lundmark (1977), in
    Hägglund, B. (1979) Ett system för bonitering av skogsmark - analys,
    kontroll och diskussion inför praktisk tillämpning. Rapport 14, Projekt
    HUGIN. Skogsvetenskapliga fakulteten, Sveriges Lantbruksuniversitet.
    Umeå. Sweden.

    Hägglund, B., Lundmark, J-E. (1977) Skattning av höjdboniteten med
    ståndortsfaktorer: Tall och gran i Sverige. Research Notes nr. 28. Dept.
    Forest Ecology & Forest Soils. Royal College of Forestry. Stockholm. Sweden.

    Details:
    Uses corrected functions from appendix II in Hägglund & Lundmark
    1979, except for when used on peat soils, in which case functions f. 8.1
    & f. 8.2. pages 138-139 from Hägglund & Lundmark (1977) is used.



    Args:
        species (str): One of "Picea abies" (default) or "Pinus sylvestris".
        vegetation (int | Sweden.FieldLayer): Integer 1-18 or enum member.
        ground_layer (int | Sweden.BottomLayer): Integer 1-6 or enum member.
        latitude (float): Decimal WGS84.
        altitude (float): Meters above sea level.
        aspect (int): Main aspect of the site. int 0-360.
        incline_percent (float): Incline of slope, in percent. Default == 0.
        soil_moisture (int | Sweden.SoilMoistureEnum):
            Integer 1-5 or enum member. 1: Dry, 2: Mesic, 3: Mesic-Moist, 4: Moist, 5: Wet
        soil_texture (int | Sweden.SoilTextureTill | Sweden.SoilTextureSediment):
            Integer 1-9 or enum member.
        soil_depth (int | Sweden.SoilDepth):
            Integer 1-5 or enum member. 1: Deep >70 cm, 2: Rather shallow 20-70 cm,
            3: Shallow < 20 cm, 4: Varying. 5: New nfi designation 'häll', en: 'outcrop'.
        lateral_water (int | Sweden.SoilWater):
            Integer 1-3 or enum member. 1: Seldom/never, 2: Shorter periods, 3: Longer periods.
        ditched (bool): FALSE (default) if plot affected by ditching.
        climate_code (str | Sweden.ClimateZone):
            One of: NA (default), 'M1', 'M2', 'K1', 'K2', 'K3' or enum member.
        coast (bool): FALSE (default) if plot is closer to coast than 50km.
        limes_norrlandicus (bool):
            FALSE (default) if plot is north of Sernanders Limes Norrlandicus
            (used for Peat soils only.)
        gotland (bool): FALSE (default) if plot is located in Gotland.
        nfi_adjustments (bool):
            TRUE (default) if adjustments based on NFI should be applied.
            N.B. This applies coastal correction n. of Limes norrlandicus always.
        dlan (int | Sweden.County): Optional. None (default). 1-31 according to NFI ID.

    Returns:
        float: Site Index H100 (meters).
        Will return NA & issue a warning message if no method was found.
    """

    soil_moisture = enum_code(soil_moisture)
    ground_layer = enum_code(ground_layer)
    vegetation = enum_code(vegetation)
    soil_texture = enum_code(soil_texture)
    climate_code = enum_code(climate_code)
    lateral_water = enum_code(lateral_water)
    soil_depth = enum_code(soil_depth)
    dlan = enum_code(dlan)

    if species not in ["Picea abies", "Pinus sylvestris"]:
        raise ValueError(
            f"species must be one of : 'Picea abies' or 'Pinus sylvestris', not '{species}'"
        )

    if latitude < 55.2 or latitude > 69.1 or latitude is None:
        print("latitude must be between (55.2, 69.1)")
        return np.nan
    if altitude < 0 or altitude > 2117 or altitude is None:
        print("altitude must be between (0,2117)")
        return np.nan
    if soil_moisture not in range(1, 6) or soil_moisture is None:
        print("soil_moisture must be int 1 - 5")
        return np.nan
    if ground_layer not in range(1, 7) or ground_layer is None:
        print("ground_layer must be int 1-6")
        return np.nan
    if vegetation not in range(1, 19) or vegetation is None:
        print("Vegetation must be int 1-18")
        return np.nan

    if not isinstance(peat, (bool, np.bool_)):
        print("Peat must be a bool: True or False")
        return np.nan

    if not peat:
        if soil_texture not in range(0, 10) or soil_texture is None:
            print("soil_texture must be int 0-10")
            return np.nan

    if pdisna(soil_depth) and not peat:
        print(
            "soil_depth must be one of float: NA; int 1-5. If soil_depth is NA peat must be True."
        )
        return np.nan

    if not peat:
        if soil_depth not in range(0, 6) or soil_depth is None:
            print(
                "soil_depth must be one of float: NA; int 1-5. "
                "If soil_depth is NA peat must be True."
            )
            return np.nan

    if dlan is not None:
        if dlan < 1 or dlan > 31:
            print("dlan must be one of int: 1-31 or NA.")
            return np.nan

    if climate_code not in ["M1", "M2", "M3", "K1", "K2", "K3"] and not pdisna(climate_code):
        print("climate_code must be one of float: NA; str: M1, M2, M3, K1, K2, K3")
        return np.nan
    if lateral_water not in range(1, 4) or lateral_water is None:
        print("lateral_water must be int 1-3")
        return np.nan

    if incline_percent < 0.0 or incline_percent > 100.0:
        print("incline_percent must be float 0-100")
        return np.nan
    if aspect < 0 or aspect > 360:
        print("Aspect must be float 0-360")
        return np.nan

    if not isinstance(gotland, (bool, np.bool_)):
        print("Gotland must be a bool: True or False")
        return np.nan
    if not isinstance(nfi_adjustments, (bool, np.bool_)):
        print("nfi_adjustments must be a bool: True or False")
    if not isinstance(coast, (bool, np.bool_)):
        print("coast must be a bool: True or False")
    if not isinstance(limes_norrlandicus, (bool, np.bool_)):
        print("limes_norrlandicus must be a bool: True or False")

    if nfi_adjustments:
        limes_norrlandicus = True
        coast = True

    args = {
        "vegetation": vegetation,
        "ground_layer": ground_layer,
        "latitude": latitude,
        "altitude": altitude,
        "aspect": aspect,
        "incline_percent": incline_percent,
        "soil_moisture": soil_moisture,
        "soil_texture": soil_texture,
        "soil_depth": soil_depth,
        "peat": peat,
        "lateral_water": lateral_water,
        "ditched": ditched,
        "climate_code": climate_code,
        "coast": coast,
        "limes_norrlandicus": limes_norrlandicus,
        "gotland": gotland,
        "nfi_adjustments": nfi_adjustments,
        "dlan": dlan,
    }

    if species == "Picea abies":
        SIS = NFI_SIS_SPRUCE(**args)
        fn = (
            Hagglund_1970.height_trajectory.picea_abies.northern_sweden
            if latitude >= 60
            else Hagglund_1970.height_trajectory.picea_abies.southern_sweden
        )
        spec = {TreeSpecies.Sweden.picea_abies}
    else:
        SIS = NFI_SIS_PINE(**args)
        fn = Hagglund_1970.height_trajectory.pinus_sylvestris.sweden
        spec = {TreeSpecies.Sweden.pinus_sylvestris}

    return SiteIndexValue(
        SIS,
        reference_age=Age.TOTAL(100),
        species=spec,
        fn=fn,
    )
