"""Utilities for working with forest stands.

This module defines :class:`Stand`, representing a collection of sample plots and
an optional boundary polygon, along with the :class:`StandMetricAccessor` helper
used to access aggregated stand metrics such as basal area or stem count.
"""

import statistics
import warnings
from dataclasses import dataclass, field
from math import isclose, pi, sqrt
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, cast

import geopandas as gpd
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
from pyforestry.base.helpers.height_models import HeightSourceSpec, resolve_height_source
from pyforestry.base.helpers.primitives import (
    BasalAreaWeightedDiameter,
    LoreysMeanHeight,
    QuadraticMeanDiameter,
    SiteBase,
    StandBasalArea,
    Stems,
    TopHeightDefinition,
    TopHeightMeasurement,
)
from pyforestry.base.helpers.top_height import compute_top_height


def _mean_and_se(values: List[float]) -> Tuple[float, float]:
    """Return the sample mean and standard error of the mean of ``values``.

    The standard error is the sample standard deviation divided by ``sqrt(n)``;
    it is ``0.0`` when fewer than two values are supplied.
    """
    n = len(values)
    if n == 0:
        return 0.0, 0.0
    mean = statistics.mean(values)
    se = sqrt(statistics.variance(values) / n) if n > 1 else 0.0
    return mean, se


def _ratio_and_se(
    numerator: List[float],
    denominator: List[float],
) -> Tuple[float, float]:
    """Ratio of two per-plot means with a covariance-aware standard error.

    Both arguments are the *per-plot series* of the numerator and denominator
    (not their means), because a ratio metric such as Lorey's mean height or the
    basal-area weighted diameter draws both parts from the same trees: they are
    strongly correlated, and treating them as independent invents variance that
    is not there.

    The standard error is the classical ratio-estimator form, which carries that
    correlation exactly::

        SE(R) = sqrt(Var(N_i - R * D_i) / n) / mean(D)

    A stand whose plots all share the same ratio therefore reports a standard
    error of zero, however much the plots differ in density.

    Returns ``(0.0, 0.0)`` when the denominator mean is non-positive (e.g. no
    basal area, or no measured heights for Lorey's mean).
    """
    n = len(numerator)
    if n == 0:
        return 0.0, 0.0
    denominator_mean = statistics.mean(denominator)
    if denominator_mean <= 0:
        return 0.0, 0.0
    ratio = statistics.mean(numerator) / denominator_mean
    if n < 2:
        return ratio, 0.0
    residuals = [num - ratio * den for num, den in zip(numerator, denominator, strict=True)]
    se = sqrt(statistics.variance(residuals) / n) / denominator_mean
    return ratio, se


_D2_PER_BA = 40000.0 / pi  # basal area (m²/ha) -> sum of d² (cm²/ha)

# Per-plot, per-species quantities accumulated once and reused to derive every
# metric: stem count, stem count of trees carrying a diameter, basal area, sum of
# cubed diameters (BAWAD numerator), and the basal-area weighted height sum with
# its matching basal area (Lorey's).
_COMPONENT_KEYS = ("stems", "stems_d", "ba", "d3", "gh", "ba_h")


def _sum_series(
    components: Dict[Any, Dict[str, List[float]]],
    species: List[Any],
) -> Dict[str, List[float]]:
    """Elementwise per-plot sum of the component series over ``species``.

    Summing the series *before* reducing keeps a species group covariance-aware
    in the same way the stand total is: species that trade off against each other
    across plots do not each contribute independent variance.
    """
    n_plots = 0
    for sp in species:
        record = components.get(sp)
        if record is not None:
            n_plots = len(record[_COMPONENT_KEYS[0]])
            break
    summed: Dict[str, List[float]] = {key: [0.0] * n_plots for key in _COMPONENT_KEYS}
    for sp in species:
        record = components.get(sp)
        if record is None:
            continue
        for key in _COMPONENT_KEYS:
            target = summed[key]
            for index, value in enumerate(record[key]):
                target[index] += value
    return summed


