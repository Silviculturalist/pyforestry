"""Soderberg (1992) bark thickness model for Swedish trees.

Implements the Söderberg (1992) double bark thickness at breast height (1.3 m).
The original equations are reported in:

    Söderberg, U. (1992). *Functions for forest management. Height, form height
    and bark thickness of individual trees*. Report 52, Department of Forest
    Survey, SLU, Umeå.

Notes
-----
- Returns **double** bark thickness in millimetres (mm).
- Inputs are explicit and use pyforestry standard units.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Dict, Union

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers.primitives import SiteIndexValue
from pyforestry.base.helpers.tree_species import TreeName, TreeSpecies
from pyforestry.sweden._model_input_normalization import (
    coerce_species as _coerce_species_shared,
)
from pyforestry.sweden._model_input_normalization import (
    normalize_hagglund_h100_site_index_m as _normalize_hagglund_h100_site_index_m,
)
from pyforestry.sweden._model_input_normalization import (
    normalize_part_of_sweden as _normalize_part_of_sweden_shared,
)
from pyforestry.sweden._model_input_normalization import (
    species_group_for_soderberg as _species_group_for_soderberg_shared,
)
from pyforestry.sweden._model_input_normalization import (
    warn_proportion as _warn_proportion_shared,
)


@dataclass(frozen=True)
class BarkCoeff:
    """Coefficient set for Söderberg (1992) bark thickness."""

    inv_diam50: float
    inv_diam50_sqr: float
    diam_quotient: float
    diam_quotient_sqr: float
    age: float
    age_sqr: float
    site_index_pine: float
    latitude: float
    altitude: float
    lat_alt: float
    prop_pine: float
    prop_spruce: float
    prop_birch: float
    south_east: float
    region5: float
    area_part: float
    constant: float


_BARK_COEFF: Dict[str, Dict[str, BarkCoeff]] = {
    "north": {
        "pine": BarkCoeff(
            inv_diam50=-402.25,
            inv_diam50_sqr=15037.0,
            diam_quotient=0.088075,
            diam_quotient_sqr=-0.011552,
            age=0.00044577,
            age_sqr=0.0,
            site_index_pine=-0.00015147,
            latitude=-0.013581,
            altitude=0.0,
            lat_alt=-1.6395e-06,
            prop_pine=-0.069739,
            prop_spruce=0.0,
            prop_birch=0.0,
            south_east=0.0,
            region5=0.0,
            area_part=0.0,
            constant=5.3324,
        ),
        "spruce": BarkCoeff(
            inv_diam50=-236.33,
            inv_diam50_sqr=7878.4,
            diam_quotient=0.35929,
            diam_quotient_sqr=0.0,
            age=0.0013589,
            age_sqr=6.2227e-06,
            site_index_pine=-0.0015491,
            latitude=0.028379,
            altitude=0.0,
            lat_alt=0.0,
            prop_pine=0.057123,
            prop_spruce=0.0,
            prop_birch=0.0,
            south_east=0.0,
            region5=0.0,
            area_part=0.020245,
            constant=1.6604,
        ),
        "birch": BarkCoeff(
            inv_diam50=-371.31,
            inv_diam50_sqr=13012.0,
            diam_quotient=0.17146,
            diam_quotient_sqr=0.0,
            age=0.0019655,
            age_sqr=0.0,
            site_index_pine=-0.00071109,
            latitude=0.0086881,
            altitude=0.0,
            lat_alt=6.2991e-06,
            prop_pine=0.18594,
            prop_spruce=0.0,
            prop_birch=0.0,
            south_east=0.0,
            region5=0.0,
            area_part=0.0,
            constant=3.174,
        ),
        "other": BarkCoeff(
            inv_diam50=-175.62,
            inv_diam50_sqr=0.0,
            diam_quotient=0.26968,
            diam_quotient_sqr=0.0,
            age=0.0049609,
            age_sqr=0.0,
            site_index_pine=0.0,
            latitude=0.0,
            altitude=0.0,
            lat_alt=0.0,
            prop_pine=0.0,
            prop_spruce=0.0,
            prop_birch=0.29703,
            south_east=0.0,
            region5=0.0,
            area_part=-0.077013,
            constant=2.8446,
        ),
        "beech": BarkCoeff(
            inv_diam50=-173.87,
            inv_diam50_sqr=0.0,
            diam_quotient=0.1635,
            diam_quotient_sqr=0.0,
            age=0.0022597,
            age_sqr=0.0,
            site_index_pine=0.0,
            latitude=0.0,
            altitude=0.0,
            lat_alt=0.0,
            prop_pine=0.0,
            prop_spruce=0.0,
            prop_birch=0.0,
            south_east=0.0,
            region5=-0.26953,
            area_part=0.0,
            constant=2.4822,
        ),
        "oak": BarkCoeff(
            inv_diam50=-296.05,
            inv_diam50_sqr=8723.5,
            diam_quotient=0.0,
            diam_quotient_sqr=0.0,
            age=0.002268,
            age_sqr=0.0,
            site_index_pine=0.0,
            latitude=0.0,
            altitude=0.0,
            lat_alt=0.0,
            prop_pine=0.0,
            prop_spruce=0.0,
            prop_birch=0.0,
            south_east=-0.24349,
            region5=0.0,
            area_part=0.044474,
            constant=3.9521,
        ),
    },
    "middle": {
        "pine": BarkCoeff(
            inv_diam50=-394.22,
            inv_diam50_sqr=14040.0,
            diam_quotient=0.12632,
            diam_quotient_sqr=-0.046079,
            age=0.00030388,
            age_sqr=0.0,
            site_index_pine=-0.00092527,
            latitude=-0.064192,
            altitude=-0.00031573,
            lat_alt=0.0,
            prop_pine=0.0,
            prop_spruce=0.058621,
            prop_birch=0.0,
            south_east=0.0,
            region5=0.0,
            area_part=0.0,
            constant=8.6428,
        ),
        "spruce": BarkCoeff(
            inv_diam50=-236.33,
            inv_diam50_sqr=7878.4,
            diam_quotient=0.35929,
            diam_quotient_sqr=0.0,
            age=0.0013589,
            age_sqr=6.2227e-06,
            site_index_pine=-0.0015491,
            latitude=0.028379,
            altitude=0.0,
            lat_alt=0.0,
            prop_pine=0.057123,
            prop_spruce=0.0,
            prop_birch=0.0,
            south_east=0.0,
            region5=0.0,
            area_part=0.020245,
            constant=1.6604,
        ),
        "birch": BarkCoeff(
            inv_diam50=-371.31,
            inv_diam50_sqr=13012.0,
            diam_quotient=0.17146,
            diam_quotient_sqr=0.0,
            age=0.0019655,
            age_sqr=0.0,
            site_index_pine=-0.00071109,
            latitude=0.0086881,
            altitude=0.0,
            lat_alt=6.2991e-06,
            prop_pine=0.18594,
            prop_spruce=0.0,
            prop_birch=0.0,
            south_east=0.0,
            region5=0.0,
            area_part=0.0,
            constant=3.174,
        ),
        "other": BarkCoeff(
            inv_diam50=-175.62,
            inv_diam50_sqr=0.0,
            diam_quotient=0.26968,
            diam_quotient_sqr=0.0,
            age=0.0049609,
            age_sqr=0.0,
            site_index_pine=0.0,
            latitude=0.0,
            altitude=0.0,
            lat_alt=0.0,
            prop_pine=0.0,
            prop_spruce=0.0,
            prop_birch=0.29703,
            south_east=0.0,
            region5=0.0,
            area_part=-0.077013,
            constant=2.8446,
        ),
        "beech": BarkCoeff(
            inv_diam50=-173.87,
            inv_diam50_sqr=0.0,
            diam_quotient=0.1635,
            diam_quotient_sqr=0.0,
            age=0.0022597,
            age_sqr=0.0,
            site_index_pine=0.0,
            latitude=0.0,
            altitude=0.0,
            lat_alt=0.0,
            prop_pine=0.0,
            prop_spruce=0.0,
            prop_birch=0.0,
            south_east=0.0,
            region5=-0.26953,
            area_part=0.0,
            constant=2.4822,
        ),
        "oak": BarkCoeff(
            inv_diam50=-296.05,
            inv_diam50_sqr=8723.5,
            diam_quotient=0.0,
            diam_quotient_sqr=0.0,
            age=0.002268,
            age_sqr=0.0,
            site_index_pine=0.0,
            latitude=0.0,
            altitude=0.0,
            lat_alt=0.0,
            prop_pine=0.0,
            prop_spruce=0.0,
            prop_birch=0.0,
            south_east=-0.24349,
            region5=0.0,
            area_part=0.044474,
            constant=3.9521,
        ),
    },
    "south": {
        "pine": BarkCoeff(
            inv_diam50=-383.6,
            inv_diam50_sqr=13442.0,
            diam_quotient=0.0,
            diam_quotient_sqr=0.0,
            age=0.0020965,
            age_sqr=-8.8795e-06,
            site_index_pine=-0.00074698,
            latitude=0.0,
            altitude=0.010185,
            lat_alt=-0.00017023,
            prop_pine=-0.024281,
            prop_spruce=0.0,
            prop_birch=-0.04923,
            south_east=0.057067,
            region5=0.0,
            area_part=0.024619,
            constant=4.724,
        ),
        "spruce": BarkCoeff(
            inv_diam50=-303.55,
            inv_diam50_sqr=13763.0,
            diam_quotient=0.3023,
            diam_quotient_sqr=0.0,
            age=0.0,
            age_sqr=2.3539e-05,
            site_index_pine=-0.0013014,
            latitude=0.0,
            altitude=-0.010863,
            lat_alt=0.00019027,
            prop_pine=0.068055,
            prop_spruce=-0.10406,
            prop_birch=0.062182,
            south_east=0.0,
            region5=0.0,
            area_part=0.027539,
            constant=3.6138,
        ),
        "birch": BarkCoeff(
            inv_diam50=-647.99,
            inv_diam50_sqr=33167.0,
            diam_quotient=0.13804,
            diam_quotient_sqr=0.0,
            age=0.0014517,
            age_sqr=0.0,
            site_index_pine=-0.00050779,
            latitude=0.0,
            altitude=0.0054445,
            lat_alt=-9.9383e-05,
            prop_pine=0.088745,
            prop_spruce=0.0,
            prop_birch=-0.14772,
            south_east=-0.051335,
            region5=0.0,
            area_part=0.0,
            constant=5.0104,
        ),
        "other": BarkCoeff(
            inv_diam50=-341.44,
            inv_diam50_sqr=9790.0,
            diam_quotient=0.0,
            diam_quotient_sqr=0.0,
            age=0.0031101,
            age_sqr=-2.2562e-05,
            site_index_pine=-0.0021013,
            latitude=0.0,
            altitude=0.0,
            lat_alt=0.0,
            prop_pine=0.0,
            prop_spruce=0.0,
            prop_birch=0.0,
            south_east=0.0,
            region5=0.0,
            area_part=0.0,
            constant=4.5835,
        ),
        "beech": BarkCoeff(
            inv_diam50=-173.87,
            inv_diam50_sqr=0.0,
            diam_quotient=0.1635,
            diam_quotient_sqr=0.0,
            age=0.0022597,
            age_sqr=0.0,
            site_index_pine=0.0,
            latitude=0.0,
            altitude=0.0,
            lat_alt=0.0,
            prop_pine=0.0,
            prop_spruce=0.0,
            prop_birch=0.0,
            south_east=0.0,
            region5=-0.26953,
            area_part=0.0,
            constant=2.4822,
        ),
        "oak": BarkCoeff(
            inv_diam50=-296.05,
            inv_diam50_sqr=8723.5,
            diam_quotient=0.0,
            diam_quotient_sqr=0.0,
            age=0.002268,
            age_sqr=0.0,
            site_index_pine=0.0,
            latitude=0.0,
            altitude=0.0,
            lat_alt=0.0,
            prop_pine=0.0,
            prop_spruce=0.0,
            prop_birch=0.0,
            south_east=-0.24349,
            region5=0.0,
            area_part=0.044474,
            constant=3.9521,
        ),
    },
}

_LOG_BIAS: Dict[str, Dict[str, float]] = {
    "north": {
        "pine": 0.02691,
        "spruce": 0.02808,
        "birch": 0.04292,
        "other": 0.04292,
        "beech": 0.03251,
        "oak": 0.02354,
    },
    "middle": {
        "pine": 0.00262,
        "spruce": 0.02808,
        "birch": 0.04292,
        "other": 0.04292,
        "beech": 0.03251,
        "oak": 0.02354,
    },
    "south": {
        "pine": 0.02832,
        "spruce": 0.03001,
        "birch": 0.04440,
        "other": 0.04440,
        "beech": 0.03251,
        "oak": 0.02354,
    },
}


def _coerce_species(species: Union[TreeName, str]) -> TreeName:
    """Normalize species input to a canonical ``TreeName``."""
    return _coerce_species_shared(species)


def _species_group(species: TreeName) -> str:
    """Resolve Söderberg bark-model species group key."""
    return _species_group_for_soderberg_shared(species, model_name="Söderberg bark model")


def _normalize_part_of_sweden(part_of_sweden: str) -> str:
    """Normalize regional labels to the bark-model north/middle/south keys."""
    return _normalize_part_of_sweden_shared(
        part_of_sweden,
        gotland_alias="south",
        gotland_warning=(
            "Gotland is not parameterized separately for Söderberg (1992) bark thickness; "
            "using southern coefficients."
        ),
        error_message="part_of_sweden must be one of: north, middle, south.",
    )


def _warn_proportion(name: str, value: float) -> None:
    """Emit a warning when a species-proportion input is outside [0, 1]."""
    _warn_proportion_shared(name, value)


def soderberg_1992_bark_thickness_bh_mm(
    *,
    species: Union[TreeName, str],
    diameter_cm: float,
    max_diameter_cm: float,
    mean_age_total_years: float,
    site_index_pine_m: float | SiteIndexValue,
    latitude_deg: float,
    altitude_m: float,
    prop_pine: float,
    prop_spruce: float,
    prop_birch: float,
    part_of_sweden: str,
    south_east: bool = False,
    region5: bool = False,
    split_plot: bool = False,
) -> float:
    """Estimate double bark thickness at breast height (mm) from Söderberg (1992).

    Args:
        species (TreeName | str): Tree species.
        diameter_cm (float): Diameter at breast height, cm (over bark).
        max_diameter_cm (float): Maximum diameter on plot, cm.
        mean_age_total_years (float): Basal-area weighted mean total age, years.
        site_index_pine_m (float | SiteIndexValue): Pine site index (H100), m.
            ``SiteIndexValue`` inputs must be Hagglund (1970) H100 for pine.
        latitude_deg (float): Latitude, degrees.
        altitude_m (float): Altitude, m.
        prop_pine (float): Pine proportion of basal area (0..1).
        prop_spruce (float): Spruce proportion of basal area (0..1).
        prop_birch (float): Birch proportion of basal area (0..1).
        part_of_sweden (str): ``north``, ``middle`` or ``south``.
        south_east (bool): Southeast Sweden indicator.
        region5 (bool): Region 5 indicator.
        split_plot (bool): Split plot indicator (unused by the original model).

    Returns:
        float: Double bark thickness at breast height, mm.

    Raises:
        ValueError: If diameter or max diameter is non-positive.

    References:
        Söderberg, U. (1992). *Functions for forest management. Height, form height
        and bark thickness of individual trees*. Report 52, SLU, Umeå.
    """
    tree_species = _coerce_species(species)
    group = _species_group(tree_species)
    region = _normalize_part_of_sweden(part_of_sweden)

    if diameter_cm < 0:
        raise ValueError("diameter_cm must be non-negative.")
    if max_diameter_cm <= 0:
        raise ValueError("max_diameter_cm must be positive.")
    if mean_age_total_years < 0:
        raise ValueError("mean_age_total_years must be non-negative.")

    if not (55.0 <= latitude_deg <= 70.0):
        warnings.warn(
            f"latitude_deg={latitude_deg} outside typical Sweden range (55-70).",
            stacklevel=2,
        )

    _warn_proportion("prop_pine", prop_pine)
    _warn_proportion("prop_spruce", prop_spruce)
    _warn_proportion("prop_birch", prop_birch)

    if split_plot:
        warnings.warn(
            "split_plot is not used in the published Söderberg (1992) bark thickness equations.",
            stacklevel=2,
        )

    coeff = _BARK_COEFF[region][group]
    log_bias = _LOG_BIAS[region][group]

    area_cm2 = math.pi * (diameter_cm**2) / 4.0
    max_area_cm2 = math.pi * (max_diameter_cm**2) / 4.0
    if max_area_cm2 <= 0:
        raise ValueError("max_diameter_cm must be positive.")

    inv_diam = 1.0 / (diameter_cm * 10.0 + 50.0)
    inv_diam_sqr = inv_diam**2
    diam_quotient_sqr = area_cm2 / max_area_cm2
    diam_quotient = math.sqrt(diam_quotient_sqr)

    site_index_pine_value_m = _normalize_hagglund_h100_site_index_m(
        site_index_pine_m,
        parameter_name="site_index_pine_m",
        expected_species=TreeSpecies.Sweden.pinus_sylvestris,
    )
    site_index_dm = site_index_pine_value_m * 10.0
    p_part = (
        mean_age_total_years * coeff.age
        + (mean_age_total_years**2) * coeff.age_sqr
        + site_index_dm * coeff.site_index_pine
        + latitude_deg * coeff.latitude
        + altitude_m * coeff.altitude
        + latitude_deg * altitude_m * coeff.lat_alt
        + prop_pine * coeff.prop_pine
        + prop_spruce * coeff.prop_spruce
        + prop_birch * coeff.prop_birch
        + (1.0 if south_east else 0.0) * coeff.south_east
        + (1.0 if region5 else 0.0) * coeff.region5
        + coeff.constant
    )

    ln_bark = (
        p_part
        + log_bias
        + inv_diam * coeff.inv_diam50
        + inv_diam_sqr * coeff.inv_diam50_sqr
        + diam_quotient * coeff.diam_quotient
        + diam_quotient_sqr * coeff.diam_quotient_sqr
    )

    bark_mm = math.exp(ln_bark)
    if not math.isfinite(bark_mm) or bark_mm < 0:
        raise ValueError("Computed bark thickness is invalid.")
    return bark_mm


__all__ = ["soderberg_1992_bark_thickness_bh_mm"]


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------


DESCRIPTOR = FormulaDescriptor(
    component_id="soderberg_1992_bark",
    source=SourceReference(
        author="Söderberg, U.",
        year=1992,
        title="Funktioner för skogsbruksplanering",
        note=(
            "Sveriges lantbruksuniversitet, institutionen för skogstaxering, "
            "Rapport nr 52, Umeå. Bark thickness at breast height."
        ),
    ),
    species_groups={},
    units={"diameter_cm": "cm", "return": "mm (double bark)"},
    kernel_names=list(__all__),
)
