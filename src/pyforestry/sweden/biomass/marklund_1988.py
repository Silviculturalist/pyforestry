"""Allometric biomass functions from Marklund (1988), Report 45.

Faithful transcription of every function in Marklund, L.-G. (1988) 'Biomassafunktioner
för tall, gran och björk i Sverige' (Biomass functions for pine, spruce and birch in
Sweden), SLU Dept. of Forest Survey, Report 45, Umeå. Each function returns component
DRY WEIGHT in kg. The published constants already include the Baskerville bias
correction for the log back-transformation, so `exp(const + Σβ·x)` is used directly.
Function ids (T-/G-/B-) follow the report (T=Tall/pine, G=Gran/spruce, B=Björk/birch)."""

import numpy as np


# Scots pine (Pinus sylvestris) — stem over bark
def Marklund_1988_T1(*, diameter_cm) -> float:
    """Scots pine stem over bark dry weight (kg) — Marklund (1988) T-1.

    Source: Marklund (1988) Report 45, function T-1, printed p20.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-2.3388 + 11.3264 * (diameter_cm / (diameter_cm + 13)))


def Marklund_1988_T2(*, diameter_cm, height_m) -> float:
    """Scots pine stem over bark dry weight (kg) — Marklund (1988) T-2.

    Source: Marklund (1988) Report 45, function T-2, printed p20.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
    """
    return np.exp(
        -2.6768
        + 7.5939 * (diameter_cm / (diameter_cm + 13))
        + 0.0151 * height_m
        + 0.8799 * np.log(height_m)
    )


def Marklund_1988_T3(*, diameter_cm, height_m, double_bark_mm, age_bh_years) -> float:
    """Scots pine stem over bark dry weight (kg) — Marklund (1988) T-3.

    Source: Marklund (1988) Report 45, function T-3, printed p21.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        double_bark_mm: double bark thickness at breast height [mm]
        age_bh_years: age at breast height [years]
    """
    return np.exp(
        -2.6232
        + 7.7318 * (diameter_cm / (diameter_cm + 13))
        + 0.0139 * height_m
        + 0.8625 * np.log(height_m)
        + -0.0704 * np.log(double_bark_mm)
        + 0.00185 * age_bh_years
    )


def Marklund_1988_T4(
    *,
    diameter_cm,
    height_m,
    double_bark_mm,
    age_bh_years,
    form_quotient3,
    form_quotient5,
    altitude_km,
) -> float:
    """Scots pine stem over bark dry weight (kg) — Marklund (1988) T-4.

    Source: Marklund (1988) Report 45, function T-4, printed p21.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        double_bark_mm: double bark thickness at breast height [mm]
        age_bh_years: age at breast height [years]
        form_quotient3: form quotient d3/d [-] (0 if d3 not measured)
        form_quotient5: form quotient d5/d [-] (0 if d5 not measured)
        altitude_km: altitude above sea level [km]
    """
    return np.exp(
        -2.4826
        + 7.9039 * (diameter_cm / (diameter_cm + 13))
        + 0.0184 * height_m
        + 0.6939 * np.log(height_m)
        + -0.0731 * np.log(double_bark_mm)
        + 0.00182 * age_bh_years
        + 0.2382 * form_quotient5
        + 0.2217 * form_quotient3
        + -0.1596 * altitude_km
    )


# Scots pine (Pinus sylvestris) — stem wood
def Marklund_1988_T5(*, diameter_cm) -> float:
    """Scots pine stem wood dry weight (kg) — Marklund (1988) T-5.

    Source: Marklund (1988) Report 45, function T-5, printed p22.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-2.2184 + 11.4219 * (diameter_cm / (diameter_cm + 14)))


def Marklund_1988_T6(*, diameter_cm, height_m) -> float:
    """Scots pine stem wood dry weight (kg) — Marklund (1988) T-6.

    Source: Marklund (1988) Report 45, function T-6, printed p22.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
    """
    return np.exp(
        -2.6864
        + 7.6066 * (diameter_cm / (diameter_cm + 14))
        + 0.02 * height_m
        + 0.8658 * np.log(height_m)
    )


def Marklund_1988_T7(*, diameter_cm, height_m, double_bark_mm, age_bh_years) -> float:
    """Scots pine stem wood dry weight (kg) — Marklund (1988) T-7.

    Source: Marklund (1988) Report 45, function T-7, printed p23.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        double_bark_mm: double bark thickness at breast height [mm]
        age_bh_years: age at breast height [years]
    """
    return np.exp(
        -2.5325
        + 7.8936 * (diameter_cm / (diameter_cm + 14))
        + 0.0231 * height_m
        + 0.7887 * np.log(height_m)
        + -0.1065 * np.log(double_bark_mm)
        + 0.00201 * age_bh_years
    )


def Marklund_1988_T8(
    *,
    diameter_cm,
    height_m,
    double_bark_mm,
    age_bh_years,
    form_quotient3,
    form_quotient5,
    altitude_km,
) -> float:
    """Scots pine stem wood dry weight (kg) — Marklund (1988) T-8.

    Source: Marklund (1988) Report 45, function T-8, printed p23.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        double_bark_mm: double bark thickness at breast height [mm]
        age_bh_years: age at breast height [years]
        form_quotient3: form quotient d3/d [-] (0 if d3 not measured)
        form_quotient5: form quotient d5/d [-] (0 if d5 not measured)
        altitude_km: altitude above sea level [km]
    """
    return np.exp(
        -2.0028
        + 7.9455 * (diameter_cm / (diameter_cm + 14))
        + 0.0439 * height_m
        + 0.2437 * np.log(height_m)
        + -0.0875 * np.log(double_bark_mm)
        + 0.00172 * age_bh_years
        + 0.7778 * form_quotient5
        + 0.4855 * form_quotient3
        + -0.1557 * altitude_km
    )


# Scots pine (Pinus sylvestris) — stem bark
def Marklund_1988_T9(*, diameter_cm) -> float:
    """Scots pine stem bark dry weight (kg) — Marklund (1988) T-9.

    Source: Marklund (1988) Report 45, function T-9, printed p24.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-2.9748 + 8.8489 * (diameter_cm / (diameter_cm + 16)))


def Marklund_1988_T10(*, diameter_cm, height_m) -> float:
    """Scots pine stem bark dry weight (kg) — Marklund (1988) T-10.

    Source: Marklund (1988) Report 45, function T-10, printed p24.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
    """
    return np.exp(
        -3.2765 + 7.2482 * (diameter_cm / (diameter_cm + 16)) + 0.4487 * np.log(height_m)
    )


def Marklund_1988_T11(*, diameter_cm, height_m, double_bark_mm) -> float:
    """Scots pine stem bark dry weight (kg) — Marklund (1988) T-11.

    Source: Marklund (1988) Report 45, function T-11, printed p25.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        double_bark_mm: double bark thickness at breast height [mm]
    """
    return np.exp(
        -3.6065
        + 7.0834 * (diameter_cm / (diameter_cm + 16))
        + 0.5086 * np.log(height_m)
        + 0.0255 * (double_bark_mm / (diameter_cm * 10.0) * 100.0)
    )


def Marklund_1988_T12(*, diameter_cm, height_m, double_bark_mm, crown_base_height_m) -> float:
    """Scots pine stem bark dry weight (kg) — Marklund (1988) T-12.

    Source: Marklund (1988) Report 45, function T-12, printed p25.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        double_bark_mm: double bark thickness at breast height [mm]
        crown_base_height_m: green crown base height krg [m]
    """
    return np.exp(
        -3.5076
        + 7.5295 * (diameter_cm / (diameter_cm + 16))
        + 0.5629 * np.log(height_m)
        + -0.2271 * np.log(height_m - crown_base_height_m)
        + 0.0222 * (double_bark_mm / (diameter_cm * 10.0) * 100.0)
    )


# Scots pine (Pinus sylvestris) — living branches (incl. needles)
def Marklund_1988_T13(*, diameter_cm) -> float:
    """Scots pine living branches (incl. needles) dry weight (kg) — Marklund (1988) T-13.

    Source: Marklund (1988) Report 45, function T-13, printed p26.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-2.8604 + 9.1015 * (diameter_cm / (diameter_cm + 10)))


def Marklund_1988_T14(*, diameter_cm, height_m) -> float:
    """Scots pine living branches (incl. needles) dry weight (kg) — Marklund (1988) T-14.

    Source: Marklund (1988) Report 45, function T-14, printed p26.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
    """
    return np.exp(
        -2.5413 + 13.3955 * (diameter_cm / (diameter_cm + 10)) + -1.1955 * np.log(height_m)
    )


