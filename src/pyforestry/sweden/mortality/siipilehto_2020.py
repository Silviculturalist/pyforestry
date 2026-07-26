"""Siipilehto et al. (2020) stand-level mortality equations for Sweden."""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Any

from ._common import (
    clamp_probability,
    mean_tree_age_years,
    resolve_soil_moisture_code,
    scale_probability_from_5_years,
    species_basal_area_m2_ha_by_group,
    species_group,
    stems_per_tree,
    tree_basal_area_cm2,
)
from .types import MortalityContext, MortalityTreeRecord


def _siipilehto_step3_probability(
    *,
    tree: MortalityTreeRecord,
    total_basal_area_m2_ha: float,
    log_total_basal_area: float,
    mdbh_m: float,
    mdbh2_m2: float,
    wet_indicator: int,
    pine_indicator: int,
    thinning_indicator: int,
    near_edge_indicator: int,
    edge_indicator: int,
    altitude_m: float,
    latitude_deg: float,
) -> float:
    """Fridman & Ståhl (2001) step-III per-tree mortality (Siipilehto composite)."""
    if tree.diameter_cm < 4.0:
        return 0.0

    diameter_m = tree.diameter_cm / 100.0
    group = species_group(tree.species)
    if group == "pine":
        xb = (
            -1.98
            - 0.739 * log_total_basal_area
            + 0.028 * tree.bal
            - 17.4 * diameter_m
            + 21.5 * diameter_m * diameter_m
            + 25.6 * mdbh_m
            - 26.6 * mdbh2_m2
            + 0.327 * wet_indicator
            - 0.456 * pine_indicator
        )
    elif group == "spruce":
        if diameter_m <= 0.0:
            raise ValueError("diameter_cm must be > 0 for spruce mortality.")
        xb = (
            -4.58
            - 0.0545 * total_basal_area_m2_ha
            + 0.0282 * tree.bal
            + 0.042 * (1.0 / diameter_m)
            + 11.2 * mdbh_m
            + 0.577 * near_edge_indicator
            - 0.594 * pine_indicator
            + 0.323 * thinning_indicator
        )
    elif group == "birch":
        xb = (
            -2.83
            - 0.0665 * total_basal_area_m2_ha
            + 0.0362 * tree.bal
            - 16.5 * diameter_m
            + 27.7 * diameter_m * diameter_m
            + 1.10e-05 * altitude_m
            + 15.7 * mdbh_m
        )
    elif group in {"oak", "beech", "southern_broadleaf"}:
        xb = -3.67 - 0.14 * total_basal_area_m2_ha + 0.168 * tree.bal + 3.34 * diameter_m
    else:
        if diameter_m <= 0.0:
            raise ValueError("diameter_cm must be > 0 for broadleaf mortality.")
        xb = (
            -5.40
            - 0.0688 * total_basal_area_m2_ha
            + 0.0693 * tree.bal
            + 0.0634 * (1.0 / diameter_m)
            - 0.345 * edge_indicator
            + 2.12e-05 * altitude_m
            + 0.0498 * latitude_deg
        )

    if xb >= 0.0:
        exp_neg = math.exp(-xb)
        return 1.0 / (1.0 + exp_neg)
    exp_pos = math.exp(xb)
    return exp_pos / (1.0 + exp_pos)


def _log_one_plus_exp(value: float) -> float:
    """Return `log(1 + exp(value))` with improved numerical stability."""
    if value > 0.0:
        return value + math.log1p(math.exp(-value))
    return math.log1p(math.exp(value))


