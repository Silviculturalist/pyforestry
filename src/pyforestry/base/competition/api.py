"""Compute competition indices for real tree records.

:func:`competition_indices` is the entry point: give it a list of
:class:`~pyforestry.base.helpers.tree.Tree`, a
:class:`~pyforestry.base.helpers.plot.CircularPlot` or a
:class:`~pyforestry.base.helpers.stand.Stand`, say which indices you want and how
competitors should be chosen, and get one :class:`TreeCompetition` back per tree.

Edge effect
-----------
A subject tree near the plot boundary has part of its competition zone outside
the plot, so its distance-dependent indices come out too low. Each result
carries ``observed_zone_fraction``, the share of the competition zone that fell
inside the plot, computed as a circle-circle overlap. With
``edge_correction="proportional_area"`` (the default for a plot of known
geometry) the spatial indices are divided by that fraction, which is exactly the
assumption that the unobserved sector holds competition at the same areal density
as the observed part. Pass ``edge_correction=None`` to get raw values and apply
your own weighting; ``observed_zone_fraction`` is reported either way, so a
caller can always filter on it instead.

Non-spatial indices are never edge-corrected: they are plot-level sums that do
not depend on where in the plot the subject sits.
"""

from dataclasses import dataclass, field
from math import hypot, pi
from typing import Callable, Dict, List, Optional, Sequence, Union

from pyforestry.base.helpers.plot import CircularPlot
from pyforestry.base.helpers.tree import Tree

from .geometry import fraction_of_circle_inside_circle
from .indices import INDEX_REGISTRY, SPATIAL_INDICES, compute_index
from .neighbourhood import MissingNeighbourhoodData, Neighbourhood, basal_area_m2
from .selection import CompetitorSelector, FixedRadius, SelectionContext

__all__ = ["TreeCompetition", "competition_indices"]

CrownRadiusSource = Union[float, Callable[[Tree], Optional[float]], None]


