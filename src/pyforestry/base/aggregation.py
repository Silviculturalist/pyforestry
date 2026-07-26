"""The single plot-to-stand estimator.

Every per-hectare stand figure in this package comes from here: :class:`Stand`
reports its metrics from :func:`aggregate_plots`, and so does the working copy a
:class:`~pyforestry.base.simulation.core.SimulationContext` holds. They used to
carry an implementation each, and the two disagreed -- the context averaged a
species over only the plots where it occurred, so a two-plot stand with one
spruce plot and one pine plot read 1.0 stems/ha through ``Stand`` and 2.0 through
the context. One estimator makes that class of divergence unrepresentable.

The estimator's conventions, in one place:

* A plot's trees are expanded over its *effective* area, ``area_ha * (1 -
  occlusion)``, so a partly occluded plot represents the area actually searched.
* ``Tree.weight_n`` is honoured everywhere: a record standing for ten stems
  counts as ten.
* A species absent from a plot contributes an explicit zero for that plot, so the
  cross-plot mean divides by the number of plots -- not by the number of plots
  where the species happens to occur.
* A record with no diameter is still a stem, but carries no basal area and is
  excluded from the diameter-derived metrics (QMD, BAWAD) so their numerator and
  denominator describe the same trees.
* Every ``precision`` is the standard error of the stand mean over plots. It is a
  *between-plot* error only and includes no measurement or model error, so a
  metric built on curve-imputed heights still reports a measured-quality error.
* Ratio metrics (Lorey's mean height, the basal-area weighted diameter, QMD) are
  reduced from the per-plot series through :func:`ratio_and_se`, which carries the
  correlation between numerator and denominator rather than assuming it away.
"""

from __future__ import annotations

import statistics
import warnings
from dataclasses import dataclass, field
from math import pi, sqrt
from typing import Any, Dict, Iterable, List, Sequence, Tuple, Union

from pyforestry.base.helpers.plot import CircularPlot
from pyforestry.base.helpers.primitives import (
    BasalAreaWeightedDiameter,
    LoreysMeanHeight,
    QuadraticMeanDiameter,
    StandBasalArea,
    Stems,
)
from pyforestry.base.helpers.tree_species import TreeName, parse_tree_species

__all__ = [
    "COMPONENT_KEYS",
    "PlotAggregation",
    "aggregate_plots",
    "mean_and_se",
    "metrics_from_series",
    "qmd_from_components",
    "qmd_from_series",
    "ratio_and_se",
    "sum_series",
]

MetricKey = Union[TreeName, str]

#: Basal area (m^2/ha) -> sum of squared diameters (cm^2/ha).
_D2_PER_BA = 40000.0 / pi

#: Per-plot, per-species quantities accumulated in one pass and reused to derive
#: every metric: stem count, stem count of trees carrying a diameter, basal area,
#: sum of cubed diameters (the BAWAD numerator), and the basal-area weighted
#: height sum with its matching basal area (Lorey's).
COMPONENT_KEYS = ("stems", "stems_d", "ba", "d3", "gh", "ba_h")


def mean_and_se(values: Sequence[float]) -> Tuple[float, float]:
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


