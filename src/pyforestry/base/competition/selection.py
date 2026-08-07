"""Rules for deciding which neighbours count as competitors.

A competition index value is only meaningful alongside the rule that chose its
competitors: the same formula on the same stand ranks trees differently under
different rules. The formula and the rule are therefore separate, composable
objects here. That framing, and this particular set of four approaches, is from
Maleki, Kiviste & Korjus (2015); the rules themselves are their own authors'.

Every number in these rules is a parameter with a literature default, not a
fixed value -- the defaults are one study's choices, and are meant to be varied::

    MeanHeightRadius(fraction=0.25)          # not stuck at 0.4
    LeeGadowRadius(k=3.0)                    # the paper tests k = 2 and 3
    BitterlichBAF(basal_area_factor=4.0)     # 1, 2 and 4 in the paper
    SearchCone(opening_angle_deg=80.0)       # 100, 80 and 60 in the paper
    FixedRadius(8.0, min_size_ratio=0.3, elimination_angle_deg=30.0)

1. :class:`FixedRadius` -- plain geometry, no citation.
   :class:`MeanHeightRadius` -- a fraction of stand mean height,
   ``CZR = 0.4 * h`` after Sims et al. (2009). The influence-zone concept it
   rests on is Staebler (1951).
2. :class:`LeeGadowRadius` -- a dynamic radius ``k * sqrt(10000 / N)``, i.e. a
   multiple of mean spacing, after Lee & von Gadow (1997).
3. :class:`BitterlichBAF` -- variable-radius selection after Bitterlich (1952):
   a tree competes when it falls inside *its own* angle-count limiting distance
   ``50 * d_j / sqrt(BAF)``, ``d_j`` in metres.
4. :class:`SearchCone` -- the reversed search-cone / angular-height method after
   Pretzsch (2009), with the apex at the subject's stem base or crown base.
5. :class:`NearestNeighbours` -- the ``n`` closest stems; plain geometry.

The radius-based rules also take a **competition elimination angle**: a
neighbour standing in the shadow of a nearer competitor, within a cone of
``elimination_angle_deg``, is dropped. The 2015 comparison applies this at 30
degrees alongside the ``d_j >= 0.3 * d_i`` size screen for its approaches 1
and 2, so reproducing those needs both.

Each rule that implements somebody's published proposal exposes it as
``.source``; :func:`selector_source` reads it, returning ``None`` for the two
that are plain geometry.

Only the radius rules (1 and 2) define a competition *zone* -- a circle fixed
before the data are seen. The variable-reach rules (3, 4, 5) report
``Selection.zone_radius_m = None``, which means Lorimer's ``Sdrl1`` and the
proportional-area edge correction do not apply to them; see :class:`Selection`.
"""

from dataclasses import dataclass
from math import asin, degrees, pi, radians, sqrt, tan
from typing import List, Optional, Protocol, Sequence, Tuple

from .geometry import mean_spacing_m
from .sources import SELECTOR_SOURCES

__all__ = [
    "BitterlichBAF",
    "Candidates",
    "CompetitorSelector",
    "FixedRadius",
    "LeeGadowRadius",
    "MeanHeightRadius",
    "NearestNeighbours",
    "SearchCone",
    "Selection",
    "SelectionContext",
    "selector_source",
]


@dataclass(frozen=True)
class Candidates:
    """The per-tree data a selector may look at, for one subject's neighbourhood.

    Bundled rather than passed as loose arrays because different rules need
    different columns: the size screen needs diameters, the elimination angle
    needs bearings, and the search cone needs heights.

    Attributes:
        diameters_cm: Diameter of every candidate tree (cm).
        distances_m: Distance from the subject to every candidate (m); the
            subject's own entry is 0.
        bearings_rad: Compass bearing from the subject to every candidate
            (radians). Required by ``elimination_angle_deg``.
        heights_m: Height of every candidate (m), where known. Required by
            :class:`SearchCone`.
        crown_base_heights_m: Crown base height of every candidate (m), where
            known. Required by :class:`SearchCone` with ``apex="crown_base"``.
    """

    diameters_cm: Tuple[float, ...]
    distances_m: Tuple[float, ...]
    bearings_rad: Optional[Tuple[float, ...]] = None
    heights_m: Optional[Tuple[Optional[float], ...]] = None
    crown_base_heights_m: Optional[Tuple[Optional[float], ...]] = None

    def __post_init__(self) -> None:
        """Check every supplied column has one entry per candidate."""
        n = len(self.diameters_cm)
        for name in ("distances_m", "bearings_rad", "heights_m", "crown_base_heights_m"):
            values = getattr(self, name)
            if values is not None and len(values) != n:
                raise ValueError(f"{name} has {len(values)} entries but there are {n} candidates.")

    def __len__(self) -> int:
        """Number of candidate trees."""
        return len(self.diameters_cm)


