"""Utilities for working with forest stands.

This module defines :class:`Stand`, representing a collection of sample plots and
an optional boundary polygon, along with the :class:`StandMetricAccessor` helper
used to access aggregated stand metrics such as basal area or stem count.
"""

import statistics
import warnings
from dataclasses import dataclass, field
from math import isclose, pi, sqrt
from typing import Any, Callable, Dict, List, Optional, Set, Union, cast

import geopandas as gpd
import numpy as np
from pyproj import CRS
from shapely import Polygon
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry

from pyforestry.base.helpers import (
    AngleCountAggregator,
    CircularPlot,
    Tree,
    TreeName,
    parse_tree_species,
)
from pyforestry.base.helpers.primitives import (
    QuadraticMeanDiameter,
    SiteBase,
    StandBasalArea,
    Stems,
    TopHeightDefinition,
    TopHeightMeasurement,
)


# -------------------------------------------------------------------------
# Accessor for .BasalArea, .Stems, etc.
# -------------------------------------------------------------------------
class StandMetricAccessor:
    """
    Provides access to stand-level metric data (e.g. BasalArea or Stems).

    Usage::

        stand.BasalArea.TOTAL
        stand.BasalArea(TreeName(...))
        float(stand.BasalArea) -> numeric total
        stand.BasalArea.precision -> total's precision
    """

    def __init__(self, stand: "Stand", metric_name: str):
        """Create a new accessor bound to ``stand`` for ``metric_name``.

        Parameters
        ----------
        stand:
            The :class:`Stand` instance this accessor reads values from.
        metric_name:
            Name of the metric (``"BasalArea"``, ``"Stems"``, ``"QMD"``) that
            this accessor should retrieve.
        """
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
        raise AttributeError(
            f"No attribute '{item}' in StandMetricAccessor for {self._metric_name}"
        )

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
            raise KeyError(
                f"No estimate found for species={sp_obj.full_name} in {self._metric_name}."
            )
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
        """Return a concise representation for debugging."""
        return f"<StandMetricAccessor metric={self._metric_name}>"