def Marklund_1988_T15(
    *, diameter_cm, height_m, crown_base_height_m, north_coordinate_100km
) -> float:
    """Scots pine living branches (incl. needles) dry weight (kg) — Marklund (1988) T-15.

    Source: Marklund (1988) Report 45, function T-15, printed p27.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        crown_base_height_m: green crown base height krg [m]
        north_coordinate_100km: RT90 north coordinate NKO [100 km units = northing_m/100000]
    """
    return np.exp(
        -0.9137
        + 11.4337 * (diameter_cm / (diameter_cm + 10))
        + -1.4815 * np.log(height_m)
        + 0.9825 * np.log(height_m - crown_base_height_m)
        + -0.0235 * north_coordinate_100km
    )


def Marklund_1988_T16(
    *,
    diameter_cm,
    height_m,
    age_bh_years,
    crown_base_height_m,
    crown_radius_m,
    diameter_increment_5yr_mm,
) -> float:
    """Scots pine living branches (incl. needles) dry weight (kg) — Marklund (1988) T-16.

    Source: Marklund (1988) Report 45, function T-16, printed p27.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        age_bh_years: age at breast height [years]
        crown_base_height_m: green crown base height krg [m]
        crown_radius_m: crown radius kr [m]
        diameter_increment_5yr_mm: last-5-year diameter increment i5 [mm]
    """
    return np.exp(
        -2.8445
        + 9.0891 * (diameter_cm / (diameter_cm + 10))
        + -1.1599 * np.log(height_m)
        + 0.6197 * np.log(height_m - crown_base_height_m)
        + 0.5372 * np.log(crown_radius_m)
        + 0.2011 * np.log(age_bh_years)
        + 0.2142 * np.log(diameter_increment_5yr_mm)
    )


# Scots pine (Pinus sylvestris) — needles
def Marklund_1988_T17(*, diameter_cm) -> float:
    """Scots pine needles dry weight (kg) — Marklund (1988) T-17.

    Source: Marklund (1988) Report 45, function T-17, printed p28.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-3.7983 + 7.7681 * (diameter_cm / (diameter_cm + 7)))


def Marklund_1988_T18(*, diameter_cm, height_m) -> float:
    """Scots pine needles dry weight (kg) — Marklund (1988) T-18.

    Source: Marklund (1988) Report 45, function T-18, printed p28.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
    """
    return np.exp(
        -3.4781
        + 12.1095 * (diameter_cm / (diameter_cm + 7))
        + 0.0413 * height_m
        + -1.565 * np.log(height_m)
    )


def Marklund_1988_T19(
    *, diameter_cm, height_m, crown_base_height_m, north_coordinate_100km
) -> float:
    """Scots pine needles dry weight (kg) — Marklund (1988) T-19.

    Source: Marklund (1988) Report 45, function T-19, printed p29.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        crown_base_height_m: green crown base height krg [m]
        north_coordinate_100km: RT90 north coordinate NKO [100 km units = northing_m/100000]
    """
    return np.exp(
        -2.6024
        + 9.8471 * (diameter_cm / (diameter_cm + 7))
        + 0.026 * height_m
        + -1.6717 * np.log(height_m)
        + 1.0419 * np.log(height_m - crown_base_height_m)
        + -0.0123 * north_coordinate_100km
    )


def Marklund_1988_T20(
    *,
    diameter_cm,
    height_m,
    age_bh_years,
    crown_base_height_m,
    crown_radius_m,
    diameter_increment_5yr_mm,
    altitude_km,
) -> float:
    """Scots pine needles dry weight (kg) — Marklund (1988) T-20.

    Source: Marklund (1988) Report 45, function T-20, printed p29.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        age_bh_years: age at breast height [years]
        crown_base_height_m: green crown base height krg [m]
        crown_radius_m: crown radius kr [m]
        diameter_increment_5yr_mm: last-5-year diameter increment i5 [mm]
        altitude_km: altitude above sea level [km]
    """
    return np.exp(
        -4.6082
        + 7.7998 * (diameter_cm / (diameter_cm + 7))
        + -0.6978 * np.log(height_m)
        + 0.4588 * np.log(height_m - crown_base_height_m)
        + 0.2398 * np.log(crown_radius_m)
        + 0.2632 * np.log(age_bh_years)
        + 0.404 * np.log(diameter_increment_5yr_mm)
        + 0.5144 * altitude_km
    )


# Scots pine (Pinus sylvestris) — dead branches
def Marklund_1988_T21(*, diameter_cm) -> float:
    """Scots pine dead branches dry weight (kg) — Marklund (1988) T-21.

    Source: Marklund (1988) Report 45, function T-21, printed p30.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-5.3338 + 9.5938 * (diameter_cm / (diameter_cm + 10)))


def Marklund_1988_T22(*, diameter_cm, height_m) -> float:
    """Scots pine dead branches dry weight (kg) — Marklund (1988) T-22.

    Source: Marklund (1988) Report 45, function T-22, printed p30.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
    """
    return np.exp(
        -5.8926
        + 7.127 * (diameter_cm / (diameter_cm + 10))
        + -0.0465 * height_m
        + 1.106 * np.log(height_m)
    )


def Marklund_1988_T23(*, diameter_cm, height_m, north_coordinate_100km, altitude_km) -> float:
    """Scots pine dead branches dry weight (kg) — Marklund (1988) T-23.

    Source: Marklund (1988) Report 45, function T-23, printed p31.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        north_coordinate_100km: RT90 north coordinate NKO [100 km units = northing_m/100000]
        altitude_km: altitude above sea level [km]
    """
    return np.exp(
        -0.9305
        + 7.1889 * (diameter_cm / (diameter_cm + 10))
        + -0.085 * height_m
        + 1.3027 * np.log(height_m)
        + -0.0702 * north_coordinate_100km
        + -1.0568 * altitude_km
    )


def Marklund_1988_T24(
    *,
    diameter_cm,
    height_m,
    age_bh_years,
    diameter_increment_5yr_mm,
    max_diameter_cm,
    north_coordinate_100km,
    altitude_km,
) -> float:
    """Scots pine dead branches dry weight (kg) — Marklund (1988) T-24.

    Source: Marklund (1988) Report 45, function T-24, printed p31.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        age_bh_years: age at breast height [years]
        diameter_increment_5yr_mm: last-5-year diameter increment i5 [mm]
        max_diameter_cm: diameter of thickest tree on a 10 m radius plot D_max [cm]
        north_coordinate_100km: RT90 north coordinate NKO [100 km units = northing_m/100000]
        altitude_km: altitude above sea level [km]
    """
    return np.exp(
        -0.8931
        + 10.3377 * (diameter_cm / (diameter_cm + 10))
        + -0.0865 * height_m
        + 0.8701 * np.log(height_m)
        + -0.6209 * np.log(age_bh_years)
        + -0.51 * np.log(diameter_increment_5yr_mm)
        + 0.5846 * np.log(max_diameter_cm)
        + -0.0577 * north_coordinate_100km
        + -1.1226 * altitude_km
    )


# Scots pine (Pinus sylvestris) — stump-root system
def Marklund_1988_T25(*, diameter_cm) -> float:
    """Scots pine stump-root system dry weight (kg) — Marklund (1988) T-25.

    Source: Marklund (1988) Report 45, function T-25, printed p32.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-3.3913 + 11.1106 * (diameter_cm / (diameter_cm + 12)))


def Marklund_1988_T26(
    *, diameter_cm, site_index_pine_m, site_index_spruce_m, north_coordinate_100km
) -> float:
    """Scots pine stump-root system dry weight (kg) — Marklund (1988) T-26.

    Source: Marklund (1988) Report 45, function T-26, printed p32.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        site_index_pine_m: site index H100 for pine SItall [m] (0 if site indexed by spruce)
        site_index_spruce_m: site index H100 for spruce SIgran [m] (0 if site indexed by pine)
        north_coordinate_100km: RT90 north coordinate NKO [100 km units = northing_m/100000]
    """
    return np.exp(
        -1.553
        + 11.2246 * (diameter_cm / (diameter_cm + 12))
        + -0.0314 * site_index_pine_m
        + -0.0268 * site_index_spruce_m
        + -0.0192 * north_coordinate_100km
    )


def Marklund_1988_T27(
    *,
    diameter_cm,
    age_bh_years,
    site_index_pine_m,
    site_index_spruce_m,
    altitude_km,
    dry_soil,
    moist_soil,
    peat_soil,
    lateral_water_long,
    lateral_water_short,
) -> float:
    """Scots pine stump-root system dry weight (kg) — Marklund (1988) T-27.

    Source: Marklund (1988) Report 45, function T-27, printed p33.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        age_bh_years: age at breast height [years]
        site_index_pine_m: site index H100 for pine SItall [m] (0 if site indexed by spruce)
        site_index_spruce_m: site index H100 for spruce SIgran [m] (0 if site indexed by pine)
        altitude_km: altitude above sea level [km]
        dry_soil: indicator 1 if dry firm land TORR_MARK else 0
        moist_soil: indicator 1 if moist/wet firm land FUKT_MARK else 0
        peat_soil: indicator 1 if peat land TORV_MARK else 0
        lateral_water_long: indicator 1 if long-period lateral water LANG_OVSI else 0
        lateral_water_short: indicator 1 if short-period lateral water KORT_OVSI else 0
    """
    return np.exp(
        -3.1638
        + 10.7181 * (diameter_cm / (diameter_cm + 12))
        + 0.0952 * np.log(age_bh_years)
        + -0.0168 * site_index_pine_m
        + -0.0136 * site_index_spruce_m
        + -0.0808 * dry_soil
        + 0.2165 * moist_soil
        + 0.3088 * peat_soil
        + -0.1655 * lateral_water_long
        + -0.107 * lateral_water_short
        + -0.5221 * altitude_km
    )


# Scots pine (Pinus sylvestris) — stump
def Marklund_1988_T28(*, diameter_cm) -> float:
    """Scots pine stump dry weight (kg) — Marklund (1988) T-28.

    Source: Marklund (1988) Report 45, function T-28, printed p34.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-3.9657 + 11.0481 * (diameter_cm / (diameter_cm + 15)))


