"""Oracle tests for Marklund (1988) Report 45 biomass functions.

Every expected value below is written inline from the coefficients printed in Report 45
(one representative function per species x component, plus fully-specified higher-order
variants), so the module is pinned to the primary source. A smoke test exercises all 86
functions, and genus-distinctness guards against the historical cross-species copy bug.
"""

import inspect

import numpy as np
import pytest

import pyforestry.sweden.biomass.marklund_1988 as M


def ln(x):
    return np.log(x)


# One base (diameter-only or diameter+height) function per species x component.
# Each row: (kernel name, kwargs, expected value from the Report-45 coefficients).
BASE_CASES = [
    # --- Scots pine (TALL) ---
    ("Marklund_1988_T1", dict(diameter_cm=20), np.exp(-2.3388 + 11.3264 * (20 / (20 + 13)))),
    ("Marklund_1988_T5", dict(diameter_cm=20), np.exp(-2.2184 + 11.4219 * (20 / (20 + 14)))),
    ("Marklund_1988_T9", dict(diameter_cm=20), np.exp(-2.9748 + 8.8489 * (20 / (20 + 16)))),
    ("Marklund_1988_T13", dict(diameter_cm=20), np.exp(-2.8604 + 9.1015 * (20 / (20 + 10)))),
    ("Marklund_1988_T17", dict(diameter_cm=20), np.exp(-3.7983 + 7.7681 * (20 / (20 + 7)))),
    ("Marklund_1988_T21", dict(diameter_cm=20), np.exp(-5.3338 + 9.5938 * (20 / (20 + 10)))),
    ("Marklund_1988_T25", dict(diameter_cm=20), np.exp(-3.3913 + 11.1106 * (20 / (20 + 12)))),
    ("Marklund_1988_T28", dict(diameter_cm=20), np.exp(-3.9657 + 11.0481 * (20 / (20 + 15)))),
    ("Marklund_1988_T31", dict(diameter_cm=20), np.exp(-6.3413 + 13.2902 * (20 / (20 + 9)))),
    ("Marklund_1988_T34", dict(diameter_cm=20), np.exp(-3.8375 + 8.8795 * (20 / (20 + 10)))),
    # --- Norway spruce (GRAN) --- components missing/wrong in the old module
    ("Marklund_1988_G1", dict(diameter_cm=20), np.exp(-2.0571 + 11.3341 * (20 / (20 + 14)))),
    ("Marklund_1988_G4", dict(diameter_cm=20), np.exp(-2.2471 + 11.4873 * (20 / (20 + 14)))),
    ("Marklund_1988_G7", dict(diameter_cm=20), np.exp(-3.3912 + 9.8364 * (20 / (20 + 15)))),
    ("Marklund_1988_G15", dict(diameter_cm=20), np.exp(-1.9602 + 7.8171 * (20 / (20 + 12)))),
    ("Marklund_1988_G19", dict(diameter_cm=20), np.exp(-4.3308 + 9.955 * (20 / (20 + 18)))),
    ("Marklund_1988_G28", dict(diameter_cm=20), np.exp(-6.3851 + 13.3703 * (20 / (20 + 8)))),
    ("Marklund_1988_G31", dict(diameter_cm=20), np.exp(-2.5706 + 7.6283 * (20 / (20 + 12)))),
    # --- Birch (BJORK) ---
    ("Marklund_1988_B1", dict(diameter_cm=20), np.exp(-3.0932 + 11.0735 * (20 / (20 + 8)))),
    ("Marklund_1988_B4", dict(diameter_cm=20), np.exp(-2.3327 + 10.8109 * (20 / (20 + 11)))),
    ("Marklund_1988_B7", dict(diameter_cm=20), np.exp(-3.2518 + 10.3876 * (20 / (20 + 14)))),
    ("Marklund_1988_B11", dict(diameter_cm=20), np.exp(-3.3633 + 10.2806 * (20 / (20 + 10)))),
    ("Marklund_1988_B15", dict(diameter_cm=20), np.exp(-5.9507 + 7.9266 * (20 / (20 + 5)))),
]


@pytest.mark.parametrize("name, kwargs, expected", BASE_CASES)
def test_base_functions_match_report45(name, kwargs, expected):
    assert float(getattr(M, name)(**kwargs)) == pytest.approx(expected, rel=1e-9)


def test_pine_stump_root_higher_order_T27():
    """T-27 uses site index, soil-moisture and lateral-water indicators."""
    got = M.Marklund_1988_T27(
        diameter_cm=20,
        age_bh_years=60,
        site_index_pine_m=24.0,
        site_index_spruce_m=0.0,
        altitude_km=0.2,
        dry_soil=0,
        moist_soil=1,
        peat_soil=0,
        lateral_water_long=0,
        lateral_water_short=0,
    )
    expected = np.exp(
        -3.1638
        + 10.7181 * (20 / (20 + 12))
        + 0.0952 * ln(60)
        - 0.0168 * 24.0
        - 0.0136 * 0.0
        - 0.0808 * 0
        + 0.2165 * 1
        + 0.3088 * 0
        - 0.1655 * 0
        - 0.107 * 0
        - 0.5221 * 0.2
    )
    assert float(got) == pytest.approx(expected, rel=1e-9)