def siipilehto_2020_probabilities(
    *,
    context: MortalityContext,
    period_years: float = 5.0,
    default_stems_per_tree: float = 1.0,
) -> tuple[list[float], dict[str, Any]]:
    """Calculate Siipilehto et al. (2020) stand-level mortality probabilities.

    Reference:
        Siipilehto, J., Allen, M., Nilsson, U., Brunner, A., Huuskonen, S.,
        Haikarainen, S., Subramanian, N., Antón-Fernández, C., Holmström, E.,
        Andreassen, K. & Hynynen, J. (2020). Stand-level mortality models for
        Nordic boreal forests. Silva Fennica 54(5), article id 10414.
        https://doi.org/10.14214/sf.10414

        The model is stand-level and two-step: Model 1 (Table 5) predicts the
        probability of no mortality (survival) on a plot, and Model 2 (Table 6)
        the proportion of basal area in surviving trees. Mortality is then
        distributed among individual trees using the step-III per-tree functions
        and correction factor of Fridman & Ståhl (2001), as the paper directs.
        Historically labelled "SNS", after the SNS (Nordic Forest Research)
        project that funded it.

    Args:
        context: Unified mortality context.
        period_years: Prediction period in years.
        default_stems_per_tree: Fallback represented stems per tree record.

    Returns:
        A tuple with per-tree probabilities and diagnostics.
    """
    trees = context.trees
    stand_conditions = context.stand
    site_conditions = context.site
    history_conditions = context.history

    if not trees:
        return [], {"p_plot": 0.0, "p_basal_area": 0.0, "correction_factor": 0.0}
    if stand_conditions.plot_area_m2 <= 0.0:
        raise ValueError("plot_area_m2 must be > 0.")

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

    mean_diameter_arithmetic_cm = stand_conditions.mean_diameter_arithmetic_cm
    if mean_diameter_arithmetic_cm is None:
        stem_sum = sum(stems_per_tree(tree, default_stems_per_tree) for tree in trees)
        if stem_sum <= 0.0:
            raise ValueError("Unable to derive mean diameter from zero stems.")
        mean_diameter_arithmetic_cm = (
            sum(tree.diameter_cm * stems_per_tree(tree, default_stems_per_tree) for tree in trees)
            / stem_sum
        )
    mdbh_m = mean_diameter_arithmetic_cm / 100.0
    mdbh2_m2 = (
        ((4.0 / math.pi) * total_basal_area_m2_ha) / total_stems_per_ha
        if total_stems_per_ha > 1.0e-4
        else 0.0
    )

    mean_age_total_years = mean_tree_age_years(trees, stand_conditions.mean_age_total_years)
    if mean_age_total_years <= 0.0:
        raise ValueError("mean_age_total_years must be > 0.")
    qmd_cm = math.sqrt(total_basal_area_m2_ha / (0.0000785 * total_stems_per_ha))

    soil_moisture_code = resolve_soil_moisture_code(site_conditions)
    if soil_moisture_code < 1 or soil_moisture_code > 5:
        warnings.warn(
            f"soil_moisture code {soil_moisture_code} is outside expected [1, 5].",
            stacklevel=2,
        )
    wet_indicator = int(soil_moisture_code in {4, 5})
    thinning_indicator = int(
        history_conditions.thinned_within_0_5_years if history_conditions is not None else False
    )
    near_edge_indicator = 0
    edge_indicator = 0

    pine_proportion = clamp_probability(by_group.get("pine", 0.0) / total_basal_area_m2_ha)
    spruce_proportion = clamp_probability(by_group.get("spruce", 0.0) / total_basal_area_m2_ha)
    leaf_proportion = clamp_probability(1.0 - pine_proportion - spruce_proportion)
    pine_indicator = int(pine_proportion >= 0.7)

    # Siipilehto et al. (2020) fit genuine Slope/100 and WEST terms (Model 1, Table 5)
    # and a Slope/100*West term (Model 2, Table 6). pyforestry reads the real
    # slope/aspect and activates these terms, faithful to the paper. Per Table 1,
    # WEST = 1 when the aspect is a western slope (225-315 degrees), else 0 (and 0 when
    # the aspect is unknown).
    slope_percent = stand_conditions.slope_percent
    aspect_degrees = stand_conditions.aspect_degrees
    west_indicator = 1 if aspect_degrees is not None and 225.0 <= aspect_degrees <= 315.0 else 0
    peat_indicator = int(site_conditions.peat)

    step1_xb = (
        3.1751
        - 0.00417 * mean_age_total_years
        + 0.01382 * (qmd_cm**1.5)
        - 0.6693 * math.sqrt(total_basal_area_m2_ha)
        + 0.004356 * (pine_proportion * mean_age_total_years)
        - 0.01112 * (leaf_proportion * mean_age_total_years)
        - 1.0542 * (slope_percent / 100.0)
        + 0.1354 * west_indicator
        + 0.005803 * (thinning_indicator * total_basal_area_m2_ha)
        - 0.2201 * peat_indicator
    )
    p_plot_alive_5_year = math.exp(
        -_log_one_plus_exp(-step1_xb) * (stand_conditions.plot_area_m2 / 314.16)
    )
    p_plot_5_year = clamp_probability(1.0 - p_plot_alive_5_year)
    p_plot = scale_probability_from_5_years(p_plot_5_year, period_years)

    # Siipilehto et al. (2020) Model 2, Table 6 (proportion of basal area in surviving
    # trees). NORWAY is a country dummy = 0 for Swedish stands, so its +0.1657 term is
    # omitted here. The Slope/100*West term is +0.2438 as published.
    step2_xb = (
        -7.3745
        + 1.4010 * math.log(total_stems_per_ha)
        - 0.0296 * math.sqrt(total_stems_per_ha)
        - 0.0117 * total_basal_area_m2_ha
        + 0.5633 * math.log(qmd_cm)
        + 0.0790 * (math.log(mean_age_total_years) * pine_proportion)
        - 0.0500 * (math.log(mean_age_total_years) * leaf_proportion)
        + 0.2438 * ((slope_percent / 100.0) * west_indicator)
    )
    p_basal_area_alive_5_year = math.exp(
        -_log_one_plus_exp(-step2_xb) * (314.16 / stand_conditions.plot_area_m2)
    )
    # Model 2 predicts the *survival* proportion (basal area in surviving trees), which
    # the logistic keeps in (0, 1). Guard the extreme tails on that survival value
    # before converting to a mortality proportion, matching the paper's survival
    # parameterization.
    if p_basal_area_alive_5_year > 0.9999:
        p_basal_area_alive_5_year = 1.0
    elif p_basal_area_alive_5_year < 0.00001:
        p_basal_area_alive_5_year = 0.0
    p_basal_area_5_year = clamp_probability(1.0 - p_basal_area_alive_5_year)
    p_basal_area = scale_probability_from_5_years(p_basal_area_5_year, period_years)

    step3_probabilities = [
        _siipilehto_step3_probability(
            tree=tree,
            total_basal_area_m2_ha=total_basal_area_m2_ha,
            log_total_basal_area=log_total_basal_area,
            mdbh_m=mdbh_m,
            mdbh2_m2=mdbh2_m2,
            wet_indicator=wet_indicator,
            pine_indicator=pine_indicator,
            thinning_indicator=thinning_indicator,
            near_edge_indicator=near_edge_indicator,
            edge_indicator=edge_indicator,
            altitude_m=site_conditions.altitude_m,
            latitude_deg=site_conditions.latitude_deg,
        )
        for tree in trees
    ]

    sum_tree_mortality = 0.0
    for tree, p_tree in zip(trees, step3_probabilities, strict=True):
        sum_tree_mortality += (
            tree_basal_area_cm2(tree)
            * stems_per_tree(tree, default_stems_per_tree)
            * p_tree
            / 10_000.0
        )
    correction_factor = (
        total_basal_area_m2_ha * p_basal_area / sum_tree_mortality
        if sum_tree_mortality > 0.0
        else 0.0
    )

    # Fridman & Ståhl (2001) eq. (4): p_i* = k * p_i is a *proportion* of trees that
    # die, so cap it at 1 before weighting by the plot-level mortality probability.
    probabilities = [
        clamp_probability(min(1.0, p_step3 * correction_factor) * p_plot)
        for p_step3 in step3_probabilities
    ]
    return (
        probabilities,
        {
            "p_plot": p_plot,
            "p_basal_area": p_basal_area,
            "correction_factor": correction_factor,
        },
    )


