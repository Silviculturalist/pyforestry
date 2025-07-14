from __future__ import annotations

# COMMENT: is_overstorey_tree is a bool without criteria in Heureka. It is designated on instantiation. 
# is_overstorey_tree is valid for 1) overstorey tree, 2) retention trees, 3) seed trees.

"""Elfving-based individual tree, stand growth and mortality model (IBM)
=======================================================================
This module exposes a convenient :class:`ElfvingIBM` wrapper class around the
suite of growth, yield and mortality equations published by **Elfving**
(2003-2010) and used in the Swedish *Heureka* forecast system.

The individual tree growth functions predict the 5-year increment in
squared diameter (cm²). This can then be used to calculate the
diameter increment (cm) or basal area increment (m²).

Example
-------
>>> from pyforestry.Site.sweden import SwedishSite, Sweden
>>> site = SwedishSite(latitude=60.0, longitude=15.0, altitude=120)
>>> d_bh_initial_cm = 28.0   # Initial diameter in cm
>>> ba_plot = 30.0  # m2 ha-1

>>> # Calculate 5-year diameter increment
>>> diam_inc_cm = ElfvingIBM.calculate_five_year_diameter_increment_cm(
...     species="Pinus sylvestris",
...     diameter_cm=d_bh_initial_cm,
...     Basal_area_weighted_mean_diameter_cm=24.7,
...     BA_sum_of_trees_with_larger_diameter=5.4,
...     BA_Spruce=12.0, # Example value, not used in Pine squared diameter increment model
...     BA_Pine=15.0,
...     Basal_area_plot=ba_plot,
...     Basal_area_stand=ba_plot,
...     computed_tree_age=55,
...     latitude=site.latitude,
...     altitude=site.altitude,
...     SIS=site.sis_pine_100 or 20,
...     vegetation=Sweden.FieldLayer.LOW_HERB_WITH_SHRUBS_BLUEBERRY,
...     uneven_aged=False,
...     fertilised=True, # Example: Pine model uses 'fertris' derived from this and vegetation
...     thinned=True,
...     last_thinned=5,
... )
>>> print(f"5-year diameter increment (cm): {diam_inc_cm:.3f}")

>>> # Optionally, calculate 5-year basal area increment
>>> ba_inc_m2 = ElfvingIBM.calculate_five_year_basal_area_increment_m2(
...     species="Pinus sylvestris",
...     diameter_cm=d_bh_initial_cm,
...     Basal_area_weighted_mean_diameter_cm=24.7,
...     BA_sum_of_trees_with_larger_diameter=5.4,
...     BA_Spruce=12.0,
...     BA_Pine=15.0,
...     Basal_area_plot=ba_plot,
...     Basal_area_stand=ba_plot,
...     computed_tree_age=55,
...     latitude=site.latitude,
...     altitude=site.altitude,
...     SIS=site.sis_pine_100 or 20,
...     vegetation=Sweden.FieldLayer.LOW_HERB_WITH_SHRUBS_BLUEBERRY,
...     uneven_aged=False,
...     fertilised=True,
...     thinned=True,
...     last_thinned=5,
... )
>>> print(f"5-year basal area increment (m2): {ba_inc_m2:.4f}")

"""

from math import exp, log, sqrt, pi  # Only math is required - keep NumPy-free.
from typing import Union, Optional, overload, Dict, Callable

# -----------------------------------------------------------------------------
# pyforestry helper imports - *only* those required for typing / enum coercion.
# -----------------------------------------------------------------------------
from pyforestry.sweden.site.swedish_site import Sweden  # Field layer enum, etc.
from pyforestry.base.helpers.tree_species import TreeName, parse_tree_species #Species
from pyforestry.sweden.geo.temperature.odin_1983 import Odin_temperature_sum

# Type alias for vegetation codes so we can accept either the enum *or* an int.
VegetationInput = Union[int, Sweden.FieldLayer]


def _veg_code(vegetation: VegetationInput) -> int:
    """Return the integer vegetation *code* from either an int or enum value.

    Args:
        vegetation (VegetationInput): NFI field-layer vegetation code (1-18)
            or the corresponding :class:`Sweden.FieldLayer` enum member.

    Returns:
        int: The integer vegetation code.
    """
    return vegetation if isinstance(vegetation, int) else vegetation.value.code

