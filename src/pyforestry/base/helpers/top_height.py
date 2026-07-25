"""Configurable stand top-height (dominant height) estimators.

Top height is estimated per plot and then averaged over all plots. Two families
of *reference* (what "the top" is) are supported, each composed with a *height
source* (measured heights, a fitted Näslund curve, or a user callable):

Tree-selection references (use the heights of selected trees):

* ``"mean_of_largest"`` -- mean height of the ``n`` largest trees, by diameter
  (widest) or by height (tallest).
* ``"garcia_u"`` -- García's (1998) distribution-free linear-unbiased
  U-statistic (his eqs 4-7), for plots that differ in size from the reference
  area.
* ``"garcia_pp"`` -- García's plotting-position estimator (his eq 3), a single
  interpolated order statistic with the Hosking Gumbel constant ``alpha = 0.65``.

Diameter-reference references (read a height off a curve at a reference
diameter; these require a *curve* height source):

* ``"percentile"`` -- the curve height at the ``p``-th diameter percentile
  (e.g. D90).
* ``"mean_plus_k_sigma"`` -- the curve height at ``mean(d) + k * sd(d)``
  (Petterson 1955 uses ``k = 3``).

Reference
---------
García, O. (1998). Estimating top height with variable plot sizes.
Canadian Journal of Forest Research 28(10): 1509-1517.
"""

import statistics
import warnings
from math import floor, sqrt
from typing import List, Optional, Sequence, Union

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers.height_models import (
    HeightSource,
    HeightSourceSpec,
    resolve_height_source,
)
from pyforestry.base.helpers.primitives import TopHeightDefinition, TopHeightMeasurement

# Hosking's (1990) recommended Gumbel plotting-position constant (beta = 0);
# García's Table 1, approximation 8.
GARCIA_ALPHA = 0.65

_DIAMETER_REFERENCES = frozenset({"percentile", "mean_plus_k_sigma"})


def _reference_cell_ha(definition: TopHeightDefinition) -> float:
    """Area (ha) that the definition allots to a single dominant tree."""
    return definition.nominal_area_ha / definition.nominal_n


def _effective_area_ha(plot) -> Optional[float]:  # noqa: ANN001
    """The plot area (ha) that was actually observed.

    A plot straddling the stand boundary only sees the ``1 - occlusion`` share of
    its nominal area, and only the trees on that share are recorded. Densities
    and reference-cell counts must therefore be taken against the observed area,
    exactly as ``Stand._compute_plot_mean_estimates`` does, or a boundary plot looks
    artificially sparse and its top height is biased low.
    """
    area_ha = getattr(plot, "area_ha", None)
    if not area_ha or area_ha <= 0:
        return None
    visible = 1.0 - float(getattr(plot, "occlusion", 0.0) or 0.0)
    if visible <= 0:
        return float(area_ha)
    return float(area_ha) * visible


def _plot_stem_count(plot) -> float:  # noqa: ANN001
    """Stems the plot represents, honouring per-record ``weight_n``.

    This is the count that sets how many trees a reference cell holds. It must
    come from the whole tree list, not from the subset carrying heights: heights
    are routinely measured on a subsample, and deriving the cell occupancy from
    the measured subset alone shrinks it in proportion to the sampling intensity.
    """
    total = 0.0
    for tree in plot.trees:
        weight = getattr(tree, "weight_n", None)
        total += 1.0 if weight is None else float(weight)
    return total


def _usable_heights(trees: Sequence, source: HeightSource) -> List[float]:
    """Heights (m) the source can supply for ``trees`` (skipping ``None``)."""
    out: List[float] = []
    for tree in trees:
        height = source.height_for(tree)
        if height is not None:
            out.append(float(height))
    return out


def _percentile(sorted_values: Sequence[float], p: float) -> float:
    """Linear-interpolation percentile (``p`` in [0, 100]) of sorted values."""
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    rank = (p / 100.0) * (n - 1)
    lo = int(floor(rank))
    if lo >= n - 1:
        return sorted_values[-1]
    frac = rank - lo
    return sorted_values[lo] * (1.0 - frac) + sorted_values[lo + 1] * frac


def _mean_of_largest(
    plot,  # noqa: ANN001
    source: HeightSource,
    area_ha: float,
    definition: TopHeightDefinition,
    n: Optional[int],
    by: str,
) -> Optional[float]:
    """Mean height of the ``n`` largest trees (by diameter or height)."""
    candidates = []  # (sort_key, height)
    for tree in plot.trees:
        height = source.height_for(tree)
        if height is None:
            continue
        if by == "diameter":
            diameter = getattr(tree, "diameter_cm", None)
            if diameter is None:
                continue
            candidates.append((float(diameter), float(height)))
        else:  # by == "height"
            candidates.append((float(height), float(height)))

    if n is None:
        n_top = max(1, round(area_ha * definition.nominal_n / definition.nominal_area_ha))
    else:
        n_top = int(n)
    if n_top < 1 or len(candidates) < n_top:
        return None

    candidates.sort(key=lambda pair: pair[0], reverse=True)
    return statistics.mean(height for _, height in candidates[:n_top])


