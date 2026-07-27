"""Fridman & Ståhl (2001) mortality equations for Swedish forests."""

from __future__ import annotations

import math
import random
import warnings
from dataclasses import dataclass, field
from typing import Any

from pyforestry.base.contracts import FormulaDescriptor, SourceReference

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
from .types import (
    MortalityContext,
    MortalityRealizationMode,
    MortalityTreeRecord,
)


def _fridman_step3_probability(
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
    """Compute Fridman-Stahl step-3 mortality probability for one tree."""
    if tree.diameter_cm < 4.0:
        return 0.0

    diameter_m = tree.diameter_cm / 100.0
    tree_group = species_group(tree.species)
    if tree_group == "pine":
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
    elif tree_group == "spruce":
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
    elif tree_group == "birch":
        xb = (
            -2.83
            - 0.0665 * total_basal_area_m2_ha
            + 0.0362 * tree.bal
            - 16.5 * diameter_m
            + 27.7 * diameter_m * diameter_m
            + 1.10e-05 * altitude_m
            + 15.7 * mdbh_m
        )
    elif tree_group in {"oak", "beech", "southern_broadleaf"}:
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


def fridman_stahl_2001_probabilities(
    *,
    context: MortalityContext,
    implementation_type: MortalityRealizationMode = MortalityRealizationMode.DETERMINISTIC,
    period_years: float = 5.0,
    rng: random.Random | None = None,
    default_stems_per_tree: float = 1.0,
) -> tuple[list[float], dict[str, Any]]:
    """Calculate Fridman-Stahl tree mortality probabilities.

    Reference:
        Fridman, J. & Ståhl, G. (2001). A three-step approach for modelling
        tree mortality in Swedish forests. Scandinavian Journal of Forest
        Research 16(5):455-466. Step I predicts the probability of mortality on
        a plot, step II the proportion of basal area that dies (ln(PBA)=a+b*X),
        and step III distributes mortality among trees. Coefficients reproduce
        the paper's Tables 6-13.

    Args:
        context: Unified mortality context.
        implementation_type: Deterministic or stochastic routing.
        period_years: Prediction period in years.
        rng: Optional random generator for stochastic mode.
        default_stems_per_tree: Fallback represented stems per tree record.

    Returns:
        A tuple with per-tree probabilities and diagnostics.

    Raises:
        ValueError: If logarithm/division domains are invalid.
    """
    trees = context.trees
    stand_conditions = context.stand
    site_conditions = context.site
    history_conditions = context.history

    if not trees:
        return [], {"p_plot": 0.0, "p_basal_area": 0.0, "correction_factor": 0.0}

    if stand_conditions.plot_area_m2 <= 0.0:
        raise ValueError("plot_area_m2 must be > 0.")
    if stand_conditions.plot_area_m2 < 20.0 or stand_conditions.plot_area_m2 > 2_000.0:
        warnings.warn(
            f"plot_area_m2={stand_conditions.plot_area_m2} is outside common sample-plot ranges.",
            stacklevel=2,
        )

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

    mean_age_total_years = mean_tree_age_years(trees, stand_conditions.mean_age_total_years)
    bald_sqr = mean_age_total_years * mean_age_total_years
    mdbh2_m2 = (
        ((4.0 / math.pi) * total_basal_area_m2_ha) / total_stems_per_ha
        if total_stems_per_ha > 1.0e-4
        else 0.0
    )

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

    pine_ba = by_group.get("pine", 0.0)
    spruce_ba = by_group.get("spruce", 0.0)
    leaf_proportion = clamp_probability(1.0 - (pine_ba + spruce_ba) / total_basal_area_m2_ha)
    pine_proportion = clamp_probability(pine_ba / total_basal_area_m2_ha)
    dec10_indicator = int(leaf_proportion >= 0.1)
    pine_indicator = int(pine_proportion >= 0.7)
    other_dec_indicator = int(
        any(species_group(tree.species) in {"aspen", "other_broadleaf"} for tree in trees)
    )

    near_edge_indicator = 0
    edge_indicator = 0

    # pyforestry threads the caller's actual plot area into the step-1 log(plotArea),
    # step-2 plotArea and step-2b variance terms below, faithful to the original
    # Fridman-Ståhl (2001) predictor, which is a function of the plot area.
    step1_xb = (
        -9.07
        + 0.0216 * total_basal_area_m2_ha
        + 0.733 * log_total_basal_area
        + 0.401 * dec10_indicator
        + 1.62e-06 * site_conditions.altitude_m * site_conditions.altitude_m
        - 16.6 * mdbh2_m2
        + 0.129 * wet_indicator
        + 0.686 * other_dec_indicator
        + 0.278 * int(site_conditions.peat)
        + 0.862 * math.log(stand_conditions.plot_area_m2)  # actual plot area (see note above)
    )
    p_plot_5_year = 1.0 / (1.0 + math.exp(-step1_xb))
    p_plot = scale_probability_from_5_years(p_plot_5_year, period_years)

    step2_intercept = (
        -5.84 if implementation_type == MortalityRealizationMode.DETERMINISTIC else -5.90
    )
    step2_xb = (
        step2_intercept
        - 0.00449 * stand_conditions.plot_area_m2  # actual plot area
        - 1.65 * log_total_basal_area
        + 23.9 * mdbh_m
        + 1.21e-05 * bald_sqr
        - 19.0 * mdbh2_m2
        + 0.776 * math.log(total_stems_per_ha)
        + 0.107 * wet_indicator
        + 0.217 * near_edge_indicator
        + 0.130 * leaf_proportion
        + 0.140 * thinning_indicator
    )
    p_basal_area_5_year = math.exp(step2_xb)
    if p_basal_area_5_year > 0.9999:
        p_basal_area_5_year = 1.0
    elif p_basal_area_5_year < 0.00001:
        p_basal_area_5_year = 0.0
    p_basal_area = scale_probability_from_5_years(p_basal_area_5_year, period_years)

    step2_variance = (
        -2.74e-01
        + 5.60e-04 * stand_conditions.plot_area_m2  # actual plot area
        + 7.62e-02 * log_total_basal_area
        + 1.83 * mdbh_m
        + 1.71e-06 * bald_sqr
        + 1.50 * mdbh2_m2
    )
    if step2_variance < 0.0:
        warnings.warn(
            "Fridman-Stahl step-2 residual variance became negative; clamped to 0.",
            stacklevel=2,
        )
        step2_variance = 0.0

    event_occurred: bool | None = None
    p_basal_area_for_correction = p_basal_area
    if implementation_type == MortalityRealizationMode.STOCHASTIC:
        if rng is None:
            raise ValueError(
                "Stochastic mortality needs a random stream: pass rng=. Falling "
                "back to an unseeded random.Random() made the result "
                "irreproducible without saying so, and made the run's own seed a "
                "number that governed nothing. Use ctx.rng.child('mortality')."
            )
        generator = rng
        # Faithful to Fridman & Ståhl (2001), "Application": step I gives the
        # *probability of mortality* on the plot, and the paper directs that "if the
        # random number is less than the estimated probability, the tree will die".
        # Hence a draw below p_plot means mortality occurs on the plot.
        event_occurred = generator.random() < p_plot
        if not event_occurred:
            return (
                [0.0 for _ in trees],
                {
                    "p_plot": p_plot,
                    "p_basal_area": p_basal_area,
                    "p_basal_area_noisy": 0.0,
                    "correction_factor": 0.0,
                    "event_occurred": False,
                    "step2_variance": step2_variance,
                },
            )
        gaussian_residual = generator.gauss(0.0, math.sqrt(step2_variance))
        # Faithful to Fridman & Ståhl (2001) Model (2): ln(PBA) = a + b*X, so the
        # Gaussian residual is added in log space and the perturbation of the basal-
        # area proportion is therefore *multiplicative* (PBA*exp(ε)), then truncated
        # to [0, 1] as the paper directs (the multiplicative log-space form is the
        # paper-faithful choice).
        p_basal_area_for_correction = clamp_probability(
            p_basal_area * max(0.0, math.exp(gaussian_residual))
        )

    step3_probabilities = [
        _fridman_step3_probability(
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
        total_basal_area_m2_ha * p_basal_area_for_correction / sum_tree_mortality
        if sum_tree_mortality > 0.0
        else 0.0
    )

    conditional_probabilities = [
        clamp_probability(p_tree * correction_factor) for p_tree in step3_probabilities
    ]
    if implementation_type == MortalityRealizationMode.STOCHASTIC:
        final_probabilities = conditional_probabilities
    else:
        final_probabilities = [
            scale_probability_from_5_years(
                clamp_probability(p_cond * p_plot_5_year),
                period_years,
            )
            for p_cond in conditional_probabilities
        ]

    return (
        final_probabilities,
        {
            "p_plot": p_plot,
            "p_basal_area": p_basal_area,
            "p_basal_area_noisy": p_basal_area_for_correction,
            "correction_factor": correction_factor,
            "event_occurred": event_occurred,
            "step2_variance": step2_variance,
        },
    )


@dataclass(slots=True)
class FridmanStahl2001Model:
    """Thin class facade for Fridman-Stahl mortality equations."""

    implementation_type: MortalityRealizationMode = MortalityRealizationMode.DETERMINISTIC
    stochastic_seed: int | None = None
    #: The random stream stochastic runs draw from. Supply the run's --
    #: ``ctx.rng.child("mortality")`` -- so mortality follows the run's seed
    #: rather than a second seed carried here. When omitted, ``stochastic_seed``
    #: opens one through the RNG service, which keeps a directly-constructed
    #: model reproducible and its draws checkpointable.
    rng: random.Random | None = None
    _rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Take the injected random stream, or open one from ``stochastic_seed``."""
        if self.rng is not None:
            self._rng = self.rng
            return
        from pyforestry.simulation.services import RandomBundle

        self._rng = RandomBundle(int(self.stochastic_seed or 0)).rng_for()

    def predict_probabilities(
        self,
        *,
        context: MortalityContext,
        period_years: float = 5.0,
        default_stems_per_tree: float = 1.0,
    ) -> tuple[list[float], dict[str, Any]]:
        """Predict tree mortality probabilities using Fridman-Stahl equations."""
        return fridman_stahl_2001_probabilities(
            context=context,
            implementation_type=self.implementation_type,
            period_years=period_years,
            rng=self._rng,
            default_stems_per_tree=default_stems_per_tree,
        )


__all__ = [
    "fridman_stahl_2001_probabilities",
    "FridmanStahl2001Model",
]


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------


DESCRIPTOR = FormulaDescriptor(
    component_id="fridman_stahl_2001_mortality",
    source=SourceReference(
        author="Fridman, J. & Ståhl, G.",
        year=2001,
        title="A three-step approach for modelling tree mortality in Swedish forests",
        note=(
            "Scandinavian Journal of Forest Research 16(5):455-466 (2001). "
            "Three-step plot/basal-area/tree mortality model reproduced from "
            "the paper's Tables 6-13."
        ),
    ),
    species_groups={},
    units={},
    kernel_names=("fridman_stahl_2001_probabilities", "FridmanStahl2001Model"),
)
