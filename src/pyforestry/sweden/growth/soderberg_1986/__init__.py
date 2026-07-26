"""Soderberg (1986) single-tree diameter growth equations."""

from __future__ import annotations

from typing import Mapping, Sequence

from pyforestry.base.contracts import FormulaModuleDescriptor

from .equations import soderberg_1986_tree_diameter_growth_cm


class _Soderberg1986GrowthDescriptor:
    """Introspection metadata for the Soderberg 1986 growth equation module."""

    @property
    def component_id(self) -> str:
        """Stable identifier for this formula module."""
        return "soderberg_1986_growth"

    @property
    def source(self) -> "SourceReference":  # noqa: F821
        """Bibliographic provenance."""
        from pyforestry.base.contracts import SourceReference

        return SourceReference(
            author="Söderberg, U.",
            year=1986,
            title=(
                "Funktioner för skogliga produktionsprognoser: tillväxt och formhöjd "
                "för enskilda träd av inhemska trädslag i Sverige"
            ),
            note=(
                "Sveriges lantbruksuniversitet, institutionen för biometri och "
                "skogsindelning, Rapport nr 14, Umeå, 251 s. ISBN 91-576-2634-0."
            ),
        )

    @property
    def species_groups(self) -> Mapping[str, frozenset[str]]:
        """Species groups and their constituent species identifiers."""
        return {
            "pine": frozenset(),
            "spruce": frozenset(),
            "birch": frozenset(),
            "aspen": frozenset(),
            "oak": frozenset(),
            "beech": frozenset(),
            "southern_broadleaf": frozenset(),
            "contorta": frozenset(),
            "other_broadleaf": frozenset(),
            "larch": frozenset(),
        }

    @property
    def units(self) -> Mapping[str, str]:
        """Unit contract for equation parameters and outputs."""
        return {
            "diameter_cm": "cm",
            "age_bh_years": "years",
            "stand_basal_area_m2_ha": "m\u00b2/ha",
            "site_index_pine_m": "m",
            "site_index_spruce_m": "m",
            "altitude_m": "m",
            "latitude_deg": "degrees",
            "return": "cm (5-year diameter increment)",
        }

    @property
    def kernel_names(self) -> Sequence[str]:
        """Public function names exposed by this formula module."""
        return ["soderberg_1986_tree_diameter_growth_cm"]


DESCRIPTOR: FormulaModuleDescriptor = _Soderberg1986GrowthDescriptor()

__all__ = ["DESCRIPTOR", "soderberg_1986_tree_diameter_growth_cm"]
