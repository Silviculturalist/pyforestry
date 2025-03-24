from pyproj import CRS
from shapely import Polygon
import geopandas as gpd
from dataclasses import field
from enum import Enum
import math
import numpy as np
import statistics
from typing import List, Any, Dict, Optional, Union
import warnings

# -------------
# Example stubs
# -------------
from Munin.Site.SiteBase import SiteBase  
from Munin.Helpers.TreeSpecies import (
    TreeName, 
    TreeSpecies,
    parse_tree_species
)

# --------------------------------------------------------------------------------
# Simple typed "float-like" classes that carry extra metadata, following your style
# --------------------------------------------------------------------------------

class Diameter_cm(float):
    """
    Diameter, in centimeters, stored as a float but including additional metadata:
      - over_bark (bool): whether the diameter is measured over bark.
      - measurement_height_m (float): height at which diameter is measured (default: 1.3 m).
    """
    def __new__(cls, value: float, over_bark: bool = True, measurement_height_m: float = 1.3):
        if value < 0:
            raise ValueError("Diameter must be non-negative.")
        if measurement_height_m < 0:
            raise ValueError('measurement_height_m must be >= 0 m!')
        obj = super().__new__(cls, value)
        obj.over_bark = over_bark
        obj.measurement_height_m = measurement_height_m
        return obj

    def __repr__(self):
        return (f"Diameter_cm({float(self)}, over_bark={self.over_bark}, "
                f"measurement_height_m={self.measurement_height_m})")


class AgeMeasurement(float):
    """
    Tree age, stored as a float with an 'age code' attribute indicating what type
    of age is measured (e.g., total age vs. breast-height age).
    """
    def __new__(cls, value: float, code: int):
        if value < 0:
            raise ValueError("Age must be non-negative.")
        obj = super().__new__(cls, value)
        obj.code = code
        return obj

    def __repr__(self):
        return f"AgeMeasurement({float(self)}, code={self.code})"


class Age(Enum):
    """
    An enum to specify which type of age is being used (total or DBH).
    """
    TOTAL = 1
    DBH = 2

    def __call__(self, value: float) -> AgeMeasurement:
        """
        Creates an AgeMeasurement object from this Age type and a numeric value.
        """
        return AgeMeasurement(value, self.value)


class StandBasalArea(float):
    """
    Represents basal area (m²/ha) for one or more species.

    Attributes:
    -----------
    species : TreeName | list[TreeName]
        The species (or list of species) to which this basal area applies.
    precision : float
        Standard deviation, standard error, or other measure of precision (if known).
    over_bark : bool
        True if the basal area is measured over bark.
    direct_estimate : bool
        True if this is a direct field estimate (e.g. from Bitterlich sampling).
    """
    def __new__(cls,
                value: float,
                species: Union[TreeName, List[TreeName]],
                precision: float = 0.0,
                over_bark: bool = True,
                direct_estimate: bool = True):
        if value < 0:
            raise ValueError("StandBasalArea must be non-negative.")
        obj = float.__new__(cls, value)
        obj.species = species
        obj.precision = precision
        obj.over_bark = over_bark
        obj.direct_estimate = direct_estimate
        return obj

    def __repr__(self):
        return (f"StandBasalArea({float(self):.3f} m^2/ha, species={self.species}, "
                f"precision={self.precision}, over_bark={self.over_bark}, "
                f"direct_estimate={self.direct_estimate})")


class StandVolume(float):
    """
    Represents a volume (m³/ha, typically) of standing trees in a stand,
    optionally for a single species or multiple species.

    Attributes:
    -----------
    species : TreeName | list[TreeName]
        The species or list of species for which the volume is estimated.
    precision : float
        Standard deviation or other measure of precision (if known).
    over_bark : bool
        True if the volume is measured over bark.
    fn : callable | None
        An optional reference to the function or model used to derive the volume.
    """
    def __new__(cls,
                value: float,
                species: Union[TreeName, List[TreeName]],
                precision: float = 0.0,
                over_bark: bool = True,
                fn=None):
        if value < 0:
            raise ValueError("StandVolume must be non-negative.")
        obj = float.__new__(cls, value)
        obj.species = species
        obj.precision = precision
        obj.over_bark = over_bark
        obj.fn = fn
        return obj

    def __repr__(self):
        f_str = self.fn.__name__ if callable(self.fn) else self.fn
        return (f"StandVolume({float(self):.3f} m^3/ha, species={self.species}, "
                f"precision={self.precision}, over_bark={self.over_bark}, fn={f_str})")


class Stems(float):
    """
    Represents the number of stems per hectare (stems/ha) for one or more species.

    Attributes:
    -----------
    species : TreeName | list[TreeName]
        The species (or list of species) to which this stems count applies.
    precision : float
        Standard deviation or similar measure of precision (if known).
    """
    def __new__(cls,
                value: float,
                species: Union[TreeName, List[TreeName]],
                precision: float = 0.0):
        if value < 0:
            raise ValueError("Stems must be non-negative.")
        obj = float.__new__(cls, value)
        obj.species = species
        obj.precision = precision
        return obj

    def __repr__(self):
        return (f"Stems({float(self):.1f} stems/ha, species={self.species}, "
                f"precision={self.precision})")


