# Näsberg (1985) branch-and-bound algorithm.
from Munin.Taper.EdgrenNylinder1949 import EdgrenNylinder1949
from Munin.TimberPriceList.PriceList import *
from enum import IntEnum
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
import math

class QualityType(IntEnum):
    Undefined = 0
    ButtLog   = 1  # Special
    MiddleLog = 2  # OS
    TopLog    = 3  # Kvint
    Pulp      = 4
    LogCull   = 5
    Fuelwood  = 6

@dataclass
class CrossCutSection:
    """Container for one log section in the final cutting solution."""
    start_point: int      # Index in decimeters from the stump
    end_point: int        # Index in decimeters from the stump
    volume: float         # Volume (e.g., m3 f ub) for that section
    top_diameter: float   # Diameter (cm) of the top of this log
    value: float          # Monetary value (e.g. in SEK) contributed by this section
    species_group: str    # For example, "Pine", "Spruce", etc.
    timber_proportion: float = 0.0
    pulp_proportion: float = 0.0
    cull_proportion: float = 0.0
    fuelwood_proportion: float = 0.0
    # Could add a `quality` field if you want to store the final quality.

@dataclass
class BuckingResult:
    """Encapsulates the output of the cross-cutting process."""
    total_value: float                    # The total value in e.g. SEK
    top_proportion: float                 # Proportion of volume above final cut
    dead_wood_proportion: float           # Proportion of volume considered dead wood
    high_stump_volume_proportion: float   # Proportion of total volume cut off as high stump
    high_stump_value_proportion: float    # Proportion of value that is in the high stump
    last_cut_relative_height: float       # Proportion of total height where final cut occurs
    volume_per_quality: List[float]       # Breakout of volumes by quality
    timber_price_by_quality: List[float]  # Per-cubic-meter average timber price by quality
    vol_fub_5cm: float                    # Volume under bark, 5 cm top
    vol_sk_ub: float                      # Total volume under bark for entire stem
    sections: Optional[List[CrossCutSection]] = None


# ------------------------------------------------------------------------------
# Here's the main branch and bound bucking logic
# ------------------------------------------------------------------------------

