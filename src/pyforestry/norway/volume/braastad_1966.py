"""Braastad (1966) birch tree-volume equation for Norway."""

from __future__ import annotations

import warnings
from typing import Optional, Union

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers.primitives import AtomicVolume, Diameter_cm
from pyforestry.base.helpers.tree_species import TreeName, TreeSpecies, parse_tree_species
from pyforestry.norway.bark.hansen_2023 import hansen_2023_birch_norway_bark_thickness

_BRAASTAD_SPECIES = {TreeSpecies.Norway.betula_pendula, TreeSpecies.Norway.betula_pubescens}


def _norway_m3sk_dm3(value_dm3: float, species_full_name: str) -> AtomicVolume:
    """Create a Norway m3sk volume from dm3."""
    return AtomicVolume.from_unit(
        max(0.0, value_dm3),
        "dm3",
        region="Norway",
        species=species_full_name,
        type="m3sk",
    )


def braastad_1966_birch_volume_norway(
    height_m: float,
    diameter_cm: Union[Diameter_cm, float],
    species: Union[TreeName, str],
    bark_thickness_cm: Optional[float] = None,
    with_bark: bool = True,
) -> AtomicVolume:
    """Return birch tree volume (`m3sk`) for Norway."""
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

    tree_species = parse_tree_species(species)
    if tree_species not in _BRAASTAD_SPECIES:
        expected = ", ".join(sorted(sp.full_name for sp in _BRAASTAD_SPECIES))
        raise ValueError(
            f"Species '{tree_species.full_name}' is not supported. Expected: {expected}."
        )

    diam_eff_cm = diam_ob_cm
    if bark_thickness_cm is None:
        bark_thickness_cm = hansen_2023_birch_norway_bark_thickness(diam_ob_cm, diam_ob_cm)
    if not isinstance(bark_thickness_cm, (float, int)):
        raise TypeError("Input 'bark_thickness_cm' must be a float or int.")
    if bark_thickness_cm < 0:
        raise ValueError("Input 'bark_thickness_cm' must be non-negative.")
    double_bark_cm = float(bark_thickness_cm)

    if not with_bark:
        diam_eff_cm = diam_ob_cm - double_bark_cm
        if diam_eff_cm < 0:
            return _norway_m3sk_dm3(0.0, tree_species.full_name)

    if diam_ob_cm <= 0.0 or diam_eff_cm <= 0.0:
        return _norway_m3sk_dm3(0.0, tree_species.full_name)

    d2 = diam_eff_cm * diam_eff_cm
    h2 = height_m * height_m
    double_bark_mm = double_bark_cm * 10.0
    volume_dm3 = (
        -1.25409
        + 0.12739 * d2
        + 0.03166 * d2 * height_m
        + 0.0009752 * diam_eff_cm * h2
        - 0.01226 * h2
        - 0.004214 * d2 * double_bark_mm
    )
    return _norway_m3sk_dm3(volume_dm3, tree_species.full_name)


__all__ = ["braastad_1966_birch_volume_norway"]


DESCRIPTOR = FormulaDescriptor(
    component_id="braastad_1966_volume",
    source=SourceReference(
        author="Braastad, H.",
        year=1966,
        title="Volumtabeller for bjørk",
        note=("Meddelelser fra Det norske Skogforsøksvesen 21:23-78. Birch tree-volume equation."),
    ),
    species_groups={"birch": frozenset({"Betula pubescens", "Betula pendula"})},
    units={},
    kernel_names=("braastad_1966_birch_volume_norway",),
)
