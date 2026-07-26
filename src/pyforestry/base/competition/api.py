"""Compute competition indices for real tree records.

:func:`competition_indices` is the entry point: give it a list of
:class:`~pyforestry.base.helpers.tree.Tree`, a
:class:`~pyforestry.base.helpers.plot.CircularPlot` or a
:class:`~pyforestry.base.helpers.stand.Stand`, say which indices you want and how
competitors should be chosen, and get one :class:`TreeCompetition` back per tree.

Two neighbourhoods per tree
---------------------------
The distance-independent indices are stand descriptors: ``BAL`` is the basal area
per hectare standing in trees larger than the subject, over the whole plot.
Restricting them to the trees a spatial selector happened to keep would make
them shrink with the search radius and stop being the published quantity. Each
subject therefore gets **two** neighbourhoods: the selector's competitors drive
the spatially explicit indices, and every other tree on the plot drives the
distance-independent ones. The selector never touches the latter.

A plot is one population
------------------------
A :class:`~pyforestry.base.helpers.stand.Stand` is processed one plot at a time.
Stem coordinates are plot-local, plot-level quantities (basal area per hectare,
QMD, stem density) describe a single plot, and trees on different plots do not
compete. Results come back in plot order, then tree order.

``weight_n`` and occlusion
--------------------------
Every per-hectare quantity honours ``Tree.weight_n``, so a record standing for
ten stems counts as ten, and ``CircularPlot.occlusion``, so a plot that only
observed ``1 - occlusion`` of its area expands accordingly -- the same
conventions the plot aggregation in
:mod:`pyforestry.base.helpers.stand` uses. The spatially explicit indices are
per-stem geometry and ignore ``weight_n``: a representation tree has one
position, and pretending it has ten would place ten stems on one point.

Edge effect
-----------
A subject tree near the plot boundary has part of its competition zone outside
the plot, so its distance-dependent indices come out too low. Each result
carries ``observed_zone_fraction``, the share of the competition zone that fell
inside the plot, computed as a circle-circle overlap. With
``edge_correction="proportional_area"`` (the default for a plot of known
geometry) the *additive* spatial indices are divided by that fraction, which is
exactly the assumption that the unobserved sector holds competition at the same
areal density as the observed part. Pass ``edge_correction=None`` to get raw
values and apply your own weighting; ``observed_zone_fraction`` is reported
either way, so a caller can always filter on it instead.

Two limits on that correction, both deliberate:

* Only indices that are plain sums over competitors scale with the observed
  share. ``SBAr`` is a ratio and ``Almdg`` a weight-normalised mean of areas --
  halving the competitor set leaves both unchanged -- so dividing them by the
  fraction would invent competition. They are reported raw and flagged by
  ``CompetitionIndex.additive``.
* The correction needs a competition zone that was fixed *before* the data were
  seen. Selectors that have no such zone (:class:`SearchCone`,
  :class:`NearestNeighbours`, :class:`BitterlichBAF`) report
  ``zone_radius_m=None`` and are left uncorrected, because deriving the zone
  from the competitors that were actually found is circular: a truncated
  neighbourhood looks smaller, so the correction it implies is too small.

Non-spatial indices are never edge-corrected: they are plot-level sums that do
not depend on where in the plot the subject sits.
"""

import warnings
from dataclasses import dataclass, field
from math import atan2, hypot, pi
from typing import Callable, Dict, List, Optional, Sequence, Tuple, Union

from pyforestry.base.helpers.plot import CircularPlot
from pyforestry.base.helpers.tree import Tree

from .geometry import fraction_of_circle_inside_circle
from .indices import INDEX_REGISTRY, resolve_index
from .neighbourhood import MissingNeighbourhoodData, Neighbourhood, basal_area_m2
from .selection import Candidates, CompetitorSelector, FixedRadius, SelectionContext

__all__ = ["TreeCompetition", "competition_indices", "zone_area_m2"]

