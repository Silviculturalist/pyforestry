from typing import Optional
from Munin.Timber.Timber import Timber
from Munin.Volume import Andersson_1954, BrandelVolume, carbonnier_1954, Johnsson_1953, Matern_1975, Naslund1947, Eriksson_1973

class SweTimber(Timber):
    def __init__(
        self,
        species: str,
        diameter_cm: float,
        height_m: float,
        double_bark_mm: Optional[float] = None,
        crown_base_height_m: Optional[float] = None,
        over_bark: bool = True,
        region: str = "southern",  # Default to "southern", can be "northern"
        latitude: Optional[float] = None,
        stump_height_m: Optional[float] = 0.3
    ):
        self.species = species.lower()
        self.diameter_cm = diameter_cm
        self.height_m = height_m
        self.double_bark_mm = double_bark_mm
        self.crown_base_height_m = crown_base_height_m
        self.over_bark = over_bark
        self.region = region.lower()
        self.stump_height_m = stump_height_m

        if latitude is None:
            if self.region == 'northern':
                self.latitude=64
            if self.region == 'southern':
                self.latitude=58
        else: 
            self.latitude = latitude

        self.validate()

    def validate(self):
        
        if self.diameter_cm < 0:
            raise ValueError("Diameter must be larger or equal to than 0 cm: {self.diameter_cm}")

        if self.crown_base_height_m is not None and self.height_m is not None and self.crown_base_height_m >= self.height_m:
            raise ValueError(f'Crown base height ({self.crown_base_height_m} m) cannot be higher than tree height: {self.height_m} m')
        
        if self.stump_height_m < 0:
            raise ValueError(f'Stump height must be larger or equal to 0 m: {self.stump_height_m}')

        if self.region not in ["northern", "southern"]:
            raise ValueError("Region must be 'northern' or 'southern'.")
        if self.species.lower() not in [
            "pinus sylvestris",
            "picea abies",
            "betula",
            "betula pendula",
            "betula pubescens",
        ]:
            raise ValueError(
                "Species must be one of: pinus sylvestris, picea abies, betula, betula pendula, betula pubescens."
            )
        
    def getvolume(self):
        if self.diameter_cm < 5:
            if self.height_m is None:
                raise ValueError('Volume for small trees from Andersson 1954 requires height')
            if self.species.startswith('betula'):
                if self.height_m is not None and self.height_m > 4:
                    vol = Andersson_1954.andersson_1954_volume_small_trees_birch_height_above_4_m(self.diameter_cm,self.height_m)
                else:
                    vol = Andersson_1954.andersson_1954_volume_small_trees_birch_under_diameter_5_cm(self.diameter_cm,self.height_m)
            elif self.species == 'picea abies':
                vol = Andersson_1954.andersson_1954_volume_small_trees_spruce(self.diameter_cm,self.height_m)
            elif self.species == 'pinus sylvestris':
                vol = Andersson_1954.andersson_1954_volume_small_trees_pine(self.diameter_cm,self.height_m)
            else:
                raise ValueError('No functionality for species {self.species} at diameter {self.diameter_cm}')
        elif self.species in ['fagus sylvatica','carpinus betulus']:
            vol = Matern_1975.matern_1975_volume_sweden_beech(self.diameter_cm,self.height_m)
        elif self.species.startswith('quercus'):
            vol = Matern_1975.matern_1975_volume_sweden_oak(self.diameter_cm,self.height_m)
        elif self.species in ['fraxinus excelsior','populus tremula'] or self.species.startswith('alnus'):
            vol = Eriksson_1973.Eriksson_1973_volume_aspen_Sweden(self.diameter_cm,self.height_m)
        elif self.species == 'pinus contorta':
            vol = Eriksson_1973.Eriksson_1973_volume_lodgepole_pine_Sweden(self.diameter_cm,self.height_m)
        elif self.species.startswith('larix'):
            if self.diameter_cm> 50:
                # Force southern pine: create a temporary SweTimber instance with latitude forced to 58 (southern)
                forced_timber = SweTimber(
                    species='pinus sylvestris',
                    diameter_cm=self.diameter_cm,
                    height_m=self.height_m,
                    double_bark_mm=self.double_bark_mm,
                    crown_base_height_m=self.crown_base_height_m,
                    over_bark=self.over_bark,
                    region='southern',  # force southern region
                    latitude=58,        # force southern latitude
                    stump_height_m=self.stump_height_m
                )
                vol = BrandelVolume.get_volume(species='pinus sylvestris',
                                               self.diameter_cm,
                                               self.height_m,
                                               self.latitude,
                                               self.altitude,
                                               self.FieldLayer
                                               , over_bark=True)
            else:
                vol = carbonnier_1954.carbonnier_1954_volume_larch(self.diameter_cm,self.height_m)


        return vol