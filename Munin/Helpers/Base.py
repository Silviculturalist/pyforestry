#These classes are not mandatory, but provide optional type-safety to avoid mixing e.g.
#Site-index at DBH-age = 100 and Site-index at total age = 100.
from Munin.Site.SiteBase import SiteBase
from Munin.Helpers.TreeSpecies import *
from dataclasses import dataclass
from enum import Enum
import math
import statistics
from typing import List, Any, Dict, Optional, Union

#E.g. d= Diameter_cm(20,over_bark=True)
@dataclass(frozen=True)
class Diameter_cm:
    value: float
    over_bark: bool
    measurement_height_m: float = 1.3  # Default: diameter measured at breast height
    
    def __post_init__(self):
        if self.value < 0:
            raise ValueError("Diameter must be non-negative.")

@dataclass(frozen=True)
class AgeMeasurement:
    value: float
    code: int

#E.g. a = Age.DBH(45)
class Age(Enum):
    TOTAL = 1
    DBH = 2

    def __call__(self, value: float) -> AgeMeasurement:
        if value < 0:
            raise ValueError("Age must be non-negative.")
        return AgeMeasurement(value=value, code=self.value)

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
