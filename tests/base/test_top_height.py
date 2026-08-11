"""Tests for the configurable top-height + height-imputation subsystem."""

import math
from math import comb, pi

import pytest

from pyforestry.base.helpers import CircularPlot, NaslundHeightCurve, Stand, Tree
from pyforestry.base.helpers.height_models import (
    CurveHeightSource,
    MeasuredHeightSource,
    resolve_height_source,
)
from pyforestry.base.helpers.top_height import _garcia_theta_integer, compute_top_height
from pyforestry.base.helpers.tree_species import parse_tree_species

PINE = parse_tree_species("pinus sylvestris")


def _radius_for(area_m2: float) -> float:
    return (area_m2 / pi) ** 0.5


def _plot(area_m2, dh_pairs):
    trees = [Tree(species=PINE, diameter_cm=d, height_m=h) for d, h in dh_pairs]
    return CircularPlot(id=1, radius_m=_radius_for(area_m2), trees=trees)


# --------------------------------------------------------------------------- #
# Näslund curve
# --------------------------------------------------------------------------- #
def test_naslund_fit_recovers_coefficients():
    true = NaslundHeightCurve(a=2.0, b=0.35, exponent=2)
    diameters = [8, 12, 16, 20, 26, 32, 40]
    heights = [true.predict(d) for d in diameters]
    fit = NaslundHeightCurve.fit(diameters, heights)
    assert fit is not None
    assert math.isclose(fit.a, 2.0, rel_tol=1e-6)
    assert math.isclose(fit.b, 0.35, rel_tol=1e-6)
    assert math.isclose(fit.predict(24), true.predict(24), rel_tol=1e-9)


def test_naslund_fit_degenerate_cases_return_none():
    assert NaslundHeightCurve.fit([10], [15]) is None  # too few
    assert NaslundHeightCurve.fit([10, 20], [1.0, 1.2]) is None  # all h <= 1.3
    assert NaslundHeightCurve.fit([10, 10, 10], [12, 14, 16]) is None  # no diameter spread


def test_naslund_predict_out_of_range_returns_none():
    curve = NaslundHeightCurve(a=2.0, b=0.35)
    assert curve.predict(0) is None
    assert curve.predict(-5) is None


def test_naslund_fit_exponent_recovers_nondefault_exponent():
    true = NaslundHeightCurve(a=3.0, b=0.25, exponent=3)
    diameters = [6, 10, 14, 18, 24, 30, 36, 42]
    heights = [true.predict(d) for d in diameters]
    auto = NaslundHeightCurve.fit(diameters, heights, fit_exponent=True)
    assert auto is not None
    assert math.isclose(auto.exponent, 3.0, abs_tol=0.05)
    # Fitting the exponent fits at least as well as the fixed default.
    fixed = NaslundHeightCurve.fit(diameters, heights, exponent=2)
    pairs = list(zip(diameters, heights, strict=True))
    assert NaslundHeightCurve._height_sse(auto, pairs) <= NaslundHeightCurve._height_sse(
        fixed, pairs
    )


def test_naslund_fit_exponent_falls_back_with_too_few_points():
    # Two pairs cannot identify the exponent, so the fixed one is kept.
    curve = NaslundHeightCurve.fit([10, 30], [12, 20], exponent=2, fit_exponent=True)
    assert curve is not None
    assert curve.exponent == 2


def test_naslund_auto_exponent_via_resolver():
    true = NaslundHeightCurve(a=3.0, b=0.25, exponent=3)
    diameters = [6, 10, 14, 18, 24, 30, 36]
    trees = [Tree(species=PINE, diameter_cm=d, height_m=true.predict(d)) for d in diameters]
    src = resolve_height_source("naslund", trees, naslund_exponent="auto")
    assert src is not None and src.is_curve
    assert math.isclose(src.height_at_diameter(27), true.predict(27), rel_tol=1e-3)


