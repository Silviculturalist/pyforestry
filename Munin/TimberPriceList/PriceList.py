from enum import IntEnum
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple


class TimberPriceForDiameter:
    """
    Represents the set of prices for a given diameter, for each log part type.
    E.g. an entry might store: PriceButt, PriceMiddle, PriceTop, ...
    """
    def __init__(self, butt_price: float, middle_price: float, top_price: float):
        self.butt_price = butt_price
        self.middle_price = middle_price
        self.top_price = top_price

    def price_for_log_part(self, part_type: int) -> float:
        """Return the price (in e.g. SEK/m3) for the given part type index."""
        if part_type == 0:  # butt
            return self.butt_price
        elif part_type == 1:  # middle
            return self.middle_price
        elif part_type == 2:  # top
            return self.top_price
        else:
            return 0.0

class LengthCorrections:
    """
    Holds logic for how the length modifies price (absolute or percent).
    This is a placeholder. 
    """
    def __init__(self):
        # Could store a dict of (diameter, length) -> some correction
        # For now, just store a default = 0
        self.default_correction = 0

    def get_length_correction(self, diameter: int, log_part: Optional[int], length: int) -> int:
        """Return price add-on or multiplier as needed. Adjust to your real logic."""
        return 0  # placeholder

class TimberPricelist:
    """Stores the entire set of timber prices by diameter class, etc."""
    # Using your code's idea of enumerations: Butt = 0, Middle = 1, Top = 2 ...
    class LogParts(IntEnum):
        Butt = 0
        Middle = 1
        Top = 2

    def __init__(self, 
                 min_diameter: int, 
                 max_diameter: int, 
                 volume_type: str = "m3to"):
        self.min_diameter = min_diameter
        self.max_diameter = max_diameter
        self.volume_type  = volume_type  # e.g. "m3to" or "m3fub"
        self._price_by_diameter: Dict[int, TimberPriceForDiameter] = {}
        self.length_corrections = LengthCorrections()

        # Example maximum heights for different quality logs
        self.max_height_quality1 = 99.9  # in meters (placeholder)
        self.max_height_quality2 = 99.9
        self.max_height_quality3 = 99.9

    def __getitem__(self, diameter: int) -> TimberPriceForDiameter:
        """Return the price structure for a given diameter."""
        return self._price_by_diameter.get(diameter, TimberPriceForDiameter(0, 0, 0))

    def set_price_for_diameter(self, diameter: int, price_struct: TimberPriceForDiameter):
        """Store a price entry for a certain diameter class."""
        self._price_by_diameter[diameter] = price_struct

    @property
    def minDiameter(self):
        return self.min_diameter

    @property
    def maxDiameter(self):
        return self.max_diameter

    def getTimberWeight(self, log_part: 'TimberPricelist.LogParts'):
        """
        If you're applying downgrading or certain proportions for pulp/fuel/cull,
        return an object that has .PulpwoodPercentage, .FuelWoodPercentage, .LogCullPercentage, etc.
        This is a placeholder. 
        """
        class Weights:
            pulpwoodPercentage = 0.0
            fuelWoodPercentage = 0.0
            logCullPercentage  = 0.0
        return Weights()

@dataclass
class DiameterRange:
    Min: int
    Max: int

@dataclass
class LengthRange:
    Min: int
    Max: int

class Pricelist:
    """Holds the combined pulpwood, timber, etc. prices and constraints."""
    def __init__(self):
        self.Timber: Dict[str, TimberPricelist] = {}
        self.PulpLogDiameter = DiameterRange(5, 70)
        self.Pulp = PulpPricelist()
        self.TopDiameter: int = 5
        self.LogCullPrice: float = 50  # SEK/m3?
        self.FuelWoodPrice: float = 25
        self.HighStumpHeight: float = 0.0
        self.PulpLogLength = LengthRange(30, 50)
        self.TimberLogLength = LengthRange(31, 55)

    def getPulpWoodWasteProportion(self, species: str) -> float:
        """Return fraction of pulpwood that is cull, etc. Placeholder."""
        return 0.0

    def getPulpwoodFuelwoodProportion(self, species: str) -> float:
        return 0.0

class PulpPricelist:
    """Placeholder for pulp prices per species."""
    def __init__(self):
        self._prices = {
            "Pine": 300,   # SEK/m3
            "Spruce": 280,
            "Birch": 250
        }

    def getPulpwoodPrice(self, species: str) -> int:
        return self._prices.get(species, 200)  # default
