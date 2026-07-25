"""Maleki et al. (2022) stand-level kernels for Norway.

The functions in this module implement the equations provided in the Norway
asset model draft and expose explicit primitive-based interfaces.
"""

from __future__ import annotations

import math
import warnings
from enum import Enum
from typing import Final

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers.primitives import (
    Age,
    AgeMeasurement,
    QuadraticMeanDiameter,
    SiteIndexValue,
    StandBasalArea,
    StandVolume,
    Stems,
)
from pyforestry.base.helpers.tree_species import TreeName, TreeSpecies

_EPS: Final[float] = 1e-9
_H40_REF_AGE: Final[AgeMeasurement] = Age.TOTAL(40.0)


class Maleki2022Species(str, Enum):
    """Supported species groups in Maleki et al. (2022)."""

    NORWAY_SPRUCE = "norway_spruce"
    SCOTS_PINE = "scots_pine"
    BROADLEAVES = "broadleaves"


_VOLUME_COEFFICIENTS: Final[dict[Maleki2022Species, tuple[float, float, float, float]]] = {
    Maleki2022Species.NORWAY_SPRUCE: (0.2134, 1.0779, 1.0498, 2.5148),
    Maleki2022Species.SCOTS_PINE: (0.4830, 0.9128, 0.9913, -1.6105),
    Maleki2022Species.BROADLEAVES: (0.5564, 0.7667, 1.0318, -1.5229),
}

_SURVIVAL_COEFFICIENTS: Final[dict[Maleki2022Species, tuple[float, float, float]]] = {
    Maleki2022Species.NORWAY_SPRUCE: (0.6159, -0.0312, 1.0602),
    Maleki2022Species.SCOTS_PINE: (0.17881, -0.0308, 0.0695),
    Maleki2022Species.BROADLEAVES: (0.4592, -0.0534, 0.9466),
}

_DENSITY_COEFFICIENTS: Final[dict[Maleki2022Species, tuple[float, float, float]]] = {
    Maleki2022Species.NORWAY_SPRUCE: (1.5124, -0.00654, 1.4747),
    Maleki2022Species.SCOTS_PINE: (0.6676, 0.0039, 0.8662),
    Maleki2022Species.BROADLEAVES: (1.1395, -0.0162, 1.2682),
}

_HEIGHT_COEFFICIENTS: Final[dict[Maleki2022Species, tuple[float, float, float]]] = {
    Maleki2022Species.NORWAY_SPRUCE: (39.5764, -396.3146, 1.6770),
    Maleki2022Species.SCOTS_PINE: (43.6698, -24.9476, 1.2967),
    Maleki2022Species.BROADLEAVES: (36.6501, -11.8787, 1.0643),
}

_BA_PROJECTION_COEFFICIENTS: Final[dict[Maleki2022Species, tuple[float, float, float]]] = {
    Maleki2022Species.NORWAY_SPRUCE: (0.4159, 2.0096, 0.7521),
    Maleki2022Species.SCOTS_PINE: (0.5381, 0.96900, 4.1579),
    Maleki2022Species.BROADLEAVES: (0.2970, 3.6124, 0.2087),
}

_SPECIES_NAME: Final[dict[Maleki2022Species, TreeName | None]] = {
    Maleki2022Species.NORWAY_SPRUCE: TreeSpecies.Norway.picea_abies,
    Maleki2022Species.SCOTS_PINE: TreeSpecies.Norway.pinus_sylvestris,
    Maleki2022Species.BROADLEAVES: None,
}


def _normalize_species(species: Maleki2022Species | str) -> Maleki2022Species:
    """Normalize species selector to :class:`Maleki2022Species`."""
    if isinstance(species, Maleki2022Species):
        return species
    try:
        return Maleki2022Species(str(species).strip().lower())
    except ValueError as exc:  # pragma: no cover - exercised by tests through ValueError path
        allowed = ", ".join(item.value for item in Maleki2022Species)
        raise ValueError(
            f"Unsupported species group {species!r}. Expected one of: {allowed}."
        ) from exc


def _require_total_age(age: AgeMeasurement, name: str) -> float:
    """Validate and convert total-age measurements."""
    if not isinstance(age, AgeMeasurement):
        raise TypeError(f"Input '{name}' must be an AgeMeasurement.")
    if age.code != Age.TOTAL.value:
        raise TypeError(f"Input '{name}' must use Age.TOTAL.")
    return float(age)


