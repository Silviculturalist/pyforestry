"""Eriksson (1976) Norway spruce stand model.

This module reimplements the Norway spruce yield and thinning model published by
Eriksson (1976/77).  The implementation mirrors the original FORTRAN77 driver
logic while exposing the results using :mod:`pyforestry` primitives such as
:class:`~pyforestry.base.helpers.primitives.StandBasalArea` and
:class:`~pyforestry.base.helpers.primitives.Stems`.

The model tracks basal area (over and under bark), stem density, quadratic mean
diameter and stand volume with explicit handling for operator thinning and
self-thinning.  Timing of events and the growth increment follow the original
``GYIELD`` subroutine.  The code largely follows the structure of the historical
F77 listing but adopts Python conventions and helper utilities already present
in the project.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

import numpy as np
import pandas as pd

from pyforestry.base.helpers.primitives import (
    Age,
    AgeMeasurement,
    QuadraticMeanDiameter,
    StandBasalArea,
    StandVolume,
    Stems,
)
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970

__all__ = [
    "ErikssonSpruceStand",
    "ThinningProgram",
    "run_program",
]

# Historical constant used in the original tables – differs slightly from
# :func:`math.pi` and reproduces legacy values exactly.
_PI_FOR_QMD = 3.1415926535


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def qmd(ba_m2_per_ha: float, stems_per_ha: float) -> float:
    """Quadratic mean diameter (cm) from basal area and stem density."""
    if stems_per_ha <= 0 or ba_m2_per_ha <= 0:
        return 0.0
    return 100.0 * math.sqrt(4.0 * ba_m2_per_ha / (_PI_FOR_QMD * stems_per_ha))


def mai(total: float, total_age_years: float) -> float:
    """Mean annual increment helper."""
    return total / total_age_years if total_age_years > 0 else 0.0


# ---------------------------------------------------------------------------
# Dataclasses representing the stand dynamics
# ---------------------------------------------------------------------------
@dataclass
class ErikssonSpruceStand:
    """Simulate a spruce stand following Eriksson (1976).

    Parameters
    ----------
    stems:
        Initial number of stems per hectare.
    dominant_height_m:
        Dominant height in metres at the starting breast-height age.  Either
        ``dominant_height_m`` or ``age_bh_years`` must be provided.
    age_bh_years:
        Breast-height age in years at the start of the simulation.  Either
        ``dominant_height_m`` or ``age_bh_years`` must be provided.
    H100_m:
        Site index at total age 100 (metres).  When both dominant height and
        age are supplied this value is derived automatically using the published
        height functions.
    northern_sweden:
        ``True`` for the northern height system, ``False`` for the southern
        variant.
    planted:
        Whether the stand originates from planting.  Affects the height system
        and initial basal area equation.
    latitude_deg:
        Latitude in decimal degrees.
    ba_m2_per_ha_over_bark:
        Optional override for the initial basal area (over bark).
    """

    stems: int
    dominant_height_m: Optional[float] = None
    age_bh_years: Optional[float] = None

    H100_m: Optional[float] = None
    northern_sweden: bool = True
    planted: bool = True
    latitude_deg: float = 65.0

    ba_m2_per_ha_over_bark: Optional[float] = None

    species = TreeSpecies.Sweden.picea_abies

    # Derived state values (floats to keep the numerical routines simple)
    time_to_bh_years: float = field(init=False)
    qmd_cm: float = field(init=False)  # Over bark QMD
    ba_m2_per_ha: float = field(init=False)  # Basal area over bark
    ba_m2_per_ha_ub: float = field(init=False)  # Basal area under bark
    qmd_cm_ub: float = field(init=False)  # QMD under bark
    volume_m3sk_per_ha: float = field(init=False)
    form_height: float = field(init=False)
    total_ba_m2_per_ha: float = field(init=False)
    total_vol_m3sk_per_ha: float = field(init=False)
    mai_ba: float = field(init=False)
    mai_vol: float = field(init=False)

    # Period-by-period storage indexed by BH age
    storage: Dict[float, Dict[str, float]] = field(default_factory=dict, init=False)

    # Empirical coefficients (indexed by site class 16–36 m)
    C1 = np.array([0.250, 0.213, 0.304, 0.260, 0.337, 0.337])
    C2 = np.array([-0.046, -0.055, -0.056, -0.059, -0.046, -0.046])
    C3 = np.array([0.049, 0.085, 0.126, 0.034, 0.056, 0.056])
    C5 = np.array([0.334, 0.460, 0.035, 0.112, 0.120, 0.120])
    C6 = np.array([-0.748, -0.875, -0.571, -0.667, -0.789, -0.789])
    C7 = np.array([-0.308, -0.313, -0.154, -0.066, -0.013, -0.013])
    FORM_EXP = np.array([0.835, 0.833, 0.838, 0.838, 0.839, 0.844])
    ST_BA_B1 = np.array([0.524, 1.858, 2.613, 2.872, 3.229, 2.646])
    ST_BA_B2 = np.array([3.505, 3.376, 3.356, 3.347, 3.458, 3.479])
    BARK_ADD_QMD_EXP = np.array([-0.224, -0.247, -0.249, -0.266, -0.255, -0.280])
    BARK_SUB_QMD_EXP = np.array([-0.138, -0.183, -0.206, -0.236, -0.243, -0.243])
    VS_C = np.array([0.447, 0.488, 0.498, 0.568, 0.763, 0.763])

    def __post_init__(self) -> None:  # noqa: C901 - large but mirrors the original logic
        if self.dominant_height_m is None and self.age_bh_years is None:
            raise ValueError("Provide either dominant_height_m or age_bh_years.")
        if self.stems is None or self.stems <= 0:
            raise ValueError("stems must be a positive integer (stems per hectare).")

        if self.dominant_height_m is not None and self.age_bh_years is not None:
            self.H100_m = self._derive_h100(self.dominant_height_m, self.age_bh_years)

        if self.H100_m is None:
            raise ValueError(
                "H100_m must be provided or derivable from (dominant_height_m, age_bh_years)."
            )

        self.time_to_bh_years = self._time_to_bh()

        if self.dominant_height_m is None:
            self.dominant_height_m = self._height_from_age(self.age_bh_years)
        if self.age_bh_years is None:
            self.age_bh_years = self._age_from_height(self.dominant_height_m)

        if self.ba_m2_per_ha_over_bark is None:
            b = 0.355 if self.planted else 0.319
            self.ba_m2_per_ha = (
                1.0111 * ((self.dominant_height_m - 1.3) ** 1.230) * ((self.stems / 1000.0) ** b)
            )
        else:
            self.ba_m2_per_ha = float(self.ba_m2_per_ha_over_bark)

        d1_ob = qmd(self.ba_m2_per_ha, self.stems)
        bark_sub_pct = self._bark_sub_pct(d1_ob, self.ba_m2_per_ha, self.age_bh_years)
        self.ba_m2_per_ha_ub = self.ba_m2_per_ha * (1.0 - bark_sub_pct / 100.0)

        self.qmd_cm = d1_ob
        self.qmd_cm_ub = qmd(self.ba_m2_per_ha_ub, self.stems)
        self.form_height = self._form_height(self.dominant_height_m, self.qmd_cm)
        self.volume_m3sk_per_ha = self.form_height * self.ba_m2_per_ha

        self.total_ba_m2_per_ha = self.ba_m2_per_ha
        self.total_vol_m3sk_per_ha = self.volume_m3sk_per_ha
        total_age = self.age_bh_years + self.time_to_bh_years
        self.mai_ba = mai(self.total_ba_m2_per_ha, total_age)
        self.mai_vol = mai(self.total_vol_m3sk_per_ha, total_age)

        self._report(
            thin=None,
            selfthin=None,
            age_bh_start=self.age_bh_years,
            hdom_start=self.dominant_height_m,
        )

    # ------------------------------------------------------------------
    # Convenience properties using pyforestry primitives
    # ------------------------------------------------------------------
    @property
    def age_bh(self) -> AgeMeasurement:
        """Breast-height age as an :class:`AgeMeasurement`."""
        return Age.DBH(self.age_bh_years)

    @property
    def stems_per_ha(self) -> Stems:
        """Current stem density (stems/ha)."""
        return Stems(self.stems, species=self.species)

    @property
    def basal_area_ob(self) -> StandBasalArea:
        """Basal area over bark (m²/ha)."""
        return StandBasalArea(self.ba_m2_per_ha, species=self.species, over_bark=True)

    @property
    def basal_area_ub(self) -> StandBasalArea:
        """Basal area under bark (m²/ha)."""
        return StandBasalArea(self.ba_m2_per_ha_ub, species=self.species, over_bark=False)

    @property
    def volume_ob(self) -> StandVolume:
        """Volume over bark (m³sk/ha)."""
        return StandVolume(self.volume_m3sk_per_ha, species=self.species, over_bark=True)

    @property
    def qmd_ob(self) -> QuadraticMeanDiameter:
        """Quadratic mean diameter over bark (cm)."""
        return QuadraticMeanDiameter(self.qmd_cm)

    @property
    def qmd_ub(self) -> QuadraticMeanDiameter:
        """Quadratic mean diameter under bark (cm)."""
        return QuadraticMeanDiameter(self.qmd_cm_ub)

    # ------------------------------------------------------------------
    # Core simulation logic
    # ------------------------------------------------------------------
    def _dq_rule(self, hdom_m: float) -> float:
        """Return the default ratio of removed-to-standing QMD based on height."""
        h_dm = hdom_m * 10.0
        if h_dm <= 284.0:
            return min(1.0, 0.768478 + 0.00081522 * h_dm)
        return 1.0

    def grow(
        self,
        years: int,
        thinning: Optional[Dict] = None,
        self_thinning: bool = True,
    ) -> None:  # noqa: C901
        """Advance the stand by ``years`` applying optional operator thinning."""
        if years < 1:
            raise ValueError("years must be >= 1")

        age_start = float(self.age_bh_years)
        h_start = float(self.dominant_height_m)
        n_start = int(self.stems)
        g1_start = float(self.ba_m2_per_ha)
        gu1_start = float(self.ba_m2_per_ha_ub)
        d1_ob = float(self.qmd_cm)
        du1_ub = float(self.qmd_cm_ub)

        thin_record = {
            "applied": False,
            "mode": None,
            "value": 0.0,
            "percent_ba": 0.0,
            "dq": 0.0,
            "stems_removed": 0,
            "stems_base": n_start,
            "ba_removed": 0.0,
            "ba_removed_ub": 0.0,
            "qmd_thin_cm": 0.0,
        }

        gu3 = 0.0
        g3_ob = 0.0
        sn3 = 0
        du3 = 0.0

        if thinning is not None:
            mode = thinning.get("mode", "PR").upper()
            value = float(thinning["value"])

            if mode == "PR":
                pr_pct = max(0.0, min(100.0, value))
            elif mode == "FG":
                residual_ob = max(0.0, value)
                pr_pct = (
                    0.0
                    if g1_start <= 0
                    else max(0.0, min(100.0, 100.0 * (g1_start - residual_ob) / g1_start))
                )
            elif mode == "M2":
                remove_ob = max(0.0, value)
                pr_pct = (
                    0.0 if g1_start <= 0 else max(0.0, min(100.0, 100.0 * remove_ob / g1_start))
                )
            else:
                raise ValueError("thinning['mode'] must be PR, FG or M2")

            gu3 = gu1_start * (pr_pct / 100.0)
            gu3 = min(max(0.0, gu3), gu1_start)

            dq_ratio = thinning.get("dq", None)
            if dq_ratio is None:
                dq_ratio = self._dq_rule(h_start)
            dq_ratio = float(max(0.1, min(1.2, dq_ratio)))
            du3 = max(1e-9, du1_ub * dq_ratio)

            sn3_float = gu3 * 12732.4 / (du3**2)
            sn3 = int(round(sn3_float))
            sn3 = min(max(0, sn3), max(1, self.stems - 1))

            bark_add_inst = (
                (10.0**1.6549)
                * (max(gu1_start, 1e-9) ** (-0.281))
                * (max(age_start, 1e-9) ** 0.125)
                * (max(du3, 1e-9) ** self.BARK_ADD_QMD_EXP[self._site_class_index()])
            )
            g3_ob = gu3 * (1.0 + 0.01 * bark_add_inst)

            self.stems -= sn3
            self.ba_m2_per_ha_ub = max(0.0, self.ba_m2_per_ha_ub - gu3)
            self.ba_m2_per_ha = max(0.0, self.ba_m2_per_ha - g3_ob)

            self.qmd_cm_ub = qmd(self.ba_m2_per_ha_ub, max(self.stems, 1))
            self.qmd_cm = qmd(self.ba_m2_per_ha, max(self.stems, 1))

            thin_record = {
                "applied": True,
                "mode": mode,
                "value": value,
                "percent_ba": pr_pct,
                "dq": dq_ratio,
                "stems_removed": sn3,
                "stems_base": n_start,
                "ba_removed": g3_ob,
                "ba_removed_ub": gu3,
                "qmd_thin_cm": du3,
            }

        selfthin_record = {
            "ba_self": 0.0,
            "ba_self_ub": 0.0,
            "stems_self": 0,
            "dq_self": 0.0,
            "qmd_self": 0.0,
        }
        gu4 = 0.0
        g4_ob = 0.0
        sn4 = 0
        if self_thinning:
            n_for_self = n_start
            if n_for_self > 4500 and h_start > 15.0:
                warnings.warn(
                    "Ekö correction applied for very dense stands.",
                    stacklevel=2,
                )
                n_for_self = 4500 + 0.1 * (n_for_self - 4500)

            site_idx = self._site_class_index()
            g4_ob = (
                years
                * (10.0**-9.4888)
                * ((n_for_self / 1000.0) ** self.ST_BA_B1[site_idx])
                * ((h_start * 10.0) ** self.ST_BA_B2[site_idx])
            )
            d4_ob = (10.0**-1.411) * ((h_start * 10.0) ** 0.517) * max(d1_ob, 1e-9)
            d4_ob = max(1e-9, d4_ob)

            sn4_float = g4_ob * 12732.4 / (d4_ob**2)
            sn4 = int(round(sn4_float))

            bark_sub_self = (
                (10.0**0.9777)
                * (max(g1_start, 1e-9) ** 0.135)
                * (max(age_start, 1e-9) ** 0.112)
                * (max(d4_ob, 1e-9) ** self.BARK_SUB_QMD_EXP[site_idx])
            )
            gu4 = g4_ob * (1.0 - 0.01 * bark_sub_self)
            gu4 = max(0.0, gu4)

            self.stems = max(1, self.stems - sn4)
            self.ba_m2_per_ha_ub = max(0.0, self.ba_m2_per_ha_ub - gu4)
            self.ba_m2_per_ha = max(0.0, self.ba_m2_per_ha - g4_ob)

            self.qmd_cm_ub = qmd(self.ba_m2_per_ha_ub, max(self.stems, 1))
            self.qmd_cm = qmd(self.ba_m2_per_ha, max(self.stems, 1))

            selfthin_record = {
                "ba_self": g4_ob,
                "ba_self_ub": gu4,
                "stems_self": sn4,
                "dq_self": d4_ob / max(d1_ob, 1e-9),
                "qmd_self": d4_ob,
            }

        site_idx = self._site_class_index()
        total_ob_removed = g3_ob + g4_ob
        total_stems_removed = sn3 + sn4

        gp = 0.01
        gs1 = 1.0
        share_pct = 0.0
        if total_ob_removed > 0.0 and total_stems_removed > 0 and g1_start > 0 and n_start > 0:
            gp = (100.0 * total_ob_removed / g1_start) + 0.01
            removal_ratio = (total_ob_removed * n_start) / (g1_start * total_stems_removed)
            gs1 = math.sqrt(max(0.0, removal_ratio) + 0.01)
            share_pct = 100.0 * total_stems_removed / n_start
        gs2 = gs1 * (share_pct + 0.01)

        VS = (
            (10.0**1.1392)
            * ((age_start * 0.1) ** self.VS_C[site_idx])
            * ((max(self.stems, 1) / 1000.0) ** (-0.052))
        )

        P = years
        S2_dm = h_start * 10.0
        S3_age = age_start

        GINC = (
            (10.0**0.4207)
            * (max(gu1_start, 1e-9) ** self.C1[site_idx])
            * (gp ** self.C2[site_idx])
            * (gs2**0.024)
            * (P ** self.C3[site_idx])
            * (S2_dm ** self.C5[site_idx])
            * (S3_age ** self.C6[site_idx])
            * (VS ** self.C7[site_idx])
        )

        gu1_after = P * GINC + self.ba_m2_per_ha_ub

        self.age_bh_years += years
        self.dominant_height_m = self._height_from_age(self.age_bh_years)

        du1_after = qmd(gu1_after, max(self.stems, 1))
        bark_add_growth = (
            (10.0**1.6539)
            * (max(gu1_after, 1e-9) ** (-0.281))
            * (max(self.age_bh_years, 1e-9) ** 0.125)
            * (max(du1_after, 1e-9) ** self.BARK_ADD_QMD_EXP[site_idx])
        )
        g1_after = gu1_after * (1.0 + 0.01 * bark_add_growth)

        self.ba_m2_per_ha_ub = gu1_after
        self.ba_m2_per_ha = g1_after
        self.qmd_cm_ub = du1_after
        self.qmd_cm = qmd(self.ba_m2_per_ha, max(self.stems, 1))
        self.form_height = self._form_height(self.dominant_height_m, self.qmd_cm)
        self.volume_m3sk_per_ha = self.form_height * self.ba_m2_per_ha

        start_bark_add = (
            (10.0**1.6539)
            * (max(gu1_start, 1e-9) ** (-0.281))
            * (max(age_start, 1e-9) ** 0.125)
            * (max(du1_ub, 1e-9) ** self.BARK_ADD_QMD_EXP[site_idx])
        )
        g1_start_recon = gu1_start * (1.0 + 0.01 * start_bark_add)
        net_ba_change_ob = self.ba_m2_per_ha - g1_start_recon
        self.total_ba_m2_per_ha += net_ba_change_ob + total_ob_removed
        self.total_vol_m3sk_per_ha += self.volume_m3sk_per_ha

        total_age = self.age_bh_years + self.time_to_bh_years
        self.mai_ba = mai(self.total_ba_m2_per_ha, total_age)
        self.mai_vol = mai(self.total_vol_m3sk_per_ha, total_age)

        self._report(
            thin=thin_record,
            selfthin=selfthin_record,
            age_bh_start=age_start,
            hdom_start=h_start,
        )

    # ------------------------------------------------------------------
    # Secondary outputs
    # ------------------------------------------------------------------
    def as_dataframe(self) -> pd.DataFrame:
        """Return the recorded stand history as a tidy :class:`~pandas.DataFrame`."""
        df = pd.DataFrame.from_dict(self.storage, orient="index").reset_index(drop=True)
        cols = [
            "desc",
            "age_bh_start",
            "Hdom_start_m",
            "THIN_APPLIED",
            "THIN_AGE_BH",
            "THIN_PCT_BA",
            "THIN_DQ",
            "age_bh_years",
            "total_age_years",
            "H100_m",
            "dominant_height_m",
            "N_stems_ha",
            "QMD_cm",
            "QMD_UB_cm",
            "BA_m2_ha",
            "BA_UB_m2_ha",
            "VOL_m3sk_ha",
            "BA_removed_m2ha",
            "BA_removed_ub_m2ha",
            "N_removed",
            "QMD_removed_cm",
            "BA_self_m2ha",
            "BA_self_ub_m2ha",
            "N_self",
            "MAI_BA",
            "MAI_VOL",
        ]
        cols = [c for c in cols if c in df.columns]
        return df[cols]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _site_class_index(self) -> int:
        """Map ``H100`` to the index of the closest discrete site class (16–36 m)."""
        levels = np.array([16, 20, 24, 28, 32, 36], dtype=float)
        idx = int(np.argmin(np.abs(levels - float(self.H100_m))))
        return idx

    def _form_height(self, dominant_height_m: float, qmd_cm: float) -> float:
        """Compute the form height used to convert basal area into volume."""
        site_idx = self._site_class_index()
        b1 = self.FORM_EXP[site_idx]
        return (
            (10.0 ** (-1.1406))
            * ((dominant_height_m * 10.0) ** b1)
            * (max(qmd_cm, 1e-9) ** 0.1232)
        )

    def _bark_add_pct(self, qmd_cm_ub: float, ba_ub: float, age_bh_years: float) -> float:
        """Percentage bark addition converting under-bark area to over-bark."""
        site_idx = self._site_class_index()
        b1 = self.BARK_ADD_QMD_EXP[site_idx]
        return (10.0**1.6539) * (
            (max(ba_ub, 1e-9) ** -0.281)
            * (max(age_bh_years, 1e-9) ** 0.125)
            * (max(qmd_cm_ub, 1e-9) ** b1)
        )

    def _bark_sub_pct(self, qmd_cm_ob: float, ba_ob: float, age_bh_years: float) -> float:
        """Percentage bark subtraction converting over-bark area to under-bark."""
        site_idx = self._site_class_index()
        b1 = self.BARK_SUB_QMD_EXP[site_idx]
        return (10.0**0.9777) * (
            (max(ba_ob, 1e-9) ** 0.135)
            * (max(age_bh_years, 1e-9) ** 0.112)
            * (max(qmd_cm_ob, 1e-9) ** b1)
        )

    def _report(
        self,
        thin: Optional[Dict],
        selfthin: Optional[Dict],
        age_bh_start: float,
        hdom_start: float,
    ) -> None:
        """Persist a snapshot of the current period to :attr:`storage`."""
        key = round(float(self.age_bh_years or 0.0), 6)
        self.storage[key] = {
            "desc": "",
            "age_bh_start": float(age_bh_start),
            "Hdom_start_m": float(hdom_start),
            "THIN_APPLIED": bool(thin["applied"] if thin else False),
            "THIN_AGE_BH": float(age_bh_start) if (thin and thin["applied"]) else float("nan"),
            "THIN_PCT_BA": float((thin or {}).get("percent_ba", 0.0)),
            "THIN_DQ": float((thin or {}).get("dq", 0.0)),
            "H100_m": float(self.H100_m),
            "age_bh_years": float(self.age_bh_years or 0.0),
            "dominant_height_m": float(self.dominant_height_m or 0.0),
            "total_age_years": float(
                (self.age_bh_years or 0.0)
                + (self.time_to_bh_years if hasattr(self, "time_to_bh_years") else 0.0)
            ),
            "QMD_cm": float(self.qmd_cm if hasattr(self, "qmd_cm") else 0.0),
            "QMD_UB_cm": float(self.qmd_cm_ub if hasattr(self, "qmd_cm_ub") else 0.0),
            "N_stems_ha": int(self.stems),
            "BA_m2_ha": float(self.ba_m2_per_ha if hasattr(self, "ba_m2_per_ha") else 0.0),
            "BA_UB_m2_ha": float(
                self.ba_m2_per_ha_ub if hasattr(self, "ba_m2_per_ha_ub") else 0.0
            ),
            "VOL_m3sk_ha": float(
                self.volume_m3sk_per_ha if hasattr(self, "volume_m3sk_per_ha") else 0.0
            ),
            "QMD_removed_cm": float((thin or {}).get("qmd_thin_cm", 0.0)),
            "N_removed": int((thin or {}).get("stems_removed", 0)),
            "BA_removed_m2ha": float((thin or {}).get("ba_removed", 0.0)),
            "BA_removed_ub_m2ha": float((thin or {}).get("ba_removed_ub", 0.0)),
            "BA_self_m2ha": float((selfthin or {}).get("ba_self", 0.0)),
            "BA_self_ub_m2ha": float((selfthin or {}).get("ba_self_ub", 0.0)),
            "N_self": int((selfthin or {}).get("stems_self", 0)),
            "MAI_BA": float(self.mai_ba if hasattr(self, "mai_ba") else 0.0),
            "MAI_VOL": float(self.mai_vol if hasattr(self, "mai_vol") else 0.0),
        }

    # ------------------------------------------------------------------
    # Height systems
    # ------------------------------------------------------------------
    def _height_from_age(self, age_bh_years: float) -> float:
        """Predict dominant height from breast-height age using Hägglund (1970)."""
        if self.northern_sweden:
            height_value = Hagglund_1970.height_trajectory.picea_abies.northern_sweden(
                float(self.H100_m),
                Age.TOTAL(100.0),
                Age.DBH(age_bh_years),
                latitude=self.latitude_deg,
                culture=self.planted,
            )
        else:
            height_value = Hagglund_1970.height_trajectory.picea_abies.southern_sweden(
                float(self.H100_m),
                Age.TOTAL(100.0),
                Age.DBH(age_bh_years),
            )
        return float(height_value)

    def _age_from_height(self, dominant_height_m: float) -> float:
        """Invert the height system via a simple grid search over 1–400 years."""
        best_age, best_diff = 1.0, 1e9
        for t in range(1, 401):
            h_t = self._height_from_age(t)
            d = abs(dominant_height_m - h_t)
            if d < best_diff:
                best_diff = d
                best_age = t
        return float(best_age)

    def _time_to_bh(self) -> float:
        """Return the Hägglund (1970) time-to-breast-height estimate."""
        if self.northern_sweden:
            return Hagglund_1970.time_to_breast_height.picea_abies.northern_sweden(
                float(self.H100_m),
                Age.TOTAL(100.0),
                Age.TOTAL(100.0),
                latitude=self.latitude_deg,
                culture=self.planted,
            )
        return Hagglund_1970.time_to_breast_height.picea_abies.southern_sweden(
            float(self.H100_m),
            Age.TOTAL(100.0),
            Age.TOTAL(100.0),
        )

    def _derive_h100(self, dominant_height_m: float, age_bh_years: float) -> float:
        """Derive :math:`H_{100}` from observed dominant height and age."""
        if self.northern_sweden:
            h100 = Hagglund_1970.height_trajectory.picea_abies.northern_sweden(
                float(dominant_height_m),
                Age.DBH(age_bh_years),
                Age.TOTAL(100.0),
                latitude=self.latitude_deg,
                culture=self.planted,
            )
        else:
            h100 = Hagglund_1970.height_trajectory.picea_abies.southern_sweden(
                float(dominant_height_m),
                Age.DBH(age_bh_years),
                Age.TOTAL(100.0),
            )
        return float(h100)


# Type aliases for thinning definitions -------------------------------------------------
TriggerKind = Literal["AR", "DM", "M2"]
GradeKind = Literal["PR", "FG", "M2"]


@dataclass
class ThinningProgram:
    """Structured thinning description used by :func:`run_program`."""

    trigger_kind: TriggerKind
    first_trigger_value: float
    intervals: List[float]
    grade_kind: GradeKind
    grades: List[float]
    dq: Optional[float] = None
    dq_schedule: Optional[List[Optional[float]]] = None


# ---------------------------------------------------------------------------
# Helper utilities for running schedules
# ---------------------------------------------------------------------------
def _next_trigger_values(tp: ThinningProgram, count: int) -> List[float]:
    """Generate ``count`` trigger values expanding :class:`ThinningProgram` intervals."""
    vals = [tp.first_trigger_value]
    for i in range(1, count):
        inc = tp.intervals[min(i - 1, len(tp.intervals) - 1)]
        vals.append(vals[-1] + inc)
    return vals


def _step_size(age_bh_years: float) -> int:
    """Return the integration step length in years based on current age."""
    if age_bh_years < 30:
        return 6
    if age_bh_years < 50:
        return 8
    return 10


# ---------------------------------------------------------------------------
# Public orchestration helper
# ---------------------------------------------------------------------------
def run_program(
    description: str,
    H100_m: float,
    N0: int,
    region_north: bool,
    planted: bool,
    latitude: float,
    start_dominant_height_m: Optional[float],
    start_age_bh_years: Optional[float],
    program: Optional[ThinningProgram],
) -> pd.DataFrame:
    """Run the Eriksson stand model for a complete thinning program."""

    stand = ErikssonSpruceStand(
        stems=N0,
        dominant_height_m=start_dominant_height_m,
        age_bh_years=start_age_bh_years,
        H100_m=H100_m,
        northern_sweden=region_north,
        planted=planted,
        latitude_deg=latitude,
    )

    thresholds: List[float] = []
    grades_to_use: List[float] = []
    dq_seq: List[Optional[float]] = []

    if program is not None and len(program.grades) > 0:
        thresholds = _next_trigger_values(program, len(program.grades))
        grades_to_use = list(program.grades)
        if program.dq_schedule is not None:
            dq_seq = list(program.dq_schedule)
            if len(dq_seq) < len(grades_to_use):
                dq_seq = dq_seq + [None] * (len(grades_to_use) - len(dq_seq))
        else:
            dq_seq = [program.dq] * len(grades_to_use)

        if program.trigger_kind == "DM":
            approx_hmax_dm = int(round(stand._height_from_age(10000) * 10.0))
            keep = [i for i, thr in enumerate(thresholds) if thr <= approx_hmax_dm]
            if len(keep) < len(thresholds):
                thresholds = [thresholds[i] for i in keep]
                grades_to_use = [grades_to_use[i] for i in keep]
                dq_seq = [dq_seq[i] for i in keep]

    thin_ix = 0
    horizon_extra_steps = 6
    steps_done_after_last_thin = 0
    max_steps = 200
    steps = 0

    while thin_ix < len(grades_to_use) or steps_done_after_last_thin < horizon_extra_steps:
        steps += 1
        if steps > max_steps:
            warnings.warn(
                f"{description}: loop guard hit at age {stand.age_bh_years:.1f} (BH). "
                f"Remaining thins: {len(grades_to_use) - thin_ix}.",
                stacklevel=2,
            )
            break

        p = _step_size(stand.age_bh_years)

        if thin_ix < len(grades_to_use) and program is not None:
            thr = thresholds[thin_ix]
            if program.trigger_kind == "AR" and program.grade_kind != "PR":
                if stand.age_bh_years < thr <= stand.age_bh_years + p:
                    p = max(1, int(round(thr - stand.age_bh_years)))
            elif program.trigger_kind == "DM":
                if (stand.dominant_height_m * 10.0) < thr:
                    for t in range(1, p + 1):
                        if stand._height_from_age(stand.age_bh_years + t) * 10.0 >= thr:
                            p = t
                            break

        thin_dict: Optional[Dict[str, float]] = None
        trigger_now = False
        if thin_ix < len(grades_to_use) and program is not None:
            thr = thresholds[thin_ix]
            if program.trigger_kind == "AR":
                trigger_now = stand.age_bh_years >= thr
            elif program.trigger_kind == "DM":
                trigger_now = (stand.dominant_height_m * 10.0) >= thr
            elif program.trigger_kind == "M2":
                trigger_now = stand.ba_m2_per_ha >= thr

        if trigger_now:
            thin_dict = {"mode": program.grade_kind, "value": grades_to_use[thin_ix]}
            if dq_seq and dq_seq[thin_ix] is not None:
                thin_dict["dq"] = dq_seq[thin_ix]
            thin_ix += 1
            steps_done_after_last_thin = 0
        else:
            steps_done_after_last_thin += 1

        stand.grow(years=p, thinning=thin_dict, self_thinning=True)

    return stand.as_dataframe().query("desc == ''").assign(desc=description)
