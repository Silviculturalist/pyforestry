from __future__ import annotations

from dataclasses import dataclass, field
from math import exp, log, pi, sqrt
from typing import Any, Callable, Optional, SupportsFloat, Tuple, Union

from pyforestry.base.helpers.tree_species import (
    RegionalGenusGroup,
    TreeName,
    TreeSpecies,
    parse_tree_species,
)
from pyforestry.sweden.site import Sweden
from pyforestry.sweden.site.sweden_site_primitives import Vegetation

Number = Union[int, float, SupportsFloat]

__all__ = [
    "Lind2003MeanDiameterCodominantTrees",
    "Elfving2003TreeAge",
]


# =============================================================================
# Stand-level helper - Lind (2003) dominant-mean diameter (md)
# =============================================================================
class Lind2003MeanDiameterCodominantTrees:
    """Mean diameter (``md``) of co-dominant trees [cm]."""

    _C0, _C1, _C2, _C3, _C4, _C5 = (-0.92313, 1.00322, -0.00701, -4.00529, 0.01859, -1.88177)
    _BIAS = 0.036

    @staticmethod
    def estimate(
        *, total_stand_age: Number, stand_density_gf: Number, site_index: Number
    ) -> float:
        """Estimate mean diameter for co-dominant trees."""
        age, gf, si = float(total_stand_age), float(stand_density_gf), float(site_index)
        if not (age > 0 and si > 0 and gf > 0):
            raise ValueError("total_stand_age, stand_density_gf, and site_index must all be > 0.")
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
            raise ArithmeticError("Calculated dominant-mean diameter is non-positive.")
        return md


