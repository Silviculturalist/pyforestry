from typing import Optional

class Timber:
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
    ):
        if diameter_cm < 5:
            raise ValueError("Diameter must be larger than 5 cm.")
        self.species = species
        self.diameter_cm = diameter_cm
        self.height_m = height_m
        self.double_bark_mm = double_bark_mm
        self.crown_base_height_m = crown_base_height_m
        self.over_bark = over_bark
        self.region = region.lower()

        if latitude is None:
            if self.region == 'northern':
                self.latitude=64
            if self.region == 'southern':
                self.latitude=58
        else: 
            self.latitude = latitude

    def validate(self):
        if self.region not in ["northern", "southern"]:
            raise ValueError("Region must be 'northern' or 'southern'.")
        if self.species not in [
            "pinus sylvestris",
            "picea abies",
            "betula",
            "betula pendula",
            "betula pubescens",
        ]:
            raise ValueError(
                "Species must be one of: pinus sylvestris, picea abies, betula, betula pendula, betula pubescens."
            )