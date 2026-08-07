"""Shared helpers for Swedish mortality models."""

from __future__ import annotations

import math
import warnings
from collections.abc import Sequence

from pyforestry.base.helpers.tree_species import TreeName, TreeSpecies, parse_tree_species
from pyforestry.sweden.site.enums import Sweden

from .types import MortalitySiteConditions, MortalityStandConditions, MortalityTreeRecord

_PINE_SPECIES = {
    TreeSpecies.Sweden.pinus_sylvestris,
    TreeSpecies.Sweden.pinus_mugo,
    TreeSpecies.Sweden.pinus_contorta,
    TreeSpecies.Sweden.larix_sibirica,
    TreeSpecies.Sweden.larix_decidua,
    TreeSpecies.Sweden.larix_europaea_x_leptolepis,
    TreeSpecies.Sweden.larix_sukaczewii,
}
_SPRUCE_SPECIES = {
    TreeSpecies.Sweden.picea_abies,
    TreeSpecies.Sweden.picea_sitchensis,
    TreeSpecies.Sweden.picea_mariana,
}
_BIRCH_SPECIES = {
    TreeSpecies.Sweden.betula_pendula,
    TreeSpecies.Sweden.betula_pubescens,
}
_ASPEN_SPECIES = {
    TreeSpecies.Sweden.populus_tremula,
    TreeSpecies.Sweden.populus_tremula_x_tremuloides,
}
_OAK_SPECIES = {
    TreeSpecies.Sweden.quercus_robur,
    TreeSpecies.Sweden.quercus_petraea,
    TreeSpecies.Sweden.quercus_rubra,
}
_BEECH_SPECIES = {TreeSpecies.Sweden.fagus_sylvatica}
_SOUTHERN_BROADLEAF_SPECIES = {
    TreeSpecies.Sweden.fraxinus_excelsior,
    TreeSpecies.Sweden.ulmus_glabra,
    TreeSpecies.Sweden.ulmus_minor,
    TreeSpecies.Sweden.ulmus_laevis,
    TreeSpecies.Sweden.tilia_cordata,
    TreeSpecies.Sweden.acer_platanoides,
    TreeSpecies.Sweden.carpinus_betulus,
    TreeSpecies.Sweden.prunus_avium,
}


def clamp_probability(value: float) -> float:
    """Clamp a probability/fraction to [0, 1]."""
    return max(0.0, min(1.0, value))


def logistic(xb: float) -> float:
    """Compute logistic transform with overflow-safe branches."""
    if xb >= 0:
        ez = math.exp(-xb)
        return 1.0 / (1.0 + ez)
    ez = math.exp(xb)
    return ez / (1.0 + ez)


def combined_probability(p_a: float, p_b: float) -> float:
    """Combine two independent probabilities."""
    return clamp_probability(p_a + p_b - p_a * p_b)


def scale_probability_from_5_years(probability_5_years: float, period_years: float) -> float:
    """Scale a 5-year probability to any positive period via hazard conversion."""
    probability_5_years = clamp_probability(probability_5_years)
    if period_years <= 0.0:
        raise ValueError("period_years must be > 0.")
    if math.isclose(period_years, 5.0):
        return probability_5_years
    if period_years < 1.0 or period_years > 10.0:
        warnings.warn(
            f"period_years={period_years} is outside the common [1, 10] range.",
            stacklevel=2,
        )
    if probability_5_years == 0.0:
        return 0.0
    if probability_5_years == 1.0:
        return 1.0
    hazard = -math.log1p(-probability_5_years) / 5.0
    return clamp_probability(1.0 - math.exp(-hazard * period_years))


def resolve_soil_moisture_code(site_conditions: MortalitySiteConditions) -> int:
    """Resolve a numeric soil-moisture code from the site state."""
    soil_moisture = site_conditions.soil_moisture
    if isinstance(soil_moisture, Sweden.SoilMoistureEnum):
        return int(soil_moisture.value.code)
    return int(soil_moisture)


def resolve_vegetation_code(site_conditions: MortalitySiteConditions) -> int:
    """Resolve vegetation type code from direct code or field-layer enum."""
    if site_conditions.vegetation_type_code is not None:
        return int(site_conditions.vegetation_type_code)
    if site_conditions.field_layer is not None:
        return int(site_conditions.field_layer.value.code)
    return 0


def normalize_part_of_sweden(part_of_sweden: str) -> str:
    """Normalize regional label into `north`, `middle`, or `south`."""
    label = part_of_sweden.strip().lower()
    if label in {"north", "northern"}:
        return "north"
    if label in {"middle", "central"}:
        return "middle"
    if label in {"south", "southern"}:
        return "south"
    warnings.warn(
        f"Unrecognized part_of_sweden={part_of_sweden!r}. Falling back to 'middle'.",
        stacklevel=2,
    )
    return "middle"


def parse_species(species: TreeName | str) -> TreeName:
    """Parse species into a canonical `TreeName`."""
    if isinstance(species, TreeName):
        return species
    return parse_tree_species(species)