@dataclass(frozen=True)
class SelectionContext:
    """Stand-level quantities a selector may need to size its search radius.

    Attributes:
        stems_per_ha: Stem density (trees/ha), for :class:`LeeGadowRadius`.
        mean_height_m: Arithmetic mean height (m), for :class:`MeanHeightRadius`.
    """

    stems_per_ha: Optional[float] = None
    mean_height_m: Optional[float] = None


@dataclass(frozen=True)
class Selection:
    """The competitors a selector picked for one subject tree.

    Attributes:
        indices: Positions of the selected competitors in the caller's tree list.
        distances_m: Distance from the subject to each selected competitor (m).
        zone_radius_m: The competition-zone radius that was applied (m), or
            ``None`` for a selector whose zone is not a circle fixed ahead of the
            data. Lorimer's ``Sdrl1`` and the proportional-area edge correction
            both need such a radius, so both are unavailable when it is ``None``
            -- substituting the reach below would make them circular, since a
            neighbourhood truncated by the plot boundary reaches less far and
            would report itself as needing less correction.
        reach_m: Distance to the farthest retained competitor (m), or ``None``
            when nothing was retained. Descriptive only: it says how far this
            subject's selection actually went.
    """

    indices: Tuple[int, ...]
    distances_m: Tuple[float, ...]
    zone_radius_m: Optional[float] = None
    reach_m: Optional[float] = None


class CompetitorSelector(Protocol):
    """Chooses competitors for a subject tree from a set of candidates."""

    def select(
        self, subject_index: int, candidates: Candidates, context: SelectionContext
    ) -> Selection:
        """Return the competitors for ``subject_index``.

        Args:
            subject_index: Index of the subject tree within ``candidates``.
            candidates: Per-tree data for the neighbourhood.
            context: Stand-level quantities for radius-sizing selectors.

        Returns:
            The chosen competitors.
        """
        ...


def _angular_gap(a: float, b: float) -> float:
    """Smallest absolute angle between two bearings (radians)."""
    gap = abs(a - b) % (2.0 * pi)
    return min(gap, 2.0 * pi - gap)


def _screen(
    subject_index: int,
    candidates: Candidates,
    within: Sequence[bool],
    min_size_ratio: float,
    elimination_angle_deg: float = 0.0,
) -> Tuple[List[int], List[float]]:
    """Drop the subject, undersized neighbours, and shadowed neighbours.

    The elimination angle is applied nearest-first: a candidate is dropped when
    an already-accepted, nearer competitor lies within half the elimination
    angle of the same bearing, i.e. when it stands in that competitor's shadow.
    """
    d_i = candidates.diameters_cm[subject_index]
    order = sorted(
        (j for j in range(len(candidates)) if j != subject_index),
        key=lambda j: candidates.distances_m[j],
    )

    if elimination_angle_deg > 0 and candidates.bearings_rad is None:
        raise ValueError(
            "elimination_angle_deg needs bearings; Candidates.bearings_rad is not set."
        )
    half_angle = radians(elimination_angle_deg) / 2.0

    keep_indices: List[int] = []
    keep_distances: List[float] = []
    for j in order:
        if not within[j]:
            continue
        if candidates.diameters_cm[j] < min_size_ratio * d_i:
            continue
        if half_angle > 0:
            bearings = candidates.bearings_rad
            assert bearings is not None  # guarded above
            shadowed = any(
                _angular_gap(bearings[j], bearings[k]) < half_angle for k in keep_indices
            )
            if shadowed:
                continue
        keep_indices.append(j)
        keep_distances.append(float(candidates.distances_m[j]))

    # Report in input order, so results line up with the caller's tree list.
    paired = sorted(zip(keep_indices, keep_distances, strict=True))
    return [i for i, _ in paired], [d for _, d in paired]


