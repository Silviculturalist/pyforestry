"""Soderberg (1986) single-tree diameter growth equations for Sweden.

Pure equation logic extracted from the block-level adapter. This module
contains all coefficient data, helper functions, and the public
:func:`soderberg_1986_tree_diameter_growth_cm` calculator.

Primary reference:
  - Söderberg, U. (1986). Report 14, SLU, Umeå (Appendix 4 and related growth
    notes).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from enum import IntEnum
from math import exp, isfinite, log, sqrt
from typing import Mapping

from pyforestry.base.helpers import Tree, TreeName, TreeSpecies, parse_tree_species
from pyforestry.base.helpers.primitives import (
    Age,
    AgeMeasurement,
    SiteIndexValue,
    basal_area_growth_cm2_to_diameter_growth_cm,
    diameter_to_basal_area_cm2,
)
from pyforestry.base.simulation import SimulationContext
from pyforestry.sweden.misc import age_to_breast_height_elfving_years
from pyforestry.sweden.site import Sweden
from pyforestry.sweden.siteindex.validation import validate_hagglund_1970_h100_site_index


class _PartOfSweden(IntEnum):
    """Regional partition used in Söderberg (1986) equations."""

    NORTH = 0
    MIDDLE = 1
    SOUTH = 2


class _SpeciesGroup(IntEnum):
    """pyforestry species grouping for the Söderberg (1986) equations.

    Söderberg (1986) fits separate diameter-growth functions per species group;
    these members are pyforestry's internal codes for those groups. The integer
    values are an implementation detail used only as mapping keys and are not
    part of the published model.
    """

    UNKNOWN = 0
    PINE = 1
    SPRUCE = 2
    BIRCH = 3
    ASPEN = 4
    OAK = 5
    BEECH = 6
    SOUTHERN_BROADLEAF = 7
    CONTORTA = 8
    OTHER_BROADLEAF = 9
    LARCH = 10


_PINE_SPECIES = {
    TreeSpecies.Sweden.pinus_sylvestris,
    TreeSpecies.Sweden.pinus_mugo,
}
_CONTORTA_SPECIES = {TreeSpecies.Sweden.pinus_contorta}
_LARCH_SPECIES = {
    TreeSpecies.Sweden.larix_sibirica,
    TreeSpecies.Sweden.larix_decidua,
    TreeSpecies.Sweden.larix_europaea_x_leptolepis,
    TreeSpecies.Sweden.larix_sukaczewii,
}
_SPRUCE_SPECIES = {
    TreeSpecies.Sweden.picea_abies,
    TreeSpecies.Sweden.picea_sitchensis,
    TreeSpecies.Sweden.picea_mariana,
}
_BIRCH_SPECIES = {
    TreeSpecies.Sweden.betula_pendula,
    TreeSpecies.Sweden.betula_pubescens,
}
_ASPEN_SPECIES = {
    TreeSpecies.Sweden.populus_tremula,
    TreeSpecies.Sweden.populus_tremula_x_tremuloides,
}
_OAK_SPECIES = {
    TreeSpecies.Sweden.quercus_robur,
    TreeSpecies.Sweden.quercus_petraea,
    TreeSpecies.Sweden.quercus_rubra,
}
_BEECH_SPECIES = {TreeSpecies.Sweden.fagus_sylvatica}
_SOUTHERN_BROADLEAF_SPECIES = {
    TreeSpecies.Sweden.fraxinus_excelsior,
    TreeSpecies.Sweden.ulmus_glabra,
    TreeSpecies.Sweden.ulmus_minor,
    TreeSpecies.Sweden.ulmus_laevis,
    TreeSpecies.Sweden.tilia_cordata,
    TreeSpecies.Sweden.acer_platanoides,
    TreeSpecies.Sweden.carpinus_betulus,
    TreeSpecies.Sweden.prunus_avium,
}

_RICH_FIELD_LAYERS = {
    Sweden.FieldLayer.HIGH_HERB_WITHOUT_SHRUBS,
    Sweden.FieldLayer.HIGH_HERB_WITH_SHRUBS_BLUEBERRY,
    Sweden.FieldLayer.HIGH_HERB_WITH_SHRUBS_LINGON,
    Sweden.FieldLayer.LOW_HERB_WITHOUT_SHRUBS,
    Sweden.FieldLayer.LOW_HERB_WITH_SHRUBS_BLUEBERRY,
    Sweden.FieldLayer.LOW_HERB_WITH_SHRUBS_LINGON,
    Sweden.FieldLayer.NO_FIELD_LAYER,
    Sweden.FieldLayer.BROADLEAVED_GRASS,
    Sweden.FieldLayer.THINLEAVED_GRASS,
    Sweden.FieldLayer.HORSETAIL,
}

_SOUTH_EAST_COUNTIES = {
    Sweden.County.KALMAR,  # H
    Sweden.County.UPPSALA,  # C
    Sweden.County.STOCKHOLM,  # AB
    Sweden.County.VASTMANLAND,  # U
    Sweden.County.SODERMANLAND,  # D
    Sweden.County.OSTERGOTLAND,  # E
}

_REGION5_COUNTIES = {
    Sweden.County.VASTRA_GOTALANDS,  # O
    Sweden.County.HALLAND,  # N
    Sweden.County.KRISTIANSTAD,  # L
    Sweden.County.MALMOHUS,  # M
    Sweden.County.BLEKINGE,  # K
    Sweden.County.GOTLAND,  # I
}

_MARITIME_CLIMATE_ZONES = {
    Sweden.ClimateZone.M1,
    Sweden.ClimateZone.M2,
    Sweden.ClimateZone.M3,
}

# Age (years) that splits the young/old coefficient sets, by species group.
# Only conifers and birch have an age split (from the HUGIN "AALD" table:
# 55/45/45 for pine/spruce/birch); the remaining groups use a single age set,
# i.e. an effective split of 0.0.
_AGE_GROUP_SPLIT_YEARS: dict[_SpeciesGroup, float] = {
    _SpeciesGroup.PINE: 55.0,
    _SpeciesGroup.SPRUCE: 45.0,
    _SpeciesGroup.BIRCH: 45.0,
    _SpeciesGroup.CONTORTA: 55.0,
    _SpeciesGroup.LARCH: 55.0,
}

# Maximum stand basal area (m2/ha), indexed by [thinning_state][basal_area_class].
# The 3 rows are the Söderberg thinning states (0 = unthinned / just-thinned
# baseline, 1 = thinned 0-5 yr ago, 2 = thinned 6-25 yr ago); the 20 columns are
# the basal-area classes selected by ``_MAX_BASAL_AREA_CLASS``. Values are the
# original HUGIN GYMAX table (the large 2446.18 entry acts as an effective
# "no cap" and is reproduced from the source, not a transcription error).
_MAX_BASAL_AREA_M2_HA: tuple[tuple[float, ...], ...] = (
    (
        43.99,
        44.66,
        47.43,
        48.86,
        41.12,
        45.10,
        50.01,
        73.47,
        60.25,
        72.60,
        45.92,
        41.84,
        31.17,
        33.26,
        31.64,
        49.89,
        42.56,
        39.41,
        38.64,
        37.82,
    ),
    (
        37.04,
        52.41,
        43.38,
        34.30,
        33.12,
        41.88,
        31.31,
        99.99,
        77.85,
        63.48,
        56.03,
        39.82,
        53.92,
        99.99,
        99.90,
        43.73,
        99.90,
        109.01,
        99.90,
        35.86,
    ),
    (
        61.78,
        49.33,
        105.62,
        58.19,
        37.62,
        50.78,
        2446.18,
        99.99,
        113.00,
        89.74,
        45.68,
        41.11,
        47.32,
        89.15,
        53.61,
        41.63,
        99.90,
        24.88,
        43.49,
        51.71,
    ),
)

# Basal-area class (i.e. which column of ``_MAX_BASAL_AREA_M2_HA``) selected per
# species group. Each value is ``(young_age_group, old_age_group)`` and within
# each the three entries are ordered by region ``(north, middle, south)``.
# Inherited from the HUGIN "KB" index table, converted to 0-based indices.
_MAX_BASAL_AREA_CLASS: dict[_SpeciesGroup, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    _SpeciesGroup.PINE: ((0, 2, 4), (1, 3, 5)),
    _SpeciesGroup.SPRUCE: ((6, 8, 10), (7, 9, 11)),
    _SpeciesGroup.BIRCH: ((12, 12, 14), (13, 13, 15)),
    _SpeciesGroup.ASPEN: ((16, 16, 17), (16, 16, 17)),
    _SpeciesGroup.OAK: ((19, 19, 19), (19, 19, 19)),
    _SpeciesGroup.BEECH: ((18, 18, 18), (18, 18, 18)),
    _SpeciesGroup.SOUTHERN_BROADLEAF: ((16, 16, 17), (16, 16, 17)),
    _SpeciesGroup.CONTORTA: ((0, 2, 4), (1, 3, 5)),
    _SpeciesGroup.OTHER_BROADLEAF: ((16, 16, 17), (16, 16, 17)),
    _SpeciesGroup.LARCH: ((0, 2, 4), (1, 3, 5)),
}

_SHARED_EQUATION_GROUP: dict[_SpeciesGroup, _SpeciesGroup] = {
    _SpeciesGroup.UNKNOWN: _SpeciesGroup.SPRUCE,
    _SpeciesGroup.PINE: _SpeciesGroup.PINE,
    _SpeciesGroup.LARCH: _SpeciesGroup.PINE,
    _SpeciesGroup.CONTORTA: _SpeciesGroup.PINE,
    _SpeciesGroup.SPRUCE: _SpeciesGroup.SPRUCE,
    _SpeciesGroup.BIRCH: _SpeciesGroup.BIRCH,
    _SpeciesGroup.OAK: _SpeciesGroup.OAK,
    _SpeciesGroup.BEECH: _SpeciesGroup.BEECH,
    _SpeciesGroup.ASPEN: _SpeciesGroup.ASPEN,
    _SpeciesGroup.OTHER_BROADLEAF: _SpeciesGroup.ASPEN,
    _SpeciesGroup.SOUTHERN_BROADLEAF: _SpeciesGroup.ASPEN,
}


@dataclass(frozen=True)
class _EquationCoefficients:
    """Named Söderberg (1986) coefficients for one equation variant."""

    ln_basal_area: float
    basal_area: float
    ln_basal_area_times_inv_age_plus_ten: float
    inv_age_plus_ten: float
    inv_age_plus_ten_squared: float
    stand_basal_area_unthinned: float
    stand_basal_area_recent_thinning: float
    stand_basal_area_old_thinning: float
    stand_basal_area_unthinned_squared: float
    stand_basal_area_recent_thinning_squared: float
    stand_basal_area_old_thinning_squared: float
    diameter_ratio: float
    diameter_ratio_squared: float
    proportion_pine: float
    proportion_spruce: float
    proportion_birch: float
    site_index_spruce_dm: float
    site_index_pine_dm: float
    peat_indicator: float
    soil_moisture_dry_indicator: float
    south_slope_indicator: float
    north_slope_indicator: float
    soil_moisture_wet_indicator: float
    latitude_deg: float
    altitude_m: float
    latitude_times_altitude: float
    latitude_squared: float
    split_plot_indicator: float
    fertilized_indicator: float
    constant: float
    south_east_indicator: float
    region5_indicator: float
    maritime_indicator: float
    rich_indicator: float
    damage_term: float


# Soderberg (1986) growth coefficients, one set per species group / region /
# age group. Each coefficient is written out with the variable it multiplies so
# it can be checked term-by-term against the source (no positional matrices).
#
# Relative to the earlier HUGIN FORTRAN GRUVAX subroutine, the only recalibrated
# coefficient is the intercept: the original HUGIN intercept is noted inline next
# to each ``constant=`` and all other coefficients are unchanged from HUGIN.
PINE_NORTH_AGE1 = _EquationCoefficients(
    ln_basal_area=1.2198944,
    basal_area=-0.0012142991,
    ln_basal_area_times_inv_age_plus_ten=-4.0367246,
    inv_age_plus_ten=77.768578,
    inv_age_plus_ten_squared=-191.97511,
    stand_basal_area_unthinned=-0.066242926,
    stand_basal_area_recent_thinning=-0.066400036,
    stand_basal_area_old_thinning=-0.054112408,
    stand_basal_area_unthinned_squared=0.0007529197,
    stand_basal_area_recent_thinning_squared=0.00089623063,
    stand_basal_area_old_thinning_squared=0.00043791247,
    diameter_ratio=-0.17016126,
    diameter_ratio_squared=0.0,
    proportion_pine=0.0,
    proportion_spruce=0.31920257,
    proportion_birch=0.0,
    site_index_spruce_dm=0.0024517791,
    site_index_pine_dm=0.0023360634,
    peat_indicator=0.0,
    soil_moisture_dry_indicator=0.0,
    south_slope_indicator=0.12152514,
    north_slope_indicator=-0.056155708,
    soil_moisture_wet_indicator=0.15604559,
    latitude_deg=1.3027869,
    altitude_m=0.0,
    latitude_times_altitude=0.0,
    latitude_squared=-0.0099352868,
    split_plot_indicator=0.092899293,
    fertilized_indicator=0.099816978,
    constant=-45.954,  # HUGIN GRUVAX: -46.041729
    south_east_indicator=0.0,
    region5_indicator=0.0,
    maritime_indicator=0.0,
    rich_indicator=0.0,
    damage_term=-0.0142,
)

PINE_NORTH_AGE2 = _EquationCoefficients(
    ln_basal_area=1.0633055,
    basal_area=-0.00053051894,
    ln_basal_area_times_inv_age_plus_ten=0.0,
    inv_age_plus_ten=158.58514,
    inv_age_plus_ten_squared=-3605.6318,
    stand_basal_area_unthinned=-0.06261526,
    stand_basal_area_recent_thinning=-0.048419956,
    stand_basal_area_old_thinning=-0.052634295,
    stand_basal_area_unthinned_squared=0.00070095109,
    stand_basal_area_recent_thinning_squared=0.00046192319,
    stand_basal_area_old_thinning_squared=0.00053348241,
    diameter_ratio=-0.31675816,
    diameter_ratio_squared=0.0,
    proportion_pine=0.0,
    proportion_spruce=0.28762233,
    proportion_birch=0.34133726,
    site_index_spruce_dm=0.003074605,
    site_index_pine_dm=0.0027870766,
    peat_indicator=0.39932078,
    soil_moisture_dry_indicator=-0.048107754,
    south_slope_indicator=0.053028483,
    north_slope_indicator=-0.053450253,
    soil_moisture_wet_indicator=0.0,
    latitude_deg=-0.061609499,
    altitude_m=-0.0076913475,
    latitude_times_altitude=0.00011708465,
    latitude_squared=0.0,
    split_plot_indicator=0.14838645,
    fertilized_indicator=0.12531452,
    constant=0.63632,  # HUGIN GRUVAX: 0.51032323
    south_east_indicator=0.0,
    region5_indicator=0.0,
    maritime_indicator=0.0,
    rich_indicator=0.0,
    damage_term=-0.0243,
)

PINE_MIDDLE_AGE1 = _EquationCoefficients(
    ln_basal_area=1.0932496,
    basal_area=-0.00045887521,
    ln_basal_area_times_inv_age_plus_ten=-4.0551753,
    inv_age_plus_ten=95.219528,
    inv_age_plus_ten_squared=-445.10657,
    stand_basal_area_unthinned=-0.047256108,
    stand_basal_area_recent_thinning=-0.034902904,
    stand_basal_area_old_thinning=-0.03043397,
    stand_basal_area_unthinned_squared=0.00049819006,
    stand_basal_area_recent_thinning_squared=0.0004022464,
    stand_basal_area_old_thinning_squared=0.000144069,
    diameter_ratio=2.3348472,
    diameter_ratio_squared=-1.6232597,
    proportion_pine=0.0,
    proportion_spruce=0.33477846,
    proportion_birch=0.0,
    site_index_spruce_dm=0.00025445185,
    site_index_pine_dm=0.00080004742,
    peat_indicator=0.17215331,
    soil_moisture_dry_indicator=0.0,
    south_slope_indicator=0.0,
    north_slope_indicator=0.0,
    soil_moisture_wet_indicator=0.13568376,
    latitude_deg=0.0,
    altitude_m=-0.036525138,
    latitude_times_altitude=0.00059703295,
    latitude_squared=0.0,
    split_plot_indicator=0.16428301,
    fertilized_indicator=0.052583363,
    constant=-3.8356,  # HUGIN GRUVAX: -3.9490423
    south_east_indicator=0.0,
    region5_indicator=0.0,
    maritime_indicator=0.0,
    rich_indicator=0.0,
    damage_term=-0.0121,
)

PINE_MIDDLE_AGE2 = _EquationCoefficients(
    ln_basal_area=0.90113842,
    basal_area=-9.421094e-05,
    ln_basal_area_times_inv_age_plus_ten=0.0,
    inv_age_plus_ten=166.34789,
    inv_age_plus_ten_squared=-4213.8643,
    stand_basal_area_unthinned=-0.058169268,
    stand_basal_area_recent_thinning=-0.056115586,
    stand_basal_area_old_thinning=-0.050914612,
    stand_basal_area_unthinned_squared=0.00059532304,
    stand_basal_area_recent_thinning_squared=0.00081798952,
    stand_basal_area_old_thinning_squared=0.00043750228,
    diameter_ratio=2.3240006,
    diameter_ratio_squared=-1.6574745,
    proportion_pine=0.0,
    proportion_spruce=0.37659919,
    proportion_birch=0.0,
    site_index_spruce_dm=0.0017995721,
    site_index_pine_dm=0.0024083664,
    peat_indicator=0.46113142,
    soil_moisture_dry_indicator=0.0,
    south_slope_indicator=0.0,
    north_slope_indicator=0.0,
    soil_moisture_wet_indicator=0.085869744,
    latitude_deg=0.0,
    altitude_m=-0.029433738,
    latitude_times_altitude=0.00047369389,
    latitude_squared=0.0,
    split_plot_indicator=0.1252287,
    fertilized_indicator=0.11201516,
    constant=-3.3826,  # HUGIN GRUVAX: -3.4959855
    south_east_indicator=0.0,
    region5_indicator=0.0,
    maritime_indicator=0.0,
    rich_indicator=0.0,
    damage_term=-0.0203,
)

PINE_SOUTH_AGE1 = _EquationCoefficients(
    ln_basal_area=1.4888244,
    basal_area=-0.0010039507,
    ln_basal_area_times_inv_age_plus_ten=-9.9781055,
    inv_age_plus_ten=140.20134,
    inv_age_plus_ten_squared=-757.1795,
    stand_basal_area_unthinned=-0.054687146,
    stand_basal_area_recent_thinning=-0.058140814,
    stand_basal_area_old_thinning=-0.061332099,
    stand_basal_area_unthinned_squared=0.00066493923,
    stand_basal_area_recent_thinning_squared=0.0008778309,
    stand_basal_area_old_thinning_squared=0.00081506383,
    diameter_ratio=-0.16288485,
    diameter_ratio_squared=0.0,
    proportion_pine=0.19799662,
    proportion_spruce=0.0,
    proportion_birch=0.0,
    site_index_spruce_dm=0.00094400049,
    site_index_pine_dm=0.00060341496,
    peat_indicator=0.34175673,
    soil_moisture_dry_indicator=-0.12512566,
    south_slope_indicator=0.0,
    north_slope_indicator=0.0,
    soil_moisture_wet_indicator=0.0,
    latitude_deg=0.0,
    altitude_m=0.0,
    latitude_times_altitude=0.0,
    latitude_squared=0.0,
    split_plot_indicator=0.092116155,
    fertilized_indicator=0.12978718,
    constant=-4.9333,  # HUGIN GRUVAX: -5.061439
    south_east_indicator=0.10166794,
    region5_indicator=0.0,
    maritime_indicator=0.0,
    rich_indicator=0.0,
    damage_term=-0.0196,
)

PINE_SOUTH_AGE2 = _EquationCoefficients(
    ln_basal_area=0.85280466,
    basal_area=-0.00014701999,
    ln_basal_area_times_inv_age_plus_ten=0.0,
    inv_age_plus_ten=148.40669,
    inv_age_plus_ten_squared=-2740.8892,
    stand_basal_area_unthinned=-0.038635094,
    stand_basal_area_recent_thinning=-0.035843845,
    stand_basal_area_old_thinning=-0.037468482,
    stand_basal_area_unthinned_squared=0.00042830984,
    stand_basal_area_recent_thinning_squared=0.00042792177,
    stand_basal_area_old_thinning_squared=0.00036890939,
    diameter_ratio=1.903843,
    diameter_ratio_squared=-1.3079877,
    proportion_pine=0.18171412,
    proportion_spruce=0.0,
    proportion_birch=0.0,
    site_index_spruce_dm=0.00087209517,
    site_index_pine_dm=0.00075936172,
    peat_indicator=0.29165804,
    soil_moisture_dry_indicator=-0.11758453,
    south_slope_indicator=-0.073810622,
    north_slope_indicator=0.0,
    soil_moisture_wet_indicator=0.0,
    latitude_deg=0.0,
    altitude_m=0.0,
    latitude_times_altitude=-8.1851649e-06,
    latitude_squared=0.0,
    split_plot_indicator=0.11152325,
    fertilized_indicator=0.10516143,
    constant=-3.0557,  # HUGIN GRUVAX: -3.1876907
    south_east_indicator=0.0,
    region5_indicator=0.0,
    maritime_indicator=0.0,
    rich_indicator=0.0,
    damage_term=-0.0274,
)

SPRUCE_NORTH_AGE1 = _EquationCoefficients(
    ln_basal_area=1.1503073,
    basal_area=-0.00065031921,
    ln_basal_area_times_inv_age_plus_ten=0.0,
    inv_age_plus_ten=70.511574,
    inv_age_plus_ten_squared=-314.35129,
    stand_basal_area_unthinned=-0.03608983,
    stand_basal_area_recent_thinning=-0.032109763,
    stand_basal_area_old_thinning=-0.022615924,
    stand_basal_area_unthinned_squared=0.00036083127,
    stand_basal_area_recent_thinning_squared=0.00051283324,
    stand_basal_area_old_thinning_squared=4.6227037e-06,
    diameter_ratio=-0.87521493,
    diameter_ratio_squared=0.49368155,
    proportion_pine=-0.27400699,
    proportion_spruce=-0.33471704,
    proportion_birch=0.0,
    site_index_spruce_dm=0.0011976203,
    site_index_pine_dm=0.0011935009,
    peat_indicator=0.23003249,
    soil_moisture_dry_indicator=0.0,
    south_slope_indicator=0.054127563,
    north_slope_indicator=0.0,
    soil_moisture_wet_indicator=0.0,
    latitude_deg=0.0,
    altitude_m=-0.0044233906,
    latitude_times_altitude=7.6409364e-05,
    latitude_squared=0.0,
    split_plot_indicator=0.048618279,
    fertilized_indicator=0.15556385,
    constant=-2.8683,  # HUGIN GRUVAX: -2.9788063
    south_east_indicator=0.0,
    region5_indicator=0.0,
    maritime_indicator=0.0,
    rich_indicator=0.0,
    damage_term=-0.0172,
)

SPRUCE_NORTH_AGE2 = _EquationCoefficients(
    ln_basal_area=1.0341823,
    basal_area=-0.00013098661,
    ln_basal_area_times_inv_age_plus_ten=0.0,
    inv_age_plus_ten=169.23524,
    inv_age_plus_ten_squared=-3620.8987,
    stand_basal_area_unthinned=-0.025065292,
    stand_basal_area_recent_thinning=-0.0079173939,
    stand_basal_area_old_thinning=-0.013173238,
    stand_basal_area_unthinned_squared=0.00017057359,
    stand_basal_area_recent_thinning_squared=-0.00018977532,
    stand_basal_area_old_thinning_squared=-0.00019557562,
    diameter_ratio=-0.20862041,
    diameter_ratio_squared=0.0,
    proportion_pine=-0.40424174,
    proportion_spruce=-0.30212277,
    proportion_birch=0.0,
    site_index_spruce_dm=0.0012081008,
    site_index_pine_dm=0.0015637354,
    peat_indicator=0.12817557,
    soil_moisture_dry_indicator=-0.14903317,
    south_slope_indicator=0.0,
    north_slope_indicator=-0.053920079,
    soil_moisture_wet_indicator=0.0,
    latitude_deg=0.92969751,
    altitude_m=0.00011499578,
    latitude_times_altitude=0.0,
    latitude_squared=-0.0071427454,
    split_plot_indicator=0.12669519,
    fertilized_indicator=0.18797243,
    constant=-33.523,  # HUGIN GRUVAX: -33.661625
    south_east_indicator=0.0,
    region5_indicator=0.0,
    maritime_indicator=0.0,
    rich_indicator=0.0,
    damage_term=-0.0253,
)

SPRUCE_SOUTH_AGE1 = _EquationCoefficients(
    ln_basal_area=1.2994665,
    basal_area=-0.00032205271,
    ln_basal_area_times_inv_age_plus_ten=-4.2744765,
    inv_age_plus_ten=130.01685,
    inv_age_plus_ten_squared=-887.71338,
    stand_basal_area_unthinned=-0.061903231,
    stand_basal_area_recent_thinning=-0.0513593,
    stand_basal_area_old_thinning=-0.060124654,
    stand_basal_area_unthinned_squared=0.00067406072,
    stand_basal_area_recent_thinning_squared=0.00045833646,
    stand_basal_area_old_thinning_squared=0.00065807032,
    diameter_ratio=-0.44756287,
    diameter_ratio_squared=0.0,
    proportion_pine=-0.19273046,
    proportion_spruce=-0.42806849,
    proportion_birch=-0.30893275,
    site_index_spruce_dm=0.00021659541,
    site_index_pine_dm=0.00070421887,
    peat_indicator=0.055117842,
    soil_moisture_dry_indicator=-0.10322542,
    south_slope_indicator=-0.079993136,
    north_slope_indicator=-0.11318654,
    soil_moisture_wet_indicator=0.045389496,
    latitude_deg=0.0,
    altitude_m=0.0,
    latitude_times_altitude=0.0,
    latitude_squared=0.0,
    split_plot_indicator=0.063629299,
    fertilized_indicator=0.037888177,
    constant=-3.4626,  # HUGIN GRUVAX: -3.6009123
    south_east_indicator=0.0,
    region5_indicator=0.098700136,
    maritime_indicator=0.0,
    rich_indicator=0.0,
    damage_term=-0.0149,
)

SPRUCE_SOUTH_AGE2 = _EquationCoefficients(
    ln_basal_area=1.0063775,
    basal_area=0.0,
    ln_basal_area_times_inv_age_plus_ten=0.0,
    inv_age_plus_ten=166.64375,
    inv_age_plus_ten_squared=-2957.2344,
    stand_basal_area_unthinned=-0.057053741,
    stand_basal_area_recent_thinning=-0.054387908,
    stand_basal_area_old_thinning=-0.055214655,
    stand_basal_area_unthinned_squared=0.00068177067,
    stand_basal_area_recent_thinning_squared=0.0006829052,
    stand_basal_area_old_thinning_squared=0.0006716082,
    diameter_ratio=1.3695741,
    diameter_ratio_squared=-1.2014568,
    proportion_pine=-0.35991868,
    proportion_spruce=-0.55521178,
    proportion_birch=-0.70004201,
    site_index_spruce_dm=0.00057151914,
    site_index_pine_dm=0.00066864898,
    peat_indicator=0.07331121,
    soil_moisture_dry_indicator=-0.19658293,
    south_slope_indicator=-0.10337412,
    north_slope_indicator=-0.102639,
    soil_moisture_wet_indicator=0.069786742,
    latitude_deg=0.0,
    altitude_m=0.0,
    latitude_times_altitude=0.0,
    latitude_squared=0.0,
    split_plot_indicator=0.035977248,
    fertilized_indicator=0.058977846,
    constant=-2.9605,  # HUGIN GRUVAX: -3.1169631
    south_east_indicator=0.0,
    region5_indicator=0.05446738,
    maritime_indicator=0.0,
    rich_indicator=0.0,
    damage_term=-0.0217,
)

BIRCH_NORTH_MIDDLE_AGE1 = _EquationCoefficients(
    ln_basal_area=1.0355833,
    basal_area=0.0,
    ln_basal_area_times_inv_age_plus_ten=0.0,
    inv_age_plus_ten=116.76567,
    inv_age_plus_ten_squared=-1064.2555,
    stand_basal_area_unthinned=-0.072642215,
    stand_basal_area_recent_thinning=-0.045532908,
    stand_basal_area_old_thinning=-0.051404983,
    stand_basal_area_unthinned_squared=0.0011651187,
    stand_basal_area_recent_thinning_squared=0.00042222082,
    stand_basal_area_old_thinning_squared=0.00054315705,
    diameter_ratio=-0.23669741,
    diameter_ratio_squared=0.0,
    proportion_pine=-0.69018793,
    proportion_spruce=-0.55953401,
    proportion_birch=-0.71411884,
    site_index_spruce_dm=0.0,
    site_index_pine_dm=0.0,
    peat_indicator=0.22858548,
    soil_moisture_dry_indicator=0.0,
    south_slope_indicator=0.0,
    north_slope_indicator=-0.16804944,
    soil_moisture_wet_indicator=0.13660824,
    latitude_deg=0.0,
    altitude_m=0.00028355193,
    latitude_times_altitude=0.0,
    latitude_squared=0.0,
    split_plot_indicator=0.045906067,
    fertilized_indicator=0.10208514,
    constant=-2.5124,  # HUGIN GRUVAX: -2.7215064
    south_east_indicator=0.0,
    region5_indicator=0.0,
    maritime_indicator=0.0,
    rich_indicator=0.13364507,
    damage_term=-0.0131,
)

BIRCH_NORTH_MIDDLE_AGE2 = _EquationCoefficients(
    ln_basal_area=1.0652922,
    basal_area=0.0,
    ln_basal_area_times_inv_age_plus_ten=0.0,
    inv_age_plus_ten=200.3112,
    inv_age_plus_ten_squared=-4058.3184,
    stand_basal_area_unthinned=-0.064159468,
    stand_basal_area_recent_thinning=-0.016802359,
    stand_basal_area_old_thinning=-0.04087507,
    stand_basal_area_unthinned_squared=0.00096451415,
    stand_basal_area_recent_thinning_squared=-0.00034084232,
    stand_basal_area_old_thinning_squared=0.00022925473,
    diameter_ratio=-1.4923184,
    diameter_ratio_squared=0.80964762,
    proportion_pine=-0.80276555,
    proportion_spruce=-0.66804576,
    proportion_birch=-0.62539017,
    site_index_spruce_dm=0.0,
    site_index_pine_dm=0.0,
    peat_indicator=0.35839468,
    soil_moisture_dry_indicator=0.0,
    south_slope_indicator=0.0,
    north_slope_indicator=-0.19078416,
    soil_moisture_wet_indicator=0.21901032,
    latitude_deg=1.053007,
    altitude_m=0.0,
    latitude_times_altitude=0.0,
    latitude_squared=-0.0081379553,
    split_plot_indicator=0.18759781,
    fertilized_indicator=0.1020048,
    constant=-36.815,  # HUGIN GRUVAX: -37.017944
    south_east_indicator=0.0,
    region5_indicator=0.0,
    maritime_indicator=0.0,
    rich_indicator=0.11808387,
    damage_term=-0.0246,
)

BIRCH_SOUTH_AGE1 = _EquationCoefficients(
    ln_basal_area=1.0730972,
    basal_area=0.0,
    ln_basal_area_times_inv_age_plus_ten=-5.7526932,
    inv_age_plus_ten=146.00055,
    inv_age_plus_ten_squared=-1033.5298,
    stand_basal_area_unthinned=-0.050493978,
    stand_basal_area_recent_thinning=-0.031237636,
    stand_basal_area_old_thinning=-0.049770426,
    stand_basal_area_unthinned_squared=0.0007980332,
    stand_basal_area_recent_thinning_squared=0.0,
    stand_basal_area_old_thinning_squared=0.0004641671,
    diameter_ratio=1.5895323,
    diameter_ratio_squared=-0.86151439,
    proportion_pine=0.86277729,
    proportion_spruce=0.28913003,
    proportion_birch=0.0,
    site_index_spruce_dm=0.0014655773,
    site_index_pine_dm=0.0015297406,
    peat_indicator=0.0,
    soil_moisture_dry_indicator=0.0,
    south_slope_indicator=0.0,
    north_slope_indicator=0.0,
    soil_moisture_wet_indicator=0.10582978,
    latitude_deg=0.0,
    altitude_m=0.0,
    latitude_times_altitude=0.0,
    latitude_squared=0.0,
    split_plot_indicator=0.18366458,
    fertilized_indicator=0.073269516,
    constant=-4.7436,  # HUGIN GRUVAX: -4.9598565
    south_east_indicator=-0.095623828,
    region5_indicator=0.0,
    maritime_indicator=0.0,
    rich_indicator=0.0,
    damage_term=0.0076,
)

BIRCH_SOUTH_AGE2 = _EquationCoefficients(
    ln_basal_area=0.86065644,
    basal_area=0.0,
    ln_basal_area_times_inv_age_plus_ten=0.0,
    inv_age_plus_ten=76.322411,
    inv_age_plus_ten_squared=0.0,
    stand_basal_area_unthinned=-0.032163251,
    stand_basal_area_recent_thinning=-0.035012688,
    stand_basal_area_old_thinning=-0.037450291,
    stand_basal_area_unthinned_squared=0.00032234247,
    stand_basal_area_recent_thinning_squared=0.00040030747,
    stand_basal_area_old_thinning_squared=0.00044980322,
    diameter_ratio=1.6701843,
    diameter_ratio_squared=-0.80137813,
    proportion_pine=0.67104298,
    proportion_spruce=0.45024577,
    proportion_birch=0.24658862,
    site_index_spruce_dm=0.0017333047,
    site_index_pine_dm=0.0022590975,
    peat_indicator=0.0,
    soil_moisture_dry_indicator=0.0,
    south_slope_indicator=0.0,
    north_slope_indicator=0.0,
    soil_moisture_wet_indicator=0.12044046,
    latitude_deg=0.0,
    altitude_m=0.0,
    latitude_times_altitude=0.0,
    latitude_squared=0.0,
    split_plot_indicator=0.13060836,
    fertilized_indicator=0.1957112,
    constant=-3.7239,  # HUGIN GRUVAX: -3.9666097
    south_east_indicator=-0.11905326,
    region5_indicator=0.0,
    maritime_indicator=0.0,
    rich_indicator=0.0,
    damage_term=0.0118,
)

LEAF_NORTH_MIDDLE = _EquationCoefficients(
    ln_basal_area=1.1207741,
    basal_area=0.0,
    ln_basal_area_times_inv_age_plus_ten=0.0,
    inv_age_plus_ten=48.728222,
    inv_age_plus_ten_squared=0.0,
    stand_basal_area_unthinned=-0.027320145,
    stand_basal_area_recent_thinning=-0.019330734,
    stand_basal_area_old_thinning=-0.019330734,
    stand_basal_area_unthinned_squared=0.00032094921,
    stand_basal_area_recent_thinning_squared=0.0,
    stand_basal_area_old_thinning_squared=0.0,
    diameter_ratio=0.0,
    diameter_ratio_squared=0.0,
    proportion_pine=-0.47541934,
    proportion_spruce=0.2470101,
    proportion_birch=0.0,
    site_index_spruce_dm=0.0,
    site_index_pine_dm=0.0,
    peat_indicator=0.0,
    soil_moisture_dry_indicator=0.0,
    south_slope_indicator=0.0,
    north_slope_indicator=-0.27834153,
    soil_moisture_wet_indicator=0.0,
    latitude_deg=0.063271083,
    altitude_m=0.0,
    latitude_times_altitude=-9.5194209e-06,
    latitude_squared=0.0,
    split_plot_indicator=0.20279391,
    fertilized_indicator=0.0,
    constant=-6.6924,  # HUGIN GRUVAX: -6.8695111
    south_east_indicator=0.0,
    region5_indicator=0.0,
    maritime_indicator=0.0,
    rich_indicator=0.0,
    damage_term=-0.0026,
)

LEAF_SOUTH = _EquationCoefficients(
    ln_basal_area=1.2425539,
    basal_area=-0.00038067318,
    ln_basal_area_times_inv_age_plus_ten=0.0,
    inv_age_plus_ten=86.922943,
    inv_age_plus_ten_squared=-496.47049,
    stand_basal_area_unthinned=-0.057340641,
    stand_basal_area_recent_thinning=-0.034258068,
    stand_basal_area_old_thinning=-0.074100301,
    stand_basal_area_unthinned_squared=0.00072741881,
    stand_basal_area_recent_thinning_squared=0.0001571333,
    stand_basal_area_old_thinning_squared=0.0014893065,
    diameter_ratio=-1.4060723,
    diameter_ratio_squared=0.85102832,
    proportion_pine=0.32524523,
    proportion_spruce=0.24568059,
    proportion_birch=0.20103903,
    site_index_spruce_dm=0.00090257742,
    site_index_pine_dm=0.0008464884,
    peat_indicator=0.0,
    soil_moisture_dry_indicator=0.0,
    south_slope_indicator=0.0,
    north_slope_indicator=-0.14761014,
    soil_moisture_wet_indicator=0.0,
    latitude_deg=0.049305089,
    altitude_m=0.0,
    latitude_times_altitude=0.0,
    latitude_squared=0.0,
    split_plot_indicator=0.10351816,
    fertilized_indicator=0.0,
    constant=-6.3258,  # HUGIN GRUVAX: -6.5246186
    south_east_indicator=0.0,
    region5_indicator=0.0,
    maritime_indicator=0.0,
    rich_indicator=0.0,
    damage_term=0.0081,
)

BEECH = _EquationCoefficients(
    ln_basal_area=1.5935903,
    basal_area=-0.00051910983,
    ln_basal_area_times_inv_age_plus_ten=0.0,
    inv_age_plus_ten=90.769325,
    inv_age_plus_ten_squared=-626.04108,
    stand_basal_area_unthinned=-0.040445954,
    stand_basal_area_recent_thinning=-0.017664259,
    stand_basal_area_old_thinning=-0.035226766,
    stand_basal_area_unthinned_squared=0.00052343268,
    stand_basal_area_recent_thinning_squared=0.0,
    stand_basal_area_old_thinning_squared=0.0004049883,
    diameter_ratio=-2.7505279,
    diameter_ratio_squared=1.2066453,
    proportion_pine=1.008566,
    proportion_spruce=0.0,
    proportion_birch=0.6875425,
    site_index_spruce_dm=0.0015977971,
    site_index_pine_dm=0.00033566036,
    peat_indicator=0.0,
    soil_moisture_dry_indicator=0.0,
    south_slope_indicator=0.0,
    north_slope_indicator=0.0,
    soil_moisture_wet_indicator=0.0,
    latitude_deg=0.0,
    altitude_m=-0.12883925,
    latitude_times_altitude=0.0022649972,
    latitude_squared=0.0,
    split_plot_indicator=0.35173616,
    fertilized_indicator=0.0,
    constant=-5.0158,  # HUGIN GRUVAX: -5.1875067
    south_east_indicator=0.0,
    region5_indicator=0.0,
    maritime_indicator=0.0,
    rich_indicator=0.0,
    damage_term=0.0,
)

OAK = _EquationCoefficients(
    ln_basal_area=1.0682794,
    basal_area=0.0,
    ln_basal_area_times_inv_age_plus_ten=-4.2895813,
    inv_age_plus_ten=162.32246,
    inv_age_plus_ten_squared=-1568.3384,
    stand_basal_area_unthinned=-0.058269843,
    stand_basal_area_recent_thinning=-0.048067022,
    stand_basal_area_old_thinning=-0.035959758,
    stand_basal_area_unthinned_squared=0.00077030365,
    stand_basal_area_recent_thinning_squared=0.00067014329,
    stand_basal_area_old_thinning_squared=0.00034773097,
    diameter_ratio=0.29030326,
    diameter_ratio_squared=0.0,
    proportion_pine=0.0,
    proportion_spruce=0.0,
    proportion_birch=0.0,
    site_index_spruce_dm=0.0,
    site_index_pine_dm=0.0,
    peat_indicator=0.0,
    soil_moisture_dry_indicator=0.0,
    south_slope_indicator=0.22321329,
    north_slope_indicator=0.25425664,
    soil_moisture_wet_indicator=0.0,
    latitude_deg=0.0,
    altitude_m=0.0,
    latitude_times_altitude=0.0,
    latitude_squared=0.0,
    split_plot_indicator=0.0,
    fertilized_indicator=0.0,
    constant=-3.7307,  # HUGIN GRUVAX: -3.8178203
    south_east_indicator=0.0,
    region5_indicator=0.0,
    maritime_indicator=0.0,
    rich_indicator=0.13856307,
    damage_term=0.0,
)

_REQUIRED_CANONICAL_ATTRS = {
    "part_of_sweden",
    "latitude_deg",
    "altitude_m",
    "site_index_species",
    "maritime",
    "south_east",
    "region5",
    "rich",
    "split",
    "soil_moisture",
    "peat",
}
_LEGACY_ALIAS_TO_CANONICAL = {
    "county_code": "part_of_sweden/south_east/region5",
    "region_code_2009": "part_of_sweden",
    "region": "part_of_sweden",
    "climate_zone": "maritime",
    "climate": "maritime",
    "is_rich": "rich",
    "is_split_plot": "split",
    "thinned_0_10_years": "thinned_0_5_years",
    "thinned_6_10_years": "thinned_6_25_years",
    "thinned_11_25_years": "thinned_6_25_years",
    "thinned_11_30_years": "thinned_6_25_years",
    "sis_pine_100": "site_index_pine_m",
    "sis_spruce_100": "site_index_spruce_m",
    "site_index": "site_index_species + site_index_pine_m/site_index_spruce_m",
    "site_index_value": "site_index_species + site_index_pine_m/site_index_spruce_m",
    "site_index_m": "site_index_species + site_index_pine_m/site_index_spruce_m",
    "fertilized_remaining_years": "fertilized_within_10_years",
    "years_since_fertilization": "fertilized_within_10_years",
}


@dataclass(frozen=True)
class _PredictorInputs:
    """Predictor inputs assembled once per tree for the Söderberg (1986) equations."""

    part_of_sweden: _PartOfSweden
    region5_indicator: int
    rich_indicator: int
    south_slope_indicator: int
    north_slope_indicator: int
    soil_moisture_dry_indicator: int
    soil_moisture_wet_indicator: int
    peat_indicator: int
    south_east_indicator: int
    split_plot_indicator: int
    thinning_state: int
    stand_basal_area_m2_ha: float
    altitude_m: float
    fertilized_indicator: float
    latitude_deg: float
    maritime_indicator: float
    proportion_pine: float
    proportion_spruce: float
    proportion_birch: float
    site_index_pine_dm: float
    site_index_spruce_dm: float
    tree_diameter_max_cm: float


def _coerce_species(species: TreeName | str | None) -> TreeName | None:
    """Parse species inputs while allowing ``None`` for unknown species."""
    if species is None:
        return None
    if isinstance(species, TreeName):
        return species
    return parse_tree_species(species)


def _tree_age_bh_years(tree: Tree, site_index_m: float, latitude_deg: float) -> float:
    """Resolve tree age at breast height (years) from tree age metadata."""
    age_val = tree.age
    species = tree.species or TreeSpecies.Sweden.pinus_sylvestris
    if isinstance(age_val, AgeMeasurement):
        if age_val.code == Age.DBH.value:
            return float(age_val)
        if age_val.code == Age.TOTAL.value:
            t13 = age_to_breast_height_elfving_years(
                site_index_m=site_index_m,
                latitude_deg=latitude_deg,
                species=species,
            )
            return max(1.0, float(age_val) - t13)
    if isinstance(age_val, (float, int)):
        return float(age_val)
    warnings.warn("Tree age missing; using 10 years as fallback.", stacklevel=3)
    return 10.0


def _species_group(species: TreeName | None) -> _SpeciesGroup:
    """Return the Söderberg species group for a species."""
    if species is None:
        return _SpeciesGroup.UNKNOWN
    if species in _CONTORTA_SPECIES:
        return _SpeciesGroup.CONTORTA
    if species in _LARCH_SPECIES:
        return _SpeciesGroup.LARCH
    if species in _PINE_SPECIES:
        return _SpeciesGroup.PINE
    if species in _SPRUCE_SPECIES:
        return _SpeciesGroup.SPRUCE
    if species in _BIRCH_SPECIES:
        return _SpeciesGroup.BIRCH
    if species in _ASPEN_SPECIES:
        return _SpeciesGroup.ASPEN
    if species in _BEECH_SPECIES:
        return _SpeciesGroup.BEECH
    if species in _OAK_SPECIES:
        return _SpeciesGroup.OAK
    if species in _SOUTHERN_BROADLEAF_SPECIES:
        return _SpeciesGroup.SOUTHERN_BROADLEAF
    if species.tree_type == "Coniferous":
        return _SpeciesGroup.SPRUCE
    if species.tree_type == "Deciduous":
        return _SpeciesGroup.OTHER_BROADLEAF
    return _SpeciesGroup.UNKNOWN


def _is_conifer_group(group: _SpeciesGroup) -> bool:
    """Return ``True`` when the group is coniferous in Söderberg routing."""
    return group in {
        _SpeciesGroup.PINE,
        _SpeciesGroup.SPRUCE,
        _SpeciesGroup.CONTORTA,
        _SpeciesGroup.LARCH,
    }


def _plot_expansion_factor(plot_area_ha: float, occlusion: float) -> float:
    """Return expansion factor from plot area and occlusion."""
    denominator = plot_area_ha * (1.0 - occlusion)
    if denominator <= 0:
        raise ValueError("Plot area must be positive for expansion.")
    return 1.0 / denominator


def _collect_trees(ctx: SimulationContext) -> list[Tree]:
    """Collect all trees from tree-list/spatial simulation contexts."""
    if ctx.mode not in ("tree_list", "spatial"):
        return []
    return [tree for plot in ctx.plots for tree in plot.trees]


def _parse_part_of_sweden(part_of_sweden: str) -> _PartOfSweden:
    """Parse canonical ``part_of_sweden`` value."""
    region = part_of_sweden.strip().lower()
    if region == "north":
        return _PartOfSweden.NORTH
    if region == "middle":
        return _PartOfSweden.MIDDLE
    if region == "south":
        return _PartOfSweden.SOUTH
    raise ValueError("part_of_sweden must be one of: north, middle, south.")


def _parse_site_index_species(site_index_species: str) -> _SpeciesGroup:
    """Parse canonical site-index species selector."""
    selector = site_index_species.strip().lower()
    if selector == "pine":
        return _SpeciesGroup.PINE
    if selector == "spruce":
        return _SpeciesGroup.SPRUCE
    raise ValueError("site_index_species must be either 'pine' or 'spruce'.")


def _normalize_h100_site_index_m(
    *,
    value: float | SiteIndexValue,
    parameter_name: str,
    expected_species: TreeName,
) -> float:
    """Normalize H100 site-index input to meters with provenance checks."""
    if isinstance(value, SiteIndexValue):
        validate_hagglund_1970_h100_site_index(
            value,
            param_name=parameter_name,
            expected_species=expected_species,
        )
        return float(value)
    return float(value)


def _resolve_site_index_dm(
    *,
    site_index_species: str,
    site_index_pine_m: float | SiteIndexValue | None,
    site_index_spruce_m: float | SiteIndexValue | None,
) -> tuple[float, float, float]:
    """Resolve canonical site index inputs to decimeters for equation usage."""
    selector = _parse_site_index_species(site_index_species)
    if selector is _SpeciesGroup.PINE:
        if site_index_pine_m is None:
            raise ValueError(
                "Soderberg1986 requires site_index_pine_m when site_index_species is 'pine'."
            )
        site_index_pine_value_m = _normalize_h100_site_index_m(
            value=site_index_pine_m,
            parameter_name="site_index_pine_m",
            expected_species=TreeSpecies.Sweden.pinus_sylvestris,
        )
        return site_index_pine_value_m * 10.0, 0.0, site_index_pine_value_m
    if site_index_spruce_m is None:
        raise ValueError(
            "Soderberg1986 requires site_index_spruce_m when site_index_species is 'spruce'."
        )
    site_index_spruce_value_m = _normalize_h100_site_index_m(
        value=site_index_spruce_m,
        parameter_name="site_index_spruce_m",
        expected_species=TreeSpecies.Sweden.picea_abies,
    )
    return 0.0, site_index_spruce_value_m * 10.0, site_index_spruce_value_m


def _active_site_index_m(
    *,
    site_index_species: str,
    site_index_pine_m: float | SiteIndexValue | None,
    site_index_spruce_m: float | SiteIndexValue | None,
) -> float:
    """Return active site index in meters for age conversion."""
    _, _, site_index_m = _resolve_site_index_dm(
        site_index_species=site_index_species,
        site_index_pine_m=site_index_pine_m,
        site_index_spruce_m=site_index_spruce_m,
    )
    return site_index_m


def _soil_moisture_indicators(
    soil_moisture: Sweden.SoilMoistureEnum | int,
) -> tuple[int, int]:
    """Return dry and wet indicator variables from soil moisture input."""
    if isinstance(soil_moisture, Sweden.SoilMoistureEnum):
        return (
            int(soil_moisture == Sweden.SoilMoistureEnum.DRY),
            int(soil_moisture == Sweden.SoilMoistureEnum.WET),
        )
    soil_moisture_code = int(soil_moisture)
    return int(soil_moisture_code == 1), int(soil_moisture_code == 5)


def _resolve_thinning_state(
    *,
    thinned_0_5_years: bool,
    thinned_6_25_years: bool,
    thinning_simulated: bool,
    include_thinning_effect: bool,
) -> int:
    """Resolve Söderberg thinning state (0/1/2) from canonical thinning flags."""
    if include_thinning_effect and thinning_simulated:
        return 0
    if thinned_0_5_years:
        return 1
    if thinned_6_25_years:
        return 2
    return 0


def _pine_coefficients(
    part_of_sweden: _PartOfSweden,
) -> tuple[_EquationCoefficients, _EquationCoefficients]:
    """Return pine coefficients for one Sweden part."""
    if part_of_sweden is _PartOfSweden.NORTH:
        return PINE_NORTH_AGE1, PINE_NORTH_AGE2
    if part_of_sweden is _PartOfSweden.MIDDLE:
        return PINE_MIDDLE_AGE1, PINE_MIDDLE_AGE2
    return PINE_SOUTH_AGE1, PINE_SOUTH_AGE2


def _spruce_coefficients(
    part_of_sweden: _PartOfSweden,
) -> tuple[_EquationCoefficients, _EquationCoefficients]:
    """Return spruce coefficients for one Sweden part.

    Note:
        Spruce in northern and middle Sweden shares the northern coefficient set
        in this implementation.
    """
    if part_of_sweden in {_PartOfSweden.NORTH, _PartOfSweden.MIDDLE}:
        return SPRUCE_NORTH_AGE1, SPRUCE_NORTH_AGE2
    return SPRUCE_SOUTH_AGE1, SPRUCE_SOUTH_AGE2


def _birch_coefficients(
    part_of_sweden: _PartOfSweden,
) -> tuple[_EquationCoefficients, _EquationCoefficients]:
    """Return birch coefficients for one Sweden part."""
    if part_of_sweden is _PartOfSweden.SOUTH:
        return BIRCH_SOUTH_AGE1, BIRCH_SOUTH_AGE2
    return BIRCH_NORTH_MIDDLE_AGE1, BIRCH_NORTH_MIDDLE_AGE2


def _leaf_coefficients(
    part_of_sweden: _PartOfSweden,
) -> tuple[_EquationCoefficients, _EquationCoefficients]:
    """Return shared deciduous (leaf) coefficients for one Sweden part."""
    if part_of_sweden is _PartOfSweden.SOUTH:
        return LEAF_SOUTH, LEAF_SOUTH
    return LEAF_NORTH_MIDDLE, LEAF_NORTH_MIDDLE


def _beech_coefficients(
    _: _PartOfSweden,
) -> tuple[_EquationCoefficients, _EquationCoefficients]:
    """Return beech coefficients independent of Sweden part."""
    return BEECH, BEECH


def _oak_coefficients(
    _: _PartOfSweden,
) -> tuple[_EquationCoefficients, _EquationCoefficients]:
    """Return oak coefficients independent of Sweden part."""
    return OAK, OAK


def _coefficients_for_formula_species(
    formula_species: _SpeciesGroup,
    part_of_sweden: _PartOfSweden,
) -> tuple[_EquationCoefficients, _EquationCoefficients]:
    """Route formula species and region to the correct coefficient pair."""
    if formula_species is _SpeciesGroup.PINE:
        return _pine_coefficients(part_of_sweden)
    if formula_species is _SpeciesGroup.SPRUCE:
        return _spruce_coefficients(part_of_sweden)
    if formula_species is _SpeciesGroup.BIRCH:
        return _birch_coefficients(part_of_sweden)
    if formula_species is _SpeciesGroup.ASPEN:
        return _leaf_coefficients(part_of_sweden)
    if formula_species is _SpeciesGroup.BEECH:
        return _beech_coefficients(part_of_sweden)
    if formula_species is _SpeciesGroup.OAK:
        return _oak_coefficients(part_of_sweden)
    raise ValueError(f"No coefficients available for formula species {formula_species}.")


def _equation_intercept_part(
    coefficient: _EquationCoefficients,
    common: _PredictorInputs,
    *,
    site_index_pine_dm: float,
    site_index_spruce_dm: float,
) -> float:
    """Calculate equation intercept part independent of age-group state terms."""
    return (
        coefficient.constant
        + coefficient.damage_term
        + coefficient.proportion_pine * common.proportion_pine
        + coefficient.proportion_spruce * common.proportion_spruce
        + coefficient.proportion_birch * common.proportion_birch
        + coefficient.site_index_pine_dm * site_index_pine_dm
        + coefficient.site_index_spruce_dm * site_index_spruce_dm
        + coefficient.peat_indicator * common.peat_indicator
        + coefficient.soil_moisture_dry_indicator * common.soil_moisture_dry_indicator
        + coefficient.south_slope_indicator * common.south_slope_indicator
        + coefficient.north_slope_indicator * common.north_slope_indicator
        + coefficient.soil_moisture_wet_indicator * common.soil_moisture_wet_indicator
        + coefficient.latitude_deg * common.latitude_deg
        + coefficient.altitude_m * common.altitude_m
        + coefficient.latitude_times_altitude * (common.latitude_deg * common.altitude_m)
        + coefficient.latitude_squared * (common.latitude_deg * common.latitude_deg)
        + coefficient.split_plot_indicator * common.split_plot_indicator
        + coefficient.fertilized_indicator * common.fertilized_indicator
        + coefficient.south_east_indicator * common.south_east_indicator
        + coefficient.region5_indicator * common.region5_indicator
        + coefficient.maritime_indicator * common.maritime_indicator
        + coefficient.rich_indicator * common.rich_indicator
    )


def _adjusted_site_indices_dm(
    species_group: _SpeciesGroup,
    common: _PredictorInputs,
) -> tuple[float, float]:
    """Site-index inputs (dm) after the group-specific peat/contorta adjustments.

    Pine and spruce on peat drop their site-index terms; lodgepole pine
    (contorta) uses the pine equation with a +30 dm site-index offset.
    """
    site_index_pine_dm = common.site_index_pine_dm
    site_index_spruce_dm = common.site_index_spruce_dm
    if species_group in {_SpeciesGroup.PINE, _SpeciesGroup.SPRUCE} and common.peat_indicator:
        site_index_pine_dm = 0.0
        site_index_spruce_dm = 0.0
    if species_group is _SpeciesGroup.CONTORTA:
        site_index_pine_dm += 30.0
    return site_index_pine_dm, site_index_spruce_dm


def _validate_canonical_attrs(attrs: Mapping[str, object]) -> None:
    """Validate canonical adapter attrs and reject legacy aliases."""
    legacy_keys = sorted(key for key in _LEGACY_ALIAS_TO_CANONICAL if key in attrs)
    if legacy_keys:
        guidance = ", ".join(f"{key}->{_LEGACY_ALIAS_TO_CANONICAL[key]}" for key in legacy_keys)
        raise ValueError(
            "Soderberg1986Model no longer accepts legacy attr keys. "
            f"Use canonical keys instead ({guidance})."
        )

    missing_keys = sorted(key for key in _REQUIRED_CANONICAL_ATTRS if key not in attrs)
    if missing_keys:
        missing_text = ", ".join(missing_keys)
        raise ValueError(f"Soderberg1986Model requires canonical attrs: {missing_text}.")

    selector = _parse_site_index_species(str(attrs["site_index_species"]))
    if selector is _SpeciesGroup.PINE and attrs.get("site_index_pine_m") is None:
        raise ValueError(
            "Soderberg1986Model requires site_index_pine_m when site_index_species is 'pine'."
        )
    if selector is _SpeciesGroup.SPRUCE and attrs.get("site_index_spruce_m") is None:
        raise ValueError(
            "Soderberg1986Model requires site_index_spruce_m when site_index_species is 'spruce'."
        )


def soderberg_1986_tree_diameter_growth_cm(
    *,
    species: TreeName | str,
    diameter_cm: float,
    age_bh_years: float,
    part_of_sweden: str,
    stand_basal_area_m2_ha: float,
    tree_diameter_max_cm: float,
    p_pine: float,
    p_spruce: float,
    p_birch: float,
    site_index_species: str,
    site_index_pine_m: float | SiteIndexValue | None,
    site_index_spruce_m: float | SiteIndexValue | None,
    latitude_deg: float,
    altitude_m: float,
    maritime: bool,
    south_east: bool,
    region5: bool,
    rich: bool,
    split: bool,
    soil_moisture: Sweden.SoilMoistureEnum | int,
    peat: bool,
    fertilized_within_10_years: bool = False,
    thinned_0_5_years: bool = False,
    thinned_6_25_years: bool = False,
    thinning_simulated: bool = False,
    include_thinning_effect: bool = True,
) -> float:
    """Calculate 5-year diameter increment for one tree with Söderberg (1986).

    Source:
        Söderberg, U. (1986). Report 14, SLU, Umeå.

    Applicability:
        Sweden tree-level equations with 5-year period output.

    Units:
        Diameter inputs/outputs in centimeters. Site index inputs in meters
        (internally converted to decimeters where required by equations).

    Example:
        >>> soderberg_1986_tree_diameter_growth_cm(
        ...     species=TreeSpecies.Sweden.pinus_sylvestris,
        ...     diameter_cm=20.0,
        ...     age_bh_years=40.0,
        ...     part_of_sweden="north",
        ...     stand_basal_area_m2_ha=25.0,
        ...     tree_diameter_max_cm=30.0,
        ...     p_pine=0.6,
        ...     p_spruce=0.3,
        ...     p_birch=0.1,
        ...     site_index_species="pine",
        ...     site_index_pine_m=20.0,
        ...     site_index_spruce_m=22.0,
        ...     latitude_deg=60.0,
        ...     altitude_m=100.0,
        ...     maritime=False,
        ...     south_east=False,
        ...     region5=False,
        ...     rich=False,
        ...     split=False,
        ...     soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        ...     peat=False,
        ... )
        0.88...
    """
    if age_bh_years < 0.0:
        raise ValueError("age_bh_years must be non-negative.")
    if diameter_cm <= 0.0 or stand_basal_area_m2_ha <= 0.0 or tree_diameter_max_cm <= 0.0:
        return 0.0

    tree_species = _coerce_species(species)
    group = _species_group(tree_species)
    if group is _SpeciesGroup.UNKNOWN:
        return 0.0

    part = _parse_part_of_sweden(part_of_sweden)
    site_index_pine_dm, site_index_spruce_dm, _ = _resolve_site_index_dm(
        site_index_species=site_index_species,
        site_index_pine_m=site_index_pine_m,
        site_index_spruce_m=site_index_spruce_m,
    )
    soil_moisture_dry_indicator, soil_moisture_wet_indicator = _soil_moisture_indicators(
        soil_moisture
    )
    thinning_state = _resolve_thinning_state(
        thinned_0_5_years=thinned_0_5_years,
        thinned_6_25_years=thinned_6_25_years,
        thinning_simulated=thinning_simulated,
        include_thinning_effect=include_thinning_effect,
    )

    common = _PredictorInputs(
        part_of_sweden=part,
        region5_indicator=int(region5),
        rich_indicator=int(rich),
        south_slope_indicator=0,
        north_slope_indicator=0,
        soil_moisture_dry_indicator=soil_moisture_dry_indicator,
        soil_moisture_wet_indicator=soil_moisture_wet_indicator,
        peat_indicator=int(peat),
        south_east_indicator=int(south_east),
        split_plot_indicator=int(split),
        thinning_state=thinning_state,
        stand_basal_area_m2_ha=stand_basal_area_m2_ha,
        altitude_m=altitude_m,
        fertilized_indicator=float(fertilized_within_10_years),
        latitude_deg=latitude_deg,
        maritime_indicator=float(maritime),
        proportion_pine=p_pine,
        proportion_spruce=p_spruce,
        proportion_birch=p_birch,
        site_index_pine_dm=site_index_pine_dm,
        site_index_spruce_dm=site_index_spruce_dm,
        tree_diameter_max_cm=tree_diameter_max_cm,
    )

    age_group = 0 if age_bh_years < _AGE_GROUP_SPLIT_YEARS.get(group, 0.0) else 1
    coefficients_age1, coefficients_age2 = _coefficients_for_formula_species(
        _SHARED_EQUATION_GROUP[group],
        part,
    )
    coefficient = coefficients_age1 if age_group == 0 else coefficients_age2
    site_index_pine_dm_adj, site_index_spruce_dm_adj = _adjusted_site_indices_dm(group, common)
    intercept = _equation_intercept_part(
        coefficient,
        common,
        site_index_pine_dm=site_index_pine_dm_adj,
        site_index_spruce_dm=site_index_spruce_dm_adj,
    )

    basal_area_cm2 = diameter_to_basal_area_cm2(diameter_cm)
    ln_basal_area = log(basal_area_cm2)
    inv_age_plus_ten = 1.0 / (age_bh_years + 10.0)
    inv_age_plus_ten_squared = inv_age_plus_ten * inv_age_plus_ten
    ln_basal_area_times_inv_age_plus_ten = ln_basal_area * inv_age_plus_ten

    basal_area_class = _MAX_BASAL_AREA_CLASS[group][age_group][int(part)]
    max_basal_area_m2_ha = _MAX_BASAL_AREA_M2_HA[thinning_state][basal_area_class]
    capped_stand_basal_area = min(stand_basal_area_m2_ha, max_basal_area_m2_ha)
    capped_stand_basal_area_squared = capped_stand_basal_area * capped_stand_basal_area

    diameter_ratio = min(diameter_cm / tree_diameter_max_cm, 1.0)
    diameter_ratio_squared = diameter_ratio * diameter_ratio

    ln_basal_area_growth = (
        intercept
        + coefficient.ln_basal_area * ln_basal_area
        + coefficient.basal_area * basal_area_cm2
        + coefficient.ln_basal_area_times_inv_age_plus_ten * ln_basal_area_times_inv_age_plus_ten
        + coefficient.inv_age_plus_ten * inv_age_plus_ten
        + coefficient.inv_age_plus_ten_squared * inv_age_plus_ten_squared
        + coefficient.stand_basal_area_unthinned
        * (capped_stand_basal_area if thinning_state == 0 else 0.0)
        + coefficient.stand_basal_area_recent_thinning
        * (capped_stand_basal_area if thinning_state == 1 else 0.0)
        + coefficient.stand_basal_area_old_thinning
        * (capped_stand_basal_area if thinning_state == 2 else 0.0)
        + coefficient.stand_basal_area_unthinned_squared
        * (capped_stand_basal_area_squared if thinning_state == 0 else 0.0)
        + coefficient.stand_basal_area_recent_thinning_squared
        * (capped_stand_basal_area_squared if thinning_state == 1 else 0.0)
        + coefficient.stand_basal_area_old_thinning_squared
        * (capped_stand_basal_area_squared if thinning_state == 2 else 0.0)
        + coefficient.diameter_ratio * diameter_ratio
        + coefficient.diameter_ratio_squared * diameter_ratio_squared
    )

    basal_area_growth_cm2 = exp(ln_basal_area_growth)
    if basal_area_growth_cm2 < 0.0 or not isfinite(basal_area_growth_cm2):
        raise ValueError("Invalid growth, must be non-negative and finite.")

    if group is _SpeciesGroup.ASPEN and age_bh_years >= 120.0:
        basal_area_growth_cm2 = 0.0
    if group is _SpeciesGroup.BEECH and stand_basal_area_m2_ha > 20.0:
        basal_area_growth_cm2 *= sqrt(20.0 / stand_basal_area_m2_ha)

    if basal_area_growth_cm2 <= 0.0:
        return 0.0
    return basal_area_growth_cm2_to_diameter_growth_cm(diameter_cm, basal_area_growth_cm2)
