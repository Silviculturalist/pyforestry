"""Eighteen individual-tree competition indices, each attributed to its own author.

Seven distance-independent and eleven spatially explicit indices, spanning
Staebler (1951) to Schroder & Gadow (1999). Every index is a pure function of a
:class:`~pyforestry.base.competition.neighbourhood.Neighbourhood`, and every one
carries the citation of the paper that *proposed* it -- reachable as
:func:`index_source` or ``INDEX_REGISTRY[name].source``. The set was assembled
and compared by Maleki, Kiviste & Korjus (2015), who are credited for that
collection in :data:`~pyforestry.base.competition.sources.INDEX_SET_REVIEW` and
for nothing else.

Symbols follow the usual convention: ``d_i`` subject diameter (cm), ``d_j``
competitor diameter (cm), ``l_ij`` stem-to-stem distance (m), ``g`` basal area
(m^2), ``G`` plot basal area (m^2/ha), ``S`` plot area (ha), ``CZR``
competition-zone radius (m), ``CZ`` competition-zone area (m^2), ``O_ij``
influence-zone overlap (m^2).

Where the transcription departs from the 2015 review's Table 2 it does so to
follow the original, and says so at the point of use:

* **Martin & Ek (1984), ``Sdrl2``** -- the exponent is negative. Table 2 prints
  ``exp(+16*l_ij/(d_i+d_j))``, as does Wang et al. (2012) Table 1, which would
  make a competitor's contribution grow without bound with distance: at
  ``d_i+d_j = 40 cm`` one 10 m away would count 24 times one at 2 m. See
  :func:`martin_ek_sdrl2`.
* **Rouvinen & Kuuluvainen** -- Table 2 dates the work 1977; it is 1997.
* The angular indices (``SAng1``, ``SAng2``, ``SdrAng``) convert diameters from
  cm to m before the arctangent. As printed the ratio mixes cm with m, putting a
  20 cm stem 5 m away at 76 degrees instead of 2.3. See :func:`lin_sang1`.
"""

from dataclasses import dataclass
from math import atan, exp, pi, sqrt
from typing import Callable, Dict

from pyforestry.base.contracts import SourceReference

from .geometry import circle_intersection_area, circle_overlap_length
from .neighbourhood import Neighbourhood
from .sources import INDEX_SOURCES

__all__ = [
    "INDEX_REGISTRY",
    "CompetitionIndex",
    "index_source",
    "NON_SPATIAL_INDICES",
    "SPATIAL_INDICES",
    "alemdag_almdg",
    "basal_area_of_larger_bal",
    "basal_area_ratio_bar",
    "basal_area_sum_ba_gj",
    "bal_ratio_balr",
    "balmod",
    "bella_sodr",
    "compute_index",
    "daniels_sbar",
    "diameter_ratio_drg",
    "gerrard_sor",
    "hegyi",
    "lin_sang1",
    "lorimer_sdrl1",
    "martin_ek_sdrl2",
    "rouvinen_kuuluvainen_sang2",
    "rouvinen_kuuluvainen_sdrang",
    "staebler_sl",
    "sum_diameter_ratio_sdr",
]

# ---------------------------------------------------------------------------
# Non-spatially explicit indices (Table 2, upper block)
# ---------------------------------------------------------------------------


def basal_area_sum_ba_gj(n: Neighbourhood) -> float:
    """``BA-gj``: basal area of the neighbours per hectare. Steneker & Jarvis (1963).

    ``sum(g_j) / S`` -- every neighbour counts, regardless of size.

    Args:
        n: The neighbourhood. Needs ``plot_area_ha``.

    Returns:
        Competitor basal area in m^2/ha.
    """
    n.require("plot_area_ha")
    return sum(n.competitor_basal_areas_m2()) / n.plot_area_ha  # type: ignore[operator]


def basal_area_of_larger_bal(n: Neighbourhood) -> float:
    """``BAL``: basal area of trees larger than the subject. Wykoff et al. (1982).

    ``sum(g_j for d_j > d_i) / S``. The single most widely used distance-
    independent index.

    Args:
        n: The neighbourhood. Needs ``plot_area_ha``.

    Returns:
        Basal area of larger trees in m^2/ha.
    """
    n.require("plot_area_ha")
    larger = n.larger_competitor_mask()
    areas = n.competitor_basal_areas_m2()
    return sum(g for g, is_larger in zip(areas, larger, strict=True) if is_larger) / (
        n.plot_area_ha  # type: ignore[operator]
    )