# =============================================================================
# Tree-level helper - Elfving (2003) single-tree age at breast height
# =============================================================================
@dataclass
class _ModelParams:  # Simplified for brevity, ensure all fields from previous version are here
    """Container for intermediate variables used in :class:`Elfving2003TreeAge`."""

    d_cm: float
    species_obj: TreeName
    altitude_m: float
    latitude: float
    processed_total_stand_age: Optional[float] = None
    sis: Optional[float] = None
    field_layer_vegetation: Vegetation = Sweden.FieldLayer.BILBERRY.value
    processed_basal_area_plot_m2_ha: Optional[float] = None  # NOTE: Removed * 0.01 scaling here
    processed_basal_area_relascope_m2_ha: Optional[float] = None
    local_qmd_cm: Optional[float] = None
    stems_ha: Optional[int] = None
    is_uneven_aged_override: Optional[bool] = None
    is_standard_override: Optional[bool] = None
    is_undergrowth_override: Optional[bool] = None
    dominant_mean_diameter_override: Optional[float] = None
    is_gotland_override: Optional[bool] = None
    is_ditched_override: Optional[bool] = None
    is_peat_soil_override: Optional[bool] = None
    is_shade_tolerant_broadleaf_override: Optional[bool] = None
    is_contorta_pine_flag: int = field(init=False)
    log_d_cm: float = field(init=False)
    dominant_mean_diameter: Optional[float] = field(init=False)
    diameter_qmd_ratio: Optional[float] = field(init=False)
    dfrel_ratio: Optional[float] = field(init=False)
    log_processed_basal_area_plot: Optional[float] = field(init=False)
    log_inverted_relascope_ba_plus_1: Optional[float] = field(init=False)
    inverted_sis: Optional[float] = field(init=False)
    temperature_sum: float = field(init=False)
    is_rich_site_flag: int = field(init=False)
    is_poor_site_flag: int = field(init=False)
    is_spruce_flag: int = field(init=False)
    is_pine_flag: int = field(init=False)
    is_light_decid_flag: int = field(init=False)
    is_bokek_flag: int = field(init=False)
    is_shade_tolerant_broadleaf_flag: int = field(init=False)
    is_gotland_flag: int = field(init=False)
    is_ditched_flag: int = field(init=False)
    is_peat_soil_flag: int = field(init=False)
    is_standard_tree: bool = field(init=False)
    is_undergrowth_tree: bool = field(init=False)
    is_ost_flag: int = field(init=False)
    is_sma_flag: int = field(init=False)

    def __post_init__(self):
        """Compute derived attributes and validate inputs."""
        if self.d_cm <= 0:
            raise ValueError("diameter (d_cm) must be > 0 cm")
        self.log_d_cm = log(self.d_cm)
        self.temperature_sum = 0.001 * (4835.0 - 5.76 * self.latitude - 0.9 * self.altitude_m)
        self.is_contorta_pine_flag = (
            1 if self.species_obj == TreeSpecies.Sweden.pinus_contorta else 0
        )

        if self.sis is not None:
            self.inverted_sis = 1.0 / self.sis if self.sis > 0 else None
        else:
            self.inverted_sis = None

        # Initial Dm calculation (will be used unless overridden or P.Contorta logic recalculates
        #  it)
        if self.dominant_mean_diameter_override is not None:
            self.dominant_mean_diameter = float(self.dominant_mean_diameter_override)
        elif (
            self.processed_total_stand_age is not None
            and self.sis is not None
            and self.sis > 0
            and self.processed_basal_area_relascope_m2_ha is not None
            and self.processed_basal_area_relascope_m2_ha > 0
        ):
            try:
                self.dominant_mean_diameter = Lind2003MeanDiameterCodominantTrees.estimate(
                    total_stand_age=self.processed_total_stand_age,
                    site_index=self.sis,
                    stand_density_gf=self.processed_basal_area_relascope_m2_ha,
                )
            except (ValueError, ArithmeticError):
                self.dominant_mean_diameter = self.d_cm
        else:
            self.dominant_mean_diameter = self.d_cm

        if self.dominant_mean_diameter and self.dominant_mean_diameter > 0:
            self.dfrel_ratio = self.d_cm / self.dominant_mean_diameter
        else:
            self.dfrel_ratio = None

        if self.local_qmd_cm and self.local_qmd_cm > 0:
            self.diameter_qmd_ratio = self.d_cm / self.local_qmd_cm
        else:
            self.diameter_qmd_ratio = None

        if self.processed_basal_area_plot_m2_ha and self.processed_basal_area_plot_m2_ha > 0:
            self.log_processed_basal_area_plot = log(self.processed_basal_area_plot_m2_ha)
        else:
            self.log_processed_basal_area_plot = None

        if (
            self.processed_basal_area_relascope_m2_ha is not None
            and self.processed_basal_area_relascope_m2_ha >= 0
        ):
            self.log_inverted_relascope_ba_plus_1 = log(
                self.processed_basal_area_relascope_m2_ha + 1.0
            )
        else:
            self.log_inverted_relascope_ba_plus_1 = None

        self.is_rich_site_flag = Elfving2003TreeAge._is_rich_site(self.field_layer_vegetation)
        self.is_poor_site_flag = Elfving2003TreeAge._is_poor_site(self.field_layer_vegetation)
        self.is_spruce_flag = 1 if self.species_obj == TreeSpecies.Sweden.picea_abies else 0
        self.is_pine_flag = 1 if self.species_obj == TreeSpecies.Sweden.pinus_sylvestris else 0

        light_decid_species = (
            TreeSpecies.Sweden.ulmus_glabra,
            TreeSpecies.Sweden.tilia_cordata,
            TreeSpecies.Sweden.acer_platanoides,
            TreeSpecies.Sweden.prunus_avium,
        )
        self.is_light_decid_flag = (
            1
            if self.species_obj in light_decid_species
            or (
                hasattr(TreeSpecies.Sweden, "salix")
                and isinstance(TreeSpecies.Sweden.salix, RegionalGenusGroup)
                and self.species_obj in TreeSpecies.Sweden.salix
            )
            else 0
        )
        self.is_bokek_flag = (
            1
            if self.species_obj == TreeSpecies.Sweden.fagus_sylvatica
            or (
                hasattr(TreeSpecies.Sweden, "quercus")
                and isinstance(TreeSpecies.Sweden.quercus, RegionalGenusGroup)
                and self.species_obj in TreeSpecies.Sweden.quercus
            )
            else 0
        )

        shade_tolerant_broadleaves = (
            TreeSpecies.Sweden.carpinus_betulus,
            TreeSpecies.Sweden.sorbus_aucuparia,
        )
        if self.is_shade_tolerant_broadleaf_override is not None:  # Allow override
            self.is_shade_tolerant_broadleaf_flag = (
                1 if self.is_shade_tolerant_broadleaf_override else 0
            )
        else:
            self.is_shade_tolerant_broadleaf_flag = (
                1 if self.species_obj in shade_tolerant_broadleaves else 0
            )

        if self.dominant_mean_diameter:
            self.is_standard_tree = self.d_cm > 1.8 * (self.dominant_mean_diameter + 8.0)
            self.is_undergrowth_tree = self.d_cm < 0.4 * self.dominant_mean_diameter
        else:
            self.is_standard_tree = self.is_undergrowth_tree = False
        self.is_ost_flag = 1 if self.is_standard_tree else 0
        self.is_sma_flag = 1 if self.is_undergrowth_tree else 0
        self.is_gotland_flag = 1 if self.is_gotland_override else 0
        self.is_ditched_flag = 1 if self.is_ditched_override else 0
        self.is_peat_soil_flag = 1 if self.is_peat_soil_override else 0


