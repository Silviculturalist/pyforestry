### 
# Some basic structures for Swedish Sites
###
from dataclasses import dataclass, field
from Munin.Geo.Geo import RetrieveGeoCode
from Munin.SiteIndex.sweden.SIS import Hagglund_Lundmark_1979_SIS, eko_pm_2008_estimate_si_birch
from Munin.Geo.Humidity import eriksson_1986_humidity
from Munin.Geo.Temperature import Odin_temperature_sum

@dataclass(frozen=True)
class Vegetation:
    code: int
    swedish_name: str
    english_name: str
    index: float

class FieldLayer:
    # Rich-herb without shrubs
    high_herb_without_shrubs = Vegetation(1, "Högört utan ris", "Rich-herb without shrubs", 4)
    # Rich-herb with shrubs/bilberry
    high_herb_with_shrubs_blueberry = Vegetation(2, "Högört med ris/blåbär", "Rich-herb with shrubs/bilberry", 2.5)
    # Rich-herb with shrubs/lingonberry
    high_herb_with_shrubs_lingon = Vegetation(3, "Högört med ris/lingon", "Rich-herb with shrubs/lingonberry", 2)
    # Low-herb without shrubs
    low_herb_without_shrubs = Vegetation(4, "Lågört utan ris", "Low-herb without shrubs", 3)
    # Low-herb with shrubs/bilberry
    low_herb_with_shrubs_blueberry = Vegetation(5, "Lågört med ris/blåbär", "Low-herb with shrubs/bilberry", 2.5)
    # Low-herb with shrubs/lingonberry
    low_herb_with_shrubs_lingon = Vegetation(6, "Lågört med ris/lingon", "Low-herb with shrubs/lingonberry", 2)
    # No field layer
    no_field_layer = Vegetation(7, "Utan fältskikt", "No field layer", 3)
    # Broadleaved grass
    broadleaved_grass = Vegetation(8, "Bredbl. gräs", "Broadleaved grass", 2.5)
    # Thinleaved grass
    thinleaved_grass = Vegetation(9, "Smalbl. gräs", "Thinleaved grass", 1.5)
    # Sedge, high
    sedge_high = Vegetation(10, "Carex ssp.,Hög starr", "Sedge, high", -3)
    # Sedge, low
    sedge_low = Vegetation(11, "Carex ssp.,Låg starr", "Sedge, low", -3)
    # Horsetail
    horsetail = Vegetation(12, "Fräken", "Horsetail, Equisetum ssp.", 1)
    # European blueberry / bilberry
    bilberry = Vegetation(13, "Blåbär", "European blueberry, bilberry", 0)
    # Lingonberry
    lingonberry = Vegetation(14, "Lingon", "Lingonberry", -0.5)
    # Crowberry
    crowberry = Vegetation(15, "Kråkbär", "Crowberry", -3)
    # Poor shrub
    poor_shrub = Vegetation(16, "Fattigris", "Poor shrub", -5)
    # Lichen, frequent occurrence
    lichen_frequent = Vegetation(17, "Lavrik", "Lichen, frequent occurrence", -0.5)
    # Lichen, dominating
    lichen_dominant = Vegetation(18, "Lav", "Lichen, dominating", -1)

@dataclass(frozen=True)
class BottomLayerType:
    code: int
    english_name: str
    swedish_name: str

class BottomLayer:
    lichen_type = BottomLayerType(
        code=1,
        english_name="Lichen type",
        swedish_name="Lavtyp"
    )
    lichen_rich_bogmoss = BottomLayerType(
        code=2,
        english_name="Lichen-rich bogmoss type",
        swedish_name="Lavrik vitmosstyp"
    )
    lichen_rich = BottomLayerType(
        code=3,
        english_name="Lichen-rich",
        swedish_name="Lavrik typ"
    )
    bogmoss_type = BottomLayerType(
        code=4,
        english_name="Bogmoss type (Sphagnum)",
        swedish_name="Vitmosstyp"
    )
    swamp_moss = BottomLayerType(
        code=5,
        english_name="Swamp moss type",
        swedish_name="Sumpmosstyp"
    )
    fresh_moss = BottomLayerType(
        code=6,
        english_name="Fresh moss type",
        swedish_name="Friskmosstyp"
    )