@dataclass(frozen=True)
class FixedRadius:
    """Competitors are the trees within a fixed radius of the subject.

    Attributes:
        radius_m: The competition-zone radius (m).
        min_size_ratio: Keep a neighbour only when ``d_j >= ratio * d_i``.
            ``0.0`` keeps everything; the 2015 comparison uses ``0.3``.
        elimination_angle_deg: Drop a neighbour standing within this angle of a
            nearer competitor's bearing. ``0.0`` disables; the 2015 comparison
            uses ``30.0``.
    """

    radius_m: float
    min_size_ratio: float = 0.0
    elimination_angle_deg: float = 0.0

    def select(
        self, subject_index: int, candidates: Candidates, context: SelectionContext
    ) -> Selection:
        """Select every tree inside ``radius_m``."""
        within = [d <= self.radius_m for d in candidates.distances_m]
        idx, dist = _screen(
            subject_index, candidates, within, self.min_size_ratio, self.elimination_angle_deg
        )
        return Selection(tuple(idx), tuple(dist), self.radius_m, max(dist) if dist else None)


@dataclass(frozen=True)
class MeanHeightRadius:
    """Influence-zone radius set as a fraction of stand mean height.

    ``CZR = fraction * mean_height``; ``fraction=0.4`` is the value tested by
    Sims et al. (2009), not a fixed constant.

    Attributes:
        fraction: Multiple of mean height to use as the radius.
        min_size_ratio: Minimum ``d_j / d_i`` for a neighbour to compete.
        elimination_angle_deg: Shadow angle; see :class:`FixedRadius`.
    """

    fraction: float = 0.4
    min_size_ratio: float = 0.0
    elimination_angle_deg: float = 0.0

    @property
    def source(self):
        """The publication this radius rule comes from: Sims et al. (2009)."""
        return SELECTOR_SOURCES["MeanHeightRadius"]

    def select(
        self, subject_index: int, candidates: Candidates, context: SelectionContext
    ) -> Selection:
        """Select every tree inside ``fraction * mean_height_m``."""
        if context.mean_height_m is None:
            raise ValueError("MeanHeightRadius needs SelectionContext.mean_height_m.")
        radius = self.fraction * context.mean_height_m
        return FixedRadius(radius, self.min_size_ratio, self.elimination_angle_deg).select(
            subject_index, candidates, context
        )


@dataclass(frozen=True)
class LeeGadowRadius:
    """Dynamic influence-zone radius scaled to mean spacing. Lee & von Gadow (1997).

    ``CZR = k * sqrt(10000 / N)``, where the square root is the mean distance
    between neighbours at ``N`` stems/ha. The 2015 comparison tests ``k = 2``
    and ``k = 3``.

    Attributes:
        k: Multiple of mean spacing.
        min_size_ratio: Minimum ``d_j / d_i`` for a neighbour to compete.
        elimination_angle_deg: Shadow angle; see :class:`FixedRadius`.
    """

    k: float = 2.0
    min_size_ratio: float = 0.0
    elimination_angle_deg: float = 0.0

    @property
    def source(self):
        """The publication this radius rule comes from: Lee & von Gadow (1997)."""
        return SELECTOR_SOURCES["LeeGadowRadius"]

    def select(
        self, subject_index: int, candidates: Candidates, context: SelectionContext
    ) -> Selection:
        """Select every tree inside ``k * mean spacing``."""
        if context.stems_per_ha is None:
            raise ValueError("LeeGadowRadius needs SelectionContext.stems_per_ha.")
        radius = self.k * mean_spacing_m(context.stems_per_ha)
        return FixedRadius(radius, self.min_size_ratio, self.elimination_angle_deg).select(
            subject_index, candidates, context
        )


