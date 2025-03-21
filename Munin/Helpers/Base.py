# These classes are development-mandatory. 
# They are not user-mandatory!
# Anticipate users passing other structures and handle these appropriately.
from Munin.Site.SiteBase import SiteBase
from Munin.Helpers.TreeSpecies import *
from dataclasses import dataclass
from enum import Enum
import math
import statistics
from typing import List, Any, Dict, Optional, Union

#E.g. d= Diameter_cm(20,over_bark=True)
class Diameter_cm(float):
    def __new__(cls, value: float, over_bark: bool, measurement_height_m: float = 1.3):
        if value < 0:
            raise ValueError("Diameter must be non-negative.")
        # Create the float instance
        obj = super().__new__(cls, value)
        # Attach extra attributes
        obj.over_bark = over_bark
        obj.measurement_height_m = measurement_height_m
        return obj

    def __repr__(self):
        return (f"Diameter_cm({float(self)}, over_bark={self.over_bark}, "
                f"measurement_height_m={self.measurement_height_m})")


class AgeMeasurement(float):
    def __new__(cls, value: float, code: int):
        if value < 0:
            raise ValueError("Age must be non-negative.")
        # Create the float instance
        obj = super().__new__(cls, value)
        # Attach the age code
        obj.code = code
        return obj

    def __repr__(self):
        return f"AgeMeasurement({float(self)}, code={self.code})"

class Age(Enum):
    TOTAL = 1
    DBH = 2

    def __call__(self, value: float) -> AgeMeasurement:
        # Use our new AgeMeasurement which behaves like a float.
        return AgeMeasurement(value, self.value)



#SiteIndexValue is a property that's held by the results from site index functions.
#This avoids unintentional mix-ups between species, reference ages and functions.
class SiteIndexValue(float):
    def __new__(cls, value: float, reference_age: float, species: TreeName, fn: callable):
        # Create the float instance
        obj = super().__new__(cls, value)
        # Attach extra attributes
        obj.reference_age = reference_age
        obj.species = species
        obj.fn = fn
        return obj

    def __repr__(self):
        return (f"SiteIndexValue({float(self)}, reference_age={self.reference_age}, "
                f"species={self.species}, fn={self.fn.__name__ if hasattr(self.fn, '__name__') else self.fn})")



#VolumeValue will avoid mix-ups between different volume units and types.
# Here, unit is e.g. m3, m3sk, m3_to, m3_fub5, (different measurement types)
# Whereas unit is dm3, m3..