class TopHeightDefinition:
    """
    Defines how the 'top height' (dominant height) is conceptually measured in a stand:
    - nominal_n: number of top trees in 1.0 hectare to average
    - nominal_area_ha: the area basis for that count
    """
    def __init__(self, nominal_n: int = 100, nominal_area_ha: float = 1.0):
        self.nominal_n = nominal_n
        self.nominal_area_ha = nominal_area_ha

    def __repr__(self):
        return f"TopHeightDefinition(nominal_n={self.nominal_n}, area_ha={self.nominal_area_ha})"


class TopHeightMeasurement(float):
    """
    A float-like class that stores the measured top (dominant) height of a stand.

    Attributes:
    -----------
    definition : TopHeightDefinition
        The definition used to identify the top height (e.g. top 100 trees per ha).
    species : TreeName | list[TreeName]
        The species or species mixture that this top height applies to.
    precision : float
        An estimate of precision (e.g. standard error) of the top height.
    est_bias : float
        Any known or estimated bias that might be subtracted (or added) from the measurement.
    """
    def __new__(cls,
                value: float,
                definition: TopHeightDefinition,
                species: Union[TreeName, List[TreeName], None] = None,
                precision: float = 0.0,
                est_bias: float = 0.0):
        if value < 0:
            raise ValueError("TopHeightMeasurement cannot be negative.")
        obj = float.__new__(cls, value)
        obj.definition = definition
        obj.species = species
        obj.precision = precision
        obj.est_bias = est_bias
        return obj

    def __repr__(self):
        return (f"TopHeightMeasurement({float(self):.2f} m, definition={self.definition}, "
                f"species={self.species}, precision={self.precision}, est_bias={self.est_bias})")


# ------------------------------------------------------------------------------
# Bitterlich (Angle count) Sampling
# ------------------------------------------------------------------------------

class BitterlichSampling:
    """
    Holds parameters for angle-count (relascope) sampling,
    along with species-specific tally counts.

    Attributes:
    -----------
    ba_factor : float
        Basal Area Factor (m²/ha) per count.
    value : list[int]
        Parallel list of integer counts, each entry matching a species in 'species'.
    species : list[TreeSpecies]
        Parallel list of species, each matching an entry in 'value'.
    point_id : str | None
        Identifies the sampling point location (e.g., 'P1', 'P2', etc.).
    slope : float
        Slope correction factor or slope angle, if desired (default: 0.0).
    """
    def __init__(self,
                 ba_factor: float,
                 value: Optional[List[int]] = None,
                 species: Optional[List[TreeSpecies]] = None,
                 point_id: Optional[str] = None,
                 slope: float = 0.0):
        self.ba_factor = ba_factor
        self.value = value if value is not None else []
        self.species = species if species is not None else []
        self.point_id = point_id
        self.slope = slope

        if len(self.species) != len(self.value):
            raise ValueError(
                f"Length mismatch: species has {len(self.species)} entries "
                f"but value has {len(self.value)}."
            )

    def add_observation(self, sp: TreeSpecies, count: int):
        """
        Add (or update) the tally count for the given species by `count`.
        Example:
            add_observation(TreeSpecies.Sweden.Picea_abies, 2)
            increments the Picea_abies count by 2.
        """
        if sp in self.species:
            idx = self.species.index(sp)
            self.value[idx] += count
        else:
            self.species.append(sp)
            self.value.append(count)

    def get_basal_area_by_species(self) -> Dict[TreeSpecies, float]:
        """
        For each species, returns the basal area per hectare (m²/ha)
        computed as (count * ba_factor).
        """
        results = {}
        for sp, cnt in zip(self.species, self.value):
            ba_ha = cnt * self.ba_factor
            results[sp] = ba_ha
        return results

    def get_stems_by_species(self) -> Dict[TreeSpecies, float]:
        """
        Simplistic approach that treats each tally as 1 stem * ba_factor stems/ha.
        i.e. stems/ha = (# tally) * ba_factor
        """
        results = {}
        for sp, cnt in zip(self.species, self.value):
            stems_ha = cnt * self.ba_factor
            results[sp] = stems_ha
        return results

    def get_stand_basal_area_objects(self) -> List[StandBasalArea]:
        """
        Return a list of `StandBasalArea` objects, one for each species tallied.
        Example usage:
            sba_list = your_bitterlich_sampling.get_stand_basal_area_objects()
        """
        sba_list = []
        for sp, cnt in zip(self.species, self.value):
            ba_ha = cnt * self.ba_factor
            sba = StandBasalArea(
                value=ba_ha,
                species=sp,
                precision=0.0,
                over_bark=True,
                direct_estimate=True
            )
            sba_list.append(sba)
        return sba_list


# ------------------------------------------------------------------------------
# SiteIndexValue: float with metadata
# ------------------------------------------------------------------------------

class SiteIndexValue(float):
    """
    A float that represents a site index value (e.g. SI=30) for a specified species
    and reference age, returned by some site-function (fn).

    Example usage:
        siv = SiteIndexValue(30.0, reference_age=100, species=TreeName("Picea_abies"), fn=my_site_index_fn)
    """
    def __new__(cls, value: float, reference_age: float, species: TreeName, fn: callable):
        if value < 0:
            raise ValueError("Site index value must be non-negative.")
        obj = super().__new__(cls, value)
        obj.reference_age = reference_age
        obj.species = species
        obj.fn = fn
        return obj

    def __repr__(self):
        fn_name = self.fn.__name__ if hasattr(self.fn, '__name__') else str(self.fn)
        return (f"SiteIndexValue({float(self)}, reference_age={self.reference_age}, "
                f"species={self.species}, fn={fn_name})")