CrownRadiusSource = Union[float, Callable[[Tree], Optional[float]], None]


@dataclass
class TreeCompetition:
    """Competition indices computed for one subject tree.

    Attributes:
        tree: The subject tree.
        indices: Index value by Table 2 abbreviation. An index that could not be
            computed is absent from this mapping and appears in ``skipped``.
        n_competitors: How many trees the selector kept for the spatially
            explicit indices. The distance-independent indices always see every
            other tree on the plot and are unaffected by this number.
        zone_radius_m: The competition-zone radius applied (m), if the selector
            defines one ahead of the data. ``None`` for the variable-reach
            selectors, which is also why those get no edge correction.
        observed_zone_fraction: Share of the competition zone inside the plot,
            in ``(0, 1]``. ``1.0`` when no plot geometry was supplied, in which
            case no edge statement is being made.
        edge_corrected: Whether the additive spatial indices were divided by
            ``observed_zone_fraction``.
        skipped: Why each unavailable index could not be computed.
    """

    tree: Tree
    indices: Dict[str, float] = field(default_factory=dict)
    n_competitors: int = 0
    zone_radius_m: Optional[float] = None
    observed_zone_fraction: float = 1.0
    edge_corrected: bool = False
    skipped: Dict[str, str] = field(default_factory=dict)


def _crown_radius(tree: Tree, source: CrownRadiusSource) -> Optional[float]:
    """Resolve a crown radius for ``tree`` from an override, a callable, or the tree."""
    if callable(source):
        value = source(tree)
    elif source is not None:
        value = float(source)
    else:
        value = getattr(tree, "crown_radius_m", None)
    return None if value is None else float(value)


def _usable(trees: Sequence[Tree]) -> List[Tree]:
    """Keep trees carrying a positive diameter; everything here is diameter-driven."""
    kept: List[Tree] = []
    for t in trees:
        d = t.diameter_cm
        if d is None:
            continue
        if float(d) > 0:
            kept.append(t)
    return kept


def _weight(tree: Tree) -> float:
    """Number of stems the record stands for; defaults to one."""
    weight = getattr(tree, "weight_n", 1.0)
    return 1.0 if weight is None else float(weight)


def _plot_units(
    source: Union[Sequence[Tree], CircularPlot, object],
) -> List[Tuple[List[Tree], Optional[CircularPlot]]]:
    """Split the input into independent populations of ``(trees, plot)``.

    A stand yields one unit per plot: stem coordinates are plot-local and trees
    on different plots are not each other's competitors.
    """
    if isinstance(source, CircularPlot):
        return [(list(source.trees or []), source)]
    plots = getattr(source, "plots", None)
    if plots is not None:  # a Stand
        return [(list(plot.trees or []), plot) for plot in plots]
    return [(list(source), None)]  # type: ignore[arg-type]


def _effective_area_ha(plot: Optional[CircularPlot], override: Optional[float]) -> Optional[float]:
    """Plot area actually observed (ha), after occlusion.

    Mirrors the ``area_ha * (1 - occlusion)`` convention that
    :meth:`~pyforestry.base.helpers.stand.Stand._compute_plot_mean_estimates`
    uses, so a partly occluded plot expands its trees over the area that was
    really searched instead of the nominal one.
    """
    area = override if override is not None else (plot.area_ha if plot is not None else None)
    if area is None or plot is None:
        return area
    visible = 1.0 - float(getattr(plot, "occlusion", 0.0) or 0.0)
    return area * visible if visible > 0 else area


