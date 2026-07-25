"""Soderberg (1986) form height and volume for Swedish trees.

Implements the form height model used by Söderberg (1986) for individual trees.
Form height is returned in metres, and volume follows from V = basal area x form
height. With basal area in cm^2 and form height in m:

    volume_m3 = form_height_m * basal_area_cm2 / 10000

Source:
    Söderberg, U. (1986). *Funktioner för skogliga produktionsprognoser -
    Tillväxt och formhöjd för enskilda träd av inhemska trädslag i Sverige*.
    Report 14, SLU, Umeå.
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
    PINE_GROUP as _PINE_GROUP,
)
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
class FormHeightCoeff:
    """Coefficient set for Söderberg (1986) form-height equations."""

    inv_diam50: float
    inv_diam50_sqr: float
    inv_age10: float
    inv_age10_sqr: float
    age: float
    diam_by_age: float
    site_index_spruce: float
    site_index_pine: float
    basal_area: float
    basal_area_sqr: float
    diam_ratio: float
    diam_ratio_sqr: float
    latitude: float
    latitude_sqr: float
    altitude_sqr: float
    altitude: float
    coast: float
    split_plot: float
    crowberry: float
    south_slope: float
    wet: float
    prop_pine: float
    prop_spruce: float
    fertilized: float
    herbs: float
    maritime: float
    region5: float
    continental: float
    north_slope: float
    dry: float
    south_east: float
    groundwater_never: float
    prop_birch: float
    prop_beech: float
    prop_oak: float
    lat_alt: float
    constant: float


_FORM_HEIGHT_COEFF: Dict[str, Dict[str, FormHeightCoeff]] = {
    "north": {
        "pine": FormHeightCoeff(
            inv_diam50=-227.98803,
            inv_diam50_sqr=6689.5701,
            inv_age10=-11.348548,
            inv_age10_sqr=172.05382,
            age=-0.0016672173,
            diam_by_age=-0.058581498,
            site_index_spruce=0.0011750416,
            site_index_pine=0.0011099238,
            basal_area=0.0097337562,
            basal_area_sqr=-9.2806971e-05,
            diam_ratio=-0.09413394,
            diam_ratio_sqr=0.011759694,
            latitude=0.43779427,
            latitude_sqr=-0.0034411219,
            altitude_sqr=-1.9820202e-07,
            altitude=0.0,
            coast=-0.020822884,
            split_plot=-0.04476601,
            crowberry=-0.019262235,
            south_slope=0.020471352,
            wet=-0.018321329,
            prop_pine=0.088735433,
            prop_spruce=0.04395428,
            fertilized=0.0,
            herbs=0.0,
            maritime=0.0,
            region5=0.0,
            continental=0.0,
            north_slope=0.0,
            dry=0.0,
            south_east=0.0,
            groundwater_never=0.0,
            prop_birch=0.0,
            prop_beech=0.0,
            prop_oak=0.0,
            lat_alt=0.0,
            constant=-11.064,
        ),
        "spruce": FormHeightCoeff(
            inv_diam50=-228.6012,
            inv_diam50_sqr=4876.6746,
            inv_age10=-8.1994843,
            inv_age10_sqr=176.12717,
            age=-0.0013356206,
            diam_by_age=-0.040995766,
            site_index_spruce=0.00073529265,
            site_index_pine=0.00055196518,
            basal_area=0.011655487,
            basal_area_sqr=-0.00010072886,
            diam_ratio=0.43924452,
            diam_ratio_sqr=-0.36955966,
            latitude=-0.010854906,
            latitude_sqr=0.0,
            altitude_sqr=-6.3245695e-07,
            altitude=0.00010400941,
            coast=-0.046334655,
            split_plot=-0.046181965,
            crowberry=0.0,
            south_slope=0.0,
            wet=-0.01012388,
            prop_pine=0.088430152,
            prop_spruce=0.089762728,
            fertilized=0.0,
            herbs=-0.011448152,
            maritime=0.0,
            region5=0.0,
            continental=0.011848882,
            north_slope=0.020148289,
            dry=-0.032980617,
            south_east=0.0,
            groundwater_never=-0.011366288,
            prop_birch=0.0,
            prop_beech=0.0,
            prop_oak=0.0,
            lat_alt=0.0,
            constant=3.3239569,
        ),
        "birch": FormHeightCoeff(
            inv_diam50=-187.79692,
            inv_diam50_sqr=4126.3542,
            inv_age10=4.9070641,
            inv_age10_sqr=0.0,
            age=0.0,
            diam_by_age=-0.038410276,
            site_index_spruce=0.00073517342,
            site_index_pine=0.00058577236,
            basal_area=0.016827143,
            basal_area_sqr=-0.00017157801,
            diam_ratio=-0.032079477,
            diam_ratio_sqr=0.0,
            latitude=-0.017385541,
            latitude_sqr=0.0,
            altitude_sqr=-4.4756402e-07,
            altitude=-0.00014858132,
            coast=0.0,
            split_plot=-0.054917452,
            crowberry=-0.095882304,
            south_slope=0.0,
            wet=-0.024337689,
            prop_pine=-0.042524039,
            prop_spruce=-0.060774144,
            fertilized=0.065036414,
            herbs=0.0,
            maritime=0.0,
            region5=0.0,
            continental=0.0,
            north_slope=0.0,
            dry=-0.062793228,
            south_east=0.0,
            groundwater_never=-0.017655774,
            prop_birch=0.0,
            prop_beech=0.0,
            prop_oak=0.0,
            lat_alt=0.0,
            constant=3.4915988,
        ),
        "other": FormHeightCoeff(
            inv_diam50=-75.460504,
            inv_diam50_sqr=0.0,
            inv_age10=-22.42175,
            inv_age10_sqr=233.25672,
            age=-0.003411201,
            diam_by_age=0.0,
            site_index_spruce=0.00093784583,
            site_index_pine=0.0012420336,
            basal_area=0.018241435,
            basal_area_sqr=-0.00016137835,
            diam_ratio=0.77487849,
            diam_ratio_sqr=-0.44198548,
            latitude=-0.013222955,
            latitude_sqr=0.0,
            altitude_sqr=0.0,
            altitude=-0.00021816895,
            coast=0.0,
            split_plot=-0.052927894,
            crowberry=0.0,
            south_slope=0.0,
            wet=0.0,
            prop_pine=0.0,
            prop_spruce=0.10235471,
            fertilized=0.0,
            herbs=0.0,
            maritime=0.09017115,
            region5=0.0,
            continental=0.0,
            north_slope=0.0,
            dry=0.0,
            south_east=0.0,
            groundwater_never=-0.083195476,
            prop_birch=0.0,
            prop_beech=0.0,
            prop_oak=0.0,
            lat_alt=0.0,
            constant=2.6800807,
        ),
        "beech": FormHeightCoeff(
            inv_diam50=-212.12487,
            inv_diam50_sqr=7386.7894,
            inv_age10=-16.096667,
            inv_age10_sqr=272.78137,
            age=0.0,
            diam_by_age=-0.030177786,
            site_index_spruce=0.00021614873,
            site_index_pine=0.0,
            basal_area=0.014468791,
            basal_area_sqr=-0.00013999385,
            diam_ratio=0.0,
            diam_ratio_sqr=0.0,
            latitude=0.0,
            latitude_sqr=0.0,
            altitude_sqr=-3.0893256e-06,
            altitude=0.0,
            coast=0.0,
            split_plot=-0.13570479,
            crowberry=0.0,
            south_slope=0.0,
            wet=0.0,
            prop_pine=0.0,
            prop_spruce=0.0,
            fertilized=0.0,
            herbs=0.0,
            maritime=0.0,
            region5=0.0,
            continental=0.0,
            north_slope=-0.086474413,
            dry=0.0,
            south_east=0.0,
            groundwater_never=0.0,
            prop_birch=0.0,
            prop_beech=0.17707772,
            prop_oak=-0.14122116,
            lat_alt=0.0,
            constant=2.7312786,
        ),
        "oak": FormHeightCoeff(
            inv_diam50=-270.69571,
            inv_diam50_sqr=11453.617,
            inv_age10=0.0,
            inv_age10_sqr=0.0,
            age=-0.001609652,
            diam_by_age=-0.017742363,
            site_index_spruce=0.00039008233,
            site_index_pine=0.00036857504,
            basal_area=0.015097781,
            basal_area_sqr=-0.00014109003,
            diam_ratio=0.57340796,
            diam_ratio_sqr=-0.5297074,
            latitude=0.0,
            latitude_sqr=0.0,
            altitude_sqr=0.0,
            altitude=-0.00031421198,
            coast=0.0,
            split_plot=-0.12130558,
            crowberry=0.0,
            south_slope=0.0,
            wet=0.12111676,
            prop_pine=0.0,
            prop_spruce=0.0,
            fertilized=0.0,
            herbs=0.064025365,
            maritime=0.0,
            region5=-0.038959742,
            continental=0.0,
            north_slope=0.0,
            dry=0.0,
            south_east=0.0,
            groundwater_never=-0.065505573,
            prop_birch=-0.091132953,
            prop_beech=0.21363462,
            prop_oak=0.0,
            lat_alt=0.0,
            constant=2.5636208,
        ),
    },
    "middle": {
        "pine": FormHeightCoeff(
            inv_diam50=-234.03773,
            inv_diam50_sqr=7519.0183,
            inv_age10=-13.150814,
            inv_age10_sqr=171.82136,
            age=-0.0015626465,
            diam_by_age=-0.033890982,
            site_index_spruce=0.0011112607,
            site_index_pine=0.001198673,
            basal_area=0.010183977,
            basal_area_sqr=-9.0301238e-05,
            diam_ratio=-0.18661412,
            diam_ratio_sqr=0.048145983,
            latitude=3.5143047,
            latitude_sqr=-0.028627503,
            altitude_sqr=-3.3545479e-07,
            altitude=0.0,
            coast=-0.04594856,
            split_plot=-0.046950091,
            crowberry=0.0,
            south_slope=0.0,
            wet=-0.012350945,
            prop_pine=-0.0168985,
            prop_spruce=0.0,
            fertilized=0.011567716,
            herbs=0.0,
            maritime=0.0,
            region5=0.0,
            continental=0.0,
            north_slope=0.0,
            dry=0.0,
            south_east=0.0,
            groundwater_never=0.0,
            prop_birch=0.0,
            prop_beech=0.0,
            prop_oak=0.0,
            lat_alt=0.0,
            constant=-104.909,
        ),
        "spruce": FormHeightCoeff(
            inv_diam50=-228.6012,
            inv_diam50_sqr=4876.6746,
            inv_age10=-8.1994843,
            inv_age10_sqr=176.12717,
            age=-0.0013356206,
            diam_by_age=-0.040995766,
            site_index_spruce=0.00073529265,
            site_index_pine=0.00055196518,
            basal_area=0.011655487,
            basal_area_sqr=-0.00010072886,
            diam_ratio=0.43924452,
            diam_ratio_sqr=-0.36955966,
            latitude=-0.010854906,
            latitude_sqr=0.0,
            altitude_sqr=-6.3245695e-07,
            altitude=0.00010400941,
            coast=-0.046334655,
            split_plot=-0.046181965,
            crowberry=0.0,
            south_slope=0.0,
            wet=-0.01012388,
            prop_pine=0.088430152,
            prop_spruce=0.089762728,
            fertilized=0.0,
            herbs=-0.011448152,
            maritime=0.0,
            region5=0.0,
            continental=0.011848882,
            north_slope=0.020148289,
            dry=-0.032980617,
            south_east=0.0,
            groundwater_never=-0.011366288,
            prop_birch=0.0,
            prop_beech=0.0,
            prop_oak=0.0,
            lat_alt=0.0,
            constant=3.3239569,
        ),
        "birch": FormHeightCoeff(
            inv_diam50=-187.79692,
            inv_diam50_sqr=4126.3542,
            inv_age10=4.9070641,
            inv_age10_sqr=0.0,
            age=0.0,
            diam_by_age=-0.038410276,
            site_index_spruce=0.00073517342,
            site_index_pine=0.00058577236,
            basal_area=0.016827143,
            basal_area_sqr=-0.00017157801,
            diam_ratio=-0.032079477,
            diam_ratio_sqr=0.0,
            latitude=-0.017385541,
            latitude_sqr=0.0,
            altitude_sqr=-4.4756402e-07,
            altitude=-0.00014858132,
            coast=0.0,
            split_plot=-0.054917452,
            crowberry=-0.095882304,
            south_slope=0.0,
            wet=-0.024337689,
            prop_pine=-0.042524039,
            prop_spruce=-0.060774144,
            fertilized=0.065036414,
            herbs=0.0,
            maritime=0.0,
            region5=0.0,
            continental=0.0,
            north_slope=0.0,
            dry=-0.062793228,
            south_east=0.0,
            groundwater_never=-0.017655774,
            prop_birch=0.0,
            prop_beech=0.0,
            prop_oak=0.0,
            lat_alt=0.0,
            constant=3.4915988,
        ),
        "other": FormHeightCoeff(
            inv_diam50=-75.460504,
            inv_diam50_sqr=0.0,
            inv_age10=-22.42175,
            inv_age10_sqr=233.25672,
            age=-0.003411201,
            diam_by_age=0.0,
            site_index_spruce=0.00093784583,
            site_index_pine=0.0012420336,
            basal_area=0.018241435,
            basal_area_sqr=-0.00016137835,
            diam_ratio=0.77487849,
            diam_ratio_sqr=-0.44198548,
            latitude=-0.013222955,
            latitude_sqr=0.0,
            altitude_sqr=0.0,
            altitude=-0.00021816895,
            coast=0.0,
            split_plot=-0.052927894,
            crowberry=0.0,
            south_slope=0.0,
            wet=0.0,
            prop_pine=0.0,
            prop_spruce=0.10235471,
            fertilized=0.0,
            herbs=0.0,
            maritime=0.09017115,
            region5=0.0,
            continental=0.0,
            north_slope=0.0,
            dry=0.0,
            south_east=0.0,
            groundwater_never=-0.083195476,
            prop_birch=0.0,
            prop_beech=0.0,
            prop_oak=0.0,
            lat_alt=0.0,
            constant=2.6800807,
        ),
        "beech": FormHeightCoeff(
            inv_diam50=-212.12487,
            inv_diam50_sqr=7386.7894,
            inv_age10=-16.096667,
            inv_age10_sqr=272.78137,
            age=0.0,
            diam_by_age=-0.030177786,
            site_index_spruce=0.00021614873,
            site_index_pine=0.0,
            basal_area=0.014468791,
            basal_area_sqr=-0.00013999385,
            diam_ratio=0.0,
            diam_ratio_sqr=0.0,
            latitude=0.0,
            latitude_sqr=0.0,
            altitude_sqr=-3.0893256e-06,
            altitude=0.0,
            coast=0.0,
            split_plot=-0.13570479,
            crowberry=0.0,
            south_slope=0.0,
            wet=0.0,
            prop_pine=0.0,
            prop_spruce=0.0,
            fertilized=0.0,
            herbs=0.0,
            maritime=0.0,
            region5=0.0,
            continental=0.0,
            north_slope=-0.086474413,
            dry=0.0,
            south_east=0.0,
            groundwater_never=0.0,
            prop_birch=0.0,
            prop_beech=0.17707772,
            prop_oak=-0.14122116,
            lat_alt=0.0,
            constant=2.7312786,
        ),
        "oak": FormHeightCoeff(
            inv_diam50=-270.69571,
            inv_diam50_sqr=11453.617,
            inv_age10=0.0,
            inv_age10_sqr=0.0,
            age=-0.001609652,
            diam_by_age=-0.017742363,
            site_index_spruce=0.00039008233,
            site_index_pine=0.00036857504,
            basal_area=0.015097781,
            basal_area_sqr=-0.00014109003,
            diam_ratio=0.57340796,
            diam_ratio_sqr=-0.5297074,
            latitude=0.0,
            latitude_sqr=0.0,
            altitude_sqr=0.0,
            altitude=-0.00031421198,
            coast=0.0,
            split_plot=-0.12130558,
            crowberry=0.0,
            south_slope=0.0,
            wet=0.12111676,
            prop_pine=0.0,
            prop_spruce=0.0,
            fertilized=0.0,
            herbs=0.064025365,
            maritime=0.0,
            region5=-0.038959742,
            continental=0.0,
            north_slope=0.0,
            dry=0.0,
            south_east=0.0,
            groundwater_never=-0.065505573,
            prop_birch=-0.091132953,
            prop_beech=0.21363462,
            prop_oak=0.0,
            lat_alt=0.0,
            constant=2.5636208,
        ),
    },
    "south": {
        "pine": FormHeightCoeff(
            inv_diam50=-244.36558,
            inv_diam50_sqr=9650.1917,
            inv_age10=-14.14199,
            inv_age10_sqr=165.15377,
            age=-0.0026773093,
            diam_by_age=-0.041275406,
            site_index_spruce=0.0012858286,
            site_index_pine=0.0016418955,
            basal_area=0.0092576436,
            basal_area_sqr=-8.9234212e-05,
            diam_ratio=0.24741307,
            diam_ratio_sqr=-0.22096774,
            latitude=-0.88419241,
            latitude_sqr=0.0076429065,
            altitude_sqr=0.0,
            altitude=-4.5526739e-05,
            coast=0.0,
            split_plot=-0.064778578,
            crowberry=-0.030357215,
            south_slope=0.0,
            wet=-0.040199559,
            prop_pine=0.0,
            prop_spruce=0.11525987,
            fertilized=0.037361122,
            herbs=-0.020583343,
            maritime=-0.021720998,
            region5=-0.028372245,
            continental=0.0,
            north_slope=0.0,
            dry=0.0,
            south_east=0.0,
            groundwater_never=0.0,
            prop_birch=0.0,
            prop_beech=0.0,
            prop_oak=0.0,
            lat_alt=0.0,
            constant=28.244825,
        ),
        "spruce": FormHeightCoeff(
            inv_diam50=-252.54722,
            inv_diam50_sqr=5203.7228,
            inv_age10=-7.9331666,
            inv_age10_sqr=153.59833,
            age=-0.0025201649,
            diam_by_age=-0.050822141,
            site_index_spruce=0.00095743659,
            site_index_pine=0.0011126337,
            basal_area=0.0086560054,
            basal_area_sqr=-6.8753457e-05,
            diam_ratio=0.5238766,
            diam_ratio_sqr=-0.44192236,
            latitude=0.0,
            latitude_sqr=0.0,
            altitude_sqr=-1.1486149e-06,
            altitude=0.00033542606,
            coast=0.0,
            split_plot=-0.051101419,
            crowberry=0.0,
            south_slope=0.0,
            wet=0.0,
            prop_pine=0.0,
            prop_spruce=0.14504482,
            fertilized=0.0,
            herbs=0.0,
            maritime=-0.018175324,
            region5=0.0,
            continental=0.021585707,
            north_slope=0.016159142,
            dry=0.0,
            south_east=0.017759946,
            groundwater_never=-0.01460803,
            prop_birch=0.0,
            prop_beech=0.0,
            prop_oak=0.0,
            lat_alt=0.0,
            constant=2.7729923,
        ),
        "birch": FormHeightCoeff(
            inv_diam50=-143.27492,
            inv_diam50_sqr=0.0,
            inv_age10=0.0,
            inv_age10_sqr=39.558422,
            age=-0.0017588788,
            diam_by_age=-0.034886973,
            site_index_spruce=0.00045798152,
            site_index_pine=0.00050811832,
            basal_area=0.011981449,
            basal_area_sqr=-0.00013693065,
            diam_ratio=0.13813899,
            diam_ratio_sqr=-0.25030366,
            latitude=0.022194942,
            latitude_sqr=0.0,
            altitude_sqr=0.0,
            altitude=0.0,
            coast=0.0,
            split_plot=-0.073602503,
            crowberry=-0.17424971,
            south_slope=0.0,
            wet=0.0,
            prop_pine=-0.063941907,
            prop_spruce=0.0,
            fertilized=0.056213691,
            herbs=0.012824818,
            maritime=-0.056749233,
            region5=-0.040859558,
            continental=0.0,
            north_slope=0.0,
            dry=-0.057646988,
            south_east=0.0,
            groundwater_never=0.0,
            prop_birch=0.040774265,
            prop_beech=0.0,
            prop_oak=0.0,
            lat_alt=-2.6037456e-06,
            constant=1.2148178,
        ),
        "other": FormHeightCoeff(
            inv_diam50=-149.2749,
            inv_diam50_sqr=3775.2215,
            inv_age10=0.0,
            inv_age10_sqr=-25.858497,
            age=0.0,
            diam_by_age=0.0,
            site_index_spruce=0.0010998703,
            site_index_pine=0.0010512808,
            basal_area=0.011069561,
            basal_area_sqr=-0.00010669284,
            diam_ratio=0.28134319,
            diam_ratio_sqr=-0.29272634,
            latitude=0.022955713,
            latitude_sqr=0.0,
            altitude_sqr=0.0,
            altitude=0.0,
            coast=0.0,
            split_plot=-0.072063512,
            crowberry=0.0,
            south_slope=0.10338771,
            wet=-0.044592745,
            prop_pine=0.0,
            prop_spruce=0.075214275,
            fertilized=0.0,
            herbs=-0.027333783,
            maritime=0.0,
            region5=0.0,
            continental=0.0,
            north_slope=0.0,
            dry=0.0,
            south_east=0.0,
            groundwater_never=0.0,
            prop_birch=0.0,
            prop_beech=0.0,
            prop_oak=0.0,
            lat_alt=0.0,
            constant=0.58178406,
        ),
        "beech": FormHeightCoeff(
            inv_diam50=-212.12487,
            inv_diam50_sqr=7386.7894,
            inv_age10=-16.096667,
            inv_age10_sqr=272.78137,
            age=0.0,
            diam_by_age=-0.030177786,
            site_index_spruce=0.00021614873,
            site_index_pine=0.0,
            basal_area=0.014468791,
            basal_area_sqr=-0.00013999385,
            diam_ratio=0.0,
            diam_ratio_sqr=0.0,
            latitude=0.0,
            latitude_sqr=0.0,
            altitude_sqr=-3.0893256e-06,
            altitude=0.0,
            coast=0.0,
            split_plot=-0.13570479,
            crowberry=0.0,
            south_slope=0.0,
            wet=0.0,
            prop_pine=0.0,
            prop_spruce=0.0,
            fertilized=0.0,
            herbs=0.0,
            maritime=0.0,
            region5=0.0,
            continental=0.0,
            north_slope=-0.086474413,
            dry=0.0,
            south_east=0.0,
            groundwater_never=0.0,
            prop_birch=0.0,
            prop_beech=0.17707772,
            prop_oak=-0.14122116,
            lat_alt=0.0,
            constant=2.7312786,
        ),
        "oak": FormHeightCoeff(
            inv_diam50=-270.69571,
            inv_diam50_sqr=11453.617,
            inv_age10=0.0,
            inv_age10_sqr=0.0,
            age=-0.001609652,
            diam_by_age=-0.017742363,
            site_index_spruce=0.00039008233,
            site_index_pine=0.00036857504,
            basal_area=0.015097781,
            basal_area_sqr=-0.00014109003,
            diam_ratio=0.57340796,
            diam_ratio_sqr=-0.5297074,
            latitude=0.0,
            latitude_sqr=0.0,
            altitude_sqr=0.0,
            altitude=-0.00031421198,
            coast=0.0,
            split_plot=-0.12130558,
            crowberry=0.0,
            south_slope=0.0,
            wet=0.12111676,
            prop_pine=0.0,
            prop_spruce=0.0,
            fertilized=0.0,
            herbs=0.064025365,
            maritime=0.0,
            region5=-0.038959742,
            continental=0.0,
            north_slope=0.0,
            dry=0.0,
            south_east=0.0,
            groundwater_never=-0.065505573,
            prop_birch=-0.091132953,
            prop_beech=0.21363462,
            prop_oak=0.0,
            lat_alt=0.0,
            constant=2.5636208,
        ),
    },
    "gotland": {
        "pine": FormHeightCoeff(
            inv_diam50=-211.45794,
            inv_diam50_sqr=7176.4736,
            inv_age10=-6.2340744,
            inv_age10_sqr=153.8246,
            age=0.0,
            diam_by_age=0.0,
            site_index_spruce=0.00039118718,
            site_index_pine=0.0,
            basal_area=0.014818417,
            basal_area_sqr=-0.00012168327,
            diam_ratio=0.0,
            diam_ratio_sqr=-0.1926574,
            latitude=0.0,
            latitude_sqr=0.0,
            altitude_sqr=0.0,
            altitude=0.0014933928,
            coast=0.0,
            split_plot=-0.13056649,
            crowberry=0.0,
            south_slope=0.0,
            wet=0.0,
            prop_pine=-0.14059611,
            prop_spruce=0.0,
            fertilized=0.0,
            herbs=0.0,
            maritime=0.0,
            region5=0.0,
            continental=0.0,
            north_slope=0.0,
            dry=0.0,
            south_east=0.0,
            groundwater_never=0.0,
            prop_birch=0.0,
            prop_beech=0.0,
            prop_oak=0.0,
            lat_alt=0.0,
            constant=2.3998,
        ),
        "spruce": FormHeightCoeff(
            inv_diam50=-252.54722,
            inv_diam50_sqr=5203.7228,
            inv_age10=-7.9331666,
            inv_age10_sqr=153.59833,
            age=-0.0025201649,
            diam_by_age=-0.050822141,
            site_index_spruce=0.00095743659,
            site_index_pine=0.0011126337,
            basal_area=0.0086560054,
            basal_area_sqr=-6.8753457e-05,
            diam_ratio=0.5238766,
            diam_ratio_sqr=-0.44192236,
            latitude=0.0,
            latitude_sqr=0.0,
            altitude_sqr=-1.1486149e-06,
            altitude=0.00033542606,
            coast=0.0,
            split_plot=-0.051101419,
            crowberry=0.0,
            south_slope=0.0,
            wet=0.0,
            prop_pine=0.0,
            prop_spruce=0.14504482,
            fertilized=0.0,
            herbs=0.0,
            maritime=-0.018175324,
            region5=0.0,
            continental=0.021585707,
            north_slope=0.016159142,
            dry=0.0,
            south_east=0.017759946,
            groundwater_never=-0.01460803,
            prop_birch=0.0,
            prop_beech=0.0,
            prop_oak=0.0,
            lat_alt=0.0,
            constant=2.7729923,
        ),
        "birch": FormHeightCoeff(
            inv_diam50=-143.27492,
            inv_diam50_sqr=0.0,
            inv_age10=0.0,
            inv_age10_sqr=39.558422,
            age=-0.0017588788,
            diam_by_age=-0.034886973,
            site_index_spruce=0.00045798152,
            site_index_pine=0.00050811832,
            basal_area=0.011981449,
            basal_area_sqr=-0.00013693065,
            diam_ratio=0.13813899,
            diam_ratio_sqr=-0.25030366,
            latitude=0.022194942,
            latitude_sqr=0.0,
            altitude_sqr=0.0,
            altitude=0.0,
            coast=0.0,
            split_plot=-0.073602503,
            crowberry=-0.17424971,
            south_slope=0.0,
            wet=0.0,
            prop_pine=-0.063941907,
            prop_spruce=0.0,
            fertilized=0.056213691,
            herbs=0.012824818,
            maritime=-0.056749233,
            region5=-0.040859558,
            continental=0.0,
            north_slope=0.0,
            dry=-0.057646988,
            south_east=0.0,
            groundwater_never=0.0,
            prop_birch=0.040774265,
            prop_beech=0.0,
            prop_oak=0.0,
            lat_alt=-2.6037456e-06,
            constant=1.2148178,
        ),
        "other": FormHeightCoeff(
            inv_diam50=-149.2749,
            inv_diam50_sqr=3775.2215,
            inv_age10=0.0,
            inv_age10_sqr=-25.858497,
            age=0.0,
            diam_by_age=0.0,
            site_index_spruce=0.0010998703,
            site_index_pine=0.0010512808,
            basal_area=0.011069561,
            basal_area_sqr=-0.00010669284,
            diam_ratio=0.28134319,
            diam_ratio_sqr=-0.29272634,
            latitude=0.022955713,
            latitude_sqr=0.0,
            altitude_sqr=0.0,
            altitude=0.0,
            coast=0.0,
            split_plot=-0.072063512,
            crowberry=0.0,
            south_slope=0.10338771,
            wet=-0.044592745,
            prop_pine=0.0,
            prop_spruce=0.075214275,
            fertilized=0.0,
            herbs=-0.027333783,
            maritime=0.0,
            region5=0.0,
            continental=0.0,
            north_slope=0.0,
            dry=0.0,
            south_east=0.0,
            groundwater_never=0.0,
            prop_birch=0.0,
            prop_beech=0.0,
            prop_oak=0.0,
            lat_alt=0.0,
            constant=0.58178406,
        ),
        "beech": FormHeightCoeff(
            inv_diam50=-212.12487,
            inv_diam50_sqr=7386.7894,
            inv_age10=-16.096667,
            inv_age10_sqr=272.78137,
            age=0.0,
            diam_by_age=-0.030177786,
            site_index_spruce=0.00021614873,
            site_index_pine=0.0,
            basal_area=0.014468791,
            basal_area_sqr=-0.00013999385,
            diam_ratio=0.0,
            diam_ratio_sqr=0.0,
            latitude=0.0,
            latitude_sqr=0.0,
            altitude_sqr=-3.0893256e-06,
            altitude=0.0,
            coast=0.0,
            split_plot=-0.13570479,
            crowberry=0.0,
            south_slope=0.0,
            wet=0.0,
            prop_pine=0.0,
            prop_spruce=0.0,
            fertilized=0.0,
            herbs=0.0,
            maritime=0.0,
            region5=0.0,
            continental=0.0,
            north_slope=-0.086474413,
            dry=0.0,
            south_east=0.0,
            groundwater_never=0.0,
            prop_birch=0.0,
            prop_beech=0.17707772,
            prop_oak=-0.14122116,
            lat_alt=0.0,
            constant=2.7312786,
        ),
        "oak": FormHeightCoeff(
            inv_diam50=-270.69571,
            inv_diam50_sqr=11453.617,
            inv_age10=0.0,
            inv_age10_sqr=0.0,
            age=-0.001609652,
            diam_by_age=-0.017742363,
            site_index_spruce=0.00039008233,
            site_index_pine=0.00036857504,
            basal_area=0.015097781,
            basal_area_sqr=-0.00014109003,
            diam_ratio=0.57340796,
            diam_ratio_sqr=-0.5297074,
            latitude=0.0,
            latitude_sqr=0.0,
            altitude_sqr=0.0,
            altitude=-0.00031421198,
            coast=0.0,
            split_plot=-0.12130558,
            crowberry=0.0,
            south_slope=0.0,
            wet=0.12111676,
            prop_pine=0.0,
            prop_spruce=0.0,
            fertilized=0.0,
            herbs=0.064025365,
            maritime=0.0,
            region5=-0.038959742,
            continental=0.0,
            north_slope=0.0,
            dry=0.0,
            south_east=0.0,
            groundwater_never=-0.065505573,
            prop_birch=-0.091132953,
            prop_beech=0.21363462,
            prop_oak=0.0,
            lat_alt=0.0,
            constant=2.5636208,
        ),
    },
}


def _coerce_species(species: Union[TreeName, str]) -> TreeName:
    """Normalize species input to a canonical ``TreeName``."""
    return _coerce_species_shared(species)


def _species_group(species: TreeName) -> str:
    """Resolve species group key for form-height dispatch."""
    return _species_group_for_soderberg_shared(species, model_name="Söderberg form height")


def _normalize_part_of_sweden(part_of_sweden: str, *, gotland: bool) -> str:
    """Normalize regional labels to north/middle/south(+optional gotland)."""
    if gotland:
        return "gotland"
    return _normalize_part_of_sweden_shared(
        part_of_sweden,
        allow_gotland=True,
        error_message="part_of_sweden must be one of: north, middle, south, gotland.",
    )


def _warn_proportion(name: str, value: float) -> None:
    """Emit a warning when a species-proportion input is outside [0, 1]."""
    _warn_proportion_shared(name, value)


def soderberg_1986_form_height_m(
    *,
    species: Union[TreeName, str],
    diameter_cm: float,
    age_bh_years: float,
    max_diameter_cm: float,
    stand_basal_area_m2_ha: float,
    dominant_species: Union[TreeName, str],
    site_index_dominant_m: float | SiteIndexValue,
    latitude_deg: float,
    altitude_m: float,
    part_of_sweden: str,
    distance_to_coast_lt_50km: bool = False,
    split_plot: bool = False,
    crowberry: bool = False,
    south_slope: bool = False,
    wet_soil: bool = False,
    fertilized: bool = False,
    herbs: bool = False,
    maritime: bool = False,
    region5: bool = False,
    continental: bool = False,
    north_slope: bool = False,
    dry_soil: bool = False,
    south_east: bool = False,
    groundwater_never: bool = False,
    prop_pine: float = 0.0,
    prop_spruce: float = 0.0,
    prop_birch: float = 0.0,
    prop_beech: float = 0.0,
    prop_oak: float = 0.0,
    gotland: bool = False,
) -> float:
    """Form height (m) from Söderberg (1986).

    Returns the form height (m) for a single tree, with site and stand context.

    ``site_index_dominant_m`` may be numeric or ``SiteIndexValue``. Site-index
    objects are validated as Hagglund (1970) H100 and must match the dominant
    conifer selector (pine or spruce).
    """
    tree_species = _coerce_species(species)
    group = _species_group(tree_species)
    dom_species = _coerce_species(dominant_species)
    dom_is_pine = dom_species in _PINE_GROUP

    expected_site_index_species = (
        TreeSpecies.Sweden.pinus_sylvestris if dom_is_pine else TreeSpecies.Sweden.picea_abies
    )
    site_index_dominant_value_m = _normalize_hagglund_h100_site_index_m(
        site_index_dominant_m,
        parameter_name="site_index_dominant_m",
        expected_species=expected_site_index_species,
    )

    if diameter_cm < 0:
        raise ValueError("diameter_cm must be non-negative.")
    if max_diameter_cm <= 0:
        raise ValueError("max_diameter_cm must be positive.")
    if age_bh_years < 0:
        raise ValueError("age_bh_years must be non-negative.")

    if not (55.0 <= latitude_deg <= 70.0):
        warnings.warn(
            f"latitude_deg={latitude_deg} outside typical Sweden range (55-70).",
            stacklevel=2,
        )

    _warn_proportion("prop_pine", prop_pine)
    _warn_proportion("prop_spruce", prop_spruce)
    _warn_proportion("prop_birch", prop_birch)
    _warn_proportion("prop_beech", prop_beech)
    _warn_proportion("prop_oak", prop_oak)

    region = _normalize_part_of_sweden(part_of_sweden, gotland=gotland)
    coeff = _FORM_HEIGHT_COEFF[region][group]

    site_index_pine_dm = site_index_dominant_value_m * 10.0 if dom_is_pine else 0.0
    site_index_spruce_dm = 0.0 if dom_is_pine else site_index_dominant_value_m * 10.0

    # Contorta adjustment: add 30 dm if site index is defined
    if tree_species is TreeSpecies.Sweden.pinus_contorta:
        site_index_pine_dm += 30.0 if site_index_pine_dm > 0 else 0.0
        site_index_spruce_dm += 30.0 if site_index_spruce_dm > 0 else 0.0

    basal_area = stand_basal_area_m2_ha
    basal_area_sqr = basal_area**2
    lat_alt = latitude_deg * altitude_m

    common = (
        site_index_spruce_dm * coeff.site_index_spruce
        + site_index_pine_dm * coeff.site_index_pine
        + basal_area * coeff.basal_area
        + basal_area_sqr * coeff.basal_area_sqr
        + latitude_deg * coeff.latitude
        + (latitude_deg**2) * coeff.latitude_sqr
        + (altitude_m**2) * coeff.altitude_sqr
        + altitude_m * coeff.altitude
        + (1.0 if distance_to_coast_lt_50km else 0.0) * coeff.coast
        + (1.0 if split_plot else 0.0) * coeff.split_plot
        + (1.0 if crowberry else 0.0) * coeff.crowberry
        + (1.0 if south_slope else 0.0) * coeff.south_slope
        + (1.0 if wet_soil else 0.0) * coeff.wet
        + prop_pine * coeff.prop_pine
        + prop_spruce * coeff.prop_spruce
        + (1.0 if fertilized else 0.0) * coeff.fertilized
        + (1.0 if herbs else 0.0) * coeff.herbs
        + (1.0 if maritime else 0.0) * coeff.maritime
        + (1.0 if region5 else 0.0) * coeff.region5
        + (1.0 if continental else 0.0) * coeff.continental
        + (1.0 if north_slope else 0.0) * coeff.north_slope
        + (1.0 if dry_soil else 0.0) * coeff.dry
        + (1.0 if south_east else 0.0) * coeff.south_east
        + (1.0 if groundwater_never else 0.0) * coeff.groundwater_never
        + prop_birch * coeff.prop_birch
        + prop_beech * coeff.prop_beech
        + prop_oak * coeff.prop_oak
        + lat_alt * coeff.lat_alt
        + coeff.constant
    )

    age = max(2.0, age_bh_years)
    inv_diam = 1.0 / (diameter_cm * 10.0 + 50.0)
    inv_diam_sqr = inv_diam**2
    inv_age = 1.0 / (age + 10.0)
    inv_age_sqr = inv_age**2
    diam_by_age = (diameter_cm * 10.0) / age
    diam_ratio = diameter_cm / max_diameter_cm
    diam_ratio_sqr = diam_ratio**2

    ln_form_height = (
        common
        + inv_diam * coeff.inv_diam50
        + inv_diam_sqr * coeff.inv_diam50_sqr
        + inv_age * coeff.inv_age10
        + inv_age_sqr * coeff.inv_age10_sqr
        + age * coeff.age
        + diam_by_age * coeff.diam_by_age
        + diam_ratio * coeff.diam_ratio
        + diam_ratio_sqr * coeff.diam_ratio_sqr
    )

    form_height_m = math.exp(ln_form_height)
    if not math.isfinite(form_height_m) or form_height_m < 0:
        raise ValueError("Computed form height is invalid.")

    # Contorta correction from Hugin comparison (1991)
    if tree_species is TreeSpecies.Sweden.pinus_contorta:
        fkorr = max(0.0, -0.0297 + 0.2596 * math.log(10.0 * diameter_cm) - 0.2142 * diam_ratio)
        form_height_m *= fkorr

    return form_height_m


def soderberg_1986_volume_m3(**kwargs) -> float:
    """Volume (m³) based on Söderberg (1986) form height."""
    form_height_m = soderberg_1986_form_height_m(**kwargs)
    diameter_cm = float(kwargs["diameter_cm"])
    basal_area_cm2 = math.pi * (diameter_cm**2) / 4.0
    volume_m3 = form_height_m * basal_area_cm2 / 10000.0
    if not math.isfinite(volume_m3) or volume_m3 < 0:
        raise ValueError("Computed volume is invalid.")
    return volume_m3


__all__ = ["soderberg_1986_form_height_m", "soderberg_1986_volume_m3"]


DESCRIPTOR = FormulaDescriptor(
    component_id="soderberg_1986_form_height",
    source=SourceReference(
        author="Söderberg, U.",
        year=1986,
        title=(
            "Funktioner för skogliga produktionsprognoser: tillväxt och formhöjd "
            "för enskilda träd av inhemska trädslag i Sverige"
        ),
        note=(
            "Sveriges lantbruksuniversitet, institutionen för biometri och "
            "skogsindelning, Rapport nr 14, Umeå, 251 s. ISBN 91-576-2634-0. "
            "Form height in metres; volume follows as basal area times form height."
        ),
    ),
    species_groups={
        "pine": frozenset({"Pinus sylvestris"}),
        "spruce": frozenset({"Picea abies"}),
        "birch": frozenset({"Betula pendula", "Betula pubescens"}),
    },
    units={
        "diameter_cm": "cm",
        "return": "m (form height) / m3 (volume)",
    },
    kernel_names=("soderberg_1986_form_height_m", "soderberg_1986_volume_m3"),
)
