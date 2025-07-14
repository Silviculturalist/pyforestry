from enum import IntEnum
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple, Union, Iterable, Sequence
from pyforestry.base.helpers.tree_species import parse_tree_species, TreeName

@dataclass
class DiameterRange:
    Min: float
    Max: float

@dataclass
class LengthRange:
    Min: float
    Max: float


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
    Now accepts a dictionary of corrections in the form:
      { diameter: { length: correction_percentage, ... }, ... }
    """
    def __init__(self, corrections: Optional[Dict[int, Dict[int, int]]] = None):
        self.corrections = corrections or {}
    
    def get_length_correction(self, diameter: int, log_part: Optional[int], length: int) -> int:
        """
        Returns the correction percentage for a given diameter and log length.
        Looks up the corrections dictionary for the closest available length (floored).
        Returns 0 if no correction applies.
        """
        if diameter not in self.corrections:
            return 0
        length_dict = self.corrections[diameter]
        # Get all lengths that are <= provided length
        available_lengths = sorted(l for l in length_dict.keys() if l <= length)
        if available_lengths:
            nearest_length = max(available_lengths)
            return length_dict[nearest_length]
        return 0  # no suitable correction

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
        # Default length corrections (can be replaced when data is loaded)
        self.length_corrections = LengthCorrections()
        # Placeholders for additional data:
        self.quality_outcome: Dict[str, List[float]] = {}
        self.downgrade_proportions: Dict[str, float] = {}

        # Example maximum heights for different quality logs
        self.max_height_quality1 = 99.9  # in meters 
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
        class LogWeights:
            pulpwoodPercentage = 0.0
            fuelWoodPercentage = 0.0
            logCullPercentage  = 0.0
        return LogWeights()
    
    def price_for_log_part(self, log_part: 'TimberPricelist.LogParts', diameter_cm: float) -> float:
        """
        Get the price for a given log part (Butt, Middle, Top) at a given diameter (cm).
        Rounds or floors the diameter to the nearest available diameter class.
        """
        diameter_class = self.get_nearest_diameter_class(diameter_cm)
        price_struct = self[diameter_class]
        return price_struct.price_for_log_part(log_part)

    def get_nearest_diameter_class(self, diameter_cm: float) -> int:
        """
        Returns the closest available diameter class (floored down to available class).
        If the requested diameter is smaller than min, returns min. If larger than max, returns max.
        """
        available_classes = sorted(self._price_by_diameter.keys())
        suitable_classes = [d for d in available_classes if d <= diameter_cm]
        
        if suitable_classes:
            return max(suitable_classes)
        else:
            return 0  # smallest available class

class PulpPricelist:
    """Placeholder for pulp prices per species."""
    def __init__(self):
        self._prices = {}

    def getPulpwoodPrice(self, species: Union[str, TreeName]) -> int:
        """
        Try to find the price for a species by first looking for a full name match.
        If none is found, look for a match on just the genus.
        Returns a default price if no match is found.
        """
        # Ensure we have a TreeName object
        if isinstance(species, str):
            try:
                species_obj = parse_tree_species(species)
            except ValueError:
                # Could not parse full species; treat the string as a genus.
                species_obj = None
                normalized = species.strip().lower()
        else:
            species_obj = species

        if species_obj:
            full_name_key = species_obj.full_name.lower()
            if full_name_key in self._prices:
                return self._prices[full_name_key]
            else:
                # Fallback: look up by genus
                genus_key = species_obj.genus.name.lower()
                if genus_key in self._prices:
                    return self._prices[genus_key]
        else:
            # When species_obj is None, try matching the input as a genus.
            NotImplementedError(
                'TODO: Implement species via genus'
            )
            #if normalized in self._prices:
            #    return self._prices[normalized]

        # Default price if no match is found.
        return 200


class Pricelist:
    """Holds the combined pulpwood, timber, etc. prices and constraints."""
    def __init__(self):
        self.Timber: Dict[str, TimberPricelist] = {}
        self.PulpLogDiameter = DiameterRange(5, 70)
        self.Pulp = PulpPricelist()
        self.TopDiameter: int = 5
        self.LogCullPrice: float = 50 
        self.FuelWoodPrice: float = 25
        self.HighStumpHeight: float = 0.0
        self.PulpLogLength = LengthRange(30, 50)
        self.TimberLogLength = LengthRange(31, 55)

    def load_from_dict(self, price_data: dict):
        """Loads and configures the entire pricelist from a dictionary."""
        try:
            # Load common parameters
            common = price_data["Common"]
            self.PulpLogDiameter = DiameterRange(*common["PulpLogDiameterRange"])
            self.TopDiameter = common["TopDiameter"]
            self.LogCullPrice = common["HarvestResiduePrice"]
            self.FuelWoodPrice = common["FuelwoodLogPrice"]
            self.HighStumpHeight = common["HighStumpHeight"]
            self.PulpLogLength = LengthRange(*common["PulpwoodLengthRange"])
            self.TimberLogLength = LengthRange(*common["SawlogLengthRange"])
            self.Pulp._prices = common["PulpwoodPrices"]

            # Load timber data for all species in the pricelist
            for species_key in [key for key in price_data if key != 'Common']:
                self._load_species_specific_data(price_data, species_key)

        except KeyError as e:
            raise KeyError(f"Missing key in price data: {e}") from e
        except Exception as e:
            raise ValueError(f"Error loading price data: {e}") from e

    def _load_species_specific_data(self, price_data: dict, species_key: str):
        """Helper to load data for a single species."""
        timber_data = price_data[species_key]
        diameters = list(timber_data["DiameterPrices"].keys())
        
        timber_pricelist = TimberPricelist(
            min_diameter=min(diameters),
            max_diameter=max(diameters),
            volume_type=timber_data["VolumeType"]
        )

        for diameter, prices in timber_data["DiameterPrices"].items():
            price_struct = TimberPriceForDiameter(*prices)
            timber_pricelist.set_price_for_diameter(diameter, price_struct)

        if "LengthCorrectionsPercent" in timber_data:
            timber_pricelist.length_corrections = LengthCorrections(
                timber_data["LengthCorrectionsPercent"]
            )
        if "QualityOutcome" in timber_data:
            timber_pricelist.quality_outcome = timber_data["QualityOutcome"]
        if "DowngradeProportions" in timber_data:
            timber_pricelist.downgrade_proportions = timber_data["DowngradeProportions"]

        timber_pricelist.max_height_quality1 = timber_data["MaxHeight"]["Butt"]
        timber_pricelist.max_height_quality2 = timber_data["MaxHeight"]["Middle"]
        timber_pricelist.max_height_quality3 = timber_data["MaxHeight"]["Top"]

        self.Timber[species_key] = timber_pricelist


def create_pricelist_from_data(
    price_data: dict,
    species_to_load: Optional[Union[str, Sequence[str]]] = None
) -> Pricelist:
    """
    Build a `Pricelist` from a dictionary.

    Parameters
    ----------
    price_data : dict
        The complete price dictionary (must contain the 'Common' block).
    species_to_load : str | Sequence[str] | None, default None
        * **None**  - load *all* species that have timber price tables.
        * **str**   - load just that species.
        * **iterable** - load every species in the iterable; it is *not*
          an error if some of them have only pulp prices.

    Returns
    -------
    Pricelist
        A fully populated `Pricelist` instance.
    """
    pricelist = Pricelist()

    # ---- common block ---------------------------------------------------
    try:
        common = price_data["Common"]
    except KeyError as exc:
        raise ValueError("Price data is missing the mandatory 'Common' block") from exc

    pricelist.PulpLogDiameter = DiameterRange(*common["PulpLogDiameterRange"])
    pricelist.TopDiameter     = common["TopDiameter"]
    pricelist.LogCullPrice    = common["HarvestResiduePrice"]
    pricelist.FuelWoodPrice   = common["FuelwoodLogPrice"]
    pricelist.HighStumpHeight = common["HighStumpHeight"]
    pricelist.PulpLogLength   = LengthRange(*common["PulpwoodLengthRange"])
    pricelist.TimberLogLength = LengthRange(*common["SawlogLengthRange"])
    pricelist.Pulp._prices    = common["PulpwoodPrices"]

    # ---- normalise parameter -------------------------------------------
    if species_to_load is None:
        species_keys: List[str] = [
            k for k in price_data.keys() if k != "Common"
        ]
    elif isinstance(species_to_load, str):
        species_keys = [species_to_load]
    elif isinstance(species_to_load, Iterable):
        species_keys = list(species_to_load)
    else:
        raise TypeError(
            "'species_to_load' must be None, a string, or an iterable of strings"
        )

    # ---- load timber price tables --------------------------------------
    for sp in species_keys:
        if sp in price_data:
            pricelist._load_species_specific_data(price_data, sp)
        else:
            # It is OK if the species is missing in timber tables but present
            # in the pulp‑price section – we already copied those above.
            if sp not in common["PulpwoodPrices"]:
                raise ValueError(
                    f"Species '{sp}' not found in timber prices **or** pulp prices."
                )

    return pricelist