from pyproj import CRS
from enum import Enum
import math
import statistics
from typing import List, Any, Dict, Optional, Union, Tuple, Callable
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
    
    @property
    def value(self) -> float:
        return float(self)

    def __repr__(self):
        return (f"Diameter_cm({float(self)}, over_bark={self.over_bark}, "
                f"measurement_height_m={self.measurement_height_m})")


# --- Age Enum ---
class Age(Enum):
    TOTAL = 1
    DBH = 2

    def __call__(self, value: float) -> 'AgeMeasurement': # Use forward reference string
        return AgeMeasurement(value, self.value)

# --- AgeMeasurement Class ---
class AgeMeasurement(float):
    def __new__(cls, value: float, code: int):
        if value < 0:
            raise ValueError("Age must be non-negative.")
        # Ensure code is valid using the Age enum definition
        if code not in [m.value for m in Age]: # Check against Age enum values
             raise ValueError(f"Invalid age code: {code}. Must be one of {[m.value for m in Age]}.")
        obj = super().__new__(cls, value)
        obj.code = code
        return obj

    @property
    def value(self) -> float:
        return float(self)

    def __repr__(self):
        # Ensure Age enum lookup is safe
        age_type = 'UNKNOWN'
        try:
            age_type = Age(self.code).name
        except ValueError:
            pass # Keep 'UNKNOWN' if code not in enum
        return f"AgeMeasurement({float(self)}, code={self.code} [{age_type}])"

    def __eq__(self, other):
         if isinstance(other, AgeMeasurement):
             # *** Crucial: Compare both value and code ***
             return float(self) == float(other) and self.code == other.code
         elif isinstance(other, (float, int)):
             # Comparison with plain number only checks value
             return float(self) == float(other)
         return NotImplemented

    def __ne__(self, other):
        equal = self.__eq__(other)
        return NotImplemented if equal is NotImplemented else not equal



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
                species: Optional[TreeName] = None,
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
    
    @property
    def value(self) -> float:
        return float(self)

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
                species: Optional[TreeName] = None,
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
    
    @property
    def value(self) -> float:
        return float(self)

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
                species: Optional[TreeName] = None,
                precision: float = 0.0):
        if value < 0:
            raise ValueError("Stems must be non-negative.")
        obj = float.__new__(cls, value)
        obj.species = species
        obj.precision = precision
        return obj

    @property
    def value(self) -> float:
        return float(self)
    
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
    
    @property
    def value(self) -> float:
        return float(self)

    def __repr__(self):
        return (f"TopHeightMeasurement({float(self):.2f} m, definition={self.definition}, "
                f"species={self.species}, precision={self.precision}, est_bias={self.est_bias})")

class QuadraticMeanDiameter(float):
    """
    Represents the quadratic mean diameter (in centimeters) with an associated precision.
    
    The value is computed as:
        QMD = sqrt((40000 * BasalArea) / (pi * Stems))
    where BasalArea is in m²/ha and Stems is in stems/ha.
    """
    def __new__(cls, value: float, precision: float = 0.0):
        if value < 0:
            raise ValueError("QuadraticMeanDiameter must be non-negative.")
        obj = float.__new__(cls, value)
        obj.precision = precision
        return obj

    @property
    def value(self) -> float:
        return float(self)

    def __repr__(self):
        return f"QuadraticMeanDiameter({float(self):.2f} cm, precision={self.precision:.2f} cm)"


# ------------------------------------------------------------------------------
# Bitterlich (Angle count) Sampling
# ------------------------------------------------------------------------------

class AngleCount:
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