def species_key(species: TreeName | str) -> str:
    """Return canonical lowercase species key."""
    return parse_species(species).full_name


def species_group(species: TreeName | str) -> str:
    """Return tree-model species group used by mortality equations."""
    tree_species = parse_species(species)
    if tree_species in _PINE_SPECIES:
        return "pine"
    if tree_species in _SPRUCE_SPECIES:
        return "spruce"
    if tree_species in _BIRCH_SPECIES:
        return "birch"
    if tree_species in _ASPEN_SPECIES:
        return "aspen"
    if tree_species in _OAK_SPECIES:
        return "oak"
    if tree_species in _BEECH_SPECIES:
        return "beech"
    if tree_species in _SOUTHERN_BROADLEAF_SPECIES:
        return "southern_broadleaf"
    return "other_broadleaf"


def calibration_group(species: TreeName | str) -> str:
    """Return calibration group (`pine`, `spruce`, `birch`, `other`)."""
    group = species_group(species)
    if group == "pine":
        return "pine"
    if group == "spruce":
        return "spruce"
    if group == "birch":
        return "birch"
    return "other"


def stems_per_tree(tree: MortalityTreeRecord, default_stems_per_tree: float = 1.0) -> float:
    """Resolve stems represented by a tree record."""
    stems = default_stems_per_tree if tree.stems_per_tree is None else float(tree.stems_per_tree)
    if stems <= 0.0:
        raise ValueError("stems_per_tree must be > 0.")
    return stems


def tree_basal_area_cm2(tree: MortalityTreeRecord) -> float:
    """Resolve basal area in cm2 for a tree state."""
    if tree.basal_area_cm2 is not None:
        if tree.basal_area_cm2 <= 0.0:
            raise ValueError("basal_area_cm2 must be > 0 when provided.")
        return float(tree.basal_area_cm2)
    if tree.diameter_cm <= 0.0:
        raise ValueError("diameter_cm must be > 0 to derive basal area.")
    radius_cm = tree.diameter_cm / 2.0
    return math.pi * radius_cm * radius_cm


def species_basal_area_m2_ha_by_group(
    trees: Sequence[MortalityTreeRecord],
    stand_conditions: MortalityStandConditions,
    default_stems_per_tree: float = 1.0,
) -> dict[str, float]:
    """Return species-group basal area map in m2/ha-like units."""
    if stand_conditions.species_basal_area_m2_ha:
        by_group: dict[str, float] = {}
        for raw_key, value in stand_conditions.species_basal_area_m2_ha.items():
            key = str(raw_key).strip().lower()
            if key in {"pine", "spruce", "birch", "aspen", "oak", "beech", "southern_broadleaf"}:
                group = key
            else:
                try:
                    group = species_group(raw_key)
                except ValueError:
                    group = "other_broadleaf"
            by_group[group] = by_group.get(group, 0.0) + float(value)
        return by_group

    by_group: dict[str, float] = {}
    for tree in trees:
        group = species_group(tree.species)
        weighted_ba = tree_basal_area_cm2(tree) * stems_per_tree(tree, default_stems_per_tree)
        by_group[group] = by_group.get(group, 0.0) + weighted_ba / 10_000.0
    return by_group


def species_mortality_fraction_from_tree_probabilities(
    trees: Sequence[MortalityTreeRecord],
    tree_probabilities: Sequence[float],
    default_stems_per_tree: float = 1.0,
    *,
    use_calibration_groups: bool = False,
) -> dict[str, float]:
    """Aggregate basal-area weighted mortality fractions by species key/group."""
    if len(trees) != len(tree_probabilities):
        raise ValueError("trees and tree_probabilities must have equal length.")

    numerator: dict[str, float] = {}
    denominator: dict[str, float] = {}
    for tree, probability in zip(trees, tree_probabilities, strict=True):
        key = (
            calibration_group(tree.species)
            if use_calibration_groups
            else species_key(tree.species)
        )
        weighted_ba = tree_basal_area_cm2(tree) * stems_per_tree(tree, default_stems_per_tree)
        numerator[key] = numerator.get(key, 0.0) + weighted_ba * clamp_probability(probability)
        denominator[key] = denominator.get(key, 0.0) + weighted_ba

    fractions: dict[str, float] = {}
    for key, total_ba in denominator.items():
        fractions[key] = 0.0 if total_ba <= 0.0 else clamp_probability(numerator[key] / total_ba)
    return fractions


def mean_tree_age_years(
    trees: Sequence[MortalityTreeRecord],
    fallback_years: float | None,
) -> float:
    """Resolve mean tree age, falling back to stand-level value when needed."""
    ages = [float(tree.age_total_years) for tree in trees if tree.age_total_years is not None]
    if ages:
        return sum(ages) / len(ages)
    if fallback_years is None:
        raise ValueError("Mean age is required for this equation.")
    return float(fallback_years)
