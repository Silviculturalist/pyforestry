"""Individual-tree competition indices.

Implements the eighteen indices reviewed by Maleki, Kiviste & Korjus (2015),
Table 2 -- seven distance-independent and eleven spatially explicit -- together
with the four competitor-selection rules the same paper tests, because an index
value is only interpretable alongside the rule that chose its competitors.

Three layers, from most to least general:

* :mod:`~pyforestry.base.competition.indices` -- the index formulas, each a pure
  function of a :class:`~pyforestry.base.competition.neighbourhood.Neighbourhood`.
* :mod:`~pyforestry.base.competition.selection` -- competitor selection rules.
* :func:`~pyforestry.base.competition.api.competition_indices` -- the convenience
  entry point over a tree list, a ``CircularPlot`` or a ``Stand``.

    >>> from pyforestry.base.competition import competition_indices, FixedRadius
    >>> results = competition_indices(plot, indices=["Heg", "BAL"],
    ...                               selector=FixedRadius(8.0, min_size_ratio=0.3))
    >>> results[0].indices["Heg"]

Distance-dependent indices are biased low for trees near a plot boundary, whose
competition zone is partly unobserved. Every result reports
``observed_zone_fraction``, and by default the spatial indices are divided by it
(proportional-area weighting).

Source:
    Maleki, K., Kiviste, A. & Korjus, H. (2015). *Analysis of individual tree
    competition effect on diameter growth of silver birch in Estonia.* Forest
    Systems 24(2), e023, 13 pp. doi:10.5424/fs/2015242-05742
"""

from pyforestry.base.contracts import FormulaDescriptor, SourceReference

from .api import TreeCompetition, competition_indices
from .geometry import (
    circle_intersection_area,
    circle_overlap_length,
    fraction_of_circle_inside_circle,
    mean_spacing_m,
)
from .indices import (
    INDEX_REGISTRY,
    NON_SPATIAL_INDICES,
    SPATIAL_INDICES,
    alemdag_almdg,
    bal_ratio_balr,
    balmod,
    basal_area_of_larger_bal,
    basal_area_ratio_bar,
    basal_area_sum_ba_gj,
    bella_sodr,
    compute_index,
    daniels_sbar,
    diameter_ratio_drg,
    gerrard_sor,
    hegyi,
    lin_sang1,
    lorimer_sdrl1,
    martin_ek_sdrl2,
    rouvinen_kuuluvainen_sang2,
    rouvinen_kuuluvainen_sdrang,
    staebler_sl,
    sum_diameter_ratio_sdr,
)
from .neighbourhood import MissingNeighbourhoodData, Neighbourhood
from .selection import (
    BitterlichBAF,
    CompetitorSelector,
    FixedRadius,
    LeeGadowRadius,
    MeanHeightRadius,
    NearestNeighbours,
    Selection,
    SelectionContext,
)

__all__ = [
    "BitterlichBAF",
    "CompetitorSelector",
    "FixedRadius",
    "INDEX_REGISTRY",
    "LeeGadowRadius",
    "MeanHeightRadius",
    "MissingNeighbourhoodData",
    "NON_SPATIAL_INDICES",
    "NearestNeighbours",
    "Neighbourhood",
    "SPATIAL_INDICES",
    "Selection",
    "SelectionContext",
    "TreeCompetition",
    "alemdag_almdg",
    "bal_ratio_balr",
    "balmod",
    "basal_area_of_larger_bal",
    "basal_area_ratio_bar",
    "basal_area_sum_ba_gj",
    "bella_sodr",
    "circle_intersection_area",
    "circle_overlap_length",
    "competition_indices",
    "compute_index",
    "daniels_sbar",
    "diameter_ratio_drg",
    "fraction_of_circle_inside_circle",
    "gerrard_sor",
    "hegyi",
    "lin_sang1",
    "lorimer_sdrl1",
    "martin_ek_sdrl2",
    "mean_spacing_m",
    "rouvinen_kuuluvainen_sang2",
    "rouvinen_kuuluvainen_sdrang",
    "staebler_sl",
    "sum_diameter_ratio_sdr",
]

DESCRIPTOR = FormulaDescriptor(
    component_id="maleki_2015_competition_indices",
    source=SourceReference(
        author="Maleki, K., Kiviste, A. & Korjus, H.",
        year=2015,
        title=(
            "Analysis of individual tree competition effect on diameter growth of "
            "silver birch in Estonia"
        ),
        appendix="Table 2",
        note=(
            "Forest Systems 24(2), e023, 13 pp. doi:10.5424/fs/2015242-05742. A review "
            "and comparison; each index carries its own original citation, given in the "
            "function docstrings (Steneker & Jarvis 1963, Wykoff et al. 1982, Lorimer "
            "1983, Hamilton 1986, Corona & Ferrara 1989, Vanclay 1991, Schroder & Gadow "
            "1999, Staebler 1951, Gerrard 1969, Bella 1971, Daniels et al. 1986, Hegyi "
            "1974, Lin 1974, Rouvinen & Kuuluvainen 1997, Alemdag 1978, Martin & Ek "
            "1984). Two departures from Table 2 as printed: the Martin & Ek exponent is "
            "negative here (the table's positive sign makes competition grow without "
            "bound with distance), and Rouvinen & Kuuluvainen is 1997, not 1977."
        ),
    ),
    species_groups={},
    units={
        "diameter": "cm",
        "distance": "m",
        "plot_area": "ha",
        "basal_area": "m2/ha",
    },
    kernel_names=("competition_indices", "compute_index"),
    domain="competition",
)
