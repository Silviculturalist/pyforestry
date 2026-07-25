"""The input a competition index is computed from: a subject tree and its competitors.

Every index in :mod:`pyforestry.base.competition.indices` takes a single
:class:`Neighbourhood`. Keeping one uniform input lets the indices be looked up
by name and compared against each other on identical data, which is the whole
point of the review this module transcribes: an index value is only meaningful
alongside the competitor-selection rule that produced it.

Fields a given index does not need are left ``None``; each index raises a clear
:class:`MissingNeighbourhoodData` naming what it needed rather than failing on an
arithmetic error deep inside a sum.
"""

from dataclasses import dataclass
from math import pi
from typing import Optional, Sequence, Tuple

__all__ = ["MissingNeighbourhoodData", "Neighbourhood", "basal_area_m2"]


class MissingNeighbourhoodData(ValueError):
    """A competition index was asked for without the inputs it requires."""


def basal_area_m2(diameter_cm: float) -> float:
    """Cross-sectional area at breast height (m^2) for a diameter in cm."""
    return pi * (float(diameter_cm) / 200.0) ** 2


@dataclass(frozen=True)
class Neighbourhood:
    """A subject tree and the competitors selected for it.

    Attributes:
        subject_dbh_cm: Diameter at breast height of the subject tree (cm).
        competitor_dbh_cm: Diameters of the selected competitors (cm), in the
            same order as every other per-competitor sequence here.
        distances_m: Distance from the subject stem to each competitor stem (m).
            Required by the spatially explicit indices; ``None`` for a
            non-spatial neighbourhood.
        subject_crown_radius_m: Radius of the subject tree's influence zone (m),
            required by the influence-zone overlap indices.
        competitor_crown_radius_m: Influence-zone radii of the competitors (m).
        plot_area_ha: Area of the plot the competitors were drawn from (ha).
        plot_basal_area_m2_ha: Total basal area of the plot (m^2/ha).
        plot_qmd_cm: Quadratic mean diameter of the plot (cm).
        relative_spacing: Relative spacing index of the plot, ``sqrt(S/N)/H_dom``
            with ``S`` in m^2 (Schroder & Gadow's ``RS``).
        competition_zone_radius_m: Radius of the competition zone the competitors
            were selected within (m), used by Lorimer's ``Sdrl1``.
    """

    subject_dbh_cm: float
    competitor_dbh_cm: Tuple[float, ...]
    distances_m: Optional[Tuple[float, ...]] = None
    subject_crown_radius_m: Optional[float] = None
    competitor_crown_radius_m: Optional[Tuple[float, ...]] = None
    plot_area_ha: Optional[float] = None
    plot_basal_area_m2_ha: Optional[float] = None
    plot_qmd_cm: Optional[float] = None
    relative_spacing: Optional[float] = None
    competition_zone_radius_m: Optional[float] = None

    def __post_init__(self) -> None:
        """Validate the subject and check every per-competitor sequence aligns."""
        if self.subject_dbh_cm is None or self.subject_dbh_cm <= 0:
            raise ValueError("subject_dbh_cm must be positive.")
        n = len(self.competitor_dbh_cm)
        for name in ("distances_m", "competitor_crown_radius_m"):
            values = getattr(self, name)
            if values is not None and len(values) != n:
                raise ValueError(
                    f"{name} has {len(values)} entries but there are {n} competitors; "
                    "every per-competitor sequence must align with competitor_dbh_cm."
                )
        if self.distances_m is not None and any(d <= 0 for d in self.distances_m):
            raise ValueError(
                "distances_m must all be positive; a competitor at zero distance is "
                "the subject tree itself and the size-ratio indices divide by distance."
            )

    @property
    def n_competitors(self) -> int:
        """Number of selected competitors."""
        return len(self.competitor_dbh_cm)

    @property
    def subject_basal_area_m2(self) -> float:
        """Basal area of the subject tree (m^2)."""
        return basal_area_m2(self.subject_dbh_cm)

    def competitor_basal_areas_m2(self) -> Tuple[float, ...]:
        """Basal area of each competitor (m^2)."""
        return tuple(basal_area_m2(d) for d in self.competitor_dbh_cm)

    def require(self, *fields: str) -> None:
        """Raise if any named field is unset.

        Args:
            *fields: Attribute names the calling index depends on.

        Raises:
            MissingNeighbourhoodData: Naming every field that is missing.
        """
        missing = [f for f in fields if getattr(self, f) is None]
        if missing:
            raise MissingNeighbourhoodData(
                f"This index needs {', '.join(missing)}, which "
                f"{'is' if len(missing) == 1 else 'are'} not set on the Neighbourhood."
            )

    def larger_competitor_mask(self) -> Tuple[bool, ...]:
        """Which competitors are strictly larger in diameter than the subject."""
        return tuple(d > self.subject_dbh_cm for d in self.competitor_dbh_cm)

    @classmethod
    def from_sequences(
        cls,
        subject_dbh_cm: float,
        competitor_dbh_cm: Sequence[float],
        distances_m: Optional[Sequence[float]] = None,
        **kwargs: object,
    ) -> "Neighbourhood":
        """Build a Neighbourhood from any sequences, coercing them to tuples.

        Args:
            subject_dbh_cm: Subject diameter (cm).
            competitor_dbh_cm: Competitor diameters (cm).
            distances_m: Competitor distances (m), if spatial.
            **kwargs: Any other :class:`Neighbourhood` field.

        Returns:
            The frozen neighbourhood.
        """
        crowns = kwargs.pop("competitor_crown_radius_m", None)
        return cls(
            subject_dbh_cm=float(subject_dbh_cm),
            competitor_dbh_cm=tuple(float(d) for d in competitor_dbh_cm),
            distances_m=None if distances_m is None else tuple(float(x) for x in distances_m),
            competitor_crown_radius_m=(
                None if crowns is None else tuple(float(x) for x in crowns)  # type: ignore[union-attr]
            ),
            **kwargs,  # type: ignore[arg-type]
        )