# ------------------------------------------------------------------------------
# Volume: float with metadata (units, region, type, etc.)
# ------------------------------------------------------------------------------

class Volume(float):
    """
    Stores a volume measurement but allows easy conversion and includes region/type constraints.

    Attributes:
    -----------
    region : str
        The region/country context (e.g. 'Sweden', 'Finland', 'Norway').
    species : str
        The species name or code (if known).
    unit : str
        The unit in which 'value' is expressed (default: 'm3').
    type : str
        A string that indicates the volume type/definition (e.g. 'm3sk', 'm3to', etc.).
    """
    UNIT_CONVERSION = {
        'mm3': 1e-9,
        'cm3': 1e-6,
        'dm3': 1e-3,
        'm3': 1,
        'dam3': 1e3,
        'hm3': 1e6,
        'km3': 1e9,
        'Mm3': 1e18,
        'Gm3': 1e27,
        'Tm3': 1e36,
        'Pm3': 1e45
    }
    ORDERED_UNITS = ['mm3', 'cm3', 'dm3', 'm3', 'dam3', 'hm3', 'km3', 'Mm3', 'Gm3', 'Tm3', 'Pm3']

    TYPE_REGIONS = {
        'm3sk': ['Sweden', 'Finland', 'Norway'],
        'm3to': ['Sweden'],
        'm3fub': ['Sweden']
    }

    def __new__(cls,
                value: float,
                region: str = 'Sweden',
                species: str = 'unknown',
                unit: str = 'm3',
                type: str = 'm3sk'):
        # Convert the incoming value to an internal float in cubic meters
        if unit not in cls.UNIT_CONVERSION:
            raise ValueError(f"Unit '{unit}' not recognized. Must be one of {list(cls.UNIT_CONVERSION.keys())}.")
        obj = float.__new__(cls, cls.UNIT_CONVERSION[unit] * value)
        obj.region = region
        obj.species = species
        obj.type = type
        obj.unit = unit
        obj._validate_region()
        return obj

    def __repr__(self):
        """
        Returns a textual representation, choosing a "nice" unit in the 1–10 range if possible.
        """
        value_m3 = float(self)
        best_unit = None
        best_value = None
        # Attempt a 1-10 range
        for unit in reversed(self.ORDERED_UNITS):
            converted_value = value_m3 / self.UNIT_CONVERSION[unit]
            if 1 <= abs(converted_value) < 10:
                return (f"Volume({converted_value:.4f} {unit}, region='{self.region}', "
                        f"species='{self.species}', type='{self.type}')")
            # Track the smallest value ≥ 1 to keep as fallback
            if abs(converted_value) >= 1 and (best_value is None or abs(converted_value) < abs(best_value)):
                best_unit = unit
                best_value = converted_value

        # If no 1-10 match, use the best fallback or extreme
        if best_unit is not None:
            return (f"Volume({best_value:.4f} {best_unit}, region='{self.region}', "
                    f"species='{self.species}', type='{self.type}')")

        # If we still got nothing, we must be extremely small or zero → use 'mm3' or 'Pm3'
        extreme_unit = 'mm3' if value_m3 < 1 else 'Pm3'
        extreme_value = value_m3 / self.UNIT_CONVERSION[extreme_unit]
        return (f"Volume({extreme_value:.4f} {extreme_unit}, region='{self.region}', "
                f"species='{self.species}', type='{self.type}')")

    def _validate_region(self):
        allowed_regions = self.TYPE_REGIONS.get(self.type, [])
        # If the volume type is not recognized in TYPE_REGIONS, no restriction is applied
        if allowed_regions and (self.region not in allowed_regions):
            raise ValueError(f"Region '{self.region}' not allowed for type '{self.type}'. "
                             f"Allowed: {allowed_regions}")

    def to(self, unit: str) -> float:
        """
        Convert the internal 'm3' float to the specified unit (e.g. 'dm3', 'cm3', etc.)
        and return the numeric value as a plain float.
        """
        if unit not in self.UNIT_CONVERSION:
            raise ValueError(f"Unit '{unit}' not recognized.")
        return float(self) / self.UNIT_CONVERSION[unit]

    def m3(self) -> float:
        """
        Return the numeric value in cubic meters.
        """
        return float(self)

    def __eq__(self, other: Any):
        if not isinstance(other, Volume):
            return NotImplemented
        # We consider them "equal" if the numeric volumes match (within float tolerance)
        # and they are the same 'type' (e.g. 'm3sk'). Region must also be valid for that type.
        return (
            abs(float(self) - float(other)) < 1e-9 and
            self.type == other.type and
            self.region in self.TYPE_REGIONS.get(self.type, [self.region]) and
            other.region in self.TYPE_REGIONS.get(other.type, [other.region])
        )

    def __add__(self, other):
        self._validate_compatibility(other)
        return Volume(float(self) + float(other),
                      region=self.region,
                      species=self.species,
                      unit='m3',
                      type=self.type)

    def __sub__(self, other):
        self._validate_compatibility(other)
        return Volume(float(self) - float(other),
                      region=self.region,
                      species=self.species,
                      unit='m3',
                      type=self.type)

    def __mul__(self, scalar):
        if isinstance(scalar, Volume):
            raise TypeError("Multiplying Volume by Volume is undefined.")
        return Volume(float(self) * scalar,
                      region=self.region,
                      species=self.species,
                      unit='m3',
                      type=self.type)

    def __truediv__(self, scalar):
        if isinstance(scalar, Volume):
            raise TypeError("Dividing Volume by Volume is undefined.")
        return Volume(float(self) / scalar,
                      region=self.region,
                      species=self.species,
                      unit='m3',
                      type=self.type)

    def _validate_compatibility(self, other):
        if not isinstance(other, Volume):
            raise TypeError("Both operands must be Volume instances.")
        if self.type != other.type:
            raise ValueError(f"Incompatible volume types: {self.type} vs {other.type}")
        if self.region not in self.TYPE_REGIONS.get(self.type, [self.region]) \
           or other.region not in self.TYPE_REGIONS.get(self.type, [other.region]):
            raise ValueError(f"Regions '{self.region}' and '{other.region}' are not both valid for type '{self.type}'")

    # Convenient factory approach for region-based syntax
    class Region:
        def __init__(self, region):
            self.region = region

        def __getattr__(self, type_unit: str):
            """
            Permits calls like:
                Volume.Sweden.m3sk(123, species='Picea_abies')
                Volume.Norway.dm3sk(500, species='Pinus_sylvestris')
            """
            def creator(value, species='unknown'):
                # We parse out any recognized 'unit' prefix from type_unit (like 'dm3')
                # Then interpret the remainder as a 'type' (like 'sk').
                for possible_unit in Volume.UNIT_CONVERSION:
                    # Example: 'dm3sk' => possible_unit='dm3', remainder='sk'
                    if type_unit.startswith(possible_unit):
                        type_suffix = type_unit[len(possible_unit):]
                        # If that remainder is recognized in TYPE_REGIONS:
                        if type_suffix in Volume.TYPE_REGIONS:
                            return Volume(value,
                                          region=self.region,
                                          species=species,
                                          unit=possible_unit,
                                          type=type_suffix)
                        # If remainder is 'sk', interpret as 'm3sk'
                        if type_suffix == 'sk':
                            return Volume(value,
                                          region=self.region,
                                          species=species,
                                          unit=possible_unit,
                                          type='m3sk')
                # Alternatively, if no recognized prefix, treat the entire thing as 'type'
                if type_unit in Volume.TYPE_REGIONS:
                    return Volume(value,
                                  region=self.region,
                                  species=species,
                                  unit='m3',
                                  type=type_unit)
                if type_unit == 'sk':
                    return Volume(value,
                                  region=self.region,
                                  species=species,
                                  unit='m3',
                                  type='m3sk')
                raise ValueError(f"Invalid type/unit combination: '{type_unit}'")

            return creator

    Sweden = Region('Sweden')
    Norway = Region('Norway')
    Finland = Region('Finland')


