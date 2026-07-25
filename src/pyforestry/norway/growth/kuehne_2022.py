"""Kuehne et al. (2022) stand-level growth & yield kernels for Scots pine, Norway.

Implements the stem-density, basal-area, volume and thinning-reduction component
equations (Eqs. 6-10) of

    Kuehne, C., McLean, J.P., Maleki, K., Anton-Fernandez, C. & Astrup, R. (2022).
    "A stand-level growth and yield model for thinned and unthinned even-aged
    Scots pine forests in Norway." Silva Fennica 56(1) article id 10627.
    DOI 10.14214/sf.10627.

The dominant-height / site-index component (Eq. 5) lives in
``pyforestry.norway.siteindex.kuehne_2022``. Coefficients are Table 3 of the
paper (columns TPH2, BA2, VOL2, TPHAFTER/TPHBEFORE). Equation forms were read
directly from the published equations (Eqs. 6-10); the authors' ``forester`` R
package agrees except for a linear ``AGE2*b4 - AGE1*b4`` in stem density, which
the paper writes as the power form ``AGE2^b4 - AGE1^b4`` (used here).

Single species: Scots pine (Pinus sylvestris). Ages are TOTAL age; ``si40`` is
site index (dominant height, m) at base age 40. Thinning enters via the basal-
area thinning quotient ``BA_AFTER/BA_BEFORE`` (= 1.0 for an unthinned period).
"""

from __future__ import annotations

import math
from typing import Final

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers.primitives import (
    Age,
    AgeMeasurement,
    SiteIndexValue,
    StandBasalArea,
    StandVolume,
    Stems,
)
from pyforestry.base.helpers.tree_species import TreeSpecies

_EPS: Final[float] = 1e-9
_SPECIES: Final = TreeSpecies.Norway.pinus_sylvestris


def _require_total_age(age: AgeMeasurement, name: str) -> float:
    """Validate and convert a total-age measurement to float."""
    if not isinstance(age, AgeMeasurement):
        raise TypeError(f"Input '{name}' must be an AgeMeasurement.")
    if age.code != Age.TOTAL.value:
        raise TypeError(f"Input '{name}' must use Age.TOTAL.")
    value = float(age)
    if value <= 0.0:
        raise ValueError(f"Input '{name}' must be positive.")
    return value


def _non_negative(value: float, name: str) -> float:
    """Convert to float and require a non-negative value."""
    out = float(value)
    if out < 0.0:
        raise ValueError(f"Input '{name}' must be non-negative.")
    return out


def kuehne_2022_stem_density(
    stems1: Stems | float,
    age1: AgeMeasurement,
    age2: AgeMeasurement,
    si40: SiteIndexValue | float,
    *,
    thinning_quotient: float = 1.0,
) -> Stems:
    """Project stem density per hectare. Kuehne et al. (2022) Eq. (6).

        TPH2 = ( TPH1^b1 + b2 * (BA_after/BA_before) * (SI40/10000)^b3
                 * (AGE2^b4 - AGE1^b4) )^(1/b1)

    ``thinning_quotient`` is BA_AFTER/BA_BEFORE (= 1.0 unthinned); ``si40`` is site
    index (m) at base age 40. b2 (the thinning-modifier coefficient) is retained
    even when unthinned.
    """
    n1 = _non_negative(stems1, "stems1")
    a1 = _require_total_age(age1, "age1")
    a2 = _require_total_age(age2, "age2")
    si = _non_negative(si40, "si40")
    if a2 < a1:
        raise ValueError("Input 'age2' must be greater than or equal to 'age1'.")
    if math.isclose(a1, a2):
        return Stems(n1, species=_SPECIES)
    if n1 <= 0.0:
        return Stems(0.0, species=_SPECIES)

    b1, b2, b3, b4 = -1.56856, 0.00284, 4.14779, 4.87715
    tq = float(thinning_quotient)
    bracket = n1**b1 + b2 * tq * (si / 10000.0) ** b3 * (a2**b4 - a1**b4)
    if bracket <= 0.0:
        return Stems(0.0, species=_SPECIES)
    projected = bracket ** (1.0 / b1)
    return Stems(max(0.0, projected), species=_SPECIES)