class Volume(float):
    UNIT_CONVERSION = {
        'mm3': 1e-9, 'cm3': 1e-6, 'dm3': 1e-3, 'm3': 1,
        'dam3': 1e3, 'hm3': 1e6, 'km3': 1e9, 'Mm3': 1e18,
        'Gm3': 1e27, 'Tm3': 1e36, 'Pm3': 1e45
    }
    ORDERED_UNITS = ['mm3', 'cm3', 'dm3', 'm3', 'dam3', 'hm3', 'km3', 'Mm3', 'Gm3', 'Tm3', 'Pm3']
    TYPE_REGIONS = {
        'm3sk': ['Sweden', 'Finland', 'Norway'],
        'm3to': ['Sweden'],
        'm3fub': ['Sweden']
    }

    def __new__(cls, value, region='Sweden', species='unknown', unit='m3', type='m3sk'):
        obj = super().__new__(cls, cls.UNIT_CONVERSION[unit] * value)
        obj.region = region
        obj.species = species
        obj.type = type
        obj.unit = unit
        obj._validate_region()
        return obj

    def __repr__(self):
        value_m3 = float(self)
        best_unit = None
        best_value = None
        # First pass: strict 1-10 range
        for unit in reversed(self.ORDERED_UNITS):
            converted_value = value_m3 / self.UNIT_CONVERSION[unit]
            if 1 <= abs(converted_value) < 10:
                return f"Volume({converted_value:.4f} {unit}, region='{self.region}', species='{self.species}', type='{self.type}')"
            # Track the unit with the smallest value ≥ 1
            if abs(converted_value) >= 1 and (best_value is None or abs(converted_value) < abs(best_value)):
                best_unit = unit
                best_value = converted_value
        # If no 1-10 match, use the best unit found (smallest value ≥ 1)
        if best_unit is not None:
            return f"Volume({best_value:.4f} {best_unit}, region='{self.region}', species='{self.species}', type='{self.type}')"
        # Extreme cases: smaller than 1 mm3 or zero
        extreme_unit = 'mm3' if value_m3 < 1 else 'Pm3'
        extreme_value = value_m3 / self.UNIT_CONVERSION[extreme_unit]
        return f"Volume({extreme_value:.4f} {extreme_unit}, region='{self.region}', species='{self.species}', type='{self.type}')"

    def to(self, unit):
        return float(self) / self.UNIT_CONVERSION[unit]

    def m3(self):
        return self.to('m3')

    def __eq__(self, other):
        if not isinstance(other, Volume):
            return NotImplemented
        return (
            abs(float(self) - float(other)) < 1e-9 and
            self.type == other.type and
            self.region in self.TYPE_REGIONS[self.type] and
            other.region in self.TYPE_REGIONS[other.type]
        )

    def __add__(self, other):
        self._validate_compatibility(other)
        return Volume(float(self) + float(other), self.region, self.species, 'm3', self.type)

    def __sub__(self, other):
        self._validate_compatibility(other)
        return Volume(float(self) - float(other), self.region, self.species, 'm3', self.type)

    def __mul__(self, scalar):
        if isinstance(scalar, Volume):
            raise TypeError("Multiplication between Volume instances is not allowed.")
        return Volume(float(self) * scalar, self.region, self.species, 'm3', self.type)

    def __truediv__(self, scalar):
        if isinstance(scalar, Volume):
            raise TypeError("Division between Volume instances is not allowed.")
        return Volume(float(self) / scalar, self.region, self.species, 'm3', self.type)

    def _validate_compatibility(self, other):
        if not isinstance(other, Volume):
            raise TypeError("Can only operate between Volume instances.")
        if self.type != other.type:
            raise ValueError(f"Incompatible types: {self.type} vs {other.type}")
        if self.region not in self.TYPE_REGIONS[self.type] or other.region not in self.TYPE_REGIONS[self.type]:
            raise ValueError(f"Regions '{self.region}' and '{other.region}' must both be valid for type '{self.type}'")

    def _validate_region(self):
        base_type = self.type
        allowed_regions = self.TYPE_REGIONS.get(base_type, [])
        if self.region not in allowed_regions:
            raise ValueError(f"Region '{self.region}' not allowed for type '{self.type}'. Allowed regions: {allowed_regions}")

    class Region:
        def __init__(self, region):
            self.region = region

        def __getattr__(self, type_unit):
            def creator(value, species='unknown'):
                for unit in Volume.UNIT_CONVERSION:
                    if type_unit.startswith(unit):
                        type_suffix = type_unit[len(unit):]
                        if type_suffix in Volume.TYPE_REGIONS:
                            return Volume(value, region=self.region, species=species, unit=unit, type=type_suffix)
                        if type_suffix == 'sk':
                            return Volume(value, region=self.region, species=species, unit=unit, type='m3sk')
                if type_unit in Volume.TYPE_REGIONS:
                    return Volume(value, region=self.region, species=species, unit='m3', type=type_unit)
                if type_unit == 'sk':
                    return Volume(value, region=self.region, species=species, unit='m3', type='m3sk')
                raise ValueError(f"Invalid type/unit combination: '{type_unit}'")
            return creator

    Sweden = Region('Sweden')
    Norway = Region('Norway')
    Finland = Region('Finland')


@dataclass(frozen=True)
class Position:
    X: float
    Y: float
    Z: Optional[float] = 0

#Internal helper to set position in tree creation.
def _set_position(position: Union[Position, tuple[float, float], tuple[float, float, float]] = None) -> None:
    if position is None:
        print("No position provided")
    elif isinstance(position, Position):
        pos = position
    elif isinstance(position, tuple):
        if len(position) == 2:
            pos = Position(position[0], position[1])
        elif len(position) == 3:
            pos = Position(position[0], position[1], position[2])
        else:
            raise ValueError("Position tuple must be of length 2 or 3")
    else:
        raise TypeError("position must be a Position or a tuple of floats")


class Tree:
    def __init__(self):
        pass

@dataclass
class SingleTree:
    '''
    Spatially explicit tree.
    '''
    position: Optional[Union[Position, tuple[float, float], tuple[float, float, float]]] = None
    species: Optional[Union[TreeSpecies, str]] = None
    age: Optional[Union[Age, float]] = None
    diameter_cm: Optional[Union[Diameter_cm, float]] = None
    height_m: Optional[float] = None

    def __post_init__(self):
        # Process the position input and assign a Position instance (or None)
        object.__setattr__(self, 'position', _set_position(self.position))

        if type(self.species)==str:
            object.__setattr__(self,'species', parse_tree_species(self.species))


@dataclass
class RepresentationTree(Tree):
    '''
    Spatially Implicit single tree that will belong to a Plot.
    '''
    position: Optional[Union[Position, tuple[float, float], tuple[float, float, float]]] = None
    species: Optional[Union[TreeSpecies, str]] = None
    age: Optional[Union[Age, float]] = None
    diameter_cm: Optional[Union[Diameter_cm, float]] = None
    height_m: Optional[float] = None

    def __post_init__(self):
        # Process the position input and assign a Position instance (or None)
        if type(self.species)==str:
            object.__setattr__(self,'species', parse_tree_species(self.species))





class Plot:
    '''
    Contains information from a plot on a stand
    '''
    def __init__(self,radius: Optional[float],area_m2: Optional[float]):
        pass
    # TODO