def sum_diameter_ratio_sdr(n: Neighbourhood) -> float:
    """``Sdr``: summed diameter ratio per hectare. Lorimer (1983).

    ``((sum(d_j)) / d_i) / S``.

    Args:
        n: The neighbourhood. Needs ``plot_area_ha``.

    Returns:
        The index in ha^-1.
    """
    n.require("plot_area_ha")
    return (sum(n.competitor_dbh_cm) / n.subject_dbh_cm) / n.plot_area_ha  # type: ignore[operator]


def diameter_ratio_drg(n: Neighbourhood) -> float:
    """``dr_g``: subject diameter over the plot quadratic mean diameter. Hamilton (1986).

    ``d_i / d_g``. Above 1 the subject is larger than the average tree, so unlike
    every other index here a *high* value means *less* competition.

    Args:
        n: The neighbourhood. Needs ``plot_qmd_cm``.

    Returns:
        The dimensionless ratio.
    """
    n.require("plot_qmd_cm")
    return n.subject_dbh_cm / n.plot_qmd_cm  # type: ignore[operator]


def basal_area_ratio_bar(n: Neighbourhood) -> float:
    """``BAr``: summed basal-area ratio per hectare. Corona & Ferrara (1989).

    ``((sum(g_j)) / g_i) / S`` -- the basal-area analogue of ``Sdr``.

    Args:
        n: The neighbourhood. Needs ``plot_area_ha``.

    Returns:
        The index in ha^-1.
    """
    n.require("plot_area_ha")
    return (sum(n.competitor_basal_areas_m2()) / n.subject_basal_area_m2) / (
        n.plot_area_ha  # type: ignore[operator]
    )


def bal_ratio_balr(n: Neighbourhood) -> float:
    """``BALr``: BAL as a share of plot basal area. Vanclay (1991).

    ``sum(g_j for d_j > d_i) / G``. Both terms are per-hectare, so the result is
    dimensionless and bounded by 1 -- it is the proportion of the stand's basal
    area held in trees larger than the subject.

    Args:
        n: The neighbourhood. Needs ``plot_area_ha`` and ``plot_basal_area_m2_ha``.

    Returns:
        A dimensionless share in ``[0, 1]``.
    """
    n.require("plot_area_ha", "plot_basal_area_m2_ha")
    return basal_area_of_larger_bal(n) / n.plot_basal_area_m2_ha  # type: ignore[operator]


def balmod(n: Neighbourhood) -> float:
    """``BALMOD``: BALr scaled by relative spacing. Schroder & Gadow (1999).

    ``[sum(g_j for d_j > d_i) / G] / RS`` with ``RS = sqrt(S/N) / H_dom`` (``S``
    in m^2). Dividing by relative spacing lets the index distinguish stands that
    share a BALr but differ in how crowded they are.

    Args:
        n: The neighbourhood. Needs ``plot_area_ha``, ``plot_basal_area_m2_ha``
            and ``relative_spacing``.

    Returns:
        The modified BAL ratio.
    """
    n.require("plot_area_ha", "plot_basal_area_m2_ha", "relative_spacing")
    if n.relative_spacing <= 0:  # type: ignore[operator]
        raise ValueError("relative_spacing must be positive.")
    return bal_ratio_balr(n) / n.relative_spacing  # type: ignore[operator]


# ---------------------------------------------------------------------------
# Influence-zone overlap indices (Table 2, first spatial group)
# ---------------------------------------------------------------------------


def staebler_sl(n: Neighbourhood) -> float:
    """``Sl``: summed linear overlap of influence zones. Staebler (1951).

    ``sum(l_ij)`` where ``l_ij`` is here the *overlap length*
    ``max(0, CZR_i + CZR_j - distance)``, not the stem distance. Table 2 reuses
    the symbol ``l_ij`` for both; the paper's own text places this index in the
    "influence-zone overlap" group, which fixes the reading.

    Args:
        n: The neighbourhood. Needs ``distances_m``, ``subject_crown_radius_m``
            and ``competitor_crown_radius_m``.

    Returns:
        Total overlap length in m.
    """
    n.require("distances_m", "subject_crown_radius_m", "competitor_crown_radius_m")
    return sum(
        circle_overlap_length(n.subject_crown_radius_m, r_j, l_ij)  # type: ignore[arg-type]
        for r_j, l_ij in zip(
            n.competitor_crown_radius_m,  # type: ignore[arg-type]
            n.distances_m,  # type: ignore[arg-type]
            strict=True,
        )
    )


