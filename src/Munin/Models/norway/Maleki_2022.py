from __future__ import annotations

import numpy as np
import math
from typing import Type

from Munin.Helpers.Primitives import (
    StandBasalArea,
    AgeMeasurement,
    Age,
    Stems,
    SiteIndexValue,
    QuadraticMeanDiameter,
    StandVolume
)

# Assuming NorwaySpecies are defined like:
# NorwaySpecies.PICEA_ABIES, NorwaySpecies.PINUS_SYLVESTRIS, NorwaySpecies.BROADLEAVES
from Munin.Helpers.TreeSpecies import TreeName, TreeSpecies

# AGE IS AGE.TOTAL IN THIS MODEL

class Maleki2022ModelNorway:
    """
    Implements stand-level models for Norway based on Maleki et al. (2022).

    Provides access to functions via species-specific interfaces:
    - `model.picea_abies.<function>(...)`
    - `model.pinus_sylvestris.<function>(...)`
    - `model.broadleaves.<function>(...)`

    Reference:
        Maleki, K., Sharma, R. P., & Tveite, B. (2022). Modelling stand
        survival, ingrowth and yield in Norway. Forest Ecology and
        Management, 505, 119931.
        https://doi.org/10.1016/j.foreco.2021.119931

    Warnings:
        - Survival/Density functions: Verify formula structure/signs against paper.
        - BA Projection functions: Verify formula structure/coefficients against paper.
        - Ingrowth Probability (Broadleaves): Verify interaction term coefficient.
    """

    # ================================================
    # Species Interface Classes
    # ================================================
    class _NorwaySpruceInterface:
        """Interface for Maleki (2022) Norway Spruce functions."""
        species = TreeSpecies.Sweden.picea_abies

        def get_StandVolume(self, dominant_height: float, basal_area: StandBasalArea, age: AgeMeasurement) -> StandVolume:
            """ Calculates stand volume per hectare (m3/ha) for Norway Spruce. """
            return Maleki2022ModelNorway._StandVolume_norway_spruce(dominant_height, basal_area, age)

        def get_stem_survival(self, age1: AgeMeasurement, age2: AgeMeasurement, stems1: Stems, si_h40: SiteIndexValue) -> Stems:
            """ Predicts stem survival for Norway Spruce. """
            return Maleki2022ModelNorway._stem_survival_norway_spruce(age1, age2, stems1, si_h40)

        def get_stem_density(self, age1: AgeMeasurement, age2: AgeMeasurement, stems1: Stems, si_h40: SiteIndexValue) -> Stems:
            """ Predicts stem density for Norway Spruce (Warning: Verify formula source/coeffs). """
            return Maleki2022ModelNorway._stem_density_norway_spruce(age1, age2, stems1, si_h40)

        def get_ingrowth_count(self, basal_area: StandBasalArea) -> float:
             """ Predicts ingrowth count per 5 years for Norway Spruce. """
             return Maleki2022ModelNorway._ingrowth_count_norway_spruce(basal_area)

        def get_ingrowth_probability(self, qmd: QuadraticMeanDiameter, stems: Stems) -> float:
             """ Predicts ingrowth probability per 5 years for Norway Spruce. """
             return Maleki2022ModelNorway._ingrowth_probability_norway_spruce(qmd, stems)

        def get_height_trajectory(self, dominant_height1: float, age1: AgeMeasurement, age2: AgeMeasurement) -> float:
             """ Predicts dominant height trajectory for Norway Spruce. """
             return Maleki2022ModelNorway._height_trajectory_norway_spruce(dominant_height1, age1, age2)

        def get_basal_area_projection(self, ba1: StandBasalArea, age1: AgeMeasurement, age2: AgeMeasurement, si_h40: SiteIndexValue, stems1: Stems, stems2: Stems) -> StandBasalArea:
             """ Predicts basal area projection for Norway Spruce (Warning: Verify formula source/coeffs). """
             return Maleki2022ModelNorway._basal_area_projection_norway_spruce(ba1, age1, age2, si_h40, stems1, stems2)


    class _ScotsPineInterface:
        """Interface for Maleki (2022) Scots Pine functions."""
        species = TreeSpecies.Sweden.pinus_sylvestris

        def get_StandVolume(self, dominant_height: float, basal_area: StandBasalArea, age: AgeMeasurement) -> StandVolume:
            """ Calculates stand volume per hectare (m3/ha) for Scots Pine. """
            return Maleki2022ModelNorway._StandVolume_scots_pine(dominant_height, basal_area, age)

        def get_stem_survival(self, age1: AgeMeasurement, age2: AgeMeasurement, stems1: Stems, si_h40: SiteIndexValue) -> Stems:
             """ Predicts stem survival for Scots Pine. """
             return Maleki2022ModelNorway._stem_survival_scots_pine(age1, age2, stems1, si_h40)

        def get_stem_density(self, age1: AgeMeasurement, age2: AgeMeasurement, stems1: Stems, si_h40: SiteIndexValue) -> Stems:
             """ Predicts stem density for Scots Pine (Warning: Verify formula source/coeffs). """
             return Maleki2022ModelNorway._stem_density_scots_pine(age1, age2, stems1, si_h40)

        def get_ingrowth_count(self, basal_area: StandBasalArea) -> float:
             """ Predicts ingrowth count per 5 years for Scots Pine. """
             return Maleki2022ModelNorway._ingrowth_count_scots_pine(basal_area)

        def get_ingrowth_probability(self, qmd: QuadraticMeanDiameter, stems: Stems) -> float:
             """ Predicts ingrowth probability per 5 years for Scots Pine. """
             return Maleki2022ModelNorway._ingrowth_probability_scots_pine(qmd, stems)

        def get_height_trajectory(self, dominant_height1: float, age1: AgeMeasurement, age2: AgeMeasurement) -> float:
             """ Predicts dominant height trajectory for Scots Pine. """
             return Maleki2022ModelNorway._height_trajectory_scots_pine(dominant_height1, age1, age2)

        def get_basal_area_projection(self, ba1: StandBasalArea, age1: AgeMeasurement, age2: AgeMeasurement, si_h40: SiteIndexValue, stems1: Stems, stems2: Stems) -> StandBasalArea:
             """ Predicts basal area projection for Scots Pine (Warning: Verify formula source/coeffs). """
             return Maleki2022ModelNorway._basal_area_projection_scots_pine(ba1, age1, age2, si_h40, stems1, stems2)

    class _BroadleavesInterface:
        """Interface for Maleki (2022) Broadleaves functions."""
        # Assuming NorwaySpecies.BROADLEAVES is a set or tuple of TreeName
        species = TreeSpecies.Sweden.Broadleaves

        def get_StandVolume(self, dominant_height: float, basal_area: StandBasalArea, age: AgeMeasurement) -> StandVolume:
            """ Calculates stand volume per hectare (m3/ha) for Broadleaves. """
            return Maleki2022ModelNorway._StandVolume_broadleaves(dominant_height, basal_area, age)

        def get_stem_survival(self, age1: AgeMeasurement, age2: AgeMeasurement, stems1: Stems, si_h40: SiteIndexValue) -> Stems:
             """ Predicts stem survival for Broadleaves. """
             return Maleki2022ModelNorway._stem_survival_broadleaves(age1, age2, stems1, si_h40)

        def get_stem_density(self, age1: AgeMeasurement, age2: AgeMeasurement, stems1: Stems, si_h40: SiteIndexValue) -> Stems:
             """ Predicts stem density for Broadleaves (Warning: Verify formula source/coeffs). """
             return Maleki2022ModelNorway._stem_density_broadleaves(age1, age2, stems1, si_h40)

        def get_ingrowth_count(self, qmd: QuadraticMeanDiameter) -> float:
             """ Predicts ingrowth count per 5 years for Broadleaves (Note: uses QMD). """
             return Maleki2022ModelNorway._ingrowth_count_broadleaves(qmd)

        def get_ingrowth_probability(self, qmd: QuadraticMeanDiameter, stems: Stems) -> float:
             """ Predicts ingrowth probability per 5 years for Broadleaves (Warning: Verify interaction coefficient). """
             return Maleki2022ModelNorway._ingrowth_probability_broadleaves(qmd, stems)

        def get_height_trajectory(self, dominant_height1: float, age1: AgeMeasurement, age2: AgeMeasurement) -> float:
             """ Predicts dominant height trajectory for Broadleaves. """
             return Maleki2022ModelNorway._height_trajectory_broadleaves(dominant_height1, age1, age2)

        def get_basal_area_projection(self, ba1: StandBasalArea, age1: AgeMeasurement, age2: AgeMeasurement, si_h40: SiteIndexValue, stems1: Stems, stems2: Stems) -> StandBasalArea:
             """ Predicts basal area projection for Broadleaves (Warning: Verify formula source/coeffs). """
             return Maleki2022ModelNorway._basal_area_projection_broadleaves(ba1, age1, age2, si_h40, stems1, stems2)

    # ================================================
    # Static Implementation Functions (Core Logic)
    # ================================================

    # --- Volume Functions ---
    @staticmethod
    def _StandVolume_norway_spruce(dominant_height: float, basal_area: StandBasalArea, age: AgeMeasurement) -> StandVolume:
        # ... (Implementation as before) ...
        b1 = 0.2134; b2 = 1.0779; b3 = 1.0498; b4 = 2.5148
        dh = float(dominant_height); ba = float(basal_area); a = float(age)
        return StandVolume(b1 * (dh**b2) * (ba**b3) * np.exp(b4 / a))

    @staticmethod
    def _StandVolume_scots_pine(dominant_height: float, basal_area: StandBasalArea, age: AgeMeasurement) -> StandVolume:
        # ... (Implementation as before) ...
        b1 = 0.4830; b2 = 0.9128; b3 = 0.9913; b4 = -1.6105
        dh = float(dominant_height); ba = float(basal_area); a = float(age)
        return StandVolume(b1 * (dh**b2) * (ba**b3) * np.exp(b4 / a))

    @staticmethod
    def _StandVolume_broadleaves(dominant_height: float, basal_area: StandBasalArea, age: AgeMeasurement) -> StandVolume:
        # ... (Implementation as before) ...
        b1 = 0.5564; b2 = 0.7667; b3 = 1.0318; b4 = -1.5229
        dh = float(dominant_height); ba = float(basal_area); a = float(age)
        return StandVolume(b1 * (dh**b2) * (ba**b3) * np.exp(b4 / a))

    # --- Stem Survival Functions ---
    @staticmethod
    def _stem_survival_norway_spruce(age1: AgeMeasurement, age2: AgeMeasurement, stems1: Stems, si_h40: SiteIndexValue) -> Stems:
        # ... (Implementation as before, including checks and warnings) ...
        b1 = 0.6159; b2 = -0.0312; b3 = 1.0602
        a1=float(age1); a2=float(age2); n1=float(stems1); si=float(si_h40)
        if a1 <= 0: return Stems(0)
        if age2 < age1: raise ValueError("age2 >= age1 required")
        if age1 == age2: return stems1
        # WARNING: Verify sign in exponent vs paper Eq. 2
        n2 = n1 * ((a2 / a1)**b1) * np.exp(b2 * (si / 1000) * ((a2 - a1)**b3))
        return Stems(max(0, n2))

    @staticmethod
    def _stem_survival_scots_pine(age1: AgeMeasurement, age2: AgeMeasurement, stems1: Stems, si_h40: SiteIndexValue) -> Stems:
        # ... (Implementation as before, including checks and warnings) ...
        b1 = 0.17881; b2 = -0.0308; b3 = 0.0695
        a1=float(age1); a2=float(age2); n1=float(stems1); si=float(si_h40)
        if a1 <= 0: return Stems(0)
        if age2 < age1: raise ValueError("age2 >= age1 required")
        if age1 == age2: return stems1
        # WARNING: Verify sign in exponent vs paper Eq. 2 & coefficients b1, b3
        n2 = n1 * ((a2 / a1)**b1) * np.exp(b2 * (si / 1000) * ((a2 - a1)**b3))
        return Stems(max(0, n2))

    @staticmethod
    def _stem_survival_broadleaves(age1: AgeMeasurement, age2: AgeMeasurement, stems1: Stems, si_h40: SiteIndexValue) -> Stems:
        # ... (Implementation as before, including checks and warnings) ...
        b1 = 0.4592; b2 = -0.0534; b3 = 0.9466
        a1=float(age1); a2=float(age2); n1=float(stems1); si=float(si_h40)
        if a1 <= 0: return Stems(0)
        if age2 < age1: raise ValueError("age2 >= age1 required")
        if age1 == age2: return stems1
        # WARNING: Verify sign in exponent vs paper Eq. 2
        n2 = n1 * ((a2 / a1)**b1) * np.exp(b2 * (si / 1000) * ((a2 - a1)**b3))
        return Stems(max(0, n2))

    # --- Stem Density Functions ---
    # WARNING: Verify source/formula for these density functions
    @staticmethod
    def _stem_density_norway_spruce(age1: AgeMeasurement, age2: AgeMeasurement, stems1: Stems, si_h40: SiteIndexValue) -> Stems:
        # ... (Implementation as before) ...
        b1 = 1.5124; b2 = -0.00654; b3 = 1.4747
        a1=float(age1); a2=float(age2); n1=float(stems1); si=float(si_h40)
        if a1 <= 0: return Stems(0)
        if age2 < age1: raise ValueError("age2 >= age1 required")
        if age1 == age2: return stems1
        n2 = n1*((a2/a1)**b1)*np.exp(b2*(si/1000)*((a2-a1)**b3))
        return Stems(max(0, n2))

    @staticmethod
    def _stem_density_scots_pine(age1: AgeMeasurement, age2: AgeMeasurement, stems1: Stems, si_h40: SiteIndexValue) -> Stems:
        # ... (Implementation as before, note positive b2) ...
        b1 = 0.6676; b2 = 0.0039; b3 = 0.8662
        a1=float(age1); a2=float(age2); n1=float(stems1); si=float(si_h40)
        if a1 <= 0: return Stems(0)
        if age2 < age1: raise ValueError("age2 >= age1 required")
        if age1 == age2: return stems1
        n2 = n1*((a2/a1)**b1)*np.exp(b2*(si/1000)*((a2-a1)**b3))
        return Stems(max(0, n2))

    @staticmethod
    def _stem_density_broadleaves(age1: AgeMeasurement, age2: AgeMeasurement, stems1: Stems, si_h40: SiteIndexValue) -> Stems:
        # ... (Implementation as before) ...
        b1 = 1.1395; b2 = -0.0162; b3 = 1.2682
        a1=float(age1); a2=float(age2); n1=float(stems1); si=float(si_h40)
        if a1 <= 0: return Stems(0)
        if age2 < age1: raise ValueError("age2 >= age1 required")
        if age1 == age2: return stems1
        n2 = n1*((a2/a1)**b1)*np.exp(b2*(si/1000)*((a2-a1)**b3))
        return Stems(max(0, n2))

    # --- Ingrowth Count Functions ---
    @staticmethod
    def _ingrowth_count_norway_spruce(basal_area: StandBasalArea) -> float:
        # ... (Implementation as before) ...
        ba = float(basal_area)
        ln_ingrowth_plus_1 = 2.2919 - 0.3780 * np.sqrt(ba)
        return max(0, np.exp(ln_ingrowth_plus_1) - 1)

    @staticmethod
    def _ingrowth_count_scots_pine(basal_area: StandBasalArea) -> float:
        # ... (Implementation as before) ...
        ba = float(basal_area)
        ln_ingrowth_plus_1 = 0.5264 - 0.0889 * np.sqrt(ba)
        return max(0, np.exp(ln_ingrowth_plus_1) - 1)

    @staticmethod
    def _ingrowth_count_broadleaves(qmd: QuadraticMeanDiameter) -> float:
        # ... (Implementation as before) ...
        q = float(qmd)
        ln_ingrowth_plus_1 = 3.0411 - 0.6213 * math.sqrt(q) # Using math.sqrt as original
        return max(0, np.exp(ln_ingrowth_plus_1) - 1)

    # --- Ingrowth Probability Functions ---
    @staticmethod
    def _ingrowth_probability_norway_spruce(qmd: QuadraticMeanDiameter, stems: Stems) -> float:
        # ... (Implementation as before) ...
        q = float(qmd); n = float(stems)
        if q < 0 or n < 0: return 0.0
        logit = 13.6210 - 3.0328*np.sqrt(q) - 0.6868*np.sqrt(n) + 0.1483*np.sqrt(q)*np.sqrt(n)
        prob = 1 / (1 + np.exp(-logit))
        return prob

    @staticmethod
    def _ingrowth_probability_scots_pine(qmd: QuadraticMeanDiameter, stems: Stems) -> float:
        # ... (Implementation as before) ...
        q = float(qmd); n = float(stems)
        if q < 0 or n < 0: return 0.0
        logit = 7.6489 - 1.2823*np.sqrt(q) - 0.5173*np.sqrt(n) + 0.0915*np.sqrt(q)*np.sqrt(n)
        prob = 1 / (1 + np.exp(-logit))
        return prob

    @staticmethod
    def _ingrowth_probability_broadleaves(qmd: QuadraticMeanDiameter, stems: Stems) -> float:
        # ... (Implementation as before) ...
        q = float(qmd); n = float(stems)
        if q < 0 or n < 0: return 0.0
        # WARNING: Verify interaction term 0.5688 vs paper 0.0569
        logit = 7.7009 - 1.6373*np.sqrt(q) - 0.3349*np.sqrt(n) + 0.5688*np.sqrt(q)*np.sqrt(n)
        prob = 1 / (1 + np.exp(-logit))
        return prob

    # --- Dominant Height Trajectory Functions ---
    @staticmethod
    def _height_trajectory_norway_spruce(dominant_height1: float, age1: AgeMeasurement, age2: AgeMeasurement) -> float:
        # ... (Implementation as before, including checks) ...
        b1 = 39.5764; b2 = -396.3146; b3 = 1.6770
        h1=float(dominant_height1); a1=float(age1); a2=float(age2)
        if a1 <= 0: return dominant_height1 if a2 > 0 else float(0)
        if age1 == age2: return dominant_height1
        phi_num = h1 - b1
        phi_den = 1 - (b2 / h1) * (a1**-b3)
        if abs(phi_den) < 1e-9: return dominant_height1 # Or raise error
        phi = phi_num / phi_den
        h2_den = 1 + (b2/phi) * (a2**-b3)
        if abs(h2_den) < 1e-9: return float(b1)
        h2 = b1 + phi / h2_den
        return float(max(0, h2))

    @staticmethod
    def _height_trajectory_scots_pine(dominant_height1: float, age1: AgeMeasurement, age2: AgeMeasurement) -> float:
        # ... (Implementation as before, including checks) ...
        b1 = 43.6698; b2 = -24.9476; b3 = 1.2967
        h1=float(dominant_height1); a1=float(age1); a2=float(age2)
        if a1 <= 0: return dominant_height1 if a2 > 0 else float(0)
        if age1 == age2: return dominant_height1
        phi_num = h1 - b1
        phi_den = 1 - (b2 / h1) * (a1**-b3)
        if abs(phi_den) < 1e-9: return dominant_height1
        phi = phi_num / phi_den
        h2_den = 1 + (b2/phi) * (a2**-b3)
        if abs(h2_den) < 1e-9: return float(b1)
        h2 = b1 + phi / h2_den
        return float(max(0, h2))

    @staticmethod
    def _height_trajectory_broadleaves(dominant_height1: float, age1: AgeMeasurement, age2: AgeMeasurement) -> float:
        # ... (Implementation as before, including checks) ...
        b1 = 36.6501; b2 = -11.8787; b3 = 1.0643
        h1=float(dominant_height1); a1=float(age1); a2=float(age2)
        if a1 <= 0: return dominant_height1 if a2 > 0 else float(0)
        if age1 == age2: return dominant_height1
        phi_num = h1 - b1
        phi_den = 1 - (b2 / h1) * (a1**-b3)
        if abs(phi_den) < 1e-9: return dominant_height1
        phi = phi_num / phi_den
        h2_den = 1 + (b2/phi) * (a2**-b3)
        if abs(h2_den) < 1e-9: return float(b1)
        h2 = b1 + phi / h2_den
        return float(max(0, h2))

    # --- Basal Area Projection Functions ---
    # WARNING: Verify formula source/structure/coefficients for BA projection
    @staticmethod
    def _basal_area_projection_norway_spruce(ba1: StandBasalArea, age1: AgeMeasurement, age2: AgeMeasurement, si_h40: SiteIndexValue, stems1: Stems, stems2: Stems) -> StandBasalArea:
        # ... (Implementation as before, including checks and warnings) ...
        b1 = 0.4159; b2 = 2.0096; b3 = 0.7521 # Verify coeffs/meaning vs paper
        h1 = Maleki2022ModelNorway._height_trajectory_norway_spruce(float(si_h40), AgeMeasurement(40, Age.TOTAL.value), age1)
        h2 = Maleki2022ModelNorway._height_trajectory_norway_spruce(float(si_h40), AgeMeasurement(40, Age.TOTAL.value), age2)
        ba_1=float(ba1); stems_1=float(stems1); stems_2=float(stems2); h_1=float(h1); h_2=float(h2)
        if h_2 <= 0 or h_1 <=0: return StandBasalArea(0)
        if stems_1 <= 0: return StandBasalArea(0)
        if age1 == age2: return ba1
        ratio_h = h_1 / h_2; ratio_n = stems_2 / stems_1
        # WARNING: Using snippet formula - verify!
        ba_2 = (ba_1**(ratio_h**b1)) * np.exp((b2**ratio_n) * b2 * (1 - ratio_h**b3))
        return StandBasalArea(max(0, ba_2))

    @staticmethod
    def _basal_area_projection_scots_pine(ba1: StandBasalArea, age1: AgeMeasurement, age2: AgeMeasurement, si_h40: SiteIndexValue, stems1: Stems, stems2: Stems) -> StandBasalArea:
        # ... (Implementation as before, including checks and warnings) ...
        b1 = 0.5381; b2 = 0.96900; b3 = 4.1579 # Verify coeffs/meaning vs paper
        h1 = Maleki2022ModelNorway._height_trajectory_scots_pine(float(si_h40), AgeMeasurement(40, Age.TOTAL.value), age1) 
        h2 = Maleki2022ModelNorway._height_trajectory_scots_pine(float(si_h40), AgeMeasurement(40, Age.TOTAL.value), age2) 
        ba_1=float(ba1); stems_1=float(stems1); stems_2=float(stems2); h_1=float(h1); h_2=float(h2)
        if h_2 <= 0 or h_1 <= 0: return StandBasalArea(0)
        if stems_1 <= 0: return StandBasalArea(0)
        if age1 == age2: return ba1
        ratio_h = h_1 / h_2; ratio_n = stems_2 / stems_1
        # WARNING: Using snippet formula - verify!
        ba_2 = (ba_1**(ratio_h**b1)) * np.exp((b2**ratio_n) * b2 * (1 - ratio_h**b3))
        return StandBasalArea(max(0, ba_2))

    @staticmethod
    def _basal_area_projection_broadleaves(ba1: StandBasalArea, age1: AgeMeasurement, age2: AgeMeasurement, si_h40: SiteIndexValue, stems1: Stems, stems2: Stems) -> StandBasalArea:
        # ... (Implementation as before, including checks and warnings) ...
        b1 = 0.2970; b2 = 3.6124; b3 = 0.2087 # Verify coeffs/meaning vs paper
        h1 = Maleki2022ModelNorway._height_trajectory_broadleaves(float(si_h40), AgeMeasurement(40, Age.TOTAL.value), age1) 
        h2 = Maleki2022ModelNorway._height_trajectory_broadleaves(float(si_h40), AgeMeasurement(40, Age.TOTAL.value), age2) 
        ba_1=float(ba1); stems_1=float(stems1); stems_2=float(stems2); h_1=float(h1); h_2=float(h2)
        if h_2 <= 0 or h_1 <= 0: return StandBasalArea(0)
        if stems_1 <= 0: return StandBasalArea(0)
        if age1 == age2: return ba1
        ratio_h = h_1 / h_2; ratio_n = stems_2 / stems_1
        # WARNING: Using snippet formula - verify!
        ba_2 = (ba_1**(ratio_h**b1)) * np.exp((b2**ratio_n) * b2 * (1 - ratio_h**b3))
        return StandBasalArea(max(0, ba_2))