def _logistic(value: float) -> float:
    """Return a numerically stable logistic transform."""
    if value >= 0.0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def _coerce_non_negative(
    value: float | StandBasalArea | Stems | QuadraticMeanDiameter,
    name: str,
) -> float:
    """Convert value to float and require non-negative value."""
    out = float(value)
    if out < 0.0:
        raise ValueError(f"Input '{name}' must be non-negative.")
    return out


def _h40_value(si_h40: SiteIndexValue) -> float:
    """Extract H40 value and warn if metadata is inconsistent with expected use."""
    if not isinstance(si_h40, SiteIndexValue):
        raise TypeError("Input 'si_h40' must be a SiteIndexValue.")
    if (
        isinstance(si_h40.reference_age, AgeMeasurement)
        and si_h40.reference_age.code == Age.TOTAL.value
        and not math.isclose(float(si_h40.reference_age), 40.0)
    ):
        warnings.warn(
            "Input 'si_h40' reference age is not 40 years; treating value as H40 anyway.",
            stacklevel=2,
        )
    return _coerce_non_negative(si_h40, "si_h40")


def maleki_2022_stand_volume(
    species: Maleki2022Species | str,
    dominant_height_m: float,
    basal_area: StandBasalArea | float,
    age: AgeMeasurement,
) -> StandVolume:
    """Return stand volume (`m3/ha`) for the selected Maleki species group."""
    species_key = _normalize_species(species)
    h = _coerce_non_negative(float(dominant_height_m), "dominant_height_m")
    g = _coerce_non_negative(basal_area, "basal_area")
    a = _require_total_age(age, "age")
    if a <= 0.0:
        raise ValueError("Input 'age' must be positive.")

    b1, b2, b3, b4 = _VOLUME_COEFFICIENTS[species_key]
    volume_value = b1 * (h**b2) * (g**b3) * math.exp(b4 / a)
    return StandVolume(max(0.0, volume_value), species=_SPECIES_NAME[species_key])


def _stem_count_projection(
    species: Maleki2022Species,
    age1: AgeMeasurement,
    age2: AgeMeasurement,
    stems1: Stems | float,
    si_h40: SiteIndexValue,
    coefficients: dict[Maleki2022Species, tuple[float, float, float]],
) -> Stems:
    """Common projection equation used for survival and density."""
    a1 = _require_total_age(age1, "age1")
    a2 = _require_total_age(age2, "age2")
    n1 = _coerce_non_negative(stems1, "stems1")
    si = _h40_value(si_h40)

    if a2 < a1:
        raise ValueError("Input 'age2' must be greater than or equal to 'age1'.")
    if math.isclose(a2, a1):
        return Stems(n1, species=_SPECIES_NAME[species])
    if a1 <= 0.0 or n1 <= 0.0:
        return Stems(0.0, species=_SPECIES_NAME[species])

    b1, b2, b3 = coefficients[species]
    # Maleki et al. (2022) Table 4, eqs. (2) stem density / (5) survival:
    # exp(b2 - (SI/1000) * (A2 - A1)^b3), with b2 an additive intercept and the
    # site/age term subtracted (not multiplied by b2).
    projected = n1 * ((a2 / a1) ** b1) * math.exp(b2 - (si / 1000.0) * ((a2 - a1) ** b3))
    return Stems(max(0.0, projected), species=_SPECIES_NAME[species])


def maleki_2022_stem_survival(
    species: Maleki2022Species | str,
    age1: AgeMeasurement,
    age2: AgeMeasurement,
    stems1: Stems | float,
    si_h40: SiteIndexValue,
) -> Stems:
    """Return projected surviving stems per hectare."""
    species_key = _normalize_species(species)
    return _stem_count_projection(species_key, age1, age2, stems1, si_h40, _SURVIVAL_COEFFICIENTS)


def maleki_2022_stem_density(
    species: Maleki2022Species | str,
    age1: AgeMeasurement,
    age2: AgeMeasurement,
    stems1: Stems | float,
    si_h40: SiteIndexValue,
) -> Stems:
    """Return projected stem density per hectare."""
    species_key = _normalize_species(species)
    return _stem_count_projection(species_key, age1, age2, stems1, si_h40, _DENSITY_COEFFICIENTS)


