"""Persson (1992) Scots Pine production model.

This port implements a stand-level growth simulator for Scots Pine
(*Pinus sylvestris* L.) in Sweden, based on:

    Persson, O. A. (1992). *En produktionsmodell för tallskog i Sverige*
    (A growth simulator for Scots Pine in Sweden). Report No. 31,
    Dept. of Forest Yield Research, Swedish University of Agricultural
    Sciences, Garpenberg. ISSN 0348-7636.

The primary driving function is a basal-area increment function
(Function 2, p. 56).  Supporting regressions cover standing volume,
bark area, annual natural mortality in basal area, and the diameter
ratio of self-thinned stems.  Height growth is estimated with Hägglund
(1974) site-index curves via :mod:`pyforestry.sweden.siteindex.hagglund_1970`.
Initial stem count and basal area, when not supplied, are estimated with
Elfving & Hägglund (1975).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Literal, Mapping, Optional, Sequence, Tuple

from pyforestry.base.contracts import FormulaDescriptor
from pyforestry.base.helpers import Age, SiteIndexValue, Stand, Stems
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.base.simulation import (
    ActionSpec,
    GrowthModel,
    Requirements,
    SimulationContext,
)
from pyforestry.simulation.contracts import SourceReference
from pyforestry.sweden.blocks.elfving_hagglund_1975 import ElfvingHagglundInitialStand
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970

__all__ = [
    "PerssonStandInit",
    "PerssonThinningProgram",
    "PerssonThinningRequest",
    "PerssonSimulationResult",
    "Persson1992Stand",
    "Persson1992Model",
    "persson_estimate_initial_stand",
    "persson_simulate",
]


# ═══════════════════════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class PerssonStandInit:
    """Initial stand and site specification for the Persson (1992) model."""

    h100_m: float
    start_bh_age: float
    latitude: float = 64.0
    altitude_m: float = 0.0
    final_bh_age: Optional[float] = None
    final_total_age: Optional[float] = None
    stems: Optional[float] = None
    basal_area: Optional[float] = None
    stand_density_factor: float = 0.65
    broadleaves_percent_ba: float = 0.0
    even_aged: bool = True
    pct: bool = False
    regeneration: Literal["culture", "natural", "unknown"] = "culture"


@dataclass(frozen=True)
class PerssonThinningProgram:
    """Thinning program for Persson (1992)."""

    interval_type: Literal["age", "basal_area"]
    first_trigger: float
    intervals: Sequence[float] = field(default_factory=list)
    outtake_type: Literal["percent", "residual", "absolute"] = "percent"
    outtakes: Sequence[float] = field(default_factory=list)
    diameter_factors: Sequence[float] = field(default_factory=list)
    use_diameter_factors: bool = False


@dataclass(frozen=True)
class PerssonThinningRequest:
    """Explicit thinning request for a single growth step."""

    outtake: float
    outtake_type: Literal["percent", "residual", "absolute"] = "percent"
    diameter_factor: Optional[float] = None


@dataclass(frozen=True)
class PerssonSimulationResult:
    """Simulation outputs for Persson (1992)."""

    rows: List[Dict[str, Any]]
    self_thinning_summary: Dict[str, float]


# ═══════════════════════════════════════════════════════════════════════════════
# Internal mutable state
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class _PerssonState:
    """Mutable internal state for the Persson 1992 simulator."""

    t: float  # current breast-height age
    sn1: float  # current stems/ha
    ba_ob: float  # basal area over bark, m²/ha
    ba_ub: float  # basal area under bark, m²/ha
    p: float = 0.0  # previous growth period length

    # Previous-period remaining-stand values (for CAI and mortality)
    ba_ob_prev: float = 0.0
    vol_prev: float = 0.0
    thinned_prev: bool = False

    # Cumulative totals
    cum_ba_ob: float = 0.0  # total BA production (over bark)
    cum_vol: float = 0.0  # total volume production

    # Self-thinning accumulators
    mort_stems: float = 0.0
    mort_ba: float = 0.0
    mort_vol: float = 0.0

    # Scheduling indices
    val: bool = False
    interval_idx: int = -1
    outtake_idx: int = -1
    gf_idx: int = -1
    tmx: Optional[float] = None
    gmx: Optional[float] = None


# ═══════════════════════════════════════════════════════════════════════════════
# Core regression functions – Persson (1992)
# ═══════════════════════════════════════════════════════════════════════════════


def _ln(x: float) -> float:
    if x <= 0.0:
        raise ValueError(f"log() argument must be > 0, got {x}")
    return math.log(x)


def _qmd_cm(ba: float, stems: float) -> float:
    """Quadratic mean diameter (cm) from basal area (m²/ha) and stems/ha."""
    if ba <= 0.0 or stems <= 0.0:
        return 0.0
    return math.sqrt(40000.0 * ba / (math.pi * stems))


def ba_increment_annual_ub(
    ba_ub_after_thinning: float,
    age_bh: float,
    h100: float,
    latitude: float,
) -> float:
    """Annual basal-area increment under bark (m²/ha/yr).

    Persson (1992), Function 2, p. 56.
    """
    return math.exp(
        4.90697
        + 0.44683 * _ln(ba_ub_after_thinning)
        - 0.63272 * _ln(age_bh)
        + 0.30834 * _ln(h100)
        - 1.32323 * _ln(latitude)
    )


def bark_area(
    ba_ob: float,
    h100: float,
    stems: float,
    latitude: float,
) -> float:
    """Bark area (m²/ha).  Persson (1992), p. 58."""
    return math.exp(
        8.43648
        + 0.94902 * _ln(ba_ob)
        - 0.176223 * _ln(h100)
        + 0.037108 * _ln(stems)
        - 2.30456 * _ln(latitude)
    )


def volume_m3sk(
    ba_ob: float,
    hdom_m: float,
    stems: float,
    latitude: float,
) -> float:
    """Standing volume over bark, m³sk/ha.  Persson (1992), p. 58."""
    if ba_ob <= 0.0 or hdom_m <= 0.0 or stems <= 0.0:
        return 0.0
    return math.exp(
        -0.58147
        + 1.11493 * _ln(ba_ob)
        + 0.73376 * _ln(hdom_m)
        - 0.072569 * _ln(stems)
        + 0.160919 * _ln(latitude)
    )


def average_basal_area(h100: float, hdom_m: float) -> float:
    """Average basal area in pine stands (m²/ha).  Persson (1992), p. 59."""
    return math.exp(-0.150317 + 0.50463 * _ln(hdom_m) + 0.62033 * _ln(h100))


def natural_mortality_ba_annual(
    ba_ob: float,
    hdom_m: float,
    h100: float,
    stems: float,
    latitude: float,
) -> float:
    """Annual natural mortality as basal area over bark (m²/ha/yr).

    Persson (1992), p. 60.  The regression predicts ln(mortality + 0.01);
    the returned value has the 0.01 bias removed.
    """
    avg_ba_threshold = 1.3 * average_basal_area(h100, hdom_m)

    if ba_ob >= avg_ba_threshold:
        raw = math.exp(
            -17.24908 + 1.86053 * _ln(ba_ob) + 1.75182 * _ln(hdom_m) + 0.44001 * _ln(stems)
        )
    else:
        raw = math.exp(
            15.33590 + 1.01872 * _ln(hdom_m) + 0.69317 * _ln(stems) - 6.38718 * _ln(latitude)
        )
    return max(0.0, raw - 0.01)


def mortality_diameter_ratio(
    hdom_m: float,
    stems: float,
    thinned: bool,
) -> float:
    """QMD ratio (dead / remaining).  Persson (1992), p. 61."""
    t = 1.0 if thinned else 0.0
    return math.exp(-1.06123 + 0.38727 * _ln(hdom_m) - 0.080630 * _ln(stems) + 0.140766 * t)


# ═══════════════════════════════════════════════════════════════════════════════
# Bark conversion helpers
# ═══════════════════════════════════════════════════════════════════════════════


def ba_ob_to_ub(ba_ob: float, h100: float, stems: float, latitude: float) -> float:
    """Convert basal area over bark to under bark."""
    if ba_ob <= 0.0 or stems <= 0.0:
        return 0.0
    ba = bark_area(ba_ob, h100, stems, latitude)
    return max(0.0, ba_ob - ba)


def ba_ub_to_ob(ba_ub: float, h100: float, stems: float, latitude: float) -> float:
    """Convert basal area under bark to over bark (fixed-point iteration)."""
    if ba_ub <= 0.0 or stems <= 0.0:
        return 0.0
    ba_ob = ba_ub * 1.15  # initial guess: ~15% bark
    for _ in range(20):
        ba = bark_area(ba_ob, h100, stems, latitude)
        ba_ob_new = ba_ub + ba
        if abs(ba_ob_new - ba_ob) < 1e-6:
            break
        ba_ob = ba_ob_new
    return ba_ob


# ═══════════════════════════════════════════════════════════════════════════════
# Thinning helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _thinning_qmd_factor(age_bh: float, removal_ba_pct: float) -> float:
    """Ratio of removed-tree QMD to stand QMD.

    Determines thinning form (from-below / neutral).  Returns a factor < 1
    for thinning from below (smaller trees removed).
    """
    if removal_ba_pct > 50.0:
        return 0.90
    if age_bh >= 35.0:
        return 0.90
    if age_bh >= 25.0:
        return 0.88
    return 0.80


# ═══════════════════════════════════════════════════════════════════════════════
# Height-trajectory context (wraps Hägglund 1974 pine)
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class _PineHeightContext:
    """Wrap Hägglund (1974) Scots Pine site-index and height functions."""

    h100_m: float
    regeneration: Literal["culture", "natural", "unknown"]

    def _regen_enum(self):
        """Map string to enum."""
        mapping = {
            "culture": Hagglund_1970.regeneration.CULTURE,
            "natural": Hagglund_1970.regeneration.NATURAL,
            "unknown": Hagglund_1970.regeneration.UNKNOWN,
        }
        return mapping[self.regeneration]

    def site_index_value(self) -> SiteIndexValue:
        """Return the SiteIndexValue for H100."""
        return Hagglund_1970.height_trajectory.pinus_sylvestris.sweden(
            dominant_height_m=self.h100_m,
            age=Age.TOTAL(100),
            age2=Age.TOTAL(100),
            regeneration=self._regen_enum(),
        )

    def time_to_breast_height(self) -> float:
        """Return T13 (years to breast height)."""
        return Hagglund_1970.time_to_breast_height.pinus_sylvestris.sweden(
            dominant_height_m=self.h100_m,
            age=Age.TOTAL(100),
            age2=Age.TOTAL(100),
            regeneration=self._regen_enum(),
        )

    def height_m(self, bh_age: float) -> float:
        """Return dominant height (m) at a breast-height age."""
        si = Hagglund_1970.height_trajectory.pinus_sylvestris.sweden(
            dominant_height_m=self.h100_m,
            age=Age.TOTAL(100),
            age2=Age.DBH(bh_age),
            regeneration=self._regen_enum(),
        )
        return float(si)


# ═══════════════════════════════════════════════════════════════════════════════
# Initial-stand estimation
# ═══════════════════════════════════════════════════════════════════════════════


def persson_estimate_initial_stand(
    init: PerssonStandInit,
) -> Tuple[float, float, float, SiteIndexValue, float]:
    """Compute dominant height, stems, basal area, site index, and T13.

    Returns:
        (hdom_m, stems, basal_area_ob, site_index, t13)
    """
    ctx = _PineHeightContext(h100_m=init.h100_m, regeneration=init.regeneration)
    site_index = ctx.site_index_value()
    t13 = ctx.time_to_breast_height()
    hdom_m = ctx.height_m(init.start_bh_age)

    stems_value = init.stems
    basal_area_value = init.basal_area
    age_bh = Age.DBH(float(init.start_bh_age))
    lat = float(init.latitude)
    alt = float(init.altitude_m)
    northern = lat >= 60.0

    if stems_value is None and basal_area_value is None:
        if northern:
            stems_obj = ElfvingHagglundInitialStand.estimate_stems_young_pine_north(
                latitude=lat,
                altitude=alt,
                dominant_height=float(hdom_m),
                stand_density_factor=init.stand_density_factor,
                pct=init.pct,
                even_or_somewhat_uneven_aged=init.even_aged,
            )
            ba_obj = ElfvingHagglundInitialStand.estimate_basal_area_young_pine_north(
                latitude=lat,
                altitude=alt,
                site_index=site_index,
                dominant_height=float(hdom_m),
                stems=stems_obj,
                stand_density_factor=init.stand_density_factor,
                broadleaves_percent_ba=init.broadleaves_percent_ba,
                pct=init.pct,
                even_or_somewhat_uneven_aged=init.even_aged,
            )
        else:
            stems_obj = ElfvingHagglundInitialStand.estimate_stems_young_pine_south(
                latitude=lat,
                site_index=site_index,
                dominant_height=float(hdom_m),
                age_at_breast_height=age_bh,
                stand_density_factor=init.stand_density_factor,
                pct=init.pct,
                regeneration=init.regeneration,
            )
            ba_obj = ElfvingHagglundInitialStand.estimate_basal_area_young_pine_south(
                latitude=lat,
                altitude=alt,
                site_index=site_index,
                dominant_height=float(hdom_m),
                stems=stems_obj,
                age_at_breast_height=age_bh,
                stand_density_factor=init.stand_density_factor,
                pct=init.pct,
                regeneration=init.regeneration,
            )
        stems_value = float(stems_obj)
        basal_area_value = float(ba_obj)
    elif stems_value is None:
        if northern:
            stems_obj = ElfvingHagglundInitialStand.estimate_stems_young_pine_north(
                latitude=lat,
                altitude=alt,
                dominant_height=float(hdom_m),
                stand_density_factor=init.stand_density_factor,
                pct=init.pct,
                even_or_somewhat_uneven_aged=init.even_aged,
            )
        else:
            stems_obj = ElfvingHagglundInitialStand.estimate_stems_young_pine_south(
                latitude=lat,
                site_index=site_index,
                dominant_height=float(hdom_m),
                age_at_breast_height=age_bh,
                stand_density_factor=init.stand_density_factor,
                pct=init.pct,
                regeneration=init.regeneration,
            )
        stems_value = float(stems_obj)
    elif basal_area_value is None:
        stems_obj = Stems(value=float(stems_value), species=TreeSpecies.Sweden.pinus_sylvestris)
        if northern:
            ba_obj = ElfvingHagglundInitialStand.estimate_basal_area_young_pine_north(
                latitude=lat,
                altitude=alt,
                site_index=site_index,
                dominant_height=float(hdom_m),
                stems=stems_obj,
                stand_density_factor=init.stand_density_factor,
                broadleaves_percent_ba=init.broadleaves_percent_ba,
                pct=init.pct,
                even_or_somewhat_uneven_aged=init.even_aged,
            )
        else:
            ba_obj = ElfvingHagglundInitialStand.estimate_basal_area_young_pine_south(
                latitude=lat,
                altitude=alt,
                site_index=site_index,
                dominant_height=float(hdom_m),
                stems=stems_obj,
                age_at_breast_height=age_bh,
                stand_density_factor=init.stand_density_factor,
                pct=init.pct,
                regeneration=init.regeneration,
            )
        basal_area_value = float(ba_obj)

    if stems_value is None or basal_area_value is None:
        raise ValueError("Initial stems and basal area could not be resolved.")

    return float(hdom_m), float(stems_value), float(basal_area_value), site_index, float(t13)


# ═══════════════════════════════════════════════════════════════════════════════
# Scheduling helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _base_period(h100: float) -> float:
    """Base growth-period length (years), ceil(200 / SI)."""
    p = math.ceil(200.0 / h100)
    return max(3.0, min(p, 10.0))


def _schedule_age(
    t: float,
    sag: float,
    tmx: float,
    val: bool,
    interval_idx: int,
    outtake_idx: int,
    gf_idx: int,
    intervals: Sequence[float],
    outtakes: Sequence[float],
    h100: float,
) -> Tuple[float, float, bool, int, int, int]:
    """Compute next step length for age-based scheduling."""
    p_base = _base_period(h100)
    if val:
        interval = intervals[interval_idx] if 0 <= interval_idx < len(intervals) else 0.0
        if interval >= 1.0:
            tmx = t + interval
        else:
            tmx = sag + 10.0
        val = False

    remaining = sag - t
    px = tmx - t

    if 1.0 <= px <= p_base:
        val = True
        interval_idx += 1
        outtake_idx += 1
        gf_idx += 1
        if outtake_idx >= len(outtakes) or outtakes[outtake_idx] <= 0.0:
            val = False
        return px, tmx, val, interval_idx, outtake_idx, gf_idx

    if remaining <= p_base:
        return max(1.0, remaining), tmx, val, interval_idx, outtake_idx, gf_idx
    if remaining <= 2.0 * p_base:
        return p_base, tmx, val, interval_idx, outtake_idx, gf_idx

    if p_base < px <= 2.0 * p_base:
        return p_base, tmx, val, interval_idx, outtake_idx, gf_idx

    return p_base, tmx, val, interval_idx, outtake_idx, gf_idx


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
    ba_ub: float,
    h100: float,
    latitude: float,
    stems: float,
) -> Tuple[float, float, bool, int, int, int]:
    """Compute next step length for basal-area scheduling."""
    p_base = _base_period(h100)

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

    remaining = sag - t
    if remaining <= p_base:
        return max(1.0, remaining), gmx, False, interval_idx, outtake_idx, gf_idx
    if remaining <= 2.0 * p_base:
        return max(1.0, math.floor(remaining * 0.5)), gmx, False, interval_idx, outtake_idx, gf_idx

    if math.isinf(gmx):
        return p_base, gmx, False, interval_idx, outtake_idx, gf_idx

    # Project forward to find when BA reaches trigger
    annual_ig = ba_increment_annual_ub(max(0.01, ba_ub), max(1.0, t), h100, latitude)
    ba_ub_proj = ba_ub + annual_ig * p_base
    ba_ob_proj = ba_ub_to_ob(ba_ub_proj, h100, stems, latitude)

    if ba_ob_proj >= gmx:
        # Will reach trigger within base period – find the year
        best_p = p_base
        for p_try in range(1, int(p_base)):
            ba_ub_try = ba_ub + annual_ig * p_try
            ba_ob_try = ba_ub_to_ob(ba_ub_try, h100, stems, latitude)
            if ba_ob_try >= gmx:
                best_p = float(p_try)
                break
        val = True
        interval_idx += 1
        outtake_idx += 1
        gf_idx += 1
        if outtake_idx >= len(outtakes) or outtakes[outtake_idx] <= 0.0:
            val = False
        return best_p, gmx, val, interval_idx, outtake_idx, gf_idx

    return p_base, gmx, False, interval_idx, outtake_idx, gf_idx


# ═══════════════════════════════════════════════════════════════════════════════
# Stand simulator
# ═══════════════════════════════════════════════════════════════════════════════


class Persson1992Stand:
    """Stateful stand simulator for Persson (1992) Scots Pine."""

    def __init__(
        self,
        init: PerssonStandInit,
        program: Optional[PerssonThinningProgram] = None,
        *,
        track_history: bool = False,
    ) -> None:
        self.init = init
        self.program = program
        self._track_history = track_history
        self.rows: List[Dict[str, Any]] = []
        self._last_row: Optional[Dict[str, Any]] = None
        self._done = False

        self._ctx = _PineHeightContext(h100_m=init.h100_m, regeneration=init.regeneration)
        hdom_m, stems, basal_area_ob, site_index, t13 = persson_estimate_initial_stand(init)
        self.site_index = site_index
        self._t13 = t13
        self._h100 = init.h100_m
        self._lat = init.latitude

        sag = None
        if init.final_bh_age is not None:
            sag = float(init.final_bh_age)
        elif init.final_total_age is not None:
            sag = float(init.final_total_age) - t13
        if sag is not None and sag <= init.start_bh_age:
            raise ValueError("Final age must be greater than start_bh_age.")
        self._sag = sag

        t = float(init.start_bh_age)
        sn1 = float(stems)
        ba_ob = float(basal_area_ob)
        ba_ub = ba_ob_to_ub(ba_ob, self._h100, sn1, self._lat)

        self._state = _PerssonState(t=t, sn1=sn1, ba_ob=ba_ob, ba_ub=ba_ub)

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
                if self._state.gmx >= 1.0 and ba_ob >= self._state.gmx:
                    self._state.val = True
                    self._state.interval_idx = 0
                    self._state.outtake_idx = 0
                    self._state.gf_idx = 0

    # ─── Properties ───────────────────────────────────────────────────────

    @property
    def done(self) -> bool:
        return self._done

    @property
    def bh_age(self) -> float:
        return self._state.t

    @property
    def total_age(self) -> float:
        return self._state.t + self._t13

    @property
    def stems_per_ha(self) -> float:
        return self._state.sn1

    @property
    def basal_area_m2_per_ha(self) -> float:
        return self._state.ba_ob

    @property
    def dominant_height_m(self) -> float:
        return self._ctx.height_m(self._state.t)

    @property
    def qmd_cm(self) -> float:
        return _qmd_cm(self._state.ba_ob, self._state.sn1)

    @property
    def volume_m3sk(self) -> float:
        return volume_m3sk(
            self._state.ba_ob,
            self._ctx.height_m(self._state.t),
            self._state.sn1,
            self._lat,
        )

    @property
    def last_row(self) -> Optional[Dict[str, Any]]:
        return self._last_row

    @property
    def track_history(self) -> bool:
        return self._track_history

    @property
    def self_thinning_summary(self) -> Dict[str, float]:
        return {
            "stems_per_ha": self._state.mort_stems,
            "basal_area_m2_per_ha": self._state.mort_ba,
            "volume_m3sk_per_ha": self._state.mort_vol,
        }

    # ─── Public interface ─────────────────────────────────────────────────

    def grow(
        self,
        years: float,
        *,
        thinning: Optional[PerssonThinningRequest | Mapping[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Advance the stand by *years* with an optional thinning."""
        return self._advance(
            years=float(years),
            thinning=self._coerce_thinning(thinning),
            use_program=False,
        )

    def step(self) -> Optional[Dict[str, Any]]:
        """Advance the stand using the scheduled thinning program."""
        if self.program is None:
            raise ValueError("PerssonThinningProgram is required for scheduled simulation.")
        if self._sag is None:
            raise ValueError("Provide final_bh_age or final_total_age for scheduled simulation.")
        return self._advance(years=None, thinning=None, use_program=True)

    def run(self) -> "Persson1992Stand":
        """Run scheduled simulation until completion."""
        while not self._done:
            row = self.step()
            if row is None:
                break
        return self

    # ─── Internal helpers ─────────────────────────────────────────────────

    def _record_row(self, row: Dict[str, Any]) -> None:
        self._last_row = row
        if self._track_history:
            self.rows.append(row)

    def _coerce_thinning(
        self, thinning: Optional[PerssonThinningRequest | Mapping[str, Any]]
    ) -> Optional[PerssonThinningRequest]:
        if thinning is None:
            return None
        if isinstance(thinning, PerssonThinningRequest):
            return thinning
        outtake = float(thinning.get("outtake", 0.0))
        outtake_type = str(thinning.get("outtake_type", "percent")).lower()
        if outtake_type not in {"percent", "residual", "absolute"}:
            raise ValueError(f"Invalid outtake_type: {outtake_type}")
        diameter_factor = thinning.get("diameter_factor")
        if diameter_factor is not None:
            diameter_factor = float(diameter_factor)
        return PerssonThinningRequest(
            outtake=outtake,
            outtake_type=outtake_type,
            diameter_factor=diameter_factor,
        )

    def _resolve_program_thinning(self) -> Optional[PerssonThinningRequest]:
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
        return PerssonThinningRequest(
            outtake=outtake,
            outtake_type=program.outtake_type,
            diameter_factor=diameter_factor,
        )

    # ─── Core growth step ─────────────────────────────────────────────────

    def _advance(
        self,
        *,
        years: Optional[float],
        thinning: Optional[PerssonThinningRequest],
        use_program: bool,
    ) -> Optional[Dict[str, Any]]:
        if self._done:
            return None
        state = self._state
        program = self.program if use_program else None
        h100 = self._h100
        lat = self._lat

        t = state.t
        sn1 = state.sn1
        ba_ob = state.ba_ob
        p_prev = state.p

        hdom_m = self._ctx.height_m(t)
        d1 = _qmd_cm(ba_ob, sn1)
        v1 = volume_m3sk(ba_ob, hdom_m, sn1, lat)

        # ── Self-thinning for the previous growth period ─────────────────
        # Persson (1992) Table 13: mortality is evaluated using the
        # end-of-period state (current Fore).  It is always accumulated
        # to the running self-thinning total.  For NON-THINNING rows the
        # mortality also appears in the Gallring column and is subtracted
        # from the stand.  For THINNING rows only the scheduled removal
        # is shown and subtracted; the self-thinning is a hidden
        # accounting entry (consistent with the published yield tables).
        mort_ba = mort_vol = mort_stems = 0.0
        d_mort = 0.0
        if p_prev > 0.0 and sn1 > 50.0 and ba_ob > 0.1:
            annual_mort = natural_mortality_ba_annual(ba_ob, hdom_m, h100, sn1, lat)
            mort_ba = max(0.0, annual_mort * p_prev)
            mort_ba = min(mort_ba, ba_ob * 0.5)
            if mort_ba > 0.01:
                ratio = mortality_diameter_ratio(hdom_m, sn1, state.thinned_prev)
                d_mort = max(0.1, ratio * d1)
                mort_stems = 40000.0 * mort_ba / (math.pi * d_mort * d_mort)
                mort_vol = volume_m3sk(mort_ba, hdom_m, mort_stems, lat)

        state.mort_stems += mort_stems
        state.mort_ba += mort_ba
        state.mort_vol += mort_vol

        # ── Determine thinning ───────────────────────────────────────────
        request = thinning or (self._resolve_program_thinning() if use_program else None)
        thinned_now = request is not None and request.outtake > 0.0

        g3 = v3 = sn3 = d3 = 0.0
        if thinned_now:
            # Thinning row: Gallring = scheduled removal only
            if request.outtake_type == "percent":
                g3 = ba_ob * (request.outtake * 0.01)
            elif request.outtake_type == "residual":
                g3 = max(0.0, ba_ob - request.outtake)
            else:
                g3 = min(request.outtake, ba_ob)

            removal_pct = 100.0 * g3 / ba_ob if ba_ob > 0.0 else 0.0
            if request.diameter_factor is not None:
                d3 = d1 * request.diameter_factor
            else:
                d3 = d1 * _thinning_qmd_factor(t, removal_pct)
            sn3 = 40000.0 * g3 / (math.pi * d3 * d3) if d3 > 0.0 else 0.0
            if sn3 > sn1:
                sn3 = sn1
                d3 = _qmd_cm(g3, sn3)
            v3 = volume_m3sk(g3, hdom_m, sn3, lat)
        elif mort_ba > 0.01:
            # Non-thinning row: Gallring = self-thinning
            g3 = mort_ba
            d3 = d_mort
            sn3 = mort_stems
            v3 = mort_vol

        # ── Remaining stand ──────────────────────────────────────────────
        sn2 = sn1 - sn3
        if sn2 < 50.0:
            self._done = True
            return None
        ba_ob_2 = max(0.0, ba_ob - g3)
        d2 = _qmd_cm(ba_ob_2, sn2)
        v2 = volume_m3sk(ba_ob_2, hdom_m, sn2, lat) if ba_ob_2 > 0.0 else 0.0

        # ── Cumulative production and increments ─────────────────────────
        gallring_ba = g3
        gallring_vol = v3

        total_age = t + self._t13
        if state.ba_ob_prev > 0.0:
            ba_growth = ba_ob - state.ba_ob_prev
            vol_growth = v1 - state.vol_prev
            cum_ba = state.cum_ba_ob + ba_growth + gallring_ba
            cum_vol = state.cum_vol + vol_growth + gallring_vol
        else:
            cum_ba = ba_ob
            cum_vol = v1

        mai_g = cum_ba / total_age if total_age > 0.0 else 0.0
        mai_v = cum_vol / total_age if total_age > 0.0 else 0.0

        if state.ba_ob_prev > 0.0 and p_prev > 0.0:
            cai_g = (ba_ob - state.ba_ob_prev + gallring_ba) / p_prev
            cai_v = (v1 - state.vol_prev + gallring_vol) / p_prev
        else:
            cai_g = cai_v = 0.0

        n_pct = int(100.0 * sn3 / sn1 + 0.5) if sn3 >= 0.5 and sn1 > 0.0 else 0
        v_pct = int(100.0 * v3 / v1 + 0.5) if v3 >= 0.5 and v1 > 0.0 else 0

        row = {
            "alder": {
                "T_AR": int(total_age + 0.5),
                "BRH_AR": int(t + 0.5),
                "HDOM_m": round(hdom_m, 1),
            },
            "fore_gallring": {
                "DG_cm": d1,
                "N_st": sn1,
                "G_m2": ba_ob,
                "V_m3sk": v1,
            },
            "kvarv_bestand": {
                "DG_cm": d2,
                "N_st": sn2,
                "G_m2": ba_ob_2,
                "V_m3sk": v2,
            },
            "gallring": {
                "DG_cm": d3,
                "N_st": sn3,
                "G_m2": g3,
                "V_m3sk": v3,
            },
            "g_proc": {"N_pct": n_pct, "V_pct": v_pct},
            "total_prod": {"G_m2": cum_ba, "V_m3sk": cum_vol},
            "med_tillv": {"G_m2_per_yr": mai_g, "V_m3sk_per_yr": mai_v},
            "lop_tillv": {"G_m2_per_yr": cai_g, "V_m3sk_per_yr": cai_v},
        }
        self._record_row(row)

        # ── Update cumulative state ──────────────────────────────────────
        state.cum_ba_ob = cum_ba
        state.cum_vol = cum_vol
        state.ba_ob_prev = ba_ob_2
        state.vol_prev = v2
        state.thinned_prev = thinned_now

        if self._sag is not None and t >= self._sag:
            self._done = True
            return row

        # ── Determine next growth period ─────────────────────────────────
        ba_ub_2 = ba_ob_to_ub(ba_ob_2, h100, sn2, lat)

        if years is not None:
            p_next = float(years)
        else:
            if program is None:
                raise ValueError("PerssonThinningProgram required when years is not provided.")
            if self._sag is None:
                raise ValueError(
                    "Provide final_bh_age or final_total_age for scheduled simulation."
                )
            if program.interval_type == "age":
                p_next, tmx, val_flag, idx_i, idx_o, idx_g = _schedule_age(
                    t,
                    self._sag,
                    state.tmx if state.tmx is not None else program.first_trigger,
                    state.val,
                    state.interval_idx,
                    state.outtake_idx,
                    state.gf_idx,
                    program.intervals,
                    program.outtakes,
                    h100,
                )
                state.tmx = tmx
            else:
                p_next, gmx, val_flag, idx_i, idx_o, idx_g = _schedule_basal_area(
                    t,
                    self._sag,
                    state.gmx if state.gmx is not None else program.first_trigger,
                    ba_ob_2,
                    state.val,
                    state.interval_idx,
                    state.outtake_idx,
                    state.gf_idx,
                    program.intervals,
                    program.outtakes,
                    ba_ub_2,
                    h100,
                    lat,
                    sn2,
                )
                state.gmx = gmx
            state.val = val_flag
            state.interval_idx = idx_i
            state.outtake_idx = idx_o
            state.gf_idx = idx_g

        if p_next <= 0.0:
            self._done = True
            state.t = t
            state.sn1 = sn2
            state.ba_ob = ba_ob_2
            state.ba_ub = ba_ub_2
            state.p = 0.0
            return row

        # ── Project growth forward ───────────────────────────────────────
        # BA increment (under bark) at post-thinning state.  Stems do
        # NOT change during growth – mortality is a discrete event
        # evaluated at the next evaluation point.
        annual_ig = ba_increment_annual_ub(max(0.01, ba_ub_2), max(1.0, t), h100, lat)
        ba_ub_new = ba_ub_2 + annual_ig * p_next
        t_new = t + p_next
        ba_ob_new = ba_ub_to_ob(ba_ub_new, h100, sn2, lat)

        state.t = t_new
        state.sn1 = sn2
        state.ba_ob = ba_ob_new
        state.ba_ub = ba_ob_to_ub(ba_ob_new, h100, sn2, lat)
        state.p = p_next
        return row