@dataclass(frozen=True)
class BitterlichBAF:
    """Variable-radius competitor selection. Bitterlich (1952).

    An angle-count sweep is taken from the subject tree, and a **neighbour**
    competes when its own stem subtends at least the gauge angle, i.e. when

        ``l_ij <= 50 * d_j / sqrt(BAF)`` with ``d_j`` in **metres**

    equivalently ``l_ij <= d_j / (2 * sqrt(BAF))`` for ``d_j`` in cm. A tree sits
    exactly on the limit when ``BAF = 10000 * (d_j / (2 * l_ij))^2``. The
    limiting distance therefore belongs to the competitor, not to the subject:
    at BAF 2 a 60 cm neighbour competes out to 21.2 m while a 10 cm one stops at
    3.5 m, which is the whole point of a variable-radius sample -- large trees
    are counted from further away.

    Two departures from the 2015 comparison's Table 1, both to follow Bitterlich:

    * It prints the *subject's* diameter in the limiting distance. That gives
      every neighbour one radius set by the subject's size, which inverts the
      method: the 60 cm neighbour above would be excluded and the 10 cm one kept.
    * It writes the diameter in cm against a footnote defining ``d`` in cm, which
      only balances once the diameter is converted -- at BAF 2 a 20 cm stem
      reaches 7.07 m, not 1.0 m. The paper's own BAF-to-angle table corroborates
      the conversion: BAF 1, 2 and 4 correspond to gauge angles of 1.15, 1.62 and
      2.30 degrees, which is ``2 * arcsin(sqrt(BAF / 10000))``.

    Because each neighbour carries its own limiting distance, the selected zone
    is not a circle and :attr:`Selection.zone_radius_m` is ``None``; see
    :class:`Selection` for what that costs.

    Attributes:
        basal_area_factor: The BAF in m^2/ha; the 2015 comparison tests 1, 2, 4.
        min_size_ratio: Minimum ``d_j / d_i`` for a neighbour to compete.
        elimination_angle_deg: Shadow angle; see :class:`FixedRadius`.
    """

    basal_area_factor: float = 2.0
    min_size_ratio: float = 0.0
    elimination_angle_deg: float = 0.0

    def __post_init__(self) -> None:
        """Reject a non-positive basal area factor."""
        if self.basal_area_factor <= 0:
            raise ValueError("basal_area_factor must be positive.")

    @property
    def source(self):
        """The publication this selection rule comes from: Bitterlich (1952)."""
        return SELECTOR_SOURCES["BitterlichBAF"]

    @property
    def gauge_angle_deg(self) -> float:
        """The angle-count gauge angle this BAF corresponds to (degrees)."""
        return degrees(2.0 * asin(sqrt(self.basal_area_factor / 10000.0)))

    def limiting_distance_m(self, diameter_cm: float) -> float:
        """Farthest distance at which a stem of ``diameter_cm`` is still tallied (m)."""
        return 50.0 * (float(diameter_cm) / 100.0) / sqrt(self.basal_area_factor)

    def select(
        self, subject_index: int, candidates: Candidates, context: SelectionContext
    ) -> Selection:
        """Select every tree inside its own angle-count limiting distance."""
        within = [
            distance <= self.limiting_distance_m(diameter)
            for diameter, distance in zip(
                candidates.diameters_cm, candidates.distances_m, strict=True
            )
        ]
        idx, dist = _screen(
            subject_index, candidates, within, self.min_size_ratio, self.elimination_angle_deg
        )
        # Each neighbour has its own limiting distance, so the selected zone is
        # not a circle and has no radius to correct against.
        return Selection(tuple(idx), tuple(dist), None, max(dist) if dist else None)


