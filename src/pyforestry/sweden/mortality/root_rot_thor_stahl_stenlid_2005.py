"""Root-rot risk model by Thor, Stahl, and Stenlid (2005)."""

from __future__ import annotations

import math

from ._common import (
    clamp_probability,
    resolve_soil_moisture_code,
    species_basal_area_m2_ha_by_group,
    species_group,
    stems_per_tree,
    tree_basal_area_cm2,
)
from .types import MortalityContext, RootRotRiskResult


def root_rot_risk_thor_stahl_stenlid_2005(
    *,
    context: MortalityContext,
    default_stems_per_tree: float = 1.0,
) -> RootRotRiskResult:
    """Calculate root-rot risk for each tree and stand totals.

    Reference:
        Thor, M., Ståhl, G. & Stenlid, J. (2005). Modelling root rot incidence
        in Sweden using tree, site and stand variables. Scandinavian Journal of
        Forest Research 20:165-176.

    Args:
        context: Unified mortality context.
        default_stems_per_tree: Fallback represented stems per tree record.

    Returns:
        RootRotRiskResult with tree probabilities and stand totals.
    """
    trees = context.trees
    stand_conditions = context.stand
    site_conditions = context.site

    if not trees:
        return RootRotRiskResult(
            tree_risk_probabilities=[],
            stems_with_root_rot=0.0,
            basal_area_with_root_rot_m2_ha=0.0,
            volume_with_root_rot_m3_ha=0.0,
        )

    mean_age_years = (
        stand_conditions.mean_age_excl_overstorey_years
        if stand_conditions.mean_age_excl_overstorey_years is not None
        else stand_conditions.mean_age_total_years
    )
    if mean_age_years is None or mean_age_years <= 0.0:
        raise ValueError("mean_age_excl_overstorey_years or mean_age_total_years must be > 0.")

    spruce_proportion = 0.0
    by_group = species_basal_area_m2_ha_by_group(
        trees=trees,
        stand_conditions=stand_conditions,
    )
    total_basal_area = (
        stand_conditions.total_basal_area_m2_ha
        if stand_conditions.total_basal_area_m2_ha is not None
        else sum(by_group.values())
    )
    if total_basal_area > 0.0:
        spruce_proportion = by_group.get("spruce", 0.0) / total_basal_area

    soil_moisture_code = resolve_soil_moisture_code(site_conditions)
    temperature_sum_800_1099 = int(800.0 <= site_conditions.temperature_sum <= 1099.0)
    ln_mean_age = math.log(mean_age_years)
    is_sandy_silty = int(site_conditions.texture_is_sand_medium)

    common_part = (
        -31.839
        - 0.3741 * mean_age_years
        + 5.792 * ln_mean_age
        + 0.05725 * mean_age_years * ln_mean_age
        + 0.01553 * site_conditions.site_index_m
        + 0.3348 * (1 - temperature_sum_800_1099)
        - 0.3099 * int(site_conditions.altitude_m >= 100.0)
        - 0.2683 * soil_moisture_code
        + 0.1510 * (1 - is_sandy_silty)
        + 0.1370 * math.log(spruce_proportion * 10.0 + 0.1)
    )

    tree_probabilities: list[float] = []
    stems_with_root_rot = 0.0
    basal_area_with_root_rot_m2_ha = 0.0
    volume_with_root_rot_m3_ha = 0.0
    for tree in trees:
        stems = stems_per_tree(tree, default_stems_per_tree)
        if species_group(tree.species) != "spruce" or stems <= 0.0:
            tree_probabilities.append(0.0)
            continue
        if tree.diameter_cm <= 0.0:
            raise ValueError("diameter_cm must be > 0 for root-rot risk.")

        dbh_mm = 10.0 * tree.diameter_cm
        ln_dbh = math.log(dbh_mm)
        xb = common_part - 0.06151 * dbh_mm + 3.3909 * ln_dbh + 0.007669 * dbh_mm * ln_dbh
        exp_xb = math.exp(xb)
        probability = clamp_probability(2.037 * (exp_xb / (1.0 + exp_xb)))
        tree_probabilities.append(probability)

        weighted_stems = probability * stems
        stems_with_root_rot += weighted_stems
        basal_area_with_root_rot_m2_ha += weighted_stems * tree_basal_area_cm2(tree) / 10_000.0
        if tree.volume_m3 is not None:
            volume_with_root_rot_m3_ha += weighted_stems * tree.volume_m3

    return RootRotRiskResult(
        tree_risk_probabilities=tree_probabilities,
        stems_with_root_rot=stems_with_root_rot,
        basal_area_with_root_rot_m2_ha=basal_area_with_root_rot_m2_ha,
        volume_with_root_rot_m3_ha=volume_with_root_rot_m3_ha,
    )


__all__ = ["root_rot_risk_thor_stahl_stenlid_2005"]


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------


class _Descriptor:
    """FormulaModuleDescriptor for Thor, M., Ståhl, G. & Stenlid, J. (2005)."""

    @property
    def component_id(self):
        return "root_rot_thor_stahl_stenlid_2005"

    @property
    def source(self):
        from pyforestry.base.contracts import SourceReference

        return SourceReference(
            author="Thor, M., Ståhl, G. & Stenlid, J.",
            year=2005,
            title="Modelling root rot incidence in Sweden using tree, site and stand variables",
            note="Scandinavian Journal of Forest Research 20:165-176.",
        )

    @property
    def species_groups(self):
        return {}

    @property
    def units(self):
        return {}

    @property
    def kernel_names(self):
        return ["root_rot_risk_thor_stahl_stenlid_2005"]


DESCRIPTOR = _Descriptor()