def Marklund_1988_T29(*, diameter_cm, age_bh_years, north_coordinate_100km) -> float:
    """Scots pine stump dry weight (kg) — Marklund (1988) T-29.

    Source: Marklund (1988) Report 45, function T-29, printed p34.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        age_bh_years: age at breast height [years]
        north_coordinate_100km: RT90 north coordinate NKO [100 km units = northing_m/100000]
    """
    return np.exp(
        -2.1762
        + 9.5137 * (diameter_cm / (diameter_cm + 15))
        + 0.3105 * np.log(age_bh_years)
        + -0.0326 * north_coordinate_100km
    )


def Marklund_1988_T30(
    *,
    diameter_cm,
    age_bh_years,
    north_coordinate_100km,
    altitude_km,
    dry_soil,
    moist_soil,
    peat_soil,
    lateral_water_any,
) -> float:
    """Scots pine stump dry weight (kg) — Marklund (1988) T-30.

    Source: Marklund (1988) Report 45, function T-30, printed p35.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        age_bh_years: age at breast height [years]
        north_coordinate_100km: RT90 north coordinate NKO [100 km units = northing_m/100000]
        altitude_km: altitude above sea level [km]
        dry_soil: indicator 1 if dry firm land TORR_MARK else 0
        moist_soil: indicator 1 if moist/wet firm land FUKT_MARK else 0
        peat_soil: indicator 1 if peat land TORV_MARK else 0
        lateral_water_any: indicator 1 if any-period lateral water OVSI else 0
    """
    return np.exp(
        -2.5087
        + 9.4014 * (diameter_cm / (diameter_cm + 15))
        + 0.322 * np.log(age_bh_years)
        + -0.1794 * dry_soil
        + 0.2047 * moist_soil
        + 0.1247 * peat_soil
        + -0.1031 * lateral_water_any
        + -0.0255 * north_coordinate_100km
        + -0.688 * altitude_km
    )


# Scots pine (Pinus sylvestris) — roots >= 5 cm
def Marklund_1988_T31(*, diameter_cm) -> float:
    """Scots pine roots >= 5 cm dry weight (kg) — Marklund (1988) T-31.

    Source: Marklund (1988) Report 45, function T-31, printed p36.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-6.3413 + 13.2902 * (diameter_cm / (diameter_cm + 9)))


def Marklund_1988_T32(
    *, diameter_cm, site_index_pine_m, site_index_spruce_m, north_coordinate_100km
) -> float:
    """Scots pine roots >= 5 cm dry weight (kg) — Marklund (1988) T-32.

    Source: Marklund (1988) Report 45, function T-32, printed p36.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        site_index_pine_m: site index H100 for pine SItall [m] (0 if site indexed by spruce)
        site_index_spruce_m: site index H100 for spruce SIgran [m] (0 if site indexed by pine)
        north_coordinate_100km: RT90 north coordinate NKO [100 km units = northing_m/100000]
    """
    return np.exp(
        -3.5882
        + 13.6524 * (diameter_cm / (diameter_cm + 9))
        + -0.0467 * site_index_pine_m
        + -0.0448 * site_index_spruce_m
        + -0.0306 * north_coordinate_100km
    )


def Marklund_1988_T33(
    *,
    diameter_cm,
    site_index_pine_m,
    site_index_spruce_m,
    altitude_km,
    dry_soil,
    moist_soil,
    peat_soil,
) -> float:
    """Scots pine roots >= 5 cm dry weight (kg) — Marklund (1988) T-33.

    Source: Marklund (1988) Report 45, function T-33, printed p37.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        site_index_pine_m: site index H100 for pine SItall [m] (0 if site indexed by spruce)
        site_index_spruce_m: site index H100 for spruce SIgran [m] (0 if site indexed by pine)
        altitude_km: altitude above sea level [km]
        dry_soil: indicator 1 if dry firm land TORR_MARK else 0
        moist_soil: indicator 1 if moist/wet firm land FUKT_MARK else 0
        peat_soil: indicator 1 if peat land TORV_MARK else 0
    """
    return np.exp(
        -5.966
        + 13.7465 * (diameter_cm / (diameter_cm + 9))
        + -0.0352 * site_index_pine_m
        + -0.0356 * site_index_spruce_m
        + -0.1443 * dry_soil
        + 0.3052 * moist_soil
        + 0.5078 * peat_soil
        + -0.6359 * altitude_km
    )


# Scots pine (Pinus sylvestris) — roots < 5 cm
def Marklund_1988_T34(*, diameter_cm) -> float:
    """Scots pine roots < 5 cm dry weight (kg) — Marklund (1988) T-34.

    Source: Marklund (1988) Report 45, function T-34, printed p38.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-3.8375 + 8.8795 * (diameter_cm / (diameter_cm + 10)))


def Marklund_1988_T35(*, diameter_cm, site_index_pine_m, site_index_spruce_m) -> float:
    """Scots pine roots < 5 cm dry weight (kg) — Marklund (1988) T-35.

    Source: Marklund (1988) Report 45, function T-35, printed p38.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        site_index_pine_m: site index H100 for pine SItall [m] (0 if site indexed by spruce)
        site_index_spruce_m: site index H100 for spruce SIgran [m] (0 if site indexed by pine)
    """
    return np.exp(
        -3.5912
        + 8.9776 * (diameter_cm / (diameter_cm + 10))
        + -0.0162 * site_index_pine_m
        + -0.0123 * site_index_spruce_m
    )


def Marklund_1988_T36(
    *, diameter_cm, site_index_pine_m, site_index_spruce_m, altitude_km
) -> float:
    """Scots pine roots < 5 cm dry weight (kg) — Marklund (1988) T-36.

    Source: Marklund (1988) Report 45, function T-36, printed p39.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        site_index_pine_m: site index H100 for pine SItall [m] (0 if site indexed by spruce)
        site_index_spruce_m: site index H100 for spruce SIgran [m] (0 if site indexed by pine)
        altitude_km: altitude above sea level [km]
    """
    return np.exp(
        -3.3979
        + 8.9668 * (diameter_cm / (diameter_cm + 10))
        + -0.0204 * site_index_pine_m
        + -0.0168 * site_index_spruce_m
        + -0.4501 * altitude_km
    )


# Norway spruce (Picea abies) — stem over bark
def Marklund_1988_G1(*, diameter_cm) -> float:
    """Norway spruce stem over bark dry weight (kg) — Marklund (1988) G-1.

    Source: Marklund (1988) Report 45, function G-1, printed p40.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-2.0571 + 11.3341 * (diameter_cm / (diameter_cm + 14)))


def Marklund_1988_G2(*, diameter_cm, height_m) -> float:
    """Norway spruce stem over bark dry weight (kg) — Marklund (1988) G-2.

    Source: Marklund (1988) Report 45, function G-2, printed p40.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
    """
    return np.exp(
        -2.1702
        + 7.469 * (diameter_cm / (diameter_cm + 14))
        + 0.0289 * height_m
        + 0.6828 * np.log(height_m)
    )


def Marklund_1988_G3(
    *, diameter_cm, height_m, age_bh_years, form_quotient3, form_quotient5
) -> float:
    """Norway spruce stem over bark dry weight (kg) — Marklund (1988) G-3.

    Source: Marklund (1988) Report 45, function G-3, printed p41.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        age_bh_years: age at breast height [years]
        form_quotient3: form quotient d3/d [-] (0 if d3 not measured)
        form_quotient5: form quotient d5/d [-] (0 if d5 not measured)
    """
    return np.exp(
        -2.1781
        + 7.2601 * (diameter_cm / (diameter_cm + 14))
        + 0.0371 * height_m
        + 0.4803 * np.log(height_m)
        + 0.0934 * np.log(age_bh_years)
        + 0.2239 * form_quotient5
        + 0.1265 * form_quotient3
    )


# Norway spruce (Picea abies) — stem wood
def Marklund_1988_G4(*, diameter_cm) -> float:
    """Norway spruce stem wood dry weight (kg) — Marklund (1988) G-4.

    Source: Marklund (1988) Report 45, function G-4, printed p42.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-2.2471 + 11.4873 * (diameter_cm / (diameter_cm + 14)))