def _metrics_from_series(
    series: Dict[str, List[float]],
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Derive the stand metrics and their standard errors from component series.

    ``series`` maps each per-plot component accumulated by
    :meth:`Stand._compute_plot_mean_estimates` (``stems``, ``ba``, ``d3``, ``gh``,
    ``ba_h``) to its per-plot values. Additive metrics come from the plot-to-plot
    mean; the ratio metrics (basal-area weighted diameter, Lorey's mean height)
    go through :func:`_ratio_and_se`, which carries the correlation between their
    numerator and denominator instead of assuming it away.

    Returns a ``(value, precision)`` pair of dicts keyed by metric name.
    """
    stems_mean, stems_se = _mean_and_se(series["stems"])
    ba_mean, ba_se = _mean_and_se(series["ba"])
    bawad, bawad_se = _ratio_and_se(series["d3"], [ba * _D2_PER_BA for ba in series["ba"]])
    hl, hl_se = _ratio_and_se(series["gh"], series["ba_h"])
    return (
        {"stems": stems_mean, "ba": ba_mean, "bawad": bawad, "hl": hl},
        {"stems": stems_se, "ba": ba_se, "bawad": bawad_se, "hl": hl_se},
    )


def _qmd_from_series(series: Dict[str, List[float]]) -> QuadraticMeanDiameter:
    """Quadratic mean diameter from per-plot basal-area and stem series.

    Uses ``stems_d`` -- the stems that actually carry a diameter -- so that the
    numerator and denominator describe the same trees; a record with no diameter
    contributes no basal area and must not enter the count either.

    ``QMD = sqrt(40000/pi * R)`` for the mean basal area per stem ``R``, so the
    standard error is obtained by propagating through that square root from
    :func:`_ratio_and_se`. Going via the ratio rather than combining the two
    standard errors and their covariance term by term avoids the cancellation
    those three near-equal terms suffer: a stand whose plots share one QMD
    reports exactly zero here instead of a small numerical residue.
    """
    stems_key = "stems_d" if "stems_d" in series else "stems"
    ratio, ratio_se = _ratio_and_se(series["ba"], series[stems_key])
    if ratio <= 0:
        return QuadraticMeanDiameter(0.0, precision=0.0)
    qmd_value = sqrt(_D2_PER_BA * ratio)
    qmd_se = qmd_value / (2.0 * ratio) * ratio_se
    return QuadraticMeanDiameter(qmd_value, precision=qmd_se)


def _qmd_from_components(
    ba_mean: float,
    ba_se: float,
    stems_mean: float,
    stems_se: float,
) -> QuadraticMeanDiameter:
    """Quadratic mean diameter (cm) from basal-area and stem means, with its SE.

    ``QMD = sqrt(40000 * BA / (pi * N))``; the standard error is propagated from
    the basal-area and stem standard errors by the delta method.

    This form treats the two as independent, which overstates the error because
    basal area and stem count rise and fall together across plots. It is only for
    callers that have nothing but the reduced means -- angle-count stands, where
    basal area comes from the tally and stems from the recorded diameters. Where
    the per-plot series survive, :func:`_qmd_from_series` is both covariance-aware
    and numerically better behaved.
    """
    if stems_mean > 0 and ba_mean > 0:
        qmd_value = sqrt((40000.0 * ba_mean) / (pi * stems_mean))
        d_qmd_d_ba = 20000.0 / (pi * stems_mean * qmd_value)
        d_qmd_d_stems = qmd_value / (2 * stems_mean)
        qmd_se = sqrt((d_qmd_d_ba * ba_se) ** 2 + (d_qmd_d_stems * stems_se) ** 2)
    else:
        qmd_value = 0.0
        qmd_se = 0.0
    return QuadraticMeanDiameter(qmd_value, precision=qmd_se)


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
        """Compute or refresh the plot-mean estimates if not done."""
        if self._metric_name not in self._stand._metric_estimates:
            if not self._stand.use_angle_count:
                self._stand._compute_plot_mean_estimates()
            else:
                raise KeyError(f"{self._metric_name} metric unavailable for angle-count data")

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

    def group(self, species=None, *, predicate=None):
        """Aggregate this metric over a group of species.

        Parameters
        ----------
        species:
            Either an iterable of species to include (each a :class:`TreeName`
            or a species-name string), or a predicate ``callable(TreeName) ->
            bool`` (a predicate may be passed positionally for convenience).
        predicate:
            A ``callable(TreeName) -> bool`` selecting species to include. A
            species is included if it matches ``species`` *or* ``predicate``.

        Returns
        -------
        The same value type this accessor exposes (:class:`StandBasalArea`,
        :class:`Stems`, :class:`QuadraticMeanDiameter`,
        :class:`BasalAreaWeightedDiameter` or :class:`LoreysMeanHeight`),
        aggregated over the selected species. Additive metrics (basal area,
        stems) are summed with standard errors combined in quadrature; ratio
        metrics (QMD, BAWAD, HL) are recomputed from the selected species'
        component sums.

        Examples
        --------
        Conifers only::

            stand.BasalArea.group(lambda s: s.tree_type == "Coniferous")

        An explicit species list::

            stand.Stems.group(["pinus sylvestris", "picea abies"])
        """
        if callable(species) and predicate is None:
            predicate = species
            species = None
        if species is None and predicate is None:
            raise ValueError("group() requires a species iterable or a predicate.")

        self._ensure_estimates()
        components = self._stand._species_components

        wanted = None
        if species is not None:
            wanted = {parse_tree_species(sp) if isinstance(sp, str) else sp for sp in species}

        # Candidate species come from the component cache (tree-list stands) or,
        # failing that, from the metric dict keys (e.g. angle-count stands).
        if components:
            candidates: List[TreeName] = list(components.keys())
        else:
            candidates = [
                k
                for k in self._stand._metric_estimates.get(self._metric_name, {})
                if isinstance(k, TreeName)
            ]

        selected = [
            sp
            for sp in candidates
            if (wanted is not None and sp in wanted) or (predicate is not None and predicate(sp))
        ]
        species_list = selected or None
        name = self._metric_name

        if components:
            group_series = _sum_series(components, selected)
            if name == "QMD":
                return _qmd_from_series(group_series)
            value, precision = _metrics_from_series(group_series)
            if name == "Stems":
                return Stems(
                    value=value["stems"], species=species_list, precision=precision["stems"]
                )
            if name == "BasalArea":
                return StandBasalArea(
                    value=value["ba"], species=species_list, precision=precision["ba"]
                )
            if name == "BAWAD":
                return BasalAreaWeightedDiameter(value["bawad"], precision=precision["bawad"])
            if name == "HL":
                return LoreysMeanHeight(value["hl"], precision=precision["hl"])

        # Fallback for stands without a component cache (e.g. angle-count):
        # only the additive metrics can be re-summed from stored values.
        metric_dict = self._stand._metric_estimates.get(name, {})
        if name in ("Stems", "BasalArea"):
            mean_total = 0.0
            var_total = 0.0
            for sp in selected:
                obj = metric_dict.get(sp)
                if obj is None:
                    continue
                mean_total += float(obj)
                var_total += getattr(obj, "precision", 0.0) ** 2
            cls = Stems if name == "Stems" else StandBasalArea
            return cls(value=mean_total, species=species_list, precision=sqrt(var_total))
        raise KeyError(
            f"Group aggregation of {name} is unavailable for this stand "
            "(it needs per-species component data)."
        )

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
    # Per-species *per-plot* component series, cached by ``_compute_plot_mean_estimates``
    # so that species-group queries and QMD can be rebuilt from the raw plot
    # values rather than from already-reduced means. Keeping the series is what
    # lets ratio metrics and groups carry their covariance instead of assuming
    # independence. Maps species -> {component: [value per plot]}.
    _species_components: Dict[Any, Dict[str, List[float]]] = field(
        default_factory=dict,
        init=False,
    )
    # The same series summed over every species, i.e. the stand total per plot.
    _total_components: Dict[str, List[float]] = field(
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
            self._apply_angle_count_metrics(all_angle_counts)
        else:
            self.use_angle_count = False

    def _apply_angle_count_metrics(self, all_angle_counts: List[Any]) -> None:
        """Populate basal-area (and, if derivable, stem) estimates from tallies.

        Basal area is always available from angle-count sampling. Stems/ha are
        only produced when the tallies carry per-tree diameters (see
        :meth:`AngleCount.__init__`); otherwise the ``"Stems"`` metric is left
        unset so the accessor reports it as unavailable rather than returning a
        physically meaningless tally count.
        """
        ba_by_sp, stems_by_sp = AngleCountAggregator(all_angle_counts).aggregate_stand_metrics()

        ba_dict: Dict[Any, Union[Stems, StandBasalArea]] = dict(ba_by_sp)
        ba_dict["TOTAL"] = StandBasalArea(
            value=sum(float(v) for v in ba_by_sp.values()),
            species=None,
            precision=sqrt(sum(getattr(v, "precision", 0.0) ** 2 for v in ba_by_sp.values())),
        )
        self._metric_estimates["BasalArea"] = ba_dict

        if stems_by_sp:
            stems_dict: Dict[Any, Union[Stems, StandBasalArea]] = dict(stems_by_sp)
            stems_dict["TOTAL"] = Stems(
                value=sum(float(v) for v in stems_by_sp.values()),
                species=None,
                precision=sqrt(
                    sum(getattr(v, "precision", 0.0) ** 2 for v in stems_by_sp.values())
                ),
            )
            self._metric_estimates["Stems"] = stems_dict
        else:
            self._metric_estimates.pop("Stems", None)

        # QMD is derived from stems; drop any stale value. The per-plot component
        # series belong to the tree-list path and must not survive a switch to
        # angle-count data, or QMD would be rebuilt from the wrong stand.
        self._metric_estimates.pop("QMD", None)
        self._species_components = {}
        self._total_components = {}
        self.use_angle_count = True

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

    @property
    def BAWAD(self) -> StandMetricAccessor:
        """Access the stand's basal-area weighted mean diameter."""
        return StandMetricAccessor(self, "BAWAD")

    @property
    def HL(self) -> StandMetricAccessor:
        """Access the stand's Lorey's (basal-area weighted) mean height, in metres.

        Only trees carrying a measured ``height_m`` contribute, so ``HL`` is the
        basal-area weighted mean of the measured heights::

            stand.HL.TOTAL               -> LoreysMeanHeight for the whole stand
            stand.HL(TreeSpecies(...))   -> species-level Lorey's mean height
            float(stand.HL)              -> numeric total value (metres)
        """
        return StandMetricAccessor(self, "HL")

    def _ensure_qmd_estimates(self):
        """
        Ensure that QMD estimates are computed.
        QMD is computed from the existing BasalArea and Stems estimates.
        """
        if "QMD" in self._metric_estimates:
            return
        if self.use_angle_count:
            # BA/Stems come from the angle-count aggregator; QMD needs stems,
            # which are only available when the tallies carry diameters.
            if "Stems" not in self._metric_estimates:
                raise KeyError(
                    "QMD is unavailable for angle-count data without per-tally "
                    "diameters (no stem estimate)."
                )
        elif "BasalArea" not in self._metric_estimates or "Stems" not in self._metric_estimates:
            self._compute_plot_mean_estimates()
        self._compute_qmd_estimates()

    def _compute_qmd_estimates(self):
        """
        Compute Quadratic Mean Diameter (QMD) estimates for each species (and total)
        from the existing basal area and stems estimates.

        Where the per-plot component series are available (tree-list stands) the
        standard error carries the basal-area/stem covariance; angle-count stands
        keep only reduced means, so their QMD falls back to assuming the two are
        independent, which is conservative.
        """
        ba_dict = self._metric_estimates["BasalArea"]
        stems_dict = self._metric_estimates["Stems"]
        components = self._species_components

        qmd_dict = {}
        for key in ba_dict:
            series = self._total_components if key == "TOTAL" else components.get(key)
            if series:
                qmd_dict[key] = _qmd_from_series(series)
            else:
                qmd_dict[key] = _qmd_from_components(
                    ba_dict[key].value,
                    ba_dict[key].precision,
                    stems_dict[key].value,
                    stems_dict[key].precision,
                )
        self._metric_estimates["QMD"] = qmd_dict

    def _compute_plot_mean_estimates(self):
        """Compute per-hectare stand estimates as the mean over all plots.

        A single pass over every plot's trees accumulates, per species, the
        per-hectare stem count, basal area, sum of cubed diameters (for BAWAD)
        and basal-area-weighted height sum (for Lorey's mean height). Species
        absent from a plot contribute an explicit zero for that plot, so the
        cross-plot mean divides by the number of plots -- not merely the plots
        where the species happens to occur (which would over-count both the
        species and the stand total).

        The reported ``precision`` of every metric is the standard error of the
        stand mean (plot-to-plot sample standard deviation divided by sqrt(n)),
        consistent with :class:`AngleCountAggregator`. It is a *between-plot*
        error only: it does not include measurement or model error, so a metric
        built on curve-imputed heights still reports a measured-quality error.
        Stand totals, species groups and ratio metrics are all reduced from the
        per-plot series, so between-species and numerator/denominator covariance
        is carried rather than assumed away.

        Results are stored in ``self._metric_estimates`` under ``"Stems"``,
        ``"BasalArea"``, ``"BAWAD"`` and ``"HL"`` (each mapping species -> value
        plus a ``"TOTAL"`` entry). The per-plot component series are cached in
        ``self._species_components`` / ``self._total_components`` so group and
        QMD queries can be rebuilt from the raw plot values.
        """
        component_keys = _COMPONENT_KEYS
        missing_diameter = 0

        # 1. Single pass over each plot: per-species per-hectare component sums.
        species_order: List[TreeName] = []
        seen: set = set()
        per_plot_species: List[Dict[TreeName, Dict[str, float]]] = []
        per_plot_total: List[Dict[str, float]] = []

        for plot in self.plots:
            area_ha = plot.area_ha or 1.0
            # effective area is the visible portion of the plot
            effective_area_ha = (
                area_ha * (1 - plot.occlusion) if (1 - plot.occlusion) > 0 else area_ha
            )

            plot_acc: Dict[TreeName, Dict[str, float]] = {}
            for tr in plot.trees:
                sp = getattr(tr, "species", None)
                if sp is None:
                    continue
                if isinstance(sp, str):
                    sp = parse_tree_species(sp)

                weight = float(tr.weight_n) if tr.weight_n is not None else 1.0
                has_diameter = tr.diameter_cm is not None
                d_cm = float(tr.diameter_cm) if has_diameter else 0.0
                g_m2 = pi * ((d_cm / 100.0) / 2.0) ** 2  # basal area of one stem

                acc = plot_acc.get(sp)
                if acc is None:
                    acc = {k: 0.0 for k in component_keys}
                    plot_acc[sp] = acc
                # A record with no diameter is still a stem, but it can carry no
                # basal area. Counting it in the QMD/BAWAD denominators as if it
                # were a zero-diameter tree would drag both downwards, so the
                # diameter-derived metrics use their own stem count.
                acc["stems"] += weight
                if not has_diameter:
                    missing_diameter += 1
                    continue
                acc["stems_d"] += weight
                acc["ba"] += g_m2 * weight
                acc["d3"] += (d_cm**3) * weight
                # Lorey's mean height weights only trees carrying a height.
                height_m = getattr(tr, "height_m", None)
                if height_m is not None:
                    acc["gh"] += g_m2 * float(height_m) * weight
                    acc["ba_h"] += g_m2 * weight

            # Convert this plot's accumulators to per-hectare and record.
            plot_species: Dict[TreeName, Dict[str, float]] = {}
            plot_total = {k: 0.0 for k in component_keys}
            for sp, acc in plot_acc.items():
                per_ha = {k: acc[k] / effective_area_ha for k in component_keys}
                plot_species[sp] = per_ha
                for k in component_keys:
                    plot_total[k] += per_ha[k]
                if sp not in seen:
                    seen.add(sp)
                    species_order.append(sp)
            per_plot_species.append(plot_species)
            per_plot_total.append(plot_total)

        if missing_diameter:
            warnings.warn(
                f"{missing_diameter} tree record(s) have no diameter_cm; they are counted "
                "in Stems but contribute no basal area, and are excluded from QMD and "
                "BAWAD so those stay consistent with the trees they describe.",
                stacklevel=2,
            )

        # 2. Per-species cross-plot component series (absent plot contributes 0).
        def component_series(sp: TreeName, key: str) -> List[float]:
            """Per-plot values of ``key`` for ``sp`` (0.0 where the species is absent)."""
            series = []
            for plot_species in per_plot_species:
                record = plot_species.get(sp)
                series.append(record[key] if record is not None else 0.0)
            return series

        stems_dict: Dict[Union[TreeName, str], Stems] = {}
        ba_dict: Dict[Union[TreeName, str], StandBasalArea] = {}
        bawad_dict: Dict[Union[TreeName, str], BasalAreaWeightedDiameter] = {}
        hl_dict: Dict[Union[TreeName, str], LoreysMeanHeight] = {}
        components: Dict[Any, Dict[str, List[float]]] = {}

        for sp in species_order:
            components[sp] = {key: component_series(sp, key) for key in component_keys}

        # The stand total is the per-plot sum over species, which is exactly the
        # elementwise sum of the per-species series, so both are built by the
        # same helper and both stay covariance-aware.
        total_series = {
            key: [plot_total[key] for plot_total in per_plot_total] for key in component_keys
        }

        for sp in species_order:
            value, precision = _metrics_from_series(components[sp])
            stems_dict[sp] = Stems(value=value["stems"], species=sp, precision=precision["stems"])
            ba_dict[sp] = StandBasalArea(value=value["ba"], species=sp, precision=precision["ba"])
            bawad_dict[sp] = BasalAreaWeightedDiameter(
                value["bawad"], precision=precision["bawad"]
            )
            hl_dict[sp] = LoreysMeanHeight(value["hl"], precision=precision["hl"])

        total_value, total_precision = _metrics_from_series(total_series)
        stems_dict["TOTAL"] = Stems(
            value=total_value["stems"], species=None, precision=total_precision["stems"]
        )
        ba_dict["TOTAL"] = StandBasalArea(
            value=total_value["ba"], species=None, precision=total_precision["ba"]
        )
        bawad_dict["TOTAL"] = BasalAreaWeightedDiameter(
            total_value["bawad"], precision=total_precision["bawad"]
        )
        hl_dict["TOTAL"] = LoreysMeanHeight(total_value["hl"], precision=total_precision["hl"])

        self._metric_estimates["Stems"] = stems_dict
        self._metric_estimates["BasalArea"] = ba_dict
        self._metric_estimates["BAWAD"] = bawad_dict
        self._metric_estimates["HL"] = hl_dict
        self._species_components = components
        self._total_components = total_series

    def __repr__(self):
        """Return a short textual description of the stand."""
        return f"Stand(area_ha={self.area_ha}, n_plots={len(self.plots)})"

    def get_dominant_height(self) -> Optional[TopHeightMeasurement]:
        """Compute a simple stand-level 'dominant height' (aka top height).

        This is the straightforward estimator: within the most common plot area,
        take the ``m`` thickest measured-height trees per plot (``m`` being the
        smallest such count across those plots), average their heights, and
        average across plots. No small-area bias correction is applied.

        For a selectable estimator -- García's (1998) selection-corrected
        order-statistic estimators for variable plot sizes, or a plain mean of
        the ``n`` tallest/widest trees -- use :meth:`estimate_top_height`.

        Returns
        -------
        TopHeightMeasurement | None
            The best estimate of top height in meters, along with metadata.
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
                plot.trees, key=lambda t: t.diameter_cm if t.diameter_cm else -999, reverse=True
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
                plot.trees, key=lambda t: t.diameter_cm if t.diameter_cm else -999, reverse=True
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

        # Standard error of the stand mean, on the same sample-variance basis as
        # every other metric here (population sigma would understate it).
        h_est_raw, precision_est = _mean_and_se(subplot_means)

        # Return the definition-based estimate directly. The previous
        # Monte-Carlo "Matérn" small-area bias correction was removed: it drew a
        # synthetic stand unrelated to the observed trees, used an unseeded RNG
        # (so repeated calls disagreed) and was costly, so it could not be
        # justified as a general correction. See estimate_top_height() for
        # principled, source-backed alternatives.
        return TopHeightMeasurement(
            value=h_est_raw,
            definition=self.top_height_definition,
            species=None,  # or you could attempt an aggregated species list
            precision=precision_est,
            est_bias=0.0,
        )

    def estimate_top_height(
        self,
        reference: str = "garcia_u",
        height_source: HeightSourceSpec = "measured",
        *,
        n: Optional[int] = None,
        by: str = "diameter",
        percentile: float = 90.0,
        k: float = 3.0,
        naslund_exponent: Union[int, float, str] = 2,
    ) -> Optional[TopHeightMeasurement]:
        """Estimate stand top height with a selectable estimator, over all plots.

        This is the flexible counterpart to :meth:`get_dominant_height`. The
        ``reference`` chooses what "the top" is and ``height_source`` chooses how
        heights are obtained; they are composed per plot and averaged over all
        plots. See
        :func:`pyforestry.base.helpers.top_height.compute_top_height` for the
        full description of each ``reference`` (``"mean_of_largest"``,
        ``"garcia_u"``, ``"garcia_pp"``, ``"percentile"``,
        ``"mean_plus_k_sigma"``) and ``height_source`` (``"measured"``,
        ``"naslund"``, a callable, or a fitted curve).

        The stand's :attr:`top_height_definition` supplies ``nominal_n`` /
        ``nominal_area_ha`` (the reference area used by the García methods).

        Returns
        -------
        TopHeightMeasurement | None
            The estimated top height (metres), or ``None`` if no plot could
            contribute an estimate.
        """
        return compute_top_height(
            self.plots,
            reference=reference,
            height_source=height_source,
            n=n,
            by=by,
            percentile=percentile,
            k=k,
            definition=self.top_height_definition,
            naslund_exponent=naslund_exponent,
        )

    def impute_heights(
        self,
        source: HeightSourceSpec = "naslund",
        *,
        which: str = "missing",
        overwrite: bool = False,
        naslund_exponent: Union[int, float, str] = 2,
    ) -> int:
        """Assign interpolated heights to trees from a height-diameter curve.

        The imputed values are written to each tree's ``predicted_height_m`` and
        are kept distinct from measured ``height_m`` (which is never modified),
        so a modelled height is never mistaken for a measurement.

        Parameters
        ----------
        source:
            A *curve* height source: ``"naslund"`` (fit from the stand's measured
            height-diameter pairs), a callable ``f(diameter_cm) -> height_m``, or
            a :class:`~pyforestry.base.helpers.height_models.NaslundHeightCurve`.
            A measured source is rejected -- there is nothing to impute from.
        which:
            ``"missing"`` (default) imputes only trees lacking a measured height;
            ``"all"`` imputes every tree that has a diameter.
        overwrite:
            When ``True``, replace an existing ``predicted_height_m``; otherwise
            keep any value already present.
        naslund_exponent:
            Exponent for the ``"naslund"`` fit. Defaults to 2.

        Returns
        -------
        int
            The number of trees assigned a predicted height.

        Raises
        ------
        ValueError
            If the source cannot be resolved/fit, or if it is not a curve.
        """
        all_trees = [tree for plot in self.plots for tree in plot.trees]
        height_source = resolve_height_source(source, all_trees, naslund_exponent=naslund_exponent)
        if height_source is None:
            measured = sum(
                1
                for tree in all_trees
                if getattr(tree, "height_m", None) is not None
                and getattr(tree, "diameter_cm", None) is not None
            )
            raise ValueError(
                "Could not fit the requested height source from "
                f"{measured} usable measured height-diameter pair(s). A Näslund fit "
                "needs at least two pairs that are well clear of breast height and "
                "that span a range of diameters; a set that is degenerate (one single "
                "diameter) or that implies a non-monotone curve is rejected."
            )
        if not height_source.is_curve:
            raise ValueError(
                "impute_heights requires a curve height source (Näslund or a "
                "callable), not measured heights."
            )

        count = 0
        for tree in all_trees:
            if which == "missing" and getattr(tree, "height_m", None) is not None:
                continue
            if not overwrite and getattr(tree, "predicted_height_m", None) is not None:
                continue
            diameter = getattr(tree, "diameter_cm", None)
            if diameter is None:
                continue
            predicted = height_source.height_at_diameter(float(diameter))
            if predicted is not None:
                tree.predicted_height_m = predicted
                count += 1
        return count

    def append_plot(self, plot: CircularPlot) -> None:
        """
        Append a new plot to the stand and recalculate the stand-level metrics.
        If any plot in the updated stand has AngleCount data, those estimates take precedence.
        """
        self.plots.append(plot)

        # Gather all AngleCount records from all plots.
        all_angle_counts = [ac for p in self.plots for ac in p.AngleCount]

        if all_angle_counts:
            # Use the AngleCount aggregator (adds TOTAL, omits stems if the
            # tallies carry no diameters).
            self._apply_angle_count_metrics(all_angle_counts)
        else:
            # Otherwise, recompute using the tree-based estimates.
            self._compute_plot_mean_estimates()
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

        self._compute_plot_mean_estimates()
        if "QMD" in self._metric_estimates:
            del self._metric_estimates["QMD"]