class AngleCountAggregator:
    """
    Aggregates multiple AngleCountRecord objects. 
    Handles merging records with the same point_id and computes stand-level metrics.
    """
    def __init__(self, records: List[AngleCount]):
        self.records = records

    def merge_by_point_id(self) -> List[AngleCount]:
        """
        Merge records that have the same point_id by averaging their counts.
        If point_id is None, they are treated as separate.
        """
        merged = {}
        for rec in self.records:
            key = rec.point_id if rec.point_id is not None else id(rec)
            if key in merged:
                merged[key] = self._merge_records(merged[key], rec)
            else:
                merged[key] = rec
        return list(merged.values())

    def _merge_records(self, rec1: AngleCount, rec2: AngleCount) -> AngleCount:
        """
        Merge two records with the same point_id.
        This example assumes both records have the same species order and ba_factor.
        """
        if rec1.ba_factor != rec2.ba_factor:
            raise ValueError("Cannot merge records with different ba_factor values.")
        if rec1.species != rec2.species:
            raise ValueError("Cannot merge records with different species lists.")

        # Average the counts; you could also sum them depending on your intended semantics.
        new_values = [(a + b) / 2 for a, b in zip(rec1.value, rec2.value)]
        return AngleCount(
            ba_factor=rec1.ba_factor,
            value=new_values,
            species=rec1.species,
            point_id=rec1.point_id,
            slope=rec1.slope  # or combine slopes as needed
        )
    
    def aggregate_stand_metrics(self) -> Tuple[Dict[TreeName, StandBasalArea],
                                              Dict[TreeName, Stems]]:
        """
        Aggregate the merged records to compute stand-level metrics.
        Returns two dictionaries keyed by species (TreeName) with their
        corresponding StandBasalArea and Stems objects.

        For StandBasalArea, the value and precision are computed as:
          value = mean(counts) * ba_factor
          precision = sqrt(pvariance(counts)) * ba_factor

        For Stems, the value and precision are computed from the raw counts.
        """
        merged_records = self.merge_by_point_id()
        species_counts: Dict[TreeName, list[float]] = {}
        total_counts: list[float] = []

        # Assume all records use the same ba_factor for simplicity.
        ba_factor = merged_records[0].ba_factor if merged_records else 0

        # Collect counts per species and overall totals for each merged record.
        for rec in merged_records:
            record_total = 0.0
            for sp, cnt in zip(rec.species, rec.value):
                record_total += cnt
                if sp not in species_counts:
                    species_counts[sp] = []
                species_counts[sp].append(cnt)
            total_counts.append(record_total)

        basal_area_by_species: Dict[TreeName, StandBasalArea] = {}
        stems_by_species: Dict[TreeName, Stems] = {}

        # Create metric objects for each species.
        for sp, counts in species_counts.items():
            # For basal area: apply the ba_factor conversion.
            count_mean = statistics.mean(counts)
            count_var = statistics.pvariance(counts) if len(counts) > 1 else 0.0
            ba_value = count_mean * ba_factor
            ba_precision = math.sqrt(count_var) * ba_factor

            basal_area_by_species[sp] = StandBasalArea(
                value=ba_value,
                species=sp,
                precision=ba_precision,
                over_bark=True,
                direct_estimate=True
            )

            # For stems: use the raw counts.
            stems_value = count_mean
            stems_precision = math.sqrt(count_var)

            stems_by_species[sp] = Stems(
                value=stems_value,
                species=sp,
                precision=stems_precision
            )

        # Compute overall (TOTAL) metrics.
        if total_counts:
            total_mean = statistics.mean(total_counts)
            total_var = statistics.pvariance(total_counts) if len(total_counts) > 1 else 0.0
            total_ba_value = total_mean * ba_factor
            total_ba_precision = math.sqrt(total_var) * ba_factor
            total_stems_value = total_mean
            total_stems_precision = math.sqrt(total_var)
        else:
            total_ba_value = total_ba_precision = total_stems_value = total_stems_precision = 0.0

        # You might use a special key for total; here we use the string "TOTAL".
        basal_area_by_species["TOTAL"] = StandBasalArea(
            value=total_ba_value,
            species="TOTAL",
            precision=total_ba_precision,
            over_bark=True,
            direct_estimate=True
        )
        stems_by_species["TOTAL"] = Stems(
            value=total_stems_value,
            species="TOTAL",
            precision=total_stems_precision
        )

        return basal_area_by_species, stems_by_species

# ------------------------------------------------------------------------------
# SiteIndexValue: float with metadata
# ------------------------------------------------------------------------------

class SiteIndexValue(float):
    def __new__(cls,
                value: float,
                reference_age: AgeMeasurement, # Expects AgeMeasurement
                species: set[TreeName], #Potentially more than one, e.g. Betula pendula, Betula pubescens.
                fn: Callable):

        # Check type of reference_age
        if not isinstance(reference_age, AgeMeasurement):
            raise TypeError(f"reference_age must be an AgeMeasurement object, not {type(reference_age)}")
        
        # --- Validate the species set ---
        if not isinstance(species, set):
            raise TypeError(f"species must be a set, not {type(species)}")
        if not species: # Check if the set is empty
             raise ValueError("species set cannot be empty.")
        for item in species:
            if not isinstance(item, TreeName):
                raise TypeError(f"All items in the species set must be TreeName objects, found {type(item)}")

        if value < 0:
            raise ValueError("Site index value must be non-negative.")

        obj = super().__new__(cls, value)
        obj.reference_age = reference_age # Store the object
        obj.species = species
        obj.fn = fn
        return obj

    def __repr__(self):
        fn_name = self.fn.__name__ if hasattr(self.fn, '__name__') else str(self.fn)
        # Represent the set of species clearly
        species_repr = "{" + ", ".join(sorted(repr(s) for s in self.species)) + "}" # Sort for consistent repr
        return (f"SiteIndexValue({float(self)}, reference_age={self.reference_age}, "
                f"species={species_repr}, fn={fn_name})") # Use the set repr
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
    
    If crs is None, the coordinate system is assumed to be non‐geographic.
        
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
        self.coordinate_system = 'cartesian'

    @classmethod
    def from_polar(cls, r: float, theta: float, z: Optional[float] = 0.0):
        """
        Create a Position using polar coordinates.

        Theta is assumed to be in radians.
        The resulting Position has no CRS.
        """
        x = r * math.cos(theta)
        y = r * math.sin(theta)
        obj = cls(x, y, z, crs=None)
        obj.coordinate_system = 'polar'
        # Optionally store the original polar parameters:
        obj.r = r
        obj.theta = theta
        return obj

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