@dataclass(slots=True)
class Siipilehto2020MortalityModel:
    """Thin class facade for Siipilehto et al. (2020) mortality equations."""

    def predict_probabilities(
        self,
        *,
        context: MortalityContext,
        period_years: float = 5.0,
        default_stems_per_tree: float = 1.0,
    ) -> tuple[list[float], dict[str, Any]]:
        """Predict tree mortality probabilities using Siipilehto (2020) equations."""
        return siipilehto_2020_probabilities(
            context=context,
            period_years=period_years,
            default_stems_per_tree=default_stems_per_tree,
        )


__all__ = [
    "siipilehto_2020_probabilities",
    "Siipilehto2020MortalityModel",
]


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------


class _Descriptor:
    """FormulaModuleDescriptor for the Siipilehto et al. (2020) mortality functions."""

    @property
    def component_id(self):
        return "siipilehto_2020_mortality"

    @property
    def source(self):
        from pyforestry.base.contracts import SourceReference

        return SourceReference(
            author=(
                "Siipilehto, J., Allen, M., Nilsson, U., Brunner, A., Huuskonen, S., "
                "Haikarainen, S., Subramanian, N., Antón-Fernández, C., Holmström, E., "
                "Andreassen, K. & Hynynen, J."
            ),
            year=2020,
            title="Stand-level mortality models for Nordic boreal forests",
            note=(
                "Silva Fennica 54(5), article id 10414. "
                "https://doi.org/10.14214/sf.10414. Two-step stand-level survival "
                "model (Tables 5-6); per-tree distribution uses the step-III "
                "functions of Fridman & Ståhl (2001). Historically labelled 'SNS'."
            ),
        )

    @property
    def species_groups(self):
        return {}

    @property
    def units(self):
        return {}

    @property
    def kernel_names(self):
        return ["siipilehto_2020_probabilities", "Siipilehto2020MortalityModel"]


DESCRIPTOR = _Descriptor()
