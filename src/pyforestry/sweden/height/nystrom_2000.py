"""Nyström (2000) sapling height growth model (Table 4, Model M2).

Reference:
    Nyström, K. (2000). Funktioner för att skatta höjdtillväxten i ungskog.
    Arbetsrapport 68. Inst. f skoglig resurshushållning och geomatik, SLU, Umeå.
"""

from __future__ import annotations

from math import exp, log

from pyforestry.base.helpers.primitives import Age, AgeMeasurement
from pyforestry.base.helpers.tree_species import TreeName, TreeSpecies
from pyforestry.simulation.contracts import SourceReference
from pyforestry.sweden.site.enums import Sweden

_PINE_SPECIES = {
    TreeSpecies.Sweden.pinus_sylvestris,
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
_BIRCH_SPECIES = {TreeSpecies.Sweden.betula_pendula, TreeSpecies.Sweden.betula_pubescens}

_RICH_FIELD_LAYERS = {
    Sweden.FieldLayer.HIGH_HERB_WITHOUT_SHRUBS,
    Sweden.FieldLayer.HIGH_HERB_WITH_SHRUBS_BLUEBERRY,
    Sweden.FieldLayer.HIGH_HERB_WITH_SHRUBS_LINGON,
    Sweden.FieldLayer.LOW_HERB_WITHOUT_SHRUBS,
    Sweden.FieldLayer.LOW_HERB_WITH_SHRUBS_BLUEBERRY,
    Sweden.FieldLayer.LOW_HERB_WITH_SHRUBS_LINGON,
    Sweden.FieldLayer.NO_FIELD_LAYER,
    Sweden.FieldLayer.BROADLEAVED_GRASS,
    Sweden.FieldLayer.THINLEAVED_GRASS,
    Sweden.FieldLayer.HORSETAIL,
}
_POOR_FIELD_LAYERS = {
    Sweden.FieldLayer.LINGONBERRY,
    Sweden.FieldLayer.CROWBERRY,
    Sweden.FieldLayer.POOR_SHRUB,
    Sweden.FieldLayer.LICHEN_FREQUENT,
    Sweden.FieldLayer.LICHEN_DOMINANT,
}


def _resolve_age_bh_years(age_bh_years: float | AgeMeasurement) -> float:
    """Validate and normalize age-at-breast-height input to years."""
    if isinstance(age_bh_years, AgeMeasurement):
        if age_bh_years.code != Age.DBH.value:
            raise TypeError("age_bh_years must be a float/int or an AgeMeasurement with Age.DBH.")
        return float(age_bh_years)
    if isinstance(age_bh_years, (float, int)):
        return float(age_bh_years)
    raise TypeError("age_bh_years must be a float/int or an AgeMeasurement with Age.DBH.")


def _resolve_age_total(*, height_m: float, age_bh_val: float) -> float:
    """Resolve total age proxy used by Nyström (2000) regressions."""
    age_val = 1.0 if age_bh_val < 0 else age_bh_val
    return height_m if height_m < 1.3 else 1.3 + age_val


def _field_layer_flags(field_layer: Sweden.FieldLayer | None) -> tuple[int, int]:
    """Return ``(rich, poor)`` vegetation indicators."""
    if field_layer is None:
        return 0, 0
    return int(field_layer in _RICH_FIELD_LAYERS), int(field_layer in _POOR_FIELD_LAYERS)


def _soil_moisture_flags(
    soil_moisture: Sweden.SoilMoistureEnum | None,
) -> tuple[int, int]:
    """Return ``(dry, wet)`` soil-moisture indicators."""
    if soil_moisture is None:
        return 0, 0
    return (
        int(soil_moisture == Sweden.SoilMoistureEnum.DRY),
        int(soil_moisture == Sweden.SoilMoistureEnum.WET),
    )


def _ln_ht_inc_pine(
    *,
    height_m: float,
    mean_height_m: float,
    total_height_sqr_m2_per_100m2: float,
    total_height_sqr_std_m2_per_100m2: float,
    age_total: float,
    temperature_sum: float,
    damage_index: float,
    edge_effect: float,
    edge_effect_alt: float,
    rich: int,
    poor: int,
    dry: int,
    wet: int,
) -> float:
    """Compute log-height increment for pine-group species."""
    return (
        -1.61703510
        + -0.09890405 * height_m
        + 0.74973747 * log(height_m)
        + 0.15139422 * log(1.0 + height_m / mean_height_m)
        + 0.0 * height_m / mean_height_m
        + -0.00015691 * (total_height_sqr_m2_per_100m2) / (mean_height_m**2)
        + -0.37810886 * log(age_total + 8.0)
        + -0.13974062 * damage_index
        + -0.79427916 * edge_effect
        + -0.06467414 * edge_effect_alt
        + -0.00017948 * total_height_sqr_std_m2_per_100m2
        + 0.38994071 * log(temperature_sum)
        + 0.03761598 * rich
        + -0.06217754 * poor
        + -0.06578999 * dry
        + -0.14593780 * wet
    )


def _ln_ht_inc_spruce(
    *,
    height_m: float,
    mean_height_m: float,
    total_height_sqr_m2_per_100m2: float,
    total_height_sqr_std_m2_per_100m2: float,
    age_total: float,
    temperature_sum: float,
    damage_index: float,
    edge_effect: float,
    edge_effect_alt: float,
    rich: int,
    poor: int,
    dry: int,
    wet: int,
) -> float:
    """Compute log-height increment for spruce-group species."""
    return (
        -4.588450376
        + -0.077548344 * height_m
        + 0.782370462 * log(height_m)
        + 2.761515391 * log(1.0 + height_m / mean_height_m)
        + -1.163131649 * height_m / mean_height_m
        + -0.000907114 * (total_height_sqr_m2_per_100m2) / (mean_height_m**2)
        + -0.618976003 * log(age_total + 8.0)
        + -0.285590921 * damage_index
        + -0.791554568 * edge_effect
        + -0.017895983 * edge_effect_alt
        + -0.000208723 * total_height_sqr_std_m2_per_100m2
        + 0.804316077 * log(temperature_sum)
        + 0.055900313 * rich
        + -0.139089705 * poor
        + -0.035249680 * dry
        + -0.027587962 * wet
    )


def _ln_ht_inc_broadleaf(
    *,
    height_m: float,
    mean_height_m: float,
    total_height_sqr_m2_per_100m2: float,
    total_height_sqr_std_m2_per_100m2: float,
    age_total: float,
    temperature_sum: float,
    damage_index: float,
    edge_effect: float,
    edge_effect_alt: float,
    rich: int,
    poor: int,
    dry: int,
    wet: int,
) -> float:
    """Compute log-height increment for broadleaf species."""
    return (
        -6.17429242
        + -0.09966875 * height_m
        + 0.80805605 * log(height_m)
        + 0.24402112 * log(1.0 + height_m / mean_height_m)
        + 0.0 * height_m / mean_height_m
        + 0.0 * (total_height_sqr_m2_per_100m2) / (mean_height_m**2)
        + -0.30652043 * log(age_total + 8.0)
        + -0.45970361 * damage_index
        + -1.37511910 * edge_effect
        + 0.0 * edge_effect_alt
        + -0.00008821 * total_height_sqr_std_m2_per_100m2
        + 0.96221620 * log(temperature_sum)
        + 0.14888969 * rich
        + -0.18520694 * poor
        + -0.07541251 * dry
        + -0.12145890 * wet
    )


def sapling_height_growth_m(
    *,
    height_m: float,
    age_bh_years: float | AgeMeasurement,
    mean_height_m: float,
    total_height_sqr_m2_per_ha: float,
    total_height_sqr_std_m2_per_ha: float,
    temperature_sum: float,
    soil_moisture: Sweden.SoilMoistureEnum | None,
    field_layer: Sweden.FieldLayer | None,
    damage_index: float = 0.0,
    edge_effect: float = 0.0,
    edge_effect_alt: float = 0.0,
    species: TreeName,
    period_years: float = 5.0,
) -> float:
    """Estimate sapling height growth (m) over ``period_years``.

    Source:
        Nyström, K. (2000). Funktioner för att skatta höjdtillväxten i ungskog.
        Arbetsrapport 68. Inst. f skoglig resurshushållning och geomatik, SLU, Umeå.

    Args:
        height_m (float): Current sapling height (m).
        age_bh_years (float | AgeMeasurement): Age at breast height (years).
            If an ``AgeMeasurement`` is provided, it must use ``Age.DBH``.
            Negative numeric ages are treated as 1.0.
        mean_height_m (float): Mean height on plot (m).
        total_height_sqr_m2_per_ha (float): Sum of height^2 (m2/ha).
        total_height_sqr_std_m2_per_ha (float): Sum of height^2 for overstorey (m2/ha).
        temperature_sum (float): Temperature sum (degree-days; Odin 1983).
        soil_moisture (Sweden.SoilMoistureEnum | None): Soil moisture class.
        field_layer (Sweden.FieldLayer | None): Vegetation class used to derive rich/poor flags.
        damage_index (float): Damage indicator term from Nyström (2000); use 0.0 if unknown.
        edge_effect (float): Edge/border indicator term from Nyström (2000); use 0.0 if unknown.
        edge_effect_alt (float): Alternative edge term from Nyström (2000); use 0.0 if unknown.
        species (TreeName): Tree species.
        period_years (float): Growth period in years (default 5.0).

    Returns:
        float: Height growth over the period (m).

    Raises:
        TypeError: If ``age_bh_years`` is not a float/int or ``AgeMeasurement`` with
            ``Age.DBH`` code.

    Notes:
        The original model is calibrated for 5-year increments. Growth is scaled linearly
        when ``period_years`` differs from 5.
        ``damage_index``, ``edge_effect`` and ``edge_effect_alt`` are retained as direct
        compatibility terms for the legacy Nyström (2000) implementation.
    """
    age_bh_val = _resolve_age_bh_years(age_bh_years)
    age_total = _resolve_age_total(height_m=height_m, age_bh_val=age_bh_val)

    total_height_sqr_m2_per_100m2 = total_height_sqr_m2_per_ha / 100.0
    total_height_sqr_std_m2_per_100m2 = total_height_sqr_std_m2_per_ha / 100.0

    rich, poor = _field_layer_flags(field_layer)
    dry, wet = _soil_moisture_flags(soil_moisture)

    if species in _PINE_SPECIES:
        ln_ht_inc = _ln_ht_inc_pine(
            height_m=height_m,
            mean_height_m=mean_height_m,
            total_height_sqr_m2_per_100m2=total_height_sqr_m2_per_100m2,
            total_height_sqr_std_m2_per_100m2=total_height_sqr_std_m2_per_100m2,
            age_total=age_total,
            temperature_sum=temperature_sum,
            damage_index=damage_index,
            edge_effect=edge_effect,
            edge_effect_alt=edge_effect_alt,
            rich=rich,
            poor=poor,
            dry=dry,
            wet=wet,
        )
    elif species in _SPRUCE_SPECIES:
        ln_ht_inc = _ln_ht_inc_spruce(
            height_m=height_m,
            mean_height_m=mean_height_m,
            total_height_sqr_m2_per_100m2=total_height_sqr_m2_per_100m2,
            total_height_sqr_std_m2_per_100m2=total_height_sqr_std_m2_per_100m2,
            age_total=age_total,
            temperature_sum=temperature_sum,
            damage_index=damage_index,
            edge_effect=edge_effect,
            edge_effect_alt=edge_effect_alt,
            rich=rich,
            poor=poor,
            dry=dry,
            wet=wet,
        )
    else:
        ln_ht_inc = _ln_ht_inc_broadleaf(
            height_m=height_m,
            mean_height_m=mean_height_m,
            total_height_sqr_m2_per_100m2=total_height_sqr_m2_per_100m2,
            total_height_sqr_std_m2_per_100m2=total_height_sqr_std_m2_per_100m2,
            age_total=age_total,
            temperature_sum=temperature_sum,
            damage_index=damage_index,
            edge_effect=edge_effect,
            edge_effect_alt=edge_effect_alt,
            rich=rich,
            poor=poor,
            dry=dry,
            wet=wet,
        )

    height_growth_m_5yr = exp(ln_ht_inc)
    if period_years == 5.0:
        return height_growth_m_5yr
    return height_growth_m_5yr * (period_years / 5.0)


__all__ = ["sapling_height_growth_m"]


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------


class _Descriptor:
    """FormulaModuleDescriptor for Nystrom (2000) sapling height growth."""

    @property
    def component_id(self):
        return "nystrom_2000_height"

    @property
    def source(self):
        return SourceReference(
            author="Nyström, K.",
            year=2000,
            title="Funktioner för att skatta höjdtillväxten i ungskog",
            note=(
                "Sveriges lantbruksuniversitet, institutionen för skoglig "
                "resurshushållning och geomatik, Arbetsrapport nr 68, Umeå. "
                "Table 4, Model M2."
            ),
        )

    @property
    def species_groups(self):
        return {"pine": frozenset(), "spruce": frozenset(), "birch": frozenset()}

    @property
    def units(self):
        return {"height_m": "m", "site_index_m": "m", "return": "m"}

    @property
    def kernel_names(self):
        return list(__all__)


DESCRIPTOR = _Descriptor()