# ------------------------------------------------------------------------------
# Position: a small data container for location with optional CRS
# ------------------------------------------------------------------------------

class Position:
    """
    Represents an (X, Y, Z) coordinate with an optional CRS.
    """
    def __init__(self,
                 X: float,
                 Y: float,
                 Z: Optional[float] = 0.0,
                 crs: Optional[CRS] = None):
        self.X = X
        self.Y = Y
        self.Z = Z
        self.crs = crs

    def __repr__(self):
        return f"Position(X={self.X}, Y={self.Y}, Z={self.Z}, crs={self.crs})"


def _set_position(pos_in: Union[Position,
                                tuple[float, float],
                                tuple[float, float, float],
                                None] = None) -> Optional[Position]:
    """
    Internal helper to standardize a user-provided position or tuple
    into a Position instance, or return None if no valid position is given.
    """
    if pos_in is None:
        return None

    if isinstance(pos_in, Position):
        return pos_in

    if isinstance(pos_in, tuple):
        if len(pos_in) == 2:
            return Position(X=pos_in[0], Y=pos_in[1], Z=0.0)
        elif len(pos_in) == 3:
            return Position(X=pos_in[0], Y=pos_in[1], Z=pos_in[2])
        else:
            raise ValueError("Position tuple must be length 2 or 3 (x, y, [z]).")

    raise TypeError("Position must be a Position or a tuple of floats (x, y, [z]).")


# ------------------------------------------------------------------------------
# Tree classes
# ------------------------------------------------------------------------------

class Tree:
    """
    Base class for all tree objects. You can expand this to include common fields/methods
    that should exist on any type of tree.
    """
    pass


