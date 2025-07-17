from enum import Enum
from typing import Optional

from .sweden_site_primitives import (
    BottomLayerType,
    ClimateZoneData,
    CountyData,
    SoilDepthCat,
    SoilMoistureData,
    SoilTextureCategory,
    SoilWaterCat,
    Vegetation,
)


class SwedenFieldLayer(Enum):
    HIGH_HERB_WITHOUT_SHRUBS = Vegetation(1, "Högört utan ris", "Rich-herb without shrubs", 4)
    HIGH_HERB_WITH_SHRUBS_BLUEBERRY = Vegetation(
        2, "Högört med ris/blåbär", "Rich-herb with shrubs/bilberry", 2.5
    )
    HIGH_HERB_WITH_SHRUBS_LINGON = Vegetation(
        3, "Högört med ris/lingon", "Rich-herb with shrubs/lingonberry", 2
    )
    LOW_HERB_WITHOUT_SHRUBS = Vegetation(4, "Lågört utan ris", "Low-herb without shrubs", 3)
    LOW_HERB_WITH_SHRUBS_BLUEBERRY = Vegetation(
        5, "Lågört med ris/blåbär", "Low-herb with shrubs/bilberry", 2.5
    )
    LOW_HERB_WITH_SHRUBS_LINGON = Vegetation(
        6, "Lågört med ris/lingon", "Low-herb with shrubs/lingonberry", 2
    )
    NO_FIELD_LAYER = Vegetation(7, "Utan fältskikt", "No field layer", 3)
    BROADLEAVED_GRASS = Vegetation(8, "Bredbl. gräs", "Broadleaved grass", 2.5)
    THINLEAVED_GRASS = Vegetation(9, "Smalbl. gräs", "Thinleaved grass", 1.5)
    SEDGE_HIGH = Vegetation(10, "Carex ssp.,Hög starr", "Sedge, high", -3)
    SEDGE_LOW = Vegetation(11, "Carex ssp.,Låg starr", "Sedge, low", -3)
    HORSETAIL = Vegetation(12, "Fräken", "Horsetail, Equisetum ssp.", 1)
    BILBERRY = Vegetation(13, "Blåbär", "European blueberry, bilberry", 0)
    LINGONBERRY = Vegetation(14, "Lingon", "Lingonberry", -0.5)
    CROWBERRY = Vegetation(15, "Kråkbär", "Crowberry", -3)
    POOR_SHRUB = Vegetation(16, "Fattigris", "Poor shrub", -5)
    LICHEN_FREQUENT = Vegetation(17, "Lavrik", "Lichen, frequent occurrence", -0.5)
    LICHEN_DOMINANT = Vegetation(18, "Lav", "Lichen, dominating", -1)


class SwedenBottomLayer(Enum):
    LICHEN_TYPE = BottomLayerType(1, "Lichen type", "Lavtyp")
    LICHEN_RICH_BOGMOSS = BottomLayerType(2, "Lichen-rich bogmoss type", "Lavrik vitmosstyp")
    LICHEN_RICH = BottomLayerType(3, "Lichen-rich", "Lavrik typ")
    BOGMOSS_TYPE = BottomLayerType(4, "Bogmoss type (Sphagnum)", "Vitmosstyp")
    SWAMP_MOSS = BottomLayerType(5, "Swamp moss type", "Sumpmosstyp")
    FRESH_MOSS = BottomLayerType(6, "Fresh moss type", "Friskmosstyp")


class SwedenSoilWater(Enum):
    SELDOM_NEVER = SoilWaterCat(1, "saknas", "Seldom/never")
    SHORTER_PERIODS = SoilWaterCat(2, "kortare perioder", "Shorter periods")
    LONGER_PERIODS = SoilWaterCat(3, "längre perioder", "Longer periods")