@dataclass(frozen=True)
class SoilWaterCat:
    code: int
    swedish_description: str
    english_description: str

class SoilWater:
    # Soil water code (rörligt markvatten / lateral water, Swedish NFI RÖRLMVA)
    seldom_never = SoilWaterCat(1, "saknas", "Seldom/never")
    shorter_periods = SoilWaterCat(2, "kortare perioder", "Shorter periods")
    longer_periods = SoilWaterCat(3, "längre perioder", "Longer periods")


@dataclass(frozen=True)
class SoilDepthCat:
    code:   int
    swedish_description: str
    english_description: str


class SoilDepth:
    deep = SoilDepthCat(1,'Mäktigt >70 cm. Inga synliga hällar','Deep >70cm. No visible stone outcrops.')
    rather_shallow = SoilDepthCat(2,'Tämligen grunt jorddjupt 20-70 cm', 'Rather shallow soil depth, 20-70 cm')
    shallow = SoilDepthCat(3,'Grunt jorddjup < 20 cm. Rikligt med hällar.','Rather shallow soil depth < 20 cm. Plenty of stony outcrops.')
    varying = SoilDepthCat(4,'Mycket varierande jorddjup. Brottytor i berggrunden delvis synliga.','Widely varying soil depth. Breaks in bedrock partly visible.')


@dataclass(frozen=True)
class SoilTextureCategory:
    code: int
    swedish_name: str
    english_name: str
    short_name: str

class SoilTexture:
    class till:
        boulder = SoilTextureCategory(
            code=1,
            swedish_name="Stenig/blockig morän",
            english_name="Boulder rich/stony till",
            short_name="Boulder"
        )
        gravel = SoilTextureCategory(
            code=2,
            swedish_name="Grusig morän",
            english_name="Gravelly till",
            short_name="Gravel"
        )
        sandy = SoilTextureCategory(
            code=3,
            swedish_name="Sandig morän",
            english_name="Sandy till",
            short_name="Coarse sand"
        )
        sandy_moig = SoilTextureCategory(
            code=4,
            swedish_name="Sandig-moig morän",
            english_name="Sandy-silty till",
            short_name="Medium sand"
        )
        silty_sand = SoilTextureCategory(
            code=5,
            swedish_name="Sandig-moig morän",
            english_name="Silty-sandy till",
            short_name="Fine sand"
        )
        coarse_silty = SoilTextureCategory(
            code=6,
            swedish_name="Moig morän",
            english_name="Coarse silty till",
            short_name="Coarse silt"
        )
        fine_silty = SoilTextureCategory(
            code=7,
            swedish_name="Mjälig morän",
            english_name="Fine silty till",
            short_name="Fine silt"
        )
        clay = SoilTextureCategory(
            code=8,
            swedish_name="Lerig morän",
            english_name="Clayey till",
            short_name="Clay"
        )
        peat = SoilTextureCategory(
            code=9,
            swedish_name="Torv",
            english_name="Peat",
            short_name="Peat"
        )

    class sediment:
        boulder = SoilTextureCategory(
            code=1,
            swedish_name="Sten/block",
            english_name="Boulders/stones",
            short_name="Boulder"
        )
        gravel = SoilTextureCategory(
            code=2,
            swedish_name="Grus",
            english_name="Gravel",
            short_name="Gravel"
        )
        coarsesand = SoilTextureCategory(
            code=3,
            swedish_name="Grovsand",
            english_name="Coarse sand",
            short_name="Coarse sand"
        )
        mediumsand = SoilTextureCategory(
            code=4,
            swedish_name="Mellansand",
            english_name="Medium sand",
            short_name="Medium sand"
        )
        finesand = SoilTextureCategory(
            code=5,
            swedish_name="Grovmo",
            english_name="Fine sand",
            short_name="Fine sand"
        )
        coarsesilt = SoilTextureCategory(
            code=6,
            swedish_name="Finmo",
            english_name="Coarse silt",
            short_name="Coarse silt"
        )
        finesilt = SoilTextureCategory(
            code=7,
            swedish_name="Mjäla",
            english_name="Fine silt",
            short_name="Fine silt"
        )
        clay = SoilTextureCategory(
            code=8,
            swedish_name="Lera",
            english_name="Clay",
            short_name="Clay"
        )
        peat = SoilTextureCategory(
            code=9,
            swedish_name="Torv",
            english_name="Peat",
            short_name="Peat"
        )

