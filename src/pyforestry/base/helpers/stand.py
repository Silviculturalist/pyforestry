"""Utilities for working with forest stands.

This module defines :class:`Stand`, representing a collection of sample plots and
an optional boundary polygon, along with the :class:`StandMetricAccessor` helper
used to access aggregated stand metrics such as basal area or stem count.
"""

import statistics
from dataclasses import dataclass, field
from math import isclose, pi, sqrt
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Mapping,
    Optional,
    Union,
    cast,
)

if TYPE_CHECKING:  # pragma: no cover - import cycle: imputation reaches helpers
    from pyforestry.base.imputation.registry import ImputerSpec

import geopandas as gpd
from pyproj import CRS
from shapely import Polygon
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry

# The plot-to-stand estimator lives in pyforestry.base.aggregation so that the
# simulation runtime reduces plots to metrics through exactly the same code this
# class does. It used to carry its own copy, and the two disagreed. The private
# aliases keep this module's internals reading as before.
from pyforestry.base.aggregation import (
    aggregate_plots as _aggregate_plots,
)
from pyforestry.base.aggregation import (
    mean_and_se as _mean_and_se,
)
from pyforestry.base.aggregation import (
    metrics_from_series as _metrics_from_series,
)
from pyforestry.base.aggregation import (
    qmd_from_components as _qmd_from_components,
)
from pyforestry.base.aggregation import (
    qmd_from_series as _qmd_from_series,
)
from pyforestry.base.aggregation import (
    sum_series as _sum_series,
)
from pyforestry.base.helpers import (
    AngleCountAggregator,
    CircularPlot,
    Tree,
    TreeName,
    parse_tree_species,
)
from pyforestry.base.helpers.height_models import HeightSourceSpec
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

