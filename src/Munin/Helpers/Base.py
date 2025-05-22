from shapely import Polygon
import geopandas as gpd
import math
import numpy as np
import statistics
from typing import List, Any, Dict, Optional, Union


# -------------
# Stubs
# -------------
from Munin.Site.SiteBase import SiteBase  
from Munin.Helpers.TreeSpecies import (
    TreeName, 
    parse_tree_species
)

from Munin.Helpers.Primitives import (
    Position,
    AngleCount,
    AngleCountAggregator,
    RepresentationTree,
    TopHeightDefinition,
    Stems,
    StandBasalArea,
    QuadraticMeanDiameter,
    TopHeightMeasurement,

)

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
                 position: Optional[Position] = None,
                 radius_m: Optional[float] = None,
                 area_m2: Optional[float] = None,
                 site: Optional[SiteBase] = None,
                 occlusion: Optional[float] = 0,
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
                 crs: str = None,
                 top_height_definition: Optional[TopHeightDefinition] = None):
        self.site = site
        self.polygon = polygon
        self.crs = crs

        self.top_height_definition = top_height_definition if top_height_definition else TopHeightDefinition()

        self.plots = plots if plots else []

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

        #Get angle-counting estimates for stand (should be stored in self._metric_estimates)
        # Determine if any plots supply AngleCount objects.
        all_angle_counts = [(ac, plot.occlusion) for plot in self.plots for ac in plot.AngleCount]
        if all_angle_counts:
            # Use AngleCount-based estimates.
            ba_dict, stems_dict = AngleCountAggregator(all_angle_counts).aggregate_stand_metrics()
            self._metric_estimates["BasalArea"] = ba_dict
            self._metric_estimates["Stems"] = stems_dict
            self.use_angle_count = True
        else:
            self.use_angle_count = False
    
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
    
    @property
    def QMD(self) -> StandMetricAccessor:
        """
        Access the stand's quadratic mean diameter (QMD) aggregator.
        Usage:
          Stand.QMD.TOTAL               -> Total QMD (QuadraticMeanDiameter)
          Stand.QMD(TreeSpecies(...))   -> Species-level QMD estimate
          float(Stand.QMD)              -> Numeric total QMD value (in cm)
        """
        self._ensure_qmd_estimates()
        return StandMetricAccessor(self, "QMD")

    def _ensure_qmd_estimates(self):
        """
        Ensure that QMD estimates are computed.
        QMD is computed from the existing BasalArea and Stems estimates.
        """
        if "QMD" not in self._metric_estimates:
            # Ensure BA and Stems are available (compute if needed)
            if "BasalArea" not in self._metric_estimates or "Stems" not in self._metric_estimates:
                self._compute_ht_estimates()
            self._compute_qmd_estimates()

    def _compute_qmd_estimates(self):
        """
        Compute Quadratic Mean Diameter (QMD) estimates for each species (and total)
        from the existing basal area and stems estimates.
        """
        qmd_dict = {}
        ba_dict = self._metric_estimates["BasalArea"]
        stems_dict = self._metric_estimates["Stems"]

        for key in ba_dict:
            ba_obj = ba_dict[key]
            stems_obj = stems_dict[key]
            if stems_obj.value > 0:
                # QMD in cm computed from BA (m²/ha) and stems (stems/ha)
                qmd_value = math.sqrt((40000.0 * ba_obj.value) / (math.pi * stems_obj.value))
                # Propagate errors:
                # dQ/dBA = 20000 / (pi * stems * QMD)
                # dQ/dStems = - QMD / (2 * stems)
                if qmd_value > 0:
                    dQ_dBA = 20000.0 / (math.pi * stems_obj.value * qmd_value)
                else:
                    dQ_dBA = 0.0
                dQ_dStems = qmd_value / (2 * stems_obj.value)
                qmd_precision = math.sqrt((dQ_dBA * ba_obj.precision)**2 +
                                          (dQ_dStems * stems_obj.precision)**2)
            else:
                qmd_value = 0.0
                qmd_precision = 0.0

            qmd_dict[key] = QuadraticMeanDiameter(qmd_value, precision=qmd_precision)

        self._metric_estimates["QMD"] = qmd_dict


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
            # effective area is the visible portion of the plot
            effective_area_ha = area_ha * (1 - plot.occlusion) if (1 - plot.occlusion) > 0 else area_ha

            # Group trees by species
            trees_by_sp: Dict[TreeName, List[RepresentationTree]] = {}
            for tr in plot.trees:
                sp = getattr(tr, 'species', None)
                if sp is None:
                    continue
                if isinstance(sp, str):
                    sp = parse_tree_species(sp)
                trees_by_sp.setdefault(sp, []).append(tr)

            # For each species in this plot, compute the adjusted stems/ha and BA/ha
            for sp, trlist in trees_by_sp.items():
                stems_count = sum(t.weight for t in trlist)
                # Adjusted stems/ha: divide by the effective area
                stems_ha = stems_count / effective_area_ha

                # Compute basal area (m²) for trees in the plot.
                ba_sum = 0.0
                for t in trlist:
                    d_cm = float(t.diameter_cm) if t.diameter_cm is not None else 0.0
                    r_m = (d_cm / 100.0) / 2.0
                    ba_sum += math.pi * (r_m ** 2) * t.weight
                # Adjusted BA/ha: divide by effective area.
                ba_ha = ba_sum / effective_area_ha

                if sp not in species_data:
                    species_data[sp] = {"stems_per_ha": [], "basal_area_per_ha": []}
                species_data[sp]["stems_per_ha"].append(stems_ha)
                species_data[sp]["basal_area_per_ha"].append(ba_ha)

        # 2. Compute means and variances across plots (as before)
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
                                        species=None,
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
    
    def append_plot(self, plot: CircularPlot) -> None:
        """
        Append a new plot to the stand and recalculate the stand-level metrics.
        If any plot in the updated stand has AngleCount data, those estimates take precedence.
        """
        self.plots.append(plot)

        # Gather all AngleCount records from all plots.
        all_angle_counts = [ac for p in self.plots for ac in p.AngleCount]

        if all_angle_counts:
            # Use the AngleCount aggregator.
            ba_dict, stems_dict = AngleCountAggregator(all_angle_counts).aggregate_stand_metrics()
            self._metric_estimates["BasalArea"] = ba_dict
            self._metric_estimates["Stems"] = stems_dict
            self.use_angle_count = True
        else:
            # Otherwise, recompute using the tree-based estimates.
            self._compute_ht_estimates()
            self.use_angle_count = False