def _garcia_theta_integer(heights_asc: Sequence[float], m: int, n: int) -> float:
    """García's U-statistic top-height estimate for integer ``m`` (his eq 7).

    Uses the numerically stable ascending recursion
    ``t <- x[i] + (i - m) * t / (i - 1)`` for ``i = m..n`` (``t = x[m]`` at
    ``i = m``), then multiplies by ``m / n``. ``heights_asc[i-1]`` is the i-th
    smallest height.
    """
    t = 0.0
    for i in range(m, n + 1):
        if i == m:
            t = heights_asc[i - 1]
        else:
            t = heights_asc[i - 1] + (i - m) * t / (i - 1)
    return (m / n) * t


def _garcia_u(
    plot,  # noqa: ANN001
    source: HeightSource,
    area_ha: float,
    definition: TopHeightDefinition,
) -> Optional[float]:
    """García's U-statistic estimator, interpolating on non-integer ``m``."""
    heights = sorted(_usable_heights(plot.trees, source))
    n_measured = len(heights)
    if n_measured == 0:
        return None
    stems = _plot_stem_count(plot)
    if stems <= 0:
        return None
    # m = N * a_ref / A is how many trees the reference cell holds. It follows
    # from the stand's density, so it is taken from the plot's whole tree list;
    # the order statistics below then come from the measured heights, which
    # estimate the same height distribution.
    m_real = stems * _reference_cell_ha(definition) / area_ha
    m_floor = int(floor(m_real))
    if m_floor < 1 or m_floor > n_measured:
        # Plot smaller than the reference cell, or too few measured heights to
        # represent a cell holding m trees.
        return None
    theta_lo = _garcia_theta_integer(heights, m_floor, n_measured)
    if m_real == m_floor or m_floor + 1 > n_measured:
        return theta_lo
    theta_hi = _garcia_theta_integer(heights, m_floor + 1, n_measured)
    frac = m_real - m_floor
    return (1.0 - frac) * theta_lo + frac * theta_hi


def _garcia_pp(
    plot,  # noqa: ANN001
    source: HeightSource,
    area_ha: float,
    definition: TopHeightDefinition,
) -> Optional[float]:
    """García's plotting-position estimator (his eq 3, ``alpha = 0.65``)."""
    heights = sorted(_usable_heights(plot.trees, source))
    n_measured = len(heights)
    if n_measured == 0:
        return None
    stems = _plot_stem_count(plot)
    if stems <= 0:
        return None
    rho = area_ha / _reference_cell_ha(definition)  # García's "100 A"
    rank_from_top = 1.0 + GARCIA_ALPHA * (rho - 1.0)
    if rank_from_top > stems:
        return None
    # The rank is defined within the plot's whole tree list. Re-express it as the
    # same quantile of the measured heights so a height subsample does not shift
    # the estimate; the two coincide when every tree carries a height.
    rank_in_sample = rank_from_top * n_measured / stems
    k = n_measured - rank_in_sample + 1.0  # k-th smallest order statistic
    if k < 1 or k > n_measured:
        return None
    k_floor = int(floor(k))
    if k == k_floor or k_floor >= n_measured:
        return heights[k_floor - 1]
    frac = k - k_floor
    return (1.0 - frac) * heights[k_floor - 1] + frac * heights[k_floor]


def _plot_diameters(plot) -> List[float]:  # noqa: ANN001
    """Positive diameters (cm) of the plot's trees."""
    diameters = []
    for tree in plot.trees:
        diameter = getattr(tree, "diameter_cm", None)
        if diameter is not None and float(diameter) > 0:
            diameters.append(float(diameter))
    return diameters


def _percentile_reference(
    plot,  # noqa: ANN001
    source: HeightSource,
    p: float,
) -> Optional[float]:
    """Curve height at the ``p``-th diameter percentile of the plot."""
    diameters = _plot_diameters(plot)
    if not diameters:
        return None
    reference_diameter = _percentile(sorted(diameters), p)
    return source.height_at_diameter(reference_diameter)


def _mean_plus_k_sigma_reference(
    plot,  # noqa: ANN001
    source: HeightSource,
    k: float,
) -> Optional[float]:
    """Curve height at ``mean(d) + k * sd(d)`` of the plot's diameters."""
    diameters = _plot_diameters(plot)
    if len(diameters) < 2:
        return None
    reference_diameter = statistics.mean(diameters) + k * statistics.stdev(diameters)
    return source.height_at_diameter(reference_diameter)


