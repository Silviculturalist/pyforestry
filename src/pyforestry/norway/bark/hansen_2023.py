"""Hansen et al. (2023) bark-thickness equations for Norway."""

from __future__ import annotations

import warnings
from typing import Union

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers.primitives import Diameter_cm


def _coerce_over_bark_dbh_cm(diameter_cm: Union[float, Diameter_cm]) -> float:
    """Convert DBH input to a validated numeric over-bark diameter in cm."""
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
        dbh_cm = float(diameter_cm)
    elif isinstance(diameter_cm, (float, int)):
        dbh_cm = float(diameter_cm)
    else:
        raise TypeError("Input 'diameter_cm' must be a float, int, or Diameter_cm.")

    if dbh_cm < 0:
        raise ValueError("Input 'diameter_cm' must be non-negative.")
    return dbh_cm


def _coerce_diameter_desired_cm(diameter_desired_cm: float) -> float:
    """Validate the diameter at the target stem position."""
    if not isinstance(diameter_desired_cm, (float, int)):
        raise TypeError("Input 'diameter_desired_cm' must be a float or int.")
    diameter = float(diameter_desired_cm)
    if diameter < 0:
        raise ValueError("Input 'diameter_desired_cm' must be non-negative.")
    return diameter


def hansen_2023_norway_spruce_norway_bark_thickness(
    diameter_cm: Union[float, Diameter_cm],
    diameter_desired_cm: float,
) -> float:
    """Return double bark thickness (cm) for Norway spruce in Norway."""
    dbh_cm = _coerce_over_bark_dbh_cm(diameter_cm)
    desired_cm = _coerce_diameter_desired_cm(diameter_desired_cm)
    if dbh_cm <= 0.0 or desired_cm <= 0.0:
        return 0.0
    bark_cm = 0.2324 + 0.0068 * dbh_cm + 0.0399 * desired_cm
    return max(0.0, bark_cm)


def hansen_2023_scots_pine_norway_bark_thickness(
    diameter_cm: Union[float, Diameter_cm],
    diameter_desired_cm: float,
) -> float:
    """Return double bark thickness (cm) for Scots pine in Norway."""
    dbh_cm = _coerce_over_bark_dbh_cm(diameter_cm)
    desired_cm = _coerce_diameter_desired_cm(diameter_desired_cm)
    if dbh_cm <= 0.0 or desired_cm <= 0.0:
        return 0.0
    bark_cm = 0.2931 - 0.0405 * dbh_cm + 0.1213 * desired_cm
    return max(0.0, bark_cm)


def hansen_2023_birch_norway_bark_thickness(
    diameter_cm: Union[float, Diameter_cm],
    diameter_desired_cm: float,
) -> float:
    """Return double bark thickness (cm) for birch in Norway."""
    dbh_cm = _coerce_over_bark_dbh_cm(diameter_cm)
    desired_cm = _coerce_diameter_desired_cm(diameter_desired_cm)
    if dbh_cm <= 0.0 or desired_cm <= 0.0:
        return 0.0
    bark_cm = -0.0483 + 0.0050 * dbh_cm + 0.0846 * desired_cm
    return max(0.0, bark_cm)


__all__ = [
    "hansen_2023_norway_spruce_norway_bark_thickness",
    "hansen_2023_scots_pine_norway_bark_thickness",
    "hansen_2023_birch_norway_bark_thickness",
]


DESCRIPTOR = FormulaDescriptor(
    component_id="hansen_2023_bark",
    source=SourceReference(
        author="Hansen, E.",
        year=2023,
        title="Bark-thickness equations for Norway",
        note="Hansen et al.; descriptive title, the formal publication title is not "
        "established here.",
    ),
    species_groups={
        "spruce": frozenset({"Picea abies"}),
        "pine": frozenset({"Pinus sylvestris"}),
        "birch": frozenset({"Betula pubescens", "Betula pendula"}),
    },
    units={},
    kernel_names=(
        "hansen_2023_norway_spruce_norway_bark_thickness",
        "hansen_2023_scots_pine_norway_bark_thickness",
        "hansen_2023_birch_norway_bark_thickness",
    ),
)