#: How a stand stores what it knows. ``tree_list`` and ``angle_count`` are
#: measurements; ``diameter_class`` and ``aggregate`` are reduced forms a model
#: may work in. The metric accessors read the same way whichever is active --
#: which representation is in use decides how ``_metric_estimates`` is filled,
#: not what a caller may ask for.
Representation = Literal["tree_list", "angle_count", "diameter_class", "aggregate"]


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

    @property
    def TOTAL(self) -> Any:
        """The whole-stand value of this metric, with its standard error.

        ``stand.BasalArea.TOTAL`` is the first line of code most users of this
        package run, and it used to resolve through ``__getattr__`` -- so no
        editor could complete it, no type checker could see it, and the only way
        to learn the name was to read the source. It is an ordinary property.

        The concrete type follows the metric: :class:`StandBasalArea` for
        ``BasalArea``, :class:`Stems` for ``Stems``, and so on. Each is a ``float``
        subclass, so it can be used directly in arithmetic and carries
        ``.value``/``.precision`` alongside.
        """
        self._ensure_estimates()
        return self._stand._metric_estimates[self._metric_name]["TOTAL"]

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
    #: Which representation currently holds this stand's state. Set by
    #: ``__post_init__`` for measured stands and by the ``from_*`` constructors
    #: and mutators for the reduced ones.
    representation: Representation = field(default="tree_list", init=False)
    #: Diameter-class inventory, species -> {"bin_mids_cm": [...], "n_per_ha": [...]}.
    #: Populated only in ``diameter_class`` representation.
    _diameter_classes: Dict[Any, Dict[str, List[float]]] = field(
        default_factory=dict,
        init=False,
    )

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
        self.representation = "angle_count"

    # ------------------------------------------------------------------
    # Reduced representations
    # ------------------------------------------------------------------
    #
    # A stand does not always hold trees. A model may need diameter classes, or
    # only stand totals, and once it steps them the result is still the stand's
    # state -- so it lives here, next to the estimator, rather than in a second
    # object that reports the same quantities from its own arithmetic.

    @classmethod
    def from_aggregate_metrics(
        cls,
        metrics: Mapping[str, Mapping[Any, Any]],
        *,
        site: Optional[SiteBase] = None,
        area_ha: Optional[float] = None,
        top_height_definition: Optional[TopHeightDefinition] = None,
    ) -> "Stand":
        """Build a stand from per-hectare totals rather than from plots.

        ``metrics`` maps ``"BasalArea"`` and ``"Stems"`` to species -> value
        mappings, each optionally carrying a ``"TOTAL"``; a missing total is
        summed from the species entries. QMD is derived, never supplied.
        """
        stand = cls(
            site=site,
            area_ha=area_ha,
            top_height_definition=top_height_definition or TopHeightDefinition(),
        )
        stand.representation = "aggregate"
        stand.set_species_metrics(
            basal_area=metrics.get("BasalArea", {}),
            stems=metrics.get("Stems", {}),
        )
        return stand

    @classmethod
    def from_diameter_classes(
        cls,
        diameter_classes: Mapping[Any, Mapping[str, List[float]]],
        *,
        site: Optional[SiteBase] = None,
        area_ha: Optional[float] = None,
        top_height_definition: Optional[TopHeightDefinition] = None,
    ) -> "Stand":
        """Build a stand from a binned diameter distribution.

        ``diameter_classes`` maps species to ``{"bin_mids_cm": [...],
        "n_per_ha": [...]}``; the two arrays must be the same length.
        """
        stand = cls(
            site=site,
            area_ha=area_ha,
            top_height_definition=top_height_definition or TopHeightDefinition(),
        )
        stand.representation = "diameter_class"
        stand.set_diameter_classes(diameter_classes)
        return stand

    def _require_representation(self, method: str, *allowed: Representation) -> None:
        """Reject a write the next metric refresh would silently undo.

        In ``tree_list``/``angle_count``/``diameter_class`` the metrics are a
        *view* of the inventory and are rebuilt from it on refresh, so writing
        totals directly in one of those looks like it worked and is then
        discarded -- a model keeping its state elsewhere and publishing through
        :meth:`set_aggregate_metrics` had its whole growth step reverted.
        """
        if self.representation not in allowed:
            names = ", ".join(repr(name) for name in allowed)
            raise RuntimeError(
                f"Stand.{method} requires representation in {{{names}}}, got "
                f"{self.representation!r}. In {self.representation!r} the metrics are "
                f"derived from the inventory and are rebuilt on the next refresh, so "
                f"this write would be silently discarded. Update the inventory instead "
                f"(the plots, or set_diameter_classes), or build the stand with "
                f"Stand.from_aggregate_metrics."
            )

    def set_aggregate_metrics(self, *, ba_total: float, stems_total: float) -> None:
        """Replace the stand totals, dropping any species detail.

        QMD is re-derived from the two. Use :meth:`set_species_metrics` when the
        per-species breakdown is known.

        Raises:
            RuntimeError: If the stand is not in ``aggregate`` representation.
        """
        self._require_representation("set_aggregate_metrics", "aggregate")
        self._metric_estimates["BasalArea"] = {
            "TOTAL": StandBasalArea(ba_total, species=None, precision=0.0)
        }
        self._metric_estimates["Stems"] = {
            "TOTAL": Stems(stems_total, species=None, precision=0.0)
        }
        self._derive_aggregate_qmd()

    def set_species_metrics(
        self,
        *,
        basal_area: Mapping[Any, Any],
        stems: Mapping[Any, Any],
    ) -> None:
        """Replace the aggregate metrics with a per-species breakdown.

        A supplied ``"TOTAL"`` is taken as given; it is summed from the species
        entries only when absent. The breakdown a stand carries is often partial
        -- basal area known per species from an angle count, stems only for the
        species that were tallied -- so forcing the total to equal the sum would
        silently shrink such a stand. The caller knows whether its breakdown is
        complete; this method does not.

        QMD *is* derived here, per species and for the total, because that
        derivation is the same arithmetic everywhere and having each model repeat
        it is how the two copies came to disagree. A species with no basal area or
        no stems gets no QMD, so the metric is never reported for a species it
        cannot be defined for.

        Raises:
            RuntimeError: If the stand is not in ``aggregate`` representation.
        """
        self._require_representation("set_species_metrics", "aggregate")

        ba_dict: Dict[Any, Any] = {}
        summed_ba = 0.0
        for key, value in basal_area.items():
            if key == "TOTAL":
                continue
            ba_dict[key] = StandBasalArea(
                float(value),
                species=getattr(value, "species", None) or key,
                precision=getattr(value, "precision", 0.0),
                over_bark=getattr(value, "over_bark", True),
                direct_estimate=getattr(value, "direct_estimate", True),
            )
            summed_ba += float(value)

        stems_dict: Dict[Any, Any] = {}
        summed_stems = 0.0
        for key, value in stems.items():
            if key == "TOTAL":
                continue
            stems_dict[key] = Stems(
                float(value),
                species=getattr(value, "species", None) or key,
                precision=getattr(value, "precision", 0.0),
            )
            summed_stems += float(value)

        total_ba = float(basal_area["TOTAL"]) if "TOTAL" in basal_area else summed_ba
        total_stems = float(stems["TOTAL"]) if "TOTAL" in stems else summed_stems
        ba_dict["TOTAL"] = StandBasalArea(total_ba, species=None, precision=0.0)
        stems_dict["TOTAL"] = Stems(total_stems, species=None, precision=0.0)

        self._metric_estimates["BasalArea"] = ba_dict
        self._metric_estimates["Stems"] = stems_dict

        qmd_dict: Dict[Any, Any] = {}
        for key, ba in ba_dict.items():
            n = stems_dict.get(key)
            if n is None or float(n) <= 0.0 or float(ba) <= 0.0:
                continue
            qmd_dict[key] = QuadraticMeanDiameter(
                sqrt((40000.0 * float(ba)) / (pi * float(n))), precision=0.0
            )
        qmd_dict.setdefault("TOTAL", QuadraticMeanDiameter(0.0, precision=0.0))
        self._metric_estimates["QMD"] = qmd_dict

    def scale_stems(self, factor: float) -> None:
        """Scale the stand totals by ``factor``, clamping at zero.

        Raises:
            RuntimeError: If the stand is not in ``aggregate`` representation.
        """
        self._require_representation("scale_stems", "aggregate")
        total_n = float(self._metric_estimates["Stems"]["TOTAL"])
        total_ba = float(self._metric_estimates["BasalArea"]["TOTAL"])
        self.set_aggregate_metrics(
            ba_total=max(0.0, total_ba * factor),
            stems_total=max(0.0, total_n * factor),
        )

    @property
    def diameter_classes(self) -> Dict[Any, Dict[str, List[float]]]:
        """The diameter-class inventory, keyed by species.

        Each entry holds ``bin_mids_cm`` and a matching ``n_per_ha``. This is a
        copy: mutate it freely and hand it back through
        :meth:`set_diameter_classes`, which revalidates and refreshes the metrics.

        Raises:
            RuntimeError: If the stand is not in ``diameter_class`` representation.
        """
        self._require_representation("diameter_classes", "diameter_class")
        return {
            key: {name: list(values) for name, values in record.items()}
            for key, record in self._diameter_classes.items()
        }

    def set_diameter_classes(
        self, diameter_classes: Mapping[Any, Mapping[str, List[float]]]
    ) -> None:
        """Replace the diameter-class inventory and recompute the metrics.

        Raises:
            RuntimeError: If the stand is not in ``diameter_class`` representation.
            ValueError: If a species' ``bin_mids_cm`` and ``n_per_ha`` differ in length.
        """
        self._require_representation("set_diameter_classes", "diameter_class")
        normalized: Dict[Any, Dict[str, List[float]]] = {}
        for key, record in diameter_classes.items():
            mids = list(record.get("bin_mids_cm", []))
            counts = list(record.get("n_per_ha", []))
            if len(mids) != len(counts):
                raise ValueError(
                    f"Diameter-class arrays length mismatch for {key}: "
                    f"{len(mids)} bin midpoints against {len(counts)} counts."
                )
            normalized[key] = {"bin_mids_cm": mids, "n_per_ha": counts}
        self._diameter_classes = normalized
        self._compute_diameter_class_estimates()

    def refresh_metrics(self) -> None:
        """Rebuild the metric estimates from whichever representation is active.

        A no-op for ``aggregate``, where the metrics *are* the state; for the
        others they are a view of an inventory that a step may have changed.
        """
        if self.representation == "tree_list":
            self._compute_plot_mean_estimates()
            self._metric_estimates.pop("QMD", None)
        elif self.representation == "angle_count":
            tallies = [ac for plot in self.plots for ac in plot.AngleCount]
            if tallies:
                self._apply_angle_count_metrics(tallies)
        elif self.representation == "diameter_class":
            self._compute_diameter_class_estimates()
        # "aggregate": the metrics are the state; nothing to recompute.

    def _derive_aggregate_qmd(self) -> None:
        """Set the total QMD from the stored total basal area and stems."""
        try:
            ba = float(self._metric_estimates["BasalArea"]["TOTAL"])
            n = float(self._metric_estimates["Stems"]["TOTAL"])
            value = sqrt((40000.0 * ba) / (pi * n)) if (ba > 0.0 and n > 0.0) else 0.0
        except KeyError:
            value = 0.0
        self._metric_estimates["QMD"] = {"TOTAL": QuadraticMeanDiameter(value, precision=0.0)}

    def _compute_diameter_class_estimates(self) -> None:
        """Reduce the diameter-class inventory to stems, basal area and QMD.

        Each class contributes ``n_per_ha`` stems at the bin midpoint's basal
        area. There is no sampling error to report -- a binned distribution is
        already a reduction -- so every ``precision`` here is zero, which is
        honest rather than optimistic: it says "no between-plot error is
        available", not "this estimate is exact".

        An inventory keyed only by ``"TOTAL"`` is an unspeciated distribution of
        the whole stand, not an empty stand. Summing the species keys and then
        overwriting ``"TOTAL"`` with that sum used to zero exactly this case, and
        it is the case ``build_context`` produces whenever it has to fall back to
        a single class at the stand's own QMD -- so a diameter-class model driven
        from a stand with no tree list read a stand of nothing.
        """
        stems_dict: Dict[Any, Any] = {}
        ba_dict: Dict[Any, Any] = {}
        total_n = 0.0
        total_ba = 0.0
        speciated = False
        for key, record in self._diameter_classes.items():
            n_class = sum(float(n) for n in record["n_per_ha"])
            ba_class = 0.0
            for diameter_cm, count in zip(record["bin_mids_cm"], record["n_per_ha"], strict=False):
                radius_m = (float(diameter_cm) / 100.0) / 2.0
                ba_class += float(count) * pi * radius_m * radius_m
            species = key if key != "TOTAL" else None
            stems_dict[key] = Stems(n_class, species=species, precision=0.0)
            ba_dict[key] = StandBasalArea(ba_class, species=species, precision=0.0)
            if key != "TOTAL":
                speciated = True
                total_n += n_class
                total_ba += ba_class

        if speciated:
            stems_dict["TOTAL"] = Stems(total_n, species=None, precision=0.0)
            ba_dict["TOTAL"] = StandBasalArea(total_ba, species=None, precision=0.0)
        else:
            total_n = float(stems_dict.get("TOTAL", Stems(0.0)))
            total_ba = float(ba_dict.get("TOTAL", StandBasalArea(0.0)))
            stems_dict.setdefault("TOTAL", Stems(0.0, species=None, precision=0.0))
            ba_dict.setdefault("TOTAL", StandBasalArea(0.0, species=None, precision=0.0))

        self._metric_estimates["Stems"] = stems_dict
        self._metric_estimates["BasalArea"] = ba_dict
        defined = total_ba > 0.0 and total_n > 0.0
        value = sqrt((40000.0 * total_ba) / (pi * total_n)) if defined else 0.0
        self._metric_estimates["QMD"] = {"TOTAL": QuadraticMeanDiameter(value, precision=0.0)}

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
        elif self.representation in ("aggregate", "diameter_class"):
            # The reduced representations set QMD whenever they set the metrics
            # it derives from, so reaching here means they hold no metrics at all.
            self._derive_aggregate_qmd()
            return
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
        aggregation = _aggregate_plots(self.plots)
        self._metric_estimates["Stems"] = dict(aggregation.stems)
        self._metric_estimates["BasalArea"] = dict(aggregation.basal_area)
        self._metric_estimates["BAWAD"] = dict(aggregation.bawad)
        self._metric_estimates["HL"] = dict(aggregation.loreys_height)
        self._species_components = aggregation.species_components
        self._total_components = aggregation.total_components

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

    def impute(
        self,
        attribute: str,
        imputer: "ImputerSpec" = None,
        *,
        which: str = "missing",
        overwrite: bool = False,
        **imputer_kwargs: object,
    ) -> int:
        """Fill in a tree attribute the inventory does not carry.

        Modelled values are written to each tree's
        :attr:`~pyforestry.base.helpers.tree.Tree.imputed` map together with the
        imputer that produced them and its citation. Measured attributes are
        never modified, so a modelled value cannot be mistaken for a measurement;
        read the two together with
        :meth:`~pyforestry.base.helpers.tree.Tree.value_of`.

        Parameters
        ----------
        attribute:
            What to impute, e.g. ``"height_m"``.
        imputer:
            A registered imputer name (``"naslund"``), an
            :class:`~pyforestry.base.imputation.imputer.Imputer`, a callable
            ``f(tree) -> value | None``, or ``None`` for the attribute's default.
            A callable is recorded as uncited, which is what it is.
        which:
            ``"missing"`` (default) imputes only trees lacking a measured value;
            ``"all"`` imputes every tree the imputer can produce a value for.
        overwrite:
            When ``True``, replace an existing imputed value; otherwise keep any
            already present.
        **imputer_kwargs:
            Passed to a *registered* imputer's constructor, e.g.
            ``naslund_exponent="auto"``. Only meaningful when ``imputer`` names a
            registered imputer (or is left to the default); an already-built
            imputer or a callable is used as given, so passing both is an error
            rather than a silently discarded argument.

        Returns
        -------
        int
            The number of trees assigned a value.

        Raises
        ------
        KeyError
            If no imputer is registered for ``attribute`` and none was given.
        TypeError
            If ``imputer_kwargs`` accompany an already-built imputer or a
            callable, which cannot be reconfigured from them.
        ValueError
            If the imputer cannot be fitted from the available trees, or
            ``which`` is not recognised.
        """
        from pyforestry.base.imputation import resolve_imputer

        if which not in ("missing", "all"):
            raise ValueError(f"Unknown which={which!r}; use 'missing' or 'all'.")

        all_trees = [tree for plot in self.plots for tree in plot.trees]
        resolved = resolve_imputer(attribute, imputer)
        if imputer_kwargs:
            # Reconstructing from kwargs is only valid when the registry built the
            # imputer from a name; doing it to a caller-supplied instance or
            # callable would throw that object away.
            if not (imputer is None or isinstance(imputer, str)):
                raise TypeError(
                    f"impute({attribute!r}, ...) got {sorted(imputer_kwargs)} alongside an "
                    "already-built imputer. Configure the imputer itself, or name a "
                    "registered one and pass its constructor arguments here."
                )
            resolved = type(resolved)(**imputer_kwargs)  # type: ignore[call-arg]

        context: dict = {"stand": self}
        fitted = resolved.fit(all_trees, context)
        if fitted is None:
            usable = sum(
                1
                for tree in all_trees
                if getattr(tree, attribute, None) is not None
                and getattr(tree, "diameter_cm", None) is not None
            )
            raise ValueError(
                f"Could not fit an imputer for {attribute!r} from {usable} usable "
                "measured pair(s). A Näslund fit needs at least two pairs that are "
                "well clear of breast height and that span a range of diameters; a "
                "set that is degenerate (one single diameter) or that implies a "
                "non-monotone curve is rejected."
            )

        count = 0
        for tree in all_trees:
            if which == "missing" and getattr(tree, attribute, None) is not None:
                continue
            if not overwrite and attribute in getattr(tree, "imputed", {}):
                continue
            value = fitted.impute(tree, context)
            if value is not None:
                tree.set_imputed(attribute, value, fitted)
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
            self.representation = "tree_list"

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
        self._require_representation("thin_trees", "tree_list")

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
