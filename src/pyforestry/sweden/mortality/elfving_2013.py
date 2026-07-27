"""Elfving (2013) single-tree mortality equations for Sweden."""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Any

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers.tree_species import TreeSpecies

from ._common import (
    mean_tree_age_years,
    parse_species,
    resolve_soil_moisture_code,
    resolve_vegetation_code,
    scale_probability_from_5_years,
    species_basal_area_m2_ha_by_group,
    species_group,
)
from .types import MortalityContext, MortalityTreeRecord

# Only Scots and mountain pine belong to the "pine" species group in the sense that takes
# the wider BAL/(diameter+1) cap of 5.0. Larch and lodgepole (contorta) pine share the same
# diameter-growth grouping but are their own mortality groups and take the 2.5 cap.
_TRUE_PINE_SPECIES = frozenset(
    {TreeSpecies.Sweden.pinus_sylvestris, TreeSpecies.Sweden.pinus_mugo}
)


def _balddgp1(tree: MortalityTreeRecord, *, pine_cap: bool) -> float:
    """Return capped BAL/(diameter+1) used in Elfving mortality equations."""
    balddgp1 = tree.bal / (tree.diameter_cm + 1.0)
    return min(balddgp1, 5.0) if pine_cap else min(balddgp1, 2.5)


def elfving_2013_probabilities(
    *,
    context: MortalityContext,
    period_years: float = 5.0,
) -> tuple[list[float], dict[str, Any]]:
    """Calculate Elfving (2013) tree mortality probabilities.

    Reference:
        Elfving, B. (2013). Single-tree mortality functions for the Swedish forest,
        PM 2013-05-02 (unpublished working memo).

    Args:
        context: Unified mortality context.
        period_years: Prediction period in years.

    Returns:
        A tuple with per-tree probabilities and diagnostics.
    """
    trees = context.trees
    stand_conditions = context.stand
    site_conditions = context.site
    history_conditions = context.history

    if not trees:
        return [], {}

    if site_conditions.site_index_m <= 0.0:
        raise ValueError("site_index_m must be > 0 for Elfving mortality.")

    soil_moisture_code = resolve_soil_moisture_code(site_conditions)
    if soil_moisture_code < 1 or soil_moisture_code > 5:
        warnings.warn(
            f"soil_moisture code {soil_moisture_code} is outside expected [1, 5].",
            stacklevel=2,
        )
    local_soil_moisture = soil_moisture_code if soil_moisture_code <= 2 else soil_moisture_code - 1

    by_group = species_basal_area_m2_ha_by_group(
        trees=trees,
        stand_conditions=stand_conditions,
    )
    total_basal_area_m2_ha = (
        stand_conditions.total_basal_area_m2_ha
        if stand_conditions.total_basal_area_m2_ha is not None
        else sum(by_group.values())
    )
    if total_basal_area_m2_ha <= 0.0:
        raise ValueError("total_basal_area_m2_ha must be > 0 for Elfving mortality.")

    mean_age_excl = (
        stand_conditions.mean_age_excl_overstorey_years
        if stand_conditions.mean_age_excl_overstorey_years is not None
        else mean_tree_age_years(trees, stand_conditions.mean_age_total_years)
    )
    mean_age_excl = min(160.0, mean_age_excl)
    mean_age_overstorey = (
        stand_conditions.mean_age_overstorey_years
        if stand_conditions.mean_age_overstorey_years > 0.0
        else mean_age_excl
    )

    thinned_within_0_2 = (
        bool(history_conditions.thinned_within_0_2_years) if history_conditions else False
    )
    thinned_within_2_20 = (
        bool(history_conditions.thinned_within_2_20_years) if history_conditions else False
    )
    thinned_2_indicator = int(thinned_within_0_2)
    thinned_20_indicator = int(not thinned_within_0_2 and thinned_within_2_20)

    dg_cm = (
        stand_conditions.mean_diameter_dg_cm
        if stand_conditions.mean_diameter_dg_cm is not None
        else stand_conditions.mean_diameter_arithmetic_cm
    )
    if dg_cm is None:
        dg_cm = sum(tree.diameter_cm for tree in trees) / float(len(trees))

    thinning_intensity_fraction = (
        history_conditions.thinning_intensity_fraction if history_conditions else 0.0
    )
    thinning_form_q = history_conditions.thinning_form_q if history_conditions else 0.0
    addition_to_pine_spruce = (
        (thinning_intensity_fraction**3.0) * dg_cm * thinning_form_q if thinned_within_0_2 else 0.0
    )

    spruce_prop = by_group.get("spruce", 0.0) / total_basal_area_m2_ha
    herb_type = int(0 < resolve_vegetation_code(site_conditions) <= 8)
    wet = 1.0 / 3.0 if soil_moisture_code == 5 else 0.0
    peat = int(site_conditions.peat)
    altitude_div_100 = site_conditions.altitude_m / 100.0
    temperature_sum_div_100 = site_conditions.temperature_sum / 100.0
    latitude_minus_50 = site_conditions.latitude_deg - 50.0
    mean_age_div100_excl = mean_age_excl / 100.0
    mean_age_div100_over = mean_age_overstorey / 100.0
    basal_area_div_sis = total_basal_area_m2_ha / site_conditions.site_index_m

    pine_base = (
        5.5057
        - 0.7544 * spruce_prop
        - 1.3815 * wet
        - 0.267 * local_soil_moisture
        - 0.2021 * peat
        - 0.3159 * herb_type
        + 0.4068 * thinned_2_indicator
        - 0.36 * addition_to_pine_spruce
    )
    spruce_base = (
        5.4892
        - 0.5338 * spruce_prop
        - 1.4598 * wet
        - 0.4963 * herb_type
        + 0.2925 * thinned_20_indicator
        - 0.2911 * thinned_2_indicator
        + 0.0256 * site_conditions.site_index_m
        - 0.36 * addition_to_pine_spruce
    )
    birch_base = (
        3.0519
        - 0.7747 * wet
        + 0.3974 * thinned_20_indicator
        - 0.1780 * altitude_div_100
        + 0.3966 * basal_area_div_sis
        + 0.3280 * latitude_minus_50
        - 0.0151 * latitude_minus_50 * latitude_minus_50
    )

    probabilities_5_year: list[float] = []
    for tree in trees:
        if tree.diameter_cm <= 0.0:
            raise ValueError("diameter_cm must be > 0 for Elfving mortality.")

        group = species_group(tree.species)
        tree_species = parse_species(tree.species)
        age_term = mean_age_div100_over if tree.is_overstorey else mean_age_div100_excl

        if tree_species == TreeSpecies.Sweden.pinus_contorta:
            # Contorta is its own mortality group, so BAL/(d+1) takes the 2.5 cap,
            # not the 5.0 pine cap.
            y = 2.0 * (pine_base - 0.9254 * _balddgp1(tree, pine_cap=False))
        elif group == "pine":
            # Only true pines take the 5.0 cap; larches (routed through the same
            # diameter-growth group) take the 2.5 cap.
            pine_cap = tree_species in _TRUE_PINE_SPECIES
            y = pine_base - 0.9254 * _balddgp1(tree, pine_cap=pine_cap)
        elif group == "spruce":
            y = (
                spruce_base
                - 0.5312 * _balddgp1(tree, pine_cap=False)
                - 0.0201 * tree.diameter_cm
                - 0.6570 * age_term
            )
        elif group == "birch":
            y = birch_base - 0.6463 * _balddgp1(tree, pine_cap=False) - 0.7160 * age_term
        elif group == "aspen":
            y = (
                5.2462
                - 0.3946 * _balddgp1(tree, pine_cap=False)
                - 1.1700 * age_term
                - 0.2750 * altitude_div_100
            )
        elif group in {"southern_broadleaf", "oak", "beech"}:
            y = (
                -0.5810
                - 0.5083 * _balddgp1(tree, pine_cap=False)
                + 0.3800 * temperature_sum_div_100
            )
        else:
            y = (
                0.2550
                - 0.3375 * _balddgp1(tree, pine_cap=False)
                + 0.2250 * temperature_sum_div_100
            )

        probabilities_5_year.append(1.0 / (1.0 + math.exp(y)))

    probabilities = [
        scale_probability_from_5_years(probability_5, period_years)
        for probability_5 in probabilities_5_year
    ]
    return (
        probabilities,
        {
            "spruce_proportion": spruce_prop,
            "herb_type_indicator": herb_type,
            "thinned_within_0_2_years": thinned_2_indicator,
            "thinned_within_2_20_years": thinned_20_indicator,
            "addition_to_pine_spruce_func": addition_to_pine_spruce,
        },
    )