# --------------------------------------------------------------------------- #
# Height sources
# --------------------------------------------------------------------------- #
def test_measured_source_cannot_evaluate_at_diameter():
    src = resolve_height_source("measured")
    assert isinstance(src, MeasuredHeightSource)
    assert src.is_curve is False
    with pytest.raises(TypeError):
        src.height_at_diameter(20.0)


def test_callable_source_is_curve():
    src = resolve_height_source(lambda d: 1.3 + d)
    assert isinstance(src, CurveHeightSource)
    assert src.is_curve is True
    assert src.height_at_diameter(10) == 11.3


def test_measured_source_imputed_fallback():
    tree = Tree(species=PINE, diameter_cm=20.0)
    tree.set_imputed("height_m", 15.0, _fake_imputer())
    assert resolve_height_source("measured").height_for(tree) is None
    assert resolve_height_source("measured+imputed").height_for(tree) == 15.0
    # The old spelling went out with Tree.predicted_height_m; no alias.
    with pytest.raises(ValueError, match="Unknown height source"):
        resolve_height_source("measured+predicted")


def _fake_imputer():
    """Minimal stand-in for an Imputer, for tests that only need a stored value."""
    from pyforestry.base.imputation import NaslundHeightImputer

    return NaslundHeightImputer()


# --------------------------------------------------------------------------- #
# Tree provenance
# --------------------------------------------------------------------------- #
def test_tree_height_provenance_and_effective_height():
    measured = Tree(species=PINE, diameter_cm=20.0, height_m=15.0)
    imputed = Tree(species=PINE, diameter_cm=20.0)
    imputed.set_imputed("height_m", 14.0, _fake_imputer())
    neither = Tree(species=PINE, diameter_cm=20.0)
    assert measured.provenance("height_m") == "measured"
    assert imputed.provenance("height_m") == "imputed"
    assert neither.provenance("height_m") is None
    # measured wins by default; imputed-preference can override
    both = Tree(species=PINE, diameter_cm=20.0, height_m=15.0)
    both.set_imputed("height_m", 14.0, _fake_imputer())
    assert both.value_of("height_m") == 15.0
    assert both.value_of("height_m", prefer="imputed") == 14.0
    assert both.value_of("height_m", prefer="imputed_only") == 14.0
    assert both.value_of("height_m", prefer="measured_only") == 15.0


# --------------------------------------------------------------------------- #
# Height imputation
# --------------------------------------------------------------------------- #
def test_impute_heights_fills_missing_without_touching_measured():
    trees = [
        Tree(species=PINE, diameter_cm=d, height_m=h) for d, h in [(10, 8), (20, 15), (30, 20)]
    ]
    trees.append(Tree(species=PINE, diameter_cm=25))  # missing height
    stand = Stand(plots=[CircularPlot(id=1, radius_m=_radius_for(500.0), trees=trees)])

    assigned = stand.impute("height_m", "naslund", which="missing")
    assert assigned == 1
    # measured untouched
    assert trees[0].height_m == 8 and "height_m" not in trees[0].imputed
    assert trees[3].value_of("height_m") is not None
    assert trees[3].provenance("height_m") == "imputed"
    # the modelled value records which curve produced it
    assert trees[3].imputed_source("height_m").year == 1936


def test_impute_heights_rejects_measured_source():
    stand = Stand(plots=[_plot(500.0, [(20, 15), (30, 20)])])
    with pytest.raises(ValueError):
        stand.impute("height_m", "measured")


# --------------------------------------------------------------------------- #
# García estimators
# --------------------------------------------------------------------------- #
def test_garcia_u_recursion_matches_binomial_weights():
    xs = [10.0, 14.0, 17.0, 22.0]  # ascending, n = 4
    n = 4
    for m in range(1, n + 1):
        explicit = sum(comb(i - 1, m - 1) / comb(n, m) * xs[i - 1] for i in range(m, n + 1))
        assert math.isclose(_garcia_theta_integer(xs, m, n), explicit, rel_tol=1e-12)


