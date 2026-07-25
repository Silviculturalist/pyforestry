"""Vestjordet (1967) spruce tree-volume equations for Norway."""

from __future__ import annotations

import warnings
from typing import Optional, Union

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers.primitives import AtomicVolume, Diameter_cm
from pyforestry.base.helpers.tree_species import TreeName, TreeSpecies, parse_tree_species
from pyforestry.norway.bark.hansen_2023 import (
    hansen_2023_birch_norway_bark_thickness,
    hansen_2023_norway_spruce_norway_bark_thickness,
    hansen_2023_scots_pine_norway_bark_thickness,
)


def _norway_m3sk_dm3(value_dm3: float, species_full_name: str) -> AtomicVolume:
    """Create a Norway m3sk volume from dm3."""
    return AtomicVolume.from_unit(
        max(0.0, value_dm3),
        "dm3",
        region="Norway",
        species=species_full_name,
        type="m3sk",
    )


def vestjordet_1967_volume_norway_spruce_norway(
    height_m: float,
    diameter_cm: Union[Diameter_cm, float],
    bark_thickness_cm: Optional[float] = None,
    with_bark: bool = True,
) -> AtomicVolume:
    """Return Norway spruce tree volume (`m3sk`) for Norway."""
    if isinstance(diameter_cm, Diameter_cm):
        if diameter_cm.measurement_height_m != 1.3:
            warnings.warn(
                (
                    "Input 'diameter_cm' (Diameter_cm) uses measurement height "
                    f"{diameter_cm.measurement_height_m} m; model assumes 1.3 m."
                ),
                stacklevel=2,
            )
        if not diameter_cm.over_bark:
            raise ValueError("Input 'diameter_cm' must be measured over bark.")
        diam_ob_cm = float(diameter_cm)
    elif isinstance(diameter_cm, (float, int)):
        diam_ob_cm = float(diameter_cm)
    else:
        raise TypeError("Input 'diameter_cm' must be a float, int, or Diameter_cm.")

    if diam_ob_cm < 0:
        raise ValueError("Input 'diameter_cm' must be non-negative.")
    if height_m < 1.3:
        raise ValueError("Input 'height_m' must be >= 1.3 meters.")

    diam_eff_cm = diam_ob_cm
    if not with_bark:
        if bark_thickness_cm is None:
            bark_thickness_cm = hansen_2023_norway_spruce_norway_bark_thickness(
                diam_ob_cm,
                diam_ob_cm,
            )
        if not isinstance(bark_thickness_cm, (float, int)):
            raise TypeError("Input 'bark_thickness_cm' must be a float or int.")
        if bark_thickness_cm < 0:
            raise ValueError("Input 'bark_thickness_cm' must be non-negative.")
        diam_eff_cm = diam_ob_cm - float(bark_thickness_cm)
        if diam_eff_cm < 0:
            return _norway_m3sk_dm3(0.0, TreeSpecies.Norway.picea_abies.full_name)

    if diam_ob_cm <= 0.0 or diam_eff_cm <= 0.0:
        return _norway_m3sk_dm3(0.0, TreeSpecies.Norway.picea_abies.full_name)

    d2 = diam_eff_cm * diam_eff_cm
    h2 = height_m * height_m
    if diam_ob_cm <= 10.0:
        volume_dm3 = (
            0.52
            + 0.02403 * d2 * height_m
            + 0.01463 * diam_eff_cm * h2
            - 0.10983 * h2
            + 0.15195 * diam_eff_cm * height_m
        )
    elif diam_ob_cm < 13.0:
        volume_dm3 = (
            -31.57
            + 0.0016 * diam_eff_cm * h2
            + 0.0186 * h2
            + 0.63 * diam_eff_cm * height_m
            - 2.34 * height_m
            + 3.20 * diam_eff_cm
        )
    else:
        volume_dm3 = (
            10.14
            + 0.01240 * d2 * height_m
            + 0.03117 * diam_eff_cm * h2
            - 0.36381 * h2
            + 0.28578 * diam_eff_cm * height_m
        )
    return _norway_m3sk_dm3(volume_dm3, TreeSpecies.Norway.picea_abies.full_name)


def vestjordet_1967_volume_tree_top(
    species: Union[TreeName, str],
    diameter_cm: Union[Diameter_cm, float],
    height_m: float,
    over_bark: bool = True,
) -> AtomicVolume:
    """Return treetop volume (`m3sk`) for Norway based on Vestjordet (1967)."""
    tree_species = parse_tree_species(species)

    if isinstance(diameter_cm, Diameter_cm):
        if diameter_cm.over_bark != over_bark:
            raise ValueError(
                (
                    f"Mismatch: over_bark={over_bark}, but Diameter_cm.over_bark="
                    f"{diameter_cm.over_bark}."
                )
            )
        if diameter_cm.measurement_height_m != 1.3:
            warnings.warn(
                (
                    "Input 'diameter_cm' (Diameter_cm) uses measurement height "
                    f"{diameter_cm.measurement_height_m} m; model assumes 1.3 m."
                ),
                stacklevel=2,
            )
        d_cm = float(diameter_cm)
    elif isinstance(diameter_cm, (float, int)):
        d_cm = float(diameter_cm)
    else:
        raise TypeError("Input 'diameter_cm' must be a float, int, or Diameter_cm.")

    if d_cm < 0:
        raise ValueError("Input 'diameter_cm' must be non-negative.")
    if height_m < 0:
        raise ValueError("Input 'height_m' must be non-negative.")

    d2 = d_cm * d_cm
    is_spruce = tree_species == TreeSpecies.Norway.picea_abies
    if is_spruce:
        top_dm3 = 9.50 - 0.41 * d_cm + 0.0049 * d2 + 0.11 * height_m
        if not over_bark:
            top_dm3 = 8.04 - 0.39 * d_cm + 0.0048 * d2 + 0.11 * height_m
    else:
        top_dm3 = 11.55 - 0.64 * d_cm + 0.0088 * d2 + 0.14 * height_m
        if not over_bark:
            top_dm3 = 9.60 - 0.55 * d_cm + 0.0075 * d2 + 0.13 * height_m
    return _norway_m3sk_dm3(top_dm3, tree_species.full_name)


def default_bark_thickness_for_species(tree_species: TreeName, dbh_cm: float) -> float:
    """Return a default double bark-thickness estimate by species."""
    if tree_species == TreeSpecies.Norway.picea_abies:
        return hansen_2023_norway_spruce_norway_bark_thickness(dbh_cm, dbh_cm)
    if tree_species == TreeSpecies.Norway.pinus_sylvestris:
        return hansen_2023_scots_pine_norway_bark_thickness(dbh_cm, dbh_cm)
    return hansen_2023_birch_norway_bark_thickness(dbh_cm, dbh_cm)


__all__ = [
    "vestjordet_1967_volume_norway_spruce_norway",
    "vestjordet_1967_volume_tree_top",
    "default_bark_thickness_for_species",
]


DESCRIPTOR = FormulaDescriptor(
    component_id="vestjordet_1967_volume",
    source=SourceReference(
        author="Vestjordet, E.",
        year=1967,
        title="Funksjoner og tabeller for kubering av stående gran",
        note=(
            "Meddelelser fra Det norske Skogforsøksvesen 22:539-574. Spruce tree-volume equations."
        ),
    ),
    species_groups={"spruce": frozenset({"Picea abies"})},
    units={},
    kernel_names=(
        "vestjordet_1967_volume_norway_spruce_norway",
        "vestjordet_1967_volume_tree_top",
        "default_bark_thickness_for_species",
    ),
)