def Marklund_1988_G5(*, diameter_cm, height_m) -> float:
    """Norway spruce stem wood dry weight (kg) — Marklund (1988) G-5.

    Source: Marklund (1988) Report 45, function G-5, printed p42.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
    """
    return np.exp(
        -2.3032
        + 7.2309 * (diameter_cm / (diameter_cm + 14))
        + 0.0355 * height_m
        + 0.703 * np.log(height_m)
    )


def Marklund_1988_G6(
    *, diameter_cm, height_m, age_bh_years, form_quotient3, form_quotient5
) -> float:
    """Norway spruce stem wood dry weight (kg) — Marklund (1988) G-6.

    Source: Marklund (1988) Report 45, function G-6, printed p43.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        age_bh_years: age at breast height [years]
        form_quotient3: form quotient d3/d [-] (0 if d3 not measured)
        form_quotient5: form quotient d5/d [-] (0 if d5 not measured)
    """
    return np.exp(
        -2.2029
        + 7.0615 * (diameter_cm / (diameter_cm + 14))
        + 0.0448 * height_m
        + 0.4522 * np.log(height_m)
        + 0.0727 * np.log(age_bh_years)
        + 0.3154 * form_quotient5
        + 0.1467 * form_quotient3
    )


# Norway spruce (Picea abies) — stem bark
def Marklund_1988_G7(*, diameter_cm) -> float:
    """Norway spruce stem bark dry weight (kg) — Marklund (1988) G-7.

    Source: Marklund (1988) Report 45, function G-7, printed p44.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-3.3912 + 9.8364 * (diameter_cm / (diameter_cm + 15)))


def Marklund_1988_G8(*, diameter_cm, height_m) -> float:
    """Norway spruce stem bark dry weight (kg) — Marklund (1988) G-8.

    Source: Marklund (1988) Report 45, function G-8, printed p44.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
    """
    return np.exp(
        -3.402
        + 8.3089 * (diameter_cm / (diameter_cm + 15))
        + 0.0147 * height_m
        + 0.2295 * np.log(height_m)
    )


def Marklund_1988_G9(*, diameter_cm, height_m, site_index_pine_m, site_index_spruce_m) -> float:
    """Norway spruce stem bark dry weight (kg) — Marklund (1988) G-9.

    Source: Marklund (1988) Report 45, function G-9, printed p45.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        site_index_pine_m: site index H100 for pine SItall [m] (0 if site indexed by spruce)
        site_index_spruce_m: site index H100 for spruce SIgran [m] (0 if site indexed by pine)
    """
    return np.exp(
        -2.9427
        + 7.2807 * (diameter_cm / (diameter_cm + 15))
        + 0.0341 * height_m
        + 0.3363 * np.log(height_m)
        + -0.0203 * site_index_pine_m
        + -0.0208 * site_index_spruce_m
    )


def Marklund_1988_G10(
    *,
    diameter_cm,
    height_m,
    double_bark_mm,
    age_bh_years,
    max_diameter_cm,
    site_index_pine_m,
    site_index_spruce_m,
) -> float:
    """Norway spruce stem bark dry weight (kg) — Marklund (1988) G-10.

    Source: Marklund (1988) Report 45, function G-10, printed p45.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        double_bark_mm: double bark thickness at breast height [mm]
        age_bh_years: age at breast height [years]
        max_diameter_cm: diameter of thickest tree on a 10 m radius plot D_max [cm]
        site_index_pine_m: site index H100 for pine SItall [m] (0 if site indexed by spruce)
        site_index_spruce_m: site index H100 for spruce SIgran [m] (0 if site indexed by pine)
    """
    return np.exp(
        -3.1923
        + 6.5893 * (diameter_cm / (diameter_cm + 15))
        + 0.0353 * height_m
        + 0.2818 * np.log(height_m)
        + 0.1662 * np.log(double_bark_mm)
        + 0.1729 * np.log(age_bh_years)
        + -0.1836 * np.log(max_diameter_cm)
        + -0.00725 * site_index_pine_m
        + -0.00849 * site_index_spruce_m
    )


# Norway spruce (Picea abies) — living branches (incl. needles)
def Marklund_1988_G11(*, diameter_cm) -> float:
    """Norway spruce living branches (incl. needles) dry weight (kg) — Marklund (1988) G-11.

    Source: Marklund (1988) Report 45, function G-11, printed p46.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-1.2804 + 8.5242 * (diameter_cm / (diameter_cm + 13)))


def Marklund_1988_G12(*, diameter_cm, height_m) -> float:
    """Norway spruce living branches (incl. needles) dry weight (kg) — Marklund (1988) G-12.

    Source: Marklund (1988) Report 45, function G-12, printed p46.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
    """
    return np.exp(
        -1.2063
        + 10.9708 * (diameter_cm / (diameter_cm + 13))
        + -0.0124 * height_m
        + -0.4923 * np.log(height_m)
    )


def Marklund_1988_G13(
    *, diameter_cm, height_m, crown_base_height_m, site_index_pine_m, site_index_spruce_m
) -> float:
    """Norway spruce living branches (incl. needles) dry weight (kg) — Marklund (1988) G-13.

    Source: Marklund (1988) Report 45, function G-13, printed p47.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        crown_base_height_m: green crown base height krg [m]
        site_index_pine_m: site index H100 for pine SItall [m] (0 if site indexed by spruce)
        site_index_spruce_m: site index H100 for spruce SIgran [m] (0 if site indexed by pine)
    """
    return np.exp(
        -1.1209
        + 10.4621 * (diameter_cm / (diameter_cm + 13))
        + -1.5211 * np.log(height_m)
        + 1.0179 * np.log(height_m - crown_base_height_m)
        + 0.0121 * site_index_pine_m
        + 0.011 * site_index_spruce_m
    )


def Marklund_1988_G14(
    *,
    diameter_cm,
    height_m,
    age_bh_years,
    crown_base_height_m,
    crown_radius_m,
    diameter_increment_5yr_mm,
    max_diameter_cm,
) -> float:
    """Norway spruce living branches (incl. needles) dry weight (kg) — Marklund (1988) G-14.

    Source: Marklund (1988) Report 45, function G-14, printed p47.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        age_bh_years: age at breast height [years]
        crown_base_height_m: green crown base height krg [m]
        crown_radius_m: crown radius kr [m]
        diameter_increment_5yr_mm: last-5-year diameter increment i5 [mm]
        max_diameter_cm: diameter of thickest tree on a 10 m radius plot D_max [cm]
    """
    return np.exp(
        -1.3242
        + 8.0106 * (diameter_cm / (diameter_cm + 13))
        + -0.9993 * np.log(height_m)
        + 0.6623 * np.log(height_m - crown_base_height_m)
        + 0.5003 * np.log(crown_radius_m)
        + 0.2248 * np.log(age_bh_years)
        + 0.2518 * np.log(diameter_increment_5yr_mm)
        + -0.164 * np.log(max_diameter_cm)
    )


