"""Naslund (1986) damage and mortality functions for young stands."""

from __future__ import annotations

from enum import Enum
from math import exp, log
from typing import Sequence

from pyforestry.base.helpers.tree import Tree
from pyforestry.base.helpers.tree_species import TreeName, TreeSpecies
from pyforestry.simulation.contracts import SourceReference


class SaplingSpeciesGroup(Enum):
    """Species groups used in the Naslund (1986) damage model."""

    PINE = "pine"
    LARCH = "larch"
    SPRUCE = "spruce"
    CONTORTA = "contorta"
    BIRCH = "birch"
    ASPEN = "aspen"
    OTHER_BROADLEAF = "other_broadleaf"


class DamageDegree(Enum):
    """Damage severity classes."""

    MINOR = 0
    SEVERE = 1
    DEAD = 2


class PineCausalAgent(Enum):
    """Causal agent ordering for pine/larch damage."""

    MOOSE = 0
    WHIP = 1
    SNOWBLIGHT = 2
    SNOW = 3
    REMAINDER = 4


class SpruceCausalAgent(Enum):
    """Causal agent ordering for spruce damage."""

    WHIP = 0
    FROST = 1
    REMAINDER = 2


class ContortaCausalAgent(Enum):
    """Causal agent ordering for contorta damage."""

    MOOSE = 0
    VOLE = 1
    REMAINDER = 2


class BirchCausalAgent(Enum):
    """Causal agent ordering for birch damage."""

    MOOSE = 0
    REMAINDER = 1


class AspenCausalAgent(Enum):
    """Causal agent ordering for aspen damage."""

    MOOSE = 0
    REMAINDER = 1


_PINE_SPECIES = {
    TreeSpecies.Sweden.pinus_sylvestris,
    TreeSpecies.Sweden.larix_sibirica,
    TreeSpecies.Sweden.larix_decidua,
    TreeSpecies.Sweden.larix_europaea_x_leptolepis,
    TreeSpecies.Sweden.larix_sukaczewii,
}
_SPRUCE_SPECIES = {TreeSpecies.Sweden.picea_abies}
_CONTORTA_SPECIES = {TreeSpecies.Sweden.pinus_contorta}
_BIRCH_SPECIES = {TreeSpecies.Sweden.betula_pendula, TreeSpecies.Sweden.betula_pubescens}
_ASPEN_SPECIES = {
    TreeSpecies.Sweden.populus_tremula,
    TreeSpecies.Sweden.populus_tremula_x_tremuloides,
}


def _species_group(species: TreeName) -> SaplingSpeciesGroup:
    """Map a tree species to the Naslund sapling species group."""
    if species in _PINE_SPECIES:
        return SaplingSpeciesGroup.PINE
    if species in _CONTORTA_SPECIES:
        return SaplingSpeciesGroup.CONTORTA
    if species in _SPRUCE_SPECIES:
        return SaplingSpeciesGroup.SPRUCE
    if species in _BIRCH_SPECIES:
        return SaplingSpeciesGroup.BIRCH
    if species in _ASPEN_SPECIES:
        return SaplingSpeciesGroup.ASPEN
    return SaplingSpeciesGroup.OTHER_BROADLEAF


def _min_max(min_val: float, value: float, max_val: float) -> float:
    """Clamp ``value`` to the closed interval ``[min_val, max_val]``."""
    return max(min_val, min(max_val, value))


def _prop_damage(x: float) -> float:
    """Convert a logit-scale value to damage proportion via logistic transform."""
    exp_x = exp(x)
    return exp_x / (exp_x + 1.0)


def _stems_and_mean_heights_from_tree_list(
    trees: Sequence[Tree], *, expansion_factor: float = 1.0
) -> tuple[dict[SaplingSpeciesGroup, float], dict[SaplingSpeciesGroup, float]]:
    """Aggregate stems and mean heights per sapling group from a tree list."""
    stems: dict[SaplingSpeciesGroup, float] = {sg: 0.0 for sg in SaplingSpeciesGroup}
    height_sums: dict[SaplingSpeciesGroup, float] = {sg: 0.0 for sg in SaplingSpeciesGroup}

    for tree in trees:
        if tree.species is None or tree.height_m is None:
            continue
        stems_val = (tree.weight_n or 0.0) * expansion_factor
        group = _species_group(tree.species)
        stems[group] += stems_val
        height_sums[group] += stems_val * tree.height_m

    mean_heights = {
        sg: (height_sums[sg] / stems[sg] if stems[sg] > 0.0 else 0.0) for sg in SaplingSpeciesGroup
    }
    return stems, mean_heights


