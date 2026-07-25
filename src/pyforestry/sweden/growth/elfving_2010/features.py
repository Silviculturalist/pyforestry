"""Feature transforms and context resolution for Elfving (2010) growth kernels.

Source:
    Elfving, B. (2010). *Growth modelling in the Heureka system.* Sveriges
    lantbruksuniversitet, Faculty of Forestry, Umeå. Appendix 3.
"""

from __future__ import annotations

import warnings
from typing import Any, Sequence, cast

from pyforestry.base.helpers import Tree, TreeName, TreeSpecies
from pyforestry.base.helpers.primitives import (
    Age,
    AgeMeasurement,
    SiteIndexValue,
    diameter_to_basal_area_cm2,
)
from pyforestry.base.helpers.tree_metrics import basal_area_larger
from pyforestry.base.simulation import SimulationContext
from pyforestry.sweden._model_input_normalization import (
    normalize_hagglund_h100_site_index_m as _normalize_hagglund_h100_site_index_m,
)
from pyforestry.sweden.misc import age_to_breast_height_elfving_years
from pyforestry.sweden.site import Sweden, SwedishSite

PINE_SPECIES = {
    TreeSpecies.Sweden.pinus_sylvestris,
    TreeSpecies.Sweden.pinus_contorta,
    TreeSpecies.Sweden.larix_sibirica,
    TreeSpecies.Sweden.larix_decidua,
    TreeSpecies.Sweden.larix_europaea_x_leptolepis,
    TreeSpecies.Sweden.larix_sukaczewii,
}
SPRUCE_SPECIES = {
    TreeSpecies.Sweden.picea_abies,
    TreeSpecies.Sweden.picea_sitchensis,
    TreeSpecies.Sweden.picea_mariana,
}
BIRCH_SPECIES = {TreeSpecies.Sweden.betula_pendula, TreeSpecies.Sweden.betula_pubescens}
ASPEN_SPECIES = {
    TreeSpecies.Sweden.populus_tremula,
    TreeSpecies.Sweden.populus_tremula_x_tremuloides,
}
BEECH_SPECIES = {TreeSpecies.Sweden.fagus_sylvatica}
OAK_SPECIES = {
    TreeSpecies.Sweden.quercus_robur,
    TreeSpecies.Sweden.quercus_petraea,
    TreeSpecies.Sweden.quercus_rubra,
}
PRECIOUS_SPECIES = {
    TreeSpecies.Sweden.fraxinus_excelsior,
    TreeSpecies.Sweden.ulmus_glabra,
    TreeSpecies.Sweden.tilia_cordata,
    TreeSpecies.Sweden.acer_platanoides,
    TreeSpecies.Sweden.carpinus_betulus,
    TreeSpecies.Sweden.prunus_avium,
}


def species_group(species: TreeName | None) -> str:
    """Classify tree species into Elfving coefficient groups."""
    if species in PINE_SPECIES:
        return "pine"
    if species in SPRUCE_SPECIES:
        return "spruce"
    if species in BIRCH_SPECIES:
        return "birch"
    if species in ASPEN_SPECIES:
        return "aspen"
    if species in BEECH_SPECIES:
        return "beech"
    if species in OAK_SPECIES:
        return "oak"
    if species in PRECIOUS_SPECIES:
        return "precious"
    return "trivial"


