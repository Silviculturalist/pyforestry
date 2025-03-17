from typing import Optional
from Munin.Timber.Timber import Timber
from Munin.Volume import Andersson_1954, BrandelVolume, carbonnier_1954, Matern_1975, Eriksson_1973
# Import SwedishSite and its region-specific namespace.
from Munin.Site.SwedishSite import SwedishSite

class SweTimber(Timber):
    def __init__(
        self,
        species: str,
        diameter_cm: float,
        height_m: float,
        double_bark_mm: Optional[float] = None,
        crown_base_height_m: Optional[float] = None,
        over_bark: bool = True,
        region: str = "southern",  # Default to "southern"; can be "northern"
        latitude: Optional[float] = None,
        # Optionally, supply a SwedishSite with additional region‐specific parameters.
        swedish_site: Optional[SwedishSite] = None
    ):
        self.species = species.lower()
        self.diameter_cm = diameter_cm
        self.height_m = height_m
        self.double_bark_mm = double_bark_mm
        self.crown_base_height_m = crown_base_height_m
        self.over_bark = over_bark
        self.region = region.lower()
        self.swedish_site = swedish_site

        # If no latitude is provided, set one based on region.
        if latitude is None:
            if self.region == 'northern':
                self.latitude = 64
            elif self.region == 'southern':
                self.latitude = 58
            else:
                raise ValueError("Region must be 'northern' or 'southern'.")
        else:
            self.latitude = latitude

        # Calculate stump height.
        self.stump_height_m = 0.01 * height_m

        self.validate()

    def validate(self):
        
        if self.height_m <= 0:
            raise ValueError('Height must be larger than 0 m: {self.height_m}')

        if self.diameter_cm < 0:
            raise ValueError(f"Diameter must be larger or equal to 0 cm: {self.diameter_cm}")
        if (self.crown_base_height_m is not None and self.height_m is not None and 
            self.crown_base_height_m >= self.height_m):
            raise ValueError(f'Crown base height ({self.crown_base_height_m} m) cannot be higher than tree height: {self.height_m} m')
        if self.stump_height_m < 0:
            raise ValueError(f'Stump height must be larger or equal to 0 m: {self.stump_height_m}')
        if self.region not in ["northern", "southern"]:
            raise ValueError("Region must be 'northern' or 'southern'.")
        if self.species not in [
            "pinus sylvestris",
            "picea abies",
            "betula",
            "betula pendula",
            "betula pubescens",
        ]:
            raise ValueError("Species must be one of: pinus sylvestris, picea abies, betula, betula pendula, betula pubescens.")

    def getvolume(self):
        # Return 0 if diameter is negative (as in C# code)
        if self.diameter_cm < 0:
            return 0

        # Define smallTree condition: a small tree is one with diameter < 4.5 cm or height < 7 m.
        small_tree = (self.diameter_cm < 4.5 or self.height_m < 7)

        sp = self.species  # species is already lower-case

        # Larch
        if sp.startswith('larix'):
            # In the C# code, for Larch we always call the Larch volume function.
            # Here we mimic that by using one volume function for larix.
            # We assume that if the diameter is large (>50 cm) we use the Brandel model,
            # otherwise we use a larch-specific model (here represented by carbonnier_1954).
            if self.diameter_cm > 50:
                if self.swedish_site is not None:
                    vol = BrandelVolume.get_volume(
                        species='pinus sylvestris',  # For larix, the model uses southern pine parameters.
                        diameter_cm=self.diameter_cm,
                        height_m=self.height_m,
                        latitude=self.swedish_site.latitude,
                        altitude=self.swedish_site.altitude,
                        field_layer=self.swedish_site.field_layer.code,
                        over_bark=self.over_bark
                    )
                else:
                    vol = BrandelVolume.get_volume(
                        species='pinus sylvestris',
                        diameter_cm=self.diameter_cm,
                        height_m=self.height_m,
                        latitude=self.latitude,
                        altitude=getattr(self, 'altitude', None),
                        field_layer=getattr(self, 'field_layer', None),
                        over_bark=self.over_bark
                    )
            else:
                vol = carbonnier_1954.carbonnier_1954_volume_larch(self.diameter_cm, self.height_m)

        # Pine (excluding larix sibirica)
        elif sp == 'pinus sylvestris':
                if small_tree:
                    vol = Andersson_1954.andersson_1954_volume_small_trees_pine(self.diameter_cm, self.height_m)
                else:
                    if self.swedish_site is not None:
                        vol = BrandelVolume.get_volume(
                            species='pinus sylvestris',
                            diameter_cm=self.diameter_cm,
                            height_m=self.height_m,
                            latitude=self.swedish_site.latitude,
                            altitude=self.swedish_site.altitude,
                            field_layer=self.swedish_site.field_layer.code,
                            over_bark=self.over_bark
                        )
                    else:
                        vol = BrandelVolume.get_volume(
                            species='pinus sylvestris',
                            diameter_cm=self.diameter_cm,
                            height_m=self.height_m,
                            latitude=self.latitude,
                            altitude=getattr(self, 'altitude', None),
                            field_layer=getattr(self, 'field_layer', None),
                            over_bark=self.over_bark
                        )

        # Spruce
        elif sp == 'picea abies':
            if small_tree:
                vol = Andersson_1954.andersson_1954_volume_small_trees_spruce(self.diameter_cm, self.height_m)
            else:
                if self.swedish_site is not None:
                    vol = BrandelVolume.get_volume(
                        species='picea abies',
                        diameter_cm=self.diameter_cm,
                        height_m=self.height_m,
                        latitude=self.swedish_site.latitude,
                        altitude=self.swedish_site.altitude,
                        field_layer=self.swedish_site.field_layer.code,
                        over_bark=self.over_bark
                    )
                else:
                    vol = BrandelVolume.get_volume(
                        species='picea abies',
                        diameter_cm=self.diameter_cm,
                        height_m=self.height_m,
                        latitude=self.latitude,
                        altitude=getattr(self, 'altitude', None),
                        field_layer=getattr(self, 'field_layer', None),
                        over_bark=self.over_bark
                    )

        # Birch
        elif sp.startswith('betula'):
            if small_tree:
                # Use different Andersson_1954 functions based on tree height.
                if self.height_m > 4:
                    vol = Andersson_1954.andersson_1954_volume_small_trees_birch_height_above_4_m(self.diameter_cm, self.height_m)
                else:
                    vol = Andersson_1954.andersson_1954_volume_small_trees_birch_under_diameter_5_cm(self.diameter_cm, self.height_m)
            else:
                if self.swedish_site is not None:
                    vol = BrandelVolume.get_volume(
                        species='betula',
                        diameter_cm=self.diameter_cm,
                        height_m=self.height_m,
                        latitude=self.swedish_site.latitude,
                        altitude=self.swedish_site.altitude,
                        field_layer=self.swedish_site.field_layer.code,
                        over_bark=self.over_bark
                    )
                else:
                    vol = BrandelVolume.get_volume(
                        species='betula',
                        diameter_cm=self.diameter_cm,
                        height_m=self.height_m,
                        latitude=self.latitude,
                        altitude=getattr(self, 'altitude', None),
                        field_layer=getattr(self, 'field_layer', None),
                        over_bark=self.over_bark
                    )

        # Aspen (and related species)
        elif sp in ['fraxinus excelsior', 'populus tremula'] or sp.startswith('alnus'):
            vol = Eriksson_1973.Eriksson_1973_volume_aspen_Sweden(self.diameter_cm, self.height_m)

        # Lodgepole pine (Contorta)
        elif sp == 'pinus contorta':
            if small_tree:
                vol = Andersson_1954.andersson_1954_volume_small_trees_pine(self.diameter_cm, self.height_m)
            else:
                vol = Eriksson_1973.Eriksson_1973_volume_lodgepole_pine_Sweden(self.diameter_cm, self.height_m)

        # Beech
        elif sp in ['fagus sylvatica', 'carpinus betulus']:
            vol = Matern_1975.matern_1975_volume_sweden_beech(self.diameter_cm, self.height_m)

        # Oak
        elif sp.startswith('quercus'):
            vol = Matern_1975.matern_1975_volume_sweden_oak(self.diameter_cm, self.height_m)

        # Default fallback: use Birch model
        else:
            if small_tree:
                if self.height_m > 4:
                    vol = Andersson_1954.andersson_1954_volume_small_trees_birch_height_above_4_m(self.diameter_cm, self.height_m)
                else:
                    vol = Andersson_1954.andersson_1954_volume_small_trees_birch_under_diameter_5_cm(self.diameter_cm, self.height_m)
            else:
                if self.swedish_site is not None:
                    vol = BrandelVolume.get_volume(
                        species='betula',
                        diameter_cm=self.diameter_cm,
                        height_m=self.height_m,
                        latitude=self.swedish_site.latitude,
                        altitude=self.swedish_site.altitude,
                        field_layer=self.swedish_site.field_layer.code,
                        over_bark=self.over_bark
                    )
                else:
                    vol = BrandelVolume.get_volume(
                        species='betula',
                        diameter_cm=self.diameter_cm,
                        height_m=self.height_m,
                        latitude=self.latitude,
                        altitude=getattr(self, 'altitude', None),
                        field_layer=getattr(self, 'field_layer', None),
                        over_bark=self.over_bark
                    )
        return vol