# ═══════════════════════════════════════════════════════════════════════════════
# GrowthModel adapter
# ═══════════════════════════════════════════════════════════════════════════════


class Persson1992Model(GrowthModel):
    """Simulation adapter for the Persson (1992) Scots Pine model."""

    def __init__(
        self,
        init: Optional[PerssonStandInit] = None,
        program: Optional[PerssonThinningProgram] = None,
        *,
        track_history: bool = False,
    ) -> None:
        self._default_init = init
        self._default_program = program
        self._track_history = track_history

    @property
    def component_id(self) -> str:
        return "persson_1992"

    @property
    def source(self) -> SourceReference:
        return SourceReference(
            author="Persson, O. A.",
            year=1992,
            title="En produktionsmodell för tallskog i Sverige",
        )

    def requirements(self) -> Requirements:
        return Requirements(inventory="aggregate")

    def build_context(
        self,
        stand: Stand,
        *,
        init: Optional[PerssonStandInit] = None,
        program: Optional[PerssonThinningProgram] = None,
        track_history: Optional[bool] = None,
        **kwargs: Any,
    ) -> SimulationContext:
        ctx = super().build_context(stand, mode_hint="aggregate", **kwargs)
        resolved_init = self._resolve_init(stand, init)
        resolved_program = (
            program or stand.attrs.get("persson_1992_program") or self._default_program
        )
        history_flag = self._track_history if track_history is None else track_history
        stand_model = Persson1992Stand(
            resolved_init,
            program=resolved_program,
            track_history=history_flag,
        )
        ctx.attrs["persson_1992_stand"] = stand_model
        ctx.attrs["persson_1992_program"] = resolved_program
        ctx.state["t"] = stand_model.bh_age
        ctx.state["years_since_thin"] = 0.0
        ctx.set_aggregate_metrics(
            ba_total=stand_model.basal_area_m2_per_ha,
            stems_total=stand_model.stems_per_ha,
        )
        return ctx

    def update_step(self, ctx: SimulationContext, dt: float) -> None:
        stand_model = self._stand_from_ctx(ctx)
        thinning = ctx.state.pop("persson_1992_pending_thinning", None)
        thinning_req = stand_model._coerce_thinning(thinning)
        row = stand_model.grow(years=dt, thinning=thinning_req)
        if row is not None:
            ctx.attrs["persson_1992_last_row"] = row
            if stand_model.track_history:
                ctx.attrs["persson_1992_rows"] = list(stand_model.rows)
        ctx.set_aggregate_metrics(
            ba_total=stand_model.basal_area_m2_per_ha,
            stems_total=stand_model.stems_per_ha,
        )
        if thinning_req is not None:
            ctx.state["years_since_thin"] = 0.0
        else:
            ctx.state["years_since_thin"] = ctx.state.get("years_since_thin", 0.0) + dt

    def available_actions(self) -> Dict[str, ActionSpec]:
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
        normalized = str(outtake_type).lower()
        if normalized not in {"percent", "residual", "absolute"}:
            raise ValueError("outtake_type must be percent, residual, or absolute.")
        ctx.state["persson_1992_pending_thinning"] = {
            "outtake": float(outtake),
            "outtake_type": normalized,
            "diameter_factor": diameter_factor,
        }

    def _resolve_init(self, stand: Stand, init: Optional[PerssonStandInit]) -> PerssonStandInit:
        resolved = init or stand.attrs.get("persson_1992_init") or self._default_init
        if resolved is None:
            raise ValueError("Persson1992Model requires a PerssonStandInit.")
        stems = resolved.stems
        basal_area = resolved.basal_area
        if stems is None:
            stems = float(stand.Stems)
        if basal_area is None:
            basal_area = float(stand.BasalArea)
        latitude = resolved.latitude
        altitude_m = resolved.altitude_m
        site = stand.site
        if site is not None:
            lat = getattr(site, "latitude", None)
            if lat is not None and latitude == 64.0:  # default
                latitude = float(lat)
            alt = getattr(site, "altitude", None) or getattr(site, "altitude_m", None)
            if alt is not None and altitude_m == 0.0:
                altitude_m = float(alt)
        return replace(
            resolved,
            stems=stems,
            basal_area=basal_area,
            latitude=latitude,
            altitude_m=altitude_m,
        )

    @staticmethod
    def _stand_from_ctx(ctx: SimulationContext) -> Persson1992Stand:
        stand_model = ctx.attrs.get("persson_1992_stand")
        if not isinstance(stand_model, Persson1992Stand):
            raise ValueError("Persson1992Model context missing stand model.")
        return stand_model


# ═══════════════════════════════════════════════════════════════════════════════
# Convenience function
# ═══════════════════════════════════════════════════════════════════════════════


def persson_simulate(
    init: PerssonStandInit, program: PerssonThinningProgram
) -> PerssonSimulationResult:
    """Run the Persson (1992) simulation and return the result."""
    stand = Persson1992Stand(init, program=program, track_history=True).run()
    return PerssonSimulationResult(
        rows=stand.rows,
        self_thinning_summary=stand.self_thinning_summary,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Module descriptor
# ═══════════════════════════════════════════════════════════════════════════════


DESCRIPTOR = FormulaDescriptor(
    component_id="persson_1992_model",
    source=SourceReference(
        author="Persson, O. A.",
        year=1992,
        title="En produktionsmodell för tallskog i Sverige",
    ),
    kind="model",
    domain="growth",
    composes=(),
    kernel_names=("Persson1992Model",),
)