def _damage_prop_pine_formula(
    *,
    mean_height_pine_larch: float,
    prop_pine: float,
    stems_pine_larch: float,
    total_stems: float,
    mean_height_leaf: float,
    total_mean_height: float,
    site_index_pine_m: float,
    climate_index: float,
    moose_factor: float,
    snow_blight_factor: float,
    snow_break_factor: float,
    whip_factor: float,
    other_factor: float,
) -> float:
    """Evaluate pine-group damage proportion from causal-agent component logits."""
    ln_moose = (
        -0.21 * mean_height_pine_larch
        + -1.36 * prop_pine
        + 0.0 * stems_pine_larch
        + 0.0 * total_stems
        + 0.07 * mean_height_leaf
        + 0.0 * total_mean_height
        + 0.0 * site_index_pine_m
        + 0.0 * climate_index
        + -0.58
    )
    ln_whip = (
        0.0 * mean_height_pine_larch
        + -1.85 * prop_pine
        + 0.0 * stems_pine_larch
        + 1.3e-04 * total_stems
        + 0.0 * mean_height_leaf
        + 0.11 * total_mean_height
        + 0.0 * site_index_pine_m
        + 0.0 * climate_index
        + -2.73
    )
    ln_snowblight = (
        -0.21 * mean_height_pine_larch
        + 0.0 * prop_pine
        + -3.91e-04 * stems_pine_larch
        + 0.0 * total_stems
        + 0.0 * mean_height_leaf
        + 0.0 * total_mean_height
        + 0.0 * site_index_pine_m
        + 1.55e-03 * climate_index
        + -6.90
    )
    ln_snow = (
        0.0 * mean_height_pine_larch
        + -1.46 * prop_pine
        + 0.0 * stems_pine_larch
        + 0.0 * total_stems
        + 0.0 * mean_height_leaf
        + 0.09 * total_mean_height
        + 0.0 * site_index_pine_m
        + 0.0 * climate_index
        + -2.54
    )
    ln_other = (
        0.0 * mean_height_pine_larch
        + -1.13 * prop_pine
        + 0.0 * stems_pine_larch
        + -2.31e-04 * total_stems
        + 0.0 * mean_height_leaf
        + 0.0 * total_mean_height
        + -0.07 * site_index_pine_m
        + 0.0 * climate_index
        + 0.71
    )
    return (
        moose_factor * _prop_damage(ln_moose)
        + whip_factor * _prop_damage(ln_whip)
        + snow_blight_factor * _prop_damage(ln_snowblight)
        + snow_break_factor * _prop_damage(ln_snow)
        + other_factor * _prop_damage(ln_other)
    )


def _damage_prop_spruce_formula(
    *,
    mean_height_spruce: float,
    stems_spruce: float,
    prop_spruce: float,
    sum_height_leaf: float,
    mean_height_leaf: float,
    climate_index: float,
    site_index_spruce_m: float,
    whip_factor: float,
    frost_factor: float,
    other_factor: float,
) -> float:
    """Evaluate spruce damage proportion from whip/frost/other components."""
    ln_whip = (
        0.0 * mean_height_spruce
        + 0.0 * stems_spruce
        + -0.86 * prop_spruce
        + 1.89e-05 * sum_height_leaf
        + 0.06 * mean_height_leaf
        + 0.0 * climate_index
        + 0.0 * site_index_spruce_m
        + -2.58
    )
    ln_frost = (
        -0.11 * mean_height_spruce
        + -5.12e-04 * stems_spruce
        + 0.0 * prop_spruce
        + 0.0 * sum_height_leaf
        + 0.0 * mean_height_leaf
        + 0.0 * climate_index
        + 0.0 * site_index_spruce_m
        + -1.96
    )
    ln_other = (
        0.0 * mean_height_spruce
        + -2.63e-04 * stems_spruce
        + 0.0 * prop_spruce
        + 0.0 * sum_height_leaf
        + 0.0 * mean_height_leaf
        + 8.29e-04 * climate_index
        + -0.02 * site_index_spruce_m
        + -3.87
    )
    return (
        whip_factor * _prop_damage(ln_whip)
        + frost_factor * _prop_damage(ln_frost)
        + other_factor * _prop_damage(ln_other)
    )


def _damage_prop_contorta_formula(
    *,
    mean_height_contorta: float,
    stems_contorta: float,
    latitude_deg: float,
    moose_factor: float,
    vole_factor: float,
    other_factor: float,
) -> float:
    """Evaluate contorta damage proportion from moose/vole/other components."""
    ln_moose = 0.0 * mean_height_contorta + 0.0 * stems_contorta + 0.0 * latitude_deg + -2.55
    ln_vole = (
        -0.63 * mean_height_contorta + -5.62e-04 * stems_contorta + 0.0 * latitude_deg + -0.43
    )
    ln_other = 0.34 * mean_height_contorta + 0.0 * stems_contorta + -0.51 * latitude_deg + -34.10
    return (
        moose_factor * _prop_damage(ln_moose)
        + vole_factor * _prop_damage(ln_vole)
        + other_factor * _prop_damage(ln_other)
    )


