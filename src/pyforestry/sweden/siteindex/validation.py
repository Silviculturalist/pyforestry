"""Validation helpers for H100 site-index metadata.

These checks enforce that model-facing ``SiteIndexValue`` inputs are:
- H100 values (reference age 100),
- tagged with exactly one expected species,
- derived from the Hagglund (1970) height trajectory family.
"""

from __future__ import annotations

from collections.abc import Set

from pyforestry.base.helpers.primitives import Age, SiteIndexValue
from pyforestry.base.helpers.tree_species import TreeName

_HAGGLUND_1970_SOURCE_MARKERS: tuple[str, ...] = (
    "hagglund_1970",
    "Hagglund_1970",
    "HagglundSpruceModel",
    "HagglundPineModel",
    "height_trajectory",
)


def _species_display_name(species: TreeName) -> str:
    """Return a stable, human-readable species label for errors."""
    return getattr(species, "full_name", repr(species))


def _validate_species_set(
    site_index_value: SiteIndexValue,
    *,
    param_name: str,
) -> TreeName:
    """Validate and return the single species encoded in ``SiteIndexValue``."""
    if not isinstance(site_index_value.species, set) or not site_index_value.species:
        raise TypeError(f"{param_name}.species must be a non-empty set of TreeName.")
    if len(site_index_value.species) != 1:
        raise ValueError(
            f"{param_name}.species must contain exactly one species; "
            f"received {site_index_value.species}."
        )
    species = next(iter(site_index_value.species))
    if not isinstance(species, TreeName):
        raise TypeError(
            f"{param_name}.species must contain TreeName objects; received {type(species)}."
        )
    return species


def validate_hagglund_1970_h100_site_index(
    site_index_value: SiteIndexValue,
    *,
    param_name: str = "site_index_value",
    expected_species: TreeName | None = None,
    allowed_species: Set[TreeName] | None = None,
) -> TreeName:
    """Validate that a site-index value is a Hagglund (1970) H100 input.

    Args:
        site_index_value (SiteIndexValue): Site-index value to validate.
        param_name (str): Input name used in error messages.
        expected_species (TreeName | None): Require an exact species match when set.
        allowed_species (set[TreeName] | None): Require species membership when set.

    Returns:
        TreeName: The validated single species encoded in ``site_index_value``.
    """
    if not isinstance(site_index_value, SiteIndexValue):
        raise TypeError(f"{param_name} must be a SiteIndexValue instance.")
    if site_index_value.reference_age != Age.TOTAL(100):
        raise ValueError(
            f"{param_name} must have reference_age Age.TOTAL(100) (H100). "
            f"Received {site_index_value.reference_age}."
        )

    site_index_species = _validate_species_set(site_index_value, param_name=param_name)

    if expected_species is not None:
        if not isinstance(expected_species, TreeName):
            raise TypeError("expected_species must be a TreeName instance.")
        if site_index_species != expected_species:
            raise ValueError(
                f"{param_name}.species must match {_species_display_name(expected_species)}; "
                f"received {_species_display_name(site_index_species)}."
            )

    if allowed_species is not None and site_index_species not in allowed_species:
        allowed_names = ", ".join(
            sorted(_species_display_name(species) for species in allowed_species)
        )
        raise ValueError(
            f"{param_name}.species must be one of {{{allowed_names}}}; "
            f"received {_species_display_name(site_index_species)}."
        )

    fn_module = getattr(site_index_value.fn, "__module__", "")
    fn_qualname = getattr(site_index_value.fn, "__qualname__", "")
    if not any(
        marker in fn_module or marker in fn_qualname for marker in _HAGGLUND_1970_SOURCE_MARKERS
    ):
        raise ValueError(
            f"{param_name}.fn does not appear to be a Hagglund 1970 site index function. "
            f"fn={fn_qualname}"
        )

    return site_index_species


__all__ = ["validate_hagglund_1970_h100_site_index"]