def competition_indices(
    source: Union[Sequence[Tree], CircularPlot, object],
    *,
    indices: Optional[Sequence[str]] = None,
    selector: Optional[CompetitorSelector] = None,
    plot_area_ha: Optional[float] = None,
    dominant_height_m: Optional[float] = None,
    crown_radius: CrownRadiusSource = None,
    edge_correction: Optional[str] = "proportional_area",
) -> List[TreeCompetition]:
    """Compute competition indices for every tree in ``source``.

    Args:
        source: A sequence of :class:`Tree`, a :class:`CircularPlot`, or a
            :class:`~pyforestry.base.helpers.stand.Stand`, whose plots are
            processed independently.
        indices: Table 2 abbreviations to compute, e.g. ``("Heg", "BAL")``.
            Defaults to every index that the available data supports.
        selector: How to choose competitors for the *spatially explicit*
            indices. Defaults to
            :class:`~pyforestry.base.competition.selection.FixedRadius` at 10 m.
            Ignored for the distance-independent indices, which always use the
            whole plot.
        plot_area_ha: Plot area (ha), before occlusion. Taken from the plot when
            not given, and applied to every plot of a stand.
        dominant_height_m: Dominant height (m), needed only for ``BALMOD``'s
            relative spacing term.
        crown_radius: Crown/influence-zone radius for the overlap indices --
            a constant, a callable ``f(tree) -> radius | None``, or ``None`` to
            read ``Tree.crown_radius_m``.
        edge_correction: ``"proportional_area"`` (default) divides the additive
            spatial indices by the observed share of the competition zone;
            ``None`` leaves them raw. Either way the share is reported.

    Returns:
        One :class:`TreeCompetition` per usable tree, in input order (plot order
        first for a stand).

    Raises:
        KeyError: If ``indices`` names an index that does not exist.
        ValueError: If ``edge_correction`` is not a recognised mode.
    """
    if edge_correction not in (None, "proportional_area"):
        raise ValueError(
            f"Unknown edge_correction {edge_correction!r}; use 'proportional_area' or None."
        )

    # Resolved up front so a misspelled abbreviation is an error, not an index
    # that quietly turns up in `skipped` on every tree.
    wanted = (
        [resolve_index(name).abbreviation for name in indices] if indices is not None else None
    )
    selector = selector or FixedRadius(radius_m=10.0)

    results: List[TreeCompetition] = []
    for trees, plot in _plot_units(source):
        results.extend(
            _unit_results(
                _usable(trees),
                plot,
                wanted=wanted,
                selector=selector,
                plot_area_ha=plot_area_ha,
                dominant_height_m=dominant_height_m,
                crown_radius=crown_radius,
                edge_correction=edge_correction,
            )
        )
    return results