def _damage_prop_birch_formula(
    *,
    mean_height_birch: float,
    prop_pine: float,
    prop_birch: float,
    stems_birch: float,
    moose_factor: float,
    other_factor: float,
) -> float:
    """Evaluate birch damage proportion from moose and remainder components."""
    ln_moose = (
        -0.38 * mean_height_birch + 1.16 * prop_pine + 0.0 * prop_birch + 0.0 * stems_birch + -0.61
    )
    ln_other = (
        0.0 * mean_height_birch
        + 0.0 * prop_pine
        + 0.69 * prop_birch
        + -5.06e-04 * stems_birch
        + -1.94
    )
    return moose_factor * _prop_damage(ln_moose) + other_factor * _prop_damage(ln_other)


def _damage_prop_aspen_formula(
    *,
    mean_height_aspen: float,
    prop_pine: float,
    prop_other_leaf: float,
    stems_aspen: float,
    total_mean_height: float,
    moose_factor: float,
    other_factor: float,
) -> float:
    """Evaluate aspen damage proportion from moose and remainder components."""
    ln_moose = (
        -0.63 * mean_height_aspen
        + 1.13 * prop_pine
        + 0.0 * prop_other_leaf
        + 0.0 * stems_aspen
        + 0.0 * total_mean_height
        + 1.94
    )
    ln_other = (
        0.0 * mean_height_aspen
        + 0.0 * prop_pine
        + -1.01 * prop_other_leaf
        + -5.24e-04 * stems_aspen
        + 0.28 * total_mean_height
        + -2.05
    )
    return moose_factor * _prop_damage(ln_moose) + other_factor * _prop_damage(ln_other)


def _degree_pine_formula(
    height_m: float, causal_agent: int, moose_damage_prop: float | None
) -> list[float]:
    """Return pine damage-degree probabilities ``[minor, severe, dead]``."""
    minor = severe = 0.0
    if causal_agent == PineCausalAgent.MOOSE.value:
        if moose_damage_prop is None:
            raise ValueError("moose_damage_prop is required for pine moose damage.")
        minor = min(
            0.95,
            0.25 * height_m - 0.28 * log(height_m) - 0.26 * moose_damage_prop + 0.1,
        )
        severe = -0.16 * height_m + 0.11 * log(height_m) + 0.26 * moose_damage_prop + 0.58
    elif causal_agent == PineCausalAgent.WHIP.value:
        minor, severe = 0.39, 0.44
    elif causal_agent == PineCausalAgent.SNOWBLIGHT.value:
        minor = min(1.0, 0.42 * height_m + 0.04)
        severe = -0.12 * height_m + 0.22
    elif causal_agent == PineCausalAgent.SNOW.value:
        minor, severe = 0.29, 0.29
    elif causal_agent == PineCausalAgent.REMAINDER.value:
        minor = min(1.0, 0.09 * height_m + 0.28)
        severe = -0.02 * height_m + 0.28
    severe = _min_max(0.0, severe, 1.0 - minor)
    dead = 1.0 - minor - severe
    return [minor, severe, dead]


def _degree_spruce_formula(height_m: float, causal_agent: int) -> list[float]:
    """Return spruce damage-degree probabilities ``[minor, severe, dead]``."""
    minor = severe = 0.0
    if causal_agent == SpruceCausalAgent.WHIP.value:
        minor = 0.03 * height_m + 0.57
        severe = -0.03 * height_m + 0.38
    elif causal_agent == SpruceCausalAgent.FROST.value:
        minor = min(1.0, 0.15 * log(height_m) + 0.72)
        severe = -0.13 * log(height_m) + 0.27
    elif causal_agent == SpruceCausalAgent.REMAINDER.value:
        minor = 0.11 * log(height_m) + 0.61
        severe = -0.08 * log(height_m) + 0.3
    severe = _min_max(0.0, severe, 1.0 - minor)
    dead = 1.0 - minor - severe
    return [minor, severe, dead]


def _degree_birch_formula(
    height_m: float, causal_agent: int, moose_damage_prop: float | None
) -> list[float]:
    """Return birch damage-degree probabilities ``[minor, severe, dead]``."""
    minor = severe = 0.0
    if causal_agent == BirchCausalAgent.MOOSE.value:
        if moose_damage_prop is None:
            raise ValueError("moose_damage_prop is required for birch moose damage.")
        minor = -0.38 * moose_damage_prop + 0.60
        severe = 0.38 * moose_damage_prop + 0.36
    elif causal_agent == BirchCausalAgent.REMAINDER.value:
        minor = min(1.0, 0.07 * height_m + 0.33)
        severe = -0.04 * height_m + 0.42
    severe = _min_max(0.0, severe, 1.0 - minor)
    dead = 1.0 - minor - severe
    return [minor, severe, dead]