# Norway spruce (Picea abies) — needles
def Marklund_1988_G15(*, diameter_cm) -> float:
    """Norway spruce needles dry weight (kg) — Marklund (1988) G-15.

    Source: Marklund (1988) Report 45, function G-15, printed p48.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-1.9602 + 7.8171 * (diameter_cm / (diameter_cm + 12)))


def Marklund_1988_G16(*, diameter_cm, height_m) -> float:
    """Norway spruce needles dry weight (kg) — Marklund (1988) G-16.

    Source: Marklund (1988) Report 45, function G-16, printed p48.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
    """
    return np.exp(
        -1.8551 + 9.7809 * (diameter_cm / (diameter_cm + 12)) + -0.4873 * np.log(height_m)
    )


def Marklund_1988_G17(*, diameter_cm, height_m, crown_base_height_m) -> float:
    """Norway spruce needles dry weight (kg) — Marklund (1988) G-17.

    Source: Marklund (1988) Report 45, function G-17, printed p49.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        crown_base_height_m: green crown base height krg [m]
    """
    return np.exp(
        -1.5732
        + 8.4127 * (diameter_cm / (diameter_cm + 12))
        + -1.5628 * np.log(height_m)
        + 1.4032 * np.log(height_m - crown_base_height_m)
    )


def Marklund_1988_G18(
    *,
    diameter_cm,
    height_m,
    age_bh_years,
    crown_base_height_m,
    crown_radius_m,
    diameter_increment_5yr_mm,
    max_diameter_cm,
) -> float:
    """Norway spruce needles dry weight (kg) — Marklund (1988) G-18.

    Source: Marklund (1988) Report 45, function G-18, printed p49.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        age_bh_years: age at breast height [years]
        crown_base_height_m: green crown base height krg [m]
        crown_radius_m: crown radius kr [m]
        diameter_increment_5yr_mm: last-5-year diameter increment i5 [mm]
        max_diameter_cm: diameter of thickest tree on a 10 m radius plot D_max [cm]
    """
    return np.exp(
        -2.6982
        + 6.6949 * (diameter_cm / (diameter_cm + 12))
        + -0.8733 * np.log(height_m)
        + 0.7249 * np.log(height_m - crown_base_height_m)
        + 0.2066 * np.log(crown_radius_m)
        + 0.282 * np.log(age_bh_years)
        + 0.4526 * np.log(diameter_increment_5yr_mm)
        + -0.1467 * np.log(max_diameter_cm)
    )


# Norway spruce (Picea abies) — dead branches
def Marklund_1988_G19(*, diameter_cm) -> float:
    """Norway spruce dead branches dry weight (kg) — Marklund (1988) G-19.

    Source: Marklund (1988) Report 45, function G-19, printed p50.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-4.3308 + 9.955 * (diameter_cm / (diameter_cm + 18)))


def Marklund_1988_G20(*, diameter_cm, height_m) -> float:
    """Norway spruce dead branches dry weight (kg) — Marklund (1988) G-20.

    Source: Marklund (1988) Report 45, function G-20, printed p50.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
    """
    return np.exp(
        -4.6351
        + 3.6518 * (diameter_cm / (diameter_cm + 18))
        + 0.0493 * height_m
        + 1.0129 * np.log(height_m)
    )


def Marklund_1988_G21(*, diameter_cm, height_m, crown_base_height_m) -> float:
    """Norway spruce dead branches dry weight (kg) — Marklund (1988) G-21.

    Source: Marklund (1988) Report 45, function G-21, printed p51.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        crown_base_height_m: green crown base height krg [m]
    """
    return np.exp(
        -5.3924
        + 5.6333 * (diameter_cm / (diameter_cm + 18))
        + 2.7826 * np.log(height_m)
        + -1.746 * np.log(height_m - crown_base_height_m)
    )


def Marklund_1988_G22(
    *, diameter_cm, height_m, crown_base_height_m, diameter_increment_5yr_mm, max_diameter_cm
) -> float:
    """Norway spruce dead branches dry weight (kg) — Marklund (1988) G-22.

    Source: Marklund (1988) Report 45, function G-22, printed p51.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        crown_base_height_m: green crown base height krg [m]
        diameter_increment_5yr_mm: last-5-year diameter increment i5 [mm]
        max_diameter_cm: diameter of thickest tree on a 10 m radius plot D_max [cm]
    """
    return np.exp(
        -5.0472
        + 5.7144 * (diameter_cm / (diameter_cm + 18))
        + 1.7185 * np.log(height_m)
        + -0.5287 * np.log(height_m - crown_base_height_m)
        + -0.5739 * np.log(diameter_increment_5yr_mm)
        + 0.2804 * np.log(max_diameter_cm)
    )


# Norway spruce (Picea abies) — stump-root system
def Marklund_1988_G23(*, diameter_cm) -> float:
    """Norway spruce stump-root system dry weight (kg) — Marklund (1988) G-23.

    Source: Marklund (1988) Report 45, function G-23, printed p52.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-2.4447 + 10.5381 * (diameter_cm / (diameter_cm + 14)))


def Marklund_1988_G24(*, diameter_cm, site_index_pine_m, site_index_spruce_m) -> float:
    """Norway spruce stump-root system dry weight (kg) — Marklund (1988) G-24.

    Source: Marklund (1988) Report 45, function G-24, printed p52.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        site_index_pine_m: site index H100 for pine SItall [m] (0 if site indexed by spruce)
        site_index_spruce_m: site index H100 for spruce SIgran [m] (0 if site indexed by pine)
    """
    return np.exp(
        -2.081
        + 10.668 * (diameter_cm / (diameter_cm + 14))
        + -0.0162 * site_index_pine_m
        + -0.019 * site_index_spruce_m
    )


def Marklund_1988_G25(
    *,
    diameter_cm,
    site_index_pine_m,
    site_index_spruce_m,
    moist_soil,
    peat_soil,
    lateral_water_long,
) -> float:
    """Norway spruce stump-root system dry weight (kg) — Marklund (1988) G-25.

    Source: Marklund (1988) Report 45, function G-25, printed p53.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        site_index_pine_m: site index H100 for pine SItall [m] (0 if site indexed by spruce)
        site_index_spruce_m: site index H100 for spruce SIgran [m] (0 if site indexed by pine)
        moist_soil: indicator 1 if moist/wet firm land FUKT_MARK else 0
        peat_soil: indicator 1 if peat land TORV_MARK else 0
        lateral_water_long: indicator 1 if long-period lateral water LANG_OVSI else 0
    """
    return np.exp(
        -2.2616
        + 10.6277 * (diameter_cm / (diameter_cm + 14))
        + -0.0102 * site_index_pine_m
        + -0.0144 * site_index_spruce_m
        + 0.2237 * moist_soil
        + 0.2693 * peat_soil
        + -0.1919 * lateral_water_long
    )


# Norway spruce (Picea abies) — stump
def Marklund_1988_G26(*, diameter_cm) -> float:
    """Norway spruce stump dry weight (kg) — Marklund (1988) G-26.

    Source: Marklund (1988) Report 45, function G-26, printed p54.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-3.3645 + 10.6686 * (diameter_cm / (diameter_cm + 17)))


def Marklund_1988_G27(
    *, diameter_cm, site_index_pine_m, site_index_spruce_m, north_coordinate_100km
) -> float:
    """Norway spruce stump dry weight (kg) — Marklund (1988) G-27.

    Source: Marklund (1988) Report 45, function G-27, printed p54.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        site_index_pine_m: site index H100 for pine SItall [m] (0 if site indexed by spruce)
        site_index_spruce_m: site index H100 for spruce SIgran [m] (0 if site indexed by pine)
        north_coordinate_100km: RT90 north coordinate NKO [100 km units = northing_m/100000]
    """
    return np.exp(
        -0.8963
        + 10.6925 * (diameter_cm / (diameter_cm + 17))
        + -0.0196 * site_index_pine_m
        + -0.0188 * site_index_spruce_m
        + -0.0305 * north_coordinate_100km
    )


# Norway spruce (Picea abies) — roots >= 5 cm
def Marklund_1988_G28(*, diameter_cm) -> float:
    """Norway spruce roots >= 5 cm dry weight (kg) — Marklund (1988) G-28.

    Source: Marklund (1988) Report 45, function G-28, printed p55.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-6.3851 + 13.3703 * (diameter_cm / (diameter_cm + 8)))


def Marklund_1988_G29(*, diameter_cm, site_index_pine_m, site_index_spruce_m) -> float:
    """Norway spruce roots >= 5 cm dry weight (kg) — Marklund (1988) G-29.

    Source: Marklund (1988) Report 45, function G-29, printed p55.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        site_index_pine_m: site index H100 for pine SItall [m] (0 if site indexed by spruce)
        site_index_spruce_m: site index H100 for spruce SIgran [m] (0 if site indexed by pine)
    """
    return np.exp(
        -6.0559
        + 13.614 * (diameter_cm / (diameter_cm + 8))
        + -0.0204 * site_index_pine_m
        + -0.0211 * site_index_spruce_m
    )


def Marklund_1988_G30(
    *,
    diameter_cm,
    height_m,
    age_bh_years,
    site_index_pine_m,
    site_index_spruce_m,
    moist_soil,
    peat_soil,
    lateral_water_long,
) -> float:
    """Norway spruce roots >= 5 cm dry weight (kg) — Marklund (1988) G-30.

    Source: Marklund (1988) Report 45, function G-30, printed p56.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        age_bh_years: age at breast height [years]
        site_index_pine_m: site index H100 for pine SItall [m] (0 if site indexed by spruce)
        site_index_spruce_m: site index H100 for spruce SIgran [m] (0 if site indexed by pine)
        moist_soil: indicator 1 if moist/wet firm land FUKT_MARK else 0
        peat_soil: indicator 1 if peat land TORV_MARK else 0
        lateral_water_long: indicator 1 if long-period lateral water LANG_OVSI else 0
    """
    return np.exp(
        -5.9948
        + 12.5949 * (diameter_cm / (diameter_cm + 8))
        + 0.3864 * np.log(height_m)
        + -0.1114 * np.log(age_bh_years)
        + -0.0215 * site_index_pine_m
        + -0.0246 * site_index_spruce_m
        + 0.3267 * moist_soil
        + 0.4094 * peat_soil
        + -0.4444 * lateral_water_long
    )


# Norway spruce (Picea abies) — roots < 5 cm
def Marklund_1988_G31(*, diameter_cm) -> float:
    """Norway spruce roots < 5 cm dry weight (kg) — Marklund (1988) G-31.

    Source: Marklund (1988) Report 45, function G-31, printed p57.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-2.5706 + 7.6283 * (diameter_cm / (diameter_cm + 12)))