@dataclass(slots=True)
class Elfving2013MortalityModel:
    """Thin class facade for Elfving (2013) mortality equations."""

    def predict_probabilities(
        self,
        *,
        context: MortalityContext,
        period_years: float = 5.0,
        default_stems_per_tree: float = 1.0,
    ) -> tuple[list[float], dict[str, Any]]:
        """Predict tree mortality probabilities using Elfving equations.

        ``default_stems_per_tree`` is accepted for a uniform mortality-model
        interface but is unused: the Elfving (2013) equations are per-tree and
        need no represented-stem count.
        """
        return elfving_2013_probabilities(
            context=context,
            period_years=period_years,
        )


__all__ = [
    "elfving_2013_probabilities",
    "Elfving2013MortalityModel",
]


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------


DESCRIPTOR = FormulaDescriptor(
    component_id="elfving_2013_mortality",
    source=SourceReference(
        author="Elfving, B.",
        year=2013,
        title="Single-tree mortality functions for the Swedish forest",
        note="PM 2013-05-02 (unpublished working memo).",
    ),
    species_groups={"pine": frozenset(), "spruce": frozenset(), "birch": frozenset()},
    units={"diameter_cm": "cm", "basal_area_m2_ha": "m²/ha", "return": "probability"},
    kernel_names=("elfving_2013_probabilities",),
)
