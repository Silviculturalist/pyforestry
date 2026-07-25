"""Scientific kernel equations for Elfving (2010) growth."""

from __future__ import annotations

from math import exp, log, sqrt


def pine_ln_d2_growth(
    *,
    diameter_cm: float,
    bal_over_dbh: float,
    age_bh_years: float,
    overstorey: int,
    mean_dgv_cm: float,
    basal_area_m2_ha: float,
    basal_area_pines_m2_ha: float,
    gotland: int,
    temperature_sum_dd: float,
    site_index_m: float,
    rich: int,
    fertilized: int,
    thinned_0_10_years_flag: int,
    thinned_11_25_years_flag: int,
    split: int,
    edge: int,
    field_ba_m2_ha: float,
) -> float:
    """Log D² growth for pine-group trees."""
    temp = ((basal_area_m2_ha - basal_area_pines_m2_ha) / basal_area_m2_ha) ** 2
    ts_scaled = temperature_sum_dd * 0.001
    return (
        3.4176
        + 1.0149 * log(diameter_cm + 1.0)
        + -0.3902 * bal_over_dbh
        + -0.7730 * log(age_bh_years + 20.0)
        + 0.2218 * overstorey
        + 0.1843 * mean_dgv_cm * 0.1
        + -0.3145 * log(basal_area_m2_ha + 3.0)
        + 0.1391 * temp
        + -0.0844 * gotland
        + 0.1178 * (ts_scaled**2)
        + 1.0890 * site_index_m * 0.1
        + -0.2164 * (site_index_m**2) * 0.01
        + 0.1011 * rich
        + 0.2790 * fertilized
        + 0.1245 * thinned_0_10_years_flag
        + 0.0451 * thinned_11_25_years_flag
        + 0.0487 * split
        + 0.1368 * edge
        + 0.0842 * log(basal_area_m2_ha / field_ba_m2_ha)
    )


def spruce_ln_d2_growth(
    *,
    diameter_cm: float,
    bal_over_dbh: float,
    age_bh_years: float,
    overstorey: int,
    mean_dgv_cm: float,
    mean_dg_cm: float,
    basal_area_m2_ha: float,
    basal_area_spruce_m2_ha: float,
    gotland: int,
    temperature_sum_dd: float,
    site_index_m: float,
    rich: int,
    fertilized: int,
    thinned_0_10_years_flag: int,
    split: int,
    edge: int,
    field_ba_m2_ha: float,
) -> float:
    """Log D² growth for spruce-group trees."""
    temp1 = min(mean_dgv_cm - mean_dg_cm, 10.0)
    temp = bal_over_dbh * (temp1 / mean_dgv_cm) ** 3 if mean_dgv_cm > 0 else 0.0
    temp2 = bal_over_dbh * ((basal_area_m2_ha - basal_area_spruce_m2_ha) / basal_area_m2_ha)
    temp3 = ((basal_area_m2_ha - basal_area_spruce_m2_ha) / basal_area_m2_ha) ** 2
    ts_scaled = temperature_sum_dd * 0.001
    return (
        3.4360
        + 1.5163 * log(diameter_cm + 1.0)
        + -0.1520 * diameter_cm * 0.1
        + -0.4024 * bal_over_dbh
        + 0.4702 * temp
        + -0.7789 * log(age_bh_years + 20.0)
        + 0.4034 * overstorey
        + 0.1914 * (mean_dgv_cm**2) * 0.001
        + -0.2342 * log(basal_area_m2_ha + 3.0)
        + 0.1625 * temp2
        + 0.1754 * temp3
        + -0.3264 * gotland
        + -0.6923 * ts_scaled
        + 0.2568 * (ts_scaled**2)
        + 0.2903 * site_index_m * 0.1
        + 0.1965 * rich
        + 0.4034 * fertilized
        + 0.1309 * thinned_0_10_years_flag
        + 0.0561 * split
        + 0.1126 * edge
        + 0.0770 * log(basal_area_m2_ha / field_ba_m2_ha)
    )


