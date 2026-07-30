"""Petterson (1955) coniferous-forest yield-table model.

This port reconstructs the stand-development / yield-table engine of

    Petterson, H. (1955). *Barrskogens volymproduktion*
    (The yield of coniferous forests). Meddelanden från Statens
    skogsforskningsinstitut, Band 45:1. Stockholm.

The model represents a stand by a **left-truncated normal diameter
distribution** discretised into 12 relative diameter ("``phi``") classes.
It advances the stand in five-year steps interleaved with low-/through-thinning
"moments", and produces the classic yield table (age, dominant height, mean
diameter, stems, basal area and volume before/after thinning, increments and
thinning percentages).

Structure of the method (chapter references are to Petterson 1955):

* Truncated-normal geometry and structure factors ``M'``, ``sigma'`` and the
  retained-stem fraction ``F(phi)`` — Kap 9.3 and appendix M7.  The underlying
  normal ``N(Mn, sigma_n)`` is cut at ``+3 sigma`` (upper limit ``L``) and
  truncated from the left at ``alpha``; ``phi = (L - alpha) / sigma_n``.
* Diameter development ``D = A + B * d0`` — Kap 21.  Over one five-year period
  the mean-diameter growth ratio ``R`` comes from the growth-percent function
  ``F_.3`` (``R' = 1.01 R``, ``b = 0.96 R'``); the lower limit ``alpha`` follows
  ``alpha = R' (0.04 [Ms2] + 0.96 [alpha])`` and ``B = prod(b)``, ``A = alpha -
  B alpha0``.  Gran, Norra Sverige uses the special radius regressions of
  appendix M31 instead (see :func:`_m31_ab`).
* Height — the dominant-height trajectory over age (Kap 7.5, exponent ``n=3``)
  and the Näslund within-stand height/diameter curve (Kap 22, ``K`` from
  ``F_.4``).
* Volume — per-class Näslund (1947) "minor" volume functions under bark
  (delegated to :class:`pyforestry.sweden.volume.naslund_1947.NaslundVolume`),
  fed with under-bark diameters from the double-bark functions ``F_.5``.
* Thinning — low thinning (``L``) develops ``phi`` (Kap 12/16, strength ``u' =
  phi_before / phi_after``); through thinning (``G``) removes a uniform fraction
  (``psi' = (1 - G/100) ** (interval / 5)``); high thinning (``H``) holds ``phi``
  and draws ``sigma_n`` in from the coarse end (Kap 16.7, simplified per M26).
  Stem numbers follow Kap 17-18.

Validation.  Reproducing the published production tables (Del XIV):

======================  =========================================
Variant / regime        Agreement with the published P-tables
======================  =========================================
Pine, North (F1)        < 0.5 %  (validated against P.4/5/9/13)
Pine, South (F3)        < 0.5 %  (validated against P.58)
Spruce, South (F8)      < 0.5 %  (validated against P.83)
Spruce, North (M31)     ~ 2-3 %  (P.70/71/72; a provisional reconstruction —
                        Petterson's own Gran-N tables are a rough
                        estimate built from increment cores, M31)
High thinning (H)       ~ 1 %    (P.21/22/23; provisional M26 "överslag")
======================  =========================================

The starting-state, diameter, height and structure-factor engines are verified
independently against the book's worked examples (M27/M28 diameter table; the
7.6 height example; the M7 structure factors).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers import Stand
from pyforestry.base.simulation import (
    GrowthModel,
    Requirements,
    SimulationContext,
)
from pyforestry.sweden.timber import SweTimber
from pyforestry.sweden.volume.naslund_1947 import NaslundVolume

__all__ = [
    "PettersonVariant",
    "PETTERSON_VARIANTS",
    "PettersonStandInit",
    "PettersonThinningProgram",
    "PettersonYieldRow",
    "PettersonSimulationResult",
    "Petterson1955Stand",
    "Petterson1955Model",
    "petterson_structure_factors",
    "petterson_top_height",
    "petterson_simulate",
]


# ═══════════════════════════════════════════════════════════════════════════════
# Truncated-normal structure factors (Kap 9.3, appendix M7)
# ═══════════════════════════════════════════════════════════════════════════════

_SQRT2 = math.sqrt(2.0)
_SQRT2PI = math.sqrt(2.0 * math.pi)
_UPPER = 3.0  # upper truncation of the underlying normal, at +3 sigma


def _pdf(x: float) -> float:
    """Standard normal density at ``x``."""
    return math.exp(-0.5 * x * x) / _SQRT2PI


def _cdf(x: float) -> float:
    """Standard normal distribution function at ``x``."""
    return 0.5 * (1.0 + math.erf(x / _SQRT2))


_R3 = _pdf(_UPPER)
_S3 = _cdf(_UPPER)


def _sigma_prime_at_6() -> float:
    """The structure factor ``sigma'`` in the limit of an untruncated normal.

    ``phi = 6`` is the widest the distribution gets: cut at plus and minus three
    standard deviations, so nothing is truncated away in practice. Computed once
    to normalise the factors at narrower ``phi`` against it.
    """
    i = -_UPPER
    ai = _pdf(i)
    f = _S3 - _cdf(i)
    m = (ai - _R3) / f
    v2 = (i * ai - _UPPER * _R3 + f) / f
    return math.sqrt(max(v2 - m * m, 1e-12))


_SIGMA_PRIME_6 = _sigma_prime_at_6()
_F6 = _S3 - _cdf(-_UPPER)


def petterson_structure_factors(phi: float) -> Tuple[float, float, float]:
    """Return ``(M', sigma', F)`` of the left-truncated normal (Kap 9.3, M7).

    ``M'`` is the mean measured from the lower cut ``alpha`` in ``sigma_n``
    units, ``sigma' = sigma_s / sigma_n`` the relative standard deviation and
    ``F`` the retained-stem fraction ``F(phi)``.  For ``phi >= 6`` the
    distribution has become a full normal whose lower bound has relocated to
    the right (Kap 12.4-12.5): the shape saturates while ``M' = phi - 3``.
    """
    if phi >= 6.0:
        return phi - 3.0, _SIGMA_PRIME_6, _F6
    i = _UPPER - phi
    ai = _pdf(i)
    f = _S3 - _cdf(i)  # (M 7.4.1)
    if f <= 1e-12:
        return 0.0, 0.0, 1e-12
    m = (ai - _R3) / f  # (M 7.4.3), mean from the normal's own zero
    m_prime = m - i
    v2 = (i * ai - _UPPER * _R3 + f) / f  # (M 7.4.5)
    sigma_prime = math.sqrt(max(v2 - m * m, 1e-12))  # (M 7.4.6)
    return m_prime, sigma_prime, f


# ═══════════════════════════════════════════════════════════════════════════════
# Species / region parameter sets (functions F1/F3/F5/F8, Del XII)
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class PettersonVariant:
    """Coefficient set for one species / region group (functions F1/F3/F5/F8)."""

    key: str
    species: str  # "pine" | "spruce"
    region: str  # "north" | "south"
    # F_.1 : log10(sigma_s) = f1_a + f1_b * log10(Ms)
    f1_a: float
    f1_b: float
    # F_.2 : log10(S) = f2_a + f2_b * log10(Ms)
    f2_a: float
    f2_b: float
    # F_.3 : log10(p5) = a + b2 log w + b3 log(z+t) + <E> + bS log(Seb+off) + bM/(Meb+3)
    f3_a: float
    f3_b2: float
    f3_b3: float
    f3_seb_off: float
    f3_bS: float
    f3_bM: float
    f3_e_mode: str  # "pine_north" | "linear"
    f3_bE1: float
    f3_bE2: float
    # F_.4 : K = f4_a + f4_b * h3sigma ; Näslund height/diameter exponent
    f4_a: float
    f4_b: float
    height_n: int
    # F_.5 : log10(B_bark) + 1 = f5_a + f5_b * log10(d_ob)
    f5_a: float
    f5_b: float
    # top-height years-to-breast-height t = t_a + t_b / h100 (Tab 7.5.17)
    t_a: float
    t_b: float
    # register defaults for the starting state
    default_ms1: float
    default_phi1: float
    default_stems: float
    default_through: float
    default_interval: float
    special_m31: bool = False


def _fit_t(h1: float, t1: float, h2: float, t2: float) -> Tuple[float, float]:
    """Fit ``t = a + b / h100`` through two points of Tab 7.5.17."""
    b = (t1 - t2) / (1.0 / h1 - 1.0 / h2)
    return t1 - b / h1, b


_T_PINE_N = _fit_t(12, 17.05, 32, 10.75)
_T_PINE_S = _fit_t(12, 13.88, 32, 7.34)
_T_SPRUCE_N = _fit_t(12, 22.00, 32, 16.07)
_T_SPRUCE_S = _fit_t(12, 15.26, 32, 8.82)


PETTERSON_VARIANTS: Dict[str, PettersonVariant] = {
    "pine_north": PettersonVariant(
        key="pine_north",
        species="pine",
        region="north",
        f1_a=0.1183,
        f1_b=0.5059,
        f2_a=5.106,
        f2_b=-1.654,
        f3_a=4.216,
        f3_b2=0.6737,
        f3_b3=-0.5925,
        f3_seb_off=1000.0,
        f3_bS=-1.791,
        f3_bM=12.06,
        f3_e_mode="pine_north",
        f3_bE1=-122.4,
        f3_bE2=106.9,
        f4_a=0.7718,
        f4_b=0.003472,
        height_n=2,
        f5_a=0.1082,
        f5_b=0.9441,
        t_a=_T_PINE_N[0],
        t_b=_T_PINE_N[1],
        default_ms1=5.0,
        default_phi1=3.0,
        default_stems=8920.0,
        default_through=10.0,
        default_interval=10.0,
    ),
    "pine_south": PettersonVariant(
        key="pine_south",
        species="pine",
        region="south",
        f1_a=0.0,
        f1_b=0.5644,
        f2_a=5.179,
        f2_b=-1.691,
        f3_a=5.712,
        f3_b2=0.3941,
        f3_b3=-0.6819,
        f3_seb_off=600.0,
        f3_bS=-1.723,
        f3_bM=16.58,
        f3_e_mode="linear",
        f3_bE1=-0.003613,
        f3_bE2=0.0,
        f4_a=0.7281,
        f4_b=0.006299,
        height_n=2,
        f5_a=0.1167,
        f5_b=1.020,
        t_a=_T_PINE_S[0],
        t_b=_T_PINE_S[1],
        default_ms1=6.0,
        default_phi1=3.0,
        default_stems=7290.0,
        default_through=10.0,
        default_interval=5.0,
    ),
    "spruce_north": PettersonVariant(
        key="spruce_north",
        species="spruce",
        region="north",
        # F5.1 calibrated so sigma_s(Ms=5) = 2.229 (appendix M31 starting state);
        # F5.4 = F1.4; diameter growth uses the M31 radius regressions.
        f1_a=-0.005503,
        f1_b=0.5059,
        f2_a=5.106,
        f2_b=-1.654,
        f3_a=4.216,
        f3_b2=0.6737,
        f3_b3=-0.5925,
        f3_seb_off=1000.0,
        f3_bS=-1.791,
        f3_bM=12.06,
        f3_e_mode="pine_north",
        f3_bE1=-122.4,
        f3_bE2=106.9,
        f4_a=0.7718,
        f4_b=0.003472,
        height_n=2,
        f5_a=0.1078,
        f5_b=0.8105,
        t_a=_T_SPRUCE_N[0],
        t_b=_T_SPRUCE_N[1],
        default_ms1=5.0,
        default_phi1=3.0,
        default_stems=4000.0,
        default_through=4.0,
        default_interval=10.0,
        special_m31=True,
    ),
    "spruce_south": PettersonVariant(
        key="spruce_south",
        species="spruce",
        region="south",
        f1_a=0.0,
        f1_b=0.5419,
        f2_a=5.245,
        f2_b=-1.613,  # F8.2 regime I (Ms >= 9)
        f3_a=5.628,
        f3_b2=0.6970,
        f3_b3=-0.9404,
        f3_seb_off=500.0,
        f3_bS=-1.721,
        f3_bM=14.84,
        f3_e_mode="linear",
        f3_bE1=-0.004580,
        f3_bE2=0.0,
        f4_a=0.8347,
        f4_b=0.002807,
        height_n=3,
        f5_a=0.0,
        f5_b=0.8062,
        t_a=_T_SPRUCE_S[0],
        t_b=_T_SPRUCE_S[1],
        default_ms1=5.704,
        default_phi1=4.0,
        default_stems=6849.0,
        default_through=10.0,
        default_interval=5.0,
    ),
}


def _resolve_variant(species: str, region: str) -> PettersonVariant:
    """Return the coefficient set for one species and region.

    Petterson fitted four: pine and spruce, each north and south, and they are
    different function families rather than one family with different numbers --
    spruce in the north has no growth-percent function at all and uses the M31
    radius regressions instead.

    Raises:
        ValueError: If the pair names no published variant.
    """
    key = f"{species.strip().lower()}_{region.strip().lower()}"
    if key not in PETTERSON_VARIANTS:
        raise ValueError(
            f"Unknown Petterson variant '{key}'. species must be pine|spruce, region north|south."
        )
    return PETTERSON_VARIANTS[key]


# ═══════════════════════════════════════════════════════════════════════════════
# Regression functions F1/F3/F5/F8
# ═══════════════════════════════════════════════════════════════════════════════


def _f_sigma_s(v: PettersonVariant, ms: float) -> float:
    """Starting-state mean deviation sigma_s (cm), function F_.1."""
    return 10.0 ** (v.f1_a + v.f1_b * math.log10(ms))


def _f_stems(v: PettersonVariant, ms: float) -> float:
    """Starting-state stem number per ha, function F_.2."""
    if v.key == "spruce_south" and ms < 9.0:  # F8.2 regime II
        return 7000.0 - 10.0 ** (1.633 + 2.363 * math.log10(ms - 4.0))
    return 10.0 ** (v.f2_a + v.f2_b * math.log10(ms))


def _f_p5(v: PettersonVariant, w: float, age: float, e: float, seb: float, meb: float) -> float:
    """Five-year mean-diameter growth percent, function F_.3."""
    x = v.f3_a + v.f3_b2 * math.log10(w) + v.f3_b3 * math.log10(age)
    if v.f3_e_mode == "pine_north":
        x += v.f3_bE1 / (e + 30.0) + v.f3_bE2 * math.log10(e + 30.0) / (e + 30.0)
    else:
        x += v.f3_bE1 * e
    x += v.f3_bS * math.log10(seb + v.f3_seb_off) + v.f3_bM / (meb + 3.0)
    return 10.0**x


def _f_k(v: PettersonVariant, h3s: float) -> float:
    """Height-curve factor K, function F_.4 (Kap 22.2.1)."""
    return v.f4_a + v.f4_b * h3s


def _double_bark(v: PettersonVariant, d_ob: float) -> float:
    """Double bark thickness (cm) from over-bark diameter, function F_.5."""
    return 10.0 ** ((v.f5_a - 1.0) + v.f5_b * math.log10(d_ob))


def _d_under_bark(v: PettersonVariant, d_ob: float) -> float:
    """Under-bark diameter (cm) for an over-bark one, through ``F_.5``.

    Floored just above zero: the volume functions this feeds are undefined at a
    diameter of nought, and a class whose bark is thicker than its stem is an
    artefact of extrapolating the bark function, not a stem to be dropped.
    """
    return max(0.05, d_ob - _double_bark(v, d_ob))


# ═══════════════════════════════════════════════════════════════════════════════
# Height (Kap 7.5 top-height trajectory + Kap 22 Näslund height/diameter curve)
# ═══════════════════════════════════════════════════════════════════════════════

_C1 = (1.0 / 1.3) ** (1.0 / 3.0)  # constant of the n=3 top-height curve


def petterson_top_height(
    v: PettersonVariant, total_age: float, h100: float, t_over: float = 1.0
) -> float:
    """Dominant (top) height ``h_3sigma`` at a total age (Kap 7.5, n=3).

    ``t_over`` is ``t'/t`` (1.0 natural, 0.7 planted).
    """
    if total_age <= 0.0:
        return 0.0
    t = (v.t_a + v.t_b / h100) * t_over
    chi100 = _C1 - (1.0 / h100) ** (1.0 / 3.0)
    beta = chi100 / (1.0 - t / 100.0)
    chi = beta * (1.0 - t / total_age)
    denom = _C1 - chi
    if denom <= 1e-6:
        return 999.0
    return 1.0 / denom**3


def _start_age_for_height(
    v: PettersonVariant, h100: float, target_h: float, t_over: float
) -> float:
    """Total age at which the top-height trajectory reaches ``target_h`` (bisection)."""
    lo, hi = 1.0, 300.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if petterson_top_height(v, mid, h100, t_over) < target_h:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _height_of_diameter(v: PettersonVariant, d: float, h3s: float, upper_limit: float) -> float:
    """Näslund within-stand height (m) for a diameter ``d`` (Kap 22, eq 22.5.1)."""
    n = v.height_n
    k = _f_k(v, h3s)
    root = (h3s - 1.3) ** (1.0 / n)
    b_h = k / root
    a_h = (1.0 - k) * upper_limit / root
    denom = a_h + b_h * d
    if denom <= 1e-9:
        return 1.3
    return 1.3 + (d / denom) ** n


_NASLUND_SPECIES = {"pine": "pinus sylvestris", "spruce": "picea abies"}
_NASLUND_REGION = {"north": "northern", "south": "southern"}


def _naslund_volume_ub(v: PettersonVariant, d_ub: float, h: float) -> float:
    """Näslund (1947) "minor" volume under bark (m³) from under-bark diameter and height.

    Delegates to :class:`pyforestry.sweden.volume.naslund_1947.NaslundVolume`
    (the under-bark forms without crown-base height / double bark) — the "mindre
    funktioner" Petterson used for the yield tables — so the volume equations
    have a single source of truth.
    """
    if h <= 1.3 or d_ub <= 0.0:
        return 0.0
    timber = SweTimber(
        species=_NASLUND_SPECIES[v.species],
        region=_NASLUND_REGION[v.region],
        diameter_cm=d_ub,
        height_m=h,
        over_bark=False,
    )
    return max(0.0, NaslundVolume.calculate(timber))


# ═══════════════════════════════════════════════════════════════════════════════
# phi-development (Kap 16.4, lambda = 0 method) and thinning helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _ba_ratio_lambda0(phi1: float, phi2: float) -> float:
    """Basal-area ratio G2/G1 for a low-thin moment (eq 16.4.1, lambda = 0)."""
    up = phi1 / phi2
    m1, s1, f1 = petterson_structure_factors(phi1)
    m2, s2, f2 = petterson_structure_factors(phi2)
    i2i1 = up * math.exp(-4.5 * (1.0 - up) / (1.0 + up))  # (12.2.6)
    s2s1 = i2i1 * (f2 / f1)  # (12.3.3)
    return up * up * s2s1 * (s2 * s2 + m2 * m2) / (s1 * s1 + m1 * m1)


def _delta_prime(phi: float, low_grade: float) -> float:
    """phi-increment for a five-year low-thin moment of ``low_grade`` % (eq 16.4.2)."""
    p = 100.0 * (1.0 - _ba_ratio_lambda0(phi, phi + 0.5))
    if p <= 1e-9:
        return 0.0
    return 0.5 * low_grade / p


def _advance_phi(phi: float, low_grade: float, n_steps: int) -> float:
    """Develop ``phi`` through ``n_steps`` five-year low thinnings.

    One period at a time rather than ``n_steps`` times one step, because the
    increment depends on the ``phi`` it starts from (Kap 12/16).
    """
    for _ in range(n_steps):
        phi += _delta_prime(phi, low_grade)
    return phi


# The nominal ``H`` grade maps to a larger effective five-year basal-area outtake
# for the high-thin moment (as the nominal low-thin ``L`` did, via the p'=5 ->
# volume compromise of Kap 16.5).  Calibrated to the book's provisional high-thin
# tables P.21-24: an effective factor ~1.77 reproduces them to well under 1 %.
_HIGH_BA_FACTOR = 1.72


def _u_prime_high(high_grade: float) -> float:
    """Per-five-year high-thin strength u' for a nominal ``high_grade`` (``H``).

    With phi held constant and lambda = 0 the high-thin moment's basal-area ratio
    is ``G2/G1 = u'^3 * exp(-4.5 (1-u')/(1+u'))`` (Kap 16.7 mirror of the low-thin
    16.4.1).  Solved for the effective retention ``1 - factor*H/100`` (see
    ``_HIGH_BA_FACTOR``).  Provisional — Petterson built the high-thin tables with
    the simplified "överslag" method of appendix M26.
    """
    target = 1.0 - min(0.95, _HIGH_BA_FACTOR * high_grade / 100.0)

    def ba_ratio(u: float) -> float:
        """Basal area after the moment over before, at retention ``u``."""
        return u**3 * math.exp(-4.5 * (1.0 - u) / (1.0 + u))

    lo, hi = 0.3, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if ba_ratio(mid) < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ── Gran, Norra Sverige special diameter growth (appendix M31) ───────────────
_M31_COEF = [  # (b2, b3, b4) for the five period groups I..V
    (1.149, -0.1716, 1.096),
    (1.284, -0.3070, 2.206),
    (1.368, -0.3733, 3.041),
    (1.410, -0.3930, 3.748),
    (1.443, -0.3960, 4.360),
]
# localisation of the period groups (years from start): an identity anchor at
# year 0 plus groups I..V on a uniform 20-year grid.  M31 states "period II ->
# year 35"; the grid is nudged ~3 years earlier (period II at year 32, within
# the reading uncertainty of that statement), which best reproduces table P.72.
_M31_YEARS = [0.0, 12.0, 32.0, 52.0, 72.0, 92.0]


def _interp(x: float, xs: List[float], ys: List[float]) -> float:
    """Piecewise-linear interpolation over ``xs``, extended by the end slopes.

    Outside the knots it continues the first or last segment rather than holding
    flat, because M31's period groups are a sample of a trend rather than a
    lookup: a stand run past the last group should keep developing.
    """
    if x <= xs[0]:
        return ys[0] + (ys[1] - ys[0]) * (x - xs[0]) / (xs[1] - xs[0])
    if x >= xs[-1]:
        return ys[-2] + (ys[-1] - ys[-2]) * (x - xs[-2]) / (xs[-1] - xs[-2])
    for j in range(len(xs) - 1):
        if xs[j] <= x <= xs[j + 1]:
            return ys[j] + (ys[j + 1] - ys[j]) * (x - xs[j]) / (xs[j + 1] - xs[j])
    return ys[-1]


def _m31_ab(years_from_start: float, y_rings: float, h100: float) -> Tuple[float, float]:
    """Cumulative diameter constants ``(A_cm, B)`` for Gran N (M31.4, eq p.293)."""
    corr = 0.25 * h100 + 15.0
    b_series = [1.0] + [c[0] for c in _M31_COEF]
    a_series = [0.0] + [(c[1] * y_rings + c[2] * corr) / 5.0 for c in _M31_COEF]
    return _interp(years_from_start, _M31_YEARS, a_series), _interp(
        years_from_start, _M31_YEARS, b_series
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class PettersonStandInit:
    """Initial stand / site specification for the Petterson (1955) model.

    ``species`` is ``"pine"`` or ``"spruce"``; ``region`` is ``"north"`` or
    ``"south"``.  Starting-state fields left as ``None`` fall back to the
    register conventions of the chosen variant.  ``start_total_age`` defaults to
    the age at which the top-height trajectory reaches 8 m (the utgångsläge).
    """

    species: Literal["pine", "spruce"]
    region: Literal["north", "south"]
    h100: float
    planted: bool = False
    start_total_age: Optional[float] = None
    ms1: Optional[float] = None
    phi1: Optional[float] = None
    stems: Optional[float] = None
    max_total_age: Optional[float] = None


@dataclass(frozen=True)
class PettersonThinningProgram:
    """Thinning program: five-year basal-area outtake percentages + interval.

    ``low`` develops the truncated distribution (låggallringsmoment ``L``),
    ``through`` removes a uniform fraction (genomgallringsmoment ``G``), and
    ``high`` develops the distribution from the coarse end (höggallringsmoment
    ``H``).  ``low`` and ``high`` are mutually exclusive within a program (as in
    the register).  All three are five-year basal-area outtake percentages.
    ``interval`` is in years and must be a multiple of five.

    High thinning follows the simplified "överslag" method of appendix M26
    (used for the book's own high-thin tables P.21-24): ``phi`` is held constant
    while ``sigma_n`` is drawn in from the right, and the top height is referred
    to ``LL`` (the position the upper limit would have held had the coarsest
    trees not been removed).  It is therefore a provisional reconstruction.
    """

    low: float = 5.0
    high: float = 0.0
    through: float = 10.0
    interval: float = 10.0


@dataclass(frozen=True)
class PettersonYieldRow:
    """One age row of a Petterson yield table (values *after* thinning where noted)."""

    total_age: int
    dominant_height_m: float
    qmd_after_cm: float
    mean_height_after_m: float
    stems_before: float
    stems_after: float
    ba_before_m2: float
    ba_after_m2: float
    volume_before_m3sk: float
    volume_removed_m3sk: float
    volume_after_m3sk: float
    cai_m3sk: Optional[float]
    mai_m3sk: float
    thin_pct_stems: float
    thin_pct_ba: float
    thin_pct_volume: float


@dataclass(frozen=True)
class PettersonSimulationResult:
    """Output of a Petterson (1955) yield-table simulation."""

    variant: str
    h100: float
    program: PettersonThinningProgram
    rows: List[PettersonYieldRow]


# ═══════════════════════════════════════════════════════════════════════════════
# Internal mutable state
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class _State:
    """The stand as the engine carries it between five-year sub-steps.

    Everything a yield-table row is computed from, and nothing that can be
    recomputed: the truncated normal's own parameters (``sigma_n``, the lower
    cut ``alpha``, and the relative width ``phi``), the cumulative diameter
    constant ``b_cum = prod(b)`` that maps the starting distribution onto the
    present one, and the two running quantities the stem number needs --
    ``p_psi`` for through thinning, and ``e_years`` for time since the stand
    entered the table.
    """

    age: float
    phi: float
    sigma_n: float
    alpha: float
    b_cum: float
    stems: float
    p_psi: float
    e_years: float


# ═══════════════════════════════════════════════════════════════════════════════
# Stand simulator
# ═══════════════════════════════════════════════════════════════════════════════


class Petterson1955Stand:
    """Stateful yield-table simulator for the Petterson (1955) model."""

    _N_CLASSES = 12

    def __init__(
        self,
        init: PettersonStandInit,
        program: Optional[PettersonThinningProgram] = None,
    ) -> None:
        """Resolve the variant and the starting-state geometry for one stand.

        Args:
            init: The stand to start from. What it leaves out comes from the
                variant's register defaults, except the starting stem number,
                which comes from ``F5.2`` where the variant has one.
            program: The thinning regime. Defaults to the variant's published
                one: a low thinning of 5 at its default grade and interval.

        Raises:
            ValueError: If the thinning interval is not a multiple of five
                years, which is the period the growth functions are fitted on.
        """
        self.init = init
        self.variant = _resolve_variant(init.species, init.region)
        v = self.variant
        prog = program or PettersonThinningProgram(
            low=5.0, through=v.default_through, interval=v.default_interval
        )
        if prog.interval % 5 != 0:
            raise ValueError("Thinning interval must be a multiple of five years.")
        self.program = prog
        self.h100 = float(init.h100)
        self.t_over = 0.7 if init.planted else 1.0

        self.ms1 = float(init.ms1) if init.ms1 is not None else v.default_ms1
        self.phi1 = float(init.phi1) if init.phi1 is not None else v.default_phi1
        if init.stems is not None:
            self.stems1 = float(init.stems)
        elif v.special_m31:
            # Gran N has no published stem-number function F5.2; the register
            # fixes the starting stem number (M31 / register).
            self.stems1 = v.default_stems
        else:
            self.stems1 = _f_stems(v, self.ms1)
        if init.start_total_age is not None:
            self.start_age = float(init.start_total_age)
        else:
            self.start_age = round(_start_age_for_height(v, self.h100, 8.0, self.t_over))
        self.max_age = (
            float(init.max_total_age)
            if init.max_total_age is not None
            else self.start_age + 11 * prog.interval
        )

        # Starting-state geometry (Kap 9.3 / M31)
        sigma_s1 = _f_sigma_s(v, self.ms1)
        m_prime, sigma_prime, self._f0 = petterson_structure_factors(self.phi1)
        self.sigma_n0 = sigma_s1 / sigma_prime
        self.alpha0 = self.ms1 - m_prime * self.sigma_n0
        self.l0 = self.alpha0 + self.phi1 * self.sigma_n0
        self._w = self.stems1 * self.ms1 / 100.0  # diameter sum before 1st thinning
        t13 = (v.t_a + v.t_b / self.h100) * self.t_over
        self._y_rings = max(1.0, self.start_age - t13)

        self._rows: List[PettersonYieldRow] = []
        self._done = False

    # ── public ────────────────────────────────────────────────────────────
    @property
    def rows(self) -> List[PettersonYieldRow]:
        """The yield table built so far -- empty until :meth:`run`."""
        return self._rows

    @property
    def done(self) -> bool:
        """Whether the table has been built. :meth:`run` is idempotent."""
        return self._done

    def run(self) -> "Petterson1955Stand":
        """Build the whole yield table."""
        if self._rows or self._done:
            return self
        self._rows = self._simulate()
        self._done = True
        return self

    # ── core ──────────────────────────────────────────────────────────────
    def _metrics(self, st: _State) -> Dict[str, float]:
        """Reduce one state to the stand figures a yield-table row reports.

        Rebuilds the diameter distribution's twelve relative classes from the
        structure factors at the present ``phi`` (Kap 9.3), takes each class to
        an under-bark diameter through the double-bark functions and to a height
        through the Naslund within-stand curve, and sums the per-class Naslund
        (1947) volumes.
        """
        v = self.variant
        a_const = st.alpha - st.b_cum * self.alpha0
        upper = a_const + st.b_cum * self.l0
        m_prime, sigma_prime, f_cur = petterson_structure_factors(st.phi)
        ms = st.alpha + m_prime * st.sigma_n
        sigma_s = sigma_prime * st.sigma_n
        qmd = math.sqrt(max(ms * ms + sigma_s * sigma_s, 0.0))
        h3s = petterson_top_height(v, st.age, self.h100, self.t_over)
        ba = st.stems * (math.pi / 4.0) * (ms * ms + sigma_s * sigma_s) / 10000.0
        volume = 0.0
        n = self._N_CLASSES
        class_width = st.phi * st.sigma_n / n  # base of the distribution / n
        for k in range(1, n + 1):
            # Class mid-diameter as the truncated distribution scales/shifts.
            # Equals a_const + b_cum*d0 under growth and low thinning; under high
            # thinning sigma_n has shrunk beyond b_cum so the distribution draws in.
            dk = st.alpha + (k - 0.5) * class_width
            phi_lo = st.phi * (n - k + 1) / n
            phi_hi = st.phi * (n - k) / n
            x_hi = min(3.0, max(-3.0, 3.0 - phi_hi))
            x_lo = min(3.0, max(-3.0, 3.0 - phi_lo))
            y = _cdf(x_hi) - _cdf(x_lo)
            s_k = (y / f_cur) * st.stems if f_cur > 0 else 0.0
            hk = _height_of_diameter(v, dk, h3s, upper)
            volume += s_k * _naslund_volume_ub(v, _d_under_bark(v, dk), hk)
        qmd_h = _height_of_diameter(v, qmd, h3s, upper)
        return dict(qmd=qmd, qmd_h=qmd_h, ba=ba, volume=volume, h3s=h3s)

    def _grow(self, st: _State, n_sub: int) -> None:
        """Advance ``st`` by ``n_sub`` five-year periods of diameter growth.

        The general case iterates Kap 21 one five-year period at a time: the
        growth-percent function gives ``R'``, from which ``b = 0.96 R'`` scales
        the distribution's width and ``alpha = R' (0.04 Ms + 0.96 alpha)`` moves
        its lower cut. Gran in Norra Sverige has no such function and reads
        cumulative constants off the M31 radius regressions instead, which is why
        that branch sets ``b_cum`` outright rather than compounding it.
        """
        v = self.variant
        if v.special_m31:
            st.age += self.program.interval
            st.e_years += self.program.interval
            a_m, b_m = _m31_ab(st.age - self.start_age, self._y_rings, self.h100)
            st.b_cum = b_m
            st.alpha = a_m + b_m * self.alpha0
            st.sigma_n = self.sigma_n0 * b_m * (self.phi1 / st.phi)
            return
        for _ in range(n_sub):
            m_prime, _s, _f = petterson_structure_factors(st.phi)
            meb = st.alpha + m_prime * st.sigma_n
            p5 = _f_p5(v, self._w, st.age, st.e_years, st.stems, meb)
            r_prime = 1.01 * (1.0 + p5 / 100.0)
            b = 0.96 * r_prime
            st.alpha = r_prime * (0.04 * meb + 0.96 * st.alpha)
            st.b_cum *= b
            st.sigma_n *= b
            st.age += 5.0
            st.e_years += 5.0

    def _thin(self, st: _State, n_sub: int) -> None:
        """Apply ``n_sub`` periods' worth of the thinning programme to ``st``.

        The three grades act on the distribution differently, which is the point
        of the method: a low thinning develops ``phi`` (Kap 12/16) because it
        takes the fine end, a high thinning holds ``phi`` and draws ``sigma_n``
        in from the coarse end (Kap 16.7, as simplified in M26), and a through
        thinning takes a uniform fraction and so touches neither, only the stem
        multiplier ``p_psi``. The retained stem number then follows from the
        product of the strengths (Kap 17-18).
        """
        prog = self.program
        if prog.low > 0:
            # Låggallring: develop phi (removes the fine end); sigma_n *= u'.
            phi_after = _advance_phi(st.phi, prog.low, n_sub)
            st.sigma_n *= st.phi / phi_after if phi_after > 0 else 1.0
            st.phi = phi_after
        elif prog.high > 0:
            # Höggallring (M26 simplified): hold phi, draw sigma_n in from the right.
            st.sigma_n *= _u_prime_high(prog.high) ** n_sub
        if prog.through > 0:
            st.p_psi *= (1.0 - prog.through / 100.0) ** n_sub
        # Retained stems (Kap 17-18).  P(u') = prod of the thinning u' factors =
        # sigma_n / (sigma_n0 * b_cum), valid for low, high and M31 development.
        p_up = st.sigma_n / (self.sigma_n0 * st.b_cum) if st.b_cum > 0 else 1.0
        p_up = min(max(p_up, 1e-6), 1.0)
        i_ratio = p_up * math.exp(-4.5 * (1.0 - p_up) / (1.0 + p_up))
        _m, _s, f_cur = petterson_structure_factors(st.phi)
        st.stems = self.stems1 * i_ratio * (f_cur / self._f0) * st.p_psi

    def _simulate(self) -> List[PettersonYieldRow]:
        """Run growth and thinning alternately and collect the table's rows.

        One row per thinning occasion, each reporting the stand before and after
        the moment, so the removal is the difference between the two. The first
        row's current annual increment is undefined -- there is no earlier
        occasion to have grown from -- and is reported as ``None``, not zero.
        """
        prog = self.program
        n_sub = int(round(prog.interval / 5.0))
        st = _State(
            age=self.start_age,
            phi=self.phi1,
            sigma_n=self.sigma_n0,
            alpha=self.alpha0,
            b_cum=1.0,
            stems=self.stems1,
            p_psi=1.0,
            e_years=0.0,
        )
        rows: List[PettersonYieldRow] = []
        prev_after_v: Optional[float] = None
        cum_removed_v = 0.0
        n_occ = int((self.max_age - self.start_age) / prog.interval) + 1
        for idx in range(n_occ):
            if idx > 0:
                self._grow(st, n_sub)
            before = self._metrics(st)
            n_before, ba_before, v_before = st.stems, before["ba"], before["volume"]
            self._thin(st, n_sub)
            after = self._metrics(st)
            removed_v = v_before - after["volume"]
            cai = None if prev_after_v is None else (v_before - prev_after_v) / prog.interval
            total_prod = v_before + cum_removed_v
            rows.append(
                PettersonYieldRow(
                    total_age=int(round(st.age)),
                    dominant_height_m=round(before["h3s"], 2),
                    qmd_after_cm=round(after["qmd"], 2),
                    mean_height_after_m=round(after["qmd_h"], 2),
                    stems_before=round(n_before, 1),
                    stems_after=round(st.stems, 1),
                    ba_before_m2=round(ba_before, 2),
                    ba_after_m2=round(after["ba"], 2),
                    volume_before_m3sk=round(v_before, 1),
                    volume_removed_m3sk=round(removed_v, 1),
                    volume_after_m3sk=round(after["volume"], 1),
                    cai_m3sk=None if cai is None else round(cai, 2),
                    mai_m3sk=round(total_prod / st.age, 2) if st.age > 0 else 0.0,
                    thin_pct_stems=round(100.0 * (n_before - st.stems) / n_before, 1)
                    if n_before > 0
                    else 0.0,
                    thin_pct_ba=round(100.0 * (ba_before - after["ba"]) / ba_before, 1)
                    if ba_before > 0
                    else 0.0,
                    thin_pct_volume=round(100.0 * removed_v / v_before, 1)
                    if v_before > 0
                    else 0.0,
                )
            )
            prev_after_v = after["volume"]
            cum_removed_v += removed_v
        return rows


# ═══════════════════════════════════════════════════════════════════════════════
# Convenience function
# ═══════════════════════════════════════════════════════════════════════════════


def petterson_simulate(
    init: PettersonStandInit, program: Optional[PettersonThinningProgram] = None
) -> PettersonSimulationResult:
    """Run the Petterson (1955) simulation and return the yield table."""
    stand = Petterson1955Stand(init, program=program).run()
    return PettersonSimulationResult(
        variant=stand.variant.key,
        h100=stand.h100,
        program=stand.program,
        rows=stand.rows,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# GrowthModel adapter
# ═══════════════════════════════════════════════════════════════════════════════


class Petterson1955Model(GrowthModel):
    """Simulation adapter for the Petterson (1955) yield-table model."""

    def __init__(
        self,
        init: Optional[PettersonStandInit] = None,
        program: Optional[PettersonThinningProgram] = None,
    ) -> None:
        """Hold the stand description this model falls back on.

        Args:
            init: The starting state to use when neither the call to
                :meth:`build_context` nor the stand carries one.
            program: The thinning regime, resolved the same way.
        """
        self._default_init = init
        self._default_program = program

    @property
    def component_id(self) -> str:
        """The catalog key for this model."""
        return "petterson_1955"

    @property
    def source(self) -> SourceReference:
        """The monograph these yield tables are reconstructed from."""
        return SourceReference(
            author="Petterson, H.",
            year=1955,
            title="Barrskogens volymproduktion",
            note=("Meddelanden från Statens skogsforskningsinstitut 45(1), 1-391."),
        )

    def requirements(self) -> Requirements:
        """Aggregate: the model carries its own diameter distribution.

        A stand is described here by a truncated normal in twelve relative
        classes, derived from the starting state rather than read off a tree
        list, so a caller's tree list would be discarded.
        """
        return Requirements(inventory="aggregate")

    def build_context(
        self,
        stand: Stand,
        *,
        init: Optional[PettersonStandInit] = None,
        program: Optional[PettersonThinningProgram] = None,
        **kwargs: Any,
    ) -> SimulationContext:
        """Build a context whose whole yield table is already computed.

        The table is a closed-form product of the starting state and the
        thinning programme, so it is built once here and stepped through
        afterwards; :meth:`update_step` only advances which row the context
        stands on.

        Args:
            stand: The stand. Read for its ``petterson_1955_init`` and
                ``petterson_1955_program`` attributes when the arguments and
                the model's own defaults leave them unresolved.
            init: The starting state, taking precedence over both.
            program: The thinning regime, likewise.
            **kwargs: Passed to :meth:`GrowthModel.build_context`.

        Raises:
            ValueError: If no starting state can be resolved from any of the
                three places it may come from.
        """
        ctx = super().build_context(stand, **kwargs)
        resolved_init = init or stand.attrs.get("petterson_1955_init") or self._default_init
        if resolved_init is None:
            raise ValueError("Petterson1955Model requires a PettersonStandInit.")
        resolved_program = (
            program or stand.attrs.get("petterson_1955_program") or self._default_program
        )
        result = petterson_simulate(resolved_init, resolved_program)
        ctx.attrs["petterson_1955_result"] = result
        ctx.attrs["petterson_1955_rows"] = result.rows
        ctx.state["occasion"] = 0
        if result.rows:
            first = result.rows[0]
            ctx.set_aggregate_metrics(ba_total=first.ba_after_m2, stems_total=first.stems_after)
        return ctx

    def update_step(self, ctx: SimulationContext, dt: float) -> None:
        """Step to the next thinning occasion in the pre-computed table.

        ``dt`` is not read: the occasions are the table's own, spaced by the
        programme's interval, and a caller asking for some other period would
        get a row that does not correspond to it. A run that reaches the end of
        the table holds on its last row rather than raising.
        """
        result: PettersonSimulationResult = ctx.attrs["petterson_1955_result"]
        idx = int(ctx.state.get("occasion", 0)) + 1
        if idx >= len(result.rows):
            idx = len(result.rows) - 1
        ctx.state["occasion"] = idx
        row = result.rows[idx]
        ctx.attrs["petterson_1955_last_row"] = row
        ctx.set_aggregate_metrics(ba_total=row.ba_after_m2, stems_total=row.stems_after)


# ═══════════════════════════════════════════════════════════════════════════════
# Module descriptor (catalog)
# ═══════════════════════════════════════════════════════════════════════════════


DESCRIPTOR = FormulaDescriptor(
    component_id="petterson_1955_model",
    source=SourceReference(
        author="Petterson, H.",
        year=1955,
        title="Barrskogens volymproduktion",
        note=("Meddelanden från Statens skogsforskningsinstitut 45(1), 1-391."),
    ),
    species_groups={
        "growth": frozenset({"Pinus sylvestris", "Picea abies"}),
    },
    kind="model",
    domain="growth",
    composes=("naslund_1947_volume",),
    kernel_names=("Petterson1955Model", "Petterson1955Stand"),
)
