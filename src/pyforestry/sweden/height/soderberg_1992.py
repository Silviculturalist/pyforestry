"""Soderberg (1992) single-tree height models for Sweden.

Implements the height equations reported in:

    Söderberg, U. (1992). *Functions for forest management. Height, form height
    and bark thickness of individual trees*. Report 52, SLU, Umeå.

Two variants are provided:
    - Stand-age (mean age) model.
    - Tree-age model.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Dict, Union

from pyforestry.base.helpers.tree_species import TreeName, TreeSpecies
from pyforestry.simulation.contracts import SourceReference
from pyforestry.sweden._model_input_normalization import (
    PINE_GROUP as _PINE_GROUP,
)
from pyforestry.sweden._model_input_normalization import (
    coerce_species as _coerce_species_shared,
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
class StandAgeCoeff:
    """Coefficient set for stand-age height equations."""

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
    coast: float
    south_east: float
    region5: float
    split_plot: float
    intercept: float
    log_bias: float


_STAND_AGE_COEFF: Dict[str, Dict[str, StandAgeCoeff]] = {
    "north": {
        "pine": StandAgeCoeff(
            inv_diam50=-283.9,
            inv_diam50_sqr=6416.8,
            diam_quotient=-0.44962,
            diam_quotient_sqr=0.070355,
            age=0.0063874,
            age_sqr=-3.0707e-05,
            site_index_pine=0.0012774,
            latitude=-0.015597,
            altitude=0.0,
            lat_alt=-4.8527e-06,
            prop_pine=0.08735,
            prop_spruce=0.0,
            prop_birch=0.0,
            coast=-0.072392,
            south_east=0.0,
            region5=0.0,
            split_plot=-0.056157,
            intercept=6.8125,
            log_bias=0.01155,
        ),
        "spruce": StandAgeCoeff(
            inv_diam50=-286.63,
            inv_diam50_sqr=4783.1,
            diam_quotient=-0.19831,
            diam_quotient_sqr=0.0,
            age=0.0031669,
            age_sqr=-1.6854e-05,
            site_index_pine=0.0010855,
            latitude=-0.0099681,
            altitude=0.00051262,
            lat_alt=-1.2449e-05,
            prop_pine=0.060923,
            prop_spruce=0.090784,
            prop_birch=0.0,
            coast=-0.062548,
            south_east=0.0,
            region5=0.0,
            split_plot=-0.030688,
            intercept=6.52,
            log_bias=0.01095,
        ),
        "birch": StandAgeCoeff(
            inv_diam50=-266.07,
            inv_diam50_sqr=7141.5,
            diam_quotient=-0.3925,
            diam_quotient_sqr=0.0765,
            age=0.0032789,
            age_sqr=-2.2514e-05,
            site_index_pine=0.00085255,
            latitude=-0.018462,
            altitude=0.0,
            lat_alt=-7.218e-06,
            prop_pine=-0.074398,
            prop_spruce=-0.022539,
            prop_birch=0.0,
            coast=0.0,
            south_east=0.0,
            region5=0.0,
            split_plot=-0.035918,
            intercept=7.2446,
            log_bias=0.01248,
        ),
        "other": StandAgeCoeff(
            inv_diam50=-145.46,
            inv_diam50_sqr=0.0,
            diam_quotient=0.0,
            diam_quotient_sqr=0.0,
            age=0.0053659,
            age_sqr=-2.9042e-05,
            site_index_pine=0.0017639,
            latitude=-0.0342,
            altitude=0.0,
            lat_alt=0.0,
            prop_pine=0.0,
            prop_spruce=0.075841,
            prop_birch=0.0,
            coast=0.15566,
            south_east=0.0,
            region5=0.0,
            split_plot=-0.082953,
            intercept=7.0706,
            log_bias=0.01248,
        ),
        "beech": StandAgeCoeff(
            inv_diam50=-144.07,
            inv_diam50_sqr=0.0,
            diam_quotient=0.0,
            diam_quotient_sqr=0.0,
            age=0.0072319,
            age_sqr=-2.7244e-05,
            site_index_pine=0.0,
            latitude=0.0,
            altitude=0.0,
            lat_alt=-5.781e-06,
            prop_pine=0.0,
            prop_spruce=0.1804,
            prop_birch=0.0,
            coast=0.0,
            south_east=0.188,
            region5=-0.18416,
            split_plot=-0.1741,
            intercept=5.2974,
            log_bias=0.01296,
        ),
        "oak": StandAgeCoeff(
            inv_diam50=-258.11,
            inv_diam50_sqr=6310.0,
            diam_quotient=-0.32505,
            diam_quotient_sqr=0.0,
            age=0.0,
            age_sqr=0.0,
            site_index_pine=0.0013039,
            latitude=0.0,
            altitude=0.0,
            lat_alt=-4.1543e-06,
            prop_pine=0.0,
            prop_spruce=0.059855,
            prop_birch=0.0,
            coast=0.0,
            south_east=0.17355,
            region5=-0.047987,
            split_plot=-0.069304,
            intercept=5.7884,
            log_bias=0.01584,
        ),
    },
    "middle": {
        "pine": StandAgeCoeff(
            inv_diam50=-292.49,
            inv_diam50_sqr=6183.2,
            diam_quotient=-0.61165,
            diam_quotient_sqr=0.13132,
            age=0.0052675,
            age_sqr=-2.5358e-05,
            site_index_pine=0.0013721,
            latitude=0.069771,
            altitude=0.0058106,
            lat_alt=-0.00010018,
            prop_pine=0.22217,
            prop_spruce=0.24504,
            prop_birch=0.23251,
            coast=-0.10186,
            south_east=0.0,
            region5=0.0,
            split_plot=-0.055749,
            intercept=1.5712,
            log_bias=0.00938,
        ),
        "spruce": StandAgeCoeff(
            inv_diam50=-286.63,
            inv_diam50_sqr=4783.1,
            diam_quotient=-0.19831,
            diam_quotient_sqr=0.0,
            age=0.0031669,
            age_sqr=-1.6854e-05,
            site_index_pine=0.0010855,
            latitude=-0.0099681,
            altitude=0.00051262,
            lat_alt=-1.2449e-05,
            prop_pine=0.060923,
            prop_spruce=0.090784,
            prop_birch=0.0,
            coast=-0.062548,
            south_east=0.0,
            region5=0.0,
            split_plot=-0.030688,
            intercept=6.52,
            log_bias=0.01095,
        ),
        "birch": StandAgeCoeff(
            inv_diam50=-266.07,
            inv_diam50_sqr=7141.5,
            diam_quotient=-0.3925,
            diam_quotient_sqr=0.0765,
            age=0.0032789,
            age_sqr=-2.2514e-05,
            site_index_pine=0.00085255,
            latitude=-0.018462,
            altitude=0.0,
            lat_alt=-7.218e-06,
            prop_pine=-0.074398,
            prop_spruce=-0.022539,
            prop_birch=0.0,
            coast=0.0,
            south_east=0.0,
            region5=0.0,
            split_plot=-0.035918,
            intercept=7.2446,
            log_bias=0.01248,
        ),
        "other": StandAgeCoeff(
            inv_diam50=-145.46,
            inv_diam50_sqr=0.0,
            diam_quotient=0.0,
            diam_quotient_sqr=0.0,
            age=0.0053659,
            age_sqr=-2.9042e-05,
            site_index_pine=0.0017639,
            latitude=-0.0342,
            altitude=0.0,
            lat_alt=0.0,
            prop_pine=0.0,
            prop_spruce=0.075841,
            prop_birch=0.0,
            coast=0.15566,
            south_east=0.0,
            region5=0.0,
            split_plot=-0.082953,
            intercept=7.0706,
            log_bias=0.01248,
        ),
        "beech": StandAgeCoeff(
            inv_diam50=-144.07,
            inv_diam50_sqr=0.0,
            diam_quotient=0.0,
            diam_quotient_sqr=0.0,
            age=0.0072319,
            age_sqr=-2.7244e-05,
            site_index_pine=0.0,
            latitude=0.0,
            altitude=0.0,
            lat_alt=-5.781e-06,
            prop_pine=0.0,
            prop_spruce=0.1804,
            prop_birch=0.0,
            coast=0.0,
            south_east=0.188,
            region5=-0.18416,
            split_plot=-0.1741,
            intercept=5.2974,
            log_bias=0.01296,
        ),
        "oak": StandAgeCoeff(
            inv_diam50=-258.11,
            inv_diam50_sqr=6310.0,
            diam_quotient=-0.32505,
            diam_quotient_sqr=0.0,
            age=0.0,
            age_sqr=0.0,
            site_index_pine=0.0013039,
            latitude=0.0,
            altitude=0.0,
            lat_alt=-4.1543e-06,
            prop_pine=0.0,
            prop_spruce=0.059855,
            prop_birch=0.0,
            coast=0.0,
            south_east=0.17355,
            region5=-0.047987,
            split_plot=-0.069304,
            intercept=5.7884,
            log_bias=0.01584,
        ),
    },
    "south": {
        "pine": StandAgeCoeff(
            inv_diam50=-303.45,
            inv_diam50_sqr=8842.7,
            diam_quotient=0.091429,
            diam_quotient_sqr=-0.28115,
            age=0.0068724,
            age_sqr=-3.8585e-05,
            site_index_pine=0.0016646,
            latitude=0.0,
            altitude=-0.0047335,
            lat_alt=8.2679e-05,
            prop_pine=0.2057,
            prop_spruce=0.29485,
            prop_birch=0.13909,
            coast=-0.19855,
            south_east=0.036444,
            region5=0.0,
            split_plot=-0.060312,
            intercept=5.2706,
            log_bias=0.01264,
        ),
        "spruce": StandAgeCoeff(
            inv_diam50=-274.21,
            inv_diam50_sqr=3801.3,
            diam_quotient=-0.2376,
            diam_quotient_sqr=0.0,
            age=0.0031094,
            age_sqr=-2.0764e-05,
            site_index_pine=0.0010161,
            latitude=0.0,
            altitude=0.0015166,
            lat_alt=-2.5385e-05,
            prop_pine=0.10172,
            prop_spruce=0.24012,
            prop_birch=0.068141,
            coast=-0.069386,
            south_east=0.0,
            region5=0.0,
            split_plot=-0.047848,
            intercept=5.7495,
            log_bias=0.01051,
        ),
        "birch": StandAgeCoeff(
            inv_diam50=-225.52,
            inv_diam50_sqr=3917.1,
            diam_quotient=-0.32296,
            diam_quotient_sqr=0.0,
            age=0.0017264,
            age_sqr=-1.1572e-05,
            site_index_pine=0.00089953,
            latitude=0.0,
            altitude=-0.0090184,
            lat_alt=0.00015804,
            prop_pine=-0.044799,
            prop_spruce=0.11728,
            prop_birch=0.10104,
            coast=0.0,
            south_east=0.047911,
            region5=0.0,
            split_plot=-0.068048,
            intercept=5.782,
            log_bias=0.01901,
        ),
        "other": StandAgeCoeff(
            inv_diam50=-220.78,
            inv_diam50_sqr=5392.0,
            diam_quotient=-0.17045,
            diam_quotient_sqr=0.0,
            age=0.0053701,
            age_sqr=-4.1932e-05,
            site_index_pine=0.00053968,
            latitude=0.0,
            altitude=-0.010758,
            lat_alt=0.00018781,
            prop_pine=-0.17291,
            prop_spruce=0.10783,
            prop_birch=-0.055868,
            coast=0.0,
            south_east=0.0,
            region5=0.0,
            split_plot=-0.05187,
            intercept=5.6569,
            log_bias=0.01901,
        ),
        "beech": StandAgeCoeff(
            inv_diam50=-144.07,
            inv_diam50_sqr=0.0,
            diam_quotient=0.0,
            diam_quotient_sqr=0.0,
            age=0.0072319,
            age_sqr=-2.7244e-05,
            site_index_pine=0.0,
            latitude=0.0,
            altitude=0.0,
            lat_alt=-5.781e-06,
            prop_pine=0.0,
            prop_spruce=0.1804,
            prop_birch=0.0,
            coast=0.0,
            south_east=0.188,
            region5=-0.18416,
            split_plot=-0.1741,
            intercept=5.2974,
            log_bias=0.01296,
        ),
        "oak": StandAgeCoeff(
            inv_diam50=-258.11,
            inv_diam50_sqr=6310.0,
            diam_quotient=-0.32505,
            diam_quotient_sqr=0.0,
            age=0.0,
            age_sqr=0.0,
            site_index_pine=0.0013039,
            latitude=0.0,
            altitude=0.0,
            lat_alt=-4.1543e-06,
            prop_pine=0.0,
            prop_spruce=0.059855,
            prop_birch=0.0,
            coast=0.0,
            south_east=0.17355,
            region5=-0.047987,
            split_plot=-0.069304,
            intercept=5.7884,
            log_bias=0.01584,
        ),
    },
}


@dataclass(frozen=True)
class PineCoeff:
    """Coefficient set for tree-age pine height equation."""

    intercept: float
    inv_diam50: float
    inv_diam50_sqr: float
    inv_age10: float
    inv_age10_sqr: float
    age: float
    diam_by_age: float
    sis_spruce: float
    sis_pine: float
    ba_total: float
    ba_total_sqr: float
    diam_ratio: float
    diam_ratio_sqr: float
    latitude: float
    latitude_sqr: float
    altitude: float
    altitude_sqr: float
    prop_pine: float
    prop_spruce: float
    prop_birch: float
    close_to_coast: float
    split_plot: float
    maritime: float
    south_east: float
    region5: float
    bias: float


@dataclass(frozen=True)
class SpruceCoeff:
    """Coefficient set for tree-age spruce height equation."""

    intercept: float
    inv_diam50: float
    inv_diam50_sqr: float
    inv_age10: float
    inv_age10_sqr: float
    age: float
    diam_by_age: float
    sis_spruce: float
    sis_pine: float
    ba_total: float
    ba_total_sqr: float
    diam_ratio: float
    diam_ratio_sqr: float
    latitude_sqr: float
    altitude: float
    altitude_sqr: float
    prop_pine: float
    prop_spruce: float
    close_to_coast: float
    continental: float
    split_plot: float
    maritime: float
    south_east: float
    bias: float


@dataclass(frozen=True)
class BirchCoeff:
    """Coefficient set for tree-age birch height equation."""

    intercept: float
    inv_diam50: float
    inv_diam50_sqr: float
    inv_age10: float
    inv_age10_sqr: float
    diam_by_age: float
    sis_spruce: float
    sis_pine: float
    ba_total: float
    ba_total_sqr: float
    diam_ratio: float
    diam_ratio_sqr: float
    latitude: float
    altitude: float
    altitude_sqr: float
    lat_alt: float
    prop_pine: float
    prop_spruce: float
    prop_birch: float
    split_plot: float
    maritime: float
    region5: float
    bias: float


@dataclass(frozen=True)
class DeciduousCoeff:
    """Coefficient set for tree-age other-deciduous height equation."""

    intercept: float
    inv_diam50: float
    inv_diam50_sqr: float
    inv_age10: float
    inv_age10_sqr: float
    age: float
    sis_spruce: float
    sis_pine: float
    ba_total: float
    ba_total_sqr: float
    diam_ratio: float
    diam_ratio_sqr: float
    latitude: float
    prop_pine: float
    prop_spruce: float
    maritime: float
    split_plot: float
    close_to_coast: float
    bias: float


@dataclass(frozen=True)
class BeechCoeff:
    """Coefficient set for tree-age beech height equation."""

    intercept: float
    inv_diam50: float
    inv_age10: float
    inv_age10_sqr: float
    sis_spruce: float
    ba_total: float
    ba_total_sqr: float
    diam_ratio: float
    diam_ratio_sqr: float
    altitude_sqr: float
    prop_beech: float
    split_plot: float
    region5: float
    bias: float


@dataclass(frozen=True)
class OakCoeff:
    """Coefficient set for tree-age oak height equation."""

    intercept: float
    inv_diam50: float
    inv_diam50_sqr: float
    age: float
    diam_by_age: float
    sis_spruce: float
    sis_pine: float
    ba_total: float
    ba_total_sqr: float
    diam_ratio_sqr: float
    altitude: float
    prop_beech: float
    split_plot: float
    region5: float
    bias: float


_TREE_AGE_COEFF: Dict[
    str, Dict[str, Union[PineCoeff, SpruceCoeff, BirchCoeff, DeciduousCoeff]]
] = {
    "north": {
        "pine": PineCoeff(
            intercept=-8.2981,
            inv_diam50=-279.95,
            inv_diam50_sqr=6781.6,
            inv_age10=-8.0059,
            inv_age10_sqr=100.56,
            age=-0.001899,
            diam_by_age=-0.066679,
            sis_spruce=0.0014751,
            sis_pine=0.0014142,
            ba_total=0.011473,
            ba_total_sqr=-0.00012937,
            diam_ratio=-0.15622,
            diam_ratio_sqr=0.02292,
            latitude=0.45084,
            latitude_sqr=-0.0035449,
            altitude=0.0,
            altitude_sqr=-2.0261e-07,
            prop_pine=0.12172,
            prop_spruce=0.063897,
            prop_birch=0.0,
            close_to_coast=-0.026745,
            split_plot=-0.047547,
            maritime=-0.016487,
            south_east=0.0,
            region5=0.0,
            bias=0.00819,
        ),
        "spruce": SpruceCoeff(
            intercept=6.1585,
            inv_diam50=-289.27,
            inv_diam50_sqr=5276.2,
            inv_age10=-4.5821,
            inv_age10_sqr=136.0,
            age=-0.0010807,
            diam_by_age=-0.038071,
            sis_spruce=0.0007429,
            sis_pine=0.00058052,
            ba_total=0.011361,
            ba_total_sqr=-0.00010922,
            diam_ratio=0.28029,
            diam_ratio_sqr=-0.2406,
            latitude_sqr=-7.1695e-05,
            altitude=0.00011744,
            altitude_sqr=-5.6669e-07,
            prop_pine=0.095561,
            prop_spruce=0.087584,
            close_to_coast=-0.041899,
            continental=0.013342,
            split_plot=-0.03918,
            maritime=0.0,
            south_east=0.0,
            bias=0.00832,
        ),
        "birch": BirchCoeff(
            intercept=6.4427,
            inv_diam50=-229.19,
            inv_diam50_sqr=4898.6,
            inv_age10=5.2925,
            inv_age10_sqr=0.0,
            diam_by_age=-0.039008,
            sis_spruce=0.00096299,
            sis_pine=0.00083824,
            ba_total=0.016511,
            ba_total_sqr=-0.00017611,
            diam_ratio=-0.087603,
            diam_ratio_sqr=0.025864,
            latitude=-0.013252,
            altitude=-0.00010123,
            altitude_sqr=-4.613e-07,
            lat_alt=0.0,
            prop_pine=-0.040542,
            prop_spruce=-0.056039,
            prop_birch=0.0,
            split_plot=-0.049758,
            maritime=0.0,
            region5=0.0,
            bias=0.01008,
        ),
        "other": DeciduousCoeff(
            intercept=6.3675,
            inv_diam50=-109.49,
            inv_diam50_sqr=0.0,
            inv_age10=-20.419,
            inv_age10_sqr=229.66,
            age=-0.0021025,
            sis_spruce=0.0011182,
            sis_pine=0.0012554,
            ba_total=0.017302,
            ba_total_sqr=-0.00016525,
            diam_ratio=0.64313,
            diam_ratio_sqr=-0.34368,
            latitude=-0.023565,
            prop_pine=0.10443,
            prop_spruce=0.11788,
            maritime=0.02636,
            split_plot=-0.053057,
            close_to_coast=0.13323,
            bias=0.01602,
        ),
    },
    "middle": {
        "pine": PineCoeff(
            intercept=-81.303,
            inv_diam50=-285.36,
            inv_diam50_sqr=7523.3,
            inv_age10=-10.295,
            inv_age10_sqr=119.34,
            age=-0.0018296,
            diam_by_age=-0.040078,
            sis_spruce=0.0011538,
            sis_pine=0.0013061,
            ba_total=0.011572,
            ba_total_sqr=-0.00011765,
            diam_ratio=-0.24016,
            diam_ratio_sqr=0.063405,
            latitude=2.8478,
            latitude_sqr=-0.023177,
            altitude=0.0,
            altitude_sqr=-4.414e-07,
            prop_pine=0.0,
            prop_spruce=0.029354,
            prop_birch=0.0,
            close_to_coast=-0.03701,
            split_plot=-0.053233,
            maritime=-0.050755,
            south_east=0.0,
            region5=0.0,
            bias=0.00673,
        ),
        "spruce": SpruceCoeff(
            intercept=6.1585,
            inv_diam50=-289.27,
            inv_diam50_sqr=5276.2,
            inv_age10=-4.5821,
            inv_age10_sqr=136.0,
            age=-0.0010807,
            diam_by_age=-0.038071,
            sis_spruce=0.0007429,
            sis_pine=0.00058052,
            ba_total=0.011361,
            ba_total_sqr=-0.00010922,
            diam_ratio=0.28029,
            diam_ratio_sqr=-0.2406,
            latitude_sqr=-7.1695e-05,
            altitude=0.00011744,
            altitude_sqr=-5.6669e-07,
            prop_pine=0.095561,
            prop_spruce=0.087584,
            close_to_coast=-0.041899,
            continental=0.013342,
            split_plot=-0.03918,
            maritime=0.0,
            south_east=0.0,
            bias=0.00832,
        ),
        "birch": BirchCoeff(
            intercept=6.4427,
            inv_diam50=-229.19,
            inv_diam50_sqr=4898.6,
            inv_age10=5.2925,
            inv_age10_sqr=0.0,
            diam_by_age=-0.039008,
            sis_spruce=0.00096299,
            sis_pine=0.00083824,
            ba_total=0.016511,
            ba_total_sqr=-0.00017611,
            diam_ratio=-0.087603,
            diam_ratio_sqr=0.025864,
            latitude=-0.013252,
            altitude=-0.00010123,
            altitude_sqr=-4.613e-07,
            lat_alt=0.0,
            prop_pine=-0.040542,
            prop_spruce=-0.056039,
            prop_birch=0.0,
            split_plot=-0.049758,
            maritime=0.0,
            region5=0.0,
            bias=0.01008,
        ),
        "other": DeciduousCoeff(
            intercept=6.3675,
            inv_diam50=-109.49,
            inv_diam50_sqr=0.0,
            inv_age10=-20.419,
            inv_age10_sqr=229.66,
            age=-0.0021025,
            sis_spruce=0.0011182,
            sis_pine=0.0012554,
            ba_total=0.017302,
            ba_total_sqr=-0.00016525,
            diam_ratio=0.64313,
            diam_ratio_sqr=-0.34368,
            latitude=-0.023565,
            prop_pine=0.10443,
            prop_spruce=0.11788,
            maritime=0.02636,
            split_plot=-0.053057,
            close_to_coast=0.13323,
            bias=0.01602,
        ),
    },
    "south": {
        "pine": PineCoeff(
            intercept=14.687,
            inv_diam50=-328.24,
            inv_diam50_sqr=10788.0,
            inv_age10=-10.143,
            inv_age10_sqr=114.51,
            age=-0.0030959,
            diam_by_age=-0.04905,
            sis_spruce=0.0013824,
            sis_pine=0.0017327,
            ba_total=0.0095731,
            ba_total_sqr=-9.5444e-05,
            diam_ratio=0.2106,
            diam_ratio_sqr=-0.21919,
            latitude=-0.3043,
            latitude_sqr=0.0026409,
            altitude=-5.9174e-05,
            altitude_sqr=0.0,
            prop_pine=0.14785,
            prop_spruce=0.24375,
            prop_birch=0.12387,
            close_to_coast=0.0,
            split_plot=-0.060927,
            maritime=-0.02554,
            south_east=0.0151,
            region5=-0.042302,
            bias=0.00819,
        ),
        "spruce": SpruceCoeff(
            intercept=6.0404,
            inv_diam50=-330.48,
            inv_diam50_sqr=7301.5,
            inv_age10=-2.4683,
            inv_age10_sqr=96.352,
            age=-0.0020097,
            diam_by_age=-0.049498,
            sis_spruce=0.00092562,
            sis_pine=0.0010289,
            ba_total=0.0077592,
            ba_total_sqr=-6.8334e-05,
            diam_ratio=0.38474,
            diam_ratio_sqr=-0.3426,
            latitude_sqr=0.0,
            altitude=0.00033536,
            altitude_sqr=-1.0375e-06,
            prop_pine=0.024412,
            prop_spruce=0.13087,
            close_to_coast=0.0,
            continental=0.020959,
            split_plot=-0.043684,
            maritime=-0.016755,
            south_east=0.018975,
            bias=0.00769,
        ),
        "birch": BirchCoeff(
            intercept=4.6194,
            inv_diam50=-216.24,
            inv_diam50_sqr=4768.3,
            inv_age10=0.0,
            inv_age10_sqr=-14.308,
            diam_by_age=-0.010377,
            sis_spruce=0.00057275,
            sis_pine=0.00070769,
            ba_total=0.012258,
            ba_total_sqr=-0.00014025,
            diam_ratio=0.15315,
            diam_ratio_sqr=-0.2544,
            latitude=0.016736,
            altitude=0.0,
            altitude_sqr=0.0,
            lat_alt=-3.5533e-06,
            prop_pine=-0.046067,
            prop_spruce=0.077659,
            prop_birch=0.081706,
            split_plot=-0.069576,
            maritime=-0.059341,
            region5=-0.041456,
            bias=0.01638,
        ),
        "other": DeciduousCoeff(
            intercept=3.9136,
            inv_diam50=-217.37,
            inv_diam50_sqr=6636.0,
            inv_age10=0.0,
            inv_age10_sqr=-39.007,
            age=0.0,
            sis_spruce=0.00080255,
            sis_pine=0.00076595,
            ba_total=0.010224,
            ba_total_sqr=-9.4866e-05,
            diam_ratio=0.26833,
            diam_ratio_sqr=-0.30654,
            latitude=0.024865,
            prop_pine=0.0,
            prop_spruce=0.093169,
            maritime=-0.029612,
            split_plot=0.0,
            close_to_coast=-0.067029,
            bias=0.01638,
        ),
    },
}

_BEECH_COEFF = BeechCoeff(
    intercept=5.6648,
    inv_diam50=-128.84,
    inv_age10=-21.199,
    inv_age10_sqr=210.53,
    sis_spruce=0.00015372,
    ba_total=0.0097506,
    ba_total_sqr=-9.029e-05,
    diam_ratio=-0.39544,
    diam_ratio_sqr=0.29474,
    altitude_sqr=-1.728e-06,
    prop_beech=0.15103,
    split_plot=-0.13339,
    region5=0.097831,
    bias=0.0114,
)

_OAK_COEFF = OakCoeff(
    intercept=5.6224,
    inv_diam50=-247.48,
    inv_diam50_sqr=6119.9,
    age=-0.0016569,
    diam_by_age=-0.016744,
    sis_spruce=0.00099719,
    sis_pine=0.0011754,
    ba_total=0.01096,
    ba_total_sqr=-0.00010344,
    diam_ratio_sqr=-0.11226,
    altitude=-0.00023866,
    prop_beech=0.16577,
    split_plot=-0.10511,
    region5=-0.054901,
    bias=0.01462,
)


def _coerce_species(species: Union[TreeName, str]) -> TreeName:
    """Normalize species input to a canonical ``TreeName``."""
    return _coerce_species_shared(species)


def _species_group(species: TreeName) -> str:
    """Resolve Söderberg height-model species group key."""
    return _species_group_for_soderberg_shared(species, model_name="Söderberg height model")


def _normalize_part_of_sweden(part_of_sweden: str, *, allow_gotland: bool = False) -> str:
    """Normalize regional labels to north/middle/south(+optional gotland)."""
    return _normalize_part_of_sweden_shared(
        part_of_sweden,
        allow_gotland=allow_gotland,
        gotland_alias="south",
        gotland_warning=(
            "Gotland is not parameterized separately for Söderberg (1992) height models; "
            "using southern coefficients."
        ),
        error_message="part_of_sweden must be one of: north, middle, south.",
    )


def _warn_proportion(name: str, value: float) -> None:
    """Emit a warning when a species-proportion input is outside [0, 1]."""
    _warn_proportion_shared(name, value)


def soderberg_1992_height_stand_age_m(
    *,
    species: Union[TreeName, str],
    diameter_cm: float,
    max_diameter_cm: float,
    mean_age_total_years: float,
    site_index_pine_m: float,
    latitude_deg: float,
    altitude_m: float,
    prop_pine: float,
    prop_spruce: float,
    prop_birch: float,
    part_of_sweden: str,
    near_coast: bool = False,
    south_east: bool = False,
    region5: bool = False,
    split_plot: bool = False,
) -> float:
    """Stand-age height model (m) from Söderberg (1992).

    Args:
        species (TreeName | str): Tree species.
        diameter_cm (float): Diameter at breast height, cm.
        max_diameter_cm (float): Maximum diameter on plot, cm.
        mean_age_total_years (float): Mean total age (years).
        site_index_pine_m (float): Pine site index (H100), m.
        latitude_deg (float): Latitude, degrees.
        altitude_m (float): Altitude, m.
        prop_pine (float): Pine proportion of basal area (0..1).
        prop_spruce (float): Spruce proportion of basal area (0..1).
        prop_birch (float): Birch proportion of basal area (0..1).
        part_of_sweden (str): ``north``, ``middle`` or ``south``.
        near_coast (bool): Near-coast indicator (<50 km).
        south_east (bool): Southeast Sweden indicator.
        region5 (bool): Region 5 indicator.
        split_plot (bool): Split plot indicator.

    Returns:
        float: Tree height, m.
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

    coeff = _STAND_AGE_COEFF[region][group]

    # Clamp age at the optimum if quadratic term exists.
    if coeff.age_sqr != 0:
        age_used = min(mean_age_total_years, -0.5 * coeff.age / coeff.age_sqr)
    else:
        age_used = mean_age_total_years

    site_index_dm = site_index_pine_m * 10.0
    common = (
        age_used * coeff.age
        + (age_used**2) * coeff.age_sqr
        + site_index_dm * coeff.site_index_pine
        + latitude_deg * coeff.latitude
        + altitude_m * coeff.altitude
        + latitude_deg * altitude_m * coeff.lat_alt
        + prop_pine * coeff.prop_pine
        + prop_spruce * coeff.prop_spruce
        + prop_birch * coeff.prop_birch
        + (1.0 if near_coast else 0.0) * coeff.coast
        + (1.0 if south_east else 0.0) * coeff.south_east
        + (1.0 if region5 else 0.0) * coeff.region5
        + (1.0 if split_plot else 0.0) * coeff.split_plot
        + coeff.intercept
        + coeff.log_bias
    )

    inv_diam = 1.0 / (diameter_cm * 10.0 + 50.0)
    inv_diam_sqr = inv_diam**2
    diam_ratio = min(diameter_cm / max_diameter_cm, 1.0)
    diam_ratio_sqr = diam_ratio**2

    ln_height = (
        common
        + inv_diam * coeff.inv_diam50
        + inv_diam_sqr * coeff.inv_diam50_sqr
        + diam_ratio * coeff.diam_quotient
        + diam_ratio_sqr * coeff.diam_quotient_sqr
    )
    height_dm = math.exp(ln_height)
    height_m = height_dm / 10.0
    if not math.isfinite(height_m) or height_m < 0:
        raise ValueError("Computed height is invalid.")
    return height_m