def _degree_aspen_formula(height_m: float, causal_agent: int) -> list[float]:
    """Return aspen damage-degree probabilities ``[minor, severe, dead]``."""
    minor = severe = 0.0
    if causal_agent == AspenCausalAgent.MOOSE.value:
        minor = _min_max(0.0, 0.12 * height_m - 0.08, 1.0)
        severe = -0.13 * height_m + 0.86
    elif causal_agent == AspenCausalAgent.REMAINDER.value:
        minor, severe = 0.20, 0.30
    severe = _min_max(0.0, severe, 1.0 - minor)
    dead = 1.0 - minor - severe
    return [minor, severe, dead]


def _degree_contorta_formula(height_m: float, causal_agent: int) -> list[float]:
    """Return contorta damage-degree probabilities ``[minor, severe, dead]``."""
    minor = severe = 0.0
    if causal_agent == ContortaCausalAgent.MOOSE.value:
        minor = min(1.0, -0.63 * height_m + 0.10 * height_m**2 + 1.51)
        severe = 1.0 - minor
    elif causal_agent == ContortaCausalAgent.VOLE.value:
        minor = min(1.0, -0.68 * height_m + 0.16 * height_m**2 + 0.81)
        severe = 1.07 * height_m - 0.20 * height_m**2 - 0.76
    elif causal_agent == ContortaCausalAgent.REMAINDER.value:
        minor = min(1.0, 0.14 * height_m + 0.30)
        severe = -0.04 * height_m + 0.27
    severe = _min_max(0.0, severe, 1.0 - minor)
    dead = 1.0 - minor - severe
    return [minor, severe, dead]


