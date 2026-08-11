"""Timber class with Swedish volume model integrations."""

from typing import Optional

from pyforestry.base.timber import Timber

# Import SwedishSite and its region-specific namespace.
from pyforestry.sweden.site import SwedishSite
from pyforestry.sweden.volume import (
    BrandelVolume,
    andersson_1954_volume_small_trees_birch_height_above_4_m,
    andersson_1954_volume_small_trees_birch_under_diameter_5_cm,
    andersson_1954_volume_small_trees_pine,
    andersson_1954_volume_small_trees_spruce,
    carbonnier_1954_volume_larch,
    eriksson_1973_volume_aspen_sweden,
    eriksson_1973_volume_lodgepole_pine_sweden,
    matern_1975_volume_sweden_beech,
    matern_1975_volume_sweden_oak,
)

_VALID_REGIONS = {"northern", "southern"}
_VALID_PRIMARY_SPECIES = {
    "pinus sylvestris",
    "picea abies",
    "betula",
    "betula pendula",
    "betula pubescens",
}


class SweTimber(Timber):
    """Timber record with access to Swedish volume models."""

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
        swedish_site: Optional[SwedishSite] = None,
    ):
        """Instantiate a timber record and infer missing fields."""
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
            if self.region == "northern":
                self.latitude = 64
            elif self.region == "southern":
                self.latitude = 58
            else:
                raise ValueError("Region must be 'northern' or 'southern'.")
        else:
            self.latitude = latitude

        # Calculate stump height.
        self.stump_height_m = 0.01 * height_m

        self.validate()

    def validate(self):
        """Verify that provided parameters are within valid ranges."""
        if self.height_m <= 0:
            raise ValueError(f"Height must be larger than 0 m: {self.height_m}")

        if self.diameter_cm < 0:
            raise ValueError(f"Diameter must be larger or equal to 0 cm: {self.diameter_cm}")
        if (
            self.crown_base_height_m is not None
            and self.height_m is not None
            and self.crown_base_height_m >= self.height_m
        ):
            raise ValueError(
                f"Crown base height ({self.crown_base_height_m} m) cannot be higher than "
                f"tree height: {self.height_m} m"
            )
        if self.stump_height_m < 0:
            raise ValueError(
                f"Stump height must be larger or equal to 0 m: {self.stump_height_m}"
            )  # pragma: no cover - unreachable
        if self.region not in _VALID_REGIONS:
            raise ValueError("Region must be 'northern' or 'southern'.")
        if self.species not in _VALID_PRIMARY_SPECIES:
            raise ValueError(
                "Species must be one of: pinus sylvestris, picea abies, betula, "
                "betula pendula, betula pubescens."
            )

    def getvolume(self):
        """Return stem volume based on species and tree size."""
        # Return 0 if diameter is negative (as in C# code)
        if self.diameter_cm < 0:
            return 0

        # Define smallTree condition: a small tree is one with diameter < 4.5 cm or height < 7 m.
        small_tree = self.diameter_cm < 4.5 or self.height_m < 7

        species_name = self.species  # species is already lower-case

        # Larch
        if species_name.startswith("larix"):
            # In the C# code, for Larch we always call the Larch volume function.
            # Here we mimic that by using one volume function for larix.
            # We assume that if the diameter is large (>50 cm) we use the Brandel model,
            # otherwise we use a larch-specific model (here represented by carbonnier_1954).
            if self.diameter_cm > 50:
                if self.swedish_site is not None:
                    volume_m3 = BrandelVolume.get_volume(
                        species="pinus sylvestris",  # For larix, uses southern pine parameters.
                        diameter_cm=self.diameter_cm,
                        height_m=self.height_m,
                        latitude=self.swedish_site.latitude,
                        altitude=self.swedish_site.altitude,
                        field_layer=self.swedish_site.field_layer.code,
                        over_bark=self.over_bark,
                    )
                else:
                    volume_m3 = BrandelVolume.get_volume(
                        species="pinus sylvestris",
                        diameter_cm=self.diameter_cm,
                        height_m=self.height_m,
                        latitude=self.latitude,
                        altitude=getattr(self, "altitude", None),
                        field_layer=getattr(self, "field_layer", None),
                        over_bark=self.over_bark,
                    )
            else:
                volume_m3 = carbonnier_1954_volume_larch(self.diameter_cm, self.height_m)

        # Pine (excluding larix sibirica)
        elif species_name == "pinus sylvestris":
            if small_tree:
                volume_m3 = andersson_1954_volume_small_trees_pine(
                    self.diameter_cm,
                    self.height_m,
                )
            else:
                if self.swedish_site is not None:
                    volume_m3 = BrandelVolume.get_volume(
                        species="pinus sylvestris",
                        diameter_cm=self.diameter_cm,
                        height_m=self.height_m,
                        latitude=self.swedish_site.latitude,
                        altitude=self.swedish_site.altitude,
                        field_layer=self.swedish_site.field_layer.code,
                        over_bark=self.over_bark,
                    )
                else:
                    volume_m3 = BrandelVolume.get_volume(
                        species="pinus sylvestris",
                        diameter_cm=self.diameter_cm,
                        height_m=self.height_m,
                        latitude=self.latitude,
                        altitude=getattr(self, "altitude", None),
                        field_layer=getattr(self, "field_layer", None),
                        over_bark=self.over_bark,
                    )

        # Spruce
        elif species_name == "picea abies":
            if small_tree:
                volume_m3 = andersson_1954_volume_small_trees_spruce(
                    self.diameter_cm,
                    self.height_m,
                )
            else:
                if self.swedish_site is not None:
                    volume_m3 = BrandelVolume.get_volume(
                        species="picea abies",
                        diameter_cm=self.diameter_cm,
                        height_m=self.height_m,
                        latitude=self.swedish_site.latitude,
                        altitude=self.swedish_site.altitude,
                        field_layer=self.swedish_site.field_layer.code,
                        over_bark=self.over_bark,
                    )
                else:
                    volume_m3 = BrandelVolume.get_volume(
                        species="picea abies",
                        diameter_cm=self.diameter_cm,
                        height_m=self.height_m,
                        latitude=self.latitude,
                        altitude=getattr(self, "altitude", None),
                        field_layer=getattr(self, "field_layer", None),
                        over_bark=self.over_bark,
                    )

        # Birch
        elif species_name.startswith("betula"):
            if small_tree:
                # Use different Andersson_1954 functions based on tree height.
                if self.height_m > 4:
                    volume_m3 = andersson_1954_volume_small_trees_birch_height_above_4_m(
                        self.diameter_cm, self.height_m
                    )
                else:
                    volume_m3 = andersson_1954_volume_small_trees_birch_under_diameter_5_cm(
                        self.diameter_cm, self.height_m
                    )
            else:
                if self.swedish_site is not None:
                    volume_m3 = BrandelVolume.get_volume(
                        species="betula",
                        diameter_cm=self.diameter_cm,
                        height_m=self.height_m,
                        latitude=self.swedish_site.latitude,
                        altitude=self.swedish_site.altitude,
                        field_layer=self.swedish_site.field_layer.code,
                        over_bark=self.over_bark,
                    )
                else:
                    volume_m3 = BrandelVolume.get_volume(
                        species="betula",
                        diameter_cm=self.diameter_cm,
                        height_m=self.height_m,
                        latitude=self.latitude,
                        altitude=getattr(self, "altitude", None),
                        field_layer=getattr(self, "field_layer", None),
                        over_bark=self.over_bark,
                    )

        # Aspen (and related species)
        elif species_name in ["fraxinus excelsior", "populus tremula"] or species_name.startswith(
            "alnus"
        ):
            volume_m3 = eriksson_1973_volume_aspen_sweden(self.diameter_cm, self.height_m)

        # Lodgepole pine (Contorta)
        elif species_name == "pinus contorta":
            if small_tree:
                volume_m3 = andersson_1954_volume_small_trees_pine(
                    self.diameter_cm,
                    self.height_m,
                )
            else:
                volume_m3 = eriksson_1973_volume_lodgepole_pine_sweden(
                    self.diameter_cm,
                    self.height_m,
                )

        # Beech
        elif species_name in ["fagus sylvatica", "carpinus betulus"]:
            volume_m3 = matern_1975_volume_sweden_beech(self.diameter_cm, self.height_m)

        # Oak
        elif species_name.startswith("quercus"):
            volume_m3 = matern_1975_volume_sweden_oak(self.diameter_cm, self.height_m)

        # Default fallback: use Birch model
        else:
            if small_tree:
                if self.height_m > 4:
                    volume_m3 = andersson_1954_volume_small_trees_birch_height_above_4_m(
                        self.diameter_cm, self.height_m
                    )
                else:
                    volume_m3 = andersson_1954_volume_small_trees_birch_under_diameter_5_cm(
                        self.diameter_cm, self.height_m
                    )
            else:
                if self.swedish_site is not None:
                    volume_m3 = BrandelVolume.get_volume(
                        species="betula",
                        diameter_cm=self.diameter_cm,
                        height_m=self.height_m,
                        latitude=self.swedish_site.latitude,
                        altitude=self.swedish_site.altitude,
                        field_layer=self.swedish_site.field_layer.code,
                        over_bark=self.over_bark,
                    )
                else:
                    volume_m3 = BrandelVolume.get_volume(
                        species="betula",
                        diameter_cm=self.diameter_cm,
                        height_m=self.height_m,
                        latitude=self.latitude,
                        altitude=getattr(self, "altitude", None),
                        field_layer=getattr(self, "field_layer", None),
                        over_bark=self.over_bark,
                    )
        return volume_m3
