from typing import Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from Munin.Site.SiteBase import SiteBase
from Munin.Geo.Geo import RetrieveGeoCode
from Munin.SiteIndex.sweden.SIS import Hagglund_Lundmark_1979_SIS, eko_pm_2008_estimate_si_birch
from Munin.Geo.Humidity import eriksson_1986_humidity
from Munin.Geo.Temperature import Odin_temperature_sum

# -------------------------------------------------------------------
# Helper dataclasses for region-specific properties
# -------------------------------------------------------------------

@dataclass(frozen=True)
class Vegetation:
    code: int
    swedish_name: str
    english_name: str
    index: float

@dataclass(frozen=True)
class BottomLayerType:
    code: int
    english_name: str
    swedish_name: str

@dataclass(frozen=True)
class SoilWaterCat:
    code: int
    swedish_description: str
    english_description: str

@dataclass(frozen=True)
class SoilDepthCat:
    code: int
    swedish_description: str
    english_description: str

@dataclass(frozen=True)
class SoilTextureCategory:
    code: int
    swedish_name: str
    english_name: str
    short_name: str

@dataclass(frozen=True)
class SoilMoistureData:
    code: int
    swedish_description: str
    english_description: str

# -------------------------------------------------------------------
# Region-specific enums defined for the Sweden model
# -------------------------------------------------------------------

class SwedenFieldLayer(Enum):
    HIGH_HERB_WITHOUT_SHRUBS = Vegetation(1, "Högört utan ris", "Rich-herb without shrubs", 4)
    HIGH_HERB_WITH_SHRUBS_BLUEBERRY = Vegetation(2, "Högört med ris/blåbär", "Rich-herb with shrubs/bilberry", 2.5)
    HIGH_HERB_WITH_SHRUBS_LINGON = Vegetation(3, "Högört med ris/lingon", "Rich-herb with shrubs/lingonberry", 2)
    LOW_HERB_WITHOUT_SHRUBS = Vegetation(4, "Lågört utan ris", "Low-herb without shrubs", 3)
    LOW_HERB_WITH_SHRUBS_BLUEBERRY = Vegetation(5, "Lågört med ris/blåbär", "Low-herb with shrubs/bilberry", 2.5)
    LOW_HERB_WITH_SHRUBS_LINGON = Vegetation(6, "Lågört med ris/lingon", "Low-herb with shrubs/lingonberry", 2)
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
    DEEP = SoilDepthCat(1, "Mäktigt >70 cm. Inga synliga hällar", "Deep >70cm. No visible stone outcrops.")
    RATHER_SHALLOW = SoilDepthCat(2, "Tämligen grunt jorddjupt 20-70 cm", "Rather shallow soil depth, 20-70 cm")
    SHALLOW = SoilDepthCat(3, "Grunt jorddjup < 20 cm. Rikligt med hällar.", "Rather shallow soil depth < 20 cm. Plenty of stony outcrops.")
    VARYING = SoilDepthCat(4, "Mycket varierande jorddjup. Brottytor i berggrunden delvis synliga.", "Widely varying soil depth. Breaks in bedrock partly visible.")

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
    MOIST = SoilMoistureData(4, "fuktig", "Moist (subsoil water depth <1 m, and pools visible in hollows)")
    WET = SoilMoistureData(5, "blöt", "Wet (subsoil water pools visible)")

# -------------------------------------------------------------------
# Define the Sweden namespace for this model.
# -------------------------------------------------------------------

class Sweden:
    FieldLayer = SwedenFieldLayer
    BottomLayer = SwedenBottomLayer
    SoilWater = SwedenSoilWater
    SoilDepth = SwedenSoilDepth
    SoilTextureTill = SwedenSoilTextureTill
    SoilTextureSediment = SwedenSoilTextureSediment
    SoilMoistureEnum = SwedenSoilMoisture