class Stand:
    def __init__(self, site: Optional[SiteBase],area_ha: Optional[float],plots: Optional[List[Plot]]):
        pass
    # TODO
    




class Horvitz_Tompson_estimator:
    def __init__(self, sample_list: List[Any], sample_category: Optional[List[str]] = None):
        """
        Initialize the estimator.
        
        :param sample_list: Can be either a list of numeric values (one per sample) 
                            or a list of Stand objects.
        :param sample_category: If sample_list is numeric, provide a corresponding list of category labels.
        """
    def __init__(self, sample_list: List[Any], sample_category: Optional[List[str]] = None):
        if sample_list:
            # Check that all items are of the same type as the first item.
            first_type = type(sample_list[0])
            if not all(isinstance(item, first_type) for item in sample_list):
                raise TypeError("All measurement samples must be of the same type.")
        self.sample_list = sample_list
        self.sample_category = sample_category

    def estimate_from_samples(self) -> Dict[str, Dict[str, float]]:
        """
        For a simple list of values (with corresponding categories) this method groups the data 
        and returns the total, mean, and variance for each category.
        """
        if self.sample_category is None or len(self.sample_list) != len(self.sample_category):
            raise ValueError("sample_category must be provided and have the same length as sample_list")
        
        data_by_category: Dict[str, List[float]] = {}
        for value, cat in zip(self.sample_list, self.sample_category):
            data_by_category.setdefault(cat, []).append(value)
            
        estimates = {}
        for cat, values in data_by_category.items():
            total = sum(values)
            mean_val = statistics.mean(values) if values else 0
            var_val = statistics.pvariance(values) if len(values) > 1 else 0
            estimates[cat] = {"total": total, "mean": mean_val, "variance": var_val}
            
        return estimates

    def estimate_from_stands(self) -> Dict[str, Dict[str, Dict[str, float]]]:
        """
        For a list of Stand objects this method iterates through each plot and tree.
        For each plot and for each species, it computes:
          - Stems per hectare (number of trees divided by plot area, where plot.area_ha is used if available, otherwise 1)
          - Basal area per hectare (sum of π*(diameter_cm/100)**2 divided by plot area)
          - Mean height (average tree height in the plot for that species)
        
        It then aggregates these per-plot values over all plots (grouped by species)
        and returns for each species a dictionary with keys for the metric 
        (e.g. "stems_per_ha", "basal_area_per_ha", "mean_height") containing a further dictionary
        with the total (sum), mean, and variance.
        """
        species_data: Dict[str, Dict[str, List[float]]] = {}
        
        # Iterate over stands
        for stand in self.sample_list:
            # Each stand should have a 'plots' attribute.
            for plot in getattr(stand, "plots", []):
                # Use plot.area_ha if available, else assume 1 hectare
                area = getattr(plot, "area_ha", 1)
                
                # Group trees by species within the plot
                plot_species: Dict[str, List[Any]] = {}
                for tree in getattr(plot, "trees", []):
                    sp = getattr(tree, "species", None)
                    if sp is None:
                        continue
                    plot_species.setdefault(sp, []).append(tree)
                    
                # For each species in this plot, compute the plot-level estimates.
                for sp, trees in plot_species.items():
                    n_trees = len(trees)
                    stems_per_ha = n_trees / area
                    basal_area = sum(math.pi * ((getattr(tree, "diameter_cm", 0) / 100) ** 2) for tree in trees)
                    basal_area_per_ha = basal_area / area
                    heights = [getattr(tree, "height_m", 0) for tree in trees if getattr(tree, "height_m", None) is not None]
                    mean_height = statistics.mean(heights) if heights else 0

                    # Initialize storage for this species if needed.
                    if sp not in species_data:
                        species_data[sp] = {
                            "stems_per_ha": [],
                            "basal_area_per_ha": [],
                            "mean_height": []
                        }
                    species_data[sp]["stems_per_ha"].append(stems_per_ha)
                    species_data[sp]["basal_area_per_ha"].append(basal_area_per_ha)
                    species_data[sp]["mean_height"].append(mean_height)
                    
        # Now aggregate across plots for each species.
        estimates = {}
        for sp, metrics in species_data.items():
            estimates[sp] = {}
            for metric, values in metrics.items():
                total_val = sum(values)
                mean_val = statistics.mean(values) if values else 0
                var_val = statistics.pvariance(values) if len(values) > 1 else 0
                estimates[sp][metric] = {"total": total_val, "mean": mean_val, "variance": var_val}
                
        return estimates

    def estimate(self) -> Dict:
        """
        Determines the type of sample_list provided. If the first element has a 'plots' attribute,
        it assumes a list of Stand objects is given and calls estimate_from_stands().
        Otherwise, it calls estimate_from_samples().
        """
        if self.sample_list and hasattr(self.sample_list[0], "plots"):
            return self.estimate_from_stands()
        else:
            return self.estimate_from_samples()