def gerrard_sor(n: Neighbourhood) -> float:
    """``SOr``: overlap area as a share of the influence zone. Gerrard (1969).

    ``sum(O_ij / CZ)`` with ``CZ = pi * CZR_i^2``. Gerrard's competition
    quotient: how many times over the subject's growing space is claimed by
    neighbours.

    Args:
        n: The neighbourhood. Needs ``distances_m``, ``subject_crown_radius_m``
            and ``competitor_crown_radius_m``.

    Returns:
        The dimensionless quotient.
    """
    n.require("distances_m", "subject_crown_radius_m", "competitor_crown_radius_m")
    zone_area = pi * n.subject_crown_radius_m**2  # type: ignore[operator]
    if zone_area <= 0:
        raise ValueError("subject_crown_radius_m must be positive.")
    return (
        sum(
            circle_intersection_area(n.subject_crown_radius_m, r_j, l_ij)  # type: ignore[arg-type]
            for r_j, l_ij in zip(
                n.competitor_crown_radius_m,  # type: ignore[arg-type]
                n.distances_m,  # type: ignore[arg-type]
                strict=True,
            )
        )
        / zone_area
    )


def bella_sodr(n: Neighbourhood) -> float:
    """``SOdr``: Gerrard's quotient weighted by diameter ratio. Bella (1971).

    ``sum((O_ij * d_j) / (CZ * d_i))``.

    Args:
        n: The neighbourhood. Needs ``distances_m``, ``subject_crown_radius_m``
            and ``competitor_crown_radius_m``.

    Returns:
        The dimensionless index.
    """
    n.require("distances_m", "subject_crown_radius_m", "competitor_crown_radius_m")
    zone_area = pi * n.subject_crown_radius_m**2  # type: ignore[operator]
    if zone_area <= 0:
        raise ValueError("subject_crown_radius_m must be positive.")
    total = 0.0
    for d_j, r_j, l_ij in zip(
        n.competitor_dbh_cm,
        n.competitor_crown_radius_m,  # type: ignore[arg-type]
        n.distances_m,  # type: ignore[arg-type]
        strict=True,
    ):
        overlap = circle_intersection_area(n.subject_crown_radius_m, r_j, l_ij)  # type: ignore[arg-type]
        total += (overlap * d_j) / (zone_area * n.subject_dbh_cm)
    return total


# ---------------------------------------------------------------------------
# Size-ratio spatial indices (Table 2, second spatial group)
# ---------------------------------------------------------------------------


def daniels_sbar(n: Neighbourhood) -> float:
    """``SBAr``: subject basal area against the competitors'. Daniels et al. (1986).

    ``(d_i^2 * N_c) / sum(d_j^2)``. Like ``dr_g``, a *high* value means the
    subject dominates its neighbours, i.e. less competition.

    Args:
        n: The neighbourhood.

    Returns:
        The dimensionless ratio.

    Raises:
        ValueError: If there are no competitors (the denominator would be zero).
    """
    denominator = sum(d * d for d in n.competitor_dbh_cm)
    if denominator <= 0:
        raise ValueError("SBAr is undefined without competitors of positive diameter.")
    return (n.subject_dbh_cm**2 * n.n_competitors) / denominator


def hegyi(n: Neighbourhood) -> float:
    """``Heg``: the Hegyi (1974) size-ratio distance-weighted index.

    ``sum(d_j / (d_i * l_ij))``. The most widely used distance-dependent index.

    Args:
        n: The neighbourhood. Needs ``distances_m``.

    Returns:
        The index in m^-1.
    """
    n.require("distances_m")
    return sum(
        d_j / (n.subject_dbh_cm * l_ij)
        for d_j, l_ij in zip(n.competitor_dbh_cm, n.distances_m, strict=True)  # type: ignore[arg-type]
    )


def lin_sang1(n: Neighbourhood) -> float:
    """``SAng1``: summed angular size of the competitors. Lin (1974).

    ``2 * sum(arctan(d_j / (2 * l_ij)))`` -- the horizontal angle each competitor
    stem subtends at the subject.

    Diameters are converted from cm to m first. Table 2 prints ``d_j`` in cm
    against ``l_ij`` in m, which is dimensionally inconsistent: a 20 cm stem 5 m
    away would come out at 76 degrees rather than the correct 2.3.

    Args:
        n: The neighbourhood. Needs ``distances_m``.

    Returns:
        The summed angle in radians.
    """
    n.require("distances_m")
    return 2.0 * sum(
        atan((d_j / 100.0) / (2.0 * l_ij))
        for d_j, l_ij in zip(n.competitor_dbh_cm, n.distances_m, strict=True)  # type: ignore[arg-type]
    )