def vegetation_flags(field_layer: Sweden.FieldLayer | None) -> tuple[int, int]:
    """Return `(rich, herb)` indicator flags from field layer."""
    if field_layer is None:
        return (0, 0)
    herb = int(
        field_layer
        in {
            Sweden.FieldLayer.HIGH_HERB_WITHOUT_SHRUBS,
            Sweden.FieldLayer.HIGH_HERB_WITH_SHRUBS_BLUEBERRY,
            Sweden.FieldLayer.HIGH_HERB_WITH_SHRUBS_LINGON,
            Sweden.FieldLayer.LOW_HERB_WITHOUT_SHRUBS,
            Sweden.FieldLayer.LOW_HERB_WITH_SHRUBS_BLUEBERRY,
            Sweden.FieldLayer.LOW_HERB_WITH_SHRUBS_LINGON,
        }
    )
    rich = int(
        field_layer
        in {
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
    )
    return (rich, herb)


def distance_to_coast_km(site: SwedishSite | None, ctx: SimulationContext) -> float:
    """Resolve distance to coast in km, with a default when unavailable."""
    if site is not None and site.distance_to_coast is not None:
        return float(site.distance_to_coast)
    val = ctx.attrs.get("distance_to_coast_km")
    if val is not None:
        return float(val)
    # Default 50 km (Ak=5) when distance to coast is unavailable.
    return 50.0


def resolve_temperature_sum(site: SwedishSite | None, ctx: SimulationContext) -> float:
    """Resolve annual temperature sum (degree-days)."""
    if site is not None and site.temperature_sum_odin1983 is not None:
        return float(site.temperature_sum_odin1983)
    for key in ("temperature_sum_dd", "temperature_sum", "temperature_sum_odin1983"):
        if key in ctx.attrs and ctx.attrs[key] is not None:
            return float(ctx.attrs[key])
    raise ValueError("Temperature sum is required for Elfving growth.")


def resolve_site_index_m(
    *,
    site: SwedishSite | None,
    ctx: SimulationContext,
    pine_ba: float | None = None,
    spruce_ba: float | None = None,
) -> float:
    """Resolve stand-level site index (m)."""
    allowed_h100_species = {
        TreeSpecies.Sweden.picea_abies,
        TreeSpecies.Sweden.pinus_sylvestris,
    }

    def _to_site_index_m(value: object, *, parameter_name: str) -> float:
        """To site index m.

        Args:
            value: Parameter for `resolve_site_index_m._to_site_index_m`.
            parameter_name: Parameter for `resolve_site_index_m._to_site_index_m`.

        Returns:
            Result produced by this callable.

        Source:
            Forestry equation implementation within pyforestry formulas modules
            and referenced scientific literature used by this package.
        """
        normalized_value: float | SiteIndexValue
        if isinstance(value, (SiteIndexValue, float, int)):
            normalized_value = value
        elif hasattr(value, "value"):
            value_attr = cast(Any, value).value
            if not isinstance(value_attr, (SiteIndexValue, float, int)):
                raise TypeError(
                    f"{parameter_name}.value must be numeric or SiteIndexValue; "
                    f"received {type(value_attr)}."
                )
            normalized_value = value_attr
        else:
            raise TypeError(
                f"{parameter_name} must be numeric or SiteIndexValue; received {type(value)}."
            )
        return _normalize_hagglund_h100_site_index_m(
            normalized_value,
            parameter_name=parameter_name,
            allowed_species=allowed_h100_species,
        )

    for key in ("site_index_m", "site_index"):
        if key in ctx.attrs and ctx.attrs[key] is not None:
            return _to_site_index_m(ctx.attrs[key], parameter_name=key)
    if "site_index_value" in ctx.attrs and ctx.attrs["site_index_value"] is not None:
        return _to_site_index_m(ctx.attrs["site_index_value"], parameter_name="site_index_value")

    if site is None:
        raise ValueError("Site index is required (no SwedishSite and no ctx.attrs).")

    dominant_species = ctx.attrs.get("dominant_species")
    if isinstance(dominant_species, TreeName):
        if dominant_species in SPRUCE_SPECIES and site.sis_spruce_100 is not None:
            return float(site.sis_spruce_100)
        if dominant_species in PINE_SPECIES and site.sis_pine_100 is not None:
            return float(site.sis_pine_100)

    if pine_ba is not None and spruce_ba is not None:
        if spruce_ba >= pine_ba and site.sis_spruce_100 is not None:
            return float(site.sis_spruce_100)
        if pine_ba > spruce_ba and site.sis_pine_100 is not None:
            return float(site.sis_pine_100)

    if site.sis_spruce_100 is not None:
        return float(site.sis_spruce_100)
    if site.sis_pine_100 is not None:
        return float(site.sis_pine_100)

    raise ValueError("Unable to resolve site index from SwedishSite.")


def resolve_latitude_altitude(
    site: SwedishSite | None,
    ctx: SimulationContext,
) -> tuple[float, float]:
    """Resolve latitude (deg) and altitude (m)."""
    if site is not None and site.latitude is not None and site.altitude is not None:
        return float(site.latitude), float(site.altitude)
    lat = ctx.attrs.get("latitude_deg")
    alt = ctx.attrs.get("altitude_m")
    if lat is None or alt is None:
        raise ValueError("latitude_deg and altitude_m are required for Elfving growth.")
    return float(lat), float(alt)


def fertilization_flag(ctx: SimulationContext) -> int:
    """Return fertilization indicator expected by Elfving equations."""
    if ctx.attrs.get("fertilized_within_10_years") is True:
        return 1
    years_left = ctx.attrs.get("fertilized_remaining_years")
    if years_left is not None and float(years_left) > 0.0:
        return 1
    return 0


def thinning_flags(
    ctx: SimulationContext,
    include_thinning_effect: bool,
) -> tuple[int, int]:
    """Return `(thinned_0_10_years_flag, thinned_10_30_years_flag)` thinning indicators."""
    if include_thinning_effect and ctx.attrs.get("thinning_simulated") is True:
        return (0, 0)
    thinned_0_10_years_flag = int(bool(ctx.attrs.get("thinned_0_10_years", False)))
    thinned_10_30_years_flag = int(
        bool(
            ctx.attrs.get(
                "thinned_11_30_years",
                ctx.attrs.get("thinned_11_25_years", False),
            )
        )
    )
    return (thinned_0_10_years_flag, thinned_10_30_years_flag)


def split_edge_flags(ctx: SimulationContext) -> tuple[int, int]:
    """Return `(split, edge)` plot indicators."""
    split = int(bool(ctx.attrs.get("is_split_plot", ctx.attrs.get("split", False))))
    edge = int(bool(ctx.attrs.get("is_edge_plot", ctx.attrs.get("edge", False))))
    return (split, edge)


def field_estimated_basal_area_m2_ha(ctx: SimulationContext) -> float | None:
    """Resolve field-estimated surrounding basal area in m²/ha."""
    val = ctx.attrs.get("field_estimated_basal_area_m2_ha")
    return None if val is None else float(val)


def tree_age_bh_years(
    *,
    tree: Tree,
    site_index_m: float,
    latitude_deg: float,
    default_species: TreeName,
) -> float:
    """Resolve age at breast height in years."""
    age_val = tree.age
    species = tree.species or default_species
    if isinstance(age_val, AgeMeasurement):
        if age_val.code == Age.DBH.value:
            return float(age_val)
        if age_val.code == Age.TOTAL.value:
            t13 = age_to_breast_height_elfving_years(
                site_index_m=site_index_m,
                latitude_deg=latitude_deg,
                species=species,
            )
            return max(1.0, float(age_val) - t13)
    if isinstance(age_val, (float, int)):
        # Assume DBH when no measurement type is provided.
        return float(age_val)
    warnings.warn("Tree age missing; using 10 years as fallback.", stacklevel=2)
    return 10.0


def tree_age_total_years(
    *,
    tree: Tree,
    site_index_m: float,
    latitude_deg: float,
    default_species: TreeName,
) -> float:
    """Resolve total age in years for stand-level averages."""
    age_val = tree.age
    species = tree.species or default_species
    if isinstance(age_val, AgeMeasurement):
        if age_val.code == Age.TOTAL.value:
            return float(age_val)
        if age_val.code == Age.DBH.value:
            t13 = age_to_breast_height_elfving_years(
                site_index_m=site_index_m,
                latitude_deg=latitude_deg,
                species=species,
            )
            return float(age_val) + t13
    if isinstance(age_val, (float, int)):
        t13 = age_to_breast_height_elfving_years(
            site_index_m=site_index_m,
            latitude_deg=latitude_deg,
            species=species,
        )
        return float(age_val) + t13
    warnings.warn("Tree age missing; using 10 years as fallback.", stacklevel=2)
    return 10.0


def plot_expansion_factor(plot_area_ha: float, occlusion: float) -> float:
    """Convert plot area/occlusion into expansion factor."""
    denom = plot_area_ha * (1.0 - occlusion)
    if denom <= 0:
        raise ValueError("Plot area must be positive for expansion.")
    return 1.0 / denom


def collect_trees(ctx: SimulationContext) -> list[Tree]:
    """Return all trees from tree-list compatible simulation contexts."""
    if ctx.mode not in ("tree_list", "spatial"):
        return []
    return [tree for plot in ctx.plots for tree in plot.trees]


def compute_bawad_cm(trees: Sequence[Tree], expansions: Sequence[float]) -> float:
    """Compute BA-weighted diameter (D3/D2) in cm."""
    d2_sum = 0.0
    d3_sum = 0.0
    for tree, exp_factor in zip(trees, expansions, strict=False):
        d = float(getattr(tree, "diameter_cm", 0.0) or 0.0)
        if d <= 0:
            continue
        w = float(getattr(tree, "weight_n", 1.0) or 1.0)
        d2 = d**2
        d3 = d**3
        d2_sum += d2 * w * exp_factor
        d3_sum += d3 * w * exp_factor
    return d3_sum / d2_sum if d2_sum > 0 else 0.0


def compute_bal_by_tree(
    trees: Sequence[Tree],
    expansions: Sequence[float],
) -> dict[int, float]:
    """Compute basal area of larger trees (BAL) in m²/ha per tree."""
    sizes: list[float] = []
    basal_areas: list[float] = []
    for tree, exp_factor in zip(trees, expansions, strict=False):
        d = float(getattr(tree, "diameter_cm", 0.0) or 0.0)
        w = float(getattr(tree, "weight_n", 1.0) or 1.0)
        ba_cm2 = diameter_to_basal_area_cm2(d)
        sizes.append(d)
        basal_areas.append(ba_cm2 * 1.0e-4 * w * exp_factor)

    bal_list = basal_area_larger(sizes, basal_areas)
    return dict(enumerate(bal_list))


def mean_age_total(
    trees: Sequence[Tree],
    expansions: Sequence[float],
    site_index_m: float,
    latitude_deg: float,
) -> float:
    """Compute basal-area weighted mean total age."""
    sum_age = 0.0
    sum_ba = 0.0
    for tree, exp_factor in zip(trees, expansions, strict=False):
        d = float(getattr(tree, "diameter_cm", 0.0) or 0.0)
        if d <= 0:
            continue
        age_total = tree_age_total_years(
            tree=tree,
            site_index_m=site_index_m,
            latitude_deg=latitude_deg,
            default_species=TreeSpecies.Sweden.pinus_sylvestris,
        )
        ba = (
            diameter_to_basal_area_cm2(d)
            * 1.0e-4
            * float(getattr(tree, "weight_n", 1.0) or 1.0)
            * exp_factor
        )
        sum_age += ba * age_total
        sum_ba += ba
    return sum_age / sum_ba if sum_ba > 0 else 0.0


__all__ = [
    "ASPEN_SPECIES",
    "BEECH_SPECIES",
    "BIRCH_SPECIES",
    "OAK_SPECIES",
    "PINE_SPECIES",
    "PRECIOUS_SPECIES",
    "SPRUCE_SPECIES",
    "collect_trees",
    "compute_bal_by_tree",
    "compute_bawad_cm",
    "distance_to_coast_km",
    "fertilization_flag",
    "field_estimated_basal_area_m2_ha",
    "mean_age_total",
    "plot_expansion_factor",
    "resolve_latitude_altitude",
    "resolve_site_index_m",
    "resolve_temperature_sum",
    "species_group",
    "split_edge_flags",
    "thinning_flags",
    "tree_age_bh_years",
    "tree_age_total_years",
    "vegetation_flags",
]
