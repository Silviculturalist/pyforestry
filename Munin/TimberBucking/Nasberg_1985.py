# Näsberg (1985) branch-and-bound algorithm.
from Munin.Taper.Taper import Taper
from Munin.Timber.Timber import Timber
from Munin.TimberBucking.Bucker import Bucker
from Munin.PriceList.PriceList import *
from enum import IntEnum
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple, Type
import math
import matplotlib.pyplot as plt
import numpy as np

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
    species_group: str                    # The species group.
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
    DBH_cm:float                          # Diameter at breast height 1.3 m
    height_m:float                        # Total tree height.
    stump_height_m:float                  # Tree stump height.
    diameter_stump_cm:float               # Diameter at stump (cm).
    taperDiams_cm:List[float]             # Taper Diameters for plotting.
    taperHeights_m:List[float]            # Taper Heights for plotting.
    sections: Optional[List[CrossCutSection]] = None

    def plot(self):
        if self.sections:
            fig, ax = plt.subplots(figsize=(10, 6))

            # Prepare points for taper line plot (subtract stump height to align axis)
            taper_x = (self.taperHeights_m - self.stump_height_m) * 10
            taper_y = self.taperDiams_cm

            # Plot taper line
            ax.plot(taper_x, taper_y, linestyle='-', color='black', label='Taper')

            # Plot filled sections under taper curve
            for section in self.sections:
                # Mask taper points within each section range
                mask = (taper_x >= section.start_point) & (taper_x <= section.end_point)
                section_x = taper_x[mask]
                section_y = taper_y[mask]

                # If there are no points within the range, interpolate
                if len(section_x) == 0:
                    section_x = np.array([section.start_point, section.end_point])
                    section_y = np.interp(section_x, taper_x, taper_y)

                # Add start and end points explicitly for a smooth fill
                if section_x[0] > section.start_point:
                    start_y = np.interp(section.start_point, taper_x, taper_y)
                    section_x = np.insert(section_x, 0, section.start_point)
                    section_y = np.insert(section_y, 0, start_diameter := start_diameter if (start_diameter := np.interp(section.start_point, taper_x, taper_y)) > 0 else 0)
                if section_x[-1] < section.end_point:
                    section_x = np.append(section_x, section.end_point)
                    section_y = np.append(section_y, end_diameter := end_diameter if (end_diameter := np.interp(section.end_point, taper_x, taper_y)) > 0 else 0)

                # Fill area under taper curve for this section
                ax.fill_between(section_x, 0, section_y, alpha=0.3)

                # Add text info (length)
                length = (section.end_point - section.start_point) / 10
                midpoint = (section.start_point + section.end_point) / 2

                ax.text(midpoint, section.top_diameter / 2,
                        f"{section.top_diameter:.1f} cm\n{length:.2f} m\n Vol {section.volume*1000:.0f} $dm^3$\n {section.value:.0f} :-",
                        ha='center', va='center', fontsize=8)

            # Plot taper line (superfluous or hinder overflow of colored areas?)
            ax.plot(taper_x, taper_y, linestyle='-', color='black')

            # Vertical lines at section boundaries
            for section in self.sections:
                p = section.end_point
                ax.axvline(x=p, color='grey', linestyle='--', alpha=0.7)
                # Interpolate to get the y-value of the taper curve at x = p
                y_value = np.interp(p, taper_x, taper_y)

                # Add the label rotated 90 degrees
                ax.text(p-2, y_value + 0.5, f"{p}", ha='center', va='bottom', rotation=90, fontsize=9)


            # DBH marker
            ax.scatter((1.3 - self.stump_height_m) * 10, self.DBH_cm, color='red', label='Diameter @ 1.3 m')

            ax.set_xlabel('Distance from stump (dm)')
            ax.set_ylabel('Diameter (cm)')
            ax.set_title('Bucking Result Log Profile')
            ax.set_xlim(left=0) #Prevent automatic axis expansion
            ax.set_ylim(bottom=0) #Prevent automatic axis expansion

            
            leg = ax.legend(loc='upper right')
            leg.get_frame().set_alpha(1)  # Set the background transparency


            textstr = '\n'.join((
                f"Species Group: {self.species_group}",
                f"DBH: {self.DBH_cm:.1f} cm",
                f"Height: {self.height_m:.1f} m",
                f"Stump Height: {self.stump_height_m:.1f} m",
                f"Stump Diameter: {self.diameter_stump_cm:.1f} cm",
                f"Vol fub 5cm: {self.vol_fub_5cm:.3f} m³"
            ))

            # Get legend bounding box
            fig.canvas.draw()

            # Set your textbox position slightly offset from the legend to avoid overlap
            legend_x0, legend_y0, _ , _  = ax.get_legend().get_window_extent().transformed(ax.transAxes.inverted()).bounds

            # Set textbox slightly below legend
            textbox_x = legend_x0  # Slightly left of legend
            textbox_y = legend_y0 - 0.02  # Slightly below legend


            # Positioning text box in upper-right, slightly offset from legend
            ax.text(textbox_x, textbox_y, textstr, transform=ax.transAxes,
                    fontsize=9, verticalalignment='top', horizontalalignment='left',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=1))

            plt.tight_layout()
            plt.show()
        else:
            raise ValueError("No sections available for plotting.")


