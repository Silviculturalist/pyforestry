"""Shared input normalization helpers for Swedish model modules.

This module centralizes recurring parsing/normalization patterns used across
equation-oriented model files, while keeping model-specific policy decisions in
the callers.
"""

from __future__ import annotations

import warnings
from typing import Union

from pyforestry.base.helpers.primitives import SiteIndexValue
from pyforestry.base.helpers.tree_species import TreeName, TreeSpecies, parse_tree_species
from pyforestry.sweden.siteindex.validation import validate_hagglund_1970_h100_site_index

PINE_GROUP = {
    TreeSpecies.Sweden.pinus_sylvestris,
    TreeSpecies.Sweden.pinus_contorta,
    TreeSpecies.Sweden.pinus_mugo,
    TreeSpecies.Sweden.larix_sibirica,
    TreeSpecies.Sweden.larix_decidua,
    TreeSpecies.Sweden.larix_europaea_x_leptolepis,
    TreeSpecies.Sweden.larix_sukaczewii,
}
SPRUCE_GROUP = {
    TreeSpecies.Sweden.picea_abies,
    TreeSpecies.Sweden.picea_sitchensis,
    TreeSpecies.Sweden.picea_mariana,
}
BIRCH_GROUP = {TreeSpecies.Sweden.betula_pendula, TreeSpecies.Sweden.betula_pubescens}
BEECH_GROUP = {TreeSpecies.Sweden.fagus_sylvatica}
OAK_GROUP = {
    TreeSpecies.Sweden.quercus_robur,
    TreeSpecies.Sweden.quercus_petraea,
    TreeSpecies.Sweden.quercus_rubra,
}


def coerce_species(species: Union[TreeName, str]) -> TreeName:
    """Parse species input into a canonical ``TreeName``."""
    return parse_tree_species(species)


def species_group_for_soderberg(species: TreeName, *, model_name: str) -> str:
    """Resolve Söderberg species group for bark/height/form-height equations."""
    if species in PINE_GROUP:
        return "pine"
    if species in SPRUCE_GROUP:
        return "spruce"
    if species in BIRCH_GROUP:
        return "birch"
    if species in BEECH_GROUP:
        return "beech"
    if species in OAK_GROUP:
        return "oak"
    if species.tree_type == "Deciduous":
        return "other"
    raise ValueError(f"Unsupported species for {model_name}: {species.full_name}")


def normalize_part_of_sweden(
    part_of_sweden: str,
    *,
    allow_gotland: bool = False,
    gotland_alias: str | None = None,
    gotland_warning: str | None = None,
    error_message: str = "part_of_sweden must be one of: north, middle, south.",
) -> str:
    """Normalize Sweden-region labels with model-specific Gotland policy."""
    part = part_of_sweden.strip().lower()
    if part in {"north", "northern"}:
        return "north"
    if part in {"middle", "central"}:
        return "middle"
    if part in {"south", "southern"}:
        return "south"
    if part == "gotland":
        if allow_gotland:
            return "gotland"
        if gotland_alias is not None:
            if gotland_warning is not None:
                warnings.warn(gotland_warning, stacklevel=2)
            return gotland_alias
    raise ValueError(error_message)


def warn_proportion(name: str, value: float) -> None:
    """Warn when a proportion is outside [0, 1]."""
    if not (0.0 <= value <= 1.0):
        warnings.warn(
            f"{name}={value} is outside [0, 1]; results may be extrapolated.",
            stacklevel=2,
        )


def normalize_hagglund_h100_site_index_m(
    site_index_input: float | SiteIndexValue,
    *,
    parameter_name: str,
    expected_species: TreeName | None = None,
    allowed_species: set[TreeName] | None = None,
) -> float:
    """Normalize a site index input to meters with optional Hagglund checks.

    Numeric values are passed through as ``float``. ``SiteIndexValue`` inputs
    are validated as Hagglund (1970) H100 values before conversion.
    """
    if isinstance(site_index_input, SiteIndexValue):
        validate_hagglund_1970_h100_site_index(
            site_index_input,
            param_name=parameter_name,
            expected_species=expected_species,
            allowed_species=allowed_species,
        )
        return float(site_index_input)
    return float(site_index_input)


__all__ = [
    "PINE_GROUP",
    "SPRUCE_GROUP",
    "BIRCH_GROUP",
    "BEECH_GROUP",
    "OAK_GROUP",
    "coerce_species",
    "species_group_for_soderberg",
    "normalize_part_of_sweden",
    "warn_proportion",
    "normalize_hagglund_h100_site_index_m",
]