class SingleTree(Tree):
    """
    A spatially explicit single tree: (x, y, [z]) in a coordinate system + attributes.

    Attributes:
    -----------
    position : Position | tuple[float,float] | tuple[float,float,float] | None
        The location of the tree in some coordinate system.
    species : TreeSpecies | str | None
        The species of the tree (or a string name to be parsed).
    age : Age | float | None
        The age of the tree. If an Age enum is used, it wraps the value in AgeMeasurement.
    diameter_cm : Diameter_cm | float | None
        The diameter (cm) if known. If a float is passed, it can be coerced to a Diameter_cm.
    height_m : float | None
        The height (m) of the tree if known.
    """
    def __init__(self,
                 position: Optional[Union[Position, tuple, None]] = None,
                 species: Optional[Union[TreeSpecies, str]] = None,
                 age: Optional[Union[Age, float]] = None,
                 diameter_cm: Optional[Union[Diameter_cm, float]] = None,
                 height_m: Optional[float] = None):
        self.position = _set_position(position)

        # Convert string species → TreeSpecies if parseable
        if isinstance(species, str):
            self.species = parse_tree_species(species)
        else:
            self.species = species

        # If `age` is e.g. float or Age, store as is (for more advanced usage,
        # you might unify to an AgeMeasurement).
        self.age = age

        # If `diameter_cm` is a float, you could coerce to a default Diameter_cm( ... )
        # or just store as float. For now, store as given:
        self.diameter_cm = diameter_cm
        self.height_m = height_m

    def __repr__(self):
        return (f"SingleTree(species={self.species}, age={self.age}, "
                f"diameter_cm={self.diameter_cm}, height_m={self.height_m}, "
                f"position={self.position})")


class RepresentationTree(Tree):
    """
    A "multiplicity" tree, i.e. a single record that represents multiple identical trees
    on a plot (spatially implicit or partially explicit).

    Attributes:
    -----------
    position : Position | tuple[float,float] | tuple[float,float,float] | None
        Location if relevant (often None or the plot center).
    species : TreeSpecies | str | None
        Species of the tree(s).
    age : Age | float | None
        Age of the tree(s).
    diameter_cm : Diameter_cm | float | None
        Diameter of the tree(s).
    height_m : float | None
        Height of the tree(s).
    weight : float
        Number of stems represented by this single record (e.g. 1, or 5).
    """
    def __init__(self,
                 position: Optional[Union[Position, tuple, None]] = None,
                 species: Optional[Union[TreeSpecies, str]] = None,
                 age: Optional[Union[Age, float]] = None,
                 diameter_cm: Optional[Union[Diameter_cm, float]] = None,
                 height_m: Optional[float] = None,
                 weight: float = 1.0):
        self.position = _set_position(position)

        if isinstance(species, str):
            self.species = parse_tree_species(species)
        else:
            self.species = species

        self.age = age
        self.diameter_cm = diameter_cm
        self.height_m = height_m
        self.weight = weight

    def __repr__(self):
        return (f"RepresentationTree(species={self.species}, age={self.age}, "
                f"diameter_cm={self.diameter_cm}, height_m={self.height_m}, weight={self.weight})")


# ------------------------------------------------------------------------------
# Plot: a set of representation trees over a circular or known-area region
# ------------------------------------------------------------------------------

class CircularPlot:
    """
    Contains information from a (usually) circular plot in a stand.

    Attributes:
    -----------
    id : int | str
        An identifier for this plot.
    position : Position | None
        The location of the plot center (if known).
    radius_m : float | None
        The radius of the circular plot in meters (if known).
    area_m2 : float | None
        The area of the plot in m² (if known). Must supply either radius_m or area_m2.
    site : SiteBase | None
        Reference to a site object, if any.
    trees : list[RepresentationTree]
        The trees recorded on this plot (each possibly representing multiple stems).
    """
    def __init__(self,
                 id: Union[int, str],
                 position: Optional[Position] = None,
                 radius_m: Optional[float] = None,
                 area_m2: Optional[float] = None,
                 site: Optional[SiteBase] = None,
                 trees: Optional[List[RepresentationTree]] = None):
        if id is None:
            raise ValueError('Plot must be given an ID (integer or string).')

        self.id = id
        self.position = position
        self.site = site
        self.trees = trees if trees is not None else []

        # Must have either radius or area
        if radius_m is None and area_m2 is None:
            raise ValueError('Plot cannot be created without either a radius_m or an area_m2!')

        if radius_m is not None:
            self.radius_m = radius_m

        if area_m2 is not None:
            self.area_m2 = area_m2

        if radius_m is not None and area_m2 is None:
            self.area_m2 = math.pi * (radius_m ** 2)
        else:
            self.radius_m = math.sqrt(self.area_m2/math.pi) 
        
        # If both were given, verify consistency
        if radius_m is not None and area_m2 is not None:
            # Check the difference
            correct_area = math.pi * (radius_m ** 2)
            if abs(correct_area - area_m2) > 1e-6:
                raise ValueError(f"Mismatch: given radius {radius_m} => area {correct_area:.6f}, "
                                 f"but you specified {area_m2:.6f}.")

    @property
    def area_ha(self) -> float:
        """
        Returns the plot area in hectares.
        """
        return self.area_m2 / 10_000.0

    def __repr__(self):
        return (f"Plot(id={self.id}, radius_m={getattr(self, 'radius_m', None)}, "
                f"area_m2={self.area_m2:.2f}, #trees={len(self.trees)})")