def _unit_results(
    trees: List[Tree],
    plot: Optional[CircularPlot],
    *,
    wanted: Optional[List[str]],
    selector: CompetitorSelector,
    plot_area_ha: Optional[float],
    dominant_height_m: Optional[float],
    crown_radius: CrownRadiusSource,
    edge_correction: Optional[str],
) -> List[TreeCompetition]:
    """Compute every requested index for one plot's worth of trees."""
    if not trees:
        return []

    names = wanted if wanted is not None else list(INDEX_REGISTRY)
    area_ha = _effective_area_ha(plot, plot_area_ha)
    plot_radius_m = getattr(plot, "radius_m", None) if plot is not None else None

    diameters = [float(t.diameter_cm) for t in trees]
    weights = [_weight(t) for t in trees]
    total_weight = sum(weights)

    basal_areas = [w * basal_area_m2(d) for w, d in zip(weights, diameters, strict=True)]
    plot_ba_m2_ha = (sum(basal_areas) / area_ha) if area_ha else None
    qmd_cm = (
        sum(w * d * d for w, d in zip(weights, diameters, strict=True)) / total_weight
    ) ** 0.5
    stems_per_ha = (total_weight / area_ha) if area_ha else None

    relative_spacing = None
    if dominant_height_m and area_ha and dominant_height_m > 0:
        relative_spacing = ((area_ha * 10000.0 / total_weight) ** 0.5) / dominant_height_m

    # Heights and crown base heights are read through value_of, so an imputed
    # value counts exactly as a measured one (see pyforestry.base.imputation).
    heights = [t.value_of("height_m") for t in trees]
    crown_bases = [t.value_of("crown_base_height_m") for t in trees]

    context = SelectionContext(
        stems_per_ha=stems_per_ha,
        mean_height_m=_mean_height(heights, weights),
    )

    # Only trees that were mapped can take part in the spatial indices. The rest
    # still contribute to every plot-level quantity above and to the
    # distance-independent neighbourhoods below.
    mapped = [k for k, t in enumerate(trees) if t.position is not None]
    if mapped and len(mapped) < len(trees):
        warnings.warn(
            f"{len(trees) - len(mapped)} of {len(trees)} trees have no position; they are "
            "excluded from the spatially explicit indices but still count towards the "
            "distance-independent ones.",
            stacklevel=4,
        )
    mapped_positions = [trees[k].position for k in mapped]
    mapped_columns = {
        "diameters_cm": tuple(diameters[k] for k in mapped),
        "heights_m": tuple(heights[k] for k in mapped),
        "crown_base_heights_m": tuple(crown_bases[k] for k in mapped),
    }
    slot = {tree_index: k for k, tree_index in enumerate(mapped)}

    results: List[TreeCompetition] = []
    for i, tree in enumerate(trees):
        chosen, chosen_dist, zone_radius = _select_for(
            i, slot, mapped, mapped_positions, mapped_columns, selector, context
        )

        crown_i = _crown_radius(tree, crown_radius)
        crown_j = (
            tuple(_crown_radius(trees[j], crown_radius) for j in chosen)
            if crown_i is not None and chosen_dist is not None
            else None
        )
        if crown_j is not None and any(r is None for r in crown_j):
            crown_j = None  # a partial crown set cannot support the overlap indices

        shared = {
            "plot_area_ha": area_ha,
            "plot_basal_area_m2_ha": plot_ba_m2_ha,
            "plot_qmd_cm": qmd_cm,
            "relative_spacing": relative_spacing,
        }
        # The distance-independent indices describe the plot, so their competitor
        # set is every other tree on it -- never the selector's subset.
        others = [j for j in range(len(trees)) if j != i]
        plot_neighbourhood = Neighbourhood(
            subject_dbh_cm=diameters[i],
            competitor_dbh_cm=tuple(diameters[j] for j in others),
            competitor_weights=tuple(weights[j] for j in others),
            **shared,  # type: ignore[arg-type]
        )
        spatial_neighbourhood = (
            None
            if chosen_dist is None
            else Neighbourhood(
                subject_dbh_cm=diameters[i],
                competitor_dbh_cm=tuple(diameters[j] for j in chosen),
                distances_m=chosen_dist,
                subject_crown_radius_m=crown_i,
                competitor_crown_radius_m=crown_j,  # type: ignore[arg-type]
                competition_zone_radius_m=zone_radius,
                **shared,  # type: ignore[arg-type]
            )
        )

        fraction = _observed_fraction(tree, plot, plot_radius_m, zone_radius)
        correct = edge_correction == "proportional_area" and 0.0 < fraction < 1.0

        result = TreeCompetition(
            tree=tree,
            n_competitors=len(chosen),
            zone_radius_m=zone_radius,
            observed_zone_fraction=fraction,
            edge_corrected=correct,
        )
        for name in names:
            entry = INDEX_REGISTRY[name]
            neighbourhood = plot_neighbourhood if not entry.spatial else spatial_neighbourhood
            if neighbourhood is None:
                result.skipped[name] = (
                    "This index needs distances_m, which are not available: the subject "
                    "tree has no position, or no other mapped tree was selected."
                )
                continue
            try:
                value = entry.compute(neighbourhood)
            except (MissingNeighbourhoodData, ValueError, ZeroDivisionError) as exc:
                result.skipped[name] = str(exc)
                continue
            if correct and entry.additive:
                value /= fraction
            result.indices[name] = value
        results.append(result)
    return results


