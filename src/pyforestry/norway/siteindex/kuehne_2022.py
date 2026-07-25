"""Kuehne et al. (2022) dominant-height / site-index trajectory for Scots pine, Norway.

Implements the dominant-height / site-index sub-model (Eq. 5) of Kuehne et al.
(2022); the stem-density, basal-area, volume and thinning components (Eqs. 6-10)
are in ``pyforestry.norway.growth.kuehne_2022``. The data are even-aged Scots
pine stands (mostly naturally regenerated or sown, not "planted").
"""

from __future__ import annotations

import warnings
from typing import Callable, Literal

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers.primitives import Age, AgeMeasurement, SiteIndexValue
from pyforestry.base.helpers.tree_species import PINUS_SYLVESTRIS


def _require_total_age(age: AgeMeasurement, argument_name: str) -> None:
    """Validate total-age input for Kuehne equations."""
    if not isinstance(age, AgeMeasurement) or age.code != Age.TOTAL.value:
        raise TypeError(f"Input '{argument_name}' must be specified as Age.TOTAL.")
    if float(age) <= 0.0:
        raise ValueError(f"Input '{argument_name}' must be positive.")


def _kuehne_height_and_h100(
    age_total: float,
    age2_total: float,
    dominant_height_m: float,
) -> tuple[float, float]:
    """Evaluate Kuehne trajectory and SI H100."""
    if dominant_height_m <= 0.0 or age_total <= 0.0 or age2_total <= 0.0:
        raise ValueError("dominant_height_m, age, and age2 must be positive.")

    b1 = 68.41819
    b2 = -24.04110
    b3 = 1.46991

    denom_x = 1.0 - b2 * dominant_height_m * (age_total**-b3)
    if abs(denom_x) < 1e-9:
        warnings.warn("Near-zero denominator in Kuehne trajectory X calculation.", stacklevel=2)
        return float("nan"), float("nan")

    x_term = (dominant_height_m - b1) / denom_x

    denom_h2 = 1.0 + b2 * x_term * (age2_total**-b3)
    if abs(denom_h2) < 1e-9:
        warnings.warn("Near-zero denominator in Kuehne trajectory age2 calculation.", stacklevel=2)
        height2 = float("nan")
    else:
        height2 = (b1 + x_term) / denom_h2

    denom_h100 = 1.0 + b2 * x_term * (100.0**-b3)
    if abs(denom_h100) < 1e-9:
        warnings.warn("Near-zero denominator in Kuehne SI H100 calculation.", stacklevel=2)
        h100 = float("nan")
    else:
        h100 = (b1 + x_term) / denom_h100
    return height2, h100


def kuehne_2022_height_trajectory_scots_pine_norway(
    dominant_height_m: float,
    age: AgeMeasurement,
    age2: AgeMeasurement,
) -> SiteIndexValue:
    """Return Scots pine dominant height at total age `age2`."""
    _require_total_age(age, "age")
    _require_total_age(age2, "age2")
    height2, _ = _kuehne_height_and_h100(float(age), float(age2), float(dominant_height_m))
    return SiteIndexValue(
        value=height2,
        reference_age=age2,
        species={PINUS_SYLVESTRIS},
        fn=Kuehne2022.height_trajectory.pinus_sylvestris,
    )


def kuehne_2022_site_index_h100_scots_pine_norway(
    dominant_height_m: float,
    age: AgeMeasurement,
) -> SiteIndexValue:
    """Return Scots pine site index H100 from current dominant height and total age."""
    _require_total_age(age, "age")
    _, h100 = _kuehne_height_and_h100(float(age), 100.0, float(dominant_height_m))
    return SiteIndexValue(
        value=h100,
        reference_age=Age.TOTAL(100.0),
        species={PINUS_SYLVESTRIS},
        fn=kuehne_2022_site_index_h100_scots_pine_norway,
    )


def kuehne_2022_height_trajectory_and_si_scots_pine_norway(
    dominant_height_m: float,
    age: AgeMeasurement,
    age2: AgeMeasurement,
    output: Literal["height", "sih100", "both"] = "height",
) -> SiteIndexValue | tuple[SiteIndexValue, float]:
    """Return trajectory result, SI H100, or both."""
    _require_total_age(age, "age")
    _require_total_age(age2, "age2")
    height2, h100 = _kuehne_height_and_h100(float(age), float(age2), float(dominant_height_m))
    height_value = SiteIndexValue(
        value=height2,
        reference_age=age2,
        species={PINUS_SYLVESTRIS},
        fn=Kuehne2022.height_trajectory.pinus_sylvestris,
    )
    key = output.lower()
    if key == "height":
        return height_value
    if key == "sih100":
        return SiteIndexValue(
            value=h100,
            reference_age=Age.TOTAL(100.0),
            species={PINUS_SYLVESTRIS},
            fn=kuehne_2022_site_index_h100_scots_pine_norway,
        )
    if key == "both":
        return height_value, h100
    raise ValueError("output must be one of: 'height', 'sih100', 'both'.")


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


class Kuehne2022:
    """Class-style compatibility facade for Kuehne (2022)."""

    height_trajectory = type(
        "HeightTrajectoryContainer",
        (),
        {"pinus_sylvestris": _Wrapper(kuehne_2022_height_trajectory_scots_pine_norway)},
    )()


class KuehnePineModel:
    """Thin compatibility class exposing Kuehne height/site-index callables."""

    height_trajectory_and_si = staticmethod(kuehne_2022_height_trajectory_and_si_scots_pine_norway)


__all__ = [
    "Kuehne2022",
    "KuehnePineModel",
    "kuehne_2022_height_trajectory_scots_pine_norway",
    "kuehne_2022_site_index_h100_scots_pine_norway",
    "kuehne_2022_height_trajectory_and_si_scots_pine_norway",
]


DESCRIPTOR = FormulaDescriptor(
    component_id="kuehne_2022_siteindex",
    source=SourceReference(
        author="Kuehne, C., McLean, J.P., Maleki, K., Antón-Fernández, C. & Astrup, R.",
        year=2022,
        title=(
            "A stand-level growth and yield model for thinned and unthinned "
            "even-aged Scots pine forests in Norway"
        ),
        note=(
            "Silva Fennica 56(1), article 10627. doi:10.14214/sf.10627. "
            "Dominant-height / site-index sub-model, Eq. 5."
        ),
    ),
    species_groups={"pine": frozenset({"Pinus sylvestris"})},
    units={},
    kernel_names=(
        "Kuehne2022",
        "KuehnePineModel",
        "kuehne_2022_height_trajectory_scots_pine_norway",
        "kuehne_2022_site_index_h100_scots_pine_norway",
        "kuehne_2022_height_trajectory_and_si_scots_pine_norway",
    ),
)
