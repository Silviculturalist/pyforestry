"""Tveite Norway height-trajectory and Lorey's-height equations.

The module gathers three publications by the same author, so it is named for the
author alone and every function carries the year of the work it implements:

* ``tveite_1977_*`` -- Norway spruce site-index curves, Tveite (1977)
  "Bonitetskurver for gran", Medd. Norsk inst. skogforsk. 33.1.
* ``tveite_1976_*`` -- Scots pine site-index curves, Tveite (1976)
  "Bonitetskurver for furu" (manuscript).
* ``tveite_1967_*`` -- Lorey's mean height, Tveite (1967).

The spruce curves were previously exported under a ``tveite_1976`` name, which
dated them a year early; the names above are the publication years.
"""

from __future__ import annotations

import math
import warnings
from typing import Callable, Set, Union

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers.primitives import (
    Age,
    AgeMeasurement,
    Diameter_cm,
    QuadraticMeanDiameter,
    SiteIndexValue,
    StandBasalArea,
    Stems,
)
from pyforestry.base.helpers.tree_species import PICEA_ABIES, PINUS_SYLVESTRIS, TreeName


def _require_dbh_age(age: AgeMeasurement, argument_name: str) -> None:
    """Validate DBH-age input for Tveite equations."""
    if not isinstance(age, AgeMeasurement) or age.code != Age.DBH.value:
        raise TypeError(f"Input '{argument_name}' must be specified as Age.DBH.")
    if float(age) <= 0.0:
        raise ValueError(f"Input '{argument_name}' must be positive.")


def _spruce_height_trajectory(dominant_height_m: float, age_dbh: float, age2_dbh: float) -> float:
    """Evaluate Tveite spruce height trajectory."""
    if age_dbh < 15 or age2_dbh < 15:
        warnings.warn(
            "Tveite spruce trajectory is not recommended below 15-20 years DBH age.",
            stacklevel=2,
        )
    h17 = ((age_dbh + 5.5) / (4.30606 + 0.164818 * (age_dbh + 5.5))) ** 2.1
    if age_dbh <= 100:
        diff_age = (
            3
            + 0.040183 * (age_dbh - 40)
            - 0.104701 * ((age_dbh - 40) ** 2) / 100.0
            + 0.679104 * ((age_dbh - 40) ** 3) / 100000.0
            + 0.184402 * ((age_dbh - 40) ** 4) / 1_000_000.0
            - 0.224249 * ((age_dbh - 40) ** 5) / 100_000_000.0
        )
    else:
        diff_age = 3.755
    diff_age /= 3.0
    number_of_differences = 0.0 if abs(diff_age) < 1e-9 else (dominant_height_m - h17) / diff_age

    h17_2 = ((age2_dbh + 5.5) / (4.30606 + 0.164818 * (age2_dbh + 5.5))) ** 2.1
    if age2_dbh <= 100:
        diff_age2 = (
            3
            + 0.040183 * (age2_dbh - 40)
            - 0.104701 * ((age2_dbh - 40) ** 2) / 100.0
            + 0.679104 * ((age2_dbh - 40) ** 3) / 100000.0
            + 0.184402 * ((age2_dbh - 40) ** 4) / 1_000_000.0
            - 0.224249 * ((age2_dbh - 40) ** 5) / 100_000_000.0
        )
    else:
        diff_age2 = 3.755
    diff_age2 /= 3.0
    return h17_2 + diff_age2 * number_of_differences


def _pine_height_trajectory(dominant_height_m: float, age_dbh: float, age2_dbh: float) -> float:
    """Evaluate Tveite pine height trajectory."""
    h14 = 24.7 * (1 - math.exp(-0.02105 * age_dbh)) ** 1.18029 + 1.3
    if age_dbh <= 119:
        diff_age = (
            3
            + 0.0394624 * (age_dbh - 40)
            - 0.0649695 * ((age_dbh - 40) ** 2) / 100.0
            + 0.487394 * ((age_dbh - 40) ** 3) / 100000.0
            - 0.141827 * ((age_dbh - 40) ** 4) / 10_000_000.0
        )
    else:
        diff_age = 3.913
    diff_age /= 3.0
    number_of_differences = 0.0 if abs(diff_age) < 1e-9 else (dominant_height_m - h14) / diff_age

    h14_2 = 24.7 * (1 - math.exp(-0.02105 * age2_dbh)) ** 1.18029 + 1.3
    if age2_dbh <= 119:
        diff_age2 = (
            3
            + 0.0394624 * (age2_dbh - 40)
            - 0.0649695 * ((age2_dbh - 40) ** 2) / 100.0
            + 0.487394 * ((age2_dbh - 40) ** 3) / 100000.0
            - 0.141827 * ((age2_dbh - 40) ** 4) / 10_000_000.0
        )
    else:
        diff_age2 = 3.913
    diff_age2 /= 3.0
    return h14_2 + diff_age2 * number_of_differences


def _site_index_result(
    value: float,
    age2: AgeMeasurement,
    species: Set[TreeName],
    fn: Callable,
) -> SiteIndexValue:
    """Build a site-index value with metadata."""
    return SiteIndexValue(value=value, reference_age=age2, species=species, fn=fn)


