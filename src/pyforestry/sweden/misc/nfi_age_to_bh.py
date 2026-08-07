"""Age-to-breast-height and dominant mean diameter helpers for Sweden.

These helpers reproduce the Elfving (2009) NFI smoothing for
time-to-breast-height (T13) and the dominant mean diameter (Dm) regression.
"""

from __future__ import annotations

import warnings
from math import exp, log

from pyforestry.base.helpers.primitives import SiteIndexValue
from pyforestry.base.helpers.tree_species import TreeName, TreeSpecies
from pyforestry.sweden._model_input_normalization import (
    normalize_hagglund_h100_site_index_m as _normalize_hagglund_h100_site_index_m,
)

_PINE_SPECIES = {
    TreeSpecies.Sweden.pinus_sylvestris,
    TreeSpecies.Sweden.pinus_contorta,
}
_LARCH_SPECIES = {
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
_ASPEN_SPECIES = {
    TreeSpecies.Sweden.populus_tremula,
    TreeSpecies.Sweden.populus_tremula_x_tremuloides,
}
_BEECH_SPECIES = {TreeSpecies.Sweden.fagus_sylvatica}
_OAK_SPECIES = {
    TreeSpecies.Sweden.quercus_robur,
    TreeSpecies.Sweden.quercus_petraea,
    TreeSpecies.Sweden.quercus_rubra,
}
_PRECIOUS_SPECIES = {
    TreeSpecies.Sweden.fraxinus_excelsior,
    TreeSpecies.Sweden.ulmus_glabra,
    TreeSpecies.Sweden.tilia_cordata,
    TreeSpecies.Sweden.acer_platanoides,
    TreeSpecies.Sweden.carpinus_betulus,
    TreeSpecies.Sweden.prunus_avium,
}


def age_to_breast_height_elfving_years(
    *,
    site_index_m: float | SiteIndexValue,
    latitude_deg: float,
    species: TreeName,
) -> float:
    """Estimate time to reach breast height (T13) in years.

    Source:
        Elfving (2009) NFI smoothing:
        T13 = 37 – 0.605*LAT – 1121/SIS + 21.92*LAT/SIS + 29.5*ISSPRUCE/SIS

    Args:
        site_index_m (float | SiteIndexValue): Site index (m), typically SIS.
            ``SiteIndexValue`` inputs must be Hagglund (1970) pine/spruce H100.
        latitude_deg (float): Latitude in degrees (N).
        species (TreeName): Tree species.

    Returns:
        float: Years to reach breast height (T13).

    Raises:
        ValueError: If ``site_index_m`` is non-positive.
    """
    site_index_value_m = _normalize_hagglund_h100_site_index_m(
        site_index_m,
        parameter_name="site_index_m",
        allowed_species={
            TreeSpecies.Sweden.pinus_sylvestris,
            TreeSpecies.Sweden.picea_abies,
        },
    )

    if site_index_value_m <= 0:
        raise ValueError("site_index_m must be positive.")

    is_spruce = int(species in _SPRUCE_SPECIES)
    is_contorta = species is TreeSpecies.Sweden.pinus_contorta
    is_broadleaf = (
        species in _BIRCH_SPECIES
        or species in _ASPEN_SPECIES
        or species in _BEECH_SPECIES
        or species in _OAK_SPECIES
        or species in _PRECIOUS_SPECIES
    )

    if is_broadleaf:
        return 150.0 / site_index_value_m

    site_index_adjusted_m = site_index_value_m + 3.0 if is_contorta else site_index_value_m
    return (
        37.0
        - 0.605 * latitude_deg
        - 1121.0 / site_index_adjusted_m
        + 21.92 * latitude_deg / site_index_adjusted_m
        + 29.5 * is_spruce / site_index_adjusted_m
    )


def dominant_mean_diameter_cm(
    *,
    mean_age_total_years: float,
    field_estimated_basal_area_m2_ha: float,
    site_index_m: float,
) -> float:
    """Compute dominant mean diameter (Dm) in centimeters.

    Source:
        Dominant mean-diameter regression (Lind 2003 / Elfving 2003).

    Args:
        mean_age_total_years (float): Basal-area weighted mean total age (years).
        field_estimated_basal_area_m2_ha (float): Field-estimated basal area (m2/ha).
        site_index_m (float): Site index (m).

    Returns:
        float: Dominant mean diameter (cm). Returns 0.0 when inputs are invalid.
    """
    if mean_age_total_years <= 0 or field_estimated_basal_area_m2_ha <= 0 or site_index_m <= 0:
        warnings.warn(
            "dominant_mean_diameter_cm requires positive age, basal area, and site index.",
            stacklevel=2,
        )
        return 0.0

    dom_mean_bias = 0.036
    return exp(
        -0.92313
        + 1.00322 * log(mean_age_total_years)
        + -0.00701 * mean_age_total_years
        + -4.00529 * (1.0 / site_index_m)
        + 0.01859 * site_index_m
        + -1.88177 * (1.0 / (1.0 + field_estimated_basal_area_m2_ha))
        + dom_mean_bias
    )


__all__ = [
    "age_to_breast_height_elfving_years",
    "dominant_mean_diameter_cm",
]