def ratio_and_se(
    numerator: Sequence[float],
    denominator: Sequence[float],
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


def sum_series(
    components: Dict[Any, Dict[str, List[float]]],
    species: Iterable[Any],
) -> Dict[str, List[float]]:
    """Elementwise per-plot sum of the component series over ``species``.

    Summing the series *before* reducing keeps a species group covariance-aware
    in the same way the stand total is: species that trade off against each other
    across plots do not each contribute independent variance.
    """
    species = list(species)
    n_plots = 0
    for sp in species:
        record = components.get(sp)
        if record is not None:
            n_plots = len(record[COMPONENT_KEYS[0]])
            break
    summed: Dict[str, List[float]] = {key: [0.0] * n_plots for key in COMPONENT_KEYS}
    for sp in species:
        record = components.get(sp)
        if record is None:
            continue
        for key in COMPONENT_KEYS:
            target = summed[key]
            for index, value in enumerate(record[key]):
                target[index] += value
    return summed


def metrics_from_series(
    series: Dict[str, List[float]],
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Derive the stand metrics and their standard errors from component series.

    ``series`` maps each per-plot component accumulated by :func:`aggregate_plots`
    (``stems``, ``ba``, ``d3``, ``gh``, ``ba_h``) to its per-plot values. Additive
    metrics come from the plot-to-plot mean; the ratio metrics (basal-area
    weighted diameter, Lorey's mean height) go through :func:`ratio_and_se`.

    Returns a ``(value, precision)`` pair of dicts keyed by metric name.
    """
    stems_mean, stems_se = mean_and_se(series["stems"])
    ba_mean, ba_se = mean_and_se(series["ba"])
    bawad, bawad_se = ratio_and_se(series["d3"], [ba * _D2_PER_BA for ba in series["ba"]])
    hl, hl_se = ratio_and_se(series["gh"], series["ba_h"])
    return (
        {"stems": stems_mean, "ba": ba_mean, "bawad": bawad, "hl": hl},
        {"stems": stems_se, "ba": ba_se, "bawad": bawad_se, "hl": hl_se},
    )


def qmd_from_series(series: Dict[str, List[float]]) -> QuadraticMeanDiameter:
    """Quadratic mean diameter from per-plot basal-area and stem series.

    Uses ``stems_d`` -- the stems that actually carry a diameter -- so that the
    numerator and denominator describe the same trees; a record with no diameter
    contributes no basal area and must not enter the count either.

    ``QMD = sqrt(40000/pi * R)`` for the mean basal area per stem ``R``, so the
    standard error is obtained by propagating through that square root from
    :func:`ratio_and_se`. Going via the ratio rather than combining the two
    standard errors and their covariance term by term avoids the cancellation
    those three near-equal terms suffer: a stand whose plots share one QMD
    reports exactly zero here instead of a small numerical residue.
    """
    stems_key = "stems_d" if "stems_d" in series else "stems"
    ratio, ratio_se = ratio_and_se(series["ba"], series[stems_key])
    if ratio <= 0:
        return QuadraticMeanDiameter(0.0, precision=0.0)
    qmd_value = sqrt(_D2_PER_BA * ratio)
    qmd_se = qmd_value / (2.0 * ratio) * ratio_se
    return QuadraticMeanDiameter(qmd_value, precision=qmd_se)


def qmd_from_components(
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
    the per-plot series survive, :func:`qmd_from_series` is both covariance-aware
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


@dataclass(frozen=True)
class PlotAggregation:
    """Per-hectare stand metrics estimated as the mean over a set of plots.

    Attributes:
        stems: Stem density by species, plus a ``"TOTAL"`` entry.
        basal_area: Basal area by species, plus a ``"TOTAL"`` entry.
        bawad: Basal-area weighted diameter by species, plus ``"TOTAL"``.
        loreys_height: Lorey's mean height by species, plus ``"TOTAL"``.
        species_components: Per-species per-plot component series, kept so that
            species-group and QMD queries can be rebuilt from the raw plot values
            rather than from already-reduced means.
        total_components: The same series summed over every species.
        species_order: The species encountered, in first-seen order.
        missing_diameter: How many tree records carried no diameter.
    """

    stems: Dict[MetricKey, Stems] = field(default_factory=dict)
    basal_area: Dict[MetricKey, StandBasalArea] = field(default_factory=dict)
    bawad: Dict[MetricKey, BasalAreaWeightedDiameter] = field(default_factory=dict)
    loreys_height: Dict[MetricKey, LoreysMeanHeight] = field(default_factory=dict)
    species_components: Dict[Any, Dict[str, List[float]]] = field(default_factory=dict)
    total_components: Dict[str, List[float]] = field(default_factory=dict)
    species_order: Tuple[TreeName, ...] = ()
    missing_diameter: int = 0

    @property
    def qmd(self) -> QuadraticMeanDiameter:
        """Stand quadratic mean diameter, reduced from the total component series."""
        if not self.total_components:
            return QuadraticMeanDiameter(0.0, precision=0.0)
        return qmd_from_series(self.total_components)


def aggregate_plots(
    plots: Iterable[CircularPlot],
    *,
    warn_missing_diameter: bool = True,
) -> PlotAggregation:
    """Estimate per-hectare stand metrics as the mean over ``plots``.

    One pass over every plot's trees accumulates, per species, the per-hectare
    stem count, basal area, sum of cubed diameters and basal-area weighted height
    sum. See the module docstring for the conventions this applies.

    Args:
        plots: The plots to aggregate. They form one population; a caller with
            several independent populations aggregates each separately.
        warn_missing_diameter: Whether to warn about tree records carrying no
            diameter. A simulation refreshing its metrics every step passes
            ``False``: the stand it was built from already reported this once, and
            repeating it per step is noise rather than information. The count is
            reported on the result either way.

    Returns:
        A :class:`PlotAggregation` holding the metrics and the per-plot series
        they were reduced from.
    """
    plots = list(plots)
    missing_diameter = 0

    # 1. Single pass over each plot: per-species per-hectare component sums.
    species_order: List[TreeName] = []
    seen: set = set()
    per_plot_species: List[Dict[TreeName, Dict[str, float]]] = []
    per_plot_total: List[Dict[str, float]] = []

    for plot in plots:
        area_ha = plot.area_ha or 1.0
        # The effective area is the visible portion of the plot.
        visible = 1.0 - float(getattr(plot, "occlusion", 0.0) or 0.0)
        effective_area_ha = area_ha * visible if visible > 0 else area_ha

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
                acc = {k: 0.0 for k in COMPONENT_KEYS}
                plot_acc[sp] = acc
            # A record with no diameter is still a stem, but it can carry no
            # basal area. Counting it in the QMD/BAWAD denominators as if it were
            # a zero-diameter tree would drag both downwards, so the
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
        plot_total = {k: 0.0 for k in COMPONENT_KEYS}
        for sp, acc in plot_acc.items():
            per_ha = {k: acc[k] / effective_area_ha for k in COMPONENT_KEYS}
            plot_species[sp] = per_ha
            for k in COMPONENT_KEYS:
                plot_total[k] += per_ha[k]
            if sp not in seen:
                seen.add(sp)
                species_order.append(sp)
        per_plot_species.append(plot_species)
        per_plot_total.append(plot_total)

    if missing_diameter and warn_missing_diameter:
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

    stems_dict: Dict[MetricKey, Stems] = {}
    ba_dict: Dict[MetricKey, StandBasalArea] = {}
    bawad_dict: Dict[MetricKey, BasalAreaWeightedDiameter] = {}
    hl_dict: Dict[MetricKey, LoreysMeanHeight] = {}
    components: Dict[Any, Dict[str, List[float]]] = {
        sp: {key: component_series(sp, key) for key in COMPONENT_KEYS} for sp in species_order
    }

    # The stand total is the per-plot sum over species, which is exactly the
    # elementwise sum of the per-species series, so both are built the same way
    # and both stay covariance-aware.
    total_series = {
        key: [plot_total[key] for plot_total in per_plot_total] for key in COMPONENT_KEYS
    }

    for sp in species_order:
        value, precision = metrics_from_series(components[sp])
        stems_dict[sp] = Stems(value=value["stems"], species=sp, precision=precision["stems"])
        ba_dict[sp] = StandBasalArea(value=value["ba"], species=sp, precision=precision["ba"])
        bawad_dict[sp] = BasalAreaWeightedDiameter(value["bawad"], precision=precision["bawad"])
        hl_dict[sp] = LoreysMeanHeight(value["hl"], precision=precision["hl"])

    total_value, total_precision = metrics_from_series(total_series)
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

    return PlotAggregation(
        stems=stems_dict,
        basal_area=ba_dict,
        bawad=bawad_dict,
        loreys_height=hl_dict,
        species_components=components,
        total_components=total_series,
        species_order=tuple(species_order),
        missing_diameter=missing_diameter,
    )