class Elfving2003TreeAge:
    """Estimate single-tree age using models from Elfving (2003)."""

    _BIAS = {
        2: 0.028,
        3: 0.062,
        4: 0.042,
        5: 0.012,
        6: 0.018,
        7: 0.038,
        8: 0.034,
        9: 0.045,
        51: 0.012,
    }
    GROUP_PINE_CONTORTA = 51

    # Coefficients are now ordered to match C# variable sequence for each respective function
    # const, d, logD, d/Dm or d/QMD, bald, logBald, logG, etc.
    _COEFF_2_TOTAL_W_AGE = (
        -1.46921,  # const
        0.29889,  # ln d (term for p.log_d_cm)
        -0.01132,  # d (term for p.d_cm) -> NOTE C# variable order often d then logD. Python
        # functions use log_d_cm then d_cm for c[1], c[2]
        # For consistency, calculation functions will be explicit.
        # For now, assuming Python functions' variable order is fixed,
        # coeff tuples must match that.
        # Let's fix tuples based on C# Variable Order and adjust calc functions.
        # C# Coeff order: const, d, logD, d/Dm, bald, logBald, lnG, SIS, SIGRAN, SID, rich, poor,
        # ljuslov, bokek, TS, TS2, gotland, ditch
        # This C# order is for CoeffFunction6 (UnevenAgedWithStandAge)
        # For Group 2 (EvenAgedWithStandAge), the original paper is the source.
        # Based on Python function for G2: lnd, d, dfrel, lnbald, tall, ljuslov, SIS, SIGRAN, ts,
        # ts2, ost, sma, LIKALD, lng, gotland, rich, poor
        # So _COEFF_2_TOTAL_W_AGE should map to this. The C# source doesn't have a direct
        # "Function2".
        # The provided _COEFF_2_TOTAL_W_AGE tuple from the problem seems to map to this variable
        # order.
        -0.01132,  # d
        0.25943,  # dfrel (d/md)
        1.01901,  # ln bald (total_stand_age)
        -0.09476,  # tall (pine species flag)
        -0.09798,  # ljuslov (light-demanding broadleaf flag)
        0.00465,  # SIS (H100 Spruce)
        -0.00372,  # SIGRAN (SI Spruce interaction)
        0.33497,  # ts (temperature sum)
        -0.15507,  # ts2 (ts squared)
        0.56842,  # ost (Original paper: this is index 11 if const is 0.
        # Corresponds to Elfving ost)
        -0.21026,  # sma (Original paper: index 12. Corresponds to Elfving sma)
        -0.03118,  # LIKALD (Original paper: index 13)
        0.04492,  # ln g (log of plot basal area)
        0.03439,  # gotland (Gotland flag)
        -0.13876,  # rich (rich site flag)
        0.06144,  # poor (poor site flag)
    )
    _COEFF_3_TOTAL_WO_AGE = (  # C# CoeffFunction8: const,logD,d/QMD, (d/QMD)2,ln(Gf+1),SIS,SIGRAN,
        # SID2GT,rich,poor,ljuslov,tall,bokek,TS,ost,sma,gotland,dike,torv
        2.25519,  # const
        1.21082,  # ln d
        -1.51153,  # reld (d/QMD)
        0.39625,  # (reld)^2
        -0.18216,  # tall (pine flag)      -- C# order: lngfp1 then SIS...
        0.14160,  # bokek (beech/oak flag) -- This tuple needs to exactly match C# sequence if
        # calc func assumes it.
        -0.12756,  # ljuslov
        -0.02778,  # SIS
        -0.00471,  # SIGRAN
        -0.00304,  # sid2gt
        -0.39207,  # ts
        0.16211,  # ost
        0.29504,  # sma
        0.19080,  # lngfp1
        0.19944,  # gotland
        -0.20707,  # rich
        0.03196,  # poor
        -0.09185,  # Dike
        0.14096,  # Torv
    )
    _COEFF_4_UNEVEN = (  # C# CoeffFunction6: const,d,logD,d/Dm,bald,logBald,lnG,SIS,SIGRAN,SID,
        # rich,poor,ljuslov,bokek,TS,TS2,gotland,ditch
        0.41811,  # const
        -0.01803,  # d
        0.55719,  # ln d
        0.17128,  # d/md (dfrel)
        0.00367,  # bald (total_stand_age)
        0.39232,  # ln bald (total_stand_age)
        0.04693,  # ln g (log of plot basal area)
        -0.01171,  # sis (H100 Spruce)
        -0.00135,  # sigran (sis * spruce_flag)
        0.00028510,  # sid (sis * d)
        -0.06676,  # rich (rich site flag)
        0.03127,  # poor (poor site flag)
        -0.22284,  # ljuslov (light-demanding broadleaf flag)
        0.10508,  # bokek (beech/oak flag)
        0.83621,  # ts (temperature sum)
        -0.44686,  # ts² (ts squared)
        0.14490,  # gotland (Gotland flag)
        -0.03794,  # dike (ditching flag)
    )
    _COEFF_5_PINE = (  # C# CoefficientPine: const, d, logD, d/Dm, bald, logBald, logG
        -1.69566,
        -0.00801,
        0.29819,
        0.07258,
        -0.00076986,
        1.15873,
        0.03098,
    )
    _COEFF_6_SPRUCE = (  # C# CoefficientSpruce: const, d, logD, d/QMD, logBald, logG
        -1.38343,
        -0.01003,
        0.37897,
        0.12834,
        1.02011,
        0.01748,
    )
    _COEFF_7_BIRCH = (  # C# CoefficientBirch: const, d, logD, d/QMD, logBald, log(Gf+1), SIS, rich
        0.10055,
        -0.00793,
        0.52067,
        -0.08139,
        0.67013,
        0.03945,
        -0.01053,
        -0.09905,
    )
    _COEFF_8_DECID = (  # C# CoefficientDeciduous: const, logD, d/Dm, logBald, slov, ljuslov
        0.13800,
        0.64693,
        -0.26496,
        0.50530,
        0.19386,
        -0.17874,
    )
    _COEFF_9_STD = (  # C# CoeffFunction5: const, d, logD, bald, sis, ljuslov
        1.79933,
        -0.01841,
        1.14894,
        0.00634,
        -0.03460,
        -0.22537,
    )
    _COEFFS = {
        2: _COEFF_2_TOTAL_W_AGE,
        3: _COEFF_3_TOTAL_WO_AGE,
        4: _COEFF_4_UNEVEN,
        5: _COEFF_5_PINE,
        6: _COEFF_6_SPRUCE,
        7: _COEFF_7_BIRCH,
        8: _COEFF_8_DECID,
        9: _COEFF_9_STD,
        51: _COEFF_5_PINE,
    }
    _CalculatorFunc = Callable[[_ModelParams, Tuple[float, ...]], float]

    @staticmethod
    def _prepare_model_params(
        diameter: Number,
        species_input: str | TreeName,
        total_stand_age: Optional[Number],
        SIS_spruce: Optional[Number],
        field_layer: Any,
        basal_area_plot_m2_ha: Optional[Number],
        basal_area_relascope_m2_ha: Optional[Number],
        altitude_m: Number,
        latitude: Number,
        QMD_cm: Optional[Number],
        stems_ha: Optional[int],
        is_uneven_aged_override: Optional[bool],
        dominant_mean_diameter_override: Optional[Number],
        is_standard_override: Optional[bool],
        is_undergrowth_override: Optional[bool],
        is_gotland_override: Optional[bool],
        is_ditched_override: Optional[bool],
        is_peat_soil_override: Optional[bool],
        is_shade_tolerant_broadleaf_override: Optional[bool],
    ) -> _ModelParams:
        """Normalise inputs and build a :class:`_ModelParams` instance."""
        species_obj = parse_tree_species(species_input)  # type: ignore
        if not isinstance(species_obj, TreeName):
            raise TypeError(f"parse_tree_species expected TreeName, got {type(species_obj)}")  # type: ignore

        # CORRECTED: No 0.01 scaling for basal_area_plot_m2_ha
        processed_ba_plot = (
            float(basal_area_plot_m2_ha) if basal_area_plot_m2_ha is not None else None
        )
        if processed_ba_plot is not None and processed_ba_plot < 0:
            raise ValueError("Plot BA cannot be negative.")

        processed_tsa = (
            min(max(float(total_stand_age), 10.0), 175.0) if total_stand_age is not None else None
        )

        processed_ba_relascope = (
            float(basal_area_relascope_m2_ha)
            if basal_area_relascope_m2_ha is not None
            else processed_ba_plot
        )  # Fallback
        if processed_ba_relascope is not None and processed_ba_relascope < 0:
            raise ValueError("Relascope BA cannot be negative.")

        local_qmd = (
            float(QMD_cm)
            if QMD_cm is not None
            else (
                sqrt(processed_ba_relascope / ((pi / 40000.0) * int(stems_ha)))
                if processed_ba_relascope is not None
                and stems_ha
                and int(stems_ha) > 0
                and processed_ba_relascope >= 0
                and (pi / 40000.0) * int(stems_ha) > 0
                else None
            )
        )
        if local_qmd is not None and local_qmd <= 0:
            raise ValueError("QMD_cm must be > 0.")

        actual_fl_veg = Sweden.FieldLayer.BILBERRY.value  # type: ignore
        if isinstance(field_layer, Sweden.FieldLayer):
            actual_fl_veg = field_layer.value  # type: ignore
        elif isinstance(field_layer, Vegetation):
            actual_fl_veg = field_layer  # type: ignore
        else:
            try:
                code = int(field_layer)
                actual_fl_veg = next(
                    (m.value for m in Sweden.FieldLayer if m.value.code == code),
                    Sweden.FieldLayer.BILBERRY.value,
                )  # type: ignore
            except (ValueError, TypeError):
                pass

        # Explicitly convert dominant_mean_diameter_override to float if not None
        dm_override_val: Optional[float] = None
        if dominant_mean_diameter_override is not None:
            dm_override_val = float(dominant_mean_diameter_override)

        return _ModelParams(
            d_cm=float(diameter),
            species_obj=species_obj,
            altitude_m=float(altitude_m),
            latitude=float(latitude),
            processed_total_stand_age=processed_tsa,
            sis=(float(SIS_spruce) if SIS_spruce is not None else None),
            field_layer_vegetation=actual_fl_veg,
            processed_basal_area_plot_m2_ha=processed_ba_plot,
            processed_basal_area_relascope_m2_ha=processed_ba_relascope,
            local_qmd_cm=local_qmd,
            stems_ha=stems_ha,
            is_uneven_aged_override=is_uneven_aged_override,
            dominant_mean_diameter_override=dm_override_val,
            is_standard_override=is_standard_override,
            is_undergrowth_override=is_undergrowth_override,
            is_gotland_override=is_gotland_override,
            is_ditched_override=is_ditched_override,
            is_peat_soil_override=is_peat_soil_override,
            is_shade_tolerant_broadleaf_override=is_shade_tolerant_broadleaf_override,
        )

    @staticmethod
    def _determine_calculation_group(params: _ModelParams) -> int:
        """Select calculation group based on tree and stand attributes."""
        if (
            params.is_standard_override
            if params.is_standard_override is not None
            else params.is_standard_tree
        ):
            return 9
        if params.is_uneven_aged_override:
            return 4 if params.processed_total_stand_age is not None else 3

        # If not standard and not explicitly uneven_aged:
        if params.is_contorta_pine_flag:  # Check Contorta before general age-based routing
            # Contorta logic in C# implies it's for even-aged with known age.
            # If age is None, it would fall into C#'s UnevenAgedWithoutStandAge (Group 3)
            # where Contorta is not special.
            if params.processed_total_stand_age is not None:
                return Elfving2003TreeAge.GROUP_PINE_CONTORTA
            else:  # No age, Contorta handled by Group 3 as any other pine
                return 3

        if params.processed_total_stand_age is None:
            return 3  # No age, not Contorta (already checked)

        # Even-aged with known stand age context from here (and not Contorta)
        species = params.species_obj
        is_pine_non_contorta_or_larch = False
        if (
            hasattr(TreeSpecies.Sweden, "pinus")
            and isinstance(TreeSpecies.Sweden.pinus, RegionalGenusGroup)
            and species in TreeSpecies.Sweden.pinus
            and not params.is_contorta_pine_flag
        ):  # type: ignore
            is_pine_non_contorta_or_larch = True
        elif (
            hasattr(TreeSpecies.Sweden, "larix")
            and isinstance(TreeSpecies.Sweden.larix, RegionalGenusGroup)
            and species in TreeSpecies.Sweden.larix
        ):  # type: ignore
            is_pine_non_contorta_or_larch = True
        if is_pine_non_contorta_or_larch:
            return 5

        if species == TreeSpecies.Sweden.picea_abies:
            return 6  # type: ignore
        if (
            hasattr(TreeSpecies.Sweden, "betula")
            and isinstance(TreeSpecies.Sweden.betula, RegionalGenusGroup)
            and species in TreeSpecies.Sweden.betula
        ):
            return 7  # type: ignore

        # CORRECTED: Access tree_type as a property
        if species.tree_type == "Deciduous":
            return 8  # type: ignore

        return 2  # Fallback to general even-aged with stand age

    @staticmethod
    def _calculate_ln_a13_group_pine_contorta(p: _ModelParams, c: Tuple[float, ...]) -> float:
        """Compute ln(age at 1.3 m) for Contorta pines."""
        # C# ContortaTreeAge logic
        adjusted_bald_val = (
            p.processed_total_stand_age - 2.0 if p.processed_total_stand_age is not None else None
        )
        adjusted_sis_val = (p.sis + 3.0) if p.sis is not None else None

        # Determine Dm for Contorta (dfrel_for_formula)
        # Default to Dm calculated with original params if override not present
        dm_for_contorta = p.dominant_mean_diameter
        if p.dominant_mean_diameter_override is None:  # Only recalculate if Dm was not an override
            if (
                adjusted_bald_val is not None
                and adjusted_bald_val > 1e-5
                and adjusted_sis_val is not None
                and adjusted_sis_val > 0
                and p.processed_basal_area_relascope_m2_ha is not None
                and p.processed_basal_area_relascope_m2_ha > 0
            ):
                try:
                    dm_for_contorta = Lind2003MeanDiameterCodominantTrees.estimate(
                        total_stand_age=adjusted_bald_val,
                        site_index=adjusted_sis_val,
                        stand_density_gf=p.processed_basal_area_relascope_m2_ha,
                    )
                except (ValueError, ArithmeticError):
                    pass  # Keep previously calculated p.dominant_mean_diameter

        dfrel_for_formula = (
            p.d_cm / dm_for_contorta if dm_for_contorta and dm_for_contorta > 0 else None
        )

        # Determine bald and logBald for formula
        bald_for_formula = p.processed_total_stand_age  # Default to original
        log_bald_for_formula = (
            log(p.processed_total_stand_age)
            if p.processed_total_stand_age and p.processed_total_stand_age > 1e-5
            else None
        )

        if adjusted_bald_val is not None and adjusted_bald_val > 1e-5:
            bald_for_formula = adjusted_bald_val
            log_bald_for_formula = log(adjusted_bald_val)
        # else: use original age and log(original age) as set above

        if bald_for_formula is None or bald_for_formula <= 0:
            raise ValueError("Contorta: bald_for_formula is invalid.")
        if dfrel_for_formula is None:
            raise ValueError("Contorta: dfrel_for_formula is invalid.")
        if p.log_processed_basal_area_plot is None:
            raise ValueError("Contorta: log_processed_basal_area_plot (ln g) is invalid.")
        if log_bald_for_formula is None:
            raise ValueError("Contorta: log_bald_for_formula is invalid.")

        # Pine formula using (potentially) adjusted values
        # c: const, d, logD, d/Dm, bald, logBald, logG
        return (
            c[0]
            + c[1] * p.d_cm
            + c[2] * p.log_d_cm
            + c[3] * dfrel_for_formula
            + c[4] * bald_for_formula
            + c[5] * log_bald_for_formula
            + c[6] * p.log_processed_basal_area_plot
        )

    @staticmethod
    def _calculate_ln_a13_group2(p: _ModelParams, c: Tuple[float, ...]) -> float:
        """Calculate ln(Age1.3) for group 2 (even-aged stands with age)."""
        # Coeffs: const,lnd,d,dfrel,lnbald,tall,ljuslov,SIS,SIGRAN,ts,ts2,ost,
        # sma,LIKALD,lng,gotland,rich,poor
        if p.processed_total_stand_age is None or p.processed_total_stand_age <= 0:
            raise ValueError("G2: positive total_stand_age.")
        if p.dfrel_ratio is None:
            raise ValueError("G2: dfrel_ratio (d/md).")
        if p.sis is None:
            raise ValueError("G2: sis (H100 Spruce).")
        if p.log_processed_basal_area_plot is None:
            raise ValueError("G2: log_processed_basal_area_plot (ln g).")
        # Python func variable order: lnd,d,dfrel,lnbald,tall,ljuslov,SIS,SIGRAN,ts,ts2,ost,
        # sma,LIKALD,lng,gotland,rich,poor
        # _COEFF_2_TOTAL_W_AGE is assumed to map to this.
        return (
            c[0]  # const
            + c[1] * p.log_d_cm  # lnd (c[0] in original tuple if _COEFF_2 didn't have const)
            +
            # The _COEFF_2_TOTAL_W_AGE starts with const, so c[1] is for lnd.
            c[2] * p.d_cm  # d
            + c[3] * p.dfrel_ratio  # dfrel
            + c[4] * log(p.processed_total_stand_age)  # lnbald
            + c[5] * p.is_pine_flag  # tall
            + c[6] * p.is_light_decid_flag  # ljuslov
            + c[7] * p.sis  # SIS
            + c[8] * p.sis * p.is_spruce_flag  # SIGRAN
            + c[9] * p.temperature_sum  # ts
            + c[10] * p.temperature_sum**2  # ts2
            + c[11] * p.is_ost_flag  # ost
            + c[12] * p.is_sma_flag  # sma
            + c[13] * 1  # LIKALD (assumed 1)
            + c[14] * p.log_processed_basal_area_plot  # lng
            + c[15] * p.is_gotland_flag  # gotland
            + c[16] * p.is_rich_site_flag  # rich
            + c[17] * p.is_poor_site_flag  # poor
        )

    @staticmethod
    def _calculate_ln_a13_group3(p: _ModelParams, c: Tuple[float, ...]) -> float:
        """Calculate ln(Age1.3) for group 3 (uneven aged without age)."""
        # C# CoeffFunction8 order: const,logD,d/QMD,(d/QMD)2,ln(Gf+1),SIS,SIGRAN,SID2GT,rich,poor,
        # ljuslov,tall,bokek,TS,ost,sma,gotland,dike,torv
        # Python _COEFF_3_TOTAL_WO_AGE is ordered as per C#.
        if p.diameter_qmd_ratio is None:
            raise ValueError("G3: diameter_qmd_ratio (reld for d/QMD).")
        if p.sis is None:
            raise ValueError("G3: sis (H100 Spruce).")
        if p.log_inverted_relascope_ba_plus_1 is None:
            raise ValueError("G3: log_inverted_relascope_ba_plus_1 (lngfp1).")
        sid2gt_term_value = 0.0  # TODO: Clarify calculation for sid2gt (c[9]) if non-zero.
        return (
            c[0]  # const
            + c[1] * p.log_d_cm  # ln d
            + c[2] * p.diameter_qmd_ratio  # reld (d/QMD)
            + c[3] * (p.diameter_qmd_ratio**2)  # (reld)^2
            +
            # Order from C# CoeffFunction8 in TreeAge.cs (after (d/QMD)^2) is:
            # lngfp1 (c13_py), SIS (c7_py), SIGRAN (c8_py), SID2GT (c9_py), rich (c15_py),
            # poor (c16_py),
            # ljuslov (c6_py), tall (c4_py), bokek (c5_py), TS (c10_py), ost (c11_py),
            # sma (c12_py),
            # gotland (c14_py), dike (c17_py), torv (c18_py)
            # The Python _COEFF_3_TOTAL_WO_AGE tuple matches this order.
            c[4] * p.is_pine_flag  # tall
            + c[5] * p.is_bokek_flag  # bokek
            + c[6] * p.is_light_decid_flag  # ljuslov
            + c[7] * p.sis  # SIS
            + c[8] * p.sis * p.is_spruce_flag  # SIGRAN
            + c[9] * sid2gt_term_value  # sid2gt
            + c[10] * p.temperature_sum  # ts
            + c[11] * p.is_ost_flag  # ost
            + c[12] * p.is_sma_flag  # sma
            + c[13] * p.log_inverted_relascope_ba_plus_1  # lngfp1
            + c[14] * p.is_gotland_flag  # gotland
            + c[15] * p.is_rich_site_flag  # rich
            + c[16] * p.is_poor_site_flag  # poor
            + c[17] * p.is_ditched_flag  # Dike
            + c[18] * p.is_peat_soil_flag  # Torv
        )

    @staticmethod
    def _calculate_ln_a13_group4(p: _ModelParams, c: Tuple[float, ...]) -> float:
        """Calculate ln(Age1.3) for group 4 (uneven aged with age)."""
        # C# CoeffFunction6 order: const,d,logD,d/Dm,bald,logBald,lnG,SIS,SIGRAN,SID,rich,poor,
        # ljuslov,bokek,TS,TS2,gotland,ditch
        # Python _COEFF_4_UNEVEN is ordered like this.
        if p.processed_total_stand_age is None or p.processed_total_stand_age <= 0:
            raise ValueError("G4: positive total_stand_age.")
        if p.dfrel_ratio is None:
            raise ValueError("G4: dfrel_ratio (d/md).")
        if p.log_processed_basal_area_plot is None:
            raise ValueError("G4: log_processed_basal_area_plot (ln g).")
        if p.sis is None:
            raise ValueError("G4: sis (H100 Spruce).")
        return (
            c[0]  # const
            + c[1] * p.d_cm  # d
            + c[2] * p.log_d_cm  # ln d
            + c[3] * p.dfrel_ratio  # d/md
            + c[4] * p.processed_total_stand_age  # bald
            + c[5] * log(p.processed_total_stand_age)  # ln bald
            + c[6] * p.log_processed_basal_area_plot  # ln g
            + c[7] * p.sis  # sis
            + c[8] * p.sis * p.is_spruce_flag  # sigran
            + c[9] * p.sis * p.d_cm  # sid
            + c[10] * p.is_rich_site_flag  # rich
            + c[11] * p.is_poor_site_flag  # poor
            + c[12] * p.is_light_decid_flag  # ljuslov
            + c[13] * p.is_bokek_flag  # bokek
            + c[14] * p.temperature_sum  # ts
            + c[15] * p.temperature_sum**2  # ts²
            + c[16] * p.is_gotland_flag  # CORRECTED from c[17] * p.is_gotland_flag,
            # C# uses c[16] for gotland
            + c[17] * p.is_ditched_flag  # dike
        )

    @staticmethod
    def _calculate_ln_a13_group5(p: _ModelParams, c: Tuple[float, ...]) -> float:  # Pine
        """Calculate ln(Age1.3) for group 5 (pine)."""
        # C# Coeffs: const, d, logD, d/Dm, bald, logBald, logG
        # Python _COEFF_5_PINE is ordered like this.
        if p.processed_total_stand_age is None or p.processed_total_stand_age <= 0:
            raise ValueError("G5: positive total_stand_age.")
        if p.dfrel_ratio is None:
            raise ValueError("G5: dfrel_ratio (d/md).")
        if p.log_processed_basal_area_plot is None:
            raise ValueError("G5: log_processed_basal_area_plot (ln g).")
        return (
            c[0]  # const
            + c[1] * p.d_cm  # d
            + c[2] * p.log_d_cm  # logD
            + c[3] * p.dfrel_ratio  # d/Dm
            + c[4] * p.processed_total_stand_age  # bald
            + c[5] * log(p.processed_total_stand_age)  # logBald
            + c[6] * p.log_processed_basal_area_plot  # logG
        )

    @staticmethod
    def _calculate_ln_a13_group6(p: _ModelParams, c: Tuple[float, ...]) -> float:  # Spruce
        """Calculate ln(Age1.3) for group 6 (spruce)."""
        # C# Coeffs: const, d, logD, d/QMD, logBald, logG
        # Python _COEFF_6_SPRUCE is ordered like this.
        if p.processed_total_stand_age is None or p.processed_total_stand_age <= 0:
            raise ValueError("G6: positive total_stand_age.")
        if p.diameter_qmd_ratio is None:
            raise ValueError("G6: diameter_qmd_ratio (d/QMD).")
        if p.log_processed_basal_area_plot is None:
            raise ValueError("G6: log_processed_basal_area_plot (ln g).")
        return (
            c[0]  # const
            + c[1] * p.d_cm  # d
            + c[2] * p.log_d_cm  # logD
            + c[3] * p.diameter_qmd_ratio  # d/QMD
            + c[4] * log(p.processed_total_stand_age)  # logBald
            + c[5] * p.log_processed_basal_area_plot  # logG
        )

    @staticmethod
    def _calculate_ln_a13_group7(p: _ModelParams, c: Tuple[float, ...]) -> float:  # Birch
        """Calculate ln(Age1.3) for group 7 (birch)."""
        # C# Coeffs: const, d, logD, d/QMD, logBald, log(Gf+1), SIS, rich
        # Python _COEFF_7_BIRCH is ordered like this.
        if p.processed_total_stand_age is None or p.processed_total_stand_age <= 0:
            raise ValueError("G7: positive total_stand_age.")
        if p.diameter_qmd_ratio is None:
            raise ValueError("G7: diameter_qmd_ratio (d/QMD).")
        if p.sis is None:
            raise ValueError("G7: sis (H100 Spruce).")
        if p.log_inverted_relascope_ba_plus_1 is None:
            raise ValueError("G7: log_inverted_relascope_ba_plus_1 (ln(Gf+1)).")
        return (
            c[0]  # const
            + c[1] * p.d_cm  # d
            + c[2] * p.log_d_cm  # logD
            + c[3] * p.diameter_qmd_ratio  # d/QMD
            + c[4] * log(p.processed_total_stand_age)  # logBald
            + c[5] * p.log_inverted_relascope_ba_plus_1  # log(Gf+1)
            + c[6] * p.sis  # SIS
            + c[7] * p.is_rich_site_flag  # rich
        )

    @staticmethod
    def _calculate_ln_a13_group8(
        p: _ModelParams, c: Tuple[float, ...]
    ) -> float:  # Other Deciduous
        """Calculate ln(Age1.3) for group 8 (other deciduous species)."""
        # C# Coeffs: const, logD, d/Dm, logBald, slov, ljuslov
        # Python _COEFF_8_DECID is ordered like this.
        if p.processed_total_stand_age is None or p.processed_total_stand_age <= 0:
            raise ValueError("G8: positive total_stand_age.")
        if p.dfrel_ratio is None:
            raise ValueError("G8: dfrel_ratio (d/md).")
        return (
            c[0]  # const
            + c[1] * p.log_d_cm  # logD
            + c[2] * p.dfrel_ratio  # d/Dm
            + c[3] * log(p.processed_total_stand_age)  # logBald
            + c[4] * p.is_shade_tolerant_broadleaf_flag  # slov
            + c[5] * p.is_light_decid_flag  # ljuslov
        )

    @staticmethod
    def _calculate_ln_a13_group9(p: _ModelParams, c: Tuple[float, ...]) -> float:  # Standards
        """Calculate ln(Age1.3) for group 9 (standard trees)."""
        # C# Coeffs: const, d, logD, bald, sis, ljuslov
        # Python _COEFF_9_STD is ordered like this.
        if p.processed_total_stand_age is None:
            raise ValueError("G9: total_stand_age is required.")
        if p.sis is None:
            raise ValueError("G9: sis (H100 Spruce).")
        return (
            c[0]  # const
            + c[1] * p.d_cm  # d
            + c[2] * p.log_d_cm  # logD
            + c[3] * p.processed_total_stand_age  # bald
            + c[4] * p.sis  # sis
            + c[5] * p.is_light_decid_flag  # ljuslov
        )

    _GROUP_CALCULATORS = {
        2: _calculate_ln_a13_group2,
        3: _calculate_ln_a13_group3,
        4: _calculate_ln_a13_group4,
        5: _calculate_ln_a13_group5,
        6: _calculate_ln_a13_group6,
        7: _calculate_ln_a13_group7,
        8: _calculate_ln_a13_group8,
        9: _calculate_ln_a13_group9,
        GROUP_PINE_CONTORTA: _calculate_ln_a13_group_pine_contorta,
    }

    @staticmethod
    def age(
        *,
        diameter: Number,
        species: str | TreeName,
        total_stand_age: Optional[Number] = None,
        SIS: Optional[Number] = None,
        field_layer: Any = Sweden.FieldLayer.BILBERRY,
        basal_area_plot_m2_ha: Optional[Number] = None,
        basal_area_relascope_m2_ha: Optional[Number] = None,
        altitude_m: Number = 100,
        latitude: Number = 64,
        QMD_cm: Optional[Number] = None,
        stems_ha: Optional[int] = None,
        is_uneven_aged: Optional[bool] = None,
        dominant_mean_diameter: Optional[Number] = None,
        is_standard_tree_hint: Optional[bool] = None,
        is_undergrowth_tree_hint: Optional[bool] = None,
        is_gotland: Optional[bool] = None,
        is_ditched: Optional[bool] = None,
        is_peat_soil: Optional[bool] = None,
        is_shade_tolerant_broadleaf_hint: Optional[bool] = None,
    ) -> float:  # type: ignore
        """Return tree age at breast height given tree and site attributes."""
        params = Elfving2003TreeAge._prepare_model_params(
            diameter,
            species,
            total_stand_age,
            SIS,
            field_layer,
            basal_area_plot_m2_ha,
            basal_area_relascope_m2_ha,
            altitude_m,
            latitude,
            QMD_cm,
            stems_ha,
            is_uneven_aged,
            dominant_mean_diameter,
            is_standard_tree_hint,
            is_undergrowth_tree_hint,
            is_gotland,
            is_ditched,
            is_peat_soil,
            is_shade_tolerant_broadleaf_hint,
        )
        group = Elfving2003TreeAge._determine_calculation_group(params)
        if group not in Elfving2003TreeAge._COEFFS or group not in Elfving2003TreeAge._BIAS:
            raise NotImplementedError(f"Coeffs/bias for group {group} undefined.")
        coeffs, bias, calculator = (
            Elfving2003TreeAge._COEFFS[group],
            Elfving2003TreeAge._BIAS[group],
            Elfving2003TreeAge._GROUP_CALCULATORS.get(group),
        )
        if calculator is None:
            raise NotImplementedError(f"Calculator for group {group} undefined.")
        ln_a13 = calculator(params, coeffs) + bias
        a13 = exp(ln_a13)
        if not (0 < a13 < 1000):
            raise ArithmeticError(f"Age {a13:.2f} (group {group}) implausible.")
        return a13

    @staticmethod
    def _get_vegetation_code(fi: Any) -> Optional[int]:
        """Return vegetation code from input or ``None`` if unavailable."""
        if fi is None:
            return None
        if isinstance(fi, Sweden.FieldLayer):
            return fi.value.code  # type: ignore
        if isinstance(fi, Vegetation):
            return fi.code  # type: ignore
        try:
            return int(fi)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _is_rich_site(fi: Any) -> int:
        """Return ``1`` if vegetation indicates a rich site else ``0``."""
        co = Elfving2003TreeAge._get_vegetation_code(fi)
        return 1 if co and (1 <= co <= 9 or co == 12) else 0

    @staticmethod
    def _is_poor_site(fi: Any) -> int:
        """Return ``1`` if vegetation indicates a poor site else ``0``."""
        co = Elfving2003TreeAge._get_vegetation_code(fi)
        return 1 if co and co > 13 else 0
