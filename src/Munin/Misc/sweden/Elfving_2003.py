from __future__ import annotations

"""swedish_forest_models.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Python translations of two classical Swedish stand / tree models.

This revision adds **robust field-layer handling**: the private helper
:py:meth:`Elfving2003SingleTreeAge._is_rich_site` now accepts either

* an **``int`` 1-18** (the raw NFI vegetation code), or
* a **``SwedenFieldLayer`` enum member** from :pymod:`SwedishSite`, or
* a plain *Vegetation* dataclass instance - all with graceful fallback to
  ``0`` (not rich) when the value is missing or cannot be parsed.

A site is considered *rich* when the vegetation code ∈ [1-9, 12].
A site is considered *poor* when the vegetation code > 13.

--------------------------------------------------------------------
Public API
--------------------------------------------------------------------
* :class:`Lind2003MeanDiameterCodominantTrees` - dominant-mean diameter
  of the co-dominant stratum (``md``, cm).
* :class:`Elfving2003SingleTreeAge` - breast-height age (years) for a
  single tree.

Both helpers are **stateless** (all public methods are
:py:meth:`@staticmethod`s) and work with either the lightweight
"typed-float" classes from your *Base.py* layer **or** plain
numbers/strings supplied by users.
"""

from math import exp, log, sqrt, pi
from typing import Union, SupportsFloat, Optional, Any, Dict, Tuple, Callable
from dataclasses import dataclass, field

# Assuming these imports are from your project structure
# Ensure Munin.Helpers.TreeSpecies.parse_tree_species returns a TreeName object
from Munin.Site.sweden.SwedishSite import SwedenFieldLayer, Vegetation, SwedenCounty # type: ignore
from Munin.Helpers.TreeSpecies import TreeSpecies, TreeName, parse_tree_species, RegionalGenusGroup # type: ignore

Number = Union[int, float, SupportsFloat]

__all__ = [
    "Lind2003MeanDiameterCodominantTrees",
    "Elfving2003SingleTreeAge",
]

# =============================================================================
# Stand-level helper - Lind (2003) dominant-mean diameter (md)
# =============================================================================
class Lind2003MeanDiameterCodominantTrees:
    """Dominant-mean diameter (``md``) of co-dominant trees [cm].

    Implements Lind (2003, Eq. 1) as used by Elfving (2003) and later
    work‐flows.  The function is deterministic and carries the
    logarithmic-bias correction (``+ 0.036``) baked-in.

    Parameters
    ----------
    total_stand_age : Number
        *bald* - basal-area-weighted stand age (yrs).
    stand_density_gf : Number
        *Gf* - relascope basal area (m² ha⁻¹).
    site_index : Number
        *sis* - top height at reference age 100 (m).

    Returns
    -------
    float
        Dominant-mean diameter, centimetres (``md``).
    """

    # Coefficients from C# reference implementation (MeanDiameterDominantTrees.cs)
    _C0, _C1, _C2, _C3, _C4, _C5 = (
        -0.92313,
        1.00322,
        -0.00701,
        -4.00529,
        0.01859,
        -1.88177,
    )
    _BIAS = 0.036  # ln-bias correction

    @staticmethod
    def estimate(
        *,
        total_stand_age: Number,
        stand_density_gf: Number,
        site_index: Number,
    ) -> float:
        """Estimates the dominant-mean diameter."""
        age = float(total_stand_age)
        gf = float(stand_density_gf)
        si = float(site_index)

        if not (age > 0 and si > 0 and gf > 0):
            raise ValueError(
                "total_stand_age, stand_density_gf, and site_index must all be > 0."
            )

        ln_md = (
            Lind2003MeanDiameterCodominantTrees._C0
            + Lind2003MeanDiameterCodominantTrees._C1 * log(age)
            + Lind2003MeanDiameterCodominantTrees._C2 * age
            + Lind2003MeanDiameterCodominantTrees._C3 / si
            + Lind2003MeanDiameterCodominantTrees._C4 * si
            + Lind2003MeanDiameterCodominantTrees._C5 / (1 + gf)
            + Lind2003MeanDiameterCodominantTrees._BIAS
        )
        md = exp(ln_md)
        if md <= 0: 
            raise ArithmeticError(
                "Calculated dominant-mean diameter is non-positive - check inputs."
            )
        return md