class ElfvingIBM:
    """Container class for Elfving (2003-2010) growth & mortality equations.

    Individual tree growth models predict the 5-year increment in squared
    diameter (cm²), which is then used to derive diameter increment or
    basal area increment. Stand-level models predict mortality or BA development.
    """

    @classmethod
    def _get_species_specific_sq_diam_inc_function(
        cls, species: Union[str, TreeName]
    ) -> Callable[..., float]:
        """Helper to get the species-specific squared diameter increment function."""
        tree: TreeName = (
            species if isinstance(species, TreeName) else parse_tree_species(species)
        )
        genus = tree.genus.name.lower()
        full = tree.full_name

        if full in {"populus tremula", "populus tremula x tremuloides"}:
            return cls._calculate_squared_diameter_increment_aspen_cm2
        elif genus == "fagus":
            return cls._calculate_squared_diameter_increment_beech_cm2
        elif genus == "betula":
            return cls._calculate_squared_diameter_increment_birch_cm2
        elif genus == "quercus":
            return cls._calculate_squared_diameter_increment_oak_cm2
        elif genus == "pinus":
            return cls._calculate_squared_diameter_increment_pine_cm2
        elif genus == "picea":
            return cls._calculate_squared_diameter_increment_spruce_cm2
        elif genus in {"fraxinus", "ulmus", "acer", "tilia", "carpinus", "prunus"}:
            return cls._calculate_squared_diameter_increment_noble_cm2
        elif genus in {"alnus", "salix", "sorbus"}:
            return cls._calculate_squared_diameter_increment_trivial_cm2
        else:
            raise NotImplementedError(
                f"No Elfving squared diameter increment equation implemented "
                f"for '{tree.full_name}'."
            )

    @classmethod
    def calculate_five_year_diameter_increment_cm(
        cls,
        species: Union[str, TreeName],
        *,
        diameter_cm: float,  # Initial diameter
        **kwargs
    ) -> float:
        """Calculate 5-year diameter increment (cm) for a specific tree species.

        This method first calculates the 5-year increment in squared diameter (cm²)
        using species-specific Elfving equations, and then derives the
        diameter increment.

        Args:
            species (Union[str, TreeName]): The tree species.
            diameter_cm (float): Initial diameter at breast-height (1.3m) of the
                subject tree, in centimeters (cm).
            **kwargs: Additional keyword arguments required by the specific
                underlying growth function. Refer to the docstrings of the
                `_calculate_squared_diameter_increment_<species_group>_cm2()`
                methods for details.

        Returns:
            float: Predicted 5-year diameter increment for the subject tree (cm).
                   Can be negative if the tree shrinks. Minimum increment is
                   -diameter_cm (tree diameter becomes 0).

        Raises:
            NotImplementedError: If no equation is implemented for the species.
            ValueError: If incompatible arguments are provided in underlying functions.
        """
        fn = cls._get_species_specific_sq_diam_inc_function(species)
        delta_d_squared_cm2 = fn(diameter_cm=diameter_cm, **kwargs)

        # d_final^2 = d_initial^2 + delta_d_squared
        d_final_squared_cm2 = diameter_cm**2 + delta_d_squared_cm2

        # Ensure d_final_squared is not negative (tree cannot have imaginary diameter)
        if d_final_squared_cm2 < 0:
            d_final_cm = 0.0
        else:
            d_final_cm = sqrt(d_final_squared_cm2)

        diameter_increment_cm = d_final_cm - diameter_cm
        return diameter_increment_cm

    # ------------------------------------------------------------------
    # Individual tree 5-year SQUARED DIAMETER increment equations (cm²)
    # Based on Elfving (2004 and other works for Heureka)
    # The output of exp(sum_of_terms) is delta_d_squared_cm2
    # ------------------------------------------------------------------

    # ----- Aspen ------------------------------------------------------
    @staticmethod
    def _calculate_squared_diameter_increment_aspen_cm2(
        *,
        diameter_cm: float,
        BA_sum_of_trees_with_larger_diameter: float,
        BA_Aspen: float,
        Basal_area_plot: float,
        Basal_area_stand: float,
        computed_tree_age: float,
        latitude: float,
        altitude: float,
        vegetation: VegetationInput,
        uneven_aged: bool,
        thinned: bool = False,
        last_thinned: int = 0,
    ) -> float:
        """Calculate 5-year squared diameter increment for Aspen (*Populus tremula*) (cm²).

        Args:
            diameter_cm (float): Initial diameter at breast-height (cm).
            Basal_area_weighted_mean_diameter_cm (float): Plot DQ (cm).
            distance_to_coast_km (float): Distance to coast (km).
            BA_sum_of_trees_with_larger_diameter (float): Basal area of larger trees (m² ha-¹).
                                                       (Corresponds to BAL in Heureka models).
            BA_Aspen (float): Plot basal area of Aspen (m² ha-¹).
            Basal_area_plot (float): Total plot basal area (m² ha-¹).
            Basal_area_stand (float): Basal area in surrounding stand (m² ha-¹).
            computed_tree_age (float): Breast-height age (years).
            latitude (float): Latitude (decimal degrees).
            altitude (float): Altitude (m).
            vegetation (VegetationInput): Vegetation code or enum.
            uneven_aged (bool): True if <80% of volume is within a 20-year span.
            fertilised (bool, optional): True if fertilised. Defaults to False.
            thinned (bool, optional): True if thinned in period. Defaults to False.
            last_thinned (int, optional): Years since last thinning. Defaults to 0.
            divided_plot (bool, optional): (Not used by Aspen model in this form).
            edge_effect (bool, optional): (Not used by Aspen model in this form).

        Returns:
            float: Predicted 5-year increment in squared diameter (cm²).
        """
        adj_computed_tree_age = computed_tree_age * 0.9 if uneven_aged else computed_tree_age
        BA_quotient_Aspen = BA_Aspen / Basal_area_plot if Basal_area_plot > 0 else 0
        bal_div_dplus1 = BA_sum_of_trees_with_larger_diameter / (diameter_cm + 1.0)
        bal_div_dplus1 = min(3.0, bal_div_dplus1)
        

        veg_code_val = _veg_code(vegetation)
        rich = 1 if veg_code_val <= 9 else 0
        thinned_recently = 1 if (thinned and 0 < last_thinned <= 10) else 0
        odin = Odin_temperature_sum(latitude, altitude)*0.001

        # Coefficients for ln(delta_d_squared_Aspen_cm2)
        # Based on AspenCoefficient[] in C#
        ln_delta_d_squared_cm2 = (
            0.9945  # C0
            + 1.9071 * log(diameter_cm + 1)  # C1
            - 0.3313 * (diameter_cm / 10.0)  # C2
            - 0.3040 * bal_div_dplus1  # C3, uses bal/(D+1)
            - 0.4058 * log(adj_computed_tree_age + 20)  # C4
            - 0.1981 * log(Basal_area_plot + 3.0)  # C5
            - 0.5967 * sqrt(BA_quotient_Aspen)  # C6
            + 0.4408 * odin  # C7, (Ts*0.001)
            + 0.4759 * rich  # C8
            + 0.2143 * thinned_recently  # C9, Hu0t10
            + 0.2427 * log( (Basal_area_plot +1.0) / (Basal_area_stand +1.0) if Basal_area_stand > 0 else 1.0) # C10, log(gry/gryf)
        )
        return exp(ln_delta_d_squared_cm2)

    # ----- Beech -----------------------------------------------------
    @staticmethod
    def _calculate_squared_diameter_increment_beech_cm2(
        *,
        diameter_cm: float,
        BA_sum_of_trees_with_larger_diameter: float,
        BA_Beech: float,
        Basal_area_plot: float,
        Basal_area_stand: float,
        computed_tree_age: float,
        latitude: float,
        SIS: float,
        uneven_aged: bool,
        thinned: bool = False,
        last_thinned: int = 0,
        divided_plot: bool = False,
    ) -> float:
        """Calculate 5-year squared diameter increment for Beech (*Fagus sylvatica*) (cm²)."""
        adj_computed_tree_age = computed_tree_age * 0.9 if uneven_aged else computed_tree_age
        BA_quotient_Beech = BA_Beech / Basal_area_plot if Basal_area_plot > 0 else 0
        bal_div_dplus1 = BA_sum_of_trees_with_larger_diameter / (diameter_cm + 1.0)
        bal_div_dplus1 = min(3.0, bal_div_dplus1)

        thinned_recently = 1 if (thinned and 0 < last_thinned <= 10) else 0
        
        # Coefficients for ln(delta_d_squared_Beech_cm2)
        # Based on BeechCoefficient[] in C#
        ln_delta_d_squared_cm2 = (
            1.7005  # C0
            + 2.5823 * log(diameter_cm + 1.0)  # C1
            - 0.3758 * (diameter_cm / 10.0)  # C2
            - 0.2079 * bal_div_dplus1  # C3
            - 0.4478 * log(adj_computed_tree_age + 20.0)  # C4
            - 0.5348 * log(Basal_area_plot + 3.0)  # C5
            - 0.9304 * sqrt(BA_quotient_Beech)  # C6
            - 0.1906 * (latitude - 50.0)  # C7
            + 0.3055 * (SIS / 10.0)  # C8
            + 0.2200 * thinned_recently  # C9
            + 0.2009 * (1 if divided_plot else 0)  # C10
            + 0.2669 * log( (Basal_area_plot +1.0) / (Basal_area_stand +1.0) if Basal_area_stand > 0 else 1.0)  # C11
        )
        return exp(ln_delta_d_squared_cm2)

    # ----- Birch -----------------------------------------------------
    @staticmethod
    def _calculate_squared_diameter_increment_birch_cm2(
        *,
        diameter_cm: float,
        distance_to_coast_km: float,
        BA_sum_of_trees_with_larger_diameter: float,
        BA_Birch: float, 
        Basal_area_plot: float,
        Basal_area_stand: float,
        computed_tree_age: float,
        latitude: float,
        altitude: float,
        vegetation: VegetationInput,
        uneven_aged: bool,
        fertilised: bool = False,
        thinned: bool = False,
        last_thinned: int = 0,
        edge_effect: bool = False,
        is_overstorey_tree: bool = False
    ) -> float:
        """Calculate 5-year squared diameter increment for Birch (*Betula spp.*) (cm²)."""
        adj_computed_tree_age = computed_tree_age * 0.9 if uneven_aged else computed_tree_age
        BA_quotient_Birch = BA_Birch / Basal_area_plot if Basal_area_plot > 0 else 0
        bal_div_dplus1 = BA_sum_of_trees_with_larger_diameter / (diameter_cm + 1.0)
        bal_div_dplus1 = min(3.0, bal_div_dplus1)

        veg_code_val = _veg_code(vegetation)
        rich = 1 if veg_code_val <= 9 else 0
        fertris = 1 if (fertilised and veg_code_val < 12) else 0 
        thinned_recently = 1 if (thinned and 0 < last_thinned <= 10) else 0
        
        odin = Odin_temperature_sum(latitude, altitude)*0.001 
        ak_term = (distance_to_coast_km / 10.0) 

        ln_delta_d_squared_cm2 = (
            5.9648  # C0
            + 1.2217 * log(diameter_cm + 1.0)  # C1
            - 0.3998 * bal_div_dplus1  # C2
            - 0.9226 * log(adj_computed_tree_age + 20.0)  # C3
            + 0.4772 * is_overstorey_tree
            - 0.2090 * log(Basal_area_plot + 3.0)  # C5
            - 0.5821 * sqrt(BA_quotient_Birch)  # C6
            - 0.5386 * odin  # C7
            - 0.4505 * (1.0 / (odin - 0.3) if odin > 0.31 else 0) # C8, added safety for denominator
            + 0.8801 * (1.0 / (ak_term + 3.0)) # C9
            + 0.3439 * rich  # C10
            + 0.3844 * fertris  # C11
            + 0.1814 * thinned_recently  # C12
            + 0.2258 * (1 if edge_effect else 0)  # C13
            + 0.1321 * log( (Basal_area_plot +1.0) / (Basal_area_stand +1.0) if Basal_area_stand > 0 else 1.0) # C14
        )
        return exp(ln_delta_d_squared_cm2)

    # ----- Noble Broadleaves -----------------------------------------
    @staticmethod
    def _calculate_squared_diameter_increment_noble_cm2(
        *,
        diameter_cm: float,
        BA_sum_of_trees_with_larger_diameter: float,
        Basal_area_plot: float,
        Basal_area_stand: float,
        vegetation: VegetationInput,
        gotland: bool = False,
        thinned: bool = False,
        last_thinned: int = 0,
    ) -> float:
        """Calculate 5-year sq. diam. increment for noble broadleaves (cm²)."""
        bal_div_dplus1 = BA_sum_of_trees_with_larger_diameter / (diameter_cm + 1.0)
        bal_div_dplus1 = min(3.0, bal_div_dplus1)

        veg_code_val = _veg_code(vegetation)
        herb = 1 if veg_code_val < 7 else 0 
        thinned_recently = 1 if (thinned and 0 < last_thinned <= 10) else 0

        ln_delta_d_squared_cm2 = (
            2.3316  # C0
            + 0.8250 * log(diameter_cm + 1.0)  # C1
            - 0.2877 * bal_div_dplus1  # C2
            - 0.4010 * log(Basal_area_plot + 3.0)  # C3
            - 0.3809 * (1 if gotland else 0)  # C4
            + 0.9397 * herb  # C5
            + 0.2410 * thinned_recently  # C6
            + 0.4676 * log( (Basal_area_plot +1.0) / (Basal_area_stand +1.0) if Basal_area_stand > 0 else 1.0)  # C7
        )
        return exp(ln_delta_d_squared_cm2)

    # ----- Oak -------------------------------------------------------
    @staticmethod
    def _calculate_squared_diameter_increment_oak_cm2(
        *,
        diameter_cm: float,
        BA_sum_of_trees_with_larger_diameter: float,
        BA_Oak: float, 
        Basal_area_plot: float,
        Basal_area_stand: float,
        altitude: float,
        vegetation: VegetationInput,
        gotland: bool = False,
        thinned: bool = False,
        last_thinned: int = 0,
        edge_effect: bool = False,
    ) -> float:
        """Calculate 5-year sq. diam. increment for Oak (*Quercus spp.*) (cm²)."""
        BA_quotient_Oak = BA_Oak / Basal_area_plot if Basal_area_plot > 0 else 0
        bal_div_dplus1 = BA_sum_of_trees_with_larger_diameter / (diameter_cm + 1.0)
        bal_div_dplus1 = min(3.0, bal_div_dplus1)

        veg_code_val = _veg_code(vegetation)
        rich = 1 if veg_code_val <= 9 else 0
        thinned_recently = 1 if (thinned and 0 < last_thinned <= 10) else 0
        alt_div_100 = altitude / 100.0

        ln_delta_d_squared_cm2 = (
            1.9047  # C0
            + 1.3115 * log(diameter_cm + 1.0)  # C1
            - 0.2640 * bal_div_dplus1  # C2
            - 0.5056 * log(Basal_area_plot + 3.0)  # C3
            - 0.6001 * sqrt(BA_quotient_Oak)  # C4
            - 0.4615 * (1 if gotland else 0)  # C5
            + 0.3833 * alt_div_100  # C6
            - 0.1938 * (alt_div_100**2)  # C7
            + 0.2635 * rich  # C8
            + 0.1034 * thinned_recently  # C9
            + 0.3551 * (1 if edge_effect else 0)  # C10
            + 0.1897 * log( (Basal_area_plot +1.0) / (Basal_area_stand +1.0) if Basal_area_stand > 0 else 1.0)  # C11
        )
        return exp(ln_delta_d_squared_cm2)

    # ----- Pine ------------------------------------------------------
    @staticmethod
    def _calculate_squared_diameter_increment_pine_cm2(
        *,
        diameter_cm: float,
        Basal_area_weighted_mean_diameter_cm: float, # Mditot
        BA_sum_of_trees_with_larger_diameter: float, # Bal
        BA_Pine: float, # Used for BA_quotient_Pine
        Basal_area_plot: float, # gry
        Basal_area_stand: float, # gryf
        computed_tree_age: float, # a13
        latitude: float, # Lat
        altitude: float, # alt (for Ts)
        SIS: float, # sis
        vegetation: VegetationInput, # For rich, fertris
        uneven_aged: bool, # For adjusting age
        fertilised: bool = False, # For fertris
        thinned: bool = False, # For Hu0t10, hullt25
        last_thinned: int = 0,
        gotland: bool = False,
        divided_plot: bool = False,
        edge_effect: bool = False,
        is_overstorey_tree: bool = False
    ) -> float:
        """Calculate 5-year sq. diam. increment for Scots Pine (*Pinus sylvestris*) (cm²)."""
        adj_computed_tree_age = computed_tree_age * 0.9 if uneven_aged else computed_tree_age
        # BA_quotient_Pine is ((gry - basalAreaPines)/gry) in C# but for (1-BA_pine_prop)^2.
        # So BA_pine_prop = basalAreaPines / gry
        # ( (gry - basalAreaPines)/gry )^2 = (1 - basalAreaPines/gry)^2
        BA_pine_prop = BA_Pine / Basal_area_plot if Basal_area_plot > 0 else 0
        ba_pine_prop_term = (1.0 - BA_pine_prop)**2 # Matches C# structure for PineCoefficient[7]

        bal_div_dplus1 = BA_sum_of_trees_with_larger_diameter / (diameter_cm + 1.0)
        bal_div_dplus1 = min(3.0, bal_div_dplus1)

        veg_code_val = _veg_code(vegetation)
        rich = 1 if veg_code_val <= 9 else 0
        fertris = 1 if (fertilised and veg_code_val < 12) else 0
        thinned_recently = 1 if (thinned and 0 < last_thinned <= 10) else 0
        thinned_long_ago = 1 if (thinned and 10 < last_thinned < 25) else 0 # C# uses <25
        
        odin = Odin_temperature_sum(latitude, altitude)*0.001
        mditot_term = Basal_area_weighted_mean_diameter_cm / 10.0 # Mditot * 0.1

        ln_delta_d_squared_cm2 = (
            3.4176  # C0
            + 1.0149 * log(diameter_cm + 1.0)  # C1
            - 0.3902 * bal_div_dplus1  # C2
            - 0.7730 * log(adj_computed_tree_age + 20.0)  # C3
            + 0.2218 * is_overstorey_tree
            + 0.1843 * mditot_term  # C5
            - 0.3145 * log(Basal_area_plot + 3.0)  # C6
            + 0.1391 * ba_pine_prop_term  # C7
            - 0.0844 * (1 if gotland else 0)  # C8
            + 0.1178 * (odin**2)  # C9
            + 1.0890 * (SIS / 10.0)  # C10
            - 0.2164 * ((SIS**2) / 100.0)  # C11
            + 0.1011 * rich  # C12
            + 0.2790 * fertris  # C13
            + 0.1245 * thinned_recently  # C14
            + 0.0451 * thinned_long_ago  # C15
            + 0.0487 * (1 if divided_plot else 0)  # C16
            + 0.1368 * (1 if edge_effect else 0)  # C17
            + 0.0842 * log( (Basal_area_plot +1.0) / (Basal_area_stand +1.0) if Basal_area_stand > 0 else 1.0)  # C18
        )
        return exp(ln_delta_d_squared_cm2)

    # ----- Spruce ----------------------------------------------------
    @staticmethod
    def _calculate_squared_diameter_increment_spruce_cm2(
        *,
        diameter_cm: float,
        Basal_area_weighted_mean_diameter_cm: float, # Mditot
        SS_diam: float, # Sum of squared diameters (d²) on the plot (cm²). Used for Mgtot.
        stems: float, # Number of stems per hectare on the plot. Used for Mgtot.
        BA_sum_of_trees_with_larger_diameter: float, # Bal
        BA_Spruce: float, 
        Basal_area_plot: float, # gry
        Basal_area_stand: float, # gryf
        computed_tree_age: float, # a13
        latitude: float, # Lat
        altitude: float, # alt (for Ts)
        SIS: float, # sis
        vegetation: VegetationInput, # For rich, fertris
        uneven_aged: bool, # For adjusting age
        fertilised: bool = False,
        thinned: bool = False,
        last_thinned: int = 0,
        gotland: bool = False,
        divided_plot: bool = False,
        edge_effect: bool = False,
        is_overstorey_tree: bool = False
    ) -> float:
        """Calculate 5-year sq. diam. increment for Norway Spruce (*Picea abies*) (cm²)."""
        adj_computed_tree_age = computed_tree_age * 0.9 if uneven_aged else computed_tree_age
        bal_div_dplus1 = BA_sum_of_trees_with_larger_diameter / (diameter_cm + 1.0)
        bal_div_dplus1 = min(3.0, bal_div_dplus1)

        # Mgtot (arithmetic mean diameter) calculation from SS_diam and stems for dif3bal
        # Mgtot = sqrt(SS_diam / stems) if stems > 0 else 0 (DG in Python)
        mean_geom_diam_dg = sqrt(SS_diam / stems) if stems > 0 else 0.0
        
        # C# term: temp1 = Math.Min(_commonData.Mditot - _commonData.Mgtot, 10.0);
        # C# term: temp = _baldp1 * Math.Pow(temp1/_commonData.Mditot, 3); (This is SpruceCoefficient[4] * term)
        # Python equivalent for temp1/_commonData.Mditot part:
        mditot_val = Basal_area_weighted_mean_diameter_cm # DQ
        mgtot_val = mean_geom_diam_dg # DG
        
        # Python dif3bal term from previous version: ((DQ - DG)/DQ)^3
        # C# dif3bal_numerator: min(DQ - DG, 10.0)
        # C# dif3bal structure: BAL/(D+1) * ( (min(DQ-DG,10))/DQ )^3 -- This is different from Python's previous structure.
        # The C# formula for SpruceCoefficient[4] is: C4 * _baldp1 * ( ( Min(Mditot-Mgtot,10) / Mditot )^3 )
        # The C# formula for SpruceCoefficient[9] is: C9 * _baldp1 * ( (gry - BA_Spruce)/gry )
        
        # Term for C4 (0.4702):
        # In C#: SpruceCoefficient[4] * _baldp1 * Math.Pow( (Math.Min(Mditot - Mgtot, 10.0)) / Mditot, 3.0 )
        # Note: The Python code was previously (DQ/10) * ((DQ-DG)/DQ)^3. Re-aligning to C# structure for this term.
        c4_term_factor = 0.0
        if mditot_val > 0:
            c4_term_factor = bal_div_dplus1 * ( (min(mditot_val - mgtot_val, 10.0)) / mditot_val )**3
        
        # Term for C9 (0.1625):
        # In C#: SpruceCoefficient[9] * _baldp1 * ((gry - BA_Spruce)/gry)
        # Python: Basal_area_weighted_mean_diameter_cm/10 * (1 - BA_quotient_Spruce)
        # Re-aligning to C# structure for this term.
        ba_spruce_prop = BA_Spruce / Basal_area_plot if Basal_area_plot > 0 else 0
        c9_term_factor = bal_div_dplus1 * (1.0 - ba_spruce_prop)

        veg_code_val = _veg_code(vegetation)
        rich = 1 if veg_code_val <= 9 else 0
        fertris = 1 if (fertilised and veg_code_val < 12) else 0
        thinned_recently = 1 if (thinned and 0 < last_thinned <= 10) else 0
        
        odin = Odin_temperature_sum(latitude, altitude)*0.001
        mditot_squared_term = (mditot_val**2) / 1000.0 # Mditot^2 * 0.001

            
        # Term for C10 (0.1754): ((gry - BA_Spruce)/gry)^2
        c10_term_factor = (1.0 - ba_spruce_prop)**2


        # Coefficients for ln(delta_d_squared_Spruce_cm2)
        # Based on SpruceCoefficient[] in C# and its variable associations
        ln_delta_d_squared_cm2 = (
            3.4360  # C0
            + 1.5163 * log(diameter_cm + 1.0)  # C1
            - 0.1520 * (diameter_cm / 10.0)  # C2
            - 0.4024 * bal_div_dplus1  # C3
            + 0.4702 * c4_term_factor # C4 * its specific term structure from C#
            - 0.7789 * log(adj_computed_tree_age + 20.0)  # C5
            + 0.4034 * is_overstorey_tree # C6 
            + 0.1914 * mditot_squared_term  # C7
            - 0.2342 * log(Basal_area_plot + 3.0)  # C8
            + 0.1625 * c9_term_factor # C9 * its specific term structure from C#
            + 0.1754 * c10_term_factor # C10 * its specific term
            - 0.3264 * (1 if gotland else 0)  # C11
            - 0.6923 * odin  # C12 (Ts*0.001)
            + 0.2568 * (odin**2)  # C13 (Ts*0.001)^2
            + 0.2903 * (SIS / 10.0)  # C14
            + 0.1965 * rich  # C15
            + 0.4034 * fertris  # C16 (Matches C# Coeff[16] for fertris; C# Coeff[6] is ost)
            + 0.1309 * thinned_recently  # C17
            + 0.0561 * (1 if divided_plot else 0)  # C18
            + 0.1126 * (1 if edge_effect else 0)  # C19
            + 0.0770 * log( (Basal_area_plot +1.0) / (Basal_area_stand +1.0) if Basal_area_stand > 0 else 1.0)  # C20
        )
        return exp(ln_delta_d_squared_cm2)

    # ----- Trivial species -------------------------------------------
    @staticmethod
    def _calculate_squared_diameter_increment_trivial_cm2(
        *,
        diameter_cm: float,
        BA_sum_of_trees_with_larger_diameter: float,
        Basal_area_plot: float,
        computed_tree_age: float,
        vegetation: VegetationInput,
        SIS: float,
        uneven_aged: bool,
        thinned: bool = False,
        last_thinned: int = 0,
    ) -> float:
        """Calculate 5-year sq. diam. increment for trivial broadleaves (cm²)."""
        adj_computed_tree_age = computed_tree_age * 0.9 if uneven_aged else computed_tree_age
        bal_div_dplus1 = BA_sum_of_trees_with_larger_diameter / (diameter_cm + 1.0)
        bal_div_dplus1 = min(3.0, bal_div_dplus1)
    
        veg_code_val = _veg_code(vegetation)
        herb = 1 if veg_code_val < 7 else 0
        thinned_recently = 1 if (thinned and 0 < last_thinned <= 10) else 0

        # Coefficients for ln(delta_d_squared_Trivial_cm2)
        # Based on TrivialCoefficient[] in C#
        ln_delta_d_squared_cm2 = (
            2.1108  # C0
            + 0.9418 * log(diameter_cm + 1.0)  # C1
            - 0.2599 * bal_div_dplus1  # C2.
            - 0.3026 * log(adj_computed_tree_age + 20.0)  # C3
            - 0.2280 * log(Basal_area_plot + 3.0)  # C4
            + 0.2595 * (SIS / 10.0)  # C5
            + 0.4392 * herb  # C6
            + 0.1561 * thinned_recently  # C7
        )
        return exp(ln_delta_d_squared_cm2)


    # ------------------------------------------------------------------
    # Stand-level models (Mortality, Gmax, BEY2)
    # These were not the primary subject of the C# comparison but are kept
    # with their original interpretation unless specified otherwise.
    # Their outputs (BA%, Gmax m2/ha, BA increment m2/ha) are distinct.
    # ------------------------------------------------------------------
    @staticmethod
    def basal_area_mortality_percent_spruce_pine(
        *,
        dominant_height: float, 
        H100: float, 
        stems: float, 
        ThinningProportionBAStart: float, 
        ThinningForm: bool = True, 
        fertilised: bool = False, # Unused in Elfving 2010 final model
    ) -> float:
        """Annual mortality (% of BA start) for Pine & Spruce stands. Elfving (2010)."""
        # DENS term as per Elfving (2010) paper for Eq 4 is (N * Hdom)^0.5
        # The C# code provided in the prompt was for TreeGrowthElfving.cs, not mortality.
        # The previous Python version used DENS = (stems * dominant_height**2) / 100_000.0
        # Reverting to a DENS consistent with Elfving 2010 paper, Eq 4: DENS = (N*Hdom)^0.5
        # If the Heureka implementation differs, that specific DENS would be needed.
        # Using the DENS = N * (Hdom_m/10)^2 for now as often cited for Heureka context.
        
        # DENS_heureka_style = stems * (dominant_height / 10.0)**2 # DENS = N * (Hdom_dm/10)^2
        # The initial Python code had DENS = (stems * dominant_height**2) / 100_000.0. Let's keep that for consistency with previous state unless a specific new source for DENS is given.
        DENS = (stems * dominant_height**2) / 100_000.0

        mortality_percentage = (
            -0.4093
            + 0.02189 * H100
            + 0.005373 * (DENS ** 2) 
            + 0.3817 * dominant_height * (ThinningProportionBAStart ** 3)
            + 0.01252 * dominant_height * (1 if ThinningForm else 0) 
        )
        return max(0.0, mortality_percentage)

    @staticmethod
    def gmax_spruce_pine(
        *,
        dominant_height: float,
        H100: float,
        stems: float,
        latitude: float,
    ) -> float:
        """Maximum potential basal-area (Gmax) for Spruce & Pine stands. Elfving (2010)."""
        g_max = (
            -89.7
            + 2.47 * dominant_height
            + 0.0212 * ((dominant_height ** 3) / H100 if H100 > 0 else 0) 
            + 0.834 * H100
            + 0.00350 * stems
            + 0.890 * latitude
        )
        return max(0.0, g_max) 

    @staticmethod
    def stand_basal_area_bey2( 
        *,
        vegetation: VegetationInput,
        stand_age: float, 
        Basal_area_Conifer_m2_ha: float, 
        Basal_area_Pine_m2_ha: float, 
        Basal_area_Birch_m2_ha: float, 
        Basal_area_after_thinning: float, 
        Basal_area_before_thinning: float, 
        Basal_area_stand: float, 
        stems_after_thinning: float, 
        peatland: bool, 
        soil_moisture: int, 
        SIS100: float, 
        latitude: float,
        altitude: float,
        ditched: bool, 
        thinned: bool, 
        last_thinned: int, 
        spruce_ba_proportion: float = 0.0, 
    ) -> float:
        """5-year stand-level basal area *increment* after thinning (Elfving 2009, BEY2)."""
        VEG_SCALE = {
            1: 4, 2: 2.5, 3: 2, 4: 3, 5: 2.5, 6: 2, 7: 3, 8: 2.5, 9: 1.5,
            10: -3, 11: -3, 12: 1, 13: 0, 14: -0.5, 15: -3, 16: -5, 17: -0.5, 18: -1,
        }
        vegetation_scaled = VEG_SCALE.get(_veg_code(vegetation), 0) 

        conifer_ba_proportion_term = 0
        if Basal_area_after_thinning > 0 and stand_age > 0:
            conifer_ba_proportion_term = (
                Basal_area_Conifer_m2_ha / Basal_area_after_thinning / stand_age
            )
        pine_ba_proportion_after_thinning = 0
        if Basal_area_after_thinning > 0:
            pine_ba_proportion_after_thinning = Basal_area_Pine_m2_ha / Basal_area_after_thinning
        birch_ba_proportion_after_thinning = 0
        if Basal_area_after_thinning > 0:
            birch_ba_proportion_after_thinning = Basal_area_Birch_m2_ha / Basal_area_after_thinning
        
        # lngrel = 0 # Not used in Elfving 2009 BEY2 paper's final model p.50
        
        peat_vegetation_term = vegetation_scaled if peatland else 0
        moist_soil = 1 if soil_moisture == 4 else 0 
        wet_soil = 1 if soil_moisture == 5 else 0   

        temp_sum = Odin_temperature_sum(latitude, altitude)*0.001
        cold_climate_factor = exp(-0.01 * (temp_sum - 300))

        thinned_recently_flag = 1 if (thinned and 0 <= last_thinned <= 10) else 0 
        thinned_long_ago_flag = 1 if (thinned and 10 < last_thinned <= 25) else 0 

        stem_number_quotient = 0
        if stems_after_thinning >= 0: 
            stem_number_quotient = stems_after_thinning / (stems_after_thinning + 80)

        log_increment = (
            0.366
            - 0.5842 * log(stand_age if stand_age > 0 else 1) 
            + 8.3740 * conifer_ba_proportion_term          
            - 0.0237 * pine_ba_proportion_after_thinning * vegetation_scaled 
            - 0.3192 * (birch_ba_proportion_after_thinning ** 2) 
            - 10.8034 * cold_climate_factor * birch_ba_proportion_after_thinning 
            + 0.5002 * log(Basal_area_after_thinning if Basal_area_after_thinning > 0 else 1) 
            - 0.00632 * Basal_area_before_thinning        
            + 1.376 * stem_number_quotient                
            + 0.0627 * vegetation_scaled                  
            - 0.0244 * peat_vegetation_term               
            - 0.0498 * moist_soil                         
            - 0.1807 * wet_soil                           
            + 0.0109 * SIS100                             
            + 0.0542 * (1 if (peatland and ditched) else 0) 
            + 0.1396 * thinned_recently_flag              
            + 0.0567 * thinned_long_ago_flag              
            - 0.06 * pine_ba_proportion_after_thinning  
            - 0.03 * spruce_ba_proportion 
        )
        return exp(log_increment)