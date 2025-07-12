
from dataclasses import dataclass, field
from typing import Optional, Union
from Munin.helpers.primitives import SiteBase
from .enums import Sweden
from Munin.siteindex.sweden.sis import Hagglund_Lundmark_1979_SIS, eko_pm_2008_estimate_si_birch
from Munin.geo.humidity import eriksson_1986_humidity
from Munin.geo.temperature import Odin_temperature_sum

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
        from Munin.geo.geo import RetrieveGeoCode
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