def birch_ln_d2_growth(
    *,
    diameter_cm: float,
    bal_over_dbh: float,
    age_bh_years: float,
    overstorey: int,
    basal_area_m2_ha: float,
    basal_area_birch_m2_ha: float,
    temperature_sum_dd: float,
    distance_to_coast_km: float,
    rich: int,
    fertilized: int,
    thinned_0_10_years_flag: int,
    edge: int,
    field_ba_m2_ha: float,
) -> float:
    """Log D² growth for birch-group trees."""
    ts_scaled = temperature_sum_dd * 0.001
    return (
        5.9648
        + 1.2217 * log(diameter_cm + 1.0)
        + -0.3998 * bal_over_dbh
        + -0.9226 * log(age_bh_years + 20.0)
        + 0.4772 * overstorey
        + -0.2090 * log(basal_area_m2_ha + 3.0)
        + -0.5821 * sqrt(basal_area_birch_m2_ha / basal_area_m2_ha)
        + -0.5386 * ts_scaled
        + -0.4505 * (1.0 / (ts_scaled - 0.3))
        + 0.8801 * (1.0 / (distance_to_coast_km / 10.0 + 3.0))
        + 0.3439 * rich
        + 0.3844 * fertilized
        + 0.1814 * thinned_0_10_years_flag
        + 0.2258 * edge
        + 0.1321 * log(basal_area_m2_ha / field_ba_m2_ha)
    )


def aspen_ln_d2_growth(
    *,
    diameter_cm: float,
    bal_over_dbh: float,
    age_bh_years: float,
    basal_area_m2_ha: float,
    basal_area_aspen_m2_ha: float,
    temperature_sum_dd: float,
    rich: int,
    thinned_0_10_years_flag: int,
    field_ba_m2_ha: float,
) -> float:
    """Log D² growth for aspen-group trees."""
    ts_scaled = temperature_sum_dd * 0.001
    return (
        0.9945
        + 1.9071 * log(diameter_cm + 1.0)
        + -0.3313 * diameter_cm * 0.1
        + -0.3040 * bal_over_dbh
        + -0.4058 * log(age_bh_years + 20.0)
        + -0.1981 * log(basal_area_m2_ha + 3.0)
        + -0.5967 * sqrt(basal_area_aspen_m2_ha / basal_area_m2_ha)
        + 0.4408 * ts_scaled
        + 0.4759 * rich
        + 0.2143 * thinned_0_10_years_flag
        + 0.2427 * log(basal_area_m2_ha / field_ba_m2_ha)
    )


def beech_ln_d2_growth(
    *,
    diameter_cm: float,
    bal_over_dbh: float,
    age_bh_years: float,
    basal_area_m2_ha: float,
    basal_area_beech_m2_ha: float,
    latitude_deg: float,
    site_index_m: float,
    thinned_0_10_years_flag: int,
    split: int,
    field_ba_m2_ha: float,
) -> float:
    """Log D² growth for beech-group trees."""
    return (
        1.7005
        + 2.5823 * log(diameter_cm + 1.0)
        + -0.3758 * diameter_cm * 0.1
        + -0.2079 * bal_over_dbh
        + -0.4478 * log(age_bh_years + 20.0)
        + -0.5348 * log(basal_area_m2_ha + 3.0)
        + -0.9304 * sqrt(basal_area_beech_m2_ha / basal_area_m2_ha)
        + -0.1906 * (latitude_deg - 50.0)
        + 0.3055 * site_index_m * 0.1
        + 0.2200 * thinned_0_10_years_flag
        + 0.2009 * split
        + 0.2669 * log(basal_area_m2_ha / field_ba_m2_ha)
    )


def oak_ln_d2_growth(
    *,
    diameter_cm: float,
    bal_over_dbh: float,
    basal_area_m2_ha: float,
    basal_area_oak_m2_ha: float,
    gotland: int,
    altitude_m: float,
    rich: int,
    thinned_0_10_years_flag: int,
    edge: int,
    field_ba_m2_ha: float,
) -> float:
    """Log D² growth for oak-group trees."""
    alt_scaled = altitude_m * 0.01
    return (
        1.9047
        + 1.3115 * log(diameter_cm + 1.0)
        + -0.2640 * bal_over_dbh
        + -0.5056 * log(basal_area_m2_ha + 3.0)
        + -0.6001 * sqrt(basal_area_oak_m2_ha / basal_area_m2_ha)
        + -0.4615 * gotland
        + 0.3833 * alt_scaled
        + -0.1938 * (alt_scaled**2)
        + 0.2635 * rich
        + 0.1034 * thinned_0_10_years_flag
        + 0.3551 * edge
        + 0.1897 * log(basal_area_m2_ha / field_ba_m2_ha)
    )