def Marklund_1988_G32(*, diameter_cm, site_index_pine_m, site_index_spruce_m) -> float:
    """Norway spruce roots < 5 cm dry weight (kg) — Marklund (1988) G-32.

    Source: Marklund (1988) Report 45, function G-32, printed p57.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        site_index_pine_m: site index H100 for pine SItall [m] (0 if site indexed by spruce)
        site_index_spruce_m: site index H100 for spruce SIgran [m] (0 if site indexed by pine)
    """
    return np.exp(
        -2.3177
        + 7.7441 * (diameter_cm / (diameter_cm + 12))
        + -0.0105 * site_index_pine_m
        + -0.0148 * site_index_spruce_m
    )


def Marklund_1988_G33(
    *, diameter_cm, site_index_pine_m, site_index_spruce_m, moist_soil, peat_soil
) -> float:
    """Norway spruce roots < 5 cm dry weight (kg) — Marklund (1988) G-33.

    Source: Marklund (1988) Report 45, function G-33, printed p58.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        site_index_pine_m: site index H100 for pine SItall [m] (0 if site indexed by spruce)
        site_index_spruce_m: site index H100 for spruce SIgran [m] (0 if site indexed by pine)
        moist_soil: indicator 1 if moist/wet firm land FUKT_MARK else 0
        peat_soil: indicator 1 if peat land TORV_MARK else 0
    """
    return np.exp(
        -2.4676
        + 7.7375 * (diameter_cm / (diameter_cm + 12))
        + -0.00675 * site_index_pine_m
        + -0.0117 * site_index_spruce_m
        + 0.1777 * moist_soil
        + 0.2461 * peat_soil
    )


# Birch (Betula pendula / pubescens) — stem over bark
def Marklund_1988_B1(*, diameter_cm) -> float:
    """Birch stem over bark dry weight (kg) — Marklund (1988) B-1.

    Source: Marklund (1988) Report 45, function B-1, printed p59.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-3.0932 + 11.0735 * (diameter_cm / (diameter_cm + 8)))


def Marklund_1988_B2(*, diameter_cm, height_m) -> float:
    """Birch stem over bark dry weight (kg) — Marklund (1988) B-2.

    Source: Marklund (1988) Report 45, function B-2, printed p59.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
    """
    return np.exp(
        -3.5686
        + 8.2827 * (diameter_cm / (diameter_cm + 7))
        + 0.0393 * height_m
        + 0.5772 * np.log(height_m)
    )


def Marklund_1988_B3(*, diameter_cm, height_m, age_bh_years) -> float:
    """Birch stem over bark dry weight (kg) — Marklund (1988) B-3.

    Source: Marklund (1988) Report 45, function B-3, printed p60.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        age_bh_years: age at breast height [years]
    """
    return np.exp(
        -3.5194
        + 8.042 * (diameter_cm / (diameter_cm + 7))
        + 0.0531 * height_m
        + 0.3897 * np.log(height_m)
        + 0.1018 * np.log(age_bh_years)
    )


# Birch (Betula pendula / pubescens) — stem wood
def Marklund_1988_B4(*, diameter_cm) -> float:
    """Birch stem wood dry weight (kg) — Marklund (1988) B-4.

    Source: Marklund (1988) Report 45, function B-4, printed p61.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-2.3327 + 10.8109 * (diameter_cm / (diameter_cm + 11)))


def Marklund_1988_B5(*, diameter_cm, height_m) -> float:
    """Birch stem wood dry weight (kg) — Marklund (1988) B-5.

    Source: Marklund (1988) Report 45, function B-5, printed p61.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
    """
    return np.exp(
        -3.3045 + 8.1184 * (diameter_cm / (diameter_cm + 11)) + 0.9783 * np.log(height_m)
    )


def Marklund_1988_B6(
    *, diameter_cm, height_m, double_bark_mm, age_bh_years, north_coordinate_100km
) -> float:
    """Birch stem wood dry weight (kg) — Marklund (1988) B-6.

    Source: Marklund (1988) Report 45, function B-6, printed p62.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        double_bark_mm: double bark thickness at breast height [mm]
        age_bh_years: age at breast height [years]
        north_coordinate_100km: RT90 north coordinate NKO [100 km units = northing_m/100000]
    """
    return np.exp(
        -3.0464
        + 8.382 * (diameter_cm / (diameter_cm + 11))
        + 0.9113 * np.log(height_m)
        + 0.1024 * np.log(age_bh_years)
        + -0.1067 * np.log(double_bark_mm)
        + -0.00552 * north_coordinate_100km
    )


# Birch (Betula pendula / pubescens) — stem bark
def Marklund_1988_B7(*, diameter_cm) -> float:
    """Birch stem bark dry weight (kg) — Marklund (1988) B-7.

    Source: Marklund (1988) Report 45, function B-7, printed p63.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-3.2518 + 10.3876 * (diameter_cm / (diameter_cm + 14)))


def Marklund_1988_B8(*, diameter_cm, height_m) -> float:
    """Birch stem bark dry weight (kg) — Marklund (1988) B-8.

    Source: Marklund (1988) Report 45, function B-8, printed p63.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
    """
    return np.exp(
        -4.0778 + 8.3019 * (diameter_cm / (diameter_cm + 14)) + 0.7433 * np.log(height_m)
    )


def Marklund_1988_B9(
    *, diameter_cm, height_m, double_bark_mm, age_bh_years, north_coordinate_100km
) -> float:
    """Birch stem bark dry weight (kg) — Marklund (1988) B-9.

    Source: Marklund (1988) Report 45, function B-9, printed p64.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        double_bark_mm: double bark thickness at breast height [mm]
        age_bh_years: age at breast height [years]
        north_coordinate_100km: RT90 north coordinate NKO [100 km units = northing_m/100000]
    """
    return np.exp(
        -3.643
        + 6.9285 * (diameter_cm / (diameter_cm + 14))
        + 0.5898 * np.log(height_m)
        + 0.2772 * np.log(age_bh_years)
        + 0.2038 * np.log(double_bark_mm)
        + -0.0137 * north_coordinate_100km
    )


def Marklund_1988_B10(
    *,
    diameter_cm,
    height_m,
    double_bark_mm,
    age_bh_years,
    diameter_increment_5yr_mm,
    max_diameter_cm,
    north_coordinate_100km,
) -> float:
    """Birch stem bark dry weight (kg) — Marklund (1988) B-10.

    Source: Marklund (1988) Report 45, function B-10, printed p64.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        double_bark_mm: double bark thickness at breast height [mm]
        age_bh_years: age at breast height [years]
        diameter_increment_5yr_mm: last-5-year diameter increment i5 [mm]
        max_diameter_cm: diameter of thickest tree on a 10 m radius plot D_max [cm]
        north_coordinate_100km: RT90 north coordinate NKO [100 km units = northing_m/100000]
    """
    return np.exp(
        -2.3569
        + 7.4965 * (diameter_cm / (diameter_cm + 14))
        + 0.5947 * np.log(height_m)
        + 0.182 * np.log(double_bark_mm)
        + 0.1972 * np.log(age_bh_years)
        + -0.1185 * np.log(diameter_increment_5yr_mm)
        + -0.1974 * np.log(max_diameter_cm)
        + -0.0182 * north_coordinate_100km
    )


# Birch (Betula pendula / pubescens) — living branches (incl. needles)
def Marklund_1988_B11(*, diameter_cm) -> float:
    """Birch living branches (incl. needles) dry weight (kg) — Marklund (1988) B-11.

    Source: Marklund (1988) Report 45, function B-11, printed p65.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-3.3633 + 10.2806 * (diameter_cm / (diameter_cm + 10)))