def tveite_1977_height_trajectory_norway_spruce_norway(
    dominant_height_m: float,
    age: AgeMeasurement,
    age2: AgeMeasurement,
) -> SiteIndexValue:
    """Return Norway spruce dominant height at `age2` DBH age."""
    _require_dbh_age(age, "age")
    _require_dbh_age(age2, "age2")
    value = _spruce_height_trajectory(float(dominant_height_m), float(age), float(age2))
    return _site_index_result(
        value=value,
        age2=age2,
        species={PICEA_ABIES},
        fn=Tveite.height_trajectory.picea_abies,
    )


def tveite_height_trajectory_scots_pine_norway(
    dominant_height_m: float,
    age: AgeMeasurement,
    age2: AgeMeasurement,
) -> SiteIndexValue:
    """Return Scots pine dominant height at `age2` DBH age."""
    _require_dbh_age(age, "age")
    _require_dbh_age(age2, "age2")
    value = _pine_height_trajectory(float(dominant_height_m), float(age), float(age2))
    return _site_index_result(
        value=value,
        age2=age2,
        species={PINUS_SYLVESTRIS},
        fn=Tveite.height_trajectory.pinus_sylvestris,
    )


def tveite_1967_loreys_height_norway_spruce(
    dominant_height_m: float,
    stems_per_ha: Union[Stems, float],
    basal_area_m2_ha: Union[StandBasalArea, float],
    qmd_cm: Union[QuadraticMeanDiameter, float],
) -> float:
    """Return Lorey's mean height for spruce (Tveite 1967)."""
    stems_value = float(stems_per_ha)
    basal_area_value = float(basal_area_m2_ha)
    qmd_value = float(qmd_cm)
    return (
        dominant_height_m
        - (
            226.439
            + 14.37 * dominant_height_m
            - 0.0329 * stems_value
            + 0.00468 * stems_value * dominant_height_m
            - 5.91 * basal_area_value
            + 0.190 * basal_area_value * dominant_height_m
            - 15.73 * qmd_value
        )
        / 100.0
    )


def tveite_1967_loreys_height_scots_pine(
    dominant_height_m: float,
    stems_per_ha: Union[Stems, float],
    basal_area_m2_ha: Union[StandBasalArea, float],
    diameter_mean_ba_stem_cm: Union[Diameter_cm, float],
) -> float:
    """Return Lorey's mean height for pine (Tveite 1967)."""
    stems_value = float(stems_per_ha)
    basal_area_value = float(basal_area_m2_ha)
    diameter_value = float(diameter_mean_ba_stem_cm)
    return (
        dominant_height_m
        - (
            159.849
            + 23.028 * dominant_height_m
            - 0.041770 * stems_value
            + 0.004652 * stems_value * dominant_height_m
            - 6.190 * basal_area_value
            + 0.223 * basal_area_value * dominant_height_m
            - 14.730 * diameter_value
        )
        / 100.0
    )


class _Wrapper:
    """Callable wrapper for class-style compatibility access."""

    def __init__(self, fn: Callable):
        """Init.

        Args:
            fn: Parameter for `_Wrapper.__init__`.

        Source:
            Forestry model implementation for Norwegian conditions as provided
            by pyforestry equation modules.
        """
        self._fn = fn

    def __call__(self, *args, **kwargs):
        """Delegate to wrapped function."""
        return self._fn(*args, **kwargs)


class Tveite:
    """Class-style compatibility facade for Tveite equations."""

    height_trajectory = type(
        "HeightTrajectoryContainer",
        (),
        {
            "picea_abies": _Wrapper(tveite_1977_height_trajectory_norway_spruce_norway),
            "pinus_sylvestris": _Wrapper(tveite_height_trajectory_scots_pine_norway),
        },
    )()
    HL = type(
        "LoreysHeightContainer",
        (),
        {
            "picea_abies": _Wrapper(tveite_1967_loreys_height_norway_spruce),
            "pinus_sylvestris": _Wrapper(tveite_1967_loreys_height_scots_pine),
        },
    )()


__all__ = [
    "Tveite",
    "tveite_1977_height_trajectory_norway_spruce_norway",
    "tveite_height_trajectory_scots_pine_norway",
    "tveite_1967_loreys_height_norway_spruce",
    "tveite_1967_loreys_height_scots_pine",
]


DESCRIPTOR = FormulaDescriptor(
    component_id="tveite_siteindex",
    source=SourceReference(
        author="Tveite, B.",
        year=1977,
        title="Bonitetskurver for gran",
        note=(
            "Medd. Norsk inst. skogforsk. 33.1. This module spans three of the "
            "author's publications and a single reference cannot carry them all; "
            "each function is named for its own year. Spruce site index: Tveite "
            "(1977), above. Pine site index: Tveite (1976) 'Bonitetskurver for "
            "furu' (manuscript). Lorey's height: Tveite (1967)."
        ),
    ),
    species_groups={
        "spruce": frozenset({"Picea abies"}),
        "pine": frozenset({"Pinus sylvestris"}),
    },
    units={},
    kernel_names=(
        "Tveite",
        "tveite_1977_height_trajectory_norway_spruce_norway",
        "tveite_height_trajectory_scots_pine_norway",
        "tveite_1967_loreys_height_norway_spruce",
        "tveite_1967_loreys_height_scots_pine",
    ),
)
