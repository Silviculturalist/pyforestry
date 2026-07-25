"""Allen et al. (2020) stand-level growth & yield model for Norway spruce.

Implements the whole-stand growth-and-yield system of

    Allen, M.G. II, Anton-Fernandez, C. & Astrup, R. (2020). "A stand-level
    growth and yield model for thinned and unthinned managed Norway spruce
    forests in Norway." Scandinavian Journal of Forest Research 35(5-6):238-251.
    DOI 10.1080/02827581.2020.1773525.

Coefficients are from the paper's Table 4. The equation forms were cross-checked
against the authors' own reference implementation (R package
``mickyallen10/sprucesim``); that package is an *indication* only -- the paper is
the source of record.

Single species: Norway spruce (Picea abies). Stand age ``A`` is age FROM PLANTING
(total age); site index ``S`` is dominant height (m) at base age 40 years.

The dominant-height projection (Eq. 4) uses the exponent ``(b2 + b3)/X0`` exactly
as published in Allen et al. (2020) and as coded in the authors' sprucesim R
package.
"""

from __future__ import annotations

import math
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
from pyforestry.base.helpers.tree_species import TreeSpecies

_EPS: Final[float] = 1e-9
_SI_REF_AGE: Final[AgeMeasurement] = Age.TOTAL(40.0)
_SPECIES: Final = TreeSpecies.Norway.picea_abies


def _require_total_age(age: AgeMeasurement, name: str) -> float:
    """Validate and convert a total (from-planting) age measurement to float."""
    if not isinstance(age, AgeMeasurement):
        raise TypeError(f"Input '{name}' must be an AgeMeasurement.")
    if age.code != Age.TOTAL.value:
        raise TypeError(f"Input '{name}' must use Age.TOTAL (age from planting).")
    value = float(age)
    if value <= 0.0:
        raise ValueError(f"Input '{name}' must be positive.")
    return value


def _coerce_non_negative(value: float, name: str) -> float:
    """Convert to float and require a non-negative value."""
    out = float(value)
    if out < 0.0:
        raise ValueError(f"Input '{name}' must be non-negative.")
    return out


def allen_2020_dominant_height(
    dominant_height_m: float,
    age1: AgeMeasurement,
    age2: AgeMeasurement,
) -> float:
    """Project Norway spruce dominant height (`m`) from ``age1`` to ``age2``.

    Allen et al. (2020) Eq. (4), GADA Chapman-Richards (Cieszewski & Bailey 2000):

        L  = ln(1 - exp(-b1 * A1))
        X0 = 0.5 * ( ln(H1) + b2*L + sqrt( (ln(H1) + b2*L)^2 - 4*b3*L ) )
        H2 = H1 * [ (1 - exp(-b1*A2)) / (1 - exp(-b1*A1)) ] ^ ( (b2 + b3)/X0 )
    """
    h1 = _coerce_non_negative(dominant_height_m, "dominant_height_m")
    a1 = _require_total_age(age1, "age1")
    a2 = _require_total_age(age2, "age2")
    if math.isclose(a1, a2):
        return h1
    if h1 <= _EPS:
        raise ValueError("Input 'dominant_height_m' must be positive for projection.")

    b1, b2, b3 = 0.01605, 0.61208, 4.43722
    lg = math.log(1.0 - math.exp(-b1 * a1))
    base = math.log(h1) + b2 * lg
    discriminant = base * base - 4.0 * b3 * lg
    if discriminant < 0.0:
        raise ValueError("Non-real X0 in Allen dominant-height (negative discriminant).")
    x0 = 0.5 * (base + math.sqrt(discriminant))
    if abs(x0) < _EPS:
        raise ValueError("Degenerate X0 (near zero) in Allen dominant-height.")
    ratio = (1.0 - math.exp(-b1 * a2)) / (1.0 - math.exp(-b1 * a1))
    return h1 * ratio ** ((b2 + b3) / x0)


def allen_2020_site_index(
    dominant_height_m: float,
    age: AgeMeasurement,
) -> SiteIndexValue:
    """Return site index (dominant height at base age 40 yr) as a SiteIndexValue."""
    si = allen_2020_dominant_height(dominant_height_m, age, _SI_REF_AGE)
    return SiteIndexValue(
        si,
        reference_age=Age.TOTAL(40.0),
        species={_SPECIES},
        fn=allen_2020_dominant_height,
    )


