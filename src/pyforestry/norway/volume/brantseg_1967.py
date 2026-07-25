"""Brantseg (1967) Scots pine tree-volume equation for Norway."""

from __future__ import annotations

import warnings
from typing import Optional, Union

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers.primitives import AtomicVolume, Diameter_cm
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.norway.bark.hansen_2023 import hansen_2023_scots_pine_norway_bark_thickness


def _norway_m3sk_dm3(value_dm3: float, species_full_name: str) -> AtomicVolume:
    """Create a Norway m3sk volume from dm3."""
    return AtomicVolume.from_unit(
        max(0.0, value_dm3),
        "dm3",
        region="Norway",
        species=species_full_name,
        type="m3sk",
    )


def brantseg_1967_volume_scots_pine_norway(
    height_m: float,
    diameter_cm: Union[Diameter_cm, float],
    bark_thickness_cm: Optional[float] = None,
    with_bark: bool = True,
) -> AtomicVolume:
    """Return Scots pine tree volume (`m3sk`) for Norway."""
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
            bark_thickness_cm = hansen_2023_scots_pine_norway_bark_thickness(
                diam_ob_cm,
                diam_ob_cm,
            )
        if not isinstance(bark_thickness_cm, (float, int)):
            raise TypeError("Input 'bark_thickness_cm' must be a float or int.")
        if bark_thickness_cm < 0:
            raise ValueError("Input 'bark_thickness_cm' must be non-negative.")
        diam_eff_cm = diam_ob_cm - float(bark_thickness_cm)
        if diam_eff_cm < 0:
            return _norway_m3sk_dm3(0.0, TreeSpecies.Norway.pinus_sylvestris.full_name)

    if diam_ob_cm <= 0.0 or diam_eff_cm <= 0.0:
        return _norway_m3sk_dm3(0.0, TreeSpecies.Norway.pinus_sylvestris.full_name)

    d2 = diam_eff_cm * diam_eff_cm
    h2 = height_m * height_m
    if diam_ob_cm <= 12.0:
        volume_dm3 = 2.912 + 0.039994 * d2 * height_m - 0.001091 * diam_eff_cm * h2
    else:
        volume_dm3 = 8.6524 + 0.076844 * d2 + 0.031573 * d2 * height_m

    return _norway_m3sk_dm3(volume_dm3, TreeSpecies.Norway.pinus_sylvestris.full_name)


__all__ = ["brantseg_1967_volume_scots_pine_norway"]


DESCRIPTOR = FormulaDescriptor(
    component_id="brantseg_1967_volume",
    source=SourceReference(
        author="Brantseg, A.",
        year=1967,
        title="Furu sønnafjells. Kubering av stående skog. Funksjoner og tabeller",
        note=(
            "Meddelelser fra Det norske Skogforsøksvesen 22:695-739. "
            "Scots pine tree-volume equation."
        ),
    ),
    species_groups={"pine": frozenset({"Pinus sylvestris"})},
    units={},
    kernel_names=("brantseg_1967_volume_scots_pine_norway",),
)
