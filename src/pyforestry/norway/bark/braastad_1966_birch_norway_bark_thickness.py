"""Braastad (1966) birch bark-thickness equation for Norway."""

from __future__ import annotations

import warnings
from typing import Union

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers.primitives import Diameter_cm


def braastad_1966_birch_norway_bark_thickness(
    diameter_cm: Union[Diameter_cm, float],
    height_m: float,
) -> float:
    """Return double bark thickness (cm) for birch in Norway."""
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
    if height_m < 0:
        raise ValueError("Input 'height_m' must be non-negative.")

    double_bark_mm = 1.046 * dbh_cm
    # Numerical safeguard (NOT from Braastad 1966), shared with the spruce/pine
    # bark models; inert here because 1.046*d always exceeds 5% of diameter.
    min_double_bark_mm = dbh_cm * 0.05
    if double_bark_mm < min_double_bark_mm:
        double_bark_mm = min_double_bark_mm
    return max(0.0, double_bark_mm / 10.0)


__all__ = ["braastad_1966_birch_norway_bark_thickness"]


DESCRIPTOR = FormulaDescriptor(
    component_id="braastad_1966_bark",
    source=SourceReference(
        author="Braastad, H.",
        year=1966,
        title="Volumtabeller for bjørk",
        note=("Meddelelser fra Det norske Skogforsøksvesen 21:23-78. Birch double-bark equation."),
    ),
    species_groups={"birch": frozenset({"Betula pubescens", "Betula pendula"})},
    units={},
    kernel_names=("braastad_1966_birch_norway_bark_thickness",),
)
