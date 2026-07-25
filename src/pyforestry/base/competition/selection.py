"""Rules for deciding which neighbours count as competitors.

Maleki, Kiviste & Korjus (2015) make the point that a competition index value is
only meaningful alongside the rule that chose its competitors: the same formula
on the same stand ranks trees differently under different selection rules. The
formula and the rule are therefore kept as separate, composable objects here.

The four approaches the paper tests are all available:

1. :class:`FixedRadius` and :class:`MeanHeightRadius` -- a fixed influence zone,
   the latter as a fraction of stand mean height (``CZR = 0.4 * h`` in the paper,
   after Sims et al. 2009).
2. :class:`LeeGadowRadius` -- a dynamic radius ``k * sqrt(10000 / N)``, i.e. a
   multiple of mean spacing (Lee & Gadow 1997); the paper uses ``k = 2, 3``.
3. :class:`BitterlichBAF` -- Bitterlich (1952) variable-radius selection, a tree
   competing when ``l_ij <= d_i * sqrt(50 / BAF)``.
4. :class:`NearestNeighbours` -- the ``k`` closest stems.

Every selector can additionally apply the paper's minimum-size screen, keeping a
neighbour only when ``d_j >= min_size_ratio * d_i`` (``0.3`` in the paper).
"""

from dataclasses import dataclass
from math import sqrt
from typing import List, Optional, Protocol, Sequence, Tuple

from .geometry import mean_spacing_m

