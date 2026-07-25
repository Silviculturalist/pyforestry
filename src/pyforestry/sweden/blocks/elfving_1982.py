"""Hugin young-stand survey functions, Elfving (1982) Rapport 27.

This module provides:
- Mean height / mean age functions for main saplings (Hugin height model).
- Crop-tree probability (Hugin cleaning proxy).
- NYSKOG reconstruction step functions for young-stand height distributions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Sequence

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers.tree import Tree
from pyforestry.base.helpers.tree_species import TreeName
from pyforestry.sweden.regeneration import elfving_1982 as _kernels
from pyforestry.sweden.site.enums import Sweden


class RegenerationType(Enum):
    """Regeneration type categories used in Hugin/NYSKOG functions."""

    NATURAL = "natural_regeneration"
    EXTENSIVE = "extensive"
    SOWN = "sown"
    PINE_PLANTATION = "pine_plantation"
    SPRUCE_PLANTATION = "spruce_plantation"
    CONTORTA_PLANTATION = "contorta_plantation"
    DECIDUOUS_PLANTATION = "deciduous_plantation"


class NfiRegion(Enum):
    """NFI region codes used in NYSKOG deciduous proportions."""

    REG1 = "Reg1"
    REG21 = "Reg21"
    REG22 = "Reg22"
    REG3 = "Reg3"
    REG4 = "Reg4"
    REG5 = "Reg5"


@dataclass(frozen=True)
class NyskogReconstructionSummary:
    """Summary outputs from the NYSKOG reconstruction workflow."""

    q: float
    qind: float
    udim: float
    stem_total: float
    prop_conifer: float
    prop_dom_conifer: float
    stems_per_species: dict[str, float]
    mean_heights_m: dict[str, float]
    cvh: dict[str, float]
    weibull_params: dict[str, tuple[float, float]]
    main_species_key: str


class HuginMeanHeightModel:
    """Mean height and mean age functions for main saplings (Hugin 1982).

    The model is defined as:
        H = SI / (exp(Y) + 1)
        Y = b0 + b1 * ln(A) + b2 * ln(A)^2

    where A is total age (years) and SI is species-specific site index (m).
    """

    @staticmethod
    def site_index_for_species(
        species: TreeName, *, site_index_pine_m: float, site_index_spruce_m: float
    ) -> float:
        """Translate pine/spruce site indices to a species-specific site index.

        Args:
            species (TreeName): Tree species to translate.
            site_index_pine_m (float): Pine site index (m).
            site_index_spruce_m (float): Spruce site index (m).

        Returns:
            float: Species-specific site index (m).
        """
        return _kernels.site_index_for_species(
            species,
            site_index_pine_m=site_index_pine_m,
            site_index_spruce_m=site_index_spruce_m,
        )

    @staticmethod
    def mean_height(
        *,
        age_years: float,
        species: TreeName,
        site_index_pine_m: float,
        site_index_spruce_m: float,
    ) -> float:
        """Compute mean height (m) from total age and site indices.

        Args:
            age_years (float): Total age in years.
            species (TreeName): Tree species.
            site_index_pine_m (float): Pine site index (m).
            site_index_spruce_m (float): Spruce site index (m).

        Returns:
            float: Mean height (m), truncated to >= 0.3.
        """
        return _kernels.mean_height(
            age_years=age_years,
            species=species,
            site_index_pine_m=site_index_pine_m,
            site_index_spruce_m=site_index_spruce_m,
        )

    @staticmethod
    def mean_age(
        *,
        mean_height_m: float,
        species: TreeName,
        site_index_pine_m: float,
        site_index_spruce_m: float,
    ) -> float:
        """Invert mean height to mean age (years).

        Args:
            mean_height_m (float): Mean height (m).
            species (TreeName): Tree species.
            site_index_pine_m (float): Pine site index (m).
            site_index_spruce_m (float): Spruce site index (m).

        Returns:
            float: Mean age (years).
        """
        return _kernels.mean_age(
            mean_height_m=mean_height_m,
            species=species,
            site_index_pine_m=site_index_pine_m,
            site_index_spruce_m=site_index_spruce_m,
        )


class HuginCropTreeProbability:
    """Probability that a tree remains after cleaning (Hugin crop tree proxy)."""

    @staticmethod
    def crop_tree_probability(
        *,
        height_m: float,
        mean_height_m: float,
        conifer_stems_per_100m2: float,
        rec_stems_per_ha: float,
        coniferous: bool,
    ) -> float:
        """Compute crop-tree probability for a single tree.

        Args:
            height_m (float): Tree height in meters.
            mean_height_m (float): Mean height in meters.
            conifer_stems_per_100m2 (float): Conifer stems per 100 m2.
            rec_stems_per_ha (float): Recommended stems per ha after cleaning.
            coniferous (bool): Whether the tree is coniferous.

        Returns:
            float: Probability in [0, 1].
        """
        return _kernels.crop_tree_probability(
            height_m=height_m,
            mean_height_m=mean_height_m,
            conifer_stems_per_100m2=conifer_stems_per_100m2,
            rec_stems_per_ha=rec_stems_per_ha,
            coniferous=coniferous,
        )

    @staticmethod
    def probabilities_from_tree_list(
        trees: Sequence[Tree],
        *,
        rec_stems_per_ha: float,
        expansion_factor: float = 1.0,
    ) -> list[float]:
        """Compute crop-tree probabilities for a tree list.

        Args:
            trees (Sequence[Tree]): Trees with ``height_m`` and ``weight_n`` set.
            rec_stems_per_ha (float): Recommended stems/ha to remain after cleaning.
            expansion_factor (float): Factor to convert tree weights to per-ha stems.

        Returns:
            list[float]: Crop-tree probabilities, same order as input trees.
        """
        return _kernels.probabilities_from_tree_list(
            trees, rec_stems_per_ha=rec_stems_per_ha, expansion_factor=expansion_factor
        )


def nyskog_indicators_from_site(
    *,
    field_layer: Optional[Sweden.FieldLayer],
    soil_moisture: Optional[Sweden.SoilMoistureEnum],
) -> dict[str, int]:
    """Backward-compatible typed wrapper delegating to extracted formulas."""
    return _kernels.nyskog_indicators_from_site(
        field_layer=field_layer,
        soil_moisture=soil_moisture,
    )


class NyskogReconstruction:
    """Stepwise NYSKOG reconstruction functions for young-stand states."""

    @staticmethod
    def young_stand_quality_asinw(
        *,
        stocking_arcsine_radians: float,
        regeneration_type: RegenerationType,
        latitude_deg: float | None = None,
    ) -> float:
        """Young-stand quality ASINW = arcsin(sqrt(W)) from regeneration stocking.

        Reference:
            Elfving, B. (1982). Hugins ungskogstaxering 1976-1979. SLU, Projekt
            Hugin, Rapport 27. The
            young-stand quality W is a deterministic function of the arcsine-
            transformed regeneration stocking (SLH); the returned ASINW feeds
            :meth:`production_potential_q` (q = 100*sin^2(asinw)). Cultivations
            carry a latitude dummy -0.031*NS (NS = latitude > 60 N).

        Args:
            stocking_arcsine_radians (float): SLH linear predictor (= 2*asinslh).
            regeneration_type (RegenerationType): Natural/extensive vs cultivation.
            latitude_deg (float | None): Latitude for the NS dummy (cultivation only).

        Returns:
            float: ASINW value (radians).
        """
        return _kernels.young_stand_quality_asinw(
            stocking_arcsine_radians=stocking_arcsine_radians,
            regeneration_type=regeneration_type,
            latitude_deg=latitude_deg,
        )

    @staticmethod
    def production_potential_q(asinw: float) -> float:
        """Compute production potential Q (0-100) from ASINW = arcsin(sqrt(W)).

        Elfving (1982), the Hugin young-stand survey report.
        q = 100 * W with W = sin^2(asinw).

        Args:
            asinw (float): ASINW value (radians), = arcsin(sqrt(W)).

        Returns:
            float: Production potential Q (0-100).
        """
        return _kernels.production_potential_q(asinw)

    @staticmethod
    def udim_probability(
        q: float, *, deterministic: bool = True, rng: Optional[float] = None
    ) -> float:
        """Probability/indicator for under-dimensioned trees.

        Args:
            q (float): Production potential Q.
            deterministic (bool): If True, return probability; otherwise return 0/1.
            rng (float | None): Optional random draw in [0, 1] for stochastic mode.

        Returns:
            float: Probability or indicator for under-dimensioned trees.
        """
        return _kernels.udim_probability(q, deterministic=deterministic, rng=rng)

    @staticmethod
    def total_stems(
        *,
        regeneration_type: RegenerationType,
        mean_height_main_m: float,
        q: float,
        ln_q: float,
        ln_si: float,
        under_dimension_prob: float,
        wet: int,
        dry: int,
        height_indicator_dm: float,
        deterministic: bool = True,
        noise: float = 0.0,
    ) -> float:
        """Step 1: Total stems per ha.

        Args:
            regeneration_type (RegenerationType): Regeneration category.
            mean_height_main_m (float): Mean height of main saplings (m).
            q (float): Production potential Q.
            ln_q (float): Log(Q).
            ln_si (float): Log(site index).
            under_dimension_prob (float): Under-dimension probability (0..1).
            wet (int): Wet site indicator (0/1).
            dry (int): Dry site indicator (0/1).
            height_indicator_dm (float): HIND in decimetres (often max(15, 10*H)).
            deterministic (bool): If True, use bias-corrected estimate.
            noise (float): Stochastic noise multiplier.

        Returns:
            float: Total stems per hectare.
        """
        return _kernels.total_stems(
            regeneration_type=regeneration_type.value,
            mean_height_main_m=mean_height_main_m,
            q=q,
            ln_q=ln_q,
            ln_si=ln_si,
            under_dimension_prob=under_dimension_prob,
            wet=wet,
            dry=dry,
            height_indicator_dm=height_indicator_dm,
            deterministic=deterministic,
            noise=noise,
        )

    @staticmethod
    def proportion_conifer(
        *,
        regeneration_type: RegenerationType,
        q: float,
        ln_qind: float,
        stem_total: float,
        ln_si: float,
        wet: int,
        dry: int,
        rich: int,
        poor: int,
        deterministic: bool = True,
        noise: float = 0.0,
    ) -> float:
        """Step 2: Proportion conifer.

        Args:
            regeneration_type (RegenerationType): Regeneration category.
            q (float): Production potential Q.
            ln_qind (float): Log(Q) for indicator model.
            stem_total (float): Total stems per ha.
            ln_si (float): Log(site index).
            wet (int): Wet site indicator (0/1).
            dry (int): Dry site indicator (0/1).
            rich (int): Rich site indicator (0/1).
            poor (int): Poor site indicator (0/1).
            deterministic (bool): If True, apply bias correction.
            noise (float): Stochastic noise multiplier.

        Returns:
            float: Proportion of conifer stems (0..1).
        """
        return _kernels.proportion_conifer(
            regeneration_type=regeneration_type.value,
            q=q,
            ln_qind=ln_qind,
            stem_total=stem_total,
            ln_si=ln_si,
            wet=wet,
            dry=dry,
            rich=rich,
            poor=poor,
            deterministic=deterministic,
            noise=noise,
        )

    @staticmethod
    def dominant_conifer_share(
        *,
        regeneration_type: RegenerationType,
        qind: float,
        ln_si: float,
        wet: int,
        dry: int,
        rich: int,
        poor: int,
        hwod: int,
        hwd: int,
        shrubs: int,
        lichen: int,
        deterministic: bool = True,
        noise: float = 0.0,
    ) -> float:
        """Step 3: Dominant conifer share.

        Args:
            regeneration_type (RegenerationType): Regeneration category.
            qind (float): Production potential indicator.
            ln_si (float): Log(site index).
            wet (int): Wet site indicator (0/1).
            dry (int): Dry site indicator (0/1).
            rich (int): Rich site indicator (0/1).
            poor (int): Poor site indicator (0/1).
            hwod (int): HWOD indicator (0/1).
            hwd (int): HWD indicator (0/1).
            shrubs (int): Shrubs indicator (0/1).
            lichen (int): Lichen indicator (0/1).
            deterministic (bool): If True, apply bias correction.
            noise (float): Stochastic noise multiplier.

        Returns:
            float: Proportion of dominant conifer within conifers (0..1).
        """
        return _kernels.dominant_conifer_share(
            regeneration_type=regeneration_type.value,
            qind=qind,
            ln_si=ln_si,
            wet=wet,
            dry=dry,
            rich=rich,
            poor=poor,
            hwod=hwod,
            hwd=hwd,
            shrubs=shrubs,
            lichen=lichen,
            deterministic=deterministic,
            noise=noise,
        )

    @staticmethod
    def secondary_mean_height(
        *,
        regeneration_type: RegenerationType,
        secondary_species: TreeName,
        site_index_m: float,
        mean_height_main_m: float,
        herb: int,
        dry: int,
        wet: int,
        deterministic: bool = True,
        noise: float = 0.0,
    ) -> float:
        """Step 4A: Mean height for secondary species.

        Args:
            regeneration_type (RegenerationType): Regeneration category.
            secondary_species (TreeName): Species for the secondary cohort.
            site_index_m (float): Site index for the secondary species (m).
            mean_height_main_m (float): Mean height of main cohort (m).
            herb (int): Herb indicator (0/1).
            dry (int): Dry site indicator (0/1).
            wet (int): Wet site indicator (0/1).
            deterministic (bool): If True, apply bias correction.
            noise (float): Stochastic noise multiplier.

        Returns:
            float: Mean height (m) of the secondary species.
        """
        return _kernels.secondary_mean_height(
            regeneration_type=regeneration_type.value,
            secondary_species=secondary_species,
            site_index_m=site_index_m,
            mean_height_main_m=mean_height_main_m,
            herb=herb,
            dry=dry,
            wet=wet,
            deterministic=deterministic,
            noise=noise,
        )

    @staticmethod
    def height_variation(
        *,
        species: TreeName,
        species_height_m: float,
        q: float,
        ln_q: float,
        self_rejuvenated: int,
        deterministic: bool = True,
        noise: float = 0.0,
        min_cv: float = 0.1,
        max_cv: float = 1.0,
    ) -> float:
        """Step 4B: Height variation (CV).

        Args:
            species (TreeName): Species for CVH model.
            species_height_m (float): Mean height of species (m).
            q (float): Production potential Q.
            ln_q (float): Log(Q).
            self_rejuvenated (int): Self-rejuvenation indicator (0/1).
            deterministic (bool): If True, use deterministic output.
            noise (float): Stochastic noise multiplier.
            min_cv (float): Minimum CV bound.
            max_cv (float): Maximum CV bound.

        Returns:
            float: Height variation (coefficient of variation).
        """
        return _kernels.height_variation(
            species=species,
            species_height_m=species_height_m,
            q=q,
            ln_q=ln_q,
            self_rejuvenated=self_rejuvenated,
            deterministic=deterministic,
            noise=noise,
            min_cv=min_cv,
            max_cv=max_cv,
        )

    @staticmethod
    def weibull_parameters(
        *,
        species: TreeName,
        cvh: float,
        mean_height_m: float,
    ) -> tuple[float, float]:
        """Step 5: Weibull scale (beta) and shape (lambda).

        Args:
            species (TreeName): Species for Weibull parameters.
            cvh (float): Height variation (CV).
            mean_height_m (float): Mean height (m).

        Returns:
            tuple[float, float]: (beta, lambda) parameters.
        """
        return _kernels.weibull_parameters(
            species=species,
            cvh=cvh,
            mean_height_m=mean_height_m,
        )

    @staticmethod
    def stems_per_species(
        *,
        regeneration_type: RegenerationType,
        species_to_plant: TreeName,
        stem_total: float,
        prop_conifer: float,
        prop_dom_conifer: float,
        site_index_m: float,
        nfi_region: NfiRegion,
    ) -> dict[str, float]:
        """Step 3: Resolve stems per species group (pine/spruce/contorta/birch/other).

        Args:
            regeneration_type (RegenerationType): Regeneration category.
            species_to_plant (TreeName): Intended planted species.
            stem_total (float): Total stems per ha.
            prop_conifer (float): Proportion conifers (0..1).
            prop_dom_conifer (float): Proportion of dominant conifer (0..1).
            site_index_m (float): Site index for planted species (m).
            nfi_region (NfiRegion): NFI region for deciduous split.

        Returns:
            dict[str, float]: Stems per species group (per ha).
        """
        return _kernels.stems_per_species(
            regeneration_type=regeneration_type.value,
            species_to_plant=species_to_plant,
            stem_total=stem_total,
            prop_conifer=prop_conifer,
            prop_dom_conifer=prop_dom_conifer,
            site_index_m=site_index_m,
            nfi_region=nfi_region.value,
        )

    @staticmethod
    def reconstruct_summary(
        *,
        asinw: float,
        mean_height_main_m: float,
        site_index_m: float,
        regeneration_type: RegenerationType,
        species_to_plant: TreeName,
        nfi_region: NfiRegion,
        field_layer: Optional[Sweden.FieldLayer] = None,
        soil_moisture: Optional[Sweden.SoilMoistureEnum] = None,
        indicators: Optional[dict[str, int]] = None,
        deterministic: bool = True,
        noise: float = 0.0,
        rng: Optional[float] = None,
    ) -> NyskogReconstructionSummary:
        """Run the full NYSKOG reconstruction workflow and return summary outputs."""
        payload = _kernels.reconstruct_summary(
            asinw=asinw,
            mean_height_main_m=mean_height_main_m,
            site_index_m=site_index_m,
            regeneration_type=regeneration_type.value,
            species_to_plant=species_to_plant,
            nfi_region=nfi_region.value,
            field_layer=field_layer,
            soil_moisture=soil_moisture,
            indicators=indicators,
            deterministic=deterministic,
            noise=noise,
            rng=rng,
        )
        return NyskogReconstructionSummary(**payload)


__all__ = [
    "RegenerationType",
    "NfiRegion",
    "NyskogReconstructionSummary",
    "HuginMeanHeightModel",
    "HuginCropTreeProbability",
    "NyskogReconstruction",
    "nyskog_indicators_from_site",
]


DESCRIPTOR = FormulaDescriptor(
    component_id="elfving_1982_model",
    source=SourceReference(
        author="Elfving, B.",
        year=1982,
        title="Hugins ungskogstaxering 1976-1979",
        note="SLU, Projekt Hugin, Rapport 27. The Hugin young stand survey.",
    ),
    kind="model",
    domain="growth",
    composes=(),
    kernel_names=("NyskogReconstruction", "HuginMeanHeightModel"),
)
