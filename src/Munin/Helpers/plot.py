from typing import Union, Optional, List
from math import sqrt, pi
from Munin.Helpers import Position, AngleCount, RepresentationTree, TreeName, parse_tree_species, SiteBase


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
    occlusion : float
        Portion [0-1] of the stand to be adjusted for being outside of the stand. Adjustment is 
    area_m2 : float | None
        The area of the plot in m² (if known). Must supply either radius_m or area_m2.
    site : SiteBase | None
        Reference to a site object, if any.
    trees : list[RepresentationTree]
        The trees recorded on this plot (each possibly representing multiple stems).
    """
    def __init__(self,
                 id: Union[int, str],
                 occlusion: float = 0.0,
                 position: Optional[Position] = None,
                 radius_m: Optional[float] = None,
                 area_m2: Optional[float] = None,
                 site: Optional[SiteBase] = None,
                 AngleCount: Optional[List[AngleCount]] = None,
                 trees: Optional[List[RepresentationTree]] = None):
        if id is None:
            raise ValueError('Plot must be given an ID (integer or string).')

        self.id = id
        self.position = position
        self.site = site

        if not 0<=occlusion<1:
            raise ValueError('Plot must have [0,0.99] occlusion!')
        self.occlusion = occlusion

        self.AngleCount = AngleCount if AngleCount is not None else []

        self.trees = trees if trees is not None else []

        # Must have either radius or area
        if radius_m is None and area_m2 is None:
            raise ValueError('Plot cannot be created without either a radius_m or an area_m2!')

        if radius_m is not None:
            self.radius_m = radius_m

        if area_m2 is not None:
            self.area_m2 = area_m2

        if radius_m is not None and area_m2 is None:
            self.area_m2 = pi * (radius_m ** 2)
        else:
            self.radius_m = sqrt(self.area_m2/pi) 
        
        # If both were given, verify consistency
        if radius_m is not None and area_m2 is not None:
            # Check the difference
            correct_area = pi * (radius_m ** 2)
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
        if self._metric_name not in self._stand._metric_estimates:
             if not self._stand.use_angle_count:
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