class Naslund1986DamageModel:
    """Deterministic damage proportions and severity for young stands."""

    @staticmethod
    def damage_proportions_from_trees(
        trees: Sequence[Tree],
        *,
        site_index_pine_m: float,
        site_index_spruce_m: float,
        latitude_deg: float,
        altitude_m: float,
        expansion_factor: float = 1.0,
        moose_factor: float = 1.0,
        vole_factor: float = 1.0,
        snow_break_factor: float = 1.0,
        whip_factor: float = 1.0,
        frost_factor: float = 1.0,
        snow_blight_factor: float = 1.0,
        other_factor: float = 1.0,
    ) -> dict[SaplingSpeciesGroup, float]:
        """Compute damage proportions from a tree list.

        Args:
            trees (Sequence[Tree]): Trees with ``height_m``, ``weight_n`` and species set.
            site_index_pine_m (float): Pine site index (m).
            site_index_spruce_m (float): Spruce site index (m).
            latitude_deg (float): Latitude (degrees).
            altitude_m (float): Altitude (m).
            expansion_factor (float): Factor to convert tree weights to stems per ha.
            moose_factor (float): Adjustment factor for moose damage.
            vole_factor (float): Adjustment factor for vole damage.
            snow_break_factor (float): Adjustment factor for snow break damage.
            whip_factor (float): Adjustment factor for whipping damage.
            frost_factor (float): Adjustment factor for frost damage.
            snow_blight_factor (float): Adjustment factor for snow blight damage.
            other_factor (float): Adjustment factor for other agents.

        Returns:
            dict[SaplingSpeciesGroup, float]: Proportion damaged per species group.
        """
        stems, mean_heights = _stems_and_mean_heights_from_tree_list(
            trees, expansion_factor=expansion_factor
        )
        return Naslund1986DamageModel.damage_proportions(
            stems=stems,
            mean_heights=mean_heights,
            site_index_pine_m=site_index_pine_m,
            site_index_spruce_m=site_index_spruce_m,
            latitude_deg=latitude_deg,
            altitude_m=altitude_m,
            moose_factor=moose_factor,
            vole_factor=vole_factor,
            snow_break_factor=snow_break_factor,
            whip_factor=whip_factor,
            frost_factor=frost_factor,
            snow_blight_factor=snow_blight_factor,
            other_factor=other_factor,
        )

    @staticmethod
    def damage_proportions(
        *,
        stems: dict[SaplingSpeciesGroup, float],
        mean_heights: dict[SaplingSpeciesGroup, float],
        site_index_pine_m: float,
        site_index_spruce_m: float,
        latitude_deg: float,
        altitude_m: float,
        moose_factor: float = 1.0,
        vole_factor: float = 1.0,
        snow_break_factor: float = 1.0,
        whip_factor: float = 1.0,
        frost_factor: float = 1.0,
        snow_blight_factor: float = 1.0,
        other_factor: float = 1.0,
    ) -> dict[SaplingSpeciesGroup, float]:
        """Compute proportion of damaged stems per species group.

        Args:
            stems (dict[SaplingSpeciesGroup, float]): Stems per species group (per ha).
            mean_heights (dict[SaplingSpeciesGroup, float]): Mean height per group (m).
            site_index_pine_m (float): Pine site index (m).
            site_index_spruce_m (float): Spruce site index (m).
            latitude_deg (float): Latitude (degrees).
            altitude_m (float): Altitude (m).
            moose_factor (float): Adjustment factor for moose damage.
            vole_factor (float): Adjustment factor for vole damage.
            snow_break_factor (float): Adjustment factor for snow break damage.
            whip_factor (float): Adjustment factor for whipping damage.
            frost_factor (float): Adjustment factor for frost damage.
            snow_blight_factor (float): Adjustment factor for snow blight damage.
            other_factor (float): Adjustment factor for other agents.

        Returns:
            dict[SaplingSpeciesGroup, float]: Proportion damaged per species group.
        """
        total_stems = sum(stems.values())
        if total_stems <= 0.0:
            return {sg: 0.0 for sg in SaplingSpeciesGroup}

        mean_height_pine = mean_heights.get(SaplingSpeciesGroup.PINE, 0.0)
        mean_height_larch = mean_heights.get(SaplingSpeciesGroup.LARCH, 0.0)
        mean_height_spruce = mean_heights.get(SaplingSpeciesGroup.SPRUCE, 0.0)
        mean_height_contorta = mean_heights.get(SaplingSpeciesGroup.CONTORTA, 0.0)
        mean_height_birch = mean_heights.get(SaplingSpeciesGroup.BIRCH, 0.0)
        mean_height_aspen = mean_heights.get(SaplingSpeciesGroup.ASPEN, 0.0)
        mean_height_other_leaf = mean_heights.get(SaplingSpeciesGroup.OTHER_BROADLEAF, 0.0)

        stems_pine = stems.get(SaplingSpeciesGroup.PINE, 0.0)
        stems_larch = stems.get(SaplingSpeciesGroup.LARCH, 0.0)
        stems_spruce = stems.get(SaplingSpeciesGroup.SPRUCE, 0.0)
        stems_contorta = stems.get(SaplingSpeciesGroup.CONTORTA, 0.0)
        stems_birch = stems.get(SaplingSpeciesGroup.BIRCH, 0.0)
        stems_aspen = stems.get(SaplingSpeciesGroup.ASPEN, 0.0)
        stems_other_leaf = stems.get(SaplingSpeciesGroup.OTHER_BROADLEAF, 0.0)

        total_height = (
            stems_pine * mean_height_pine
            + stems_larch * mean_height_larch
            + stems_spruce * mean_height_spruce
            + stems_contorta * mean_height_contorta
            + stems_birch * mean_height_birch
            + stems_aspen * mean_height_aspen
            + stems_other_leaf * mean_height_other_leaf
        )
        total_mean_height = total_height / total_stems if total_stems > 0.0 else 0.0

        stems_pine_larch = stems_pine + stems_larch
        if stems_pine_larch > 0.0:
            mean_height_pine_larch = (
                stems_pine * mean_height_pine + stems_larch * mean_height_larch
            ) / stems_pine_larch
        else:
            mean_height_pine_larch = 0.0

        sum_height_leaf = (
            stems_birch * mean_height_birch
            + stems_aspen * mean_height_aspen
            + stems_other_leaf * mean_height_other_leaf
        )
        leaf_stems = stems_birch + stems_aspen + stems_other_leaf
        mean_height_leaf = sum_height_leaf / leaf_stems if leaf_stems > 0.0 else 0.0

        prop_pine = stems_pine_larch / total_stems
        prop_spruce = stems_spruce / total_stems
        prop_birch = stems_birch / total_stems
        prop_other_leaf = (leaf_stems - stems_birch) / total_stems if total_stems > 0.0 else 0.0

        climate_index = 50.0 * latitude_deg + altitude_m

        pine_damage = _damage_prop_pine_formula(
            mean_height_pine_larch=mean_height_pine_larch,
            prop_pine=prop_pine,
            stems_pine_larch=stems_pine_larch,
            total_stems=total_stems,
            mean_height_leaf=mean_height_leaf,
            total_mean_height=total_mean_height,
            site_index_pine_m=site_index_pine_m,
            climate_index=climate_index,
            moose_factor=moose_factor,
            snow_blight_factor=snow_blight_factor,
            snow_break_factor=snow_break_factor,
            whip_factor=whip_factor,
            other_factor=other_factor,
        )
        spruce_damage = _damage_prop_spruce_formula(
            mean_height_spruce=mean_height_spruce,
            stems_spruce=stems_spruce,
            prop_spruce=prop_spruce,
            sum_height_leaf=sum_height_leaf,
            mean_height_leaf=mean_height_leaf,
            climate_index=climate_index,
            site_index_spruce_m=site_index_spruce_m,
            whip_factor=whip_factor,
            frost_factor=frost_factor,
            other_factor=other_factor,
        )
        contorta_damage = _damage_prop_contorta_formula(
            mean_height_contorta=mean_height_contorta,
            stems_contorta=stems_contorta,
            latitude_deg=latitude_deg,
            moose_factor=moose_factor,
            vole_factor=vole_factor,
            other_factor=other_factor,
        )
        birch_damage = _damage_prop_birch_formula(
            mean_height_birch=mean_height_birch,
            prop_pine=prop_pine,
            prop_birch=prop_birch,
            stems_birch=stems_birch,
            moose_factor=moose_factor,
            other_factor=other_factor,
        )
        aspen_damage = _damage_prop_aspen_formula(
            mean_height_aspen=mean_height_aspen,
            prop_pine=prop_pine,
            prop_other_leaf=prop_other_leaf,
            stems_aspen=stems_aspen,
            total_mean_height=total_mean_height,
            moose_factor=moose_factor,
            other_factor=other_factor,
        )

        return {
            SaplingSpeciesGroup.PINE: pine_damage,
            SaplingSpeciesGroup.SPRUCE: spruce_damage,
            SaplingSpeciesGroup.CONTORTA: contorta_damage,
            SaplingSpeciesGroup.BIRCH: birch_damage,
            SaplingSpeciesGroup.ASPEN: aspen_damage,
        }

    @staticmethod
    def risk_of_damage(
        *,
        species_group: SaplingSpeciesGroup,
        height_m: float,
        moose_factor: float = 1.0,
        vole_factor: float = 1.0,
        snow_break_factor: float = 1.0,
        whip_factor: float = 1.0,
        frost_factor: float = 1.0,
        snow_blight_factor: float = 1.0,
        other_factor: float = 1.0,
    ) -> list[float]:
        """Step 2: Risk of damage per causal agent for a tree.

        Args:
            species_group (SaplingSpeciesGroup): Species group.
            height_m (float): Tree height (m).
            moose_factor (float): Adjustment factor for moose damage.
            vole_factor (float): Adjustment factor for vole damage.
            snow_break_factor (float): Adjustment factor for snow break damage.
            whip_factor (float): Adjustment factor for whipping damage.
            frost_factor (float): Adjustment factor for frost damage.
            snow_blight_factor (float): Adjustment factor for snow blight damage.
            other_factor (float): Adjustment factor for other agents.

        Returns:
            list[float]: Risk values per causal agent (order per Enum).
        """
        if height_m <= 0.0:
            return []
        if species_group in {SaplingSpeciesGroup.PINE, SaplingSpeciesGroup.LARCH}:
            moose_risk = (
                0.01
                if height_m < 0.34 or height_m > 9.6
                else (-0.03 * height_m - 0.11 * log(height_m) - 0.15 / height_m + 0.42)
                * moose_factor
            )
            return [
                max(0.01, moose_risk),
                0.02 * whip_factor,
                0.3 * exp(-2.52 * max(height_m, 0.23)) * snow_blight_factor,
                (0.006 * log(height_m) + 0.009) * snow_break_factor,
                (-0.02 * log(height_m) + 0.09) * other_factor,
            ]
        if species_group == SaplingSpeciesGroup.SPRUCE:
            return [
                0.04 * whip_factor,
                0.08 * exp(-0.5 * height_m) * frost_factor,
                (-0.01 * height_m + 0.19) * other_factor,
            ]
        if species_group == SaplingSpeciesGroup.BIRCH:
            moose_risk = (
                0.01
                if height_m < 0.38
                else (0.02 * height_m - 0.33 * log(height_m) - 0.22 / height_m + 0.45)
                * moose_factor
            )
            return [max(0.01, moose_risk), 0.07 * other_factor]
        if species_group == SaplingSpeciesGroup.ASPEN:
            moose_risk = (
                0.01
                if height_m <= 0.0
                else (0.04 * height_m - 0.31 * log(height_m) - 0.18 / height_m + 0.58)
                * moose_factor
            )
            return [max(0.01, moose_risk), 0.05 * other_factor]
        if species_group == SaplingSpeciesGroup.CONTORTA:
            return [
                max(0.0, (-0.01 * height_m + 0.08) * moose_factor),
                max(0.0, (-0.06 * height_m + 0.26) * vole_factor),
                max(0.0, (-0.06 * height_m + 0.38) * other_factor),
            ]
        return []

    @staticmethod
    def moose_damage_prop_pine(
        *,
        mean_height_pine_larch: float,
        prop_pine: float,
        stems_pine_larch: float,
        total_stems: float,
        mean_height_leaf: float,
        total_mean_height: float,
        site_index_pine_m: float,
        climate_index: float,
        moose_factor: float = 1.0,
    ) -> float:
        """Compute moose damage proportion for pine/larch.

        Args:
            mean_height_pine_larch (float): Mean height for pine + larch (m).
            prop_pine (float): Proportion pine/larch of total stems.
            stems_pine_larch (float): Pine + larch stems per ha.
            total_stems (float): Total stems per ha.
            mean_height_leaf (float): Mean height of broadleaves (m).
            total_mean_height (float): Stand mean height (m).
            site_index_pine_m (float): Pine site index (m).
            climate_index (float): Climate index (50 * latitude + altitude).
            moose_factor (float): Adjustment factor for moose damage.

        Returns:
            float: Moose damage proportion for pine/larch.
        """
        ln_damage = (
            -0.21 * mean_height_pine_larch
            + -1.36 * prop_pine
            + 0.0 * stems_pine_larch
            + 0.0 * total_stems
            + 0.07 * mean_height_leaf
            + 0.0 * total_mean_height
            + 0.0 * site_index_pine_m
            + 0.0 * climate_index
            + -0.58
        )
        return moose_factor * _prop_damage(ln_damage)

    @staticmethod
    def moose_damage_prop_birch(
        *,
        mean_height_birch: float,
        prop_pine: float,
        prop_birch: float,
        stems_birch: float,
        moose_factor: float = 1.0,
    ) -> float:
        """Compute moose damage proportion for birch.

        Args:
            mean_height_birch (float): Mean height of birch (m).
            prop_pine (float): Proportion pine/larch of total stems.
            prop_birch (float): Proportion birch of total stems.
            stems_birch (float): Birch stems per ha.
            moose_factor (float): Adjustment factor for moose damage.

        Returns:
            float: Moose damage proportion for birch.
        """
        ln_damage = (
            -0.38 * mean_height_birch
            + 1.16 * prop_pine
            + 0.0 * prop_birch
            + 0.0 * stems_birch
            + -0.61
        )
        return moose_factor * _prop_damage(ln_damage)

    @staticmethod
    def moose_damage_prop_contorta(
        *,
        mean_height_contorta: float,
        stems_contorta: float,
        latitude_deg: float,
        moose_factor: float = 1.0,
    ) -> float:
        """Compute moose damage proportion for contorta.

        Args:
            mean_height_contorta (float): Mean height of contorta (m).
            stems_contorta (float): Contorta stems per ha.
            latitude_deg (float): Latitude (degrees).
            moose_factor (float): Adjustment factor for moose damage.

        Returns:
            float: Moose damage proportion for contorta.
        """
        ln_damage = 0.0 * mean_height_contorta + 0.0 * stems_contorta + 0.0 * latitude_deg + -2.55
        return moose_factor * _prop_damage(ln_damage)

    @staticmethod
    def damage_degree(
        *,
        species_group: SaplingSpeciesGroup,
        causal_agent: int,
        height_m: float,
        moose_damage_prop: float | None = None,
    ) -> list[float]:
        """Step 4: Damage degree probabilities (minor, severe, dead).

        Args:
            species_group (SaplingSpeciesGroup): Species group.
            causal_agent (int): Causal agent enum value.
            height_m (float): Tree height (m).
            moose_damage_prop (float | None): Moose damage proportion. Required for
                pine/birch when ``causal_agent`` is moose.

        Returns:
            list[float]: Probabilities for [minor, severe, dead].
        """
        height_m = min(6.0, height_m)
        if species_group in {SaplingSpeciesGroup.PINE, SaplingSpeciesGroup.LARCH}:
            return _degree_pine_formula(height_m, causal_agent, moose_damage_prop)
        if species_group == SaplingSpeciesGroup.SPRUCE:
            return _degree_spruce_formula(height_m, causal_agent)
        if species_group == SaplingSpeciesGroup.BIRCH:
            return _degree_birch_formula(height_m, causal_agent, moose_damage_prop)
        if species_group == SaplingSpeciesGroup.CONTORTA:
            return _degree_contorta_formula(height_m, causal_agent)
        if species_group == SaplingSpeciesGroup.ASPEN:
            return _degree_aspen_formula(height_m, causal_agent)
        return [0.0, 0.0, 1.0]

    @staticmethod
    def _damage_prop_pine(
        *,
        mean_height_pine_larch: float,
        prop_pine: float,
        stems_pine_larch: float,
        total_stems: float,
        mean_height_leaf: float,
        total_mean_height: float,
        site_index_pine_m: float,
        climate_index: float,
        moose_factor: float,
        snow_blight_factor: float,
        snow_break_factor: float,
        whip_factor: float,
        other_factor: float,
    ) -> float:
        """Wrapper for pine damage-proportion equation."""
        return _damage_prop_pine_formula(
            mean_height_pine_larch=mean_height_pine_larch,
            prop_pine=prop_pine,
            stems_pine_larch=stems_pine_larch,
            total_stems=total_stems,
            mean_height_leaf=mean_height_leaf,
            total_mean_height=total_mean_height,
            site_index_pine_m=site_index_pine_m,
            climate_index=climate_index,
            moose_factor=moose_factor,
            snow_blight_factor=snow_blight_factor,
            snow_break_factor=snow_break_factor,
            whip_factor=whip_factor,
            other_factor=other_factor,
        )

    @staticmethod
    def _damage_prop_spruce(
        *,
        mean_height_spruce: float,
        stems_spruce: float,
        prop_spruce: float,
        sum_height_leaf: float,
        mean_height_leaf: float,
        climate_index: float,
        site_index_spruce_m: float,
        whip_factor: float,
        frost_factor: float,
        other_factor: float,
    ) -> float:
        """Wrapper for spruce damage-proportion equation."""
        return _damage_prop_spruce_formula(
            mean_height_spruce=mean_height_spruce,
            stems_spruce=stems_spruce,
            prop_spruce=prop_spruce,
            sum_height_leaf=sum_height_leaf,
            mean_height_leaf=mean_height_leaf,
            climate_index=climate_index,
            site_index_spruce_m=site_index_spruce_m,
            whip_factor=whip_factor,
            frost_factor=frost_factor,
            other_factor=other_factor,
        )

    @staticmethod
    def _damage_prop_contorta(
        *,
        mean_height_contorta: float,
        stems_contorta: float,
        latitude_deg: float,
        moose_factor: float,
        vole_factor: float,
        other_factor: float,
    ) -> float:
        """Wrapper for contorta damage-proportion equation."""
        return _damage_prop_contorta_formula(
            mean_height_contorta=mean_height_contorta,
            stems_contorta=stems_contorta,
            latitude_deg=latitude_deg,
            moose_factor=moose_factor,
            vole_factor=vole_factor,
            other_factor=other_factor,
        )

    @staticmethod
    def _damage_prop_birch(
        *,
        mean_height_birch: float,
        prop_pine: float,
        prop_birch: float,
        stems_birch: float,
        moose_factor: float,
        other_factor: float,
    ) -> float:
        """Wrapper for birch damage-proportion equation."""
        return _damage_prop_birch_formula(
            mean_height_birch=mean_height_birch,
            prop_pine=prop_pine,
            prop_birch=prop_birch,
            stems_birch=stems_birch,
            moose_factor=moose_factor,
            other_factor=other_factor,
        )

    @staticmethod
    def _damage_prop_aspen(
        *,
        mean_height_aspen: float,
        prop_pine: float,
        prop_other_leaf: float,
        stems_aspen: float,
        total_mean_height: float,
        moose_factor: float,
        other_factor: float,
    ) -> float:
        """Wrapper for aspen damage-proportion equation."""
        return _damage_prop_aspen_formula(
            mean_height_aspen=mean_height_aspen,
            prop_pine=prop_pine,
            prop_other_leaf=prop_other_leaf,
            stems_aspen=stems_aspen,
            total_mean_height=total_mean_height,
            moose_factor=moose_factor,
            other_factor=other_factor,
        )

    @staticmethod
    def _degree_pine(
        height_m: float, causal_agent: int, moose_damage_prop: float | None
    ) -> list[float]:
        """Wrapper for pine damage-degree probabilities."""
        return _degree_pine_formula(height_m, causal_agent, moose_damage_prop)

    @staticmethod
    def _degree_spruce(height_m: float, causal_agent: int) -> list[float]:
        """Wrapper for spruce damage-degree probabilities."""
        return _degree_spruce_formula(height_m, causal_agent)

    @staticmethod
    def _degree_birch(
        height_m: float, causal_agent: int, moose_damage_prop: float | None
    ) -> list[float]:
        """Wrapper for birch damage-degree probabilities."""
        return _degree_birch_formula(height_m, causal_agent, moose_damage_prop)

    @staticmethod
    def _degree_aspen(height_m: float, causal_agent: int) -> list[float]:
        """Wrapper for aspen damage-degree probabilities."""
        return _degree_aspen_formula(height_m, causal_agent)

    @staticmethod
    def _degree_contorta(height_m: float, causal_agent: int) -> list[float]:
        """Wrapper for contorta damage-degree probabilities."""
        return _degree_contorta_formula(height_m, causal_agent)