# -------------------------------------------------------------------------
# Accessor for .BasalArea, .Stems, etc.
# -------------------------------------------------------------------------
class StandMetricAccessor:
    """
    Provides access to stand-level metric data (e.g. BasalArea or Stems).
    Usage:
        stand.BasalArea.TOTAL
        stand.BasalArea(TreeName(...))
        float(stand.BasalArea) -> numeric total
        stand.BasalArea.precision -> total's precision
    """
    def __init__(self, stand: 'Stand', metric_name: str):
        self._stand = stand
        self._metric_name = metric_name

    def _ensure_estimates(self):
        """Compute or refresh HT estimates if not done."""
        if not hasattr(self._stand, '_metric_estimates'):
            self._stand._compute_ht_estimates()

    def __getattr__(self, item):
        """
        Allows dot-based access .TOTAL => returns aggregator for total.
        """
        if item == "TOTAL":
            self._ensure_estimates()
            metric_dict = self._stand._metric_estimates[self._metric_name]
            return metric_dict["TOTAL"]
        raise AttributeError(f"No attribute '{item}' in StandMetricAccessor for {self._metric_name}")

    def __call__(self, species: Union[TreeName, str]):
        """
        Call-syntax for species-level estimates:
          stand.BasalArea(TreeName(...)) or stand.BasalArea("picea abies")
        """
        self._ensure_estimates()
        # Convert species (TreeName or str) → TreeName
        if isinstance(species, str):
            sp_obj = parse_tree_species(species)
        else:
            sp_obj = species

        metric_dict = self._stand._metric_estimates[self._metric_name]
        if sp_obj not in metric_dict:
            raise KeyError(f"No estimate found for species={sp_obj.full_name} in {self._metric_name}.")
        return metric_dict[sp_obj]

    def __float__(self):
        """
        float(stand.BasalArea) -> numeric value of the total aggregator
        """
        self._ensure_estimates()
        total_obj = self._stand._metric_estimates[self._metric_name]["TOTAL"]
        return float(total_obj)

    @property
    def value(self) -> float:
        """Shortcut to the total aggregator's numeric value."""
        return float(self)

    @property
    def precision(self) -> float:
        """Shortcut to the total aggregator's precision."""
        self._ensure_estimates()
        total_obj = self._stand._metric_estimates[self._metric_name]["TOTAL"]
        return getattr(total_obj, "precision", 0.0)

    def __repr__(self):
        return f"<StandMetricAccessor metric={self._metric_name}>"


# ------------------------------------------------------------------------------
# Stand: a collection of plots and/or a polygon
# ------------------------------------------------------------------------------