# ------------------------------------------------------------------------------
# Here's the main branch and bound bucking logic
# ------------------------------------------------------------------------------

class Nasberg_1985_BranchBound(Bucker):
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

    def __init__(self, timber: Timber, pricelist: Pricelist, taper_class: Optional[Type[Taper]] = None):
        if pricelist is None:
            raise ValueError("Pricelist must be set")

        self._pricelist = pricelist
        self._timber = timber

        self._taper_class = taper_class

        # If species is not in self._pricelist.Timber, skip or handle
        self._timber_prices = self._pricelist.Timber.get(timber.species, None)
        if not self._timber_prices:
            raise ValueError(f"Pricelist does not contain values for species '{timber.species}'. Available species: {list(pricelist.Timber.keys())}")


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
        self._mvarde = self._pricelist.Pulp.getPulpwoodPrice(timber.species) * 100  # SEK -> öre

        # Build the 'modules' array (possible log lengths) 
        self._moduler = self._build_modules()

        # Build a big table for timberValue[diam][module_index][qualityIndex]
        self._timberValue = self._build_timber_value_table()

    def _build_modules(self) -> List[int]:
        """
        Build the array of possible log lengths (the 'moduler') from the smallest pulp
        or timber length up to the max timber length, plus a sentinel large value.
        """
        min_log_length = min(self._minLengthPulpwoodLog*10, self._minLengthTimberLog*10)
        max_log_length = self._maxLengthTimberLog*10
        modules = []
        # Fill from min_log_length up to max_log_length

        for length_dm in range(int(min_log_length), int(max_log_length) + 1):
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
                if length_dm > self._maxLengthTimberLog*10 or length_dm < self._minLengthTimberLog*10:
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
        min_diam_dead_wood: float,
        use_downgrading: bool = False,
        timber_price_factor: float = 1.0,
        pulp_wood_price_factor: float = 1.0,
        save_sections: bool = False
    ) -> BuckingResult:
        """
        Main dynamic programming logic to find the best set of cuts (modules)
        from stump to top that maximize total log/pulp/fuelwood/cull value.
        """
        # --- Instantiate the taper using the provided taper class.
        taper = self._taper_class(self._timber)

        # Total tree height
        HTOT = self._timber.height_m
        # Use the tree's inherent stump height
        HSTUB = self._timber.stump_height_m

        #get diameter at stump. used only for plotting.
        DSTUB = taper.get_diameter_at_height(timber=self._timber,height_m=self._timber.stump_height_m)
        
        taperheights = np.linspace(0.01 * self._timber.height_m, self._timber.height_m - 0.01, 500)
        taperdiameters = np.array([taper.get_diameter_at_height(timber=self._timber,height_m=h) for h in taperheights])

        # --- Compute key diameters for inversion ---

        # Get the target diameter for the top cut: the larger of the TopDiameter and the minimum pulp log diameter
        top_diam = max(self._pricelist.TopDiameter, self._pricelist.PulpLogDiameter.Min)

        # --- Use inversion to determine key heights ---
        # Height at which the stem reaches the top diameter
        HTOP = taper.get_height_at_diameter(timber=self._timber,diameter=top_diam)

        # For quality logs, the minimum allowed diameter is the same for all qualities here
        # (you could change these if needed)
        heightQuality1 = taper.get_height_at_diameter(timber=self._timber,diameter=self._minDiameterTimberLog)
        heightQuality2 = taper.get_height_at_diameter(timber=self._timber,diameter=self._minDiameterTimberLog)
        heightQuality3 = taper.get_height_at_diameter(timber=self._timber,diameter=self._minDiameterTimberLog)

        # Cap these quality heights by the maximum allowed heights (from the pricelist)
        max_height_quality1 = self._timber_prices.max_height_quality1 if self._timber_prices else 0.0
        max_height_quality2 = self._timber_prices.max_height_quality2 if self._timber_prices else 0.0
        max_height_quality3 = self._timber_prices.max_height_quality3 if self._timber_prices else 0.0

        maxHeightButtLog   = min(max_height_quality1, heightQuality1)
        maxHeightMiddleLog = min(max_height_quality2, heightQuality2)
        maxHeightTopLog    = min(max_height_quality3, heightQuality3)

        # --- Discretize the tree stem ---
        # We work in decimeters from the stump up to the computed top (HTOP)
        NMAX = 400
        total_length_dm = min(int((HTOP - HSTUB) * 10), NMAX)
        if total_length_dm <= 0:
            # Tree is too small to yield any viable logs.
            return BuckingResult(
                total_value=0.0, top_proportion=1.0, dead_wood_proportion=1.0,
                high_stump_volume_proportion=1.0, high_stump_value_proportion=1.0,
                last_cut_relative_height=0.0, volume_per_quality=[0]*7,
                timber_price_by_quality=[0]*7,
                vol_fub_5cm=0.0, vol_sk_ub=0.0,
                DBH_cm=self._timber.diameter_cm,
                height_m=self._timber.height_m,
                stump_height_m=self._timber.stump_height_m,
                diameter_stump_cm=DSTUB, #plotting only
                taperDiams_cm=taperdiameters, #plotting only
                taperHeights_m=taperheights #plotting only
            )

        # Build arrays for height (h) and diameter (dh) along the stem.
        h  = [0.0] * (total_length_dm + 1)
        dh = [0.0] * (total_length_dm + 1)
        dead_wood_endpoint = 0
        vol_fub_endpoint = 0
        timber_and_pulp_endpoint = 0

        for i in range(total_length_dm + 1):
            # Height above stump in meters
            h[i] = HSTUB + i / 10.0
            # Diameter at that height (cm)
            dh[i] = taper.get_diameter_at_height(timber=self._timber,height_m=h[i])
            if dh[i] >= min_diam_dead_wood:
                dead_wood_endpoint = i
            if dh[i] >= 5:
                vol_fub_endpoint = i
            if dh[i] >= self._pricelist.TopDiameter:
                timber_and_pulp_endpoint = i

        # Compute volumes for reporting
        vol_fub_5cm = taper.volume_section(HSTUB, h[min(vol_fub_endpoint, total_length_dm)])
        vol_fub = taper.volume_section(HSTUB, h[vol_fub_endpoint])
        vol_sk_ub = vol_fub
        if HTOT > h[vol_fub_endpoint]:
            vol_sk_ub += taper.volume_section(h[vol_fub_endpoint], HTOT)
        vol_dead_wood = taper.volume_section(h[0], h[dead_wood_endpoint])
        p_dead_wood = (vol_dead_wood / vol_sk_ub) if vol_sk_ub > 0 else 0.0

        # Determine high stump endpoint, if applicable.
        high_stump_endpoint = 0
        if self._pricelist.HighStumpHeight*10 > 0:
            for i in range(total_length_dm + 1):
                if h[i] >= self._pricelist.HighStumpHeight*10:
                    high_stump_endpoint = i
                    break
        vol_high_stump = taper.volume_section(h[0], h[high_stump_endpoint]) if high_stump_endpoint > 0 else 0.0
        p_volume_high_stump = (vol_high_stump / vol_sk_ub) if vol_sk_ub > 0 else 0.0
        if p_volume_high_stump > 1.0:
            p_volume_high_stump = 1.0

        # If the stem is too short for even the smallest module, no solution.
        if total_length_dm < min(self._moduler):
            return BuckingResult(
                total_value=0.0, top_proportion=1.0, dead_wood_proportion=p_dead_wood,
                high_stump_volume_proportion=p_volume_high_stump, high_stump_value_proportion=0.0,
                last_cut_relative_height=0.0, volume_per_quality=[0]*7,
                timber_price_by_quality=[0]*7,
                vol_fub_5cm=vol_fub_5cm, vol_sk_ub=vol_sk_ub,
                DBH_cm=self._timber.diameter_cm,
                height_m=self._timber.height_m,
                stump_height_m=self._timber.stump_height_m,
                diameter_stump_cm=DSTUB,
                taperHeights_m=taperheights,
                taperDiams_cm=taperdiameters
            )

        # Map discrete boundaries for quality assignments using the computed quality heights.
        # Convert quality height limits to decimeter indices.
        i_butt = int((maxHeightButtLog - HSTUB) * 10 - 1e-7)
        i_mid  = int((maxHeightMiddleLog - HSTUB) * 10 - 1e-7)
        i_top  = int((maxHeightTopLog - HSTUB) * 10 - 1e-7)
        def get_quality(i_dm):
            if i_dm <= i_butt:
                return QualityType.ButtLog
            elif i_dm <= i_mid:
                return QualityType.MiddleLog
            elif i_dm <= i_top:
                return QualityType.TopLog
            else:
                return QualityType.Pulp

        # --- Dynamic Programming (DP) arrays initialization ---
        # v[i] = best overall value (in öre) up to i dm.
        # vtimber[i] = best timber-only value (in öre) up to i dm.
        v       = [0.0] * (total_length_dm + 1)
        vtimber = [0.0] * (total_length_dm + 1)
        IP      = [0] * (total_length_dm + 1)    # Backpointer for reconstruction.
        kval    = [QualityType.Undefined] * (total_length_dm + 1)

        # Use a small positive number at the start to break ties.
        v[0] = 1e-5
        vtimber[0] = 1e-5
        IP[0] = 0

        cull_price = self._pricelist.LogCullPrice * 100.0   # SEK -> öre
        fuelwood_price = self._pricelist.FuelWoodPrice * 100.0

        # --- Main DP Loop ---
        for IKAP in range(total_length_dm + 1):
            # Optimization: if we have passed the timber/pulp endpoint and no value has been accumulated, skip.
            if IKAP > timber_and_pulp_endpoint and v[IKAP] <= 0:
                continue

            # Determine the maximum module length possible from this cut.
            lmax = 0
            if IKAP <= i_top:
                lmax = max(lmax, min(i_top - IKAP, self._maxLengthTimberLog*10))
            lmax = max(lmax, min(total_length_dm - IKAP, self._maxLengthPulpwoodLog*10))

            for length_dm in self._moduler:
                if length_dm > lmax:
                    break
                lj = IKAP + length_dm
                if lj > total_length_dm:
                    break

                # Compute the volume (under bark) for the piece from h[IKAP] to h[lj].
                h1 = h[IKAP]
                h2 = h[lj]
                vol_log = taper.volume_section(h1, h2)
                if vol_log <= 0:
                    continue

                # Decide the product type (timber log, pulp log, or cull) for this section.
                new_value = 0.0
                new_value_timber = 0.0
                current_quality = QualityType.Undefined

                diam_lj = int(dh[lj])
                if (length_dm >= self._minLengthTimberLog*10 and 
                    get_quality(lj) != QualityType.Pulp and 
                    diam_lj >= self._minDiameterTimberLog*10 and 
                    diam_lj <= self._maxDiameterTimberLog*10 + 1 and
                    lj <= i_top):
                    # Timber log branch.
                    current_quality = get_quality(lj)
                    log_part_enum = self.quality_log_part[current_quality]
                    prop_pulp = 0.0
                    prop_fuel = 0.0
                    prop_cull = 0.0
                    if use_downgrading and self._timber_prices is not None:
                        w = self._timber_prices.getTimberWeight(log_part_enum)
                        prop_pulp = w.pulpwoodPercentage / 100.0
                        prop_fuel = w.fuelWoodPercentage / 100.0
                        prop_cull = w.logCullPercentage / 100.0
                        s = prop_pulp + prop_fuel + prop_cull
                        if s > 1.0:
                            prop_cull = max(0.0, 1.0 - (prop_pulp + prop_fuel))
                    dklass = min(diam_lj, self._maxDiameterTimberLog)
                    base_timber_price_ore = self._timberValue[dklass][self._moduler.index(length_dm)][current_quality.value]
                    base_timber_price_ore *= timber_price_factor
                    if self._timber_prices and self._timber_prices.volume_type == "m3fub":
                        base_timber_price_ore *= vol_log

                    timber_only = (1.0 - prop_pulp - prop_cull - prop_fuel) * base_timber_price_ore
                    if timber_only < 0:
                        timber_only = 0
                        base_timber_price_ore = 0

                    pulp_value_ore     = prop_pulp * pulp_wood_price_factor * self._mvarde * vol_log
                    cull_value_ore     = prop_cull * cull_price * vol_log
                    fuelwood_value_ore = prop_fuel * fuelwood_price * vol_log

                    new_value = v[IKAP] + timber_only + pulp_value_ore + cull_value_ore + fuelwood_value_ore
                    new_value_timber = vtimber[IKAP] + base_timber_price_ore

                elif (length_dm >= self._minLengthPulpwoodLog*10 and length_dm <= self._maxLengthPulpwoodLog*10 and
                      diam_lj >= self._pricelist.PulpLogDiameter.Min and 
                      diam_lj <= self._pricelist.PulpLogDiameter.Max):
                    # Pulp log branch.
                    current_quality = QualityType.Pulp
                    prop_cull = 0.0
                    prop_fuel = 0.0
                    if use_downgrading:
                        prop_cull = self._pricelist.getPulpWoodWasteProportion(self._timber.species)
                        prop_fuel = self._pricelist.getPulpwoodFuelwoodProportion(self._timber.species)
                        s = prop_cull + prop_fuel
                        if s > 1.0:
                            prop_cull = max(0.0, 1.0 - prop_fuel)
                    pulp_value_ore     = (1.0 - prop_cull - prop_fuel) * pulp_wood_price_factor * self._mvarde * vol_log
                    cull_value_ore     = prop_cull * cull_price * vol_log
                    fuelwood_value_ore = prop_fuel * fuelwood_price * vol_log
                    new_value = v[IKAP] + pulp_value_ore + cull_value_ore + fuelwood_value_ore
                    new_value_timber = vtimber[IKAP]

                elif length_dm >= 0.5 * self._minLengthPulpwoodLog*10:
                    # Log is too short for pulp: classify as cull.
                    current_quality = QualityType.LogCull
                    cull_value_ore = cull_price * vol_log
                    new_value = v[IKAP] + cull_value_ore
                    new_value_timber = vtimber[IKAP]
                else:
                    continue

                # Update DP if the new value is better.
                if new_value > v[lj]:
                    v[lj] = new_value
                    vtimber[lj] = new_value_timber
                    IP[lj] = IKAP
                    kval[lj] = current_quality

        # --- Find the best endpoint ---
        end_point = total_length_dm
        best_val = v[end_point]
        for i in range(total_length_dm + 1):
            if v[i] > best_val:
                best_val = v[i]
                end_point = i

        total_value_ore = best_val
        total_value = total_value_ore / 100.0  # Convert from öre to SEK
        vol_top = taper.volume_section(h[end_point], HTOT)
        p_top = (vol_top / vol_sk_ub) if vol_sk_ub > 0 else 0.0
        last_cut_rel_height = (10.0 * h[end_point] / HTOT) if HTOT > 0 else 1.0

        high_stump_value_proportion = 0.0
        if total_value > 0 and high_stump_endpoint > 0:
            high_stump_value_proportion = (v[high_stump_endpoint] / 100.0) / total_value

        # --- Reconstruct the solution (cut sections, volume, quality breakdown, etc.) ---
        volume_per_quality = [0.0] * 7  # Indices correspond to QualityType enum values.
        timber_price_by_quality = [0.0] * 7
        vol_for_price_calc = [0.0] * 7
        sections: List[CrossCutSection] = []
        cursor = end_point

        while cursor > 0:
            prev = IP[cursor]
            q = kval[cursor]
            h1 = h[prev]
            h2 = h[cursor]
            vol_log = taper.volume_section(h1, h2)
            value_section_ore = v[cursor] - v[prev]
            species = self._timber.species

            prop_cull = 0.0
            prop_fuel = 0.0
            prop_pulp = 0.0
            timber_prop = 0.0

            if q in (QualityType.ButtLog, QualityType.MiddleLog, QualityType.TopLog):
                part = self.quality_log_part[q]
                if use_downgrading and self._timber_prices is not None:
                    w = self._timber_prices.getTimberWeight(part)
                    prop_pulp = w.pulpwoodPercentage / 100.0
                    prop_fuel = w.fuelWoodPercentage / 100.0
                    prop_cull = w.logCullPercentage / 100.0
                    s = prop_pulp + prop_fuel + prop_cull
                    if s > 1.0:
                        prop_cull = max(0.0, 1.0 - (prop_pulp + prop_fuel))
                timber_prop = max(0.0, 1.0 - (prop_pulp + prop_fuel + prop_cull))
                volume_per_quality[q.value] += timber_prop * vol_log
                volume_per_quality[QualityType.Pulp.value] += prop_pulp * vol_log
                timber_price_increment = (vtimber[cursor] - vtimber[prev]) / 100.0
                timber_price_by_quality[q.value] += timber_price_increment
                vol_for_price_calc[q.value] += vol_log
            elif q == QualityType.Pulp:
                if use_downgrading:
                    prop_cull = self._pricelist.getPulpWoodWasteProportion(species)
                    prop_fuel = self._pricelist.getPulpwoodFuelwoodProportion(species)
                    s = prop_cull + prop_fuel
                    if s > 1.0:
                        prop_cull = max(0.0, 1.0 - prop_fuel)
                prop_pulp = max(0.0, 1.0 - (prop_cull + prop_fuel))
                volume_per_quality[QualityType.Pulp.value] += prop_pulp * vol_log

            if q == QualityType.LogCull:
                prop_cull = 1.0
            volume_per_quality[QualityType.LogCull.value] += prop_cull * vol_log
            volume_per_quality[QualityType.Fuelwood.value] += prop_fuel * vol_log

            if save_sections:
                sec = CrossCutSection(
                    start_point=prev,
                    end_point=cursor,
                    volume=vol_log,
                    top_diameter=dh[cursor],
                    value=value_section_ore / 100.0,
                    species_group=species,
                    timber_proportion=timber_prop,
                    pulp_proportion=prop_pulp,
                    cull_proportion=prop_cull,
                    fuelwood_proportion=prop_fuel
                )
                sections.append(sec)

            cursor = prev

        # Convert average timber price to per cubic meter for each quality.
        for i in [QualityType.ButtLog, QualityType.MiddleLog, QualityType.TopLog]:
            iv = i.value
            if vol_for_price_calc[iv] > 0:
                timber_price_by_quality[iv] /= vol_for_price_calc[iv]

        return BuckingResult(
            species_group=species,
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
            DBH_cm=self._timber.diameter_cm,
            height_m=self._timber.height_m,
            stump_height_m=self._timber.stump_height_m,
            diameter_stump_cm=DSTUB,#plotting only
            taperDiams_cm=taperdiameters,#plotting only
            taperHeights_m=taperheights, #plotting only
            sections=sections if save_sections else None
        )