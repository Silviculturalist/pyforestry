# These classes are development-mandatory. 
# They are not user-mandatory!
# Anticipate users passing other structures and handle these appropriately.
from pyproj import CRS
from shapely import Polygon
import geopandas as gpd
from Munin.Site.SiteBase import SiteBase
from Munin.Helpers.TreeSpecies import *
from dataclasses import dataclass
from enum import Enum
import math
import numpy as np
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
    CRS: Optional[CRS]

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
    weight: Optional[float] = 1 # Number of trees it represents.

    def __post_init__(self):
        # Process the position input and assign a Position instance (or None)
        if type(self.species)==str:
            object.__setattr__(self,'species', parse_tree_species(self.species))





class Plot:
    '''
    Contains information from a circular plot on a stand
    '''
    def __init__(self,id:int|str, position: Optional[Position] = None, radius_m: Optional[float] = None, 
                 area_m2: Optional[float] = None, site: Optional[SiteBase] = None, 
                 trees: Optional[List[RepresentationTree]] = None):
        
        if id is None:
            raise ValueError('Plot must be given an ID (integer or string)!')
        else:
            self.id = id
        
        if radius_m is None and area_m2 is None:
            raise ValueError('Plot class cannot be instanced without either a valid radius_m or area_m2!')
        
        if radius_m:
            self.radius_m = radius_m
        if radius_m and not area_m2:
            self.area_m2 = math.pi * self.radius_m ** 2
        if area_m2:
            self.area_m2 = area_m2
        if area_m2 and not radius_m:
            self.radius_m = math.sqrt(self.area_m2 / math.pi)
        if radius_m and area_m2 and abs(math.pi * radius_m ** 2 - area_m2) > 1e-6:
            raise ValueError(f'Plot radius of {self.radius_m} m does not have an area of {self.area_m2} m²!')

        self.position = position
        self.site = site
        self.trees = trees if trees is not None else []
    
    @property
    def area_ha(self):
        return self.area_m2 / 10000
    
@dataclass
class TopHeightDefinition:
    nominal_n:100
    nominal_area_ha:1
    