def maleki_2022_ingrowth_count(
    species: Maleki2022Species | str,
    *,
    basal_area: StandBasalArea | float | None = None,
    qmd: QuadraticMeanDiameter | float | None = None,
) -> float:
    """Return expected ingrowth count per 5-year period."""
    species_key = _normalize_species(species)
    if species_key is Maleki2022Species.BROADLEAVES:
        if qmd is None:
            raise ValueError("Input 'qmd' is required for broadleaves ingrowth count.")
        qmd_value = _coerce_non_negative(qmd, "qmd")
        return max(0.0, math.exp(3.0411 - 0.6213 * math.sqrt(qmd_value)))

    if basal_area is None:
        raise ValueError("Input 'basal_area' is required for conifer ingrowth count.")
    basal_area_value = _coerce_non_negative(basal_area, "basal_area")
    if species_key is Maleki2022Species.NORWAY_SPRUCE:
        return max(0.0, math.exp(2.2919 - 0.3780 * math.sqrt(basal_area_value)))
    return max(0.0, math.exp(0.5264 - 0.0889 * math.sqrt(basal_area_value)))


def maleki_2022_ingrowth_probability(
    species: Maleki2022Species | str,
    qmd: QuadraticMeanDiameter | float,
    stems: Stems | float,
) -> float:
    """Return probability of ingrowth occurrence for the next 5-year period."""
    species_key = _normalize_species(species)
    q = float(qmd)
    n = float(stems)
    if q < 0.0 or n < 0.0:
        return 0.0

    sqrt_q = math.sqrt(q)
    sqrt_n = math.sqrt(n)
    if species_key is Maleki2022Species.NORWAY_SPRUCE:
        logit = 13.6210 - 3.0328 * sqrt_q - 0.6868 * sqrt_n + 0.1483 * sqrt_q * sqrt_n
    elif species_key is Maleki2022Species.SCOTS_PINE:
        logit = 7.6489 - 1.2823 * sqrt_q - 0.5173 * sqrt_n + 0.0915 * sqrt_q * sqrt_n
    else:
        logit = 7.7009 - 1.6373 * sqrt_q - 0.3349 * sqrt_n + 0.5688 * sqrt_q * sqrt_n
    return min(max(_logistic(logit), 0.0), 1.0)


def maleki_2022_height_trajectory(
    species: Maleki2022Species | str,
    dominant_height_m: float,
    age1: AgeMeasurement,
    age2: AgeMeasurement,
) -> float:
    """Return projected dominant height (`m`) at `age2`."""
    species_key = _normalize_species(species)
    h1 = _coerce_non_negative(dominant_height_m, "dominant_height_m")
    a1 = _require_total_age(age1, "age1")
    a2 = _require_total_age(age2, "age2")

    if math.isclose(a1, a2):
        return h1
    if a1 <= 0.0:
        return 0.0 if a2 <= 0.0 else h1

    b1, b2, b3 = _HEIGHT_COEFFICIENTS[species_key]
    if h1 <= _EPS:
        raise ValueError("Input 'dominant_height_m' must be positive for trajectory projection.")

    # Maleki et al. (2022) Table 4 eq. (1), a GADA formulation (Dieguez-Aranda
    # et al. 2005a). X is the site variable recovered from the reference (H1, A1);
    # the same X then projects to A2, so the equation reproduces H1 at A1 exactly
    # and is valid for A2 either greater or smaller than A1:
    #   X  = (H1 - b1) / (1 - b2 * H1 * A1**-b3)
    #   H2 = (b1 + X) / (1 + b2 * X * A2**-b3)
    x_den = 1.0 - b2 * h1 * (a1**-b3)
    if abs(x_den) < _EPS:
        warnings.warn(
            "Near-zero denominator in Maleki height site variable. Returning input height.",
            stacklevel=2,
        )
        return h1

    x0 = (h1 - b1) / x_den
    h2_den = 1.0 + b2 * x0 * (a2**-b3)
    if abs(h2_den) < _EPS:
        warnings.warn(
            "Near-zero denominator in Maleki age2 trajectory term. Returning asymptotic height.",
            stacklevel=2,
        )
        return max(0.0, b1)
    return max(0.0, (b1 + x0) / h2_den)


