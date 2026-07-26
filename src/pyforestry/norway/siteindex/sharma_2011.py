"""Sharma et al. (2011) height trajectories for Norway spruce and Scots pine."""

from __future__ import annotations

import math
import warnings
from typing import Callable, Set

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers.primitives import Age, AgeMeasurement, SiteIndexValue
from pyforestry.base.helpers.tree_species import PICEA_ABIES, PINUS_SYLVESTRIS, TreeName


def _require_dbh_age(age: AgeMeasurement, argument_name: str) -> None:
    """Validate DBH-age input for Sharma equations."""
    if not isinstance(age, AgeMeasurement) or age.code != Age.DBH.value:
        raise TypeError(f"Input '{argument_name}' must be specified as Age.DBH.")
    if float(age) <= 0.0:
        raise ValueError(f"Input '{argument_name}' must be positive.")


def _sharma_height(
    dominant_height_m: float,
    age_dbh: float,
    age2_dbh: float,
    b1: float,
    b2: float,
    b3: float,
) -> float:
    """Evaluate the generic Sharma (2011) difference equation."""
    if dominant_height_m <= 1.3:
        raise ValueError("Dominant height must be > 1.3 m.")
    theta = (dominant_height_m - 1.3) - b1
    age_pow = age_dbh ** (-b3)
    sqrt_arg = theta * theta + 4.0 * b2 * (dominant_height_m - 1.3) * age_pow
    if sqrt_arg < 0.0:
        warnings.warn(
            f"Negative square-root argument ({sqrt_arg:.4f}) in Sharma equation.",
            stacklevel=2,
        )
        return float("nan")
    x_term = 0.5 * (theta + math.sqrt(sqrt_arg))
    if abs(x_term) < 1e-9:
        warnings.warn("Near-zero intermediate x term in Sharma equation.", stacklevel=2)
        return float("nan")
    denom = 1.0 + (b2 / x_term) * (age2_dbh ** (-b3))
    if abs(denom) < 1e-9:
        warnings.warn("Near-zero denominator in Sharma equation.", stacklevel=2)
        return float("nan")
    return (b1 + x_term) / denom + 1.3


def _site_index_result(
    value: float,
    age2: AgeMeasurement,
    species: Set[TreeName],
    fn: Callable,
) -> SiteIndexValue:
    """Build a site-index value with metadata."""
    return SiteIndexValue(value=value, reference_age=age2, species=species, fn=fn)


def sharma_2011_height_trajectory_norway_spruce_norway(
    dominant_height_m: float,
    age: AgeMeasurement,
    age2: AgeMeasurement,
) -> SiteIndexValue:
    """Return Norway spruce dominant height at `age2` DBH age."""
    _require_dbh_age(age, "age")
    _require_dbh_age(age2, "age2")
    value = _sharma_height(
        float(dominant_height_m),
        float(age),
        float(age2),
        18.9206,
        5175.18,
        1.1576,
    )
    return _site_index_result(
        value=value,
        age2=age2,
        species={PICEA_ABIES},
        fn=Sharma2011.height_trajectory.picea_abies,
    )


def sharma_2011_height_trajectory_scots_pine_norway(
    dominant_height_m: float,
    age: AgeMeasurement,
    age2: AgeMeasurement,
) -> SiteIndexValue:
    """Return Scots pine dominant height at `age2` DBH age."""
    _require_dbh_age(age, "age")
    _require_dbh_age(age2, "age2")
    value = _sharma_height(
        float(dominant_height_m),
        float(age),
        float(age2),
        12.8361,
        3263.99,
        1.1758,
    )
    return _site_index_result(
        value=value,
        age2=age2,
        species={PINUS_SYLVESTRIS},
        fn=Sharma2011.height_trajectory.pinus_sylvestris,
    )


class _HeightTrajectoryWrapper:
    """Callable wrapper for class-style compatibility access."""

    def __init__(self, fn: Callable):
        """Init.

        Source:
            Forestry model implementation for Norwegian conditions as provided
            by pyforestry equation modules.
        """
        self._fn = fn

    def __call__(self, *args, **kwargs):
        """Delegate to wrapped function."""
        return self._fn(*args, **kwargs)


class Sharma2011:
    """Class-style compatibility facade for Sharma (2011)."""

    height_trajectory = type(
        "HeightTrajectoryContainer",
        (),
        {
            "picea_abies": _HeightTrajectoryWrapper(
                sharma_2011_height_trajectory_norway_spruce_norway
            ),
            "pinus_sylvestris": _HeightTrajectoryWrapper(
                sharma_2011_height_trajectory_scots_pine_norway
            ),
        },
    )()


__all__ = [
    "Sharma2011",
    "sharma_2011_height_trajectory_norway_spruce_norway",
    "sharma_2011_height_trajectory_scots_pine_norway",
]


DESCRIPTOR = FormulaDescriptor(
    component_id="sharma_2011_siteindex",
    source=SourceReference(
        author="Sharma, R.P., Brunner, A., Eid, T. & Øyen, B.-H.",
        year=2011,
        title=(
            "Modelling dominant height growth from national forest inventory individual "
            "tree data with short time series and large age errors"
        ),
        note="Forest Ecology and Management 262(12):2162-2175.",
    ),
    species_groups={
        "spruce": frozenset({"Picea abies"}),
        "pine": frozenset({"Pinus sylvestris"}),
    },
    units={},
    kernel_names=(
        "Sharma2011",
        "sharma_2011_height_trajectory_norway_spruce_norway",
        "sharma_2011_height_trajectory_scots_pine_norway",
    ),
)
