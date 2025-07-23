from math import pi
from typing import Optional, Type

import numpy as np

from pyforestry.base.pricelist import Pricelist, TimberPricelist
from pyforestry.base.taper import Taper
from pyforestry.base.timber import Timber

from ..helpers.bucking import (
    BuckingConfig,
    BuckingResult,
    CrossCutSection,
    QualityType,
    _TreeCache,
)


# -------------------------------------------------------------------------
class Nasberg_1985_BranchBound:
    """
    Vectorised version – interface identical to the earlier class.
    """

    # -------------------- ctor helpers (unchanged except float32 tv) -------
    def __init__(
        self, timber: Timber, pricelist: Pricelist, taper_class: Optional[Type[Taper]] = None
    ):
        """Initialise the optimizer with timber data and pricing information."""
        self._timber = timber
        self._species = timber.species
        self._taper_class = taper_class or Taper
        if pricelist is None:
            raise ValueError("Pricelist must be set")
        self._pricelist = pricelist

        self._timber_prices = pricelist.Timber.get(timber.species)
        if self._timber_prices is None:
            raise ValueError(f"No prices for {timber.species}")

        # length/diam ranges
        # Convert length limits from metres to decimetres
        self._minLengthTimberLog_dm = int(round(pricelist.TimberLogLength.Min * 10))  # 34
        self._maxLengthTimberLog_dm = int(round(pricelist.TimberLogLength.Max * 10))  # 55
        self._minLengthPulpwoodLog_dm = int(round(pricelist.PulpLogLength.Min * 10))  # 27
        self._maxLengthPulpwoodLog_dm = int(round(pricelist.PulpLogLength.Max * 10))  # 55

        self._minDiameterTimberLog = self._timber_prices.minDiameter
        self._maxDiameterTimberLog = self._timber_prices.maxDiameter
        self._mvarde = pricelist.Pulp.getPulpwoodPrice(timber.species) * 100.0

        # modules list + O(1) reverse map
        min_len = int(min(self._minLengthPulpwoodLog_dm, self._minLengthTimberLog_dm))
        max_len = int(self._maxLengthTimberLog_dm)

        if min_len < 10:
            raise ValueError("Minimum log length must be at least 1 meter")

        self._moduler = list(range(min_len, max_len + 1)) + [999]

        self._mod_ix = {dm: i for i, dm in enumerate(self._moduler)}

        self._timberValue = self._build_value_table().astype(np.float32)

        # static map butt/middle/top
        self.quality_log_part = {
            QualityType.ButtLog: TimberPricelist.LogParts.Butt,
            QualityType.MiddleLog: TimberPricelist.LogParts.Middle,
            QualityType.TopLog: TimberPricelist.LogParts.Top,
            QualityType.Pulp: -1,
            QualityType.LogCull: -1,
            QualityType.Fuelwood: -1,
            QualityType.Undefined: -1,
        }

    def _build_value_table(self) -> np.ndarray:
        """Pre-compute log values for quick lookups during optimisation."""
        max_diam = self._maxDiameterTimberLog
        tv = np.zeros((max_diam + 1, len(self._moduler), 4))
        tp = self._timber_prices
        if tp is None:
            return tv
        for d in range(self._minDiameterTimberLog, max_diam + 1):
            for idx, dm in enumerate(self._moduler[:-1]):  # skip sentinel
                if dm < self._minLengthTimberLog_dm or dm > self._maxLengthTimberLog_dm:
                    continue
                vf = 1.0
                if tp.volume_type == "m3to":
                    r = (d / 100) * 0.5
                    vf = pi * r * r * (dm / 10)
                for p in (0, 1, 2):
                    base = tp[d].price_for_log_part(p)
                    corr = tp.length_corrections.get_length_correction(d, p, dm)
                    tv[d, idx, p + 1] = (base + corr) * 100.0 * vf
        return tv

    # ---------------------------------------------------------------------
    def calculate_tree_value(
        self, *, min_diam_dead_wood: float, config: BuckingConfig | None = None
    ) -> BuckingResult:
        """Run the branch-and-bound optimisation and return the result."""
        config = config or BuckingConfig()
        height_m = self._timber.height_m
        taper = self._taper_class(self._timber)
        cache = _TreeCache()

        # ------------ heights with cached inversion ----------------------
        HSTUB = self._timber.stump_height_m
        top_diam = max(self._pricelist.TopDiameter, self._pricelist.PulpLogDiameter.Min)
        HTOP = cache.height(taper, top_diam)

        q_height = cache.height(taper, self._minDiameterTimberLog)
        tp = self._timber_prices
        h_butt = min(tp.max_height_quality1, q_height)
        h_mid = min(tp.max_height_quality2, q_height)
        h_top = min(tp.max_height_quality3, q_height)

        # ------------ general --------------------------------------------
        # Observe! This is *height above stump*
        DBH_cm = Taper.get_diameter_at_height(taper, 1.3 - HSTUB)  # cm
        diameter_stump_cm = Taper.get_diameter_at_height(taper, 0.0)  # cm

        # ------------ discretise (vector) --------------------------------

        NMAX = 400
        total_dm = min(int((HTOP - HSTUB * 10)), NMAX)
        if total_dm <= 0:
            return BuckingResult(0, 1, 1, 1, 1, 0, [0] * 7, [0] * 7, 0, 0)

        dm = np.arange(total_dm + 1, dtype=np.int32)
        h = HSTUB + dm * 0.1
        dh = taper.get_diameter_vectorised(h)  # vectorised diameter

        taperDiams_cm = dh.tolist()  # NumPy → list[float]
        taperHeights_m = h.tolist()  # ditto

        #  endpoints ------------------------------------------------------
        dead_idx = int(dm[dh >= min_diam_dead_wood].max(initial=0))
        fub_idx = int(dm[dh >= 5].max(initial=0))
        tp_idx = int(dm[dh >= self._pricelist.TopDiameter].max(initial=0))

        vol_fub5 = taper.volume_section(HSTUB, h[min(fub_idx, total_dm)])
        vol_fub = taper.volume_section(HSTUB, h[fub_idx])
        vol_sk = vol_fub + (
            taper.volume_section(h[fub_idx], height_m) if height_m > h[fub_idx] else 0
        )
        vol_dead = taper.volume_section(h[0], h[dead_idx])
        p_dead = vol_dead / vol_sk if vol_sk else 0.0

        # high stump
        hs_ep = 0
        HSheight = self._pricelist.HighStumpHeight
        if HSheight > 0:
            hs_ep = int(dm[h >= HSheight].min(initial=0))
        vol_hs = taper.volume_section(h[0], h[hs_ep]) if hs_ep else 0.0
        p_vol_hs = vol_hs / vol_sk if vol_sk else 0.0

        # ---------------- DP arrays (float32) ----------------------------
        v = np.full(total_dm + 1, -np.inf, dtype=np.float32)
        vtimber = np.full_like(v, -np.inf)
        back = np.zeros(total_dm + 1, dtype=np.int16)
        kval = np.zeros(total_dm + 1, dtype=np.uint8)
        v[0] = vtimber[0] = 1e-5

        # quality dm limits
        i_butt = int((h_butt - HSTUB) * 10 - 1e-7)
        i_mid = int((h_mid - HSTUB) * 10 - 1e-7)
        i_top = int((h_top - HSTUB) * 10 - 1e-7)

        def qual(i):
            """Return the quality class index for position ``i``."""
            if i <= i_butt:
                return QualityType.ButtLog
            if i <= i_mid:
                return QualityType.MiddleLog
            if i <= i_top:
                return QualityType.TopLog
            return QualityType.Pulp

        cull_price = self._pricelist.LogCullPrice * 100.0
        fuel_price = self._pricelist.FuelWoodPrice * 100.0

        # ---- DP main loop (vector over modules) -------------------------
        mod_arr = np.array(self._moduler[:-1], dtype=np.int32)  # skip 999 sentinel
        mod_len = mod_arr.size
        zero_f = np.zeros(mod_len, dtype=np.float32)

        for left in range(total_dm + 1):
            if left > tp_idx and v[left] <= 0:
                continue
            # vector of right indices for all modules
            right = left + mod_arr
            mask = right <= total_dm
            if not mask.any():
                continue
            right = right[mask]
            mods = mod_arr[mask]
            h1 = h[left]
            h2 = h[right]
            vol_vec = np.array([taper.volume_section(h1, hh) for hh in h2], dtype=np.float32)
            diam_vec = dh[right].astype(np.int16)

            q_vec = np.vectorize(qual, otypes=[np.uint8])(right)

            # --- timber candidate mask -----------------------------------
            timber_ok = (
                (q_vec != QualityType.Pulp.value)
                & (mods >= self._minLengthTimberLog_dm)
                & (diam_vec >= self._minDiameterTimberLog)
                & (diam_vec <= self._maxDiameterTimberLog)
                & (right <= i_top)
            )
            # --- pulp candidate mask ------------------------------------
            pulp_ok = (
                (~timber_ok)
                & (mods >= self._minLengthPulpwoodLog_dm)
                & (mods <= self._maxLengthPulpwoodLog_dm)
                & (diam_vec >= self._pricelist.PulpLogDiameter.Min)
                & (diam_vec <= self._pricelist.PulpLogDiameter.Max)
            )
            # --- cull mask ----------------------------------------------
            cull_ok = (~timber_ok) & (~pulp_ok) & (mods >= 0.5 * self._minLengthPulpwoodLog_dm)

            # ---------- compute values in vector form -------------------
            new_v = np.full_like(vol_vec, -np.inf)
            new_vt = np.full_like(vol_vec, -np.inf)
            # timber branch
            if timber_ok.any():
                idxs = np.where(timber_ok)[0]
                parts = np.vectorize(lambda q: self.quality_log_part[QualityType(q)])
                part_vec = parts(q_vec[idxs])
                pulp_p = fuel_p = cull_p = zero_f[: idxs.size]
                price = self._timberValue[
                    diam_vec[idxs], [self._mod_ix[m] for m in mods[idxs]], q_vec[idxs]
                ]
                price *= config.timber_price_factor
                if self._timber_prices.volume_type == "m3fub":
                    price *= vol_vec[idxs]
                timber_val = price  # default (no downgrade)

                if config.use_downgrading:
                    # loop small (<=3) – negligible
                    for k, _ in enumerate(idxs):
                        w = self._timber_prices.getTimberWeight(part_vec[k])
                        pp, fp, cp = (
                            w.pulpwoodPercentage / 100.0,
                            w.fuelWoodPercentage / 100.0,
                            w.logCullPercentage / 100.0,
                        )
                        s = pp + fp + cp
                        cp = cp if s <= 1 else max(0.0, 1 - pp - fp)
                        pulp_p[k] = pp
                        fuel_p[k] = fp
                        cull_p[k] = cp
                    timber_val = price * (1 - pulp_p - fuel_p - cull_p)

                new_v[idxs] = (
                    v[left]
                    + timber_val
                    + pulp_p * config.pulp_price_factor * self._mvarde * vol_vec[idxs]
                    + cull_p * cull_price * vol_vec[idxs]
                    + fuel_p * fuel_price * vol_vec[idxs]
                )
                new_vt[idxs] = vtimber[left] + price

            # pulp branch
            if pulp_ok.any():
                idxs = np.where(pulp_ok)[0]
                pulp_val = config.pulp_price_factor * self._mvarde * vol_vec[idxs]
                if config.use_downgrading:
                    waste = self._pricelist.getPulpWoodWasteProportion(self._species)
                    fuel = self._pricelist.getPulpwoodFuelwoodProportion(self._species)
                    if waste + fuel > 1.0:
                        waste = max(0.0, 1 - fuel)
                    pulp_val *= 1 - waste - fuel
                    pulp_val += (
                        fuel * fuel_price * vol_vec[idxs] + waste * cull_price * vol_vec[idxs]
                    )
                new_v[idxs] = v[left] + pulp_val
                new_vt[idxs] = vtimber[left]

            # cull branch
            if cull_ok.any():
                idxs = np.where(cull_ok)[0]
                new_v[idxs] = v[left] + cull_price * vol_vec[idxs]
                new_vt[idxs] = vtimber[left]
                q_vec[idxs] = QualityType.LogCull.value

            # -------- scatter update into global DP arrays ---------------
            better = new_v > v[right]
            if better.any():
                v[right[better]] = new_v[better]
                vtimber[right[better]] = new_vt[better]
                back[right[better]] = left
                kval[right[better]] = q_vec[better]

        # ---------------- pick best endpoint ----------------------------
        end = int(np.argmax(v))
        best = v[end]
        if best <= 0:
            return BuckingResult(0, 1, p_dead, p_vol_hs, 0, 0, [0] * 7, [0] * 7, vol_fub5, vol_sk)

        total_SEK = best / 100.0
        vol_top = taper.volume_section(h[end], height_m)
        p_top = vol_top / vol_sk if vol_sk else 0.0
        last_rel = h[end] / height_m if height_m else 1.0

        # ---------------- reconstruct (still small loop) ----------------
        vol_q = [0.0] * 7
        price_q = [0.0] * 7
        vol_for_p = [0.0] * 7
        secs = []
        cur = end
        while cur > 0:
            prev = back[cur]
            q = QualityType(kval[cur])
            vol = taper.volume_section(h[prev], h[cur])
            if q in (QualityType.ButtLog, QualityType.MiddleLog, QualityType.TopLog):
                vol_q[q.value] += vol
                vol_for_p[q.value] += vol
                price_q[q.value] += (vtimber[cur] - vtimber[prev]) / 100.0
            elif q == QualityType.Pulp:
                vol_q[QualityType.Pulp.value] += vol
            elif q == QualityType.LogCull:
                vol_q[QualityType.LogCull.value] += vol

            # Store reconstruction CrossCutSection ---------------------------
            if config.save_sections:
                # crude but safe proportions (can be refined later)
                timber_prop = (
                    1.0
                    if q in (QualityType.ButtLog, QualityType.MiddleLog, QualityType.TopLog)
                    else 0.0
                )
                sec = CrossCutSection(
                    start_point=prev,
                    end_point=cur,
                    volume=vol,
                    top_diameter=dh[cur],
                    value=(v[cur] - v[prev]) / 100.0,  # öre → SEK
                    species_group=self._species,
                    timber_proportion=timber_prop,
                    pulp_proportion=0.0,
                    cull_proportion=0.0,
                    fuelwood_proportion=0.0,
                    quality=q,
                )
                # --- merge with previous if contiguous and same class ----
                if secs:
                    last = secs[-1]
                    contiguous = last.start_point == sec.end_point  # bottom-to-top order
                    if contiguous and last.quality == sec.quality:
                        secs[-1] = self._merge_sections(sec, last)
                    else:
                        secs.append(sec)
                else:
                    secs.append(sec)

            cur = prev

        for q in (QualityType.ButtLog, QualityType.MiddleLog, QualityType.TopLog):
            if vol_for_p[q.value] > 0:
                price_q[q.value] /= vol_for_p[q.value]

        return BuckingResult(
            species_group=self._species,
            total_value=total_SEK,
            top_proportion=p_top,
            dead_wood_proportion=p_dead,
            high_stump_volume_proportion=p_vol_hs,
            high_stump_value_proportion=((v[back[hs_ep]] / 100.0) / total_SEK if hs_ep else 0.0),
            last_cut_relative_height=last_rel,
            volume_per_quality=vol_q,
            timber_price_by_quality=price_q,
            vol_fub_5cm=vol_fub5,
            vol_sk_ub=vol_sk,
            DBH_cm=DBH_cm,
            height_m=height_m,
            stump_height_m=self._timber.stump_height_m,
            diameter_stump_cm=diameter_stump_cm,
            taperDiams_cm=taperDiams_cm,
            taperHeights_m=taperHeights_m,
            sections=secs if config.save_sections else None,
        )

    @staticmethod
    def _merge_sections(a: CrossCutSection, b: CrossCutSection) -> CrossCutSection:
        """Return a new section combining ``a`` and ``b`` using volume weights."""
        total_vol = a.volume + b.volume

        new_start = min(a.start_point, b.start_point)
        new_end = max(a.end_point, b.end_point)

        def w_avg(attr):
            """Weighted average of attribute ``attr`` across both sections."""
            return ((getattr(a, attr) * a.volume) + (getattr(b, attr) * b.volume)) / total_vol

        return CrossCutSection(
            start_point=new_start,
            end_point=new_end,
            volume=total_vol,
            top_diameter=b.top_diameter if b.end_point > a.end_point else a.top_diameter,
            value=a.value + b.value,
            species_group=a.species_group,
            timber_proportion=w_avg("timber_proportion"),
            pulp_proportion=w_avg("pulp_proportion"),
            cull_proportion=w_avg("cull_proportion"),
            fuelwood_proportion=w_avg("fuelwood_proportion"),
            quality=a.quality,
        )
