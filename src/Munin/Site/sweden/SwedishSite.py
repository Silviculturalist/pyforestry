from typing import Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from Munin.Helpers.Primitives import SiteBase
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

@dataclass(frozen=True)
class CountyData:
    code: int
    label: str #Descriptive string label


@dataclass(frozen=True)
class ClimateZoneData:
    code: int
    label: str # e.g., "M1", "K2"
    description: str # Descriptive name

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

class SwedenCounty(Enum):
    NORRBOTTENS_LAPPMARK = CountyData(1, "Norrbottens lappmark (BD lappm)")
    NORRBOTTENS_KUSTLAND = CountyData(2, "Norrbottens kustland (BD kust)")
    VASTERBOTTENS_LAPPMARK = CountyData(3, "Västerbottens lappmark (AC lappm)")
    VASTERBOTTENS_KUSTLAND = CountyData(4, "Västerbottens kustland (AC kust)")
    JAMTLAND_JAMTLANDS = CountyData(5, "Jämtland - Jämtlands landskap (Z)")
    JAMTLAND_HARJEDALENS = CountyData(6, "Jämtland - Härjedalens landskap (Z Härjed)")
    VASTERNORRLAND_ANGERMANLANDS = CountyData(7, "Västernorrland - Ångermanlands landskap (Y Ångerm)")
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
    def from_code(cls, code: int) -> Optional['SwedenCounty']:
        """Lookup enum member by code."""
        for member in cls:
            if member.value.code == code:
                return member
        return None # Return None if code not found
    
