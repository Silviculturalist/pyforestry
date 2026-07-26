"""Eriksson (1976) spruce production model (FORTRAN77 port).

This port keeps the original growth, thinning, and mortality logic while
integrating with pyforestry primitives:

- Site index and height trajectories use Hagglund (1970). The southern trajectory delegates
  to the shared module (it matches the FORTRAN ``GRANS`` exactly). The northern trajectory
  uses an Eriksson-local Hagglund function 8.4 (:func:`_solve_northern_spruce_8_4`) to match
  the FORTRAN ``GRANN`` (latitude-independent) rather than the shared module's latitude-refined
  function 8.7. ``StandInit.reproduce_fortran_errors`` flips the two known transcription errors
  in the canonical listing's ``GRANN`` (RK exponent, RM2 intercept).
- Initial stems/basal area use Elfving & Hagglund (1975) when not supplied. This is the same
  model as the FORTRAN's built-in generator (labels 600-616, comment "HAGGLUND, ELFVING"):
  the FORTRAN ``Q``/``R`` regressions are Functions 5.3/5.4 (stems) and 6.3 (basal area), and
  its ``X(1) > 3.5`` branch is the north/south split (see :func:`estimate_initial_stand`).
- Thinning schedules support age, basal-area, and dominant-height intervals; the last mirrors
  FORTRAN ``IV=2`` by converting height targets to ages (:func:`_height_program_to_age`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from functools import lru_cache
from typing import Any, Dict, List, Literal, Mapping, Optional, Sequence, Tuple

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers import Age, SiteIndexValue, Stand, Stems
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.base.simulation import (
    ActionSpec,
    GrowthModel,
    Requirements,
    SimulationContext,
    TriggerSpec,
)
from pyforestry.sweden.blocks.elfving_hagglund_1975 import ElfvingHagglundInitialStand
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970

__all__ = [
    "StandInit",
    "ThinningProgram",
    "ThinningRequest",
    "SimulationResult",
    "Eriksson1976Stand",
    "Eriksson1976ManagementSchedule",
    "Eriksson1976Model",
    "estimate_initial_stand",
    "simulate",
]


# -------------------------
# Coefficient matrix C(6,14)
# Fortran DATA fills column-major; here we store row-major for MC=1..6.
# Columns are C(MC,1..14).
# -------------------------
C = [
    [
        0.250,
        -0.046,
        0.049,
        0.334,
        -0.748,
        -0.308,
        0.835,
        0.524,
        3.505,
        0.899,
        4.777,
        -0.224,
        -0.138,
        0.447,
    ],
    [
        0.213,
        -0.055,
        0.085,
        0.460,
        -0.875,
        -0.313,
        0.833,
        1.858,
        3.376,
        2.548,
        4.606,
        -0.247,
        -0.183,
        0.488,
    ],
    [
        0.304,
        -0.056,
        0.126,
        0.035,
        -0.571,
        -0.154,
        0.838,
        2.613,
        3.356,
        3.313,
        4.589,
        -0.249,
        -0.206,
        0.498,
    ],
    [
        0.260,
        -0.059,
        0.034,
        0.112,
        -0.667,
        -0.066,
        0.838,
        2.872,
        3.347,
        3.666,
        4.567,
        -0.266,
        -0.236,
        0.568,
    ],
    [
        0.337,
        -0.046,
        0.056,
        0.120,
        -0.789,
        -0.013,
        0.839,
        3.229,
        3.458,
        4.090,
        4.681,
        -0.255,
        -0.243,
        0.763,
    ],
    [
        0.337,
        -0.046,
        0.056,
        0.120,
        -0.789,
        -0.013,
        0.844,
        2.646,
        3.479,
        3.260,
        4.738,
        -0.280,
        -0.243,
        0.763,
    ],
]


@dataclass(frozen=True)
class ThinningProgram:
    """Thinning program for Eriksson (1976).

    Units of ``first_trigger`` and ``intervals`` depend on ``interval_type``:

    - ``"age"``: ``first_trigger`` is the first thinning breast-height age (years) and
      ``intervals`` are the year gaps between successive thinnings.
    - ``"basal_area"``: ``first_trigger`` is the standing basal area (m2/ha) that triggers
      the first thinning and ``intervals`` are basal-area increments (m2/ha).
    - ``"dominant_height"``: ``first_trigger`` is the first target dominant height (m) and
      ``intervals`` are successive dominant-height increments (m). Mirrors FORTRAN ``IV=2``:
      the targets are converted to breast-height ages via the site's height trajectory and the
      simulation then runs on the age scheduler.
    """

    interval_type: Literal["age", "basal_area", "dominant_height"]
    first_trigger: float
    intervals: Sequence[float] = field(default_factory=list)
    outtake_type: Literal["percent", "residual", "absolute"] = "percent"
    outtakes: Sequence[float] = field(default_factory=list)
    diameter_factors: Sequence[float] = field(default_factory=list)
    use_diameter_factors: bool = False


@dataclass(frozen=True)
class StandInit:
    """Initial stand and site specification for the Eriksson (1976) model."""

    region: Literal["north", "south", 1, 2]
    h100_m: float
    start_bh_age: float
    final_bh_age: Optional[float] = None
    final_total_age: Optional[float] = None
    stems: Optional[float] = None
    basal_area: Optional[float] = None
    latitude: Optional[float] = None
    altitude_m: float = 0.0
    stand_density_factor: float = 0.65
    broadleaves_percent_ba: float = 0.0
    even_aged: bool = True
    spatial_distribution: int = 1
    pct: bool = False
    growth_scaling: int = 1
    culture_class: int = 1
    vg: float = 100.0
    use_culture_height: bool = False
    reproduce_fortran_errors: bool = False


@dataclass(frozen=True)
class SimulationResult:
    """Simulation outputs for Eriksson (1976)."""

    rows: List[Dict[str, Any]]
    self_thinning_summary: Dict[str, float]


@dataclass(frozen=True)
class ThinningRequest:
    """Explicit thinning request for a single growth step."""

    outtake: float
    outtake_type: Literal["percent", "residual", "absolute"] = "percent"
    diameter_factor: Optional[float] = None


@dataclass
class _ErikssonState:
    """Mutable internal state for the Eriksson 1976 simulator."""

    t: float
    sn1: float
    g1: float
    gu1: float
    du1: float
    p: float = 0.0
    gu22: float = 0.0
    vu22: float = 0.0
    du22: float = 0.0
    g22: float = 0.0
    v22: float = 0.0
    w22: float = 0.0
    to_g2: float = 0.0
    to_v2: float = 0.0
    tw12: float = 0.0
    sn5: float = 0.0
    tmg: float = 0.0
    tmv: float = 0.0
    gz1: float = 0.0
    gp: float = 0.0
    gs2: float = 0.0
    vs: float = 1.0
    val: bool = False
    interval_idx: int = -1
    outtake_idx: int = -1
    gf_idx: int = -1
    tmx: Optional[float] = None
    gmx: Optional[float] = None


def _normalize_region(region: str | int) -> Literal["north", "south"]:
    """Normalize region inputs to 'north' or 'south'."""
    if isinstance(region, str):
        norm = region.strip().lower()
        if norm in {"north", "n", "norr", "norra"}:
            return "north"
        if norm in {"south", "s", "sodra"}:
            return "south"
    if region == 1:
        return "north"
    if region == 2:
        return "south"
    raise ValueError(f"Unknown region: {region}")


def _site_class_index_from_h100_dm(h100_dm: float) -> int:
    """Return the site class index based on H100 in decimetres."""
    mc = 1
    if h100_dm >= 180:
        mc = 2
    if h100_dm >= 220:
        mc = 3
    if h100_dm >= 260:
        mc = 4
    if h100_dm >= 300:
        mc = 5
    if h100_dm >= 340:
        mc = 6
    return mc


@lru_cache(maxsize=None)
def _solve_northern_spruce_8_4(
    h100_m: float, culture: bool, reproduce_fortran_errors: bool
) -> Tuple[float, float, float, float]:
    """Solve Hägglund (1972) function 8.4 parameters for northern-Sweden spruce.

    Mirrors the FORTRAN ``GRANN`` subroutine, which uses function 8.4
    (latitude-independent) rather than the latitude-refined 8.7 that the shared
    :class:`~pyforestry.sweden.siteindex.hagglund_1970.Hagglund_1970` module selects at
    mid latitudes. The bisection/Newton calibration is copied verbatim from that module so
    the only differences are the fixed 8.4 coefficients and the two toggled constants.

    ``reproduce_fortran_errors`` reproduces the canonical listing's transcription errors
    (RK exponent ``1.105``, RM2 intercept ``-0.42795``); the default uses the corrected
    values (``1.0105`` and ``-0.42759``). The corrected RM2 intercept is intentionally kept
    local here and is *not* the ``-0.42579`` currently in ``hagglund_1970.py``.

    Returns ``(A, RK, RM2, T13)`` calibrated so the trajectory passes through ``h100_m`` at
    total age 100. Dominant height at breast-height age ``t`` is
    ``13 + A * (1 - exp(-RK * t)) ** RM2`` (decimetres).
    """
    d_intercept = -0.42795 if reproduce_fortran_errors else -0.42759
    rk_exponent = 1.105 if reproduce_fortran_errors else 1.0105
    b_coeff, c_coeff, e_coeff = 3.4501, 0.77518, 1.33935
    p = 0.9175 if culture else 1.0
    top_height_dm = h100_m * 10.0 - 13.0

    def bonitering(eff_age: float) -> Tuple[float, float, float, float]:
        ai1, ai2 = 10.0, 600.0
        a2 = rk = rm2 = 0.0
        while abs(ai1 - ai2) > 1:
            ai3 = (ai1 + ai2) / 2.0
            rk = 0.001936 + 0.00004100 * ai3**rk_exponent
            a2 = b_coeff * ai3**c_coeff
            rm2 = d_intercept + e_coeff / (0.56721 + 0.000008 * ai3**1.8008)
            dif = top_height_dm - a2 * (1 - math.exp(-eff_age * rk)) ** rm2
            if dif <= 0:
                ai2 = ai3
            else:
                ai1 = ai3
        t26 = (-1 / rk) * math.log(1 - (13 / a2) ** (1 / rm2))
        t13 = p * (7.0287 + 0.66118 * t26)
        return a2, rk, rm2, t13

    # Effective DBH age at TOTAL(100): solve eff_age + T13(eff_age) = 100 (Newton-Raphson).
    def f(x: float) -> float:
        return x + bonitering(x)[3] - 100.0

    x = 100.0 * 0.35
    for _ in range(30):
        fx = f(x)
        fpx = (f(x + 0.001) - f(x - 0.001)) / 0.002
        if abs(fpx) < 1e-8:  # pragma: no cover - defensive numerical guard
            break
        x_new = x - fx / fpx
        if abs(x_new - x) < 1e-6:
            x = x_new
            break
        x = x_new

    return bonitering(x)


@dataclass(frozen=True)
class _HagglundContext:
    """Wrap Hägglund (1970) site index and height functions for the stand.

    Northern dominant height and time-to-breast-height are computed with an Eriksson-local
    function 8.4 (:func:`_solve_northern_spruce_8_4`) to match the FORTRAN ``GRANN``; the
    southern trajectory delegates to the shared module, which already matches ``GRANS``.
    """

    h100_m: float
    region: Literal["north", "south"]
    latitude: Optional[float]
    culture: bool
    reproduce_fortran_errors: bool = False

    def site_index_value(self) -> SiteIndexValue:
        """Return the site index value for the configured region."""
        if self.region == "north":
            lat = 64.0 if self.latitude is None else float(self.latitude)
            return Hagglund_1970.height_trajectory.picea_abies.northern_sweden(
                dominant_height=self.h100_m,
                age=Age.TOTAL(100),
                age2=Age.TOTAL(100),
                latitude=lat,
                culture=self.culture,
            )
        return Hagglund_1970.height_trajectory.picea_abies.southern_sweden(
            dominant_height=self.h100_m,
            age=Age.TOTAL(100),
            age2=Age.TOTAL(100),
        )

    def time_to_breast_height(self) -> float:
        """Return time (years) to breast height for the stand."""
        if self.region == "north":
            _, _, _, t13 = _solve_northern_spruce_8_4(
                self.h100_m, self.culture, self.reproduce_fortran_errors
            )
            return t13
        return Hagglund_1970.time_to_breast_height.picea_abies.southern_sweden(
            dominant_height=self.h100_m,
            age=Age.TOTAL(100),
            age2=Age.TOTAL(100),
        )

    def height_dm(self, bh_age: float) -> float:
        """Return dominant height in decimetres at breast-height age."""
        if self.region == "north":
            a2, rk, rm2, _ = _solve_northern_spruce_8_4(
                self.h100_m, self.culture, self.reproduce_fortran_errors
            )
            return 13.0 + a2 * (1 - math.exp(-rk * bh_age)) ** rm2
        height = Hagglund_1970.height_trajectory.picea_abies.southern_sweden(
            dominant_height=self.h100_m,
            age=Age.TOTAL(100),
            age2=Age.DBH(bh_age),
        )
        return float(height) * 10.0

    def bh_age_for_height_dm(self, target_dm: float) -> float:
        """Invert the (monotonic) height trajectory for breast-height age.

        Used by the ``"dominant_height"`` thinning schedule to turn dominant-height targets
        into breast-height ages, mirroring FORTRAN ``IV=2`` (labels 94-99).
        """
        lo, hi = 0.0, 400.0
        for _ in range(60):
            mid = (lo + hi) / 2.0
            if self.height_dm(mid) < target_dm:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0


def _qmd_cm_from_basal_area_and_stems(basal_area: float, stems: float) -> float:
    """Return quadratic mean diameter (cm) from basal area and stems."""
    if basal_area <= 0.0 or stems <= 0.0:
        return 0.0
    return math.sqrt(12732.4 * basal_area / stems)


def convert_basal_area_over_to_under_bark(
    basal_area_over_bark: float,
    breast_height_age_years: float,
    qmd_over_bark_cm: float,
    site_class_index: int,
) -> float:
    """Convert stand basal area from over-bark to under-bark terms."""
    if basal_area_over_bark <= 0.0:
        return 0.0
    c13 = C[site_class_index - 1][12]
    factor = (
        0.01
        * (10**0.9777)
        * (basal_area_over_bark**0.135)
        * (breast_height_age_years**0.112)
        * (qmd_over_bark_cm**c13)
    )
    return basal_area_over_bark * (1.0 - factor)


def convert_basal_area_over_to_under_bark_with_reference(
    basal_area_over_bark: float,
    breast_height_age_years: float,
    qmd_over_bark_cm: float,
    reference_basal_area: float,
    site_class_index: int,
) -> float:
    """Convert over-bark basal area using a reference basal-area term."""
    if basal_area_over_bark <= 0.0:
        return 0.0
    reference = max(reference_basal_area, 0.01)
    c13 = C[site_class_index - 1][12]
    factor = (
        0.01
        * (10**0.9777)
        * (reference**0.135)
        * (breast_height_age_years**0.112)
        * (qmd_over_bark_cm**c13)
    )
    return basal_area_over_bark * (1.0 - factor)


def convert_basal_area_under_to_over_bark(
    basal_area_under_bark: float,
    breast_height_age_years: float,
    qmd_under_bark_cm: float,
    site_class_index: int,
) -> float:
    """Convert stand basal area from under-bark to over-bark terms."""
    if basal_area_under_bark <= 0.0:
        return 0.0
    c12 = C[site_class_index - 1][11]
    factor = (
        0.01
        * (10**1.6549)
        * (basal_area_under_bark ** (-0.281))
        * (breast_height_age_years**0.125)
        * (qmd_under_bark_cm**c12)
    )
    return basal_area_under_bark * (1.0 + factor)


def convert_thinning_basal_area_under_to_over_bark(
    thinning_basal_area_under_bark: float,
    breast_height_age_years: float,
    thinning_qmd_under_bark_cm: float,
    reference_basal_area_under_bark: float,
    site_class_index: int,
) -> float:
    """Under-to-over bark conversion used for thinning removals."""
    if thinning_basal_area_under_bark <= 0.0:
        return 0.0
    c12 = C[site_class_index - 1][11]
    factor = (
        0.01
        * (10**1.6549)
        * (reference_basal_area_under_bark ** (-0.281))
        * (breast_height_age_years**0.125)
        * (thinning_qmd_under_bark_cm**c12)
    )
    return thinning_basal_area_under_bark * (1.0 + factor)


def compute_stand_volume_m3sk(
    basal_area_over_bark: float,
    dominant_height_dm: float,
    qmd_over_bark_cm: float,
    site_class_index: int,
) -> float:
    """Estimate stand volume (m3sk/ha) from stand-level state variables."""
    if basal_area_over_bark <= 0.0:
        return 0.0
    c7 = C[site_class_index - 1][6]
    return (
        basal_area_over_bark
        * (10 ** (-1.1406))
        * (dominant_height_dm**c7)
        * (qmd_over_bark_cm**0.1232)
    )


def compute_dry_weight_factor(diameter_increment_index: float, latitude_constant: float) -> float:
    """Compute dry-weight adjustment used in annual increment accounting."""
    if diameter_increment_index <= 0.0:
        return 0.0
    z = diameter_increment_index
    b = latitude_constant
    return (1.0467 + 0.03012 / z - 0.06523 * z + 0.005143 * z * z - 0.009945 * b) * 0.96


def project_growth_step(
    recent_thinning_basal_area_under_bark: float,
    coeff_recent_thinning: float,
    thinning_proportion_percent: float,
    coeff_thinning_proportion: float,
    thinning_structure_factor: float,
    growth_period_years: float,
    coeff_growth_period: float,
    dominant_height_dm: float,
    coeff_height: float,
    breast_height_age_years: float,
    coeff_bh_age: float,
    growth_scaling_factor: float,
    coeff_growth_scaling: float,
    residual_basal_area_under_bark: float,
    residual_stems_per_ha: float,
    site_class_index: int,
) -> Tuple[float, float, float, float, float]:
    """Run one Eriksson (1976) growth step and return updated stand metrics."""
    basal_area_increment_under_bark = (
        (10**0.4207)
        * (recent_thinning_basal_area_under_bark**coeff_recent_thinning)
        * (thinning_proportion_percent**coeff_thinning_proportion)
        * (thinning_structure_factor**0.024)
        * (growth_period_years**coeff_growth_period)
        * (dominant_height_dm**coeff_height)
        * (breast_height_age_years**coeff_bh_age)
        * (growth_scaling_factor**coeff_growth_scaling)
    )
    new_basal_area_under_bark = (
        growth_period_years * basal_area_increment_under_bark + residual_basal_area_under_bark
    )
    new_bh_age_years = breast_height_age_years + growth_period_years
    new_qmd_under_bark_cm = _qmd_cm_from_basal_area_and_stems(
        new_basal_area_under_bark, residual_stems_per_ha
    )
    new_basal_area_over_bark = convert_basal_area_under_to_over_bark(
        new_basal_area_under_bark,
        new_bh_age_years,
        new_qmd_under_bark_cm,
        site_class_index,
    )
    return (
        basal_area_increment_under_bark,
        new_basal_area_under_bark,
        new_bh_age_years,
        new_qmd_under_bark_cm,
        new_basal_area_over_bark,
    )


def estimate_initial_stand(init: StandInit) -> Tuple[float, float, float, SiteIndexValue, float]:
    """Compute dominant height, stems, and basal area for the initial stand.

    When ``stems``/``basal_area`` are not supplied, they are generated with Elfving & Hagglund
    (1975) via :class:`ElfvingHagglundInitialStand`. This is the same model as the FORTRAN's
    built-in generator (labels 600-616): its stem regression ``Q`` is Function 5.3 (north) /
    5.4 (south) and its basal-area regression ``R`` is Function 6.3 -- the slope coefficients
    match to the digit (altitude, density, ``SI > 22`` i.e. ``H100 > 220`` dm, broadleaves,
    stems, spatial distribution). The FORTRAN ``X`` inputs map to ``StandInit`` fields:
    altitude -> ``altitude_m``, stand-density factor -> ``stand_density_factor``, broadleaves
    -> ``broadleaves_percent_ba``, spatial/age structure -> ``spatial_distribution`` /
    ``even_aged``, pre-commercial thinning -> ``pct``.
    """
    region = _normalize_region(init.region)
    ctx = _HagglundContext(
        h100_m=init.h100_m,
        region=region,
        latitude=init.latitude,
        culture=init.use_culture_height,
        reproduce_fortran_errors=init.reproduce_fortran_errors,
    )
    site_index = ctx.site_index_value()
    t13 = ctx.time_to_breast_height()
    h_dom_m = ctx.height_dm(init.start_bh_age) * 0.1

    stems_value = init.stems
    basal_area_value = init.basal_area
    age_bh = Age.DBH(float(init.start_bh_age))

    if stems_value is None and basal_area_value is None:
        stems_obj, ba_obj = ElfvingHagglundInitialStand.estimate_initial_spruce_stand(
            dominant_height=float(h_dom_m),
            age_bh=age_bh,
            site_index=site_index,
            altitude=init.altitude_m,
            northern_sweden=(region == "north"),
            broadleaves_percent_ba=init.broadleaves_percent_ba,
            even_aged=init.even_aged,
            stand_density_factor=init.stand_density_factor,
            pct=init.pct,
            spatial_distribution=init.spatial_distribution,
        )
        stems_value = float(stems_obj)
        basal_area_value = float(ba_obj)
    elif stems_value is None:
        if region == "north":
            stems_obj = ElfvingHagglundInitialStand.estimate_stems_young_spruce_north(
                altitude=init.altitude_m,
                site_index=site_index,
                stand_density_factor=init.stand_density_factor,
                broadleaves_percent_ba=init.broadleaves_percent_ba,
                pct=init.pct,
                even_or_somewhat_uneven_aged=init.even_aged,
            )
        else:
            stems_obj = ElfvingHagglundInitialStand.estimate_stems_young_spruce_south(
                altitude=init.altitude_m,
                site_index=site_index,
                age_at_breast_height=age_bh,
                stand_density_factor=init.stand_density_factor,
                broadleaves_percent_ba=init.broadleaves_percent_ba,
                even_or_somewhat_uneven_aged=init.even_aged,
            )
        stems_value = float(stems_obj)
    elif basal_area_value is None:
        stems_obj = Stems(value=float(stems_value), species=TreeSpecies.Sweden.picea_abies)
        if region == "north":
            ba_obj = ElfvingHagglundInitialStand.estimate_basal_area_young_spruce_north(
                altitude=init.altitude_m,
                site_index=site_index,
                dominant_height=float(h_dom_m),
                stems=stems_obj,
                stand_density_factor=init.stand_density_factor,
                broadleaves_percent_ba=init.broadleaves_percent_ba,
                spatial_distribution=init.spatial_distribution,
                pct=init.pct,
                even_or_somewhat_uneven_aged=init.even_aged,
            )
        else:
            ba_obj = ElfvingHagglundInitialStand.estimate_basal_area_young_spruce_south(
                altitude=init.altitude_m,
                site_index=site_index,
                dominant_height=float(h_dom_m),
                age_at_breast_height=age_bh,
                stems=stems_obj,
                stand_density_factor=init.stand_density_factor,
                broadleaves_percent_ba=init.broadleaves_percent_ba,
                spatial_distribution=init.spatial_distribution,
                even_or_somewhat_uneven_aged=init.even_aged,
                pct=init.pct,
            )
        basal_area_value = float(ba_obj)

    if stems_value is None or basal_area_value is None:
        raise ValueError("Initial stems and basal area could not be resolved.")

    return float(h_dom_m), float(stems_value), float(basal_area_value), site_index, float(t13)


def _thinning_qmd_under_bark_cm(
    stand_qmd_under_bark_cm: float,
    dominant_height_dm: float,
    program: Optional[ThinningProgram],
    diameter_factor_index: int,
    diameter_factor: Optional[float] = None,
) -> float:
    """Compute QMD under bark for the thinning removal."""
    if diameter_factor is not None:
        return stand_qmd_under_bark_cm * diameter_factor
    if program is not None and program.use_diameter_factors and program.diameter_factors:
        if 0 <= diameter_factor_index < len(program.diameter_factors):
            return stand_qmd_under_bark_cm * program.diameter_factors[diameter_factor_index]
        return stand_qmd_under_bark_cm * program.diameter_factors[-1]
    if dominant_height_dm > 284.0:
        return stand_qmd_under_bark_cm
    return stand_qmd_under_bark_cm * (0.768478 + 0.00081522 * dominant_height_dm)


def _apply_growth_scaling(vs: float, init: StandInit) -> float:
    """Apply optional growth scaling adjustments."""
    if init.growth_scaling == 2:
        return vs * init.vg * 0.01
    if init.growth_scaling == 3:
        if init.culture_class == 1:
            return vs / 1.1
        if init.culture_class == 2:
            return vs / 0.85
        if init.culture_class == 3:
            return vs / 0.7
    return vs


def _schedule_age(
    t: float,
    sag: float,
    tmx: float,
    val: bool,
    interval_idx: int,
    outtake_idx: int,
    gf_idx: int,
    intervals: Sequence[float],
) -> Tuple[float, float, bool, int, int, int]:
    """Compute the next step length for age-based scheduling."""
    if val:
        interval = intervals[interval_idx] if 0 <= interval_idx < len(intervals) else 0.0
        if interval >= 1.0:
            tmx = t + interval
        else:
            tmx = sag + 10.0
        val = False
    px = tmx - t
    schedule_now = False
    if t < 30.0:
        if 1.0 <= px <= 6.0:
            schedule_now = True
        elif 6.0 < px <= 12.0:
            return math.floor(px * 0.5), tmx, val, interval_idx, outtake_idx, gf_idx
        else:
            return 6.0, tmx, val, interval_idx, outtake_idx, gf_idx
    elif t < 50.0:
        if 1.0 <= px <= 8.0:
            schedule_now = True
        elif 8.0 < px <= 16.0:
            return math.floor(px * 0.5), tmx, val, interval_idx, outtake_idx, gf_idx
        else:
            return 8.0, tmx, val, interval_idx, outtake_idx, gf_idx
    else:
        if 1.0 <= px <= 10.0:
            schedule_now = True
        elif 10.0 < px <= 20.0:
            return math.floor(px * 0.5), tmx, val, interval_idx, outtake_idx, gf_idx
        else:
            return 10.0, tmx, val, interval_idx, outtake_idx, gf_idx

    if schedule_now:
        val = True
        interval_idx += 1
        outtake_idx += 1
        gf_idx += 1
        if interval_idx >= len(intervals):
            val = False
        return px, tmx, val, interval_idx, outtake_idx, gf_idx

    return px, tmx, val, interval_idx, outtake_idx, gf_idx


def _schedule_basal_area(
    t: float,
    sag: float,
    gmx: float,
    current_ba: float,
    val: bool,
    interval_idx: int,
    outtake_idx: int,
    gf_idx: int,
    intervals: Sequence[float],
    outtakes: Sequence[float],
    gz1: float,
    gp: float,
    gs2: float,
    h_dm: float,
    gu2: float,
    sn1: float,
    mc: int,
    vs: float,
) -> Tuple[float, float, bool, int, int, int]:
    """Compute the next step length for basal-area scheduling."""
    if t < 30.0:
        p_base = 6.0
    elif t < 50.0:
        p_base = 8.0
    else:
        p_base = 10.0

    if val:
        interval = intervals[interval_idx] if 0 <= interval_idx < len(intervals) else 0.0
        if interval >= 1.0:
            gmx = current_ba + interval
        else:
            gmx = float("inf")
        next_outtake_idx = outtake_idx + 1
        if next_outtake_idx >= len(outtakes) or outtakes[next_outtake_idx] <= 0.0:
            gmx = float("inf")
        val = False

    if not val and outtake_idx >= 0:
        next_outtake_idx = outtake_idx + 1
        if next_outtake_idx >= len(outtakes) or outtakes[next_outtake_idx] <= 0.0:
            gmx = float("inf")

    if (p_base + t) >= sag:
        return max(1.0, sag - t), gmx, False, interval_idx, outtake_idx, gf_idx
    if (2 * p_base + t) >= sag:
        return max(1.0, math.floor(0.5 * (sag - t))), gmx, False, interval_idx, outtake_idx, gf_idx

    if math.isinf(gmx):
        return p_base, gmx, False, interval_idx, outtake_idx, gf_idx

    def _project(p: float) -> Tuple[float, float, float, float]:
        """Project stand state for a candidate growth period."""
        _, gu1, t1, du1, g1 = project_growth_step(
            max(0.01, gz1),
            C[mc - 1][0],
            max(0.01, gp),
            C[mc - 1][1],
            max(0.01, gs2),
            p,
            C[mc - 1][2],
            h_dm,
            C[mc - 1][3],
            t,
            C[mc - 1][4],
            vs,
            C[mc - 1][5],
            gu2,
            sn1,
            mc,
        )
        return g1, gu1, du1, t1

    midpoint = 0.5 * (gmx + current_ba)
    g12, _, _, _ = _project(p_base)

    if g12 > gmx:
        best_p = p_base
        best_diff = abs(g12 - gmx)
        p = p_base - 1.0
        while p > 0.0:
            g12, _, _, _ = _project(p)
            diff = abs(g12 - gmx)
            if diff > best_diff:
                break
            best_diff = diff
            best_p = p
            p -= 1.0
        val = True
        interval_idx += 1
        outtake_idx += 1
        gf_idx += 1
        if outtake_idx >= len(outtakes) or outtakes[outtake_idx] <= 0.0:
            val = False
        return best_p, gmx, val, interval_idx, outtake_idx, gf_idx

    best_p = p_base
    best_diff = abs(g12 - midpoint)
    p = p_base - 1.0
    while p > 0.0:
        g12, _, _, _ = _project(p)
        diff = abs(g12 - midpoint)
        if diff > best_diff:
            break
        best_diff = diff
        best_p = p
        p -= 1.0
    return best_p, gmx, False, interval_idx, outtake_idx, gf_idx


def _height_program_to_age(
    program: ThinningProgram, ctx: _HagglundContext, final_age: float
) -> ThinningProgram:
    """Convert a dominant-height thinning schedule into an equivalent age schedule.

    Mirrors FORTRAN ``IV=2`` (labels 94-99): the dominant-height targets (metres) are mapped
    to breast-height ages via the site height trajectory, then the ordinary age scheduler
    runs. ``first_trigger`` is the first target height; ``intervals`` are successive
    height increments. A height increment below 0.1 m terminates the schedule (FORTRAN
    ``GIV(K) < 1`` decimetre), as does a target that would fall at or beyond ``final_age``.
    Whole-year rounding matches the FORTRAN ``AINT(T2 + 0.5)``.
    """
    first_age = float(
        math.floor(ctx.bh_age_for_height_dm(float(program.first_trigger) * 10.0) + 0.5)
    )
    intervals_age: List[float] = []
    prev_age = first_age
    cumulative_m = float(program.first_trigger)
    for increment in list(program.intervals)[:9]:
        if float(increment) < 0.1:
            break
        cumulative_m += float(increment)
        age_k = float(math.floor(ctx.bh_age_for_height_dm(cumulative_m * 10.0) + 0.5))
        if age_k >= final_age:
            break
        intervals_age.append(age_k - prev_age)
        prev_age = age_k
    return replace(program, interval_type="age", first_trigger=first_age, intervals=intervals_age)


class Eriksson1976Stand:
    """Stateful stand simulator for the Eriksson (1976) model."""

    def __init__(
        self,
        init: StandInit,
        program: Optional[ThinningProgram] = None,
        *,
        track_history: bool = False,
    ) -> None:
        """Initialize stand state and optional thinning program."""
        self.init = init
        self.program = program
        self._track_history = track_history
        self.rows: List[Dict[str, Any]] = []
        self._last_row: Optional[Dict[str, Any]] = None
        self._done = False

        region = _normalize_region(init.region)
        self._region = region
        self._ctx = _HagglundContext(
            h100_m=init.h100_m,
            region=region,
            latitude=init.latitude,
            culture=init.use_culture_height,
            reproduce_fortran_errors=init.reproduce_fortran_errors,
        )
        _, stems, basal_area, site_index, t13 = estimate_initial_stand(init)
        self.site_index = site_index
        self._t13 = t13
        self._mc = _site_class_index_from_h100_dm(init.h100_m * 10.0)
        self._b = 64.0 if region == "north" else 57.0

        sag = None
        if init.final_bh_age is not None:
            sag = float(init.final_bh_age)
        elif init.final_total_age is not None:
            sag = float(init.final_total_age) - float(t13)
        if sag is not None and sag <= init.start_bh_age:
            raise ValueError("Final age must be greater than start_bh_age.")
        self._sag = sag

        if program is not None and program.interval_type == "dominant_height":
            final_age = sag if sag is not None else float("inf")
            program = _height_program_to_age(program, self._ctx, final_age)
            self.program = program

        t = float(init.start_bh_age)
        sn1 = float(stems)
        g1 = float(basal_area)
        d1 = _qmd_cm_from_basal_area_and_stems(g1, sn1)
        gu1 = convert_basal_area_over_to_under_bark(g1, t, d1, self._mc)
        du1 = _qmd_cm_from_basal_area_and_stems(gu1, sn1)

        self._state = _ErikssonState(t=t, sn1=sn1, g1=g1, gu1=gu1, du1=du1)

        if program is not None:
            if program.interval_type == "age":
                self._state.tmx = float(program.first_trigger)
                if self._state.tmx >= 1.0 and t >= self._state.tmx:
                    self._state.val = True
                    self._state.interval_idx = 0
                    self._state.outtake_idx = 0
                    self._state.gf_idx = 0
            else:
                self._state.gmx = float(program.first_trigger)
                if self._state.gmx >= 1.0 and g1 >= self._state.gmx:
                    self._state.val = True
                    self._state.interval_idx = 0
                    self._state.outtake_idx = 0
                    self._state.gf_idx = 0

    @property
    def done(self) -> bool:
        """Whether the simulator has reached a stopping condition."""
        return self._done

    @property
    def bh_age(self) -> float:
        """Current breast-height age."""
        return self._state.t

    @property
    def total_age(self) -> float:
        """Current total age including time to breast height."""
        return self._state.t + self._t13

    @property
    def stems_per_ha(self) -> float:
        """Current stem density per hectare."""
        return self._state.sn1

    @property
    def basal_area_m2_per_ha(self) -> float:
        """Current basal area (m²/ha) over bark."""
        return self._state.g1

    @property
    def dominant_height_m(self) -> float:
        """Current dominant height (m)."""
        return self._ctx.height_dm(self._state.t) * 0.1

    @property
    def qmd_cm(self) -> float:
        """Current quadratic mean diameter (cm)."""
        return _qmd_cm_from_basal_area_and_stems(self._state.g1, self._state.sn1)

    @property
    def volume_m3sk(self) -> float:
        """Current stand compute_stand_volume_m3sk (m³sk/ha)."""
        h_dm = self._ctx.height_dm(self._state.t)
        d1 = _qmd_cm_from_basal_area_and_stems(self._state.g1, self._state.sn1)
        return compute_stand_volume_m3sk(self._state.g1, h_dm, d1, self._mc)

    @property
    def last_row(self) -> Optional[Dict[str, Any]]:
        """Last output row produced by the simulator."""
        return self._last_row

    @property
    def track_history(self) -> bool:
        """Whether the stand records all output rows."""
        return self._track_history

    @property
    def self_thinning_summary(self) -> Dict[str, float]:
        """Summary of self-thinning removals accumulated to date."""
        return {
            "stems_per_ha": self._state.sn5,
            "basal_area_m2_per_ha": self._state.tmg,
            "volume_m3sk_per_ha": self._state.tmv,
        }

    def grow(
        self,
        years: float,
        *,
        thinning: Optional[ThinningRequest | Mapping[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Advance the stand by ``years`` with an optional thinning."""
        return self._advance(
            years=float(years),
            thinning=self._coerce_thinning(thinning),
            use_program=False,
        )

    def step(self) -> Optional[Dict[str, Any]]:
        """Advance the stand using scheduled thinning and step length."""
        if self.program is None:
            raise ValueError("ThinningProgram is required for scheduled simulation.")
        if self._sag is None:
            raise ValueError("Provide final_bh_age or final_total_age for scheduled simulation.")
        return self._advance(years=None, thinning=None, use_program=True)

    def run(self) -> "Eriksson1976Stand":
        """Run scheduled simulation until completion."""
        while not self._done:
            row = self.step()
            if row is None:
                break
        return self

    def _record_row(self, row: Dict[str, Any]) -> None:
        """Store the latest output row and append to history if enabled."""
        self._last_row = row
        if self._track_history:
            self.rows.append(row)

    def _coerce_thinning(
        self, thinning: Optional[ThinningRequest | Mapping[str, Any]]
    ) -> Optional[ThinningRequest]:
        """Normalize thinning inputs to a ``ThinningRequest``."""
        if thinning is None:
            return None
        if isinstance(thinning, ThinningRequest):
            return thinning
        outtake = float(thinning.get("outtake", 0.0))
        outtake_type = str(thinning.get("outtake_type", "percent")).lower()
        if outtake_type not in {"percent", "residual", "absolute"}:
            raise ValueError(f"Invalid outtake_type: {outtake_type}")
        diameter_factor = thinning.get("diameter_factor")
        if diameter_factor is not None:
            diameter_factor = float(diameter_factor)
        return ThinningRequest(
            outtake=outtake,
            outtake_type=outtake_type,
            diameter_factor=diameter_factor,
        )

    def _resolve_program_thinning(self) -> Optional[ThinningRequest]:
        """Build a thinning request from the program schedule state."""
        program = self.program
        state = self._state
        if program is None or not state.val:
            return None
        if not (0 <= state.outtake_idx < len(program.outtakes)):
            return None
        outtake = program.outtakes[state.outtake_idx]
        if outtake <= 0.0:
            return None
        diameter_factor = None
        if program.use_diameter_factors and program.diameter_factors:
            if 0 <= state.gf_idx < len(program.diameter_factors):
                diameter_factor = program.diameter_factors[state.gf_idx]
            else:
                diameter_factor = program.diameter_factors[-1]
        return ThinningRequest(
            outtake=outtake,
            outtake_type=program.outtake_type,
            diameter_factor=diameter_factor,
        )

    def _advance(
        self,
        *,
        years: Optional[float],
        thinning: Optional[ThinningRequest],
        use_program: bool,
    ) -> Optional[Dict[str, Any]]:
        """Execute a single growth step and return the output row."""
        if self._done:
            return None
        state = self._state
        program = self.program if use_program else None

        t = state.t
        sn1 = state.sn1
        g1 = state.g1
        gu1 = state.gu1
        du1 = state.du1
        p_prev = state.p

        h_dm = self._ctx.height_dm(t)
        d1 = _qmd_cm_from_basal_area_and_stems(g1, sn1)
        v1 = compute_stand_volume_m3sk(g1, h_dm, d1, self._mc)
        vu1 = compute_stand_volume_m3sk(gu1, h_dm, du1, self._mc)

        g3 = v3 = sn3 = 0.0
        gu3 = vu3 = 0.0
        du3 = 0.0
        g4 = v4 = sn4 = 0.0
        gu4 = vu4 = 0.0
        du4 = 0.0

        request = thinning or (self._resolve_program_thinning() if use_program else None)
        if request is not None and request.outtake > 0.0:
            if request.outtake_type == "percent":
                gu3 = gu1 * (request.outtake * 0.01)
            elif request.outtake_type == "residual":
                g3_over = max(0.0, g1 - request.outtake)
                pct = 100.0 * g3_over / g1 if g1 > 0.0 else 0.0
                gu3 = gu1 * (pct * 0.01)
            else:
                pct = 100.0 * request.outtake / g1 if g1 > 0.0 else 0.0
                gu3 = gu1 * (pct * 0.01)

            du3 = _thinning_qmd_under_bark_cm(
                du1, h_dm, program, state.gf_idx, request.diameter_factor
            )
            g3 = convert_thinning_basal_area_under_to_over_bark(gu3, t, du3, gu1, self._mc)
            sn3 = gu3 * 12732.4 / (du3 * du3) if du3 > 0.0 else 0.0
            if sn3 > sn1 + 50.0:
                raise ValueError("Invalid thinning form: removed stems exceed stand stems.")
            d3 = _qmd_cm_from_basal_area_and_stems(g3, sn3)
            v3 = compute_stand_volume_m3sk(g3, h_dm, d3, self._mc)
            vu3 = compute_stand_volume_m3sk(gu3, h_dm, du3, self._mc)

        if state.g22 != 0.0:
            n_eff = sn1
            if n_eff > 4500.0:
                n_eff = 4500.0 + 0.1 * (n_eff - 4500.0)
            c8 = C[self._mc - 1][7]
            c9 = C[self._mc - 1][8]
            # Mortality basal area uses the dominant height at the *start* of the elapsed
            # period. In the FORTRAN this is ``S(2)`` (the stored previous-row height), whereas
            # the diameter/volume of the dead trees below use the current height ``H``. Because
            # G4 scales as H**~3.3 and height grows fastest early, using the end-of-period
            # height here would front-load mortality and over-count (small) dead stems.
            h_dm_start = self._ctx.height_dm(t - p_prev) if p_prev > 0.0 else h_dm
            g4 = p_prev * (10 ** (-9.4888)) * ((n_eff * 0.001) ** c8) * (h_dm_start**c9)
            d4 = (10 ** (-1.411)) * (h_dm**0.517) * d1
            v4 = compute_stand_volume_m3sk(g4, h_dm, d4, self._mc)
            sn4 = g4 * 12732.4 / (d4 * d4) if d4 > 0.0 else 0.0
            gu4 = convert_basal_area_over_to_under_bark_with_reference(g4, t, d4, g1, self._mc)
            du4 = _qmd_cm_from_basal_area_and_stems(gu4, sn4)
            vu4 = compute_stand_volume_m3sk(gu4, h_dm, du4, self._mc)

            sn3 += sn4
            gu3 += gu4
            vu3 += vu4
            if gu3 > 0.1:
                du3 = _qmd_cm_from_basal_area_and_stems(gu3, sn3)
                g3 += g4
                v3 += v4
                state.sn5 += sn4
                state.tmg += g4
                state.tmv += v4

        sn2 = sn1 - sn3
        if sn2 < 50.0:
            self._done = True
            return None
        g2 = max(0.0, g1 - g3)
        gu2 = max(0.0, gu1 - gu3)
        d2 = _qmd_cm_from_basal_area_and_stems(g2, sn2)
        du2 = _qmd_cm_from_basal_area_and_stems(gu2, sn2)
        v2 = max(0.0, v1 - v3)
        vu2 = max(0.0, vu1 - vu3)

        if state.gu22 != 0.0 and p_prev > 0.0:
            z = (du1 - state.du22) * 5.0 / p_prev if p_prev > 0.0 else 0.0
            wz = compute_dry_weight_factor(z, self._b)
            w1 = state.w22 + wz * (vu1 - state.vu22)
            if request is not None and du3 > 0.0 and gu1 > 0.0:
                z = (du3 - (du3 * state.du22 / du1)) * 5.0 / p_prev if du1 > 0.0 else 0.0
                wz = compute_dry_weight_factor(z, self._b)
                w3 = wz * (vu3 - (gu3 * state.vu22 / gu1)) + state.w22 * 1.01 * gu3 / gu1
                w4 = 0.0
            else:
                w3 = 0.0
                if du4 >= 0.1 and gu1 > 0.0:
                    z = (du4 - (du4 * state.du22 / du1)) * 5.0 / p_prev if du1 > 0.0 else 0.0
                    wz = compute_dry_weight_factor(z, self._b)
                    w4 = wz * (vu4 - (gu4 * state.vu22 / gu1)) + state.w22 * 1.01 * gu4 / gu1
                else:
                    w4 = 0.0
            w2 = w1 - w3 - w4
        else:
            z = du1 * 5.0 / t if t > 0.0 else 0.0
            wz = compute_dry_weight_factor(z, self._b)
            w1 = wz * vu1
            if request is not None and du3 > 0.0 and t > 0.0:
                z = du3 * 5.0 / t
                wz = compute_dry_weight_factor(z, self._b)
                w3 = wz * vu3
            else:
                w3 = 0.0
            w4 = 0.0
            w2 = w1 - w3 - w4

        total_age = t + self._t13
        wtog = state.to_g2 - state.g22 + g1
        wtov = state.to_v2 - state.v22 + v1
        wtwd = state.tw12 - state.w22 + w1

        cai_g = (g1 - state.g22) / p_prev if state.g22 >= 0.1 and p_prev > 0.0 else 0.0
        cai_v = (v1 - state.v22) / p_prev if state.v22 >= 0.1 and p_prev > 0.0 else 0.0
        cai_w = (w1 - state.w22) / p_prev if state.w22 >= 0.1 and p_prev > 0.0 else 0.0

        mai_g = wtog / total_age if total_age > 0.0 else 0.0
        mai_v = wtov / total_age if total_age > 0.0 else 0.0
        mai_w = wtwd / total_age if total_age > 0.0 else 0.0

        d3 = _qmd_cm_from_basal_area_and_stems(g3, sn3) if g3 >= 0.05 else 0.0
        n_pct = int(100.0 * sn3 / sn1 + 0.5) if sn3 >= 0.5 and sn1 > 0.0 else 0
        v_pct = int(100.0 * v3 / v1 + 0.5) if v3 >= 0.5 and v1 > 0.0 else 0

        row = {
            "alder": {
                "T_AR": int(total_age + 0.5),
                "BRH_AR": int(t + 0.5),
                "HDOM_m": h_dm * 0.1,
            },
            "fore_gallring": {
                "DG_cm": d1,
                "N_st": sn1,
                "G_m2": g1,
                "V_m3sk": v1,
            },
            "kvarv_bestand": {"DG_cm": d2, "N_st": sn2, "G_m2": g2, "V_m3sk": v2},
            "gallring": {"DG_cm": d3, "N_st": sn3, "G_m2": g3, "V_m3sk": v3},
            "g_proc": {"N_pct": n_pct, "V_pct": v_pct},
            "total_prod": {"G_m2": wtog, "V_m3sk": wtov},
            "med_tillv": {"G_m2_per_yr": mai_g, "V_m3sk_per_yr": mai_v},
            "lop_tillv": {"G_m2_per_yr": cai_g, "V_m3sk_per_yr": cai_v},
            "torrsubprod": {"med_ton_per_yr": mai_w, "lop_ton_per_yr": cai_w},
        }
        self._record_row(row)

        state.to_g2 = wtog
        state.to_v2 = wtov
        state.tw12 = wtwd
        state.g22 = g2
        state.v22 = v2
        state.w22 = w2
        state.du22 = du2
        state.gu22 = gu2
        state.vu22 = vu2

        if self._sag is not None and t >= self._sag:
            self._done = True
            return row

        thinning_ub = max(0.0, gu3 - gu4)
        gz1 = state.gz1
        gp = state.gp
        gs2 = state.gs2
        if thinning_ub >= 0.1:
            gz1 = gu1
            gp = 100.0 * g3 / g1 + 0.01 if g1 > 0.0 else 0.01
            if sn3 < 1.0:
                gs2 = 1.0
            else:
                gs1 = math.sqrt((g3 * sn1) / (g1 * sn3) + 0.01)
                gs2 = gs1 * (100.0 * sn3 / sn1 + 0.01)
        else:
            program_trigger = program.first_trigger if program is not None else 0.0
            if gz1 < 1.0 or program_trigger < 1.0:
                gz1 = gu1
            if gp < 1.0 or program_trigger < 1.0:
                gp = 100.0 * g3 / g1 + 0.01 if g1 > 0.0 else 0.01
            if gs2 < 1.0 or program_trigger < 1.0:
                if sn3 < 1.0:
                    gs2 = 1.0
                else:
                    gs1 = math.sqrt((g3 * sn1) / (g1 * sn3) + 0.01)
                    gs2 = gs1 * (100.0 * sn3 / sn1 + 0.01)

        sn1 = sn2
        g1 = g2

        vs = (10**1.1392) * ((t * 0.1) ** C[self._mc - 1][13]) * ((sn1 * 0.001) ** (-0.052))
        vs = _apply_growth_scaling(vs, self.init)

        gz1 = max(0.01, gz1)
        gp = max(0.01, gp)
        gs2 = max(0.01, gs2)

        if years is not None:
            p_next = float(years)
        else:
            if program is None:
                raise ValueError("ThinningProgram required when years is not provided.")
            if self._sag is None:
                raise ValueError(
                    "Provide final_bh_age or final_total_age for scheduled simulation."
                )
            if program.interval_type == "age":
                p_next, tmx, val, interval_idx, outtake_idx, gf_idx = _schedule_age(
                    t,
                    self._sag,
                    state.tmx if state.tmx is not None else program.first_trigger,
                    state.val,
                    state.interval_idx,
                    state.outtake_idx,
                    state.gf_idx,
                    program.intervals,
                )
                state.tmx = tmx
            else:
                p_next, gmx, val, interval_idx, outtake_idx, gf_idx = _schedule_basal_area(
                    t,
                    self._sag,
                    state.gmx if state.gmx is not None else program.first_trigger,
                    g1,
                    state.val,
                    state.interval_idx,
                    state.outtake_idx,
                    state.gf_idx,
                    program.intervals,
                    program.outtakes,
                    gz1,
                    gp,
                    gs2,
                    h_dm,
                    gu2,
                    sn1,
                    self._mc,
                    vs,
                )
                state.gmx = gmx
            state.val = val
            state.interval_idx = interval_idx
            state.outtake_idx = outtake_idx
            state.gf_idx = gf_idx

        if p_next <= 0.0:
            self._done = True
            state.t = t
            state.sn1 = sn1
            state.g1 = g1
            state.gu1 = gu2
            state.du1 = du2
            state.p = p_next
            state.gz1 = gz1
            state.gp = gp
            state.gs2 = gs2
            state.vs = vs
            return row

        _, gu1, t, du1, g1 = project_growth_step(
            gz1,
            C[self._mc - 1][0],
            gp,
            C[self._mc - 1][1],
            gs2,
            p_next,
            C[self._mc - 1][2],
            h_dm,
            C[self._mc - 1][3],
            t,
            C[self._mc - 1][4],
            vs,
            C[self._mc - 1][5],
            gu2,
            sn1,
            self._mc,
        )

        state.t = t
        state.sn1 = sn1
        state.g1 = g1
        state.gu1 = gu1
        state.du1 = du1
        state.p = p_next
        state.gz1 = gz1
        state.gp = gp
        state.gs2 = gs2
        state.vs = vs
        return row