@dataclass
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

    site: Optional[SiteBase] = None
    area_ha: Optional[float] = None
    plots: List[CircularPlot] = field(default_factory=list)
    polygon: Optional[Polygon] = None
    crs: Optional[CRS] = None
    top_height_definition: TopHeightDefinition = field(default_factory=TopHeightDefinition)
    attrs: Dict[str, Any] = field(default_factory=dict, init=False)
    _metric_estimates: Dict[str, Dict[Any, Union[Stems, StandBasalArea]]] = field(
        default_factory=dict,
        init=False,
    )
    use_angle_count: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        """Initialize derived attributes and pre-compute metric estimates.

        * If ``polygon`` is provided, its area is projected to a suitable UTM
          system and used to fill ``area_ha`` (or validated against the supplied
          value).
        * If the stand contains plots with :class:`~pyforestry.base.helpers.AngleCount`
          records, the aggregated basal area and stem estimates are calculated
          immediately and the stand is marked as using angle-count data.
        """
        # If a polygon is given, compute its area in hectares after projecting
        if self.polygon:
            gdf = gpd.GeoDataFrame({"geometry": [self.polygon]}, crs=self.crs)
            if gdf.crs is not None and gdf.crs.is_geographic:
                utm_crs = gdf.estimate_utm_crs()
                gdf = gdf.to_crs(utm_crs)

            proj_polygon = cast(BaseGeometry, gdf.geometry.iloc[0])
            if not proj_polygon.is_valid:
                raise ValueError(
                    "Polygon is not valid after reprojection to a UTM projection. "
                    "Check original provided CRS."
                )
            polygon_area_m2 = proj_polygon.area
            derived_area_ha = polygon_area_m2 / 10_000.0

            if self.area_ha is not None:
                diff = abs(self.area_ha - derived_area_ha)
                if diff > 0.01:
                    raise ValueError(
                        f"Polygon area is {derived_area_ha:.2f} ha, but you set "
                        f"area_ha={self.area_ha:.2f} ha."
                    )
            else:
                self.area_ha = derived_area_ha

        # Determine if any plots supply AngleCount objects
        all_angle_counts = [ac for plot in self.plots for ac in plot.AngleCount]
        if all_angle_counts:
            ba_from_angle_count, stems_from_angle_count = AngleCountAggregator(
                all_angle_counts
            ).aggregate_stand_metrics()
            basal_area_metrics: Dict[Any, Union[Stems, StandBasalArea]] = {
                k: v for k, v in ba_from_angle_count.items()
            }
            stems_metrics: Dict[Any, Union[Stems, StandBasalArea]] = {
                k: v for k, v in stems_from_angle_count.items()
            }
            self._metric_estimates["BasalArea"] = basal_area_metrics
            self._metric_estimates["Stems"] = stems_metrics
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

        Usage::

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
                qmd_value = sqrt((40000.0 * ba_obj.value) / (pi * stems_obj.value))
                # Propagate errors:
                # dQ/dBA = 20000 / (pi * stems * QMD)
                # dQ/dStems = - QMD / (2 * stems)
                if qmd_value > 0:
                    dQ_dBA = 20000.0 / (pi * stems_obj.value * qmd_value)
                else:
                    dQ_dBA = 0.0
                dQ_dStems = qmd_value / (2 * stems_obj.value)
                qmd_precision = sqrt(
                    (dQ_dBA * ba_obj.precision) ** 2 + (dQ_dStems * stems_obj.precision) ** 2
                )
            else:
                qmd_value = 0.0
                qmd_precision = 0.0

            qmd_dict[key] = QuadraticMeanDiameter(qmd_value, precision=qmd_precision)

        self._metric_estimates["QMD"] = qmd_dict

    def _compute_ht_estimates(self):
        """
        Compute Horvitz-Thompson style estimates across all plots.
        We'll sum or average the per-plot values for each species:
          - stems/ha
          - basal_area/ha
        Store them in self._metric_estimates:
            {
                "Stems": {TreeName(...): Stems(...), ..., "TOTAL": Stems(...)},
                "BasalArea": {
                    TreeName(...): StandBasalArea(...),
                    ...,
                    "TOTAL": StandBasalArea(...),
                }
            }
        """
        species_data: Dict[TreeName, Dict[str, List[float]]] = {}
        # 1. Gather data from each plot
        for plot in self.plots:
            area_ha = plot.area_ha or 1.0
            # effective area is the visible portion of the plot
            effective_area_ha = (
                area_ha * (1 - plot.occlusion) if (1 - plot.occlusion) > 0 else area_ha
            )

            # Group trees by species
            trees_by_sp: Dict[TreeName, List[Tree]] = {}
            for tr in plot.trees:
                sp = getattr(tr, "species", None)
                if sp is None:
                    continue
                if isinstance(sp, str):
                    sp = parse_tree_species(sp)
                trees_by_sp.setdefault(sp, []).append(tr)

            # For each species in this plot, compute the adjusted stems/ha and BA/ha
            for sp, trlist in trees_by_sp.items():
                stems_count = sum(t.weight_n for t in trlist)
                # Adjusted stems/ha: divide by the effective area
                stems_ha = stems_count / effective_area_ha

                # Compute basal area (m²) for trees in the plot.
                ba_sum = 0.0
                for t in trlist:
                    d_cm = float(t.diameter_cm) if t.diameter_cm is not None else 0.0
                    r_m = (d_cm / 100.0) / 2.0
                    ba_sum += pi * (r_m**2) * t.weight_n
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

            stems_dict[sp] = Stems(value=stems_mean, species=sp, precision=sqrt(stems_var))
            ba_dict[sp] = StandBasalArea(value=ba_mean, species=sp, precision=sqrt(ba_var))

            total_stems_val += stems_mean
            total_stems_var += stems_var
            total_ba_val += ba_mean
            total_ba_var += ba_var

            # "TOTAL" aggregator
        stems_dict["TOTAL"] = Stems(
            value=total_stems_val, species=None, precision=sqrt(total_stems_var)
        )
        ba_dict["TOTAL"] = StandBasalArea(
            value=total_ba_val, species=None, precision=sqrt(total_ba_var)
        )

        self._metric_estimates["Stems"] = {k: v for k, v in stems_dict.items()}
        self._metric_estimates["BasalArea"] = {k: v for k, v in ba_dict.items()}

    def __repr__(self):
        """Return a short textual description of the stand."""
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
        subplots = [p for p in self.plots if isclose(p.area_ha, mode_area_ha, rel_tol=1e-9)]

        if not subplots:
            return None

        # 2. Determine how many top trees with valid heights each subplot can contribute
        #    We'll pick the smallest number of valid-height trees among these subplots
        #    so we can consistently choose the top M from each.
        m_values = []
        for plot in subplots:
            # Sort trees descending by diameter
            sorted_trees = sorted(
                plot.trees, key=lambda t: (t.diameter_cm if t.diameter_cm else -999), reverse=True
            )
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
            sorted_trees = sorted(
                plot.trees, key=lambda t: (t.diameter_cm if t.diameter_cm else -999), reverse=True
            )
            # The top M among those that have heights
            valid_heights = [t.height_m for t in sorted_trees[:m_real] if t.height_m is not None]

            # The original logic intended to skip any plot that could not provide M valid heights.
            # This check preserves that intent.
            if len(valid_heights) < m_real:
                continue

            # Because the "if t.height_m is not None" check is inside the comprehension,
            # Pylance knows that `valid_heights` is of type `list[float]`.
            subplot_mean_h = statistics.mean(valid_heights)

            subplot_means.append(subplot_mean_h)

        if not subplot_means:
            return None

        h_est_raw = statistics.mean(subplot_means)

        # Simple standard error across subplots
        if len(subplot_means) > 1:
            precision_est = statistics.pstdev(subplot_means) / sqrt(len(subplot_means))
        else:
            precision_est = 0.0

        # 4. Use a small Monte Carlo to estimate bias for (r_real, m_real)
        real_radius_m = sqrt(mode_area_ha * 10_000 / pi)
        nominal_top_n = self.top_height_definition.nominal_n
        nominal_area_ha = self.top_height_definition.nominal_area_ha

        bias, _bias_percentage = self.calculate_top_height_bias(
            r=real_radius_m,
            m=m_real,
            n_trees=1000,
            n_simulations=5000,
            nominal_top_n=nominal_top_n,
            nominal_area=nominal_area_ha * 10_000,
            sigma=3.0,
        )

        h_est_corrected = h_est_raw - bias

        # Return a TopHeightMeasurement
        return TopHeightMeasurement(
            value=h_est_corrected,
            definition=self.top_height_definition,
            species=None,  # or you could attempt an aggregated species list
            precision=precision_est,
            est_bias=float(bias),
        )

    @staticmethod
    def calculate_top_height_bias(
        r: float,
        m: int,
        n_trees: int = 1000,
        n_simulations: int = 10000,
        nominal_top_n: int = 100,
        nominal_area: float = 10000.0,
        sigma: float = 3.0,
    ):
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
            side = sqrt(nominal_area)
            x_pos = np.random.uniform(0, side, n_trees)
            y_pos = np.random.uniform(0, side, n_trees)

            # Generate diameters (exponential distribution, mean ~20 cm)
            diameters = np.random.exponential(scale=20.0, size=n_trees)

            # 'True' heights from a toy height-diameter function
            # You can replace this with a more realistic model
            heights_true = 1.3 + (diameters**2) / ((1.1138 + 0.2075 * diameters) ** 2)

            # Add 3% measurement error (for example)
            noise = np.random.normal(0, (sigma / 100.0) * heights_true, n_trees)
            heights_measured = heights_true + noise

            # The "true" top height H_bar in the entire stand is the mean of
            # top nominal_top_n by diameter
            top_indices = np.argsort(diameters)[-nominal_top_n:][::-1]
            H_bar = np.mean(heights_true[top_indices])
            H_bar_list.append(H_bar)

            # Now place a random circular plot of radius r
            center_x = np.random.uniform(r, side - r)
            center_y = np.random.uniform(r, side - r)
            dist = np.sqrt((x_pos - center_x) ** 2 + (y_pos - center_y) ** 2)
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
            self._metric_estimates["Stems"] = {k: v for k, v in stems_dict.items()}
            self._metric_estimates["BasalArea"] = {k: v for k, v in ba_dict.items()}
            self.use_angle_count = True
        else:
            # Otherwise, recompute using the tree-based estimates.
            self._compute_ht_estimates()
            self.use_angle_count = False

        # Invalidate any cached QMD estimates
        if "QMD" in self._metric_estimates:
            del self._metric_estimates["QMD"]

    def thin_trees(
        self,
        uids: Optional[List[Any]] = None,
        rule: Optional[Callable[[Tree], bool]] = None,
        polygon: Optional[Polygon] = None,
    ) -> None:
        """Remove trees from the stand based on various criteria.

        Parameters
        ----------
        uids:
            List of tree ``uid`` values to remove.
        rule:
            Callable that returns ``True`` for trees that should be removed.
        polygon:
            When provided, the rule and/or UIDs are applied only to trees whose
            coordinates fall inside this polygon. If both ``uids`` and ``rule``
            are ``None`` all trees inside the polygon are removed.
        """

        if self.use_angle_count:
            raise ValueError("Thinning not supported when using AngleCount data.")

        for plot in self.plots:
            new_trees = []
            for t in plot.trees:
                within_poly = True
                if polygon is not None:
                    pos = getattr(t, "position", None)
                    if pos is None:
                        within_poly = False
                    else:
                        within_poly = polygon.contains(Point(pos.X, pos.Y))

                remove = False
                if polygon is not None and uids is None and rule is None:
                    remove = within_poly
                else:
                    if uids is not None and getattr(t, "uid", None) in uids:
                        if polygon is None or within_poly:
                            remove = True
                    if rule is not None and rule(t):
                        if polygon is None or within_poly:
                            remove = True

                if not remove:
                    new_trees.append(t)

            plot.trees = new_trees

        self._compute_ht_estimates()
        if "QMD" in self._metric_estimates:
            del self._metric_estimates["QMD"]

    def attach_simulation_ruleset(
        self,
        ruleset: "SimulationRuleset",
        species_remap: Optional[Dict[TreeName, TreeName]] = None,
    ) -> None:
        """Attach a :class:`~pyforestry.base.simulation.SimulationRuleset`.

        Species in the stand are validated against each module in ``ruleset``.
        For the ingrowth module, unsupported species trigger a warning and are
        assumed to produce no ingrowth. For growth, mortality and calamity
        modules a warning is emitted if a species is not supported; a mapping in
        ``species_remap`` can be supplied to translate unsupported species to a
        supported one.

        Parameters
        ----------
        ruleset:
            The ruleset to attach to the stand.
        species_remap:
            Optional mapping from species present in the stand to alternative
            species understood by the ruleset modules.
        """

        species_remap = species_remap or {}

        present_species: Set[TreeName] = set()
        for plot in self.plots:
            for tr in plot.trees:
                sp = getattr(tr, "species", None)
                if sp is None:
                    continue
                if isinstance(sp, str):
                    sp = parse_tree_species(sp)
                present_species.add(sp)

        # Validate ingrowth module support
        for sp in present_species:
            mapped = species_remap.get(sp, sp)
            if not ruleset.ingrowth.supports(mapped):
                warnings.warn(
                    f"Ingrowth module does not support {mapped.full_name}; ingrowth set to zero.",
                    UserWarning,
                    stacklevel=2,
                )

        other_modules = [ruleset.growth, ruleset.mortality]
        if ruleset.calamity is not None:
            other_modules.append(ruleset.calamity)

        for sp in present_species:
            mapped = species_remap.get(sp, sp)
            for mod in other_modules:
                if not mod.supports(mapped):
                    warnings.warn(
                        f"{mod.__class__.__name__} does not support "
                        f"{mapped.full_name} (from {sp.full_name}). "
                        "Provide species_remap to map unsupported species.",
                        UserWarning,
                        stacklevel=2,
                    )

        self.simulation_ruleset = ruleset