class Stand:
    """
    Represents a forest stand, which may have:
      - A polygon boundary
      - A list of sample plots
      - A site reference
      - Additional attributes (attrs dict)
      - A user-defined definition of "top height"

    If a polygon is provided, the area_ha is computed from the polygon geometry
    (reprojected to a suitable UTM if the original CRS is geographic).
    """
    def __init__(self,
                 site: Optional[SiteBase] = None,
                 area_ha: Optional[float] = None,
                 plots: Optional[List[CircularPlot]] = None,
                 polygon: Optional[Polygon] = None,
                 crs: str = "EPSG:4326",
                 top_height_definition: Optional[TopHeightDefinition] = None):
        self.site = site
        self.polygon = polygon
        self.crs = crs

        self.top_height_definition = top_height_definition if top_height_definition else TopHeightDefinition()

        self.plots: List[CircularPlot] = plots if plots else []

        # If user gave an explicit area
        self.area_ha = area_ha

        # If a polygon is given, compute its area in hectares after projecting
        if polygon:
            gdf = gpd.GeoDataFrame({'geometry': [polygon]}, crs=self.crs)
            if gdf.crs is not None and gdf.crs.is_geographic:
                # Reproject to an appropriate UTM
                utm_crs = gdf.estimate_utm_crs()
                gdf = gdf.to_crs(utm_crs)
            proj_polygon = gdf.geometry.iloc[0]
            if not proj_polygon.is_valid:
                raise ValueError('Polygon is not valid after reprojection to a UTM projection. Check original provided CRS.')
            polygon_area_m2 = proj_polygon.area
            derived_area_ha = polygon_area_m2 / 10_000.0

            # If user specified area_ha, check consistency
            if self.area_ha is not None:
                diff = abs(self.area_ha - derived_area_ha)
                if diff > 0.01:
                    raise ValueError(f"Polygon area is {derived_area_ha:.2f} ha, but you set area_ha={self.area_ha:.2f} ha.")
            else:
                self.area_ha = derived_area_ha

        # Arbitrary dictionary for user-defined stand-level metadata
        self.attrs: Dict[str, Any] = {}

        # Where we store final "Stems", "BasalArea", etc. after computing
        self._metric_estimates: Dict[str, Dict[Any, Union[Stems, StandBasalArea]]] = {}

        #Get angle-counting estimates for stand
        self.Stems = Stems(BitterlichSampling())

    
    # Two key properties for your requested usage:
    @property
    def BasalArea(self) -> StandMetricAccessor:
        """
        Access the stand's basal-area aggregator.
        Example:
            stand.BasalArea.TOTAL         -> StandBasalArea for total
            stand.BasalArea(TreeName(...))-> species-level StandBasalArea
            float(stand.BasalArea)        -> numeric total
        """
        return StandMetricAccessor(self, "BasalArea")

    @property
    def Stems(self) -> StandMetricAccessor:
        """
        Access the stand's stems aggregator.
        Example:
            stand.Stems.TOTAL          -> Stems object
            stand.Stems(TreeName(...)) -> species-level Stems
            float(stand.Stems)         -> numeric total
        """
        return StandMetricAccessor(self, "Stems")

    def _compute_ht_estimates(self):
        """
        Compute Horvitz–Thompson style estimates across all plots.
        We'll sum or average the per-plot values for each species:
          - stems/ha
          - basal_area/ha
        Store them in self._metric_estimates: 
            {
              "Stems": {TreeName(...) : Stems(...), ..., "TOTAL": Stems(...)},
              "BasalArea": {TreeName(...): StandBasalArea(...), ..., "TOTAL": StandBasalArea(...)}
            }
        """
        species_data: Dict[TreeName, Dict[str, List[float]]] = {}

        # 1. Gather data from each plot
        for plot in self.plots:
            area_ha = plot.area_ha or 1.0

            # Group by TreeName
            trees_by_sp: Dict[TreeName, List[RepresentationTree]] = {}
            for tr in plot.trees:
                sp = getattr(tr, 'species', None)
                if sp is None:
                    continue
                if isinstance(sp, str):
                    sp = parse_tree_species(sp)  # convert
                trees_by_sp.setdefault(sp, []).append(tr)

            # For each species in this plot, compute stems/ha & BA/ha
            for sp, trlist in trees_by_sp.items():
                stems_count = sum(t.weight for t in trlist)  # sum of weights
                stems_ha = stems_count / area_ha

                # Basal area: sum of pi * (d/2)^2 * weight, with d in meters
                ba_sum = 0.0
                for t in trlist:
                    d_cm = float(t.diameter_cm) if t.diameter_cm is not None else 0.0
                    r_m = (d_cm / 100.0) / 2.0  # radius in meters
                    ba_sum += math.pi * (r_m**2) * t.weight
                ba_ha = ba_sum / area_ha

                # Store
                if sp not in species_data:
                    species_data[sp] = {
                        "stems_per_ha": [],
                        "basal_area_per_ha": []
                    }
                species_data[sp]["stems_per_ha"].append(stems_ha)
                species_data[sp]["basal_area_per_ha"].append(ba_ha)

        # 2. Compute means + (population) variance across plots
        stems_dict: Dict[Union[TreeName, str], Stems] = {}
        ba_dict: Dict[Union[TreeName, str], StandBasalArea] = {}

        total_stems_val = 0.0
        total_stems_var = 0.0
        total_ba_val = 0.0
        total_ba_var = 0.0

        for sp, metricvals in species_data.items():
            s_vals = metricvals["stems_per_ha"]
            b_vals = metricvals["basal_area_per_ha"]

            stems_mean = statistics.mean(s_vals) if s_vals else 0.0
            stems_var = statistics.pvariance(s_vals) if len(s_vals) > 1 else 0.0

            ba_mean = statistics.mean(b_vals) if b_vals else 0.0
            ba_var = statistics.pvariance(b_vals) if len(b_vals) > 1 else 0.0

            stems_dict[sp] = Stems(value=stems_mean, species=sp, precision=math.sqrt(stems_var))
            ba_dict[sp] = StandBasalArea(value=ba_mean, species=sp, precision=math.sqrt(ba_var))

            total_stems_val += stems_mean
            total_stems_var += stems_var
            total_ba_val += ba_mean
            total_ba_var += ba_var

        # "TOTAL" aggregator
        stems_dict["TOTAL"] = Stems(value=total_stems_val,
                                    species=None,  # or "TOTAL"
                                    precision=math.sqrt(total_stems_var))
        ba_dict["TOTAL"] = StandBasalArea(value=total_ba_val,
                                          species=None,
                                          precision=math.sqrt(total_ba_var))

        self._metric_estimates["Stems"] = stems_dict
        self._metric_estimates["BasalArea"] = ba_dict

    def __repr__(self):
        return f"Stand(area_ha={self.area_ha}, n_plots={len(self.plots)})"

    def get_dominant_height(self) -> Optional[TopHeightMeasurement]:
        """
        Attempts to compute a stand-level 'dominant height' (aka top height)
        from the available plots, then correct it by subtracting a simulated bias.

        Returns
        -------
        TopHeightMeasurement | None
            The final best estimate of top height in meters, along with metadata.
            If insufficient data, returns None.
        """
        if not self.plots:
            return None

        # 1. Identify the "mode" (most common) plot area so we can treat them uniformly
        plot_areas_ha = [p.area_ha for p in self.plots]
        if not plot_areas_ha:
            return None

        try:
            mode_area_ha = statistics.mode(plot_areas_ha)
        except statistics.StatisticsError:
            # If there's no unique mode, just pick the first
            mode_area_ha = plot_areas_ha[0]

        # Subset the plots that match this mode
        subplots = [p for p in self.plots if math.isclose(p.area_ha, mode_area_ha, rel_tol=1e-9)]

        if not subplots:
            return None

        # 2. Determine how many top trees with valid heights each subplot can contribute
        #    We'll pick the smallest number of valid-height trees among these subplots
        #    so we can consistently choose the top M from each.
        m_values = []
        for plot in subplots:
            # Sort trees descending by diameter
            sorted_trees = sorted(plot.trees,
                                  key=lambda t: (t.diameter_cm if t.diameter_cm else -999),
                                  reverse=True)
            count_valid = sum(1 for t in sorted_trees if t.height_m is not None)
            m_values.append(count_valid)

        if not m_values:
            return None

        m_real = min(m_values)
        if m_real == 0:
            # No measured heights
            return None

        # 3. For each subplot, take the top M (by diameter) that have heights, average them
        #    Then average across subplots to get a raw estimate
        subplot_means = []
        for plot in subplots:
            sorted_trees = sorted(plot.trees,
                                  key=lambda t: (t.diameter_cm if t.diameter_cm else -999),
                                  reverse=True)
            # The top M among those that have heights
            top_m = [t for t in sorted_trees[:m_real] if t.height_m is not None]
            if len(top_m) < m_real:
                continue

            subplot_mean_h = statistics.mean([t.height_m for t in top_m])
            subplot_means.append(subplot_mean_h)

        if not subplot_means:
            return None

        h_est_raw = statistics.mean(subplot_means)

        # Simple standard error across subplots
        if len(subplot_means) > 1:
            precision_est = statistics.pstdev(subplot_means) / math.sqrt(len(subplot_means))
        else:
            precision_est = 0.0

        # 4. Use a small Monte Carlo to estimate bias for (r_real, m_real)
        real_radius_m = math.sqrt(mode_area_ha * 10_000 / math.pi)
        nominal_top_n = self.top_height_definition.nominal_n
        nominal_area_ha = self.top_height_definition.nominal_area_ha

        bias, _bias_percentage = self.calculate_top_height_bias(
            r=real_radius_m,
            m=m_real,
            n_trees=1000,
            n_simulations=5000,
            nominal_top_n=nominal_top_n,
            nominal_area=nominal_area_ha * 10_000,
            sigma=3.0
        )

        h_est_corrected = h_est_raw - bias

        # Return a TopHeightMeasurement
        return TopHeightMeasurement(
            value=h_est_corrected,
            definition=self.top_height_definition,
            species=None,  # or you could attempt an aggregated species list
            precision=precision_est,
            est_bias=bias
        )

    @staticmethod
    def calculate_top_height_bias(r: float,
                                  m: int,
                                  n_trees: int = 1000,
                                  n_simulations: int = 10000,
                                  nominal_top_n: int = 100,
                                  nominal_area: float = 10000.0,
                                  sigma: float = 3.0):
        """
        Calculate the bias of the estimator h_hat for top height in a forest stand.
        Based on (a simplified interpretation of) Matérn's ideas on top-height sampling.

        Parameters:
        -----------
        r : float
            Radius of the circular plot (meters).
        m : int
            Number of largest trees (by diameter) to average in the plot.
        n_trees : int
            Number of trees in each simulated stand.
        n_simulations : int
            Number of Monte Carlo runs (default 10,000).
        nominal_top_n : int
            The nominal definition of "top" trees (e.g. top 100 in 1.0 ha).
        nominal_area : float
            The nominal area in which we define top_n (default: 10,000 m² = 1.0 ha).
        sigma : float
            Percentage measurement error in height (default 3.0% of the tree's height).

        Returns:
        --------
        (bias, bias_percentage):
            bias : float
                Average difference (h_hat - H_bar).
            bias_percentage : float
                That bias as a percentage of the true top height H_bar.
        """
        h_hat_list = []
        H_bar_list = []

        for _ in range(n_simulations):
            # Generate random positions in the square bounding nominal_area
            side = math.sqrt(nominal_area)
            x_pos = np.random.uniform(0, side, n_trees)
            y_pos = np.random.uniform(0, side, n_trees)

            # Generate diameters (exponential distribution, mean ~20 cm)
            diameters = np.random.exponential(scale=20.0, size=n_trees)

            # 'True' heights from a toy height-diameter function
            # You can replace this with a more realistic model
            heights_true = 1.3 + (diameters**2) / ((1.1138 + 0.2075 * diameters)**2)

            # Add 3% measurement error (for example)
            noise = np.random.normal(0, (sigma / 100.0) * heights_true, n_trees)
            heights_measured = heights_true + noise

            # The "true" top height H_bar in the entire stand is the mean of top nominal_top_n by diameter
            top_indices = np.argsort(diameters)[-nominal_top_n:][::-1]
            H_bar = np.mean(heights_true[top_indices])
            H_bar_list.append(H_bar)

            # Now place a random circular plot of radius r
            center_x = np.random.uniform(r, side - r)
            center_y = np.random.uniform(r, side - r)
            dist = np.sqrt((x_pos - center_x)**2 + (y_pos - center_y)**2)
            in_plot = dist <= r

            # If enough trees are in the plot, compute h_hat
            if np.sum(in_plot) >= m:
                plot_diams = diameters[in_plot]
                plot_h = heights_measured[in_plot]
                # The top m by diameter
                top_m_indices = np.argsort(plot_diams)[-m:][::-1]
                h_hat = np.mean(plot_h[top_m_indices])
            else:
                h_hat = np.nan

            h_hat_list.append(h_hat)

        # Compute average bias
        h_hat_avg = np.nanmean(h_hat_list)
        H_bar_avg = np.mean(H_bar_list)

        bias = h_hat_avg - H_bar_avg
        bias_percentage = (bias / H_bar_avg) * 100.0 if H_bar_avg != 0 else 0.0

        return bias, bias_percentage