def compute_top_height(
    plots: Sequence,
    *,
    reference: str = "garcia_u",
    height_source: HeightSourceSpec = "measured",
    n: Optional[int] = None,
    by: str = "diameter",
    percentile: float = 90.0,
    k: float = 3.0,
    definition: Optional[TopHeightDefinition] = None,
    naslund_exponent: Union[int, float, str] = 2,
) -> Optional[TopHeightMeasurement]:
    """Estimate stand top height, averaging a per-plot estimate over all plots.

    Parameters
    ----------
    plots:
        The sample plots (each exposing ``trees`` and ``area_ha``).
    reference:
        Which top-height reference to use: ``"mean_of_largest"``, ``"garcia_u"``,
        ``"garcia_pp"``, ``"percentile"`` or ``"mean_plus_k_sigma"``.
    height_source:
        ``"measured"``, ``"naslund"`` (fit stand-wide), a callable
        ``f(diameter_cm) -> height_m``, or a ready height source/curve. The
        diameter-reference methods require a curve source. With ``"measured"``
        only trees carrying a measured height contribute, so if the thickest
        trees lack heights, impute them first (``Stand.impute_heights``) or use a
        curve source instead.
    n:
        For ``"mean_of_largest"``: number of largest trees per plot. Defaults to
        the definition-consistent count ``round(area_ha * nominal_n /
        nominal_area_ha)``.
    by:
        For ``"mean_of_largest"``: ``"diameter"`` (widest) or ``"height"``
        (tallest).
    percentile:
        For ``"percentile"``: the diameter percentile (e.g. ``90`` for D90).
    k:
        For ``"mean_plus_k_sigma"``: the sigma multiplier (Petterson uses 3).
    definition:
        The top-height definition (``nominal_n`` per ``nominal_area_ha``).
        Defaults to 100 per hectare.
    naslund_exponent:
        Exponent for a ``"naslund"`` fit: a number, or ``"auto"`` to fit the
        exponent from the data too. Defaults to 2.

    Returns
    -------
    TopHeightMeasurement | None
        The stand top height (metres), or ``None`` if no plot could contribute.

    Raises
    ------
    ValueError
        For an unknown ``reference``, or a diameter-reference method with a
        non-curve height source.
    """
    if not plots:
        return None
    definition = definition or TopHeightDefinition()
    reference = reference.lower()
    by = by.lower()

    all_trees = [tree for plot in plots for tree in plot.trees]
    source = resolve_height_source(height_source, all_trees, naslund_exponent=naslund_exponent)
    if source is None:
        return None  # e.g. Näslund could not be fit

    if reference in _DIAMETER_REFERENCES and not source.is_curve:
        raise ValueError(
            f"reference={reference!r} needs a curve height source (Näslund or a "
            "callable), not measured heights."
        )

    estimates: List[float] = []
    skipped = 0
    for plot in plots:
        area_ha = _effective_area_ha(plot)
        if area_ha is None:
            skipped += 1
            continue
        if reference == "mean_of_largest":
            est = _mean_of_largest(plot, source, area_ha, definition, n, by)
        elif reference == "garcia_u":
            est = _garcia_u(plot, source, area_ha, definition)
        elif reference == "garcia_pp":
            est = _garcia_pp(plot, source, area_ha, definition)
        elif reference == "percentile":
            est = _percentile_reference(plot, source, percentile)
        elif reference == "mean_plus_k_sigma":
            est = _mean_plus_k_sigma_reference(plot, source, k)
        else:
            raise ValueError(f"Unknown top-height reference {reference!r}.")
        if est is not None and est > 0:
            estimates.append(float(est))
        else:
            skipped += 1

    if not estimates:
        warnings.warn(
            f"No plot could supply a {reference!r} top-height estimate "
            f"({skipped} of {len(plots)} plot(s) skipped). Typically the plots are "
            "smaller than the reference cell, or too few trees carry a height to "
            "resolve the top of the distribution -- impute heights first, or use a "
            "curve height source.",
            stacklevel=2,
        )
        return None
    if skipped:
        # Averaging only the plots that happened to resolve is a selection, not a
        # sample, so the caller has to know it happened.
        warnings.warn(
            f"{skipped} of {len(plots)} plot(s) could not supply a {reference!r} "
            "top-height estimate and were excluded from the stand mean.",
            stacklevel=2,
        )
    value = statistics.mean(estimates)
    precision = statistics.stdev(estimates) / sqrt(len(estimates)) if len(estimates) > 1 else 0.0
    return TopHeightMeasurement(
        value=value,
        definition=definition,
        species=None,
        precision=precision,
        est_bias=0.0,
    )


DESCRIPTOR = FormulaDescriptor(
    component_id="garcia_1998_top_height",
    source=SourceReference(
        author="García, O.",
        year=1998,
        title="Estimating top height with variable plot sizes",
        note=(
            "Canadian Journal of Forest Research 28(10), 1509-1517. Supplies the "
            "'garcia_u' distribution-free linear-unbiased U-statistic (his eqs 4-7) "
            "and the 'garcia_pp' plotting-position estimator (his eq 3, with the "
            "Hosking Gumbel constant alpha = 0.65). The other references composed "
            "here carry their own provenance: the Näslund height curve is "
            "naslund_1936_height_curve, and the 'mean_plus_k_sigma' reference with "
            "k = 3 follows Petterson, H. (1955), 'Barrskogens volymproduktion', "
            "Meddelanden från Statens skogsforskningsinstitut 45(1)."
        ),
    ),
    species_groups={},
    units={
        "diameter": "cm",
        "height": "m",
        "return": "m",
    },
    kernel_names=("compute_top_height",),
    domain="height",
)