def _si_value(si_h40: SiteIndexValue | float) -> float:
    """Extract the site-index value (m at base age 40) as a float."""
    return _coerce_non_negative(float(si_h40), "si_h40")


def allen_2020_stem_survival(
    stems1: Stems | float,
    age1: AgeMeasurement,
    age2: AgeMeasurement,
    si_h40: SiteIndexValue | float,
    *,
    thinning_quotient: float = 1.0,
) -> Stems:
    """Project surviving stems per hectare. Allen et al. (2020) Eq. (3).

        N2 = ( N1^b1 + b2 * (GA/GB) * (S/1000)^b3 * (A2^b4 - A1^b4) )^(1/b5)

    ``thinning_quotient`` is the basal-area thinning quotient GA/GB (= 1.0 for an
    unthinned period); thinning (GA/GB < 1) reduces the additive mortality term.
    """
    n1 = _coerce_non_negative(stems1, "stems1")
    a1 = _require_total_age(age1, "age1")
    a2 = _require_total_age(age2, "age2")
    si = _si_value(si_h40)
    if a2 < a1:
        raise ValueError("Input 'age2' must be greater than or equal to 'age1'.")
    if math.isclose(a1, a2):
        return Stems(n1, species=_SPECIES)
    if n1 <= 0.0:
        return Stems(0.0, species=_SPECIES)

    b1, b2, b3, b4, b5 = -1.0085, 0.03675, 3.76228, 2.55410, -1.0097
    tq = float(thinning_quotient)
    bracket = n1**b1 + b2 * tq * (si / 1000.0) ** b3 * (a2**b4 - a1**b4)
    if bracket <= 0.0:
        return Stems(0.0, species=_SPECIES)
    projected = bracket ** (1.0 / b5)
    return Stems(max(0.0, projected), species=_SPECIES)


def allen_2020_basal_area(
    basal_area1: StandBasalArea | float,
    age1: AgeMeasurement,
    age2: AgeMeasurement,
    dominant_height1: float,
    dominant_height2: float,
    stems1: Stems | float,
    stems2: Stems | float,
    *,
    thinning_quotient: float = 1.0,
    height_at_thinning: float | None = None,
) -> StandBasalArea:
    """Project basal area (`m2/ha`). Allen et al. (2020) Eq. (2).

        G2 = G1^(H1/H2) * exp[ b1 * (N2/N1)^b2 * (1 - H1/H2) * TR ]
        TR = (GA/GB)^( b3 * HT/H2 )            (thinning response; TR = 1 unthinned)

    Per Eq. (2) the thinning response ``TR`` sits INSIDE the exponential,
    scaling the whole exponent argument -- not as a factor on ``G2`` outside
    the exp. ``b1`` is the single linear multiplier and ``b2`` is the EXPONENT
    on the density ratio N2/N1 (contrast with the mis-typeset Maleki et al.
    2022 variant). Pass the observed/projected dominant heights explicitly. For
    an unthinned period leave ``thinning_quotient=1.0`` / ``height_at_thinning=None``.
    """
    g1 = _coerce_non_negative(basal_area1, "basal_area1")
    a1 = _require_total_age(age1, "age1")
    a2 = _require_total_age(age2, "age2")
    h1 = _coerce_non_negative(dominant_height1, "dominant_height1")
    h2 = _coerce_non_negative(dominant_height2, "dominant_height2")
    n1 = _coerce_non_negative(stems1, "stems1")
    n2 = _coerce_non_negative(stems2, "stems2")
    if a2 < a1:
        raise ValueError("Input 'age2' must be greater than or equal to 'age1'.")
    if math.isclose(a1, a2):
        return StandBasalArea(g1, species=_SPECIES)
    if n1 <= 0.0 or h2 <= _EPS:
        return StandBasalArea(0.0, species=_SPECIES)

    b1, b2, b3 = 4.77696, 0.30957, -0.1479
    ratio_h = h1 / h2
    ratio_n = n2 / n1
    tq = float(thinning_quotient)
    if height_at_thinning is not None and 0.0 < tq < 1.0:
        tr = tq ** (b3 * (float(height_at_thinning) / h2))
    else:
        tr = 1.0
    # Eq. (2): TR multiplies the exponent argument inside the exp; unthinned
    # (TR = 1) reduces to G1^(H1/H2) * exp[b1 * (N2/N1)^b2 * (1 - H1/H2)].
    g2 = g1**ratio_h * math.exp(b1 * ratio_n**b2 * (1.0 - ratio_h) * tr)
    return StandBasalArea(max(0.0, g2), species=_SPECIES)


