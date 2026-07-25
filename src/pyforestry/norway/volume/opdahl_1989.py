"""Opdahl & Skroppa (1989) aspen tree-volume equation for Norway."""

from __future__ import annotations

import warnings
from typing import Optional, Union

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers.primitives import AtomicVolume, Diameter_cm
from pyforestry.base.helpers.tree_species import TreeName, TreeSpecies, parse_tree_species
from pyforestry.norway.bark.hansen_2023 import hansen_2023_birch_norway_bark_thickness

_OPDAHL_SPECIES = {TreeSpecies.Norway.populus_tremula}


def _norway_m3sk_dm3(value_dm3: float, species_full_name: str) -> AtomicVolume:
    """Create a Norway m3sk volume from dm3."""
    return AtomicVolume.from_unit(
        max(0.0, value_dm3),
        "dm3",
        region="Norway",
        species=species_full_name,
        type="m3sk",
    )


def opdahl_1989_volume_aspen_norway(
    height_m: float,
    diameter_cm: Union[Diameter_cm, float],
    species: Union[TreeName, str],
    bark_thickness_cm: Optional[float] = None,
    with_bark: bool = True,
) -> AtomicVolume:
    """Return aspen tree volume (`m3sk`) for Norway."""
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

    tree_species = parse_tree_species(species)
    if tree_species not in _OPDAHL_SPECIES:
        expected = ", ".join(sorted(sp.full_name for sp in _OPDAHL_SPECIES))
        raise ValueError(
            f"Species '{tree_species.full_name}' is not supported. Expected: {expected}."
        )

    if height_m < 1.3:
        return _norway_m3sk_dm3(0.0, tree_species.full_name)

    diam_eff_cm = diam_ob_cm
    if not with_bark:
        if bark_thickness_cm is None:
            warnings.warn(
                "Aspen bark thickness missing; estimating via Hansen (2023) birch equation.",
                stacklevel=2,
            )
            bark_thickness_cm = hansen_2023_birch_norway_bark_thickness(diam_ob_cm, diam_ob_cm)
        if not isinstance(bark_thickness_cm, (float, int)):
            raise TypeError("Input 'bark_thickness_cm' must be a float or int.")
        if bark_thickness_cm < 0:
            raise ValueError("Input 'bark_thickness_cm' must be non-negative.")
        diam_eff_cm = diam_ob_cm - float(bark_thickness_cm)
        if diam_eff_cm < 0:
            return _norway_m3sk_dm3(0.0, tree_species.full_name)

    if diam_ob_cm <= 1e-9 or diam_eff_cm <= 0.0:
        return _norway_m3sk_dm3(0.0, tree_species.full_name)

    d2 = diam_eff_cm * diam_eff_cm
    volume_m3 = -0.04755 + 0.00699 * diam_eff_cm - 0.00023 * d2 + 0.00004 * d2 * height_m
    volume_dm3 = volume_m3 * 1000.0
    return _norway_m3sk_dm3(volume_dm3, tree_species.full_name)


__all__ = ["opdahl_1989_volume_aspen_norway"]


DESCRIPTOR = FormulaDescriptor(
    component_id="opdahl_1989_volume",
    source=SourceReference(
        author="Opdahl, H.; Skroppa, T.",
        year=1989,
        title="Aspen tree-volume equation for Norway",
        note="Descriptive title; the formal publication title is not established here.",
    ),
    species_groups={"aspen": frozenset({"Populus tremula"})},
    units={},
    kernel_names=("opdahl_1989_volume_aspen_norway",),
)
