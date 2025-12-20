"""Carbonnier (1975) beech height development and site index helpers."""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field
from typing import Sequence, Union

from pyforestry.base.helpers import Age, AgeMeasurement, SiteIndexValue, TreeName, TreeSpecies

DEFAULT_SITE_INDEX_AGE = Age.TOTAL(100.0)

AgeLike = Union[float, int, AgeMeasurement]
SiteIndexLike = Union[float, int, SiteIndexValue]


@dataclass
class CarbonnierHeightModel:
    """
    Carbonnier (1975) height development model for European beech.

    The original model uses age-indexed ``a`` and ``b`` coefficient tables with
    the linear relationship ``h_j = a_j + τ * b_j`` where ``τ`` is derived from
    the site index at a reference age (typically H100).

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