@dataclass(frozen=True)
class Eriksson1976ManagementSchedule:
    """Bridge ThinningProgram schedules into simulation triggers."""

    program: ThinningProgram
    state_prefix: str = "eriksson_1976_schedule"
    action_name: str = "schedule_thinning"

    def initialize(self, ctx: SimulationContext) -> None:
        """Seed schedule state keys in the simulation context."""
        ctx.state[self._key("outtake_idx")] = 0
        ctx.state[self._key("interval_idx")] = 0
        ctx.state[self._key("gf_idx")] = 0
        if self.program.interval_type == "basal_area":
            trigger = float(self.program.first_trigger)
            if trigger < 1.0:
                trigger = float("inf")
            ctx.state[self._key("ba_trigger")] = trigger

    def triggers(self) -> List[TriggerSpec]:
        """Return trigger specifications for the configured schedule."""
        if self.program.interval_type == "age":
            return self._age_triggers()
        if self.program.interval_type == "basal_area":
            return [self._basal_area_trigger()]
        raise NotImplementedError(
            "Eriksson1976ManagementSchedule does not support 'dominant_height' schedules; "
            "convert to an age schedule first (Eriksson1976Stand and simulate() accept "
            "dominant_height programs directly)."
        )

    def _key(self, name: str) -> str:
        """Build a namespaced state key."""
        return f"{self.state_prefix}_{name}"

    def _diameter_factor(self, idx: int) -> Optional[float]:
        """Return the diameter factor for a thinning index, if provided."""
        if not self.program.use_diameter_factors or not self.program.diameter_factors:
            return None
        if 0 <= idx < len(self.program.diameter_factors):
            return self.program.diameter_factors[idx]
        return self.program.diameter_factors[-1]

    def _age_events(self) -> List[Tuple[float, float, Optional[float]]]:
        """Expand age schedule inputs into thinning events."""
        events: List[Tuple[float, float, Optional[float]]] = []
        age = float(self.program.first_trigger)
        if age < 1.0:
            return events
        for idx, outtake in enumerate(self.program.outtakes):
            if outtake <= 0.0:
                break
            events.append((age, outtake, self._diameter_factor(idx)))
            interval = self.program.intervals[idx] if idx < len(self.program.intervals) else 0.0
            if interval < 1.0:
                break
            age += interval
        return events

    def _queue_thinning(
        self, ctx: SimulationContext, outtake: float, diameter_factor: Optional[float]
    ) -> None:
        """Queue a thinning action on the simulation context."""
        if outtake <= 0.0:
            return
        ctx.do(
            self.action_name,
            outtake=outtake,
            outtake_type=self.program.outtake_type,
            diameter_factor=diameter_factor,
        )

    def _age_triggers(self) -> List[TriggerSpec]:
        """Build age-based thinning triggers."""
        triggers: List[TriggerSpec] = []
        for idx, (age, outtake, diameter_factor) in enumerate(self._age_events()):
            name = f"eriksson_thin_age_{idx}_{int(age)}"

            def _predicate(ctx: SimulationContext, threshold=age) -> bool:
                """Return True when the age threshold is reached."""
                return float(ctx.state.get("t", 0.0)) >= threshold

            def _action(
                ctx: SimulationContext,
                outtake=outtake,
                factor=diameter_factor,
            ) -> None:
                """Queue the thinning corresponding to this age trigger."""
                self._queue_thinning(ctx, outtake, factor)

            triggers.append(
                TriggerSpec(
                    name=name,
                    check_phase="pre",
                    predicate=_predicate,
                    action=_action,
                    once=True,
                )
            )
        return triggers

    @staticmethod
    def _residual_ba(current_ba: float, outtake: float, outtake_type: str) -> float:
        """Estimate residual basal area after a thinning."""
        if outtake_type == "percent":
            return max(0.0, current_ba * (1.0 - outtake * 0.01))
        if outtake_type == "residual":
            return max(0.0, outtake)
        return max(0.0, current_ba - outtake)

    def _basal_area_trigger(self) -> TriggerSpec:
        """Build a basal-area trigger specification."""
        name = "eriksson_thin_ba"

        def _predicate(ctx: SimulationContext) -> bool:
            """Return True when basal area meets the trigger."""
            trigger = float(ctx.state.get(self._key("ba_trigger"), float("inf")))
            current_ba = float(ctx.metrics["BasalArea"]["TOTAL"])
            return current_ba >= trigger

        def _action(ctx: SimulationContext) -> None:
            """Queue a thinning and advance basal-area thresholds."""
            outtake_idx = int(ctx.state.get(self._key("outtake_idx"), 0))
            if outtake_idx >= len(self.program.outtakes):
                ctx.state[self._key("ba_trigger")] = float("inf")
                return
            outtake = float(self.program.outtakes[outtake_idx])
            if outtake <= 0.0:
                ctx.state[self._key("ba_trigger")] = float("inf")
                return
            interval_idx = int(ctx.state.get(self._key("interval_idx"), 0))
            gf_idx = int(ctx.state.get(self._key("gf_idx"), 0))
            self._queue_thinning(ctx, outtake, self._diameter_factor(gf_idx))
            ctx.state[self._key("outtake_idx")] = outtake_idx + 1
            ctx.state[self._key("interval_idx")] = interval_idx + 1
            ctx.state[self._key("gf_idx")] = gf_idx + 1

            interval = (
                self.program.intervals[interval_idx]
                if interval_idx < len(self.program.intervals)
                else 0.0
            )
            if interval < 1.0:
                ctx.state[self._key("ba_trigger")] = float("inf")
                return
            current_ba = float(ctx.metrics["BasalArea"]["TOTAL"])
            residual = self._residual_ba(current_ba, outtake, self.program.outtake_type)
            ctx.state[self._key("ba_trigger")] = residual + interval

        return TriggerSpec(
            name=name,
            check_phase="pre",
            predicate=_predicate,
            action=_action,
            once=False,
        )