class SwedenClimateZone(Enum):
    M1 = ClimateZoneData(1, "M1", "Maritime, West coast")
    M2 = ClimateZoneData(2, "M2", "Maritime, East coast")
    M3 = ClimateZoneData(3, "M3", "Maritime, Mountain range")
    K1 = ClimateZoneData(4, "K1", "Continental, Middle Sweden")
    K2 = ClimateZoneData(5, "K2", "Continental, Northern Sweden")
    K3 = ClimateZoneData(6, "K3", "Continental, Southern Sweden")

    @classmethod
    def from_code(cls, code: int) -> Optional['SwedenClimateZone']:
        """Lookup enum member by code."""
        for member in cls:
            if member.value.code == code:
                return member
        return None # Return None if code not found
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
    County = SwedenCounty
    ClimateZone = SwedenClimateZone

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
    soil_texture: Optional[Union[Sweden.SoilTextureTill, Sweden.SoilTextureSediment]] = None
    soil_moisture: Optional[Sweden.SoilMoistureEnum] = None
    soil_depth: Optional[Sweden.SoilDepth] = None
    soil_water: Optional[Sweden.SoilWater] = None
    aspect: Optional[float] = None
    incline_percent: Optional[float] = None
    ditched: Optional[bool] = None

    # Computed attributes are optional and default to None.
    temperature_sum_odin1983: Optional[float] = field(init=False, default=None)
    county: Optional[Sweden.County] = field(init=False, default=None)
    humidity: Optional[float] = field(init=False, default=None)
    distance_to_coast: Optional[float] = field(init=False, default=None)
    climate_zone: Optional[Sweden.ClimateZone] = field(init=False, default=None) # Changed type hint
    sis_spruce_100: Optional[float] = field(init=False, default=None)
    sis_pine_100: Optional[float] = field(init=False, default=None)
    sis_birch_50: Optional[float] = field(init=False, default=None)
    n_of_limes_norrlandicus: Optional[bool] = field(init=False, default=None)

    def __post_init__(self) -> None:
        # Compute county first
        try:
            county_enum = RetrieveGeoCode.getCountyCode(lon=self.longitude, lat=self.latitude)
            object.__setattr__(self, 'county', county_enum)
        except Exception:
            object.__setattr__(self, 'county', None)

        # Compute climate zone
        try:
            climate_enum = RetrieveGeoCode.getClimateCode(lon=self.longitude, lat=self.latitude)
            object.__setattr__(self, 'climate_zone', climate_enum)
        except Exception:
            object.__setattr__(self, 'climate_zone', None)

        # Compute n_of_limes_norrlandicus
        try:
            object.__setattr__(self, 'n_of_limes_norrlandicus', self.latitude > 60)
        except Exception:
            object.__setattr__(self, 'n_of_limes_norrlandicus', None)

        # Compute temperature sum
        try:
            if self.altitude is not None:
                ts = Odin_temperature_sum(latitude=self.latitude, altitude_m=self.altitude)
                object.__setattr__(self, 'temperature_sum_odin1983', ts)
            else:
                object.__setattr__(self, 'temperature_sum_odin1983', None)
        except Exception:
            object.__setattr__(self, 'temperature_sum_odin1983', None)

        # Compute humidity
        try:
            h = eriksson_1986_humidity(longitude=self.longitude, latitude=self.latitude)
            object.__setattr__(self, 'humidity', h)
        except Exception:
            object.__setattr__(self, 'humidity', None)

        # Compute distance to coast
        try:
            d = RetrieveGeoCode.getDistanceToCoast(lon=self.longitude, lat=self.latitude)
            object.__setattr__(self, 'distance_to_coast', d)
        except Exception:
            object.__setattr__(self, 'distance_to_coast', None)

        # --- Site Index Calculations ---

        # Check if all required inputs for SIS are present (including computed ones)
        sis_inputs_ok = (
            self.altitude is not None and
            self.field_layer is not None and
            self.bottom_layer is not None and
            self.soil_texture is not None and
            self.soil_moisture is not None and
            self.soil_depth is not None and
            self.soil_water is not None and
            self.aspect is not None and
            self.incline_percent is not None and
            self.ditched is not None and
            self.climate_zone is not None and # Check climate_zone (enum)
            self.county is not None and
            self.n_of_limes_norrlandicus is not None
        )

        if sis_inputs_ok:
            
            #To assure static code analysis tools that this clause is only possible if sis_inputs_ok. 
            #it will otherwise cause warnings when getting the labels.
            assert self.county is not None
            assert self.climate_zone is not None
            assert self.altitude is not None
            assert self.soil_moisture is not None
            assert self.bottom_layer is not None
            assert self.soil_texture is not None
            assert self.field_layer is not None
            assert self.soil_water is not None
            assert self.soil_depth is not None
            assert self.incline_percent is not None
            assert self.aspect is not None
            assert self.ditched is not None
            assert self.n_of_limes_norrlandicus is not None


            # Common inputs derived from site state
            is_peat = self.soil_texture in (Sweden.SoilTextureSediment.PEAT, Sweden.SoilTextureTill.PEAT)
            is_gotland = (self.county == Sweden.County.GOTLAND)
            is_coast = (self.distance_to_coast < 50) if self.distance_to_coast is not None else False
            county_label = self.county.value.code
            climate_label = self.climate_zone.value.label # Use the label string ("M1", "K2", etc.)

            # Attempt Spruce SI
            try:
                spruce_si = Hagglund_Lundmark_1979_SIS(
                    latitude=self.latitude, altitude=self.altitude,
                    soil_moisture=self.soil_moisture.value.code, ground_layer=self.bottom_layer.value.code,
                    vegetation=self.field_layer.value.code, soil_texture=self.soil_texture.value.code,
                    climate_code=climate_label, # Pass the label
                    lateral_water=self.soil_water.value.code, soil_depth=self.soil_depth.value.code,
                    incline_percent=self.incline_percent, aspect=self.aspect, ditched=self.ditched,
                    peat=is_peat, gotland=is_gotland, coast=is_coast,
                    limes_norrlandicus=self.n_of_limes_norrlandicus, nfi_adjustments=False,
                    species='Picea abies', dlan=county_label
                )
                object.__setattr__(self, 'sis_spruce_100', spruce_si)
            except Exception:
                object.__setattr__(self, 'sis_spruce_100', None)

            # Attempt Pine SI
            try:
                pine_si = Hagglund_Lundmark_1979_SIS(
                    latitude=self.latitude, altitude=self.altitude,
                    soil_moisture=self.soil_moisture.value.code, ground_layer=self.bottom_layer.value.code,
                    vegetation=self.field_layer.value.code, soil_texture=self.soil_texture.value.code,
                    climate_code=climate_label, # Pass the label
                    lateral_water=self.soil_water.value.code, soil_depth=self.soil_depth.value.code,
                    incline_percent=self.incline_percent, aspect=self.aspect, ditched=self.ditched,
                    peat=is_peat, gotland=is_gotland, coast=is_coast,
                    limes_norrlandicus=self.n_of_limes_norrlandicus, nfi_adjustments=False,
                    species='Pinus sylvestris', dlan=county_label
                )
                object.__setattr__(self, 'sis_pine_100', pine_si)
            except Exception:
                object.__setattr__(self, 'sis_pine_100', None)
        else:
            # Set SI to None if inputs weren't complete
            object.__setattr__(self, 'sis_spruce_100', None)
            object.__setattr__(self, 'sis_pine_100', None)


        # Compute sis_birch_50 if possible.
        birch_inputs_ok = (
            self.altitude is not None and self.latitude is not None and
            self.field_layer is not None and self.bottom_layer is not None and
            self.soil_water is not None and self.soil_moisture is not None
        )
        if birch_inputs_ok:
            assert self.altitude is not None
            assert self.field_layer is not None
            assert self.bottom_layer is not None
            assert self.soil_water is not None
            assert self.soil_moisture is not None

            try:
                birch_si = eko_pm_2008_estimate_si_birch(
                    altitude=self.altitude, latitude=self.latitude,
                    vegetation=self.field_layer.value.code, ground_layer=self.bottom_layer.value.code,
                    lateral_water=self.soil_water.value.code, soil_moisture=self.soil_moisture.value.code
                )
                object.__setattr__(self, 'sis_birch_50', birch_si)
            except Exception:
                object.__setattr__(self, 'sis_birch_50', None)
        else:
            object.__setattr__(self, 'sis_birch_50', None)