__all__ = [
    "BitterlichBAF",
    "CompetitorSelector",
    "FixedRadius",
    "LeeGadowRadius",
    "MeanHeightRadius",
    "NearestNeighbours",
    "SelectionContext",
    "Selection",
]


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
            ``None`` for a selector that does not define one (nearest-neighbour
            and Bitterlich selection have no single radius).
    """

    indices: Tuple[int, ...]
    distances_m: Tuple[float, ...]
    zone_radius_m: Optional[float] = None


class CompetitorSelector(Protocol):
    """Chooses competitors for a subject tree from a set of candidates."""

    def select(
        self,
        subject_index: int,
        diameters_cm: Sequence[float],
        distances_m: Sequence[float],
        context: SelectionContext,
    ) -> Selection:
        """Return the competitors for ``subject_index``.

        Args:
            subject_index: Index of the subject tree.
            diameters_cm: Diameter of every candidate tree (cm).
            distances_m: Distance from the subject to every candidate (m); the
                subject's own entry is 0.
            context: Stand-level quantities for radius-sizing selectors.

        Returns:
            The chosen competitors.
        """
        ...


def _screen(
    subject_index: int,
    diameters_cm: Sequence[float],
    distances_m: Sequence[float],
    within: Sequence[bool],
    min_size_ratio: float,
) -> Tuple[List[int], List[float]]:
    """Apply the size screen and drop the subject itself."""
    d_i = diameters_cm[subject_index]
    keep_indices: List[int] = []
    keep_distances: List[float] = []
    for j, inside in enumerate(within):
        if j == subject_index or not inside:
            continue
        if diameters_cm[j] < min_size_ratio * d_i:
            continue
        keep_indices.append(j)
        keep_distances.append(float(distances_m[j]))
    return keep_indices, keep_distances


@dataclass(frozen=True)
class FixedRadius:
    """Competitors are the trees within a fixed radius of the subject.

    Attributes:
        radius_m: The competition-zone radius (m).
        min_size_ratio: Keep a neighbour only when ``d_j >= ratio * d_i``.
            ``0.0`` keeps everything; the paper uses ``0.3``.
    """

    radius_m: float
    min_size_ratio: float = 0.0

    def select(
        self,
        subject_index: int,
        diameters_cm: Sequence[float],
        distances_m: Sequence[float],
        context: SelectionContext,
    ) -> Selection:
        """Select every tree inside ``radius_m``."""
        within = [d <= self.radius_m for d in distances_m]
        idx, dist = _screen(subject_index, diameters_cm, distances_m, within, self.min_size_ratio)
        return Selection(tuple(idx), tuple(dist), self.radius_m)


@dataclass(frozen=True)
class MeanHeightRadius:
    """Influence-zone radius set as a fraction of stand mean height.

    ``CZR = fraction * mean_height``; the paper's ``CZR_0.4h`` is
    ``fraction=0.4`` (Sims et al. 2009).

    Attributes:
        fraction: Multiple of mean height to use as the radius.
        min_size_ratio: Minimum ``d_j / d_i`` for a neighbour to compete.
    """

    fraction: float = 0.4
    min_size_ratio: float = 0.0

    def select(
        self,
        subject_index: int,
        diameters_cm: Sequence[float],
        distances_m: Sequence[float],
        context: SelectionContext,
    ) -> Selection:
        """Select every tree inside ``fraction * mean_height_m``."""
        if context.mean_height_m is None:
            raise ValueError("MeanHeightRadius needs SelectionContext.mean_height_m.")
        radius = self.fraction * context.mean_height_m
        return FixedRadius(radius, self.min_size_ratio).select(
            subject_index, diameters_cm, distances_m, context
        )


@dataclass(frozen=True)
class LeeGadowRadius:
    """Dynamic influence-zone radius scaled to mean spacing. Lee & Gadow (1997).

    ``CZR = k * sqrt(10000 / N)``, where the square root is the mean distance
    between neighbours at ``N`` stems/ha. The paper tests ``k = 2`` and ``k = 3``.

    Attributes:
        k: Multiple of mean spacing.
        min_size_ratio: Minimum ``d_j / d_i`` for a neighbour to compete.
    """

    k: float = 2.0
    min_size_ratio: float = 0.0

    def select(
        self,
        subject_index: int,
        diameters_cm: Sequence[float],
        distances_m: Sequence[float],
        context: SelectionContext,
    ) -> Selection:
        """Select every tree inside ``k * mean spacing``."""
        if context.stems_per_ha is None:
            raise ValueError("LeeGadowRadius needs SelectionContext.stems_per_ha.")
        radius = self.k * mean_spacing_m(context.stems_per_ha)
        return FixedRadius(radius, self.min_size_ratio).select(
            subject_index, diameters_cm, distances_m, context
        )


@dataclass(frozen=True)
class BitterlichBAF:
    """Variable-radius competitor selection. Bitterlich (1952).

    A neighbour competes when it falls inside the limiting distance of an
    angle-count sweep taken from the subject tree,
    ``l_ij <= 50 * d_i / sqrt(BAF)`` with ``d_i`` in **metres**. Equivalently,
    for ``d_i`` in cm, ``l_ij <= d_i / (2 * sqrt(BAF))``.

    That is the standard Bitterlich relation: a tree sits exactly on the limit
    when ``BAF = 10000 * (d_i / (2 * l_ij))^2``. The paper writes it with ``d_i``
    in cm against a footnote that defines ``d`` in cm, which only balances once
    the diameter is converted -- at BAF 2 a 20 cm subject reaches 7.07 m, not
    1.0 m.

    The zone grows with the *subject's* size, so a large tree reaches further for
    its competitors than a small one.

    Attributes:
        basal_area_factor: The BAF in m^2/ha; the paper tests 1, 2 and 4.
        min_size_ratio: Minimum ``d_j / d_i`` for a neighbour to compete.
    """

    basal_area_factor: float = 2.0
    min_size_ratio: float = 0.0

    def __post_init__(self) -> None:
        """Reject a non-positive basal area factor."""
        if self.basal_area_factor <= 0:
            raise ValueError("basal_area_factor must be positive.")

    def select(
        self,
        subject_index: int,
        diameters_cm: Sequence[float],
        distances_m: Sequence[float],
        context: SelectionContext,
    ) -> Selection:
        """Select every tree inside the subject's angle-count limiting distance."""
        # 50 * d_i(m) / sqrt(BAF), with d_i converted from cm.
        limit_m = 50.0 * (diameters_cm[subject_index] / 100.0) / sqrt(self.basal_area_factor)
        within = [d <= limit_m for d in distances_m]
        idx, dist = _screen(subject_index, diameters_cm, distances_m, within, self.min_size_ratio)
        return Selection(tuple(idx), tuple(dist), limit_m)


@dataclass(frozen=True)
class NearestNeighbours:
    """The ``n`` closest trees, irrespective of distance.

    Attributes:
        n: How many neighbours to take.
        min_size_ratio: Minimum ``d_j / d_i``, applied *before* taking the
            closest ``n`` so the screen cannot be swamped by suppressed stems.
    """

    n: int = 4
    min_size_ratio: float = 0.0

    def __post_init__(self) -> None:
        """Reject a non-positive neighbour count."""
        if self.n <= 0:
            raise ValueError("n must be positive.")

    def select(
        self,
        subject_index: int,
        diameters_cm: Sequence[float],
        distances_m: Sequence[float],
        context: SelectionContext,
    ) -> Selection:
        """Select the ``n`` nearest qualifying trees."""
        within = [True] * len(diameters_cm)
        idx, dist = _screen(subject_index, diameters_cm, distances_m, within, self.min_size_ratio)
        order = sorted(range(len(idx)), key=lambda k: dist[k])[: self.n]
        order.sort(key=lambda k: idx[k])
        chosen_idx = tuple(idx[k] for k in order)
        chosen_dist = tuple(dist[k] for k in order)
        # No single radius defines this zone, but the farthest retained competitor
        # is the effective reach, which the edge correction can use.
        reach = max(chosen_dist) if chosen_dist else None
        return Selection(chosen_idx, chosen_dist, reach)