@dataclass
class TreeCompetition:
    """Competition indices computed for one subject tree.

    Attributes:
        tree: The subject tree.
        indices: Index value by Table 2 abbreviation. An index that could not be
            computed is absent from this mapping and appears in ``skipped``.
        n_competitors: How many trees the selector kept.
        zone_radius_m: The competition-zone radius applied (m), if the selector
            defines one.
        observed_zone_fraction: Share of the competition zone inside the plot,
            in ``(0, 1]``. ``1.0`` when no plot geometry was supplied, in which
            case no edge statement is being made.
        edge_corrected: Whether the spatial indices were divided by
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


def _collect_trees(source: Union[Sequence[Tree], CircularPlot, object]) -> tuple:
    """Return ``(trees, plot)`` for a tree list, a plot, or a stand."""
    if isinstance(source, CircularPlot):
        return list(source.trees or []), source
    plots = getattr(source, "plots", None)
    if plots is not None:  # a Stand
        trees: List[Tree] = []
        for plot in plots:
            trees.extend(plot.trees or [])
        # Per-tree geometry is only well defined against a single plot; a
        # multi-plot stand gets no edge correction unless it has exactly one.
        only_plot = plots[0] if len(plots) == 1 else None
        return trees, only_plot
    return list(source), None  # type: ignore[arg-type]


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
            :class:`~pyforestry.base.helpers.stand.Stand`.
        indices: Table 2 abbreviations to compute, e.g. ``("Heg", "BAL")``.
            Defaults to every index that the available data supports.
        selector: How to choose competitors. Defaults to
            :class:`~pyforestry.base.competition.selection.FixedRadius` at 10 m.
            Ignored for the non-spatial indices, which always use the whole plot.
        plot_area_ha: Plot area (ha). Taken from the plot when not given.
        dominant_height_m: Dominant height (m), needed only for ``BALMOD``'s
            relative spacing term.
        crown_radius: Crown/influence-zone radius for the overlap indices --
            a constant, a callable ``f(tree) -> radius | None``, or ``None`` to
            read ``Tree.crown_radius_m``.
        edge_correction: ``"proportional_area"`` (default) divides the spatial
            indices by the observed share of the competition zone; ``None``
            leaves them raw. Either way the share is reported.

    Returns:
        One :class:`TreeCompetition` per usable tree, in input order.

    Raises:
        ValueError: If ``edge_correction`` is not a recognised mode.
    """
    if edge_correction not in (None, "proportional_area"):
        raise ValueError(
            f"Unknown edge_correction {edge_correction!r}; use 'proportional_area' or None."
        )

    trees, plot = _collect_trees(source)
    trees = _usable(trees)
    if not trees:
        return []

    wanted = list(indices) if indices is not None else list(INDEX_REGISTRY)
    selector = selector or FixedRadius(radius_m=10.0)

    area_ha = plot_area_ha
    if area_ha is None and plot is not None:
        area_ha = plot.area_ha
    plot_radius_m = getattr(plot, "radius_m", None) if plot is not None else None

    diameters = [float(t.diameter_cm) for t in trees]
    positions = [t.position for t in trees]
    have_positions = all(p is not None for p in positions)

    basal_areas = [basal_area_m2(d) for d in diameters]
    total_ba_m2 = sum(basal_areas)
    plot_ba_m2_ha = (total_ba_m2 / area_ha) if area_ha else None
    qmd_cm = (sum(d * d for d in diameters) / len(diameters)) ** 0.5
    stems_per_ha = (len(trees) / area_ha) if area_ha else None

    relative_spacing = None
    if dominant_height_m and area_ha and dominant_height_m > 0:
        relative_spacing = ((area_ha * 10000.0 / len(trees)) ** 0.5) / dominant_height_m

    context = SelectionContext(
        stems_per_ha=stems_per_ha,
        mean_height_m=_mean_height(trees),
    )

    results: List[TreeCompetition] = []
    for i, tree in enumerate(trees):
        distances = _distances_from(i, positions) if have_positions else None

        if distances is None:
            chosen_idx: tuple = tuple(j for j in range(len(trees)) if j != i)
            chosen_dist = None
            zone_radius = None
        else:
            selection = selector.select(i, diameters, distances, context)
            chosen_idx = selection.indices
            chosen_dist = selection.distances_m
            zone_radius = selection.zone_radius_m

        crown_i = _crown_radius(tree, crown_radius)
        crown_j = (
            tuple(_crown_radius(trees[j], crown_radius) for j in chosen_idx)
            if crown_i is not None
            else None
        )
        if crown_j is not None and any(r is None for r in crown_j):
            crown_j = None  # a partial crown set cannot support the overlap indices

        neighbourhood = Neighbourhood(
            subject_dbh_cm=diameters[i],
            competitor_dbh_cm=tuple(diameters[j] for j in chosen_idx),
            distances_m=chosen_dist,
            subject_crown_radius_m=crown_i,
            competitor_crown_radius_m=crown_j,  # type: ignore[arg-type]
            plot_area_ha=area_ha,
            plot_basal_area_m2_ha=plot_ba_m2_ha,
            plot_qmd_cm=qmd_cm,
            relative_spacing=relative_spacing,
            competition_zone_radius_m=zone_radius,
        )

        fraction = _observed_fraction(tree, plot, plot_radius_m, zone_radius)
        correct = edge_correction == "proportional_area" and fraction < 1.0

        result = TreeCompetition(
            tree=tree,
            n_competitors=len(chosen_idx),
            zone_radius_m=zone_radius,
            observed_zone_fraction=fraction,
            edge_corrected=correct,
        )
        for name in wanted:
            try:
                value = compute_index(name, neighbourhood)
            except (MissingNeighbourhoodData, ValueError, KeyError) as exc:
                result.skipped[name] = str(exc)
                continue
            if correct and name in SPATIAL_INDICES:
                value /= fraction
            result.indices[name] = value
        results.append(result)
    return results


def _mean_height(trees: Sequence[Tree]) -> Optional[float]:
    """Arithmetic mean of whatever heights are available, or ``None``."""
    heights = [h for h in (t.effective_height_m() for t in trees) if h is not None]
    return sum(heights) / len(heights) if heights else None


def _distances_from(i: int, positions: Sequence) -> List[float]:
    """Horizontal distance (m) from tree ``i`` to every tree, itself included as 0."""
    p_i = positions[i]
    return [hypot(p.X - p_i.X, p.Y - p_i.Y) for p in positions]


def _observed_fraction(
    tree: Tree,
    plot: Optional[CircularPlot],
    plot_radius_m: Optional[float],
    zone_radius_m: Optional[float],
) -> float:
    """Share of the subject's competition zone that lies inside the plot."""
    if plot is None or plot_radius_m is None or zone_radius_m is None or zone_radius_m <= 0:
        return 1.0
    if tree.position is None or plot.position is None:
        return 1.0
    offset = hypot(tree.position.X - plot.position.X, tree.position.Y - plot.position.Y)
    return fraction_of_circle_inside_circle(offset, zone_radius_m, plot_radius_m)


def zone_area_m2(radius_m: float) -> float:
    """Area of a circular competition zone (m^2)."""
    return pi * float(radius_m) ** 2