class Nasberg_1985_BranchBound:
    """
    Python version of the DP cross-cut logic from the C# code. 
    """

    # Mapping from our QualityType to the type index used in 'timberValue[diam][module][quality]'
    # The original code used: { Butt=1, Middle=2, Top=3 }, so we shift them or keep an offset.
    quality_log_part = {
        QualityType.ButtLog:   TimberPricelist.LogParts.Butt,
        QualityType.MiddleLog: TimberPricelist.LogParts.Middle,
        QualityType.TopLog:    TimberPricelist.LogParts.Top,
        QualityType.Pulp:      -1,
        QualityType.LogCull:   -1,
        QualityType.Fuelwood:  -1,
        QualityType.Undefined: -1
    }

    def __init__(self, species: str, region: str, pricelist: Pricelist):
        if pricelist is None:
            raise ValueError("Pricelist must be set")

        self._pricelist = pricelist
        self._species   = species
        self._region    = region

        # If species is not in self._pricelist.Timber, skip or handle
        self._timber_prices = self._pricelist.Timber.get(species, None)

        # Ranges
        self._minLengthTimberLog   = self._pricelist.TimberLogLength.Min
        self._maxLengthTimberLog   = self._pricelist.TimberLogLength.Max
        self._minLengthPulpwoodLog = self._pricelist.PulpLogLength.Min
        self._maxLengthPulpwoodLog = self._pricelist.PulpLogLength.Max

        # Diameters:
        if self._timber_prices:
            self._minDiameterTimberLog = self._timber_prices.minDiameter
            self._maxDiameterTimberLog = self._timber_prices.maxDiameter
        else:
            # If no timber prices for this species, treat as giant or zero
            self._minDiameterTimberLog = 999
            self._maxDiameterTimberLog = 999

        # For pulp:
        self._mvarde = self._pricelist.Pulp.getPulpwoodPrice(self._species) * 100  # SEK -> öre

        # Build the 'modules' array (possible log lengths) 
        self._moduler = self._build_modules()

        # Build a big table for timberValue[diam][module_index][qualityIndex]
        self._timberValue = self._build_timber_value_table()

    def _build_modules(self) -> List[int]:
        """
        Build the array of possible log lengths (the 'moduler') from the smallest pulp
        or timber length up to the max timber length, plus a sentinel large value.
        """
        min_log_length = min(self._minLengthPulpwoodLog, self._minLengthTimberLog)
        max_log_length = self._maxLengthTimberLog
        modules = []
        # Fill from min_log_length up to max_log_length
        for length_dm in range(min_log_length, max_log_length + 1):
            modules.append(length_dm)
        # Some Fortran code had a sentinel 999 at the end
        modules.append(999)
        return modules

    def _build_timber_value_table(self) -> List[List[List[float]]]:
        """
        Initialize the 3D table: timberValue[diam][moduleIndex][quality].
        We'll index diam up to self._maxDiameterTimberLog.
        We'll have len(self._moduler) modules, and 4 possible qualities
        (Butt=1, Middle=2, Top=3 in the original code).
        
        Because the original code used an offset for indexing, we replicate that
        with an easy direct approach: 
            timberValue[diam][modIndex][q] = price in öre for that stock. 
        """
        max_diam = self._maxDiameterTimberLog
        n_mod = len(self._moduler)
        # We'll store 4 qualities: index 1=Butt, 2=Middle, 3=Top. We'll put them at [1..3].
        # In python, we can store them at [0..3], ignoring index 0 or something similar.
        # For clarity, we can do [4] so that we can do [1], [2], [3].
        timber_value = [[[0.0 for _ in range(4)] 
                         for _ in range(n_mod)] 
                         for _ in range(max_diam + 1)]

        if self._timber_prices is None:
            return timber_value  # No data => all 0

        for diam in range(self._minDiameterTimberLog, self._maxDiameterTimberLog + 1):
            for mod_i, length_dm in enumerate(self._moduler):
                if length_dm > self._maxLengthTimberLog or length_dm < self._minLengthTimberLog:
                    continue
                # volumeFactor depends on the volume measure. 
                volume_factor = 1.0
                # If volume type == "m3to", approximate a cylinder for that piece:
                if self._timber_prices.volume_type == "m3to":
                    radius_m = (diam / 100.0) * 0.5  # cm -> m
                    length_m = length_dm / 10.0     # dm -> m
                    cylinder_volume = math.pi * (radius_m ** 2) * length_m
                    volume_factor = cylinder_volume

                # For each of the 3 logPart indices:
                for part_type in (0, 1, 2):
                    # For example, 0=Butt, 1=Middle, 2=Top
                    base_price = self._timber_prices[diam].price_for_log_part(part_type)
                    # Possibly do length correction:
                    length_corr = self._timber_prices.length_corrections.get_length_correction(diam, part_type, length_dm)
                    # If your length correction is absolute, add it:
                    # or if it's percentage, multiply it. This is just an example:
                    corrected_price = (base_price + length_corr) * 100.0  # SEK -> öre
                    # Multiply by volume factor:
                    price_ore = corrected_price * volume_factor
                    # We store it in our table. part_type+1 => 1..3
                    timber_value[diam][mod_i][part_type+1] = price_ore

        return timber_value

    def calculate_tree_value(
        self,
        diameter_cm: float,
        height_dm: float,
        min_diam_dead_wood: float,
        use_downgrading: bool = False,
        timber_price_factor: float = 1.0,
        pulp_wood_price_factor: float = 1.0,
        save_sections: bool = False
    ) -> BuckingResult:
        """
        Main DP logic to find the best set of cuts (modules) from stump to top
        that maximize total log/pulp/fuelwood/cull value. 
        `height_dm` is total tree height in decimeters.
        """

        # Build the taper object
        taper = TaperEdgrenNylinder(
            region=self._region,
            species=self._species,
            total_height_m=height_dm / 10.0,
            dbh_cm=diameter_cm
        )

        # 1) Precompute some stump heights, top heights, etc.
        (maxHeightButtLog, 
         maxHeightMiddleLog, 
         maxHeightTopLog, 
         HTOP, 
         HSTUB) = taper.get_heights(
            top_diam_for_timber = max(self._pricelist.TopDiameter, self._pricelist.PulpLogDiameter.Min),
            min_diam_buttlog    = self._minDiameterTimberLog,
            min_diam_middlelog  = self._minDiameterTimberLog,
            min_diam_toplog     = self._minDiameterTimberLog,
            max_height_quality1 = (self._timber_prices.max_height_quality1 
                                   if self._timber_prices else 0.0),
            max_height_quality2 = (self._timber_prices.max_height_quality2 
                                   if self._timber_prices else 0.0),
            max_height_quality3 = (self._timber_prices.max_height_quality3 
                                   if self._timber_prices else 0.0)
        )

        # 2) Convert the tree stem into discrete dm steps
        NMAX = 400
        total_length_dm = min(int((HTOP - HSTUB) * 10), NMAX)
        if total_length_dm <= 0:
            # Tree is too small
            return BuckingResult(
                total_value=0.0, top_proportion=1.0, dead_wood_proportion=1.0,
                high_stump_volume_proportion=1.0, high_stump_value_proportion=1.0,
                last_cut_relative_height=0.0, volume_per_quality=[0]*7, 
                timber_price_by_quality=[0]*7,
                vol_fub_5cm=0.0, vol_sk_ub=0.0,
            )

        # Build arrays of diameter and heights
        # h[i] is the height above stump
        # dh[i] is diameter (cm) at that height
        h  = [0.0]*(total_length_dm+1)
        dh = [0.0]*(total_length_dm+1)
        dead_wood_endpoint = 0
        vol_fub_endpoint   = 0
        timber_and_pulp_endpoint = 0

        for i in range(total_length_dm+1):
            h[i]  = HSTUB + i/10.0
            dh[i] = taper.get_diameter(h[i])
            if dh[i] >= min_diam_dead_wood:
                dead_wood_endpoint = i
            if dh[i] >= 5:
                vol_fub_endpoint = i
            if dh[i] >= self._pricelist.TopDiameter:
                timber_and_pulp_endpoint = i

        # For reporting: volumes up to 5 cm and up to actual top:
        vol_fub_5cm = taper.volume_under_bark(HSTUB, h[min(vol_fub_endpoint, total_length_dm)])
        vol_fub     = taper.volume_under_bark(HSTUB, h[vol_fub_endpoint])
        vol_sk_ub   = vol_fub
        if (height_dm/10.0) > h[vol_fub_endpoint]:
            vol_sk_ub += taper.volume_under_bark(h[vol_fub_endpoint], height_dm/10.0)

        vol_dead_wood = taper.volume_under_bark(h[0], h[dead_wood_endpoint])
        p_dead_wood   = (vol_dead_wood / vol_sk_ub) if vol_sk_ub > 0 else 0.0

        # Possibly handle high stump endpoints:
        high_stump_endpoint = 0
        if self._pricelist.HighStumpHeight > 0:
            for i in range(total_length_dm+1):
                if h[i] >= self._pricelist.HighStumpHeight:
                    high_stump_endpoint = i
                    break
        vol_high_stump = 0.0
        if high_stump_endpoint > 0:
            vol_high_stump = taper.volume_under_bark(h[0], h[high_stump_endpoint])
        p_volume_high_stump = (vol_high_stump / vol_sk_ub) if vol_sk_ub > 0 else 0.0
        if p_volume_high_stump > 1.0:
            p_volume_high_stump = 1.0

        # If not enough length for even the smallest module, no solution
        if total_length_dm < min(self._moduler):
            return BuckingResult(
                total_value=0.0, top_proportion=1.0, dead_wood_proportion=p_dead_wood,
                high_stump_volume_proportion=p_volume_high_stump, high_stump_value_proportion=0.0,
                last_cut_relative_height=0.0, volume_per_quality=[0]*7,
                timber_price_by_quality=[0]*7,
                vol_fub_5cm=vol_fub_5cm, vol_sk_ub=vol_sk_ub,
            )

        # Build a quick mapping of logPart based on height (like in your code):
        #   i <= maxHeightButtLog => Butt, etc.
        # Convert them to a discrete boundary in dm
        i_butt = int((maxHeightButtLog - HSTUB)*10 - 1e-7)
        i_mid  = int((maxHeightMiddleLog - HSTUB)*10 - 1e-7)
        i_top  = int((maxHeightTopLog - HSTUB)*10 - 1e-7)
        def get_quality(i_dm):
            if i_dm <= i_butt: return QualityType.ButtLog
            elif i_dm <= i_mid: return QualityType.MiddleLog
            elif i_dm <= i_top: return QualityType.TopLog
            else: return QualityType.Pulp

        # DP arrays: v[i] = best value up to i, vtimber[i] = best timber-only value up to i
        v       = [0.0]*(total_length_dm+1)
        vtimber = [0.0]*(total_length_dm+1)
        IP      = [0]*(total_length_dm+1)     # stores the last cut that leads to best solution
        kval    = [QualityType.Undefined]*(total_length_dm+1)

        # Avoid floating precision issues: store in öre but we keep them as float for now
        v[0]       = 1e-5  # to break ties
        vtimber[0] = 1e-5
        IP[0]      = 0

        cull_price     = self._pricelist.LogCullPrice * 100.0  # SEK->öre
        fuelwood_price = self._pricelist.FuelWoodPrice * 100.0

        # Main DP loop
        # We only need to do this up to total_length_dm
        # for IKAP from 0 to total_length_dm - min(module):
        for IKAP in range(total_length_dm+1):
            # A small optimization: if v[IKAP] <= 0 and IKAP>timber_and_pulp_endpoint => break
            if IKAP > timber_and_pulp_endpoint and v[IKAP] <= 0:
                continue

            # max length possible for next log
            lmax = 0
            # If we can still fit a timber log:
            if IKAP <= i_top:
                lmax = max(lmax, min(i_top - IKAP, self._maxLengthTimberLog))
            # If we can still fit a pulp log:
            lmax = max(lmax, min(total_length_dm - IKAP, self._maxLengthPulpwoodLog))

            for length_dm in self._moduler:
                if length_dm > lmax:
                    break
                lj = IKAP + length_dm
                if lj > total_length_dm:
                    break

                # Compute the volume under bark for that piece
                h1 = h[IKAP]
                h2 = h[lj]
                vol_log = taper.volume_under_bark(h1, h2)
                if vol_log <= 0:
                    continue

                # Decide if it is timber or pulp or cull
                new_value = 0.0
                new_value_timber = 0.0
                current_quality = QualityType.Undefined

                diam_lj = int(dh[lj])
                if (length_dm >= self._minLengthTimberLog and 
                    get_quality(lj) != QualityType.Pulp and 
                    diam_lj >= self._minDiameterTimberLog and 
                    diam_lj <= self._maxDiameterTimberLog+1 and
                    lj <= i_top):
                    # It's a timber log
                    current_quality = get_quality(lj)
                    log_part_enum   = self.quality_log_part[current_quality]
                    # We apply any downgrading proportions
                    prop_pulp = 0.0
                    prop_fuel = 0.0
                    prop_cull = 0.0
                    if use_downgrading and self._timber_prices is not None:
                        w = self._timber_prices.getTimberWeight(log_part_enum)
                        prop_pulp = w.pulpwoodPercentage / 100.0
                        prop_fuel = w.fuelWoodPercentage / 100.0
                        prop_cull = w.logCullPercentage / 100.0
                        # Adjust if sum>1
                        s = prop_pulp + prop_fuel + prop_cull
                        if s > 1.0:
                            # reduce cull first, or fuel, etc. 
                            # depends on your logic. We'll keep it simple:
                            prop_cull = max(0.0, 1.0 - (prop_pulp + prop_fuel))

                    dklass = min(diam_lj, self._maxDiameterTimberLog)
                    # base timber value from the 3D table, then scale by factors
                    base_timber_price_ore = self._timberValue[dklass][self._moduler.index(length_dm)][current_quality.value]
                    # Multiply by your factor
                    base_timber_price_ore *= timber_price_factor
                    if self._timber_prices and self._timber_prices.volume_type == "m3fub":
                        base_timber_price_ore *= vol_log

                    # Subtract the downgraded portion from the timber portion
                    timber_only = (1.0 - prop_pulp - prop_cull - prop_fuel) * base_timber_price_ore
                    if timber_only < 0: 
                        timber_only = 0
                        base_timber_price_ore = 0

                    # Gains from pulp/fuel/cull portion:
                    pulp_value_ore      = prop_pulp * pulp_wood_price_factor * self._mvarde * vol_log
                    cull_value_ore      = prop_cull * cull_price * vol_log
                    fuelwood_value_ore  = prop_fuel * fuelwood_price * vol_log

                    new_value        = v[IKAP] + timber_only + pulp_value_ore + cull_value_ore + fuelwood_value_ore
                    new_value_timber = vtimber[IKAP] + base_timber_price_ore

                elif (length_dm >= self._minLengthPulpwoodLog and length_dm <= self._maxLengthPulpwoodLog
                      and diam_lj >= self._pricelist.PulpLogDiameter.Min
                      and diam_lj <= self._pricelist.PulpLogDiameter.Max):
                    # It's a pulp log
                    current_quality = QualityType.Pulp
                    prop_cull = 0.0
                    prop_fuel = 0.0
                    if use_downgrading:
                        prop_cull = self._pricelist.getPulpWoodWasteProportion(self._species)
                        prop_fuel = self._pricelist.getPulpwoodFuelwoodProportion(self._species)
                        s = prop_cull + prop_fuel
                        if s > 1.0:
                            prop_cull = max(0.0, 1.0 - prop_fuel)
                    pulp_value_ore     = (1.0 - prop_cull - prop_fuel) * pulp_wood_price_factor * self._mvarde * vol_log
                    cull_value_ore     = prop_cull * cull_price * vol_log
                    fuelwood_value_ore = prop_fuel * fuelwood_price * vol_log
                    new_value = v[IKAP] + pulp_value_ore + cull_value_ore + fuelwood_value_ore
                    new_value_timber = vtimber[IKAP]

                elif length_dm >= 0.5 * self._minLengthPulpwoodLog:
                    # log is too short for pulp, so cull it
                    current_quality = QualityType.LogCull
                    cull_value_ore = cull_price * vol_log
                    new_value = v[IKAP] + cull_value_ore
                    new_value_timber = vtimber[IKAP]
                else:
                    # do nothing
                    continue

                # Update DP if better
                if new_value > v[lj]:
                    v[lj]       = new_value
                    vtimber[lj] = new_value_timber
                    IP[lj]      = IKAP
                    kval[lj]    = current_quality

        # Find best endpoint
        end_point = total_length_dm
        best_val  = v[end_point]
        for i in range(total_length_dm+1):
            if v[i] > best_val:
                best_val = v[i]
                end_point = i

        total_value_ore = best_val
        total_value     = total_value_ore / 100.0  # öre->SEK
        # proportion of top left uncut
        vol_top = taper.volume_under_bark(h[end_point], height_dm/10.0)
        p_top = (vol_top / vol_sk_ub) if vol_sk_ub>0 else 0.0
        last_cut_rel_height = (10.0 * h[end_point] / height_dm) if height_dm>0 else 1.0

        # proportion of value in high stump
        high_stump_value_proportion = 0.0
        if total_value>0 and high_stump_endpoint>0:
            high_stump_value_proportion = (v[high_stump_endpoint] / 100.0) / total_value

        # Reconstruct solution (volumes per quality, etc.)
        volume_per_quality = [0.0]*7  # indices match QualityType
        timber_price_by_quality = [0.0]*7
        vol_for_price_calc = [0.0]*7

        # optional: build a list of cut sections
        sections: List[CrossCutSection] = []
        cursor = end_point

        while cursor>0:
            prev = IP[cursor]
            q = kval[cursor]
            h1 = h[prev]
            h2 = h[cursor]
            vol_log = taper.volume_under_bark(h1, h2)
            value_section_ore = v[cursor] - v[prev]
            species = self._species

            # We can compute the proportions for pulp/fuel/cull if we want
            prop_cull = 0.0
            prop_fuel = 0.0
            prop_pulp = 0.0
            timber_prop = 0.0

            if q in (QualityType.ButtLog, QualityType.MiddleLog, QualityType.TopLog):
                # possibly apply downgrading
                part = self.quality_log_part[q]
                if use_downgrading and self._timber_prices is not None:
                    w = self._timber_prices.getTimberWeight(part)
                    prop_pulp = w.pulpwoodPercentage / 100.0
                    prop_fuel = w.fuelWoodPercentage / 100.0
                    prop_cull = w.logCullPercentage / 100.0
                    s = prop_pulp + prop_fuel + prop_cull
                    if s>1.0:
                        prop_cull = max(0.0, 1.0 - (prop_pulp + prop_fuel))
                # fraction used as good timber
                timber_prop = max(0.0, 1.0 - (prop_pulp + prop_fuel + prop_cull))
                volume_per_quality[q.value] += timber_prop*vol_log
                volume_per_quality[QualityType.Pulp.value] += prop_pulp*vol_log
                # get the timber price from DP
                # vtimber array: difference => we can do something like:
                timber_price_increment = (vtimber[cursor] - vtimber[prev]) / 100.0
                timber_price_by_quality[q.value] += timber_price_increment
                vol_for_price_calc[q.value] += vol_log
            elif q == QualityType.Pulp:
                if use_downgrading:
                    prop_cull = self._pricelist.getPulpWoodWasteProportion(species)
                    prop_fuel = self._pricelist.getPulpwoodFuelwoodProportion(species)
                    s = prop_cull + prop_fuel
                    if s>1.0:
                        prop_cull = max(0.0, 1.0 - prop_fuel)
                prop_pulp = max(0.0, 1.0 - (prop_cull + prop_fuel))
                volume_per_quality[QualityType.Pulp.value] += prop_pulp*vol_log

            if q == QualityType.LogCull:
                prop_cull = 1.0
            volume_per_quality[QualityType.LogCull.value]   += prop_cull*vol_log
            volume_per_quality[QualityType.Fuelwood.value]  += prop_fuel*vol_log

            if save_sections:
                sec = CrossCutSection(
                    start_point = prev,
                    end_point   = cursor,
                    volume      = vol_log,
                    top_diameter= dh[cursor],
                    value       = value_section_ore / 100.0,
                    species_group = species,
                    timber_proportion = timber_prop,
                    pulp_proportion   = prop_pulp,
                    cull_proportion   = prop_cull,
                    fuelwood_proportion=prop_fuel
                )
                sections.append(sec)

            cursor = prev

        # Convert average timber price from total lumps to per cubic meter
        for i in [QualityType.ButtLog, QualityType.MiddleLog, QualityType.TopLog]:
            iv = i.value
            if vol_for_price_calc[iv] > 0:
                timber_price_by_quality[iv] /= vol_for_price_calc[iv]

        return BuckingResult(
            total_value=total_value,
            top_proportion=p_top,
            dead_wood_proportion=p_dead_wood,
            high_stump_volume_proportion=p_volume_high_stump,
            high_stump_value_proportion=high_stump_value_proportion,
            last_cut_relative_height=last_cut_rel_height,
            volume_per_quality=volume_per_quality,
            timber_price_by_quality=timber_price_by_quality,
            vol_fub_5cm=vol_fub_5cm,
            vol_sk_ub=vol_sk_ub,
            sections=sections if save_sections else None
        )
