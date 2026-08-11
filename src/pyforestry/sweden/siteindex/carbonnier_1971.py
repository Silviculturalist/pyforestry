"""Carbonnier (1971) beech height development and site index helpers.

The height-development model is Appendix IV of Carbonnier (1971): a stand's height at
age ``j`` is ``h_j = a_j + tau * b_j``, where ``{a_j}`` and ``{b_j}`` are species-wide
constants tabulated per five-year total age and ``tau`` characterises the individual
stand. Fixing the site index at total age 100 pins ``tau = (h100 - a100) / b100``.

Source:
    Carbonnier, C. (1971). *Bokens produktion i södra Sverige = Yield of beech in
    southern Sweden.* Studia Forestalia Suecica nr 91. Institutionen för
    skogsproduktion, Skogshögskolan (Royal College of Forestry), Stockholm.
    Height-development curves: Appendix IV, derived by Susanne Kallstenius after a
    method of Bertil Matérn.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field
from typing import Sequence, Union

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers import Age, AgeMeasurement, SiteIndexValue, TreeName, TreeSpecies

DEFAULT_SITE_INDEX_AGE = Age.TOTAL(100.0)

AgeLike = Union[float, int, AgeMeasurement]
SiteIndexLike = Union[float, int, SiteIndexValue]


@dataclass
class CarbonnierHeightModel:
    """
    Carbonnier (1971) height development model for European beech.

    The original model uses age-indexed ``a`` and ``b`` coefficient tables with
    the linear relationship ``h_j = a_j + τ * b_j`` where ``τ`` is derived from
    the site index at a reference age (typically H100). ``τ`` is Matérn's ``t``
    in Appendix IV: ``τ = 0`` is the average height development, positive values
    grow faster and negative values slower.

    Parameters
    ----------
    ages
        Age grid (years, total age) corresponding to each ``a``/``b`` pair.
    a_vals
        ``a_j`` coefficients for each age in ``ages``.
    b_vals
        ``b_j`` coefficients for each age in ``ages``.
    species
        Tree species set attached to returned :class:`SiteIndexValue` objects.
    """

    ages: Sequence[AgeLike]
    a_vals: Sequence[float]
    b_vals: Sequence[float]
    species: set[TreeName] = field(default_factory=lambda: {TreeSpecies.Sweden.fagus_sylvatica})

    def __post_init__(self) -> None:
        """Validate inputs and normalise ages to Age.TOTAL measurements."""
        if not (len(self.ages) == len(self.a_vals) == len(self.b_vals)):
            raise ValueError("ages, a_vals, and b_vals must have the same length.")

        self.ages = tuple(self._ensure_total_age(age, "ages") for age in self.ages)
        self.a_vals = tuple(float(val) for val in self.a_vals)
        self.b_vals = tuple(float(val) for val in self.b_vals)
        self.species = set(self.species)
        if not self.species:
            raise ValueError("species cannot be empty.")

        self._age_values = tuple(float(age) for age in self.ages)
        if list(self._age_values) != sorted(self._age_values):
            raise ValueError("ages must be sorted in increasing order.")

    def _ensure_total_age(self, age: AgeLike, param_name: str) -> AgeMeasurement:
        """Return age as ``Age.TOTAL`` measurement, validating type and sign."""
        if isinstance(age, AgeMeasurement):
            if age.code != Age.TOTAL.value:
                raise TypeError(f"{param_name} must use Age.TOTAL, got code {age.code}.")
            return age
        if isinstance(age, (float, int)):
            if age < 0:
                raise ValueError(f"{param_name} must be non-negative.")
            return Age.TOTAL(float(age))
        raise TypeError(f"{param_name} must be a float/int or an AgeMeasurement.")

    def _coefficients_at_age(
        self, age: AgeMeasurement, interpolate: bool = True
    ) -> tuple[float, float]:
        """Return (a, b) coefficients for the provided age."""
        if age in self.ages:
            idx = self.ages.index(age)
            return self.a_vals[idx], self.b_vals[idx]

        if not interpolate:
            raise ValueError("Age not tabulated and interpolate=False.")

        target_age = float(age)
        i = bisect.bisect_left(self._age_values, target_age)

        if i == 0 or i == len(self._age_values):
            raise ValueError(
                f"Age {target_age} outside coefficient range "
                f"[{self._age_values[0]}, {self._age_values[-1]}]."
            )

        w = (target_age - self._age_values[i - 1]) / (
            self._age_values[i] - self._age_values[i - 1]
        )
        a_val = self.a_vals[i - 1] + w * (self.a_vals[i] - self.a_vals[i - 1])
        b_val = self.b_vals[i - 1] + w * (self.b_vals[i] - self.b_vals[i - 1])

        return a_val, b_val

    def _tau_from_SI(
        self, site_index: SiteIndexLike, si_age: AgeLike = DEFAULT_SITE_INDEX_AGE
    ) -> float:
        """
        Compute τ (site quality parameter) from top height at age ``si_age``.

        τ = (SI - a_si_age) / b_si_age
        """
        si_age_measurement = self._ensure_total_age(si_age, "si_age")
        si_value = float(site_index)
        if isinstance(site_index, SiteIndexValue) and (
            site_index.reference_age != si_age_measurement
        ):
            raise ValueError("site_index reference_age must match si_age.")

        a_si, b_si = self._coefficients_at_age(si_age_measurement, interpolate=True)

        if b_si == 0:
            raise ZeroDivisionError("b coefficient at si_age is zero; cannot compute tau.")

        return (si_value - a_si) / b_si

    def _height_at_age(self, age: AgeLike, tau: float, interpolate: bool = True) -> float:
        """
        Compute height at arbitrary age for a given τ.

        If age is tabulated exactly, the formula h = a + τ b is used.
        Otherwise, linear interpolation is applied between the nearest
        age classes.
        """
        age_measurement = self._ensure_total_age(age, "age")
        a_val, b_val = self._coefficients_at_age(age_measurement, interpolate=interpolate)
        return a_val + tau * b_val

    def height_from_SI(
        self,
        age: AgeLike,
        site_index: SiteIndexLike,
        si_age: AgeLike = DEFAULT_SITE_INDEX_AGE,
        interpolate: bool = True,
    ) -> SiteIndexValue:
        """
        Compute height at ``age`` for a stand with given site index (H100).
        """
        tau = self._tau_from_SI(site_index, si_age)
        height = self._height_at_age(age, tau, interpolate=interpolate)
        age_measurement = self._ensure_total_age(age, "age")
        return SiteIndexValue(
            height,
            reference_age=age_measurement,
            species=self.species,
            fn=self.height_from_SI,
        )

    def site_index_from_height(
        self,
        height: float,
        measurement_age: AgeLike,
        si_age: AgeLike = DEFAULT_SITE_INDEX_AGE,
        interpolate: bool = True,
    ) -> SiteIndexValue:
        """Estimate site index at ``si_age`` from a measured top height."""
        measurement_age_value = self._ensure_total_age(measurement_age, "measurement_age")
        si_age_measurement = self._ensure_total_age(si_age, "si_age")
        a_val, b_val = self._coefficients_at_age(measurement_age_value, interpolate=interpolate)

        if b_val == 0:
            raise ZeroDivisionError(
                "b coefficient at measurement_age is zero; cannot compute tau."
            )

        tau = (float(height) - a_val) / b_val
        site_index_value = self._height_at_age(si_age_measurement, tau, interpolate=True)

        return SiteIndexValue(
            site_index_value,
            reference_age=si_age_measurement,
            species=self.species,
            fn=self.site_index_from_height,
        )


# Table IV.1, "Utjämnade värden för talföljderna {a_j} och {b_j}" -- the smoothed
# sequences from Carbonnier (1971) Appendix IV. Held as (total age, a_j, b_j)
# triples rather than three parallel lists so the columns cannot drift out of
# alignment during transcription.
#
# The paper is explicit that the curves must not be extrapolated above 135 years
# ("Kurvorna bör under inga förhållanden extrapoleras ovanför 135 år"), which is
# why the table stops there; ``_coefficients_at_age`` already refuses ages
# outside the tabulated range.
CARBONNIER_1971_BEECH_HEIGHT_TABLE: tuple[tuple[float, float, float], ...] = (
    (10.0, 1.4027, 0.0115),
    (15.0, 3.6122, 0.0263),
    (20.0, 5.7323, 0.0405),
    (25.0, 7.7630, 0.0541),
    (30.0, 9.7043, 0.0671),
    (35.0, 11.5562, 0.0795),
    (40.0, 13.3187, 0.0913),
    (45.0, 14.9918, 0.1025),
    (50.0, 16.5755, 0.1131),
    (55.0, 18.0698, 0.1231),
    (60.0, 19.4747, 0.1325),
    (65.0, 20.7902, 0.1413),
    (70.0, 22.0163, 0.1495),
    (75.0, 23.1530, 0.1571),
    (80.0, 24.2003, 0.1641),
    (85.0, 25.1582, 0.1705),
    (90.0, 26.0267, 0.1763),
    (95.0, 26.8058, 0.1815),
    (100.0, 27.4955, 0.1861),
    (105.0, 28.0958, 0.1901),
    (110.0, 28.6067, 0.1935),
    (115.0, 29.0282, 0.1963),
    (120.0, 29.3603, 0.1985),
    (125.0, 29.6030, 0.2001),
    (130.0, 29.7563, 0.2011),
    (135.0, 29.8202, 0.2015),
)

#: Highest total age the published curves may be evaluated at (Appendix IV).
CARBONNIER_1971_MAX_TOTAL_AGE = 135.0


def carbonnier_1971_beech_height_model() -> CarbonnierHeightModel:
    """Return the published beech height model of Carbonnier (1971).

    The coefficients are Table IV.1 of Appendix IV; the returned model is valid
    for total ages 10-135 years and is keyed on H100 (top height at 100 years
    total age).

    Returns:
        A :class:`CarbonnierHeightModel` carrying the published ``{a_j}`` and
        ``{b_j}`` sequences for *Fagus sylvatica*.
    """
    ages = tuple(age for age, _, _ in CARBONNIER_1971_BEECH_HEIGHT_TABLE)
    a_vals = tuple(a for _, a, _ in CARBONNIER_1971_BEECH_HEIGHT_TABLE)
    b_vals = tuple(b for _, _, b in CARBONNIER_1971_BEECH_HEIGHT_TABLE)
    return CarbonnierHeightModel(ages=ages, a_vals=a_vals, b_vals=b_vals)


DESCRIPTOR = FormulaDescriptor(
    component_id="carbonnier_1971_siteindex",
    source=SourceReference(
        author="Carbonnier, C.",
        year=1971,
        title="Bokens produktion i södra Sverige = Yield of beech in southern Sweden",
        appendix="Bilaga IV: Härledning av höjdutvecklingskurvor, av Susanne Kallstenius",
        note=(
            "Studia Forestalia Suecica nr 91. Institutionen för skogsproduktion, "
            "Skogshögskolan (Royal College of Forestry), Stockholm. The height-development "
            "curves come from Appendix IV, derived by Susanne Kallstenius after a method of "
            "Bertil Matérn; the smoothed sequences {a_j}, {b_j} are Table IV.1. Not to be "
            "confused with Carbonnier (1975), Studia Forestalia Suecica nr 125, which is the "
            "OAK yield study and uses a different (Hägglund exponential) height function."
        ),
    ),
    species_groups={"beech": frozenset({"Fagus sylvatica"})},
    units={
        "height": "m",
        "measurement_age": "years (Age.TOTAL)",
        "si_age": "years (Age.TOTAL)",
        "return": "SiteIndexValue (m at total age 100)",
    },
    kernel_names=("CarbonnierHeightModel", "carbonnier_1971_beech_height_model"),
)