def _select_for(
    i: int,
    slot: Dict[int, int],
    mapped: Sequence[int],
    positions: Sequence,
    columns: Dict[str, tuple],
    selector: CompetitorSelector,
    context: SelectionContext,
) -> Tuple[Tuple[int, ...], Optional[Tuple[float, ...]], Optional[float]]:
    """Run the selector for subject ``i``, returning tree indices and distances.

    Distances and bearings are measured from the subject, so the candidate view
    is rebuilt per subject; the size and height columns are shared.
    """
    if len(mapped) < 2 or i not in slot:
        return (), None, None

    subject = slot[i]
    candidates = Candidates(
        distances_m=_distances_from(subject, positions),
        bearings_rad=_bearings_from(subject, positions),
        **columns,
    )
    selection = selector.select(subject, candidates, context)

    pairs = [
        (mapped[j], d)
        for j, d in zip(selection.indices, selection.distances_m, strict=True)
        if d > 0
    ]
    dropped = len(selection.indices) - len(pairs)
    if dropped:
        warnings.warn(
            f"{dropped} competitor(s) share the subject tree's coordinates exactly and were "
            "dropped; the size-ratio indices divide by distance. Check for duplicated or "
            "rounded stem positions.",
            stacklevel=5,
        )
    return tuple(k for k, _ in pairs), tuple(d for _, d in pairs), selection.zone_radius_m


def _mean_height(heights: Sequence[Optional[float]], weights: Sequence[float]) -> Optional[float]:
    """Weighted mean of whatever heights are available, or ``None``."""
    pairs = [(h, w) for h, w in zip(heights, weights, strict=True) if h is not None]
    if not pairs:
        return None
    total = sum(w for _, w in pairs)
    return sum(h * w for h, w in pairs) / total if total else None


def _bearings_from(i: int, positions: Sequence) -> Tuple[float, ...]:
    """Bearing (radians) from tree ``i`` to every tree; its own entry is 0."""
    p_i = positions[i]
    return tuple(atan2(p.Y - p_i.Y, p.X - p_i.X) for p in positions)


def _distances_from(i: int, positions: Sequence) -> Tuple[float, ...]:
    """Horizontal distance (m) from tree ``i`` to every tree, itself included as 0."""
    p_i = positions[i]
    return tuple(hypot(p.X - p_i.X, p.Y - p_i.Y) for p in positions)


def _observed_fraction(
    tree: Tree,
    plot: Optional[CircularPlot],
    plot_radius_m: Optional[float],
    zone_radius_m: Optional[float],
) -> float:
    """Share of the subject's competition zone that lies inside the plot.

    Returns ``1.0`` -- "no edge statement" -- when there is no plot geometry, no
    fixed competition zone, or the subject lies outside the plot circle, which
    means the coordinates and the plot do not describe the same thing and
    proportional-area weighting has no meaning.
    """
    if plot is None or plot_radius_m is None or zone_radius_m is None or zone_radius_m <= 0:
        return 1.0
    if tree.position is None or plot.position is None:
        return 1.0
    offset = hypot(tree.position.X - plot.position.X, tree.position.Y - plot.position.Y)
    if offset > plot_radius_m:
        warnings.warn(
            f"Tree at {offset:.2f} m from the centre of plot {getattr(plot, 'id', '?')!r} lies "
            f"outside its {plot_radius_m:.2f} m radius; no edge correction was applied. Check "
            "that stem coordinates and the plot centre share a coordinate system.",
            stacklevel=5,
        )
        return 1.0
    return fraction_of_circle_inside_circle(offset, zone_radius_m, plot_radius_m)


def zone_area_m2(radius_m: float) -> float:
    """Area of a circular competition zone (m^2)."""
    return pi * float(radius_m) ** 2