def soderberg_1992_height_tree_age_m(
    *,
    species: Union[TreeName, str],
    diameter_cm: float,
    tree_age_bh_years: float,
    max_diameter_cm: float,
    stand_basal_area_m2_ha: float,
    dominant_species: Union[TreeName, str],
    site_index_dominant_m: float,
    latitude_deg: float,
    altitude_m: float,
    prop_pine: float,
    prop_spruce: float,
    prop_birch: float,
    prop_beech: float = 0.0,
    part_of_sweden: str = "south",
    maritime: bool = False,
    continental: bool = False,
    near_coast: bool = False,
    south_east: bool = False,
    region5: bool = False,
    split_plot: bool = False,
) -> float:
    """Tree-age height model (m) from Söderberg (1992).

    Args:
        species (TreeName | str): Tree species.
        diameter_cm (float): Diameter at breast height, cm.
        tree_age_bh_years (float): Age at breast height, years.
        max_diameter_cm (float): Maximum diameter on plot, cm.
        stand_basal_area_m2_ha (float): Stand basal area, m²/ha (clamped to 80).
        dominant_species (TreeName | str): Dominant species for site index.
        site_index_dominant_m (float): Dominant site index (H100), m.
        latitude_deg (float): Latitude, degrees.
        altitude_m (float): Altitude, m.
        prop_pine (float): Pine proportion of basal area (0..1).
        prop_spruce (float): Spruce proportion of basal area (0..1).
        prop_birch (float): Birch proportion of basal area (0..1).
        prop_beech (float): Beech proportion of basal area (0..1).
        part_of_sweden (str): ``north``, ``middle`` or ``south``.
        maritime (bool): Maritime climate indicator.
        continental (bool): Continental climate indicator.
        near_coast (bool): Distance-to-coast < 50 km indicator.
        south_east (bool): Southeast Sweden indicator.
        region5 (bool): Region 5 indicator.
        split_plot (bool): Split plot indicator.

    Returns:
        float: Tree height, m.
    """
    tree_species = _coerce_species(species)
    group = _species_group(tree_species)
    region = _normalize_part_of_sweden(part_of_sweden)

    dom_species = _coerce_species(dominant_species)
    dom_is_pine = dom_species in _PINE_GROUP

    if diameter_cm < 0:
        raise ValueError("diameter_cm must be non-negative.")
    if max_diameter_cm <= 0:
        raise ValueError("max_diameter_cm must be positive.")
    if tree_age_bh_years < 0:
        raise ValueError("tree_age_bh_years must be non-negative.")

    if not (55.0 <= latitude_deg <= 70.0):
        warnings.warn(
            f"latitude_deg={latitude_deg} outside typical Sweden range (55-70).",
            stacklevel=2,
        )

    _warn_proportion("prop_pine", prop_pine)
    _warn_proportion("prop_spruce", prop_spruce)
    _warn_proportion("prop_birch", prop_birch)
    _warn_proportion("prop_beech", prop_beech)

    age = max(2.0, tree_age_bh_years)
    diameter_mm = diameter_cm * 10.0
    inv_diam = 1.0 / (diameter_mm + 50.0)
    inv_diam_sqr = inv_diam**2
    inv_age = 1.0 / (age + 10.0)
    inv_age_sqr = inv_age**2
    diam_by_age = diameter_mm / age
    diam_ratio = diameter_cm / max_diameter_cm
    diam_ratio_sqr = diam_ratio**2

    ba_total = min(80.0, stand_basal_area_m2_ha)
    ba_total_sqr = ba_total**2

    sis_pine = site_index_dominant_m * 10.0 if dom_is_pine else 0.0
    sis_spruce = 0.0 if dom_is_pine else site_index_dominant_m * 10.0

    if group == "pine":
        coeff = _TREE_AGE_COEFF[region]["pine"]
        if tree_species is TreeSpecies.Sweden.pinus_contorta:
            sis_pine_use = sis_pine + (30.0 if sis_pine > 0 else 0.0)
            sis_spruce_use = sis_spruce + (30.0 if sis_spruce > 0 else 0.0)
        else:
            sis_pine_use = sis_pine
            sis_spruce_use = sis_spruce
        height_ln = (
            coeff.intercept
            + inv_diam * coeff.inv_diam50
            + inv_diam_sqr * coeff.inv_diam50_sqr
            + inv_age * coeff.inv_age10
            + inv_age_sqr * coeff.inv_age10_sqr
            + age * coeff.age
            + diam_by_age * coeff.diam_by_age
            + sis_spruce_use * coeff.sis_spruce
            + sis_pine_use * coeff.sis_pine
            + ba_total * coeff.ba_total
            + ba_total_sqr * coeff.ba_total_sqr
            + diam_ratio * coeff.diam_ratio
            + diam_ratio_sqr * coeff.diam_ratio_sqr
            + latitude_deg * coeff.latitude
            + (latitude_deg**2) * coeff.latitude_sqr
            + altitude_m * coeff.altitude
            + (altitude_m**2) * coeff.altitude_sqr
            + prop_pine * coeff.prop_pine
            + prop_spruce * coeff.prop_spruce
            + prop_birch * coeff.prop_birch
            + (1.0 if near_coast else 0.0) * coeff.close_to_coast
            + (1.0 if split_plot else 0.0) * coeff.split_plot
            + (1.0 if maritime else 0.0) * coeff.maritime
            + (1.0 if south_east else 0.0) * coeff.south_east
            + (1.0 if region5 else 0.0) * coeff.region5
            + coeff.bias
        )
    elif group == "spruce":
        coeff = _TREE_AGE_COEFF[region]["spruce"]
        height_ln = (
            coeff.intercept
            + inv_diam * coeff.inv_diam50
            + inv_diam_sqr * coeff.inv_diam50_sqr
            + inv_age * coeff.inv_age10
            + inv_age_sqr * coeff.inv_age10_sqr
            + age * coeff.age
            + diam_by_age * coeff.diam_by_age
            + sis_spruce * coeff.sis_spruce
            + sis_pine * coeff.sis_pine
            + ba_total * coeff.ba_total
            + ba_total_sqr * coeff.ba_total_sqr
            + diam_ratio * coeff.diam_ratio
            + diam_ratio_sqr * coeff.diam_ratio_sqr
            + (latitude_deg**2) * coeff.latitude_sqr
            + altitude_m * coeff.altitude
            + (altitude_m**2) * coeff.altitude_sqr
            + prop_pine * coeff.prop_pine
            + prop_spruce * coeff.prop_spruce
            + (1.0 if near_coast else 0.0) * coeff.close_to_coast
            + (1.0 if continental else 0.0) * coeff.continental
            + (1.0 if split_plot else 0.0) * coeff.split_plot
            + (1.0 if maritime else 0.0) * coeff.maritime
            + (1.0 if south_east else 0.0) * coeff.south_east
            + coeff.bias
        )
    elif group == "birch":
        coeff = _TREE_AGE_COEFF[region]["birch"]
        height_ln = (
            coeff.intercept
            + inv_diam * coeff.inv_diam50
            + inv_diam_sqr * coeff.inv_diam50_sqr
            + inv_age * coeff.inv_age10
            + inv_age_sqr * coeff.inv_age10_sqr
            + diam_by_age * coeff.diam_by_age
            + sis_spruce * coeff.sis_spruce
            + sis_pine * coeff.sis_pine
            + ba_total * coeff.ba_total
            + ba_total_sqr * coeff.ba_total_sqr
            + diam_ratio * coeff.diam_ratio
            + diam_ratio_sqr * coeff.diam_ratio_sqr
            + latitude_deg * coeff.latitude
            + altitude_m * coeff.altitude
            + (altitude_m**2) * coeff.altitude_sqr
            + (latitude_deg * altitude_m) * coeff.lat_alt
            + prop_pine * coeff.prop_pine
            + prop_spruce * coeff.prop_spruce
            + prop_birch * coeff.prop_birch
            + (1.0 if split_plot else 0.0) * coeff.split_plot
            + (1.0 if maritime else 0.0) * coeff.maritime
            + (1.0 if region5 else 0.0) * coeff.region5
            + coeff.bias
        )
    elif group == "beech":
        coeff = _BEECH_COEFF
        height_ln = (
            coeff.intercept
            + inv_diam * coeff.inv_diam50
            + inv_age * coeff.inv_age10
            + inv_age_sqr * coeff.inv_age10_sqr
            + sis_spruce * coeff.sis_spruce
            + ba_total * coeff.ba_total
            + ba_total_sqr * coeff.ba_total_sqr
            + diam_ratio * coeff.diam_ratio
            + diam_ratio_sqr * coeff.diam_ratio_sqr
            + (altitude_m**2) * coeff.altitude_sqr
            + prop_beech * coeff.prop_beech
            + (1.0 if split_plot else 0.0) * coeff.split_plot
            + (1.0 if region5 else 0.0) * coeff.region5
            + coeff.bias
        )
    elif group == "oak":
        coeff = _OAK_COEFF
        height_ln = (
            coeff.intercept
            + inv_diam * coeff.inv_diam50
            + inv_diam_sqr * coeff.inv_diam50_sqr
            + age * coeff.age
            + diam_by_age * coeff.diam_by_age
            + sis_spruce * coeff.sis_spruce
            + sis_pine * coeff.sis_pine
            + ba_total * coeff.ba_total
            + ba_total_sqr * coeff.ba_total_sqr
            + diam_ratio_sqr * coeff.diam_ratio_sqr
            + altitude_m * coeff.altitude
            + prop_beech * coeff.prop_beech
            + (1.0 if split_plot else 0.0) * coeff.split_plot
            + (1.0 if region5 else 0.0) * coeff.region5
            + coeff.bias
        )
    else:
        coeff = _TREE_AGE_COEFF[region]["other"]
        height_ln = (
            coeff.intercept
            + inv_diam * coeff.inv_diam50
            + inv_diam_sqr * coeff.inv_diam50_sqr
            + inv_age * coeff.inv_age10
            + inv_age_sqr * coeff.inv_age10_sqr
            + age * coeff.age
            + sis_spruce * coeff.sis_spruce
            + sis_pine * coeff.sis_pine
            + ba_total * coeff.ba_total
            + ba_total_sqr * coeff.ba_total_sqr
            + diam_ratio * coeff.diam_ratio
            + diam_ratio_sqr * coeff.diam_ratio_sqr
            + latitude_deg * coeff.latitude
            + prop_pine * coeff.prop_pine
            + prop_spruce * coeff.prop_spruce
            + (1.0 if maritime else 0.0) * coeff.maritime
            + (1.0 if split_plot else 0.0) * coeff.split_plot
            + (1.0 if near_coast else 0.0) * coeff.close_to_coast
            + coeff.bias
        )

    height_dm = math.exp(height_ln)
    height_m = height_dm / 10.0
    if not math.isfinite(height_m) or height_m < 0:
        raise ValueError("Computed height is invalid.")
    return height_m


__all__ = ["soderberg_1992_height_stand_age_m", "soderberg_1992_height_tree_age_m"]


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------


class _Descriptor:
    """FormulaModuleDescriptor for Soderberg (1992) height functions."""

    @property
    def component_id(self):
        return "soderberg_1992_height"

    @property
    def source(self):
        return SourceReference(
            author="Söderberg, U.",
            year=1992,
            title="Funktioner för skogsbruksplanering",
            note=(
                "Sveriges lantbruksuniversitet, institutionen för skogstaxering, "
                "Rapport nr 52, Umeå. Height, form height and bark thickness of "
                "individual trees."
            ),
        )

    @property
    def species_groups(self):
        return {}

    @property
    def units(self):
        return {"diameter_cm": "cm", "age_years": "years", "return": "m"}

    @property
    def kernel_names(self):
        return list(__all__)


DESCRIPTOR = _Descriptor()