def test_spruce_stem_bark_higher_order_G10():
    """G-10 uses bark, age, D_max and site index."""
    got = M.Marklund_1988_G10(
        diameter_cm=25,
        height_m=17,
        double_bark_mm=8,
        age_bh_years=60,
        max_diameter_cm=30,
        site_index_pine_m=0.0,
        site_index_spruce_m=26.0,
    )
    expected = np.exp(
        -3.1923
        + 6.5893 * (25 / (25 + 15))
        + 0.0353 * 17
        + 0.2818 * ln(17)
        + 0.1662 * ln(8)
        + 0.1729 * ln(60)
        - 0.1836 * ln(30)
        - 0.00725 * 0.0
        - 0.00849 * 26.0
    )
    assert float(got) == pytest.approx(expected, rel=1e-9)


def test_birch_stem_bark_higher_order_B10():
    """B-10 uses bark, age, i5, D_max and the north coordinate NKO."""
    got = M.Marklund_1988_B10(
        diameter_cm=22,
        height_m=16,
        double_bark_mm=6,
        age_bh_years=50,
        diameter_increment_5yr_mm=12,
        max_diameter_cm=28,
        north_coordinate_100km=66.0,
    )
    expected = np.exp(
        -2.3569
        + 7.4965 * (22 / (22 + 14))
        + 0.5947 * ln(16)
        + 0.182 * ln(6)
        + 0.1972 * ln(50)
        - 0.1185 * ln(12)
        - 0.1974 * ln(28)
        - 0.0182 * 66.0
    )
    assert float(got) == pytest.approx(expected, rel=1e-9)


def test_relative_bark_thickness_derived_internally():
    """T-11 uses relative bark thickness bt% = bt / (d*10) * 100, derived from bt and d."""
    got = M.Marklund_1988_T11(diameter_cm=25, height_m=18, double_bark_mm=12)
    bt_pct = 12 / (25 * 10.0) * 100.0
    expected = np.exp(-3.6065 + 7.0834 * (25 / (25 + 16)) + 0.5086 * ln(18) + 0.0255 * bt_pct)
    assert float(got) == pytest.approx(expected, rel=1e-9)


@pytest.mark.parametrize(
    "pine, spruce, birch",
    [
        ("Marklund_1988_T1", "Marklund_1988_G1", "Marklund_1988_B1"),  # stem over bark
        ("Marklund_1988_T21", "Marklund_1988_G19", "Marklund_1988_B15"),  # dead branches
    ],
)
def test_genus_distinct(pine, spruce, birch):
    """Guards the historical bug where birch==spruce and spruce/pine shared coefficients."""
    vals = {
        round(float(getattr(M, pine)(diameter_cm=20)), 6),
        round(float(getattr(M, spruce)(diameter_cm=20)), 6),
        round(float(getattr(M, birch)(diameter_cm=20)), 6),
    }
    assert len(vals) == 3


_STD_TREE = dict(
    diameter_cm=22,
    height_m=17,
    double_bark_mm=8,
    age_bh_years=60,
    crown_base_height_m=8,
    crown_radius_m=2.0,
    form_quotient3=0.0,
    form_quotient5=0.72,
    diameter_increment_5yr_mm=12.0,
    max_diameter_cm=30.0,
    site_index_pine_m=24.0,
    site_index_spruce_m=0.0,
    north_coordinate_100km=66.0,
    altitude_km=0.2,
    dry_soil=0,
    moist_soil=0,
    peat_soil=0,
    lateral_water_long=0,
    lateral_water_short=0,
    lateral_water_any=0,
)


def _all_kernels():
    return [getattr(M, n) for n in dir(M) if n.startswith("Marklund_1988_")]


def test_all_86_functions_present():
    assert len(_all_kernels()) == 86


@pytest.mark.parametrize("kernel", _all_kernels(), ids=lambda k: k.__name__)
def test_every_kernel_positive_and_finite(kernel):
    params = list(inspect.signature(kernel).parameters)
    value = float(kernel(**{p: _STD_TREE[p] for p in params}))
    assert np.isfinite(value) and value > 0.0


def test_component_inventory_matches_report():
    """Report 45: spruce has needles + roots; birch has no needles and no stump/roots."""
    pine = set(M.species_map["pinus sylvestris"])
    spruce = set(M.species_map["picea abies"])
    birch = set(M.species_map["betula pendula"])
    roots = {"stump_root_system", "stump", "coarse_roots", "fine_roots"}
    assert roots <= pine and roots <= spruce
    assert "needles" in pine and "needles" in spruce
    assert "needles" not in birch
    assert not (roots & birch)
    assert {"stem_wood", "stem_bark"} <= birch