class SwedenSoilDepth(Enum):
    DEEP = SoilDepthCat(
        1, "Mäktigt >70 cm. Inga synliga hällar", "Deep >70cm. No visible stone outcrops."
    )
    RATHER_SHALLOW = SoilDepthCat(
        2, "Tämligen grunt jorddjupt 20-70 cm", "Rather shallow soil depth, 20-70 cm"
    )
    SHALLOW = SoilDepthCat(
        3,
        "Grunt jorddjup < 20 cm. Rikligt med hällar.",
        "Rather shallow soil depth < 20 cm. Plenty of stony outcrops.",
    )
    VARYING = SoilDepthCat(
        4,
        "Mycket varierande jorddjup. Brottytor i berggrunden delvis synliga.",
        "Widely varying soil depth. Breaks in bedrock partly visible.",
    )


class SwedenSoilTextureTill(Enum):
    BOULDER = SoilTextureCategory(1, "Stenig/blockig morän", "Boulder rich/stony till", "Boulder")
    GRAVEL = SoilTextureCategory(2, "Grusig morän", "Gravelly till", "Gravel")
    SANDY = SoilTextureCategory(3, "Sandig morän", "Sandy till", "Coarse sand")
    SANDY_MOIG = SoilTextureCategory(4, "Sandig-moig morän", "Sandy-silty till", "Medium sand")
    SILTY_SAND = SoilTextureCategory(5, "Sandig-moig morän", "Silty-sandy till", "Fine sand")
    COARSE_SILTY = SoilTextureCategory(6, "Moig morän", "Coarse silty till", "Coarse silt")
    FINE_SILTY = SoilTextureCategory(7, "Mjälig morän", "Fine silty till", "Fine silt")
    CLAY = SoilTextureCategory(8, "Lerig morän", "Clayey till", "Clay")
    PEAT = SoilTextureCategory(9, "Torv", "Peat", "Peat")


class SwedenSoilTextureSediment(Enum):
    BOULDER = SoilTextureCategory(1, "Sten/block", "Boulders/stones", "Boulder")
    GRAVEL = SoilTextureCategory(2, "Grus", "Gravel", "Gravel")
    COARSE_SAND = SoilTextureCategory(3, "Grovsand", "Coarse sand", "Coarse sand")
    MEDIUM_SAND = SoilTextureCategory(4, "Mellansand", "Medium sand", "Medium sand")
    FINE_SAND = SoilTextureCategory(5, "Grovmo", "Fine sand", "Fine sand")
    COARSE_SILT = SoilTextureCategory(6, "Finmo", "Coarse silt", "Coarse silt")
    FINE_SILT = SoilTextureCategory(7, "Mjäla", "Fine silt", "Fine silt")
    CLAY = SoilTextureCategory(8, "Lera", "Clay", "Clay")
    PEAT = SoilTextureCategory(9, "Torv", "Peat", "Peat")


class SwedenSoilMoisture(Enum):
    DRY = SoilMoistureData(1, "torr", "Dry (subsoil water depth >2 m)")
    MESIC = SoilMoistureData(2, "frisk", "Mesic (subsoil water depth = 1-2 m)")
    MESIC_MOIST = SoilMoistureData(3, "frisk-fuktig", "Mesic-moist (subsoil water depth <1 m)")
    MOIST = SoilMoistureData(
        4, "fuktig", "Moist (subsoil water depth <1 m, and pools visible in hollows)"
    )
    WET = SoilMoistureData(5, "blöt", "Wet (subsoil water pools visible)")


