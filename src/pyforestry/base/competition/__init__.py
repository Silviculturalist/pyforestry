"""Individual-tree competition indices.

Eighteen indices -- seven distance-independent and eleven spatially explicit --
each attributed to the paper that proposed it, from Staebler (1951) through to
Schroder & Gadow (1999). Alongside them are the competitor-selection rules they
are used with, because an index value is only interpretable next to the rule that
chose its competitors.

    >>> from pyforestry.base.competition import competition_indices, FixedRadius
    >>> results = competition_indices(plot, indices=["Heg", "BAL"],
    ...                               selector=FixedRadius(8.0, min_size_ratio=0.3))
    >>> results[0].indices["Heg"]

Every number in a selection rule is a parameter with a literature default, not a
fixed value. The defaults are one study's choices and are meant to be varied::

    MeanHeightRadius(fraction=0.25)              # 0.4 is Sims et al.'s, not a law
    LeeGadowRadius(k=3.0)                        # k = 2 and 3 both tested
    BitterlichBAF(basal_area_factor=4.0)         # 1, 2 and 4 tested
    SearchCone(opening_angle_deg=60.0)           # 100, 80 and 60 tested
    SearchCone(80.0, apex="crown_base")          # apex at the crown base instead
    FixedRadius(8.0, min_size_ratio=0.3, elimination_angle_deg=30.0)

The last of those reproduces the size screen *and* the shadow screen that the
2015 comparison applies together for its approaches 1 and 2: a neighbour is
dropped when it is under ``0.3 * d_i``, or when it stands within 30 degrees of
the bearing of a nearer competitor.

Every index carries its own citation::

    >>> from pyforestry.base.competition import index_source
    >>> index_source("Heg")     # Hegyi (1974), not the review it was collected from
    >>> index_source("Sdrl2")   # Martin & Ek (1984)

Three layers:

* :mod:`~pyforestry.base.competition.indices` -- the formulas, each a pure
  function of a :class:`~pyforestry.base.competition.neighbourhood.Neighbourhood`.
* :mod:`~pyforestry.base.competition.selection` -- competitor selection rules.
* :func:`~pyforestry.base.competition.api.competition_indices` -- the entry point
  over a tree list, a ``CircularPlot`` or a ``Stand``.

Distance-dependent indices are biased low for trees near a plot boundary, whose
competition zone is partly unobserved. Every result reports
``observed_zone_fraction``, and by default the spatial indices are divided by it
(proportional-area weighting).

This package holds no science of its own. The set of eighteen was assembled and
compared by Maleki, Kiviste & Korjus (2015), which is why these particular
indices are here; see
:data:`~pyforestry.base.competition.sources.INDEX_SET_REVIEW`. Per-index
provenance is in :data:`~pyforestry.base.competition.sources.INDEX_SOURCES`.
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
    CompetitionIndex,
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
    index_source,
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
    Candidates,
    CompetitorSelector,
    FixedRadius,
    LeeGadowRadius,
    MeanHeightRadius,
    NearestNeighbours,
    SearchCone,
    Selection,
    SelectionContext,
    selector_source,
)
from .sources import INDEX_SET_REVIEW, INDEX_SOURCES, SELECTOR_SOURCES

__all__ = [
    "Candidates",
    "SearchCone",
    "selector_source",
    "index_source",
    "SELECTOR_SOURCES",
    "INDEX_SOURCES",
    "INDEX_SET_REVIEW",
    "CompetitionIndex",
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
    component_id="competition_indices",
    source=SourceReference(
        author="(none)",
        year=0,
        title="Individual-tree competition indices (pyforestry collection)",
        note=(
            "No primary publication, and none is possible: this package collects "
            "eighteen indices by eighteen different authors, each carrying its own "
            "citation in `INDEX_SOURCES` and reachable via `index_source(name)`. "
            "year=0 is a sentinel for 'not applicable', not a citation date. The "
            "particular set assembled here follows the comparison in Maleki, Kiviste & "
            "Korjus (2015), Forest Systems 24(2) e023, doi:10.5424/fs/2015242-05742 -- "
            "see `INDEX_SET_REVIEW`; that review supplies the selection and the "
            "abbreviations, not the science."
        ),
    ),
    species_groups={},
    units={
        "diameter": "cm",
        "distance": "m",
        "plot_area": "ha",
        "basal_area": "m2/ha",
    },
    kernel_names=("competition_indices", "compute_index", "index_source"),
    composes=tuple(sorted(INDEX_REGISTRY)),
    domain="competition",
)
