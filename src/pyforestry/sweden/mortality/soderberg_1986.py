"""Soderberg (1986) self-thinning calibration for mortality."""

from __future__ import annotations

import math
import warnings
from collections.abc import Sequence
from typing import Any

from pyforestry.base.contracts import FormulaDescriptor, SourceReference

from ._common import (
    calibration_group,
    clamp_probability,
    scale_probability_from_5_years,
    species_basal_area_m2_ha_by_group,
    species_mortality_fraction_from_tree_probabilities,
    stems_per_tree,
)
from .types import MortalityContext


def calibrate_soderberg(
    *,
    context: MortalityContext,
    tree_probabilities: Sequence[float],
    site_index_adjustment_factor: float = 1.0,
    period_years: float = 5.0,
    default_stems_per_tree: float = 1.0,
) -> tuple[list[float], dict[str, float], dict[str, float], dict[str, Any]]:
    """Calibrate tree probabilities to Soderberg self-thinning response.

    Reference:
        Söderberg, U. (1986). Funktioner för skogliga produktionsprognoser:
        tillväxt och formhöjd för enskilda träd av inhemska trädslag i Sverige.
        Report 14, Section of Forest Mensuration and Management, Swedish
        University of Agricultural Sciences (SLU), Umeå.

    Args:
        context: Unified mortality context.
        tree_probabilities: Base tree probabilities before calibration.
        site_index_adjustment_factor: Multiplier applied to spruce SI branch.
        period_years: Prediction period in years.
        default_stems_per_tree: Fallback represented stems per tree record.

    Returns:
        A tuple with calibrated probabilities, adjusted species fractions,
        correction factors, and diagnostics.
    """
    trees = context.trees
    stand_conditions = context.stand
    site_conditions = context.site

    if len(trees) != len(tree_probabilities):
        raise ValueError("context.trees and tree_probabilities must have equal length.")
    if not trees:
        return [], {}, {}, {}
    if site_conditions.site_index_m <= 0.0:
        raise ValueError("site_index_m must be > 0 for Soderberg calibration.")

    by_group = species_basal_area_m2_ha_by_group(
        trees=trees,
        stand_conditions=stand_conditions,
        default_stems_per_tree=default_stems_per_tree,
    )
    total_basal_area_m2_ha = (
        stand_conditions.total_basal_area_m2_ha
        if stand_conditions.total_basal_area_m2_ha is not None
        else sum(by_group.values())
    )
    if total_basal_area_m2_ha <= 0.0:
        raise ValueError("total_basal_area_m2_ha must be > 0.")
    log_total_basal_area = math.log(total_basal_area_m2_ha)

    total_stems_per_ha = stand_conditions.total_stems_per_ha
    if total_stems_per_ha is None:
        total_stems_per_ha = sum(stems_per_tree(tree, default_stems_per_tree) for tree in trees)
    if total_stems_per_ha <= 0.0:
        raise ValueError("total_stems_per_ha must be > 0.")

    mean_age_excl = (
        stand_conditions.mean_age_excl_overstorey_years
        if stand_conditions.mean_age_excl_overstorey_years is not None
        else stand_conditions.mean_age_total_years
    )
    if mean_age_excl is None:
        raise ValueError("mean_age_excl_overstorey_years or mean_age_total_years is required.")
    if mean_age_excl <= 0.0:
        raise ValueError("mean age must be > 0.")

    inv_age_plus_ten = 1.0 / (mean_age_excl + 10.0)
    inv_age_plus_ten_sqr = inv_age_plus_ten * inv_age_plus_ten
    pine_proportion = clamp_probability(by_group.get("pine", 0.0) / total_basal_area_m2_ha)
    spruce_proportion = clamp_probability(by_group.get("spruce", 0.0) / total_basal_area_m2_ha)
    leaf_proportion = clamp_probability(1.0 - pine_proportion - spruce_proportion)
    spruce_proportion_sqr = spruce_proportion * spruce_proportion
    leaf_proportion_sqr = leaf_proportion * leaf_proportion

    if pine_proportion > 0.5:
        site_index_pine_m = site_conditions.site_index_m
        site_index_spruce_m = 0.0
    else:
        site_index_pine_m = 0.0
        site_index_spruce_m = site_conditions.site_index_m * site_index_adjustment_factor

    self_thinning_per_year = (
        6.09490e-1 * inv_age_plus_ten
        - 1.25903e1 * inv_age_plus_ten_sqr
        + 3.31700e-4 * total_basal_area_m2_ha
        - 1.00600e-2 * log_total_basal_area
        + 1.73000e-4 * site_index_spruce_m
        + 1.56000e-4 * site_index_pine_m
        - 1.30000e-2 * spruce_proportion
        + 1.19000e-2 * spruce_proportion_sqr
        + 1.89000e-2 * leaf_proportion
        - 1.74000e-2 * leaf_proportion_sqr
        + 2.32000e-2
    )
    if self_thinning_per_year < 0.0 or self_thinning_per_year > 1.0:
        warnings.warn(
            "Soderberg self-thinning annual probability exceeded [0, 1]; clamped.",
            stacklevel=2,
        )
        self_thinning_per_year = clamp_probability(self_thinning_per_year)
    self_thinning_5_year = clamp_probability(1.0 - (1.0 - self_thinning_per_year) ** 5.0)
    self_thinning = scale_probability_from_5_years(self_thinning_5_year, period_years)

    self_thinning_limit_xb = (
        -1.86120e1 * inv_age_plus_ten
        - 7.65295e2 * inv_age_plus_ten_sqr
        + 4.79800e-2 * site_index_spruce_m
        + 5.58900e-2 * site_index_pine_m
        + 6.71700e-5 * total_stems_per_ha
        - 2.86400e-9 * (total_stems_per_ha**2.0)
        + 7.20400e-1 * spruce_proportion
        - 4.87900e-1 * spruce_proportion_sqr
        + 1.06200e-1 * leaf_proportion
        - 2.07300e-1 * leaf_proportion_sqr
        + 2.52250e0
    )
    self_thinning_limit_m2_ha = math.exp(self_thinning_limit_xb)
    if not math.isfinite(self_thinning_limit_m2_ha) or self_thinning_limit_m2_ha <= 0.0:
        raise ValueError("Invalid self-thinning limit in Soderberg calibration.")

    transition = (-1.0 + total_basal_area_m2_ha / self_thinning_limit_m2_ha) / 0.1
    transition = math.tanh(transition)
    transition_weight = (1.0 - transition) / 2.0

    current_fractions = species_mortality_fraction_from_tree_probabilities(
        trees=trees,
        tree_probabilities=tree_probabilities,
        default_stems_per_tree=default_stems_per_tree,
        use_calibration_groups=True,
    )
    groups_present = {calibration_group(tree.species) for tree in trees}
    adjusted_fractions: dict[str, float] = {}
    correction_factors: dict[str, float] = {}
    for group in groups_present:
        current = current_fractions.get(group, 0.0)
        adjusted = current * transition_weight + self_thinning * (1.0 - transition_weight)
        adjusted = clamp_probability(adjusted)
        adjusted_fractions[group] = adjusted
        correction_factors[group] = adjusted / current if current > 0.0 else 1.0

    calibrated_probabilities = [
        clamp_probability(
            probability * correction_factors.get(calibration_group(tree.species), 1.0)
        )
        for tree, probability in zip(trees, tree_probabilities, strict=True)
    ]
    diagnostics = {
        "self_thinning_probability": self_thinning,
        "self_thinning_limit_m2_ha": self_thinning_limit_m2_ha,
        "transition_weight": transition_weight,
        "current_fractions": current_fractions,
    }
    return calibrated_probabilities, adjusted_fractions, correction_factors, diagnostics


__all__ = ["calibrate_soderberg"]


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------


DESCRIPTOR = FormulaDescriptor(
    component_id="soderberg_1986_mortality_calibration",
    source=SourceReference(
        author="Söderberg, U.",
        year=1986,
        title=(
            "Funktioner för skogliga produktionsprognoser: tillväxt och formhöjd "
            "för enskilda träd av inhemska trädslag i Sverige"
        ),
        note=(
            "Report 14, Section of Forest Mensuration and Management, "
            "Swedish University of Agricultural Sciences (SLU), Umeå."
        ),
    ),
    species_groups={},
    units={},
    kernel_names=("calibrate_soderberg",),
)