class Eriksson1976Model(GrowthModel):
    """Simulation adapter for the Eriksson (1976) stand model."""

    def __init__(
        self,
        init: Optional[StandInit] = None,
        program: Optional[ThinningProgram] = None,
        *,
        track_history: bool = False,
    ) -> None:
        """Store default initialization and management settings."""
        self._default_init = init
        self._default_program = program
        self._track_history = track_history

    @property
    def component_id(self) -> str:
        """Stable identifier for the Eriksson 1976 stand model."""
        return "eriksson_1976"

    @property
    def source(self) -> SourceReference:
        """Bibliographic provenance for the Eriksson 1976 stand model."""
        return SourceReference(
            author="Eriksson, H.",
            year=1976,
            title="Granens produktion i Sverige",
            note=(
                "Skogshögskolan, institutionen för skogsproduktion, Rapporter och "
                "uppsatser nr 41, Stockholm, 291 s. Doctoral thesis."
            ),
        )

    def requirements(self) -> Requirements:
        """Declare aggregate inventory requirements."""
        return Requirements(inventory="aggregate")

    def build_context(
        self,
        stand: Stand,
        *,
        init: Optional[StandInit] = None,
        program: Optional[ThinningProgram] = None,
        track_history: Optional[bool] = None,
        **kwargs: Any,
    ) -> SimulationContext:
        """Build a simulation context with an attached Eriksson 1976 stand."""
        ctx = super().build_context(stand, **kwargs)
        resolved_init = self._resolve_init(stand, init)
        resolved_program = (
            program or stand.attrs.get("eriksson_1976_program") or self._default_program
        )
        history_flag = self._track_history if track_history is None else track_history
        stand_model = Eriksson1976Stand(
            resolved_init,
            program=resolved_program,
            track_history=history_flag,
        )
        ctx.attrs["eriksson_1976_stand"] = stand_model
        ctx.attrs["eriksson_1976_program"] = resolved_program
        ctx.state["t"] = stand_model.bh_age
        ctx.state["years_since_thin"] = 0.0
        ctx.set_aggregate_metrics(
            ba_total=stand_model.basal_area_m2_per_ha,
            stems_total=stand_model.stems_per_ha,
        )
        return ctx

    def update_step(self, ctx: SimulationContext, dt: float) -> None:
        """Advance the stand model and sync aggregate metrics."""
        stand_model = self._stand_from_ctx(ctx)
        thinning = ctx.state.pop("eriksson_1976_pending_thinning", None)
        thinning_req = stand_model._coerce_thinning(thinning)
        row = stand_model.grow(years=dt, thinning=thinning_req)
        if row is not None:
            ctx.attrs["eriksson_1976_last_row"] = row
            if stand_model.track_history:
                ctx.attrs["eriksson_1976_rows"] = list(stand_model.rows)
        ctx.set_aggregate_metrics(
            ba_total=stand_model.basal_area_m2_per_ha,
            stems_total=stand_model.stems_per_ha,
        )
        if thinning_req is not None:
            ctx.state["years_since_thin"] = 0.0
        else:
            ctx.state["years_since_thin"] = ctx.state.get("years_since_thin", 0.0) + dt

    def available_actions(self) -> Dict[str, ActionSpec]:
        """Expose simulation actions supported by the model."""
        return {
            "schedule_thinning": ActionSpec(
                name="schedule_thinning",
                description="Queue a thinning for the next growth step.",
                fn=self._act_schedule_thinning,
                params={
                    "outtake": "float",
                    "outtake_type": "percent|residual|absolute",
                    "diameter_factor": "optional float",
                },
                requires_modes=["aggregate"],
            )
        }

    def _act_schedule_thinning(
        self,
        ctx: SimulationContext,
        *,
        outtake: float,
        outtake_type: str = "percent",
        diameter_factor: Optional[float] = None,
    ) -> None:
        """Store a pending thinning request for the next step."""
        normalized = str(outtake_type).lower()
        if normalized not in {"percent", "residual", "absolute"}:
            raise ValueError("outtake_type must be percent, residual, or absolute.")
        ctx.state["eriksson_1976_pending_thinning"] = {
            "outtake": float(outtake),
            "outtake_type": normalized,
            "diameter_factor": diameter_factor,
        }

    def _resolve_init(self, stand: Stand, init: Optional[StandInit]) -> StandInit:
        """Resolve StandInit values from defaults and stand metrics."""
        resolved = init or stand.attrs.get("eriksson_1976_init") or self._default_init
        if resolved is None:
            raise ValueError("Eriksson1976Model requires a StandInit.")
        stems = resolved.stems
        basal_area = resolved.basal_area
        if stems is None:
            stems = float(stand.Stems)
        if basal_area is None:
            basal_area = float(stand.BasalArea)
        latitude = resolved.latitude
        altitude_m = resolved.altitude_m
        site = stand.site
        if latitude is None and site is not None:
            lat = getattr(site, "latitude", None)
            if lat is not None:
                latitude = float(lat)
        if altitude_m == 0.0 and site is not None:
            alt = getattr(site, "altitude", None)
            if alt is None:
                alt = getattr(site, "altitude_m", None)
            if alt is not None:
                altitude_m = float(alt)
        return replace(
            resolved,
            stems=stems,
            basal_area=basal_area,
            latitude=latitude,
            altitude_m=altitude_m,
        )

    @staticmethod
    def _stand_from_ctx(ctx: SimulationContext) -> Eriksson1976Stand:
        """Return the bound Eriksson stand model from a context."""
        stand_model = ctx.attrs.get("eriksson_1976_stand")
        if not isinstance(stand_model, Eriksson1976Stand):
            raise ValueError("Eriksson1976Model context missing stand model.")
        return stand_model


def simulate(init: StandInit, program: ThinningProgram) -> SimulationResult:
    """Run the Eriksson (1976) simulation."""
    stand = Eriksson1976Stand(init, program=program, track_history=True).run()
    return SimulationResult(
        rows=stand.rows,
        self_thinning_summary=stand.self_thinning_summary,
    )


DESCRIPTOR = FormulaDescriptor(
    component_id="eriksson_1976_model",
    source=SourceReference(
        author="Eriksson, H.",
        year=1976,
        title="Granens produktion i Sverige",
        note=(
            "Skogshögskolan, institutionen för skogsproduktion, Rapporter och "
            "uppsatser nr 41, Stockholm, 291 s. Doctoral thesis."
        ),
    ),
    kind="model",
    domain="growth",
    composes=(),
    kernel_names=("Eriksson1976Model",),
)