class SwedenCounty(Enum):
    NORRBOTTENS_LAPPMARK = CountyData(1, "Norrbottens lappmark (BD lappm)")
    NORRBOTTENS_KUSTLAND = CountyData(2, "Norrbottens kustland (BD kust)")
    VASTERBOTTENS_LAPPMARK = CountyData(3, "Västerbottens lappmark (AC lappm)")
    VASTERBOTTENS_KUSTLAND = CountyData(4, "Västerbottens kustland (AC kust)")
    JAMTLAND_JAMTLANDS = CountyData(5, "Jämtland - Jämtlands landskap (Z)")
    JAMTLAND_HARJEDALENS = CountyData(6, "Jämtland - Härjedalens landskap (Z Härjed)")
    VASTERNORRLAND_ANGERMANLANDS = CountyData(
        7, "Västernorrland - Ångermanlands landskap (Y Ångerm)"
    )
    VASTERNORRLAND_MEDELPADS = CountyData(8, "Västernorrland - Medelpads landskap (Y Medelp)")
    GAVLEBORG_HALSINGLANDS = CountyData(9, "Gävleborg - Hälsinglands landskap (X Hälsingl)")
    GAVLEBORG_OVRIGA = CountyData(10, "Gävleborg, övriga (X övr)")
    KOPPARBERG_SALEN_IDRE = CountyData(11, "Kopparberg (Dalarna), Sälen - Idre (W)")
    KOPPARBERG_OVRIGA = CountyData(12, "Kopparberg (Dalarna), övriga (W övr)")
    VARMLAND = CountyData(13, "Värmland (S)")
    OREBRO = CountyData(14, "Örebro (T)")
    VASTMANLAND = CountyData(15, "Västmanland (U)")
    UPPSALA = CountyData(16, "Uppsala (C)")
    STOCKHOLM = CountyData(17, "Stockholm (AB)")
    SODERMANLAND = CountyData(18, "Södermanland (D)")
    OSTERGOTLAND = CountyData(19, "Östergötland (E)")
    SKARABORG = CountyData(20, "Skaraborg (R)")
    ALVSBORG_DALSLANDS = CountyData(21, "Älvsborg, Dalslands landskap (P)")
    ALVSBORG_VASTERGOTLANDS = CountyData(22, "Älvsborg, Västergötlands landskap (P)")
    JONKOPING = CountyData(23, "Jönköping (F)")
    KRONOBERG = CountyData(24, "Kronoberg (G)")
    KALMAR = CountyData(25, "Kalmar (H)")
    VASTRA_GOTALANDS = CountyData(26, "Västra Götalands (Göteborg - Bohuslän) (O)")
    HALLAND = CountyData(27, "Halland (N)")
    KRISTIANSTAD = CountyData(28, "Kristianstad (L)")
    MALMOHUS = CountyData(29, "Malmöhus (M)")
    BLEKINGE = CountyData(30, "Blekinge (K)")
    GOTLAND = CountyData(31, "Gotland (I)")

    @classmethod
    def from_code(cls, code: int) -> Optional["SwedenCounty"]:
        """Lookup enum member by code."""
        for member in cls:
            if member.value.code == code:
                return member
        return None  # Return None if code not found


class SwedenClimateZone(Enum):
    M1 = ClimateZoneData(1, "M1", "Maritime, West coast")
    M2 = ClimateZoneData(2, "M2", "Maritime, East coast")
    M3 = ClimateZoneData(3, "M3", "Maritime, Mountain range")
    K1 = ClimateZoneData(4, "K1", "Continental, Middle Sweden")
    K2 = ClimateZoneData(5, "K2", "Continental, Northern Sweden")
    K3 = ClimateZoneData(6, "K3", "Continental, Southern Sweden")

    @classmethod
    def from_code(cls, code: int) -> Optional["SwedenClimateZone"]:
        """Lookup enum member by code."""
        for member in cls:
            if member.value.code == code:
                return member
        return None  # Return None if code not found


class Sweden:
    FieldLayer = SwedenFieldLayer
    BottomLayer = SwedenBottomLayer
    SoilWater = SwedenSoilWater
    SoilDepth = SwedenSoilDepth
    SoilTextureTill = SwedenSoilTextureTill
    SoilTextureSediment = SwedenSoilTextureSediment
    SoilMoistureEnum = SwedenSoilMoisture
    County = SwedenCounty
    ClimateZone = SwedenClimateZone