@dataclass(frozen=True)
class SoilMoisture:
    code: int
    swedish_description: str
    english_description: str

class SoilMoistures:
    # Soil moisture code (subsoil water conditions)
    dry = SoilMoisture(
        code=1,
        swedish_description="torr",
        english_description="Dry (subsoil water depth >2 m)"
    )
    mesic = SoilMoisture(
        code=2,
        swedish_description="frisk",
        english_description="Mesic (subsoil water depth = 1-2 m)"
    )
    mesic_moist = SoilMoisture(
        code=3,
        swedish_description="frisk-fuktig",
        english_description="Mesic-moist (subsoil water depth <1 m)"
    )
    moist = SoilMoisture(
        code=4,
        swedish_description="fuktig",
        english_description="Moist (subsoil water depth <1 m, and pools visible in hollows)"
    )
    wet = SoilMoisture(
        code=5,
        swedish_description="blöt",
        english_description="Wet (subsoil water pools visible)"
    )

@dataclass
class SwedishSite:
    '''
    Helper for Swedish sites.
    '''
    latitude:float
    longitude:float
    altitude:float
    FieldLayer:FieldLayer
    BottomLayer:BottomLayer
    SoilTexture:SoilTexture
    SoilMoisture:SoilMoisture
    SoilDepth:SoilDepth
    SoilWater:SoilWater
    aspect:float
    ditched:bool
    limes_norrlandicus:bool

    # Computed attributes (not provided during initialization)
    temperature_sum_odin1983: float = field(init=False)
    county_code: str = field(init=False)
    humidity: float = field(init=False)
    distance_to_coast: float = field(init=False)
    climate_code: str = field(init=False)
    sis_spruce_100: float = field(init=False)
    sis_pine_100: float = field(init=False)
    sis_birch_50: float = field(init=False)
        
    def __post_init__(self) -> None:
        # Compute temperature sum using latitude and altitude.
        self.temperature_sum_odin1983 = Odin_temperature_sum(latitude=self.latitude, altitude=self.altitude)
        # Retrieve the county code from geographic coordinates.
        self.county_code = RetrieveGeoCode.getCountyCode(lon=self.longitude, lat=self.latitude)
        # Compute humidity using the Eriksson (1986) method.
        self.humidity = eriksson_1986_humidity(longitude=self.longitude, latitude=self.latitude)
        # Calculate distance to coast.
        self.distance_to_coast = RetrieveGeoCode.getDistanceToCoast(lon=self.longitude, lat=self.latitude)
        # Get the climate code based on coordinates.
        self.climate_code = RetrieveGeoCode.getClimateCode(lon=self.longitude, lat=self.latitude)
        # Calculate volume estimates using various methods.
        # Replace the ellipsis with actual arguments as required by the functions.
        self.sis_spruce_100 = Hagglund_Lundmark_1979_SIS(...)  
        self.sis_pine_100 = Hagglund_Lundmark_1979_SIS(...)
        self.sis_birch_50 = eko_pm_2008_estimate_si_birch(...)