def rouvinen_kuuluvainen_sang2(n: Neighbourhood) -> float:
    """``SAng2``: summed horizontal angle. Rouvinen & Kuuluvainen (1997).

    ``sum(arctan(d_j / l_ij))``, diameters converted to m (see :func:`lin_sang1`).

    Args:
        n: The neighbourhood. Needs ``distances_m``.

    Returns:
        The summed angle in radians.
    """
    n.require("distances_m")
    return sum(
        atan((d_j / 100.0) / l_ij)
        for d_j, l_ij in zip(n.competitor_dbh_cm, n.distances_m, strict=True)  # type: ignore[arg-type]
    )


def rouvinen_kuuluvainen_sdrang(n: Neighbourhood) -> float:
    """``SdrAng``: horizontal angle weighted by diameter ratio. Rouvinen & Kuuluvainen (1997).

    ``sum((d_j / d_i) * arctan(d_j / l_ij))``, diameters converted to m in the
    arctangent (the ``d_j / d_i`` ratio is unit-free either way).

    Args:
        n: The neighbourhood. Needs ``distances_m``.

    Returns:
        The weighted angle sum in radians.
    """
    n.require("distances_m")
    return sum(
        (d_j / n.subject_dbh_cm) * atan((d_j / 100.0) / l_ij)
        for d_j, l_ij in zip(n.competitor_dbh_cm, n.distances_m, strict=True)  # type: ignore[arg-type]
    )


def alemdag_almdg(n: Neighbourhood) -> float:
    """``Almdg``: potentially available growing space. Alemdag (1978).

    ``sum(pi * [(l_ij * d_i) / (d_i + d_j)]^2 * (d_j / l_ij) / sum(d_j / l_ij))``.

    The bracketed term is the radius (m) at which the subject and competitor
    exert equal influence along the line joining them, so each summand is an
    area weighted by that competitor's share of the total size-over-distance.

    Args:
        n: The neighbourhood. Needs ``distances_m``.

    Returns:
        Growing space in m^2.

    Raises:
        ValueError: If there are no competitors.
    """
    n.require("distances_m")
    ratios = [
        d_j / l_ij
        for d_j, l_ij in zip(n.competitor_dbh_cm, n.distances_m, strict=True)  # type: ignore[arg-type]
    ]
    total_ratio = sum(ratios)
    if total_ratio <= 0:
        raise ValueError("Almdg is undefined without competitors.")
    total = 0.0
    for d_j, l_ij, ratio in zip(n.competitor_dbh_cm, n.distances_m, ratios, strict=True):  # type: ignore[arg-type]
        equal_influence_radius_m = (l_ij * n.subject_dbh_cm) / (n.subject_dbh_cm + d_j)
        total += pi * equal_influence_radius_m**2 * (ratio / total_ratio)
    return total


def lorimer_sdrl1(n: Neighbourhood) -> float:
    """``Sdrl1``: diameter ratio damped by the square root of relative distance. Lorimer (1983).

    ``sum((d_j / d_i) / sqrt(l_ij / CZR))``.

    Args:
        n: The neighbourhood. Needs ``distances_m`` and
            ``competition_zone_radius_m``.

    Returns:
        The dimensionless index.
    """
    n.require("distances_m", "competition_zone_radius_m")
    if n.competition_zone_radius_m <= 0:  # type: ignore[operator]
        raise ValueError("competition_zone_radius_m must be positive.")
    return sum(
        (d_j / n.subject_dbh_cm) / sqrt(l_ij / n.competition_zone_radius_m)  # type: ignore[operator]
        for d_j, l_ij in zip(n.competitor_dbh_cm, n.distances_m, strict=True)  # type: ignore[arg-type]
    )