# -------------------------------------------------------------------
# SwedishSite using the Sweden namespace
# -------------------------------------------------------------------
@dataclass(frozen=True)
class SwedishSite(SiteBase):
    """
    A robust SwedishSite class that carries at least latitude and longitude.
    Other attributes (altitude, field layer, etc.) are optional.
    If not provided (or if computation fails), the computed attributes will be left as None.
    """
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    field_layer: Optional[Sweden.FieldLayer] = None
    bottom_layer: Optional[Sweden.BottomLayer] = None
    # Accept either a SoilTextureTill or SoilTextureSediment enum member.
    soil_texture: Optional[Union[Sweden.SoilTextureTill, Sweden.SoilTextureSediment]] = None
    soil_moisture: Optional[Sweden.SoilMoistureEnum] = None
    soil_depth: Optional[Sweden.SoilDepth] = None
    soil_water: Optional[Sweden.SoilWater] = None
    aspect: Optional[float] = None
    incline_percent: Optional[float] = None
    ditched: Optional[bool] = None
    n_of_limes_norrlandicus: Optional[bool] = None

    # Computed attributes are optional and default to None.
    temperature_sum_odin1983: Optional[float] = field(init=False, default=None)
    county_code: Optional[str] = field(init=False, default=None)
    humidity: Optional[float] = field(init=False, default=None)
    distance_to_coast: Optional[float] = field(init=False, default=None)
    climate_code: Optional[str] = field(init=False, default=None)
    sis_spruce_100: Optional[float] = field(init=False, default=None)
    sis_pine_100: Optional[float] = field(init=False, default=None)
    sis_birch_50: Optional[float] = field(init=False, default=None)

    def __post_init__(self) -> None:
        # Compute n_of_limes_norrlandicus from latitude.
        try:
            object.__setattr__(self, 'n_of_limes_norrlandicus', self.latitude > 60)
        except Exception:
            object.__setattr__(self, 'n_of_limes_norrlandicus', None)

        # Compute temperature sum if altitude is available.
        try:
            if self.altitude is not None:
                ts = Odin_temperature_sum(latitude=self.latitude, altitude=self.altitude)
                object.__setattr__(self, 'temperature_sum_odin1983', ts)
            else:
                object.__setattr__(self, 'temperature_sum_odin1983', None)
        except Exception:
            object.__setattr__(self, 'temperature_sum_odin1983', None)

        # Compute county code.
        try:
            cc = RetrieveGeoCode.getCountyCode(lon=self.longitude, lat=self.latitude)
            object.__setattr__(self, 'county_code', cc)
        except Exception:
            object.__setattr__(self, 'county_code', None)

        # Compute humidity.
        try:
            h = eriksson_1986_humidity(longitude=self.longitude, latitude=self.latitude)
            object.__setattr__(self, 'humidity', h)
        except Exception:
            object.__setattr__(self, 'humidity', None)

        # Compute distance to coast.
        try:
            d = RetrieveGeoCode.getDistanceToCoast(lon=self.longitude, lat=self.latitude)
            object.__setattr__(self, 'distance_to_coast', d)
        except Exception:
            object.__setattr__(self, 'distance_to_coast', None)

        # Compute climate code.
        try:
            cc2 = RetrieveGeoCode.getClimateCode(lon=self.longitude, lat=self.latitude)
            object.__setattr__(self, 'climate_code', cc2)
        except Exception:
            object.__setattr__(self, 'climate_code', None)

        # Attempt to compute sis_spruce_100 if all required parameters are available.
        try:
            if (self.altitude is not None and
                self.field_layer is not None and
                self.bottom_layer is not None and
                self.soil_texture is not None and
                self.soil_moisture is not None and
                self.soil_depth is not None and
                self.soil_water is not None and
                self.aspect is not None and
                self.incline_percent is not None and
                self.ditched is not None and
                self.climate_code is not None):
                
                spruce = Hagglund_Lundmark_1979_SIS(
                    latitude=self.latitude,
                    altitude=self.altitude,
                    soil_moisture=self.soil_moisture.value.code,
                    ground_layer=self.bottom_layer.value.code,
                    vegetation=self.field_layer.value.code,
                    soil_texture=self.soil_texture.value.code,
                    climate_code=self.climate_code,
                    lateral_water=self.soil_water.value.code,
                    soil_depth=self.soil_depth.value.code,
                    incline_percent=self.incline_percent,
                    aspect=self.aspect,
                    ditched=self.ditched,
                    peat=self.soil_texture in (Sweden.SoilTextureSediment.PEAT, Sweden.SoilTextureTill.PEAT),
                    gotland=(self.county_code == 31) if self.county_code is not None else False,
                    coast=(self.distance_to_coast < 50) if self.distance_to_coast is not None else False,
                    limes_norrlandicus=self.n_of_limes_norrlandicus,
                    nfi_adjustments=False,
                    species='Picea abies',
                    dlan=self.county_code if self.county_code is not None else ""
                )
                object.__setattr__(self, 'sis_spruce_100', spruce)
            else:
                object.__setattr__(self, 'sis_spruce_100', None)
        except Exception:
            object.__setattr__(self, 'sis_spruce_100', None)

        # Attempt to compute sis_pine_100 in a similar manner.
        try:
            if (self.altitude is not None and
                self.field_layer is not None and
                self.bottom_layer is not None and
                self.soil_texture is not None and
                self.soil_moisture is not None and
                self.soil_depth is not None and
                self.soil_water is not None and
                self.aspect is not None and
                self.incline_percent is not None and
                self.ditched is not None and
                self.climate_code is not None):
                
                pine = Hagglund_Lundmark_1979_SIS(
                    latitude=self.latitude,
                    altitude=self.altitude,
                    soil_moisture=self.soil_moisture.value.code,
                    ground_layer=self.bottom_layer.value.code,
                    vegetation=self.field_layer.value.code,
                    soil_texture=self.soil_texture.value.code,
                    climate_code=self.climate_code,
                    lateral_water=self.soil_water.value.code,
                    soil_depth=self.soil_depth.value.code,
                    incline_percent=self.incline_percent,
                    aspect=self.aspect,
                    ditched=self.ditched,
                    peat=self.soil_texture in (Sweden.SoilTextureSediment.PEAT, Sweden.SoilTextureTill.PEAT),
                    gotland=(self.county_code == 31) if self.county_code is not None else False,
                    coast=(self.distance_to_coast < 50) if self.distance_to_coast is not None else False,
                    limes_norrlandicus=self.n_of_limes_norrlandicus,
                    nfi_adjustments=False,
                    species='Pinus sylvestris',
                    dlan=self.county_code if self.county_code is not None else ""
                )
                object.__setattr__(self, 'sis_pine_100', pine)
            else:
                object.__setattr__(self, 'sis_pine_100', None)
        except Exception:
            object.__setattr__(self, 'sis_pine_100', None)

        # Compute sis_birch_50 if possible.
        try:
            birch = eko_pm_2008_estimate_si_birch(
                altitude=self.altitude if self.altitude is not None else 0,
                latitude=self.latitude,
                vegetation=self.field_layer.value.code if self.field_layer is not None else 0,
                ground_layer=self.bottom_layer.value.code if self.bottom_layer is not None else 0,
                lateral_water=self.soil_water.value.code if self.soil_water is not None else 0,
                soil_moisture=self.soil_moisture.value.code if self.soil_moisture is not None else 0
            )
            object.__setattr__(self, 'sis_birch_50', birch)
        except Exception:
            object.__setattr__(self, 'sis_birch_50', None)