def allen_2020_stand_volume(
    basal_area2: StandBasalArea | float,
    dominant_height2: float,
    age2: AgeMeasurement,
) -> StandVolume:
    """Return stand volume (`m3/ha`). Allen et al. (2020) Eq. (1).

        V2 = b1 * G2^b2 * H2^b3 * exp( b4 / A2 )

    Total stem volume base data from Vestjordet (1967). Single equation for
    thinned and unthinned stands.
    """
    g2 = _coerce_non_negative(basal_area2, "basal_area2")
    h2 = _coerce_non_negative(dominant_height2, "dominant_height2")
    a2 = _require_total_age(age2, "age2")
    b1, b2, b3, b4 = 0.24961, 1.15036, 1.01153, 2.320398
    volume = b1 * g2**b2 * h2**b3 * math.exp(b4 / a2)
    return StandVolume(max(0.0, volume), species=_SPECIES)


def allen_2020_quadratic_mean_diameter(
    basal_area: StandBasalArea | float,
    stems: Stems | float,
) -> QuadraticMeanDiameter:
    """Return quadratic mean diameter (`cm`) from basal area and stem number.

    QMD = 200 * sqrt( G / (pi * N) )      (G in m2/ha, N in stems/ha)
    """
    g = _coerce_non_negative(basal_area, "basal_area")
    n = _coerce_non_negative(stems, "stems")
    if n <= 0.0:
        return QuadraticMeanDiameter(0.0)
    qmd = 200.0 * math.sqrt(g / (math.pi * n))
    return QuadraticMeanDiameter(qmd)


def allen_2020_stems_after_thinning_ratio(basal_area_quotient: float) -> float:
    """Trees-after / trees-before ratio (NA/NB). Allen et al. (2020) Eq. (5a).

        NA/NB = exp( b1 + b2 * (GA/GB) )

    ``basal_area_quotient`` is GA/GB (basal area after / before thinning). Use to
    convert a specified basal-area removal into the corresponding stem removal
    under the paper's thinning-from-below assumption.
    """
    gq = _coerce_non_negative(basal_area_quotient, "basal_area_quotient")
    b1, b2 = -1.93267, 1.92953
    return math.exp(b1 + b2 * gq)


def allen_2020_basal_area_after_thinning_ratio(stem_quotient: float) -> float:
    """Basal-area-after / before ratio (GA/GB). Allen et al. (2020) Eq. (5b).

        GA/GB = ( log(NA/NB) - b1 ) / b2

    Algebraic inverse of :func:`allen_2020_stems_after_thinning_ratio`; use to
    convert a specified stem removal into the corresponding basal-area removal.
    """
    nq = float(stem_quotient)
    if nq <= 0.0:
        raise ValueError("Input 'stem_quotient' must be positive.")
    b1, b2 = -1.93267, 1.92953
    return (math.log(nq) - b1) / b2


__all__ = [
    "allen_2020_dominant_height",
    "allen_2020_site_index",
    "allen_2020_stem_survival",
    "allen_2020_basal_area",
    "allen_2020_stand_volume",
    "allen_2020_quadratic_mean_diameter",
    "allen_2020_stems_after_thinning_ratio",
    "allen_2020_basal_area_after_thinning_ratio",
]


DESCRIPTOR = FormulaDescriptor(
    component_id="allen_2020_growth",
    source=SourceReference(
        author="Allen, M.G. II; Anton-Fernandez, C.; Astrup, R.",
        year=2020,
        title=(
            "A stand-level growth and yield model for thinned and unthinned "
            "managed Norway spruce forests in Norway. "
            "Scand. J. For. Res. 35(5-6):238-251"
        ),
    ),
    species_groups={"norway_spruce": frozenset({"Picea abies"})},
    units={},
    kernel_names=(
        "allen_2020_dominant_height",
        "allen_2020_site_index",
        "allen_2020_stem_survival",
        "allen_2020_basal_area",
        "allen_2020_stand_volume",
        "allen_2020_quadratic_mean_diameter",
        "allen_2020_stems_after_thinning_ratio",
        "allen_2020_basal_area_after_thinning_ratio",
    ),
)