# =============================================================================
# Tree-level helper - Elfving (2003) single-tree age at breast height
# =============================================================================

@dataclass
class _ModelParams:
    """Helper dataclass to store processed parameters for Elfving2003SingleTreeAge."""
    # Core inputs
    d_cm: float
    species_obj: TreeName 
    altitude_m: float
    latitude: float
    
    # Processed stand context variables
    processed_total_stand_age: Optional[float] = None
    sis: Optional[float] = None 
    field_layer_vegetation: Vegetation = SwedenFieldLayer.BILBERRY.value 
    processed_basal_area_plot_m2_ha: Optional[float] = None 
    processed_basal_area_relascope_m2_ha: Optional[float] = None
    local_qmd_cm: Optional[float] = None
    stems_ha: Optional[int] = None

    # Helper hints / overrides
    is_uneven_aged_override: Optional[bool] = None
    is_standard_override: Optional[bool] = None 
    is_undergrowth_override: Optional[bool] = None 
    dominant_mean_diameter_override: Optional[float] = None
    is_gotland_override: Optional[bool] = None 
    is_ditched_override: Optional[bool] = None 
    is_peat_soil_override: Optional[bool] = None 
    is_shade_tolerant_broadleaf_override: Optional[bool] = None # User hint for shade-tolerant broadleaf

    # Derived values
    log_d_cm: float = field(init=False)
    dominant_mean_diameter: Optional[float] = field(init=False) 
    diameter_qmd_ratio: Optional[float] = field(init=False)
    dfrel_ratio: Optional[float] = field(init=False) 
    log_processed_basal_area_plot: Optional[float] = field(init=False) 
    log_inverted_relascope_ba_plus_1: Optional[float] = field(init=False) 
    inverted_sis: Optional[float] = field(init=False)
    temperature_sum: float = field(init=False)
    
    # Site richness flags
    is_rich_site_flag: int = field(init=False)
    is_poor_site_flag: int = field(init=False)

    # Species indicator flags
    is_spruce_flag: int = field(init=False)
    is_pine_flag: int = field(init=False) 
    is_light_decid_flag: int = field(init=False)
    is_bokek_flag: int = field(init=False) 
    is_shade_tolerant_broadleaf_flag: int = field(init=False) # For "slov" coefficient

    # Location/Condition flags
    is_gotland_flag: int = field(init=False)
    is_ditched_flag: int = field(init=False)
    is_peat_soil_flag: int = field(init=False)
    # TODO: Add is_coast_flag if needed by any model group explicitly

    # Group determination flags (ost & sma)
    is_standard_tree: bool = field(init=False) 
    is_undergrowth_tree: bool = field(init=False) 
    is_ost_flag: int = field(init=False)
    is_sma_flag: int = field(init=False)


    def __post_init__(self):
        """Initialize derived fields."""
        if self.d_cm <= 0:
            raise ValueError("diameter (d_cm) must be > 0 cm")
        self.log_d_cm = log(self.d_cm)

        self.temperature_sum = 0.001 * (4835.0 - 5.76 * self.latitude - 0.9 * self.altitude_m)

        if self.sis is not None:
            if self.sis <= 0: 
                self.inverted_sis = None 
            else:
                self.inverted_sis = 1.0 / self.sis
        else:
            self.inverted_sis = None
            
        if self.dominant_mean_diameter_override is not None:
            self.dominant_mean_diameter = float(self.dominant_mean_diameter_override)
        elif (self.processed_total_stand_age is not None and
              self.sis is not None and self.sis > 0 and
              self.processed_basal_area_relascope_m2_ha is not None and
              self.processed_basal_area_relascope_m2_ha > 0):
            try:
                self.dominant_mean_diameter = Lind2003MeanDiameterCodominantTrees.estimate(
                    total_stand_age=self.processed_total_stand_age,
                    site_index=self.sis,
                    stand_density_gf=self.processed_basal_area_relascope_m2_ha
                )
            except (ValueError, ArithmeticError): 
                 self.dominant_mean_diameter = self.d_cm 
        else:
            self.dominant_mean_diameter = self.d_cm

        if self.dominant_mean_diameter is not None and self.dominant_mean_diameter > 0:
            self.dfrel_ratio = self.d_cm / self.dominant_mean_diameter
        else: 
            self.dfrel_ratio = None 

        if self.local_qmd_cm is not None and self.local_qmd_cm > 0:
            self.diameter_qmd_ratio = self.d_cm / self.local_qmd_cm
        else:
            self.diameter_qmd_ratio = None 

        if self.processed_basal_area_plot_m2_ha is not None and self.processed_basal_area_plot_m2_ha > 0:
            self.log_processed_basal_area_plot = log(self.processed_basal_area_plot_m2_ha)
        else:
            self.log_processed_basal_area_plot = None

        if self.processed_basal_area_relascope_m2_ha is not None and self.processed_basal_area_relascope_m2_ha >=0: 
            self.log_inverted_relascope_ba_plus_1 = log(self.processed_basal_area_relascope_m2_ha + 1.0)
        else:
            self.log_inverted_relascope_ba_plus_1 = None
            
        self.is_rich_site_flag = Elfving2003SingleTreeAge._is_rich_site(self.field_layer_vegetation)
        self.is_poor_site_flag = Elfving2003SingleTreeAge._is_poor_site(self.field_layer_vegetation)

        self.is_spruce_flag = 1 if self.species_obj == TreeSpecies.Sweden.picea_abies else 0
        self.is_pine_flag = 1 if self.species_obj == TreeSpecies.Sweden.pinus_sylvestris else 0 
        
        light_decid_species_exact = (
            TreeSpecies.Sweden.ulmus_glabra, TreeSpecies.Sweden.tilia_cordata,
            TreeSpecies.Sweden.acer_platanoides, TreeSpecies.Sweden.prunus_avium
        )
        self.is_light_decid_flag = 0
        if self.species_obj in light_decid_species_exact:
            self.is_light_decid_flag = 1
        elif hasattr(TreeSpecies.Sweden, 'salix') and \
             isinstance(TreeSpecies.Sweden.salix, RegionalGenusGroup) and \
             self.species_obj in TreeSpecies.Sweden.salix: 
            self.is_light_decid_flag = 1

        self.is_bokek_flag = 0
        if self.species_obj == TreeSpecies.Sweden.fagus_sylvatica: 
            self.is_bokek_flag = 1
        elif hasattr(TreeSpecies.Sweden, 'quercus') and \
             isinstance(TreeSpecies.Sweden.quercus, RegionalGenusGroup) and \
             self.species_obj in TreeSpecies.Sweden.quercus: 
            self.is_bokek_flag = 1
        
        # Shade-tolerant broadleaf flag ("slov")
        # Define which species are considered shade-tolerant broadleaves
        shade_tolerant_broadleaves = (
            TreeSpecies.Sweden.carpinus_betulus, # Hornbeam
            TreeSpecies.Sweden.sorbus_aucuparia,  # Rowan
        )
        if self.is_shade_tolerant_broadleaf_override is not None:
            self.is_shade_tolerant_broadleaf_flag = 1 if self.is_shade_tolerant_broadleaf_override else 0
        else:
            self.is_shade_tolerant_broadleaf_flag = 1 if self.species_obj in shade_tolerant_broadleaves else 0
            
        if self.dominant_mean_diameter is not None: 
            self.is_standard_tree = self.d_cm > 1.8 * (self.dominant_mean_diameter + 8.0)
            self.is_undergrowth_tree = self.d_cm < 0.4 * self.dominant_mean_diameter
        else: 
            self.is_standard_tree = False 
            self.is_undergrowth_tree = False
        
        self.is_ost_flag = 1 if self.is_standard_tree else 0
        self.is_sma_flag = 1 if self.is_undergrowth_tree else 0

        if self.is_gotland_override is not None:
            self.is_gotland_flag = 1 if self.is_gotland_override else 0
        else:
            self.is_gotland_flag = 0 
        
        self.is_ditched_flag = 1 if self.is_ditched_override else 0
        self.is_peat_soil_flag = 1 if self.is_peat_soil_override else 0


