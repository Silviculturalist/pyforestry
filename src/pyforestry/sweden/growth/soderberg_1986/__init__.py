"""Soderberg (1986) single-tree diameter growth equations."""

from __future__ import annotations

from pyforestry.base.contracts import FormulaDescriptor, SourceReference

from .equations import soderberg_1986_tree_diameter_growth_cm

DESCRIPTOR = FormulaDescriptor(
    component_id="soderberg_1986_growth",
    source=SourceReference(
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
    ),
    species_groups={
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
    },
    units={
        "diameter_cm": "cm",
        "age_bh_years": "years",
        "stand_basal_area_m2_ha": "m\u00b2/ha",
        "site_index_pine_m": "m",
        "site_index_spruce_m": "m",
        "altitude_m": "m",
        "latitude_deg": "degrees",
        "return": "cm (5-year diameter increment)",
    },
    kernel_names=("soderberg_1986_tree_diameter_growth_cm",),
)

__all__ = ["DESCRIPTOR", "soderberg_1986_tree_diameter_growth_cm"]