def test_garcia_reduces_to_single_largest_when_plot_equals_reference_cell():
    # 100 m2 plot, definition 100/ha -> reference cell 0.01 ha -> single largest.
    stand = Stand(plots=[_plot(100.0, [(15, 12), (30, 21), (22, 17), (26, 19)])])
    assert math.isclose(float(stand.estimate_top_height("garcia_u")), 21.0, rel_tol=1e-9)
    assert math.isclose(float(stand.estimate_top_height("garcia_pp")), 21.0, rel_tol=1e-9)


def test_garcia_u_larger_plot_uses_lower_order_statistic():
    # 400 m2 plot, 4 trees -> m = 4 * 0.01 / 0.04 = 1 -> mean of all heights.
    stand = Stand(plots=[_plot(400.0, [(15, 12), (30, 21), (22, 17), (26, 19)])])
    assert math.isclose(
        float(stand.estimate_top_height("garcia_u")), (12 + 21 + 17 + 19) / 4, rel_tol=1e-9
    )


# --------------------------------------------------------------------------- #
# mean_of_largest and diameter references
# --------------------------------------------------------------------------- #
def test_mean_of_largest_by_diameter_and_height():
    stand = Stand(plots=[_plot(500.0, [(15, 12), (30, 21), (22, 17), (26, 19)])])
    # widest two: d30(h21), d26(h19) -> 20; tallest two: 21, 19 -> 20
    assert math.isclose(
        float(stand.estimate_top_height("mean_of_largest", n=2, by="diameter")), 20.0
    )
    assert math.isclose(
        float(stand.estimate_top_height("mean_of_largest", n=2, by="height")), 20.0
    )


def test_percentile_reference_reads_curve_at_diameter_percentile():
    stand = Stand(plots=[_plot(500.0, [(15, 12), (30, 21), (22, 17), (26, 19)])])
    curve = NaslundHeightCurve.fit([15, 22, 26, 30], [12, 17, 19, 21])
    # D90 of [15,22,26,30] by linear interpolation: rank 2.7 -> 26*0.3 + 30*0.7 = 28.8
    result = float(stand.estimate_top_height("percentile", height_source=curve, percentile=90))
    assert math.isclose(result, curve.predict(28.8), rel_tol=1e-9)


def test_mean_plus_k_sigma_requires_curve_source():
    stand = Stand(plots=[_plot(500.0, [(15, 12), (30, 21), (22, 17), (26, 19)])])
    with pytest.raises(ValueError):
        stand.estimate_top_height("mean_plus_k_sigma", height_source="measured", k=3.0)
    # With a curve it produces a positive height.
    assert (
        float(stand.estimate_top_height("mean_plus_k_sigma", height_source="naslund", k=3.0)) > 0
    )


# --------------------------------------------------------------------------- #
# Aggregation over all plots
# --------------------------------------------------------------------------- #
def test_estimate_top_height_averages_over_all_plots_with_se():
    # Two 100 m2 plots -> single largest per plot -> [20, 22] -> mean 21, SE = 1.
    p1 = _plot(100.0, [(20, 16), (30, 20)])
    p2 = _plot(100.0, [(22, 18), (28, 22)])
    stand = Stand(plots=[p1, p2])
    result = stand.estimate_top_height("garcia_u")
    assert math.isclose(float(result), 21.0, rel_tol=1e-9)
    assert math.isclose(result.precision, 1.0, rel_tol=1e-9)


def test_estimate_top_height_none_when_no_plots_or_no_heights():
    assert Stand(plots=[]).estimate_top_height() is None
    no_heights = Stand(
        plots=[
            CircularPlot(
                id=1, radius_m=_radius_for(100.0), trees=[Tree(species=PINE, diameter_cm=20.0)]
            )
        ]
    )
    assert no_heights.estimate_top_height("garcia_u") is None


def test_compute_top_height_unknown_reference_raises():
    with pytest.raises(ValueError):
        compute_top_height([_plot(100.0, [(20, 16)])], reference="nonsense")