__all__ = [
    "SaplingSpeciesGroup",
    "DamageDegree",
    "PineCausalAgent",
    "SpruceCausalAgent",
    "ContortaCausalAgent",
    "BirchCausalAgent",
    "AspenCausalAgent",
    "Naslund1986DamageModel",
]


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------


class _Descriptor:
    """FormulaModuleDescriptor for Naslund (1986) young-stand damage model."""

    @property
    def component_id(self):
        return "naslund_1986_damage"

    @property
    def source(self):
        return SourceReference(
            author="Näslund, B.-Å.",
            year=1986,
            title=(
                "Simulering av skador och avgång i ungskog och deras betydelse för "
                "beståndsutvecklingen"
            ),
            note=(
                "Sveriges lantbruksuniversitet, institutionen för skogsskötsel, "
                "Rapporter nr 18, 147 s. Bert-Åke Näslund; not to be confused with "
                "Manfred Näslund (volume functions, 1947)."
            ),
        )

    @property
    def species_groups(self):
        return {
            "pine": frozenset({"Pinus sylvestris"}),
            "spruce": frozenset({"Picea abies"}),
            "contorta": frozenset({"Pinus contorta"}),
            "birch": frozenset({"Betula pubescens", "Betula pendula"}),
            "aspen": frozenset({"Populus tremula"}),
        }

    @property
    def units(self):
        return {"height_m": "m", "return": "damage proportion"}

    @property
    def kernel_names(self):
        return ["Naslund1986DamageModel"]


DESCRIPTOR = _Descriptor()