class Elfving2003SingleTreeAge:
    """Age at 1.3 m for a single tree according to Elfving (2003)."""

    _BIAS: Dict[int, float] = {
        2: 0.028, 3: 0.062, 4: 0.042, 5: 0.012, 6: 0.018, 7: 0.038, 8: 0.034, 9: 0.045,
    }

    _COEFF_2_TOTAL_W_AGE: Tuple[float, ...] = ( 
        -1.46921, 0.29889, -0.01132, 0.25943, 1.01901, -0.09476, -0.09798,
         0.00465, -0.00372, 0.33497, -0.15507, 0.56842, -0.21026, -0.03118,
         0.04492, 0.03439, -0.13876, 0.06144 
    )
    _COEFF_3_TOTAL_WO_AGE: Tuple[float, ...] = (
        2.25519, 1.21082, -1.51153, 0.39625, -0.18216, 0.14160, -0.12756, -0.02778, 
        -0.00471, -0.00304, -0.39207, 0.16211, 0.29504, 0.19080, 0.19944, -0.20707, 
        0.03196, -0.09185, 0.14096   
    )
    _COEFF_4_UNEVEN: Tuple[float, ...] = ( 
        0.41811, 0.55719, -0.01803, 0.17128, 0.39232, 0.00367, 0.10508, -0.22284,
        -0.01171, 0.00028510, -0.00135, 0.83621, -0.44686, 0.04693, -0.06676,
         0.03127, -0.03794, 0.14490, 
    )
    _COEFF_5_PINE: Tuple[float, ...] = ( 
        -1.69566, 0.29819, -0.00801, 0.07258, 1.15873, 0.00076986, 0.03098,
    )
    _COEFF_6_SPRUCE: Tuple[float, ...] = ( 
        -1.38343, 0.37897, -0.01003, 0.12834, 1.02011, 0.01748,
    )
    _COEFF_7_BIRCH: Tuple[float, ...] = ( 
        0.10055, 0.52067, -0.00793, -0.08139, 0.67013, -0.01053, -0.09905, 0.03945,
    )
    _COEFF_8_DECID: Tuple[float, ...] = ( # slov is c[4]
        0.13800, 0.64693, -0.26496, 0.50530, 0.19386, -0.17874,
    )
    _COEFF_9_STD: Tuple[float, ...] = ( 
        1.79933, 1.14894, -0.01841, 0.00634, -0.03460, -0.22537,
    )

    _COEFFS: Dict[int, Tuple[float, ...]] = {
        2: _COEFF_2_TOTAL_W_AGE, 3: _COEFF_3_TOTAL_WO_AGE, 4: _COEFF_4_UNEVEN, 
        5: _COEFF_5_PINE, 6: _COEFF_6_SPRUCE, 7: _COEFF_7_BIRCH, 
        8: _COEFF_8_DECID, 9: _COEFF_9_STD,
    }
    
    _CalculatorFunc = Callable[[_ModelParams, Tuple[float, ...]], float]

    @staticmethod
    def _prepare_model_params(
        diameter: Number, species_input: str | TreeName, 
        total_stand_age: Optional[Number], SIS_spruce: Optional[Number],
        field_layer: Any, basal_area_plot_m2_ha: Optional[Number],
        basal_area_relascope_m2_ha: Optional[Number], altitude_m: Number,
        latitude: Number, QMD_cm: Optional[Number], stems_ha: Optional[int],
        is_uneven_aged_override: Optional[bool],
        dominant_mean_diameter_override: Optional[Number],
        is_standard_override: Optional[bool],
        is_undergrowth_override: Optional[bool],
        is_gotland_override: Optional[bool],
        is_ditched_override: Optional[bool], 
        is_peat_soil_override: Optional[bool],
        is_shade_tolerant_broadleaf_override: Optional[bool] # Added
    ) -> _ModelParams:
        d_cm = float(diameter)
        species_obj = parse_tree_species(species_input)
        if not isinstance(species_obj, TreeName):
            raise TypeError(f"parse_tree_species expected to return TreeName, got {type(species_obj)}")

        processed_total_stand_age: Optional[float] = None
        if total_stand_age is not None:
            val_tsa = float(total_stand_age)
            processed_total_stand_age = min(max(val_tsa, 10.0), 175.0) 
        
        processed_sis: Optional[float] = float(SIS_spruce) if SIS_spruce is not None else None

        scaled_basal_area_plot: Optional[float] = None
        if basal_area_plot_m2_ha is not None:
            scaled_basal_area_plot = float(basal_area_plot_m2_ha) * 0.01 
            if scaled_basal_area_plot < 0:
                 raise ValueError("basal_area_plot_m2_ha cannot result in negative scaled value.")

        processed_basal_area_relascope: Optional[float] = None
        if basal_area_relascope_m2_ha is not None:
            processed_basal_area_relascope = float(basal_area_relascope_m2_ha)
            if processed_basal_area_relascope < 0:
                 raise ValueError("basal_area_relascope_m2_ha cannot be negative.")
        elif scaled_basal_area_plot is not None: 
            processed_basal_area_relascope = scaled_basal_area_plot

        local_qmd_cm: Optional[float] = None
        if QMD_cm is not None:
            local_qmd_cm = float(QMD_cm)
            if local_qmd_cm <=0: raise ValueError("QMD_cm must be > 0 if provided.")
        elif processed_basal_area_relascope is not None and stems_ha is not None:
            val_stems_ha = int(stems_ha)
            if val_stems_ha > 0 and processed_basal_area_relascope >=0: 
                denominator = (pi / 40000.0) * val_stems_ha 
                if denominator > 0: local_qmd_cm = sqrt(processed_basal_area_relascope / denominator)
        
        actual_field_layer_vegetation: Vegetation
        if isinstance(field_layer, SwedenFieldLayer): actual_field_layer_vegetation = field_layer.value
        elif isinstance(field_layer, Vegetation): actual_field_layer_vegetation = field_layer
        else: 
            try: 
                code = int(field_layer)
                found_sfl = next((sfl_member.value for sfl_member in SwedenFieldLayer if sfl_member.value.code == code), None)
                actual_field_layer_vegetation = found_sfl or SwedenFieldLayer.BILBERRY.value 
            except (ValueError, TypeError): actual_field_layer_vegetation = SwedenFieldLayer.BILBERRY.value 
        
        return _ModelParams(
            d_cm=d_cm, species_obj=species_obj,
            processed_total_stand_age=processed_total_stand_age, sis=processed_sis,
            field_layer_vegetation=actual_field_layer_vegetation,
            processed_basal_area_plot_m2_ha=scaled_basal_area_plot,
            processed_basal_area_relascope_m2_ha=processed_basal_area_relascope,
            altitude_m=float(altitude_m), latitude=float(latitude),
            local_qmd_cm=local_qmd_cm, stems_ha=stems_ha,
            is_uneven_aged_override=is_uneven_aged_override,
            dominant_mean_diameter_override=dominant_mean_diameter_override,
            is_standard_override=is_standard_override,
            is_undergrowth_override=is_undergrowth_override,
            is_gotland_override=is_gotland_override,
            is_ditched_override=is_ditched_override,
            is_peat_soil_override=is_peat_soil_override,
            is_shade_tolerant_broadleaf_override=is_shade_tolerant_broadleaf_override # Added
        )

    @staticmethod
    def _determine_calculation_group(params: _ModelParams) -> int:
        is_standard = params.is_standard_override if params.is_standard_override is not None else params.is_standard_tree
        if is_standard: return 9
        
        if params.is_uneven_aged_override: return 4
        
        if params.processed_total_stand_age is not None:
            return 2 
        else: 
            return 3 

        # This fallback logic is now unlikely to be reached due to explicit Group 2/3 selection above.
        # Kept for conceptual completeness or if Group 2/3 selection criteria changes.
        species = params.species_obj
        is_pine_or_larch = False
        if hasattr(TreeSpecies.Sweden, 'pinus') and isinstance(TreeSpecies.Sweden.pinus, RegionalGenusGroup) and species in TreeSpecies.Sweden.pinus: is_pine_or_larch = True
        elif hasattr(TreeSpecies.Sweden, 'larix') and isinstance(TreeSpecies.Sweden.larix, RegionalGenusGroup) and species in TreeSpecies.Sweden.larix: is_pine_or_larch = True
        
        if is_pine_or_larch: return 5
        if species == TreeSpecies.Sweden.picea_abies: return 6
        if hasattr(TreeSpecies.Sweden, 'betula') and isinstance(TreeSpecies.Sweden.betula, RegionalGenusGroup) and species in TreeSpecies.Sweden.betula: return 7
        
        return 8 

    @staticmethod
    def _calculate_ln_a13_group2(p: _ModelParams, c: Tuple[float, ...]) -> float: 
        if p.processed_total_stand_age is None or p.processed_total_stand_age <=0: raise ValueError("G2: positive total_stand_age.")
        if p.dfrel_ratio is None: raise ValueError("G2: dfrel_ratio (d/md).")
        if p.sis is None: raise ValueError("G2: sis (H100 Spruce).")
        if p.log_processed_basal_area_plot is None: raise ValueError("G2: log_processed_basal_area_plot (ln g).")
        likald_indicator = 1 
        return (
            c[0] + c[1]*p.log_d_cm + c[2]*p.d_cm + c[3]*p.dfrel_ratio                         
            + c[4]*log(p.processed_total_stand_age) + c[5]*p.is_pine_flag                       
            + c[6]*p.is_light_decid_flag + c[7]*p.sis                                
            + c[8]*p.sis*p.is_spruce_flag + c[9]*p.temperature_sum                    
            + c[10]*p.temperature_sum**2 + c[11]*p.is_ost_flag                       
            + c[12]*p.is_sma_flag + c[13]*likald_indicator                    
            + c[14]*p.log_processed_basal_area_plot + c[15]*p.is_gotland_flag                   
            + c[16]*p.is_rich_site_flag + c[17]*p.is_poor_site_flag                 
        )
    
    @staticmethod
    def _calculate_ln_a13_group3(p: _ModelParams, c: Tuple[float, ...]) -> float:
        if p.diameter_qmd_ratio is None: raise ValueError("G3: diameter_qmd_ratio (reld for d/QMD).")
        if p.sis is None: raise ValueError("G3: sis (H100 Spruce).")
        if p.log_inverted_relascope_ba_plus_1 is None: raise ValueError("G3: log_inverted_relascope_ba_plus_1 (lngfp1).")
        sid2gt_term_value = 0.0 # TODO: Clarify calculation for sid2gt (c[9]) if non-zero.
        return (
            c[0] + c[1]*p.log_d_cm + c[2]*p.diameter_qmd_ratio + c[3]*(p.diameter_qmd_ratio**2)                
            + c[4]*p.is_pine_flag + c[5]*p.is_bokek_flag + c[6]*p.is_light_decid_flag                      
            + c[7]*p.sis + c[8]*p.sis*p.is_spruce_flag + c[9]*sid2gt_term_value                          
            + c[10]*p.temperature_sum + c[11]*p.is_ost_flag + c[12]*p.is_sma_flag                             
            + c[13]*p.log_inverted_relascope_ba_plus_1 + c[14]*p.is_gotland_flag                         
            + c[15]*p.is_rich_site_flag + c[16]*p.is_poor_site_flag                       
            + c[17]*p.is_ditched_flag + c[18]*p.is_peat_soil_flag                       
        )

    @staticmethod
    def _calculate_ln_a13_group4(p: _ModelParams, c: Tuple[float, ...]) -> float: 
        if p.processed_total_stand_age is None or p.processed_total_stand_age <=0: raise ValueError("G4: positive total_stand_age.")
        if p.dfrel_ratio is None: raise ValueError("G4: dfrel_ratio (d/md).")
        if p.log_processed_basal_area_plot is None: raise ValueError("G4: log_processed_basal_area_plot (ln g).")
        if p.sis is None: raise ValueError("G4: sis (H100 Spruce).")
        return (
            c[0] + c[1]*p.log_d_cm + c[2]*p.d_cm + c[3]*p.dfrel_ratio 
            + c[4]*log(p.processed_total_stand_age) + c[5]*p.processed_total_stand_age
            + c[6]*p.is_bokek_flag + c[7]*p.is_light_decid_flag + c[8]*p.sis
            + c[9]*p.sis*p.d_cm + c[10]*p.sis*p.is_spruce_flag + c[11]*p.temperature_sum
            + c[12]*p.temperature_sum**2 + c[13]*p.log_processed_basal_area_plot
            + c[14]*p.is_rich_site_flag + c[15]*p.is_poor_site_flag
            + c[16]*p.is_ditched_flag + c[17]*p.is_gotland_flag 
        )

    @staticmethod
    def _calculate_ln_a13_group5(p: _ModelParams, c: Tuple[float, ...]) -> float: 
        if p.processed_total_stand_age is None or p.processed_total_stand_age <=0: raise ValueError("G5: positive total_stand_age.")
        if p.dfrel_ratio is None: raise ValueError("G5: dfrel_ratio (d/md).")
        if p.log_processed_basal_area_plot is None: raise ValueError("G5: log_processed_basal_area_plot (ln g).")
        return (
            c[0] + c[1]*p.log_d_cm + c[2]*p.d_cm + c[3]*p.dfrel_ratio
            + c[4]*log(p.processed_total_stand_age) + c[5]*p.processed_total_stand_age
            + c[6]*p.log_processed_basal_area_plot
        )

    @staticmethod
    def _calculate_ln_a13_group6(p: _ModelParams, c: Tuple[float, ...]) -> float: 
        if p.processed_total_stand_age is None or p.processed_total_stand_age <=0: raise ValueError("G6: positive total_stand_age.")
        if p.diameter_qmd_ratio is None: raise ValueError("G6: diameter_qmd_ratio (d/QMD).")
        if p.log_processed_basal_area_plot is None: raise ValueError("G6: log_processed_basal_area_plot (ln g).")
        return (
            c[0] + c[1]*p.log_d_cm + c[2]*p.d_cm + c[3]*p.diameter_qmd_ratio
            + c[4]*log(p.processed_total_stand_age) + c[5]*p.log_processed_basal_area_plot
        )

    @staticmethod
    def _calculate_ln_a13_group7(p: _ModelParams, c: Tuple[float, ...]) -> float: 
        if p.processed_total_stand_age is None or p.processed_total_stand_age <=0: raise ValueError("G7: positive total_stand_age.")
        if p.diameter_qmd_ratio is None: raise ValueError("G7: diameter_qmd_ratio (d/QMD).")
        if p.sis is None: raise ValueError("G7: sis (H100 Spruce).")
        if p.log_inverted_relascope_ba_plus_1 is None: raise ValueError("G7: log_inverted_relascope_ba_plus_1 (ln(Gf+1)).")
        return (
            c[0] + c[1]*p.log_d_cm + c[2]*p.d_cm + c[3]*p.diameter_qmd_ratio
            + c[4]*log(p.processed_total_stand_age) + c[5]*p.sis
            + c[6]*p.is_rich_site_flag + c[7]*p.log_inverted_relascope_ba_plus_1
        )

    @staticmethod
    def _calculate_ln_a13_group8(p: _ModelParams, c: Tuple[float, ...]) -> float: 
        if p.processed_total_stand_age is None or p.processed_total_stand_age <=0: raise ValueError("G8: positive total_stand_age.")
        if p.dfrel_ratio is None: raise ValueError("G8: dfrel_ratio (d/md).")
        return ( # slov is c[4]
            c[0] + c[1]*p.log_d_cm + c[2]*p.dfrel_ratio
            + c[3]*log(p.processed_total_stand_age) 
            + c[4]*p.is_shade_tolerant_broadleaf_flag # Using the new flag for slov
            + c[5]*p.is_light_decid_flag
        )

    @staticmethod
    def _calculate_ln_a13_group9(p: _ModelParams, c: Tuple[float, ...]) -> float: 
        if p.processed_total_stand_age is None : raise ValueError("G9: total_stand_age is required (used as 'bald').") 
        if p.sis is None: raise ValueError("G9: sis (H100 Spruce).")
        return (
            c[0] + c[1]*p.log_d_cm + c[2]*p.d_cm
            + c[3]*p.processed_total_stand_age + c[4]*p.sis 
            + c[5]*p.is_light_decid_flag
        )

    _GROUP_CALCULATORS: Dict[int, _CalculatorFunc] = {
        2: _calculate_ln_a13_group2, 3: _calculate_ln_a13_group3, 
        4: _calculate_ln_a13_group4, 5: _calculate_ln_a13_group5, 
        6: _calculate_ln_a13_group6, 7: _calculate_ln_a13_group7, 
        8: _calculate_ln_a13_group8, 9: _calculate_ln_a13_group9,
    }

    @staticmethod
    def age(
        *,
        diameter: Number, species: str | TreeName, 
        total_stand_age: Optional[Number] = None, SIS: Optional[Number] = None, 
        field_layer: Any = SwedenFieldLayer.BILBERRY, 
        basal_area_plot_m2_ha: Optional[Number] = None, 
        basal_area_relascope_m2_ha: Optional[Number] = None, 
        altitude_m: Number = 100, latitude: Number = 64, 
        QMD_cm: Optional[Number] = None, stems_ha: Optional[int] = None, 
        is_uneven_aged: Optional[bool] = None, 
        dominant_mean_diameter: Optional[Number] = None, 
        is_standard_tree_hint: Optional[bool] = None, 
        is_undergrowth_tree_hint: Optional[bool] = None,
        is_gotland: Optional[bool] = None,
        is_ditched: Optional[bool] = None, 
        is_peat_soil: Optional[bool] = None,
        is_shade_tolerant_broadleaf_hint: Optional[bool] = None # Added
    ) -> float:
        """Return breast-height age (yrs) for a single tree."""
        params = Elfving2003SingleTreeAge._prepare_model_params(
            diameter=diameter, species_input=species,
            total_stand_age=total_stand_age, SIS_spruce=SIS,
            field_layer=field_layer,
            basal_area_plot_m2_ha=basal_area_plot_m2_ha,
            basal_area_relascope_m2_ha=basal_area_relascope_m2_ha,
            altitude_m=altitude_m, latitude=latitude,
            QMD_cm=QMD_cm, stems_ha=stems_ha,
            is_uneven_aged_override=is_uneven_aged,
            dominant_mean_diameter_override=dominant_mean_diameter,
            is_standard_override=is_standard_tree_hint,
            is_undergrowth_override=is_undergrowth_tree_hint,
            is_gotland_override=is_gotland,
            is_ditched_override=is_ditched,
            is_peat_soil_override=is_peat_soil,
            is_shade_tolerant_broadleaf_override=is_shade_tolerant_broadleaf_hint # Added
        )
        group = Elfving2003SingleTreeAge._determine_calculation_group(params)

        if group not in Elfving2003SingleTreeAge._COEFFS or group not in Elfving2003SingleTreeAge._BIAS:
            raise NotImplementedError(f"Coefficients or bias for group {group} is not defined.")
        
        coeffs = Elfving2003SingleTreeAge._COEFFS[group]
        bias = Elfving2003SingleTreeAge._BIAS[group]
        calculator = Elfving2003SingleTreeAge._GROUP_CALCULATORS.get(group)

        if calculator is None:
            raise NotImplementedError(f"No calculator function defined for group {group}.")

        ln_a13 = calculator(params, coeffs) + bias
        a13 = exp(ln_a13)

        if not (0 < a13 < 1000): 
            raise ArithmeticError(
                f"Computed tree age ({a13:.2f} yrs for group {group}) is implausible; check inputs."
            )
        return a13

    @staticmethod
    def _get_vegetation_code(field_layer_input: Any) -> Optional[int]:
        if field_layer_input is None: return None
        if isinstance(field_layer_input, SwedenFieldLayer): return field_layer_input.value.code
        if isinstance(field_layer_input, Vegetation): return field_layer_input.code
        try: return int(field_layer_input)
        except (ValueError, TypeError): return None 

    @staticmethod
    def _is_rich_site(field_layer_input: Any) -> int:
        code = Elfving2003SingleTreeAge._get_vegetation_code(field_layer_input)
        if code is None: return 0 
        return 1 if (1 <= code <= 9 or code == 12) else 0

    @staticmethod
    def _is_poor_site(field_layer_input: Any) -> int:
        code = Elfving2003SingleTreeAge._get_vegetation_code(field_layer_input)
        if code is None: return 0 
        return 1 if code > 13 else 0