def kuehne_2022_basal_area(
    basal_area1: StandBasalArea | float,
    age1: AgeMeasurement,
    age2: AgeMeasurement,
    dominant_height1: float,
    dominant_height2: float,
    stems1: Stems | float,
    stems2: Stems | float,
    *,
    thinning_quotient: float = 1.0,
    age_thin: float | None = None,
) -> StandBasalArea:
    """Project total basal area (`m2/ha`). Kuehne et al. (2022) Eq. (7).

        BA2 = exp[ (A1/A2)*ln(BA1) + b1*(1 - A1/A2)
                   + b2*(ln(H2) - (A1/A2)*ln(H1))
                   + b3*(ln(TPH2) - (A1/A2)*ln(TPH1))
                   + b4*((ln(TPH2) - ln(TPH1))/A2)
                   + b5*((BA_rem/BA_before / AGE_thin)*(1/A2 - 1/A1)) ]

    Modified Brooks (1992) ADA form with a thinning modifier. ``thinning_quotient``
    is BA_AFTER/BA_BEFORE (so BA_rem/BA_before = 1 - thinning_quotient);
    ``age_thin`` is the total stand age at thinning. The b5 term vanishes for an
    unthinned period (thinning_quotient = 1.0 or age_thin = None).
    """
    g1 = _non_negative(basal_area1, "basal_area1")
    a1 = _require_total_age(age1, "age1")
    a2 = _require_total_age(age2, "age2")
    h1 = _non_negative(dominant_height1, "dominant_height1")
    h2 = _non_negative(dominant_height2, "dominant_height2")
    n1 = _non_negative(stems1, "stems1")
    n2 = _non_negative(stems2, "stems2")
    if a2 < a1:
        raise ValueError("Input 'age2' must be greater than or equal to 'age1'.")
    if math.isclose(a1, a2):
        return StandBasalArea(g1, species=_SPECIES)
    if g1 <= _EPS or h1 <= _EPS or h2 <= _EPS or n1 <= _EPS or n2 <= _EPS:
        return StandBasalArea(0.0, species=_SPECIES)

    b1, b2, b3, b4, b5 = 1.46553, 0.52449, 0.17701, 16.53755, -386.71670
    ratio_a = a1 / a2
    tq = float(thinning_quotient)
    if age_thin is not None and 0.0 < tq < 1.0 and float(age_thin) > 0.0:
        ba_rem_over_before = 1.0 - tq
        thin_term = b5 * ((ba_rem_over_before / float(age_thin)) * (1.0 / a2 - 1.0 / a1))
    else:
        thin_term = 0.0
    log_arg = (
        ratio_a * math.log(g1)
        + b1 * (1.0 - ratio_a)
        + b2 * (math.log(h2) - ratio_a * math.log(h1))
        + b3 * (math.log(n2) - ratio_a * math.log(n1))
        + b4 * ((math.log(n2) - math.log(n1)) / a2)
        + thin_term
    )
    return StandBasalArea(max(0.0, math.exp(log_arg)), species=_SPECIES)


def kuehne_2022_stand_volume(
    basal_area2: StandBasalArea | float,
    dominant_height2: float,
    age2: AgeMeasurement,
    *,
    thinning_quotient: float = 1.0,
    age_thin: float | None = None,
) -> StandVolume:
    """Return total stem volume (`m3/ha`). Kuehne et al. (2022) Eq. (8).

        VOL2 = b1 * BA2^b2 * HTDOM2^b3 * exp(b4/A2)
               * (BA_after/BA_before)^( b5 * (AGE_thin/A2) )

    The thinning factor is 1.0 for an unthinned period (thinning_quotient = 1.0
    or age_thin = None). Volume base data: individual-tree over-bark functions of
    Braastad (1966), Brantseg (1967) and Vestjordet (1967).
    """
    g2 = _non_negative(basal_area2, "basal_area2")
    h2 = _non_negative(dominant_height2, "dominant_height2")
    a2 = _require_total_age(age2, "age2")
    b1, b2, b3, b4, b5 = 0.65394, 0.96928, 0.91504, -2.05278, -0.06848
    tq = float(thinning_quotient)
    if age_thin is not None and 0.0 < tq < 1.0 and float(age_thin) > 0.0:
        thin_factor = tq ** (b5 * (float(age_thin) / a2))
    else:
        thin_factor = 1.0
    volume = b1 * g2**b2 * h2**b3 * math.exp(b4 / a2) * thin_factor
    return StandVolume(max(0.0, volume), species=_SPECIES)


def kuehne_2022_stems_after_thinning_ratio(basal_area_quotient: float) -> float:
    """Trees-after / trees-before ratio. Kuehne et al. (2022) Eq. (9).

        TPH_after/TPH_before = exp( b1 + b2 * (BA_after/BA_before) )

    Converts a specified basal-area thinning into the corresponding stem removal.
    """
    gq = _non_negative(basal_area_quotient, "basal_area_quotient")
    b1, b2 = -1.91239, 1.94414
    return math.exp(b1 + b2 * gq)


def kuehne_2022_basal_area_after_thinning_ratio(stem_quotient: float) -> float:
    """Basal-area-after / before ratio. Kuehne et al. (2022) Eq. (10).

        BA_after/BA_before = ( ln(TPH_after/TPH_before) - b1 ) / b2

    Algebraic inverse of :func:`kuehne_2022_stems_after_thinning_ratio`.
    """
    nq = float(stem_quotient)
    if nq <= 0.0:
        raise ValueError("Input 'stem_quotient' must be positive.")
    b1, b2 = -1.91239, 1.94414
    return (math.log(nq) - b1) / b2


__all__ = [
    "kuehne_2022_stem_density",
    "kuehne_2022_basal_area",
    "kuehne_2022_stand_volume",
    "kuehne_2022_stems_after_thinning_ratio",
    "kuehne_2022_basal_area_after_thinning_ratio",
]


DESCRIPTOR = FormulaDescriptor(
    component_id="kuehne_2022_growth",
    source=SourceReference(
        author="Kuehne, C., McLean, J.P., Maleki, K., Antón-Fernández, C. & Astrup, R.",
        year=2022,
        title=(
            "A stand-level growth and yield model for thinned and unthinned "
            "even-aged Scots pine forests in Norway. Silva Fennica 56(1) art. "
            "10627 (stem density, basal area, volume and thinning, Eqs. 6-10)"
        ),
    ),
    species_groups={"pine": frozenset({"Pinus sylvestris"})},
    units={},
    kernel_names=(
        "kuehne_2022_stem_density",
        "kuehne_2022_basal_area",
        "kuehne_2022_stand_volume",
        "kuehne_2022_stems_after_thinning_ratio",
        "kuehne_2022_basal_area_after_thinning_ratio",
    ),
)