class Stand:
    def __init__(self, 
                 site: Optional['SiteBase'] = None,
                 area_ha: Optional[float] = None,
                 plots: Optional[List['Plot']] = None,
                 polygon: Optional[Polygon] = None,
                 crs: str = "EPSG:4326",# default assumes lat/lon
                 top_height_definition: Optional[TopHeightDefinition] = TopHeightDefinition()
                 ):  
        self.site = site
        self.area_ha = area_ha
        self.plots = plots
        self.polygon = polygon
        self.top_height_definition = top_height_definition
        self.attrs = {}

        if polygon:
            gdf = gpd.GeoDataFrame({'geometry': [self.polygon]}, crs=crs)

            # Check if the polygon CRS is geographic (degrees)
            if gdf.crs.is_geographic:
                # Reproject to UTM
                utm_crs = gdf.estimate_utm_crs()
                gdf = gdf.to_crs(utm_crs)
            
            # Otherwise, assume projected CRS is already suitable (area in meters²)
            self.projected_polygon = gdf.geometry.iloc[0]
            
            # Calculate area in hectares
            self.area_ha = self.projected_polygon.area / 10_000
        
        if plots:
            self.attrs['QMD']

    def get_dominant_height(self):
        if self.plots is None:
            self.dominant_height = (None, None)
            return 
        else:
            # Step 1. Get plot size.
            mode_area = statistics.mode([x.area_m2 for x in self.plots])
            # Step 1a. Filter for plots with an area equal to the area mode.
            subplots = [x for x in self.plots if math.isclose(x.area_m2,mode_area)]
            
            # Step 2. Get the number of top_m heights measured on the thickest diameters per plot available.
            mplot = []
            for plot in self.plots:
                if any(np.isnan([x.diameter_cm for x in plot.trees])):
                    raise ValueError(f'One or more trees have missing diameters on plot with id: {plot.id}!')
                sorted_trees = sorted(plot.trees,
                                      key=lambda t: t.diameter_cm if t.diameter_cm is not None else -np.inf,
                                      reverse=True)
                
                if sorted_trees[0].height_m is None:
                    warnings.warn(f'Tree with the largest diameter on plot {plot.id} does not have an associated height. Skipping plot.')
                    continue
                
                isOK = True
                m=0

                while isOK and m<10:
                    for tree in sorted_trees:
                        if tree.height_m:
                            m+=1
                        else:
                            isOK=False
                
                mplot.append(m)

            # Step 3. Calculate estimate


            # Step 4. Calculate eventual bias incurred by TopHeightDefinition and chosen plot size and top_m measured heights from thickest diameters. 

            # Step 5. Correct estimate

            # Step 6. Calculate precision

            self.dominant_height = (estimate,precision)
            return


    @staticmethod
    def calculate_top_height_bias(r, m, n_trees=1_000, n_simulations=10_000, 
                       nominal_top_n=100,nominal_area =10_000, sigma=3.0):
        """
        Calculate the bias of the estimator h_hat for top height in a forest stand.
        Based on lecture by Bertil Matérn, e.g. Matérn, B. 1984. Four lectures on forest biometry. Section of Forest Biometry, Swedish University of Agricultural Sciences. Report 23. ISBN 91-576-2001-6. p. 139 pp. 100-103. 

        Parameters:
        - r: Radius of the circular plot (meters)
        - m: Number of largest trees to average in the plot
        - nominal_area: Nominal area (m², default 10000 = 1 ha)
        - n_trees: Total number of trees in the stand (default 1000)
        - n_simulations: Number of simulation runs (default 10000)
        - nominal_top_n: Number of top trees defining H_bar per nominal_area (default 100)
        - sigma: Percent error in height measurements (default 3.0)

        Returns:
        - bias: Average h_hat - H_bar (meters)
        - bias_percentage: Bias as a percentage of H_bar
        """
        h_hat_list = []
        H_bar_list = []

        for _ in range(n_simulations):
            # Generate tree positions uniformly in the stand
            x_pos = np.random.uniform(0, np.sqrt(nominal_area), n_trees)
            y_pos = np.random.uniform(0, np.sqrt(nominal_area), n_trees)

            # Generate diameters (exponential distribution, mean 20 cm)
            diameters = np.random.exponential(scale=20.0, size=n_trees)

            # Compute true heights using the height-diameter function
            heights_true = 1.3 + (diameters**2) / ((1.1138 + 0.2075 * diameters)**2)

            # Add 3% measurement error to heights
            noise = np.random.normal(0, (sigma/100) * heights_true, n_trees)
            heights_measured = heights_true + noise

            # Compute H_bar: mean height of top nominal_top_n trees by diameter
            top_indices = np.argsort(diameters)[-nominal_top_n:][::-1]
            H_bar = np.mean(heights_true[top_indices])  # True heights for true parameter
            H_bar_list.append(H_bar)

            # Sample a circular plot with radius r
            center_x = np.random.uniform(r, np.sqrt(nominal_area) - r)
            center_y = np.random.uniform(r, np.sqrt(nominal_area) - r)
            distances = np.sqrt((x_pos - center_x)**2 + (y_pos - center_y)**2)
            in_plot = distances <= r

            # Compute h_hat if enough trees are in the plot
            if np.sum(in_plot) >= m:
                plot_diameters = diameters[in_plot]
                plot_heights = heights_measured[in_plot]
                plot_top_indices = np.argsort(plot_diameters)[-m:][::-1]
                h_hat = np.mean(plot_heights[plot_top_indices])
            else:
                h_hat = np.nan  # Insufficient trees
            h_hat_list.append(h_hat)

        # Calculate averages and bias
        h_hat_avg = np.nanmean(h_hat_list)
        H_bar_avg = np.mean(H_bar_list)
        bias = h_hat_avg - H_bar_avg
        bias_percentage = (bias / H_bar_avg) * 100

        return bias, bias_percentage


            
        
    

    




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