def Marklund_1988_B12(*, diameter_cm, height_m, north_coordinate_100km) -> float:
    """Birch living branches (incl. needles) dry weight (kg) — Marklund (1988) B-12.

    Source: Marklund (1988) Report 45, function B-12, printed p65.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        north_coordinate_100km: RT90 north coordinate NKO [100 km units = northing_m/100000]
    """
    return np.exp(
        0.0432
        + 12.7821 * (diameter_cm / (diameter_cm + 10))
        + -0.8525 * np.log(height_m)
        + -0.0409 * north_coordinate_100km
    )


def Marklund_1988_B13(
    *, diameter_cm, height_m, crown_base_height_m, north_coordinate_100km
) -> float:
    """Birch living branches (incl. needles) dry weight (kg) — Marklund (1988) B-13.

    Source: Marklund (1988) Report 45, function B-13, printed p66.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        crown_base_height_m: green crown base height krg [m]
        north_coordinate_100km: RT90 north coordinate NKO [100 km units = northing_m/100000]
    """
    return np.exp(
        0.0282
        + 10.7485 * (diameter_cm / (diameter_cm + 10))
        + -1.2066 * np.log(height_m)
        + 1.0409 * np.log(height_m - crown_base_height_m)
        + -0.0415 * north_coordinate_100km
    )


def Marklund_1988_B14(
    *,
    diameter_cm,
    height_m,
    age_bh_years,
    crown_base_height_m,
    crown_radius_m,
    diameter_increment_5yr_mm,
    north_coordinate_100km,
) -> float:
    """Birch living branches (incl. needles) dry weight (kg) — Marklund (1988) B-14.

    Source: Marklund (1988) Report 45, function B-14, printed p66.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        age_bh_years: age at breast height [years]
        crown_base_height_m: green crown base height krg [m]
        crown_radius_m: crown radius kr [m]
        diameter_increment_5yr_mm: last-5-year diameter increment i5 [mm]
        north_coordinate_100km: RT90 north coordinate NKO [100 km units = northing_m/100000]
    """
    return np.exp(
        -0.3916
        + 8.0492 * (diameter_cm / (diameter_cm + 10))
        + -1.1407 * np.log(height_m)
        + 0.7207 * np.log(height_m - crown_base_height_m)
        + 0.9133 * np.log(crown_radius_m)
        + 0.1702 * np.log(age_bh_years)
        + 0.1747 * np.log(diameter_increment_5yr_mm)
        + -0.032 * north_coordinate_100km
    )


# Birch (Betula pendula / pubescens) — dead branches
def Marklund_1988_B15(*, diameter_cm) -> float:
    """Birch dead branches dry weight (kg) — Marklund (1988) B-15.

    Source: Marklund (1988) Report 45, function B-15, printed p67.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
    """
    return np.exp(-5.9507 + 7.9266 * (diameter_cm / (diameter_cm + 5)))


def Marklund_1988_B16(*, diameter_cm, height_m) -> float:
    """Birch dead branches dry weight (kg) — Marklund (1988) B-16.

    Source: Marklund (1988) Report 45, function B-16, printed p67.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
    """
    return np.exp(
        -6.6237
        + 11.2872 * (diameter_cm / (diameter_cm + 30))
        + -0.3081 * height_m
        + 2.6821 * np.log(height_m)
    )


def Marklund_1988_B17(*, diameter_cm, height_m, north_coordinate_100km, altitude_km) -> float:
    """Birch dead branches dry weight (kg) — Marklund (1988) B-17.

    Source: Marklund (1988) Report 45, function B-17, printed p68.
    Units:
        diameter_cm: diameter over bark at breast height [cm]
        height_m: tree height [m]
        north_coordinate_100km: RT90 north coordinate NKO [100 km units = northing_m/100000]
        altitude_km: altitude above sea level [km]
    """
    return np.exp(
        -0.67
        + 12.0799 * (diameter_cm / (diameter_cm + 30))
        + -0.3448 * height_m
        + 2.7062 * np.log(height_m)
        + 1.5634 * altitude_km
        + -0.0914 * north_coordinate_100km
    )


# --- component dispatch lists (most predictors first) ---
_MarklundPineStem = [Marklund_1988_T4, Marklund_1988_T3, Marklund_1988_T2, Marklund_1988_T1]
_MarklundPineStemWood = [Marklund_1988_T8, Marklund_1988_T7, Marklund_1988_T6, Marklund_1988_T5]
_MarklundPineStemBark = [Marklund_1988_T12, Marklund_1988_T11, Marklund_1988_T10, Marklund_1988_T9]
_MarklundPineLivingBranches = [
    Marklund_1988_T16,
    Marklund_1988_T15,
    Marklund_1988_T14,
    Marklund_1988_T13,
]
_MarklundPineNeedles = [Marklund_1988_T20, Marklund_1988_T19, Marklund_1988_T18, Marklund_1988_T17]
_MarklundPineDeadBranches = [
    Marklund_1988_T24,
    Marklund_1988_T23,
    Marklund_1988_T22,
    Marklund_1988_T21,
]
_MarklundPineStumpRootSystem = [Marklund_1988_T27, Marklund_1988_T26, Marklund_1988_T25]
_MarklundPineStump = [Marklund_1988_T30, Marklund_1988_T29, Marklund_1988_T28]
_MarklundPineCoarseRoots = [Marklund_1988_T33, Marklund_1988_T32, Marklund_1988_T31]
_MarklundPineFineRoots = [Marklund_1988_T36, Marklund_1988_T35, Marklund_1988_T34]
_MarklundSpruceStem = [Marklund_1988_G3, Marklund_1988_G2, Marklund_1988_G1]
_MarklundSpruceStemWood = [Marklund_1988_G6, Marklund_1988_G5, Marklund_1988_G4]
_MarklundSpruceStemBark = [Marklund_1988_G10, Marklund_1988_G9, Marklund_1988_G8, Marklund_1988_G7]
_MarklundSpruceLivingBranches = [
    Marklund_1988_G14,
    Marklund_1988_G13,
    Marklund_1988_G12,
    Marklund_1988_G11,
]
_MarklundSpruceNeedles = [
    Marklund_1988_G18,
    Marklund_1988_G17,
    Marklund_1988_G16,
    Marklund_1988_G15,
]
_MarklundSpruceDeadBranches = [
    Marklund_1988_G22,
    Marklund_1988_G21,
    Marklund_1988_G20,
    Marklund_1988_G19,
]
_MarklundSpruceStumpRootSystem = [Marklund_1988_G25, Marklund_1988_G24, Marklund_1988_G23]
_MarklundSpruceStump = [Marklund_1988_G27, Marklund_1988_G26]
_MarklundSpruceCoarseRoots = [Marklund_1988_G30, Marklund_1988_G29, Marklund_1988_G28]
_MarklundSpruceFineRoots = [Marklund_1988_G33, Marklund_1988_G32, Marklund_1988_G31]
_MarklundBirchStem = [Marklund_1988_B3, Marklund_1988_B2, Marklund_1988_B1]
_MarklundBirchStemWood = [Marklund_1988_B6, Marklund_1988_B5, Marklund_1988_B4]
_MarklundBirchStemBark = [Marklund_1988_B10, Marklund_1988_B9, Marklund_1988_B8, Marklund_1988_B7]
_MarklundBirchLivingBranches = [
    Marklund_1988_B14,
    Marklund_1988_B13,
    Marklund_1988_B12,
    Marklund_1988_B11,
]
_MarklundBirchDeadBranches = [Marklund_1988_B17, Marklund_1988_B16, Marklund_1988_B15]

species_map = {
    "pinus sylvestris": {
        "stem": _MarklundPineStem,
        "stem_wood": _MarklundPineStemWood,
        "stem_bark": _MarklundPineStemBark,
        "living_branches": _MarklundPineLivingBranches,
        "needles": _MarklundPineNeedles,
        "dead_branches": _MarklundPineDeadBranches,
        "stump_root_system": _MarklundPineStumpRootSystem,
        "stump": _MarklundPineStump,
        "coarse_roots": _MarklundPineCoarseRoots,
        "fine_roots": _MarklundPineFineRoots,
    },
    "picea abies": {
        "stem": _MarklundSpruceStem,
        "stem_wood": _MarklundSpruceStemWood,
        "stem_bark": _MarklundSpruceStemBark,
        "living_branches": _MarklundSpruceLivingBranches,
        "needles": _MarklundSpruceNeedles,
        "dead_branches": _MarklundSpruceDeadBranches,
        "stump_root_system": _MarklundSpruceStumpRootSystem,
        "stump": _MarklundSpruceStump,
        "coarse_roots": _MarklundSpruceCoarseRoots,
        "fine_roots": _MarklundSpruceFineRoots,
    },
    "betula pendula": {
        "stem": _MarklundBirchStem,
        "stem_wood": _MarklundBirchStemWood,
        "stem_bark": _MarklundBirchStemBark,
        "living_branches": _MarklundBirchLivingBranches,
        "dead_branches": _MarklundBirchDeadBranches,
    },
    "betula pubescens": {
        "stem": _MarklundBirchStem,
        "stem_wood": _MarklundBirchStemWood,
        "stem_bark": _MarklundBirchStemBark,
        "living_branches": _MarklundBirchLivingBranches,
        "dead_branches": _MarklundBirchDeadBranches,
    },
}