def martin_ek_sdrl2(n: Neighbourhood) -> float:
    """``Sdrl2``: diameter ratio with exponential distance decay. Martin & Ek (1984).

    ``sum((d_j / d_i) * exp(-16 * l_ij / (d_i + d_j)))`` with ``l_ij`` in m and
    diameters in cm -- the constant 16 assumes that mixture.

    **The exponent is negative here and positive in the source table.** Maleki
    et al. (2015) Table 2 and Wang et al. (2012) Table 1 both print
    ``exp(+16*...)``. That cannot be right: the index is a distance-decay
    weighting, and a positive exponent makes far competitors dominate near ones
    without bound (at ``d_i + d_j = 40 cm``, a competitor at 10 m would weigh 24
    times one at 2 m). The negative form is the one in general use and is what
    Martin & Ek describe as an "exponential weighting scheme".

    Args:
        n: The neighbourhood. Needs ``distances_m``.

    Returns:
        The dimensionless index.
    """
    n.require("distances_m")
    return sum(
        (d_j / n.subject_dbh_cm) * exp(-16.0 * l_ij / (n.subject_dbh_cm + d_j))
        for d_j, l_ij in zip(n.competitor_dbh_cm, n.distances_m, strict=True)  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompetitionIndex:
    """One competition index: its formula, its provenance and what it needs.

    Attributes:
        abbreviation: The short name used in the literature, e.g. ``"Heg"``.
        compute: The kernel, a pure function of a :class:`Neighbourhood`.
        source: The publication that proposed *this index*. Not the review it was
            collected from -- see
            :data:`pyforestry.base.competition.sources.INDEX_SET_REVIEW` for that.
        spatial: Whether the index needs stem-to-stem distances.
    """

    abbreviation: str
    compute: Callable[[Neighbourhood], float]
    source: SourceReference
    spatial: bool

    def __call__(self, neighbourhood: Neighbourhood) -> float:
        """Evaluate the index."""
        return self.compute(neighbourhood)


def _entry(abbrev: str, fn: Callable[[Neighbourhood], float], spatial: bool) -> CompetitionIndex:
    """Bind a kernel to its own primary citation."""
    return CompetitionIndex(abbrev, fn, INDEX_SOURCES[abbrev], spatial)


#: Non-spatial indices, keyed by the abbreviation used in the literature.
NON_SPATIAL_INDICES: Dict[str, CompetitionIndex] = {
    entry.abbreviation: entry
    for entry in (
        _entry("BA-gj", basal_area_sum_ba_gj, False),
        _entry("BAL", basal_area_of_larger_bal, False),
        _entry("Sdr", sum_diameter_ratio_sdr, False),
        _entry("drg", diameter_ratio_drg, False),
        _entry("BAr", basal_area_ratio_bar, False),
        _entry("BALr", bal_ratio_balr, False),
        _entry("BALMOD", balmod, False),
    )
}

#: Spatially explicit indices, keyed by the abbreviation used in the literature.
SPATIAL_INDICES: Dict[str, CompetitionIndex] = {
    entry.abbreviation: entry
    for entry in (
        _entry("Sl", staebler_sl, True),
        _entry("SOr", gerrard_sor, True),
        _entry("SOdr", bella_sodr, True),
        _entry("SBAr", daniels_sbar, False),
        _entry("Heg", hegyi, True),
        _entry("SAng1", lin_sang1, True),
        _entry("SAng2", rouvinen_kuuluvainen_sang2, True),
        _entry("SdrAng", rouvinen_kuuluvainen_sdrang, True),
        _entry("Almdg", alemdag_almdg, True),
        _entry("Sdrl1", lorimer_sdrl1, True),
        _entry("Sdrl2", martin_ek_sdrl2, True),
    )
}

#: Every index, keyed by abbreviation.
INDEX_REGISTRY: Dict[str, CompetitionIndex] = {**NON_SPATIAL_INDICES, **SPATIAL_INDICES}


def _resolve(name: str) -> CompetitionIndex:
    """Look an index up by abbreviation, case-insensitively."""
    key = {k.lower(): k for k in INDEX_REGISTRY}.get(name.lower())
    if key is None:
        raise KeyError(f"Unknown competition index {name!r}. Known: {sorted(INDEX_REGISTRY)}")
    return INDEX_REGISTRY[key]


def compute_index(name: str, neighbourhood: Neighbourhood) -> float:
    """Compute one index by its abbreviation.

    Args:
        name: The abbreviation, e.g. ``"Heg"`` or ``"BAL"``. Case-insensitive.
        neighbourhood: The subject tree and its competitors.

    Returns:
        The index value.

    Raises:
        KeyError: If ``name`` is not one of the eighteen indices.
    """
    return _resolve(name).compute(neighbourhood)


def index_source(name: str) -> SourceReference:
    """Return the publication that proposed the named index.

    Args:
        name: The abbreviation, e.g. ``"Heg"``. Case-insensitive.

    Returns:
        The index's own primary citation -- Hegyi (1974) for ``"Heg"``, not the
        review the set was collected from.

    Raises:
        KeyError: If ``name`` is not one of the eighteen indices.
    """
    return _resolve(name).source
