"""Retained-tree mortality overrides after final felling."""

from __future__ import annotations

from collections.abc import Mapping

from pyforestry.base.helpers.tree_species import TreeName

from ._common import clamp_probability, species_key


def retained_tree_mortality_by_species(
    *,
    years_since_final_felling: float | None,
    mortality_year1_5: Mapping[TreeName | str, float],
    mortality_year6_10: Mapping[TreeName | str, float],
) -> dict[str, float] | None:
    """Return retained-tree mortality by species for applicable year windows.

    Source:
        None. This is bookkeeping, not a model: both mortality levels are supplied
        by the caller and the function only selects the window that applies to the
        elapsed time and clamps the result. Whatever science the rates embody
        belongs to whoever produced them.

    Args:
        years_since_final_felling: Years elapsed since final felling.
        mortality_year1_5: Species mortality mapping for years 0-5.
        mortality_year6_10: Species mortality mapping for years 5-10.

    Returns:
        Species mortality mapping keyed by canonical species string, or `None`
        when retained-tree override is not applicable.
    """
    if years_since_final_felling is None:
        return None
    if years_since_final_felling < 0.0 or years_since_final_felling >= 10.0:
        return None

    selected = mortality_year1_5 if years_since_final_felling < 5.0 else mortality_year6_10
    normalized: dict[str, float] = {}
    for raw_species, raw_probability in selected.items():
        key = str(raw_species).strip().lower()
        if key in {"pine", "spruce", "birch", "other"}:
            normalized[key] = clamp_probability(float(raw_probability))
        else:
            normalized[species_key(raw_species)] = clamp_probability(float(raw_probability))
    return normalized


__all__ = ["retained_tree_mortality_by_species"]


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------


class _Descriptor:
    """FormulaModuleDescriptor for retained-tree mortality (Elfving, unpublished)."""

    @property
    def component_id(self):
        """Stable identifier for this formula module."""
        return "retained_trees_mortality"

    @property
    def source(self):
        """Bibliographic provenance for this formula module."""
        from pyforestry.base.contracts import SourceReference

        return SourceReference(
            author="(none)",
            year=0,
            title="Retained-tree mortality window selection",
            note=(
                "No primary publication, and none is needed: the module holds no "
                "coefficients. The caller supplies the year 1-5 and year 6-10 "
                "mortality levels and this selects the applicable window and clamps "
                "to [0, 1]. year=0 is a sentinel for 'not applicable', not a "
                "citation date. It was previously attributed to B. Elfving on a "
                "tentative basis; there is no equation here to attribute."
            ),
        )

    @property
    def species_groups(self):
        """Species groups handled by this module (none)."""
        return {}

    @property
    def units(self):
        """Unit contract for this module (none)."""
        return {}

    @property
    def kernel_names(self):
        """Public kernel function names exposed by this module."""
        return ["retained_tree_mortality_by_species"]


DESCRIPTOR = _Descriptor()