_COMPONENT_ORDER = [
    "stem",
    "stem_wood",
    "stem_bark",
    "living_branches",
    "needles",
    "dead_branches",
    "stump_root_system",
    "stump",
    "coarse_roots",
    "fine_roots",
]


def _select_and_call(functions, kwargs):
    """Return the value of the most detailed function whose inputs are all supplied.

    ``functions`` is ordered most-predictors-first; the first function whose every
    keyword-only parameter is present in ``kwargs`` is evaluated. Returns ``None`` if
    none can be satisfied.
    """
    import inspect

    for func in functions:
        required = list(inspect.signature(func).parameters)
        if all(name in kwargs and kwargs[name] is not None for name in required):
            return float(func(**{name: kwargs[name] for name in required}))
    return None


def Marklund_1988(species=None, component=None, *, timber=None, **kwargs):
    """Dry-weight biomass (kg) for a single tree following Marklund (1988), Report 45.

    Selects the most detailed published function for each requested component whose
    required inputs are supplied. Pass a :class:`~pyforestry.base.timber.Timber` /
    :class:`~pyforestry.sweden.timber.SweTimber` as the first argument, or give
    ``species`` plus the measured variables as keywords (units per the kernel
    docstrings, e.g. ``diameter_cm``, ``height_m``, ``double_bark_mm``,
    ``crown_base_height_m``, ``age_bh_years``, ``site_index_pine_m`` ...).

    Args:
        species: Canonical species string (e.g. ``"pinus sylvestris"``) or a timber
            object as the first positional argument.
        component: One of the keys in :data:`species_map` for the species. If omitted,
            a dict of every computable component is returned.
        timber: Optional timber object (alternative to passing it positionally).
        **kwargs: Measured predictor values (see kernel docstrings for units).

    Returns:
        A ``float`` biomass in kg for a single ``component``, else a ``dict`` mapping
        each computable component to its biomass in kg.

    Raises:
        ValueError: Unknown species/component, or no function matched the inputs.

    Source:
        Marklund, L.-G. (1988). Biomassafunktioner för tall, gran och björk i Sverige
        [Biomass functions for pine, spruce and birch in Sweden]. Report 45,
        Dept. of Forest Survey, Swedish University of Agricultural Sciences, Umeå.
    """
    if species is not None and not isinstance(species, str):
        timber = species
        species = None
    if timber is not None:
        species = getattr(timber, "species", None)
        for attr in ("diameter_cm", "height_m", "double_bark_mm", "crown_base_height_m"):
            value = getattr(timber, attr, None)
            if value is not None:
                kwargs.setdefault(attr, value)

    if not species:
        raise ValueError("Species must be specified either directly or through a Timber object.")
    species = species.strip().lower()
    if species not in species_map:
        raise ValueError(f"Unknown species: {species}")

    if component is not None:
        if component not in species_map[species]:
            raise ValueError(f"Unknown component for species {species}: {component}")
        value = _select_and_call(species_map[species][component], kwargs)
        if value is None:
            raise ValueError("No function matched the provided arguments.")
        return value

    results = {}
    for comp in _COMPONENT_ORDER:
        functions = species_map[species].get(comp)
        if not functions:
            continue
        value = _select_and_call(functions, kwargs)
        if value is not None:
            results[comp] = value
    return results


class _Descriptor:
    """FormulaModuleDescriptor for Marklund, L.-G. (1988), Report 45."""

    @property
    def component_id(self):
        """Stable identifier for this formula module."""
        return "marklund_1988_biomass"

    @property
    def source(self):
        """Bibliographic provenance for this formula module."""
        from pyforestry.simulation.contracts import SourceReference

        return SourceReference(
            author="Marklund, L.-G.",
            year=1988,
            title="Biomassafunktioner för tall, gran och björk i Sverige",
            appendix="Report 45",
            note=(
                "Sveriges lantbruksuniversitet, institutionen för skogstaxering, "
                "Rapport 45, Umeå, 73 s. ISBN 91-576-3524-2. Dry-weight component "
                "functions; constants include the bias correction for the log "
                "back-transformation. Spruce functions largely follow Marklund (1987), "
                "'Biomass functions for Norway spruce (Picea abies (L.) Karst.) in "
                "Sweden', Rapport 43, with corrected constants."
            ),
        )

    @property
    def species_groups(self):
        """Species groups and their constituent scientific names."""
        return {
            "pine": frozenset({"Pinus sylvestris"}),
            "spruce": frozenset({"Picea abies"}),
            "birch": frozenset({"Betula pendula", "Betula pubescens"}),
        }

    @property
    def units(self):
        """Unit contract for the module outputs."""
        return {"output": "kg (dry weight)"}

    @property
    def kernel_names(self):
        """Public callables exposed by this formula module."""
        return ("Marklund_1988",)


DESCRIPTOR = _Descriptor()

__all__ = [
    "Marklund_1988",
    "species_map",
    "DESCRIPTOR",
    "Marklund_1988_T1",
    "Marklund_1988_T2",
    "Marklund_1988_T3",
    "Marklund_1988_T4",
    "Marklund_1988_T5",
    "Marklund_1988_T6",
    "Marklund_1988_T7",
    "Marklund_1988_T8",
    "Marklund_1988_T9",
    "Marklund_1988_T10",
    "Marklund_1988_T11",
    "Marklund_1988_T12",
    "Marklund_1988_T13",
    "Marklund_1988_T14",
    "Marklund_1988_T15",
    "Marklund_1988_T16",
    "Marklund_1988_T17",
    "Marklund_1988_T18",
    "Marklund_1988_T19",
    "Marklund_1988_T20",
    "Marklund_1988_T21",
    "Marklund_1988_T22",
    "Marklund_1988_T23",
    "Marklund_1988_T24",
    "Marklund_1988_T25",
    "Marklund_1988_T26",
    "Marklund_1988_T27",
    "Marklund_1988_T28",
    "Marklund_1988_T29",
    "Marklund_1988_T30",
    "Marklund_1988_T31",
    "Marklund_1988_T32",
    "Marklund_1988_T33",
    "Marklund_1988_T34",
    "Marklund_1988_T35",
    "Marklund_1988_T36",
    "Marklund_1988_G1",
    "Marklund_1988_G2",
    "Marklund_1988_G3",
    "Marklund_1988_G4",
    "Marklund_1988_G5",
    "Marklund_1988_G6",
    "Marklund_1988_G7",
    "Marklund_1988_G8",
    "Marklund_1988_G9",
    "Marklund_1988_G10",
    "Marklund_1988_G11",
    "Marklund_1988_G12",
    "Marklund_1988_G13",
    "Marklund_1988_G14",
    "Marklund_1988_G15",
    "Marklund_1988_G16",
    "Marklund_1988_G17",
    "Marklund_1988_G18",
    "Marklund_1988_G19",
    "Marklund_1988_G20",
    "Marklund_1988_G21",
    "Marklund_1988_G22",
    "Marklund_1988_G23",
    "Marklund_1988_G24",
    "Marklund_1988_G25",
    "Marklund_1988_G26",
    "Marklund_1988_G27",
    "Marklund_1988_G28",
    "Marklund_1988_G29",
    "Marklund_1988_G30",
    "Marklund_1988_G31",
    "Marklund_1988_G32",
    "Marklund_1988_G33",
    "Marklund_1988_B1",
    "Marklund_1988_B2",
    "Marklund_1988_B3",
    "Marklund_1988_B4",
    "Marklund_1988_B5",
    "Marklund_1988_B6",
    "Marklund_1988_B7",
    "Marklund_1988_B8",
    "Marklund_1988_B9",
    "Marklund_1988_B10",
    "Marklund_1988_B11",
    "Marklund_1988_B12",
    "Marklund_1988_B13",
    "Marklund_1988_B14",
    "Marklund_1988_B15",
    "Marklund_1988_B16",
    "Marklund_1988_B17",
]