@dataclass(frozen=True)
class SearchCone:
    """Reversed search-cone / angular-height selection. Pretzsch (2009).

    A cone opens upward from the subject tree with opening angle ``beta``; a
    neighbour competes when its top penetrates that cone::

        l_ij < h_j / tan(90 - beta/2)                    apex at the stem base
        l_ij < (h_j - cbh_i) / tan(90 - beta/2)          apex at the crown base

    so a tall neighbour competes from further away than a short one, and a
    suppressed neighbour close by may not compete at all.

    The 2015 comparison prints ``h_i`` (the *subject's* height) in both
    equations. That cannot be the intent: the accompanying text defines
    competitors as "neighbouring trees whose heights are greater than" the
    critical value, and with ``h_i`` the neighbour's own size plays no part at
    all, collapsing the cone into a plain fixed radius. The competitor's height
    is used here, which is also the method as Pretzsch defines it.

    Attributes:
        opening_angle_deg: The cone's opening angle ``beta``; the 2015
            comparison tests 100, 80 and 60 degrees.
        apex: ``"stem_base"`` (equation 4) or ``"crown_base"`` (equation 5),
            the latter needing the subject's crown base height.
        min_size_ratio: Minimum ``d_j / d_i`` for a neighbour to compete.
        elimination_angle_deg: Shadow angle; see :class:`FixedRadius`.
    """

    opening_angle_deg: float = 80.0
    apex: str = "stem_base"
    min_size_ratio: float = 0.0
    elimination_angle_deg: float = 0.0

    def __post_init__(self) -> None:
        """Reject an angle outside (0, 180) or an unknown apex."""
        if not 0.0 < self.opening_angle_deg < 180.0:
            raise ValueError("opening_angle_deg must be strictly between 0 and 180 degrees.")
        if self.apex not in ("stem_base", "crown_base"):
            raise ValueError(f"Unknown apex {self.apex!r}; use 'stem_base' or 'crown_base'.")

    @property
    def source(self):
        """The publication this selection rule comes from: Pretzsch (2009)."""
        return SELECTOR_SOURCES["SearchCone"]

    @property
    def _slope(self) -> float:
        """``tan(90 - beta/2)``: the cone's rise per unit horizontal distance."""
        return tan(radians(90.0 - self.opening_angle_deg / 2.0))

    def select(
        self, subject_index: int, candidates: Candidates, context: SelectionContext
    ) -> Selection:
        """Select the neighbours whose tops fall inside the cone.

        Raises:
            ValueError: If heights are missing, or ``apex="crown_base"`` without
                a crown base height for the subject.
        """
        if candidates.heights_m is None:
            raise ValueError(
                "SearchCone needs heights; Candidates.heights_m is not set. Impute "
                'them first with stand.impute("height_m").'
            )
        apex_height = 0.0
        if self.apex == "crown_base":
            crown_bases = candidates.crown_base_heights_m
            base = None if crown_bases is None else crown_bases[subject_index]
            if base is None:
                raise ValueError(
                    "SearchCone(apex='crown_base') needs the subject's crown base "
                    "height; Candidates.crown_base_heights_m is not set for it."
                )
            apex_height = float(base)

        slope = self._slope
        within: List[bool] = []
        for j, height in enumerate(candidates.heights_m):
            if height is None:
                within.append(False)
                continue
            rise = float(height) - apex_height
            within.append(rise > 0 and candidates.distances_m[j] < rise / slope)

        idx, dist = _screen(
            subject_index, candidates, within, self.min_size_ratio, self.elimination_angle_deg
        )
        # The cone's reach depends on each neighbour's own height, so there is no
        # zone radius -- only how far this subject's selection happened to go.
        return Selection(tuple(idx), tuple(dist), None, max(dist) if dist else None)


@dataclass(frozen=True)
class NearestNeighbours:
    """The ``n`` closest trees, irrespective of distance.

    Attributes:
        n: How many neighbours to take.
        min_size_ratio: Minimum ``d_j / d_i``, applied *before* taking the
            closest ``n`` so the screen cannot be swamped by suppressed stems.
        elimination_angle_deg: Shadow angle; see :class:`FixedRadius`. Applied
            before the count, so ``n`` counts unshadowed neighbours.
    """

    n: int = 4
    min_size_ratio: float = 0.0
    elimination_angle_deg: float = 0.0

    def __post_init__(self) -> None:
        """Reject a non-positive neighbour count."""
        if self.n <= 0:
            raise ValueError("n must be positive.")

    def select(
        self, subject_index: int, candidates: Candidates, context: SelectionContext
    ) -> Selection:
        """Select the ``n`` nearest qualifying trees."""
        within = [True] * len(candidates)
        idx, dist = _screen(
            subject_index, candidates, within, self.min_size_ratio, self.elimination_angle_deg
        )
        order = sorted(range(len(idx)), key=lambda k: dist[k])[: self.n]
        order.sort(key=lambda k: idx[k])
        chosen_idx = tuple(idx[k] for k in order)
        chosen_dist = tuple(dist[k] for k in order)
        # A count is not a zone: how far the n-th neighbour sits is an outcome of
        # the data, not a radius fixed in advance.
        return Selection(chosen_idx, chosen_dist, None, max(chosen_dist) if chosen_dist else None)


def selector_source(selector: object):
    """Return the publication a selector implements, if it has one.

    Args:
        selector: Any competitor selector.

    Returns:
        Its :class:`~pyforestry.base.contracts.SourceReference`, or ``None`` for
        the rules that are plain geometry rather than somebody's proposal
        (:class:`FixedRadius`, :class:`NearestNeighbours`).
    """
    return getattr(selector, "source", None)