def maleki_2022_basal_area_projection(
    species: Maleki2022Species | str,
    basal_area1: StandBasalArea | float,
    age1: AgeMeasurement,
    age2: AgeMeasurement,
    si_h40: SiteIndexValue,
    stems1: Stems | float,
    stems2: Stems | float,
) -> StandBasalArea:
    """Return projected basal area (`m2/ha`) for the selected species group."""
    species_key = _normalize_species(species)
    a1 = _require_total_age(age1, "age1")
    a2 = _require_total_age(age2, "age2")
    g1 = _coerce_non_negative(basal_area1, "basal_area1")
    n1 = _coerce_non_negative(stems1, "stems1")
    n2 = _coerce_non_negative(stems2, "stems2")
    si_value = _h40_value(si_h40)

    if a2 < a1:
        raise ValueError("Input 'age2' must be greater than or equal to 'age1'.")
    if math.isclose(a1, a2):
        return StandBasalArea(g1, species=_SPECIES_NAME[species_key])
    if n1 <= 0.0:
        return StandBasalArea(0.0, species=_SPECIES_NAME[species_key])

    h1 = maleki_2022_height_trajectory(species_key, si_value, _H40_REF_AGE, age1)
    h2 = maleki_2022_height_trajectory(species_key, si_value, _H40_REF_AGE, age2)
    if h1 <= _EPS or h2 <= _EPS:
        return StandBasalArea(0.0, species=_SPECIES_NAME[species_key])

    b1, b2, b3 = _BA_PROJECTION_COEFFICIENTS[species_key]
    ratio_h = h1 / h2
    ratio_n = n2 / n1
    # Maleki et al. (2022) Table 4 eq. (3) is PRINTED with a double-b2 --
    # exp[ b2**(N2/N1) * b2 * (1 - (H1/H2)**b3) ] -- reusing the single fitted b2
    # (Table 6) as both an exponent base and a linear multiplier, which is an
    # unidentifiable typesetting error. The intended single-b2 form is the linear
    # one applied here:
    #     exp( b2 * (N2/N1) * (1 - (H1/H2)**b3) ).
    # Confirmed by reproducing the paper's Fig. 7 basal-area projections: this form
    # yields the rising/plateauing basal area Fig. 7 shows, whereas the alternative
    # (N2/N1)**b2 reading makes basal area DECLINE over the projection -- which no
    # Fig. 7 trajectory does. See pyforestry.norway.growth.allen_2020 (Hasenauer/
    # Allen parent). Coefficients: paper Table 6 (spruce/pine/broadleaves verified).
    projected = (g1 ** (ratio_h**b1)) * math.exp(b2 * ratio_n * (1.0 - ratio_h**b3))
    return StandBasalArea(max(0.0, projected), species=_SPECIES_NAME[species_key])


__all__ = [
    "Maleki2022Species",
    "maleki_2022_stand_volume",
    "maleki_2022_stem_survival",
    "maleki_2022_stem_density",
    "maleki_2022_ingrowth_count",
    "maleki_2022_ingrowth_probability",
    "maleki_2022_height_trajectory",
    "maleki_2022_basal_area_projection",
]


DESCRIPTOR = FormulaDescriptor(
    component_id="maleki_2022_growth",
    source=SourceReference(
        author="Maleki, K., Astrup, R., Kuehne, C., McLean, J.P. & Antón-Fernández, C.",
        year=2022,
        title=(
            "Stand-level growth models for long-term projections of the main "
            "species groups in Norway"
        ),
        note=(
            "Scandinavian Journal of Forest Research 37(2):130-143. "
            "doi:10.1080/02827581.2022.2056632"
        ),
    ),
    species_groups={
        "norway_spruce": frozenset({"Picea abies"}),
        "scots_pine": frozenset({"Pinus sylvestris"}),
    },
    units={},
    kernel_names=(
        "Maleki2022Species",
        "maleki_2022_stand_volume",
        "maleki_2022_stem_survival",
        "maleki_2022_stem_density",
        "maleki_2022_ingrowth_count",
        "maleki_2022_ingrowth_probability",
        "maleki_2022_height_trajectory",
        "maleki_2022_basal_area_projection",
    ),
)
