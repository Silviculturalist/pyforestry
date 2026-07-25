"""Brantseg (1967) Scots pine bark-thickness equation for Norway."""

from __future__ import annotations

import warnings
from typing import Union

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers.primitives import Diameter_cm


def brantseg_1967_scots_pine_norway_bark_thickness(
    diameter_cm: Union[Diameter_cm, float],
    height_m: float,
) -> float:
    """Return double bark thickness (cm) for Scots pine in Norway."""
    if isinstance(diameter_cm, Diameter_cm):
        if not diameter_cm.over_bark:
            raise ValueError("Input 'diameter_cm' must be measured over bark.")
        if diameter_cm.measurement_height_m != 1.3:
            warnings.warn(
                (
                    "Input 'diameter_cm' (Diameter_cm) uses measurement height "
                    f"{diameter_cm.measurement_height_m} m; model assumes 1.3 m."
                ),
                stacklevel=2,
            )
        dbh_cm = float(diameter_cm)
    elif isinstance(diameter_cm, (float, int)):
        dbh_cm = float(diameter_cm)
    else:
        raise TypeError("Input 'diameter_cm' must be a float, int, or Diameter_cm.")

    if dbh_cm < 0:
        raise ValueError("Input 'diameter_cm' must be non-negative.")
    if height_m <= 0:
        return 0.0

    double_bark_mm = 2.9571 + 1.1499 * dbh_cm - 0.7304 * dbh_cm / height_m
    # Numerical safeguard (NOT from Brantseg 1967): floor double bark at 5% of
    # diameter so the polynomial cannot return negative/implausibly-thin bark at
    # small d / large h. Implementation choice only, not a published rule.
    min_double_bark_mm = dbh_cm * 0.05
    if double_bark_mm < min_double_bark_mm:
        double_bark_mm = min_double_bark_mm
    return max(0.0, double_bark_mm / 10.0)


__all__ = ["brantseg_1967_scots_pine_norway_bark_thickness"]


DESCRIPTOR = FormulaDescriptor(
    component_id="brantseg_1967_bark",
    source=SourceReference(
        author="Brantseg, A.",
        year=1967,
        title="Furu sønnafjells. Kubering av stående skog. Funksjoner og tabeller",
        note=("Meddelelser fra Det norske Skogforsøksvesen 22:695-739. Double-bark equation."),
    ),
    species_groups={"pine": frozenset({"Pinus sylvestris"})},
    units={},
    kernel_names=("brantseg_1967_scots_pine_norway_bark_thickness",),
)