def precious_ln_d2_growth(
    *,
    diameter_cm: float,
    bal_over_dbh: float,
    basal_area_m2_ha: float,
    gotland: int,
    herb: int,
    thinned_0_10_years_flag: int,
    field_ba_m2_ha: float,
) -> float:
    """Log D² growth for precious broadleaves."""
    return (
        2.3316
        + 0.8250 * log(diameter_cm + 1.0)
        + -0.2877 * bal_over_dbh
        + -0.4010 * log(basal_area_m2_ha + 3.0)
        + -0.3809 * gotland
        + 0.9397 * herb
        + 0.2410 * thinned_0_10_years_flag
        + 0.4676 * log(basal_area_m2_ha / field_ba_m2_ha)
    )


def trivial_ln_d2_growth(
    *,
    diameter_cm: float,
    bal_over_dbh: float,
    age_bh_years: float,
    basal_area_m2_ha: float,
    site_index_m: float,
    herb: int,
    thinned_0_10_years_flag: int,
) -> float:
    """Log D² growth for trivial broadleaves."""
    return (
        2.1108
        + 0.9418 * log(diameter_cm + 1.0)
        + -0.2511 * bal_over_dbh
        + -0.3026 * log(age_bh_years + 20.0)
        + -0.2280 * log(basal_area_m2_ha + 3.0)
        + 0.2595 * site_index_m * 0.1
        + 0.4392 * herb
        + 0.1561 * thinned_0_10_years_flag
    )


def stand_basal_area_growth_elfving_2009(
    *,
    ln_mean_age: float,
    conifer_share_per_age: float,
    pine_share_times_veg: float,
    birch_share_sq: float,
    birch_share_cold: float,
    basal_area_survived_m2_ha: float,
    basal_area_all_m2_ha: float,
    stem_number_factor: float,
    veg: float,
    peat: int,
    moist: int,
    wet: int,
    site_index_m: float,
    ditch: int,
    fertilized: int,
    edge: int,
    split: int,
    thinned_0_10_years_flag: int,
    thinned_10_30_years_flag: int,
    ln_relative_basal_area: float,
    pine_share: float,
    spruce_share: float,
    use_edge_effects: bool,
) -> float:
    """Compute stand basal-area growth (m²/ha) over 5 years.

    Elfving (2009) stand-level basal-area growth function. Parameter names below map
    to Elfving's original symbols as follows:

    - ``ln_mean_age`` -> ln of mean stand age.
    - ``conifer_share_per_age`` -> (pine share + spruce share) / mean age.
    - ``pine_share_times_veg`` -> pine share * vegetation index.
    - ``birch_share_sq`` -> (birch basal-area share) squared.
    - ``birch_share_cold`` -> birch basal-area share * cold-climate term.
    - ``stem_number_factor`` -> stems / (stems + 80).
    - ``ln_relative_basal_area`` -> ln(BA / surrounding BA).
    - ``pine_share`` / ``spruce_share`` -> pine / spruce basal-area shares.
    """
    if basal_area_survived_m2_ha <= 0:
        return 0.0
    edge_term = 0.076 * edge if use_edge_effects else 0.0
    split_term = 0.0607 * split if use_edge_effects else 0.0
    ln_relative_basal_area_term = 0.1163 * ln_relative_basal_area if use_edge_effects else 0.0

    return exp(
        0.366
        + -0.5842 * ln_mean_age
        + 8.374 * conifer_share_per_age
        + -0.0237 * pine_share_times_veg
        + -0.3192 * birch_share_sq
        + -10.8034 * birch_share_cold
        + 0.5002 * log(basal_area_survived_m2_ha)
        + -0.00632 * basal_area_all_m2_ha
        + 1.376 * stem_number_factor
        + 0.0627 * veg
        + -0.0244 * peat
        + -0.0498 * moist
        + -0.1807 * wet
        + 0.0109 * site_index_m
        + 0.0542 * ditch
        + 0.3065 * fertilized
        + edge_term
        + split_term
        + 0.1396 * thinned_0_10_years_flag
        + 0.0567 * thinned_10_30_years_flag
        + ln_relative_basal_area_term
        + -0.06 * pine_share
        + -0.03 * spruce_share
    )


__all__ = [
    "aspen_ln_d2_growth",
    "beech_ln_d2_growth",
    "birch_ln_d2_growth",
    "oak_ln_d2_growth",
    "pine_ln_d2_growth",
    "precious_ln_d2_growth",
    "spruce_ln_d2_growth",
    "stand_basal_area_growth_elfving_2009",
    "trivial_ln_d2_growth",
]
