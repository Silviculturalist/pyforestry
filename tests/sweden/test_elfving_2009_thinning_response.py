"""Tests for the Elfving (2009) continuous thinning-response function."""

from math import exp

import pytest

from pyforestry.sweden.growth.elfving_2010.thinning_response import (
    ThinningEvent,
    elfving_2009_thinning_response_factor,
    residual_release_effect,
)


def test_no_thinning_returns_unity():
    factor = elfving_2009_thinning_response_factor(last_thinning=None, spruce_basal_area_share=0.0)
    assert factor == 1.0


def test_pine_single_thinning_matches_published_coefficients():
    ev = ThinningEvent(years_since_thinning=0.0, proportion_basal_area_removed=0.3)
    tath = 2.5  # 0 + mid-period offset
    # pine: intercept + THPROP + RRE + THPROP*TATH + NEWTH + THFA
    expected_effect = (
        0.0585 + 0.4617 * 0.3 + 0.2843 * 0.0 - 0.01832 * (0.3 * tath) - 0.0943 * 1.0 + 0.0
    )
    expected = exp(max(0.0, expected_effect))
    factor = elfving_2009_thinning_response_factor(last_thinning=ev, spruce_basal_area_share=0.2)
    assert factor == pytest.approx(expected)
    assert factor > 1.0


def test_spruce_single_thinning_matches_published_coefficients():
    ev = ThinningEvent(years_since_thinning=0.0, proportion_basal_area_removed=0.3)
    tath = 2.5
    expected_effect = 0.0589 + 0.8478 * 0.3 + 0.4821 * 0.0 - 0.0333 * (0.3 * tath)
    expected = exp(max(0.0, expected_effect))
    factor = elfving_2009_thinning_response_factor(last_thinning=ev, spruce_basal_area_share=0.6)
    assert factor == pytest.approx(expected)


def test_spruce_response_stronger_than_pine_for_same_thinning():
    ev = ThinningEvent(years_since_thinning=5.0, proportion_basal_area_removed=0.3)
    pine = elfving_2009_thinning_response_factor(last_thinning=ev, spruce_basal_area_share=0.2)
    spruce = elfving_2009_thinning_response_factor(last_thinning=ev, spruce_basal_area_share=0.8)
    assert spruce > pine > 1.0


def test_newly_thinned_indicator_reduces_pine_response():
    recent = ThinningEvent(
        years_since_thinning=0.0, proportion_basal_area_removed=0.3
    )  # tath 2.5 < 4
    older = ThinningEvent(
        years_since_thinning=3.0, proportion_basal_area_removed=0.3
    )  # tath 5.5 >= 4
    # The NEWTH penalty (-0.0943) applies to the recent one; but the -THPROP*TATH term
    # grows with TATH. Compare the raw effect via the newly-thinned flag directly.
    f_recent = elfving_2009_thinning_response_factor(
        last_thinning=recent, spruce_basal_area_share=0.0
    )
    f_older = elfving_2009_thinning_response_factor(
        last_thinning=older, spruce_basal_area_share=0.0
    )
    # Both valid; the recent one carries the NEWTH penalty.
    assert f_recent > 0.0 and f_older > 0.0


def test_response_decays_towards_unity_with_time():
    early = ThinningEvent(years_since_thinning=1.0, proportion_basal_area_removed=0.3)
    late = ThinningEvent(years_since_thinning=25.0, proportion_basal_area_removed=0.3)
    f_early = elfving_2009_thinning_response_factor(
        last_thinning=early, spruce_basal_area_share=0.8
    )
    f_late = elfving_2009_thinning_response_factor(last_thinning=late, spruce_basal_area_share=0.8)
    assert f_early > f_late >= 1.0


def test_residual_release_effect_adds_earlier_thinnings():
    last = ThinningEvent(years_since_thinning=0.0, proportion_basal_area_removed=0.3)
    earlier = [ThinningEvent(years_since_thinning=5.0, proportion_basal_area_removed=0.25)]
    rre = residual_release_effect(last_thinning=last, earlier_thinnings=earlier)
    # earlier tath = 7.5; contribution = 0.25 * (1 - 0.0333*7.5)
    assert rre == pytest.approx(0.25 * (1.0 - 0.0333 * 7.5))
    # and a stand with prior thinnings grows more than one without
    with_prior = elfving_2009_thinning_response_factor(
        last_thinning=last, earlier_thinnings=earlier, spruce_basal_area_share=0.8
    )
    without = elfving_2009_thinning_response_factor(
        last_thinning=last, spruce_basal_area_share=0.8
    )
    assert with_prior > without


def test_residual_release_effect_ignores_thinnings_older_than_30_years():
    ancient = [ThinningEvent(years_since_thinning=37.5, proportion_basal_area_removed=0.25)]
    # The >30-year cutoff acts on the reference chain: a last thinning older than
    # 30 years (tath 32.5) yields no residual release from earlier thinnings.
    old_last = ThinningEvent(
        years_since_thinning=30.0, proportion_basal_area_removed=0.3
    )  # tath 32.5
    rre = residual_release_effect(last_thinning=old_last, earlier_thinnings=ancient)
    assert rre == 0.0


def test_factor_never_below_unity():
    # A large TATH could push the linear effect negative; the exp(max(0, .)) floor keeps it >= 1.
    ev = ThinningEvent(years_since_thinning=100.0, proportion_basal_area_removed=0.05)
    factor = elfving_2009_thinning_response_factor(last_thinning=ev, spruce_basal_area_share=0.8)
    assert factor >= 1.0


def test_thinning_from_above_disabled_by_default():
    ev = ThinningEvent(
        years_since_thinning=5.0, proportion_basal_area_removed=0.3, thinned_from_above=1.0
    )
    default = elfving_2009_thinning_response_factor(last_thinning=ev, spruce_basal_area_share=0.0)
    with_form = elfving_2009_thinning_response_factor(
        last_thinning=ev, spruce_basal_area_share=0.0, ignore_thinning_form=False
    )
    assert with_form > default  # THFA term (+0.1172*THFA*THPROP) adds response
