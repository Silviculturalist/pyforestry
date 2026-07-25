"""Regression guards for the plot-aggregation and top-height estimator fixes.

Each test below pins a property that a specific defect violated. They are written
as properties (an invariance, or an exactly-known answer) rather than as pinned
numbers, so they keep their meaning if the surrounding code is refactored.
"""

import math
import warnings

import pytest

from pyforestry.base.helpers import (
    AngleCount,
    AngleCountAggregator,
    CircularPlot,
    Stand,
    Tree,
    parse_tree_species,
)
from pyforestry.base.helpers.height_models import NaslundHeightCurve
from pyforestry.base.helpers.top_height import compute_top_height

PINE = parse_tree_species("pinus sylvestris")


def naslund_height(diameter_cm: float, a: float = 3.0, b: float = 0.35) -> float:
    """A true Näslund curve used to generate consistent synthetic heights."""
    return 1.3 + diameter_cm**2 / (a + b * diameter_cm) ** 2


# ---------------------------------------------------------------------------
# Ratio metrics must carry the numerator/denominator covariance
# ---------------------------------------------------------------------------


def _plots_with_identical_diameter_mix():
    """Three plots with the same diameter mix at 1x, 2x and 4x density."""
    plots = []
    for index, multiplier in enumerate((1, 2, 4)):
        trees = [
            Tree(species=PINE, diameter_cm=d, height_m=naslund_height(d))
            for d in (20.0, 30.0, 40.0)
            for _ in range(multiplier)
        ]
        plots.append(CircularPlot(id=index, area_m2=500.0, trees=trees))
    return plots


def test_ratio_metrics_report_zero_error_when_every_plot_shares_the_ratio():
    """BAWAD/HL/QMD vary only with the diameter mix, which is identical here.

    Density differs 4-fold between plots, so basal area, stem count and the sum
    of cubed diameters all vary a lot -- but their *ratios* do not. Propagating
    the ratio as if numerator and denominator were independent invented a
    standard error of about half the estimate; the covariance-aware form gives
    the correct zero.
    """
    stand = Stand(plots=_plots_with_identical_diameter_mix())

    expected_bawad = sum(d**3 for d in (20, 30, 40)) / sum(d**2 for d in (20, 30, 40))
    assert float(stand.BAWAD.TOTAL) == pytest.approx(expected_bawad)
    assert stand.BAWAD.TOTAL.precision == pytest.approx(0.0, abs=1e-9)
    assert stand.HL.TOTAL.precision == pytest.approx(0.0, abs=1e-9)
    assert stand.QMD.TOTAL.precision == pytest.approx(0.0, abs=1e-9)

    # The additive metrics genuinely do vary between these plots.
    assert stand.BasalArea.TOTAL.precision > 0
    assert stand.Stems.TOTAL.precision > 0


def test_species_group_ratio_is_covariance_aware_like_the_total():
    """A one-species group must agree with the stand total, error included.

    Groups used to sum per-species standard errors in quadrature while the total
    was reduced from the per-plot series, so the two disagreed.
    """
    stand = Stand(plots=_plots_with_identical_diameter_mix())
    group = stand.BAWAD.group([PINE])
    assert float(group) == pytest.approx(float(stand.BAWAD.TOTAL))
    assert group.precision == pytest.approx(stand.BAWAD.TOTAL.precision, abs=1e-12)


def test_trees_without_a_diameter_do_not_drag_qmd_down():
    """A record with no diameter is a stem but contributes no basal area.

    Counting it in the QMD denominator as though it were a zero-diameter tree
    pulled QMD below every tree actually measured.
    """
    trees = [Tree(species=PINE, diameter_cm=30.0) for _ in range(4)]
    trees.append(Tree(species=PINE, diameter_cm=None))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        stand = Stand(plots=[CircularPlot(id=1, area_m2=500.0, trees=trees)])
        qmd = float(stand.QMD.TOTAL)
        stems = float(stand.Stems.TOTAL)
    assert qmd == pytest.approx(30.0)
    assert stems == pytest.approx(100.0)  # the diameterless record is still a stem


def test_missing_diameter_is_reported():
    """The user has to learn that a record was unusable for diameter metrics."""
    trees = [
        Tree(species=PINE, diameter_cm=30.0),
        Tree(species=PINE, diameter_cm=None),
    ]
    with pytest.warns(UserWarning, match="no diameter_cm"):
        stems = Stand(plots=[CircularPlot(id=1, area_m2=500.0, trees=trees)]).Stems.TOTAL
    assert float(stems) > 0


# ---------------------------------------------------------------------------
# Top height: reference-cell occupancy and occlusion
# ---------------------------------------------------------------------------


def _stand_trees(diameters, measured_every=1):
    """Trees whose heights are measured on every ``measured_every``-th record."""
    return [
        Tree(
            species=PINE,
            diameter_cm=d,
            height_m=naslund_height(d) if index % measured_every == 0 else None,
        )
        for index, d in enumerate(diameters)
    ]


@pytest.mark.parametrize("reference", ["garcia_u", "garcia_pp"])
def test_garcia_is_stable_under_height_subsampling(reference):
    """Measuring heights on a subsample must not move the estimate much.

    The reference cell's occupancy is a property of stand density. Deriving it
    from the count of *height-carrying* trees shrank it in proportion to the
    sampling intensity and biased the estimate down by nearly half a metre on
    this stand; taking it from the plot's tree list removes that.
    """
    diameters = [10.0 + i for i in range(50)]
    full = CircularPlot(id=1, area_m2=500.0, trees=_stand_trees(diameters))
    half = CircularPlot(id=2, area_m2=500.0, trees=_stand_trees(diameters, measured_every=2))

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        full_estimate = compute_top_height([full], reference=reference)
        half_estimate = compute_top_height([half], reference=reference)

    assert full_estimate is not None and half_estimate is not None
    # What remains is ordinary sampling noise, not a systematic shrinkage.
    assert abs(float(half_estimate) - float(full_estimate)) < 0.15


@pytest.mark.parametrize("reference", ["garcia_u", "garcia_pp", "mean_of_largest"])
def test_top_height_honours_occlusion(reference):
    """A half-occluded plot and the equivalent smaller plot must agree.

    Both describe the same observed area holding the same trees. Reading the
    nominal area while the trees only cover the visible part made the stand look
    half as dense and biased the top height.
    """
    diameters = [10.0 + 2 * i for i in range(25)]
    trees = _stand_trees(diameters)
    occluded = CircularPlot(id=1, area_m2=500.0, occlusion=0.5, trees=trees)
    equivalent = CircularPlot(id=2, area_m2=250.0, trees=list(trees))

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        occluded_estimate = compute_top_height([occluded], reference=reference)
        equivalent_estimate = compute_top_height([equivalent], reference=reference)

    assert occluded_estimate is not None and equivalent_estimate is not None
    assert float(occluded_estimate) == pytest.approx(float(equivalent_estimate))


def test_unresolvable_top_height_is_announced_not_silent():
    """Returning None because no plot resolved must not be silent."""
    plot = CircularPlot(id=1, area_m2=500.0, trees=_stand_trees([10.0, 12.0], measured_every=99))
    with pytest.warns(UserWarning, match="No plot could supply"):
        assert compute_top_height([plot], reference="garcia_u") is None


# ---------------------------------------------------------------------------
# Näslund height curve
# ---------------------------------------------------------------------------


def test_naslund_recovers_the_generating_curve():
    """A clean fit must return the coefficients the data were built from."""
    diameters = [10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0]
    curve = NaslundHeightCurve.fit(diameters, [naslund_height(d) for d in diameters])
    assert curve is not None
    assert curve.a == pytest.approx(3.0)
    assert curve.b == pytest.approx(0.35)


def test_naslund_excludes_trees_at_breast_height():
    """A record just above 1.3 m must not be able to destroy the fit.

    The linearising transform divides by ``(h - 1.3) ** (1/p)``, so such a record
    dominates the regression; one 1.31 m sapling used to make the fit fail
    outright even with eight good pairs beside it.
    """
    diameters = [10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0]
    heights = [naslund_height(d) for d in diameters]

    with pytest.warns(UserWarning, match="breast height"):
        curve = NaslundHeightCurve.fit(diameters + [5.0], heights + [1.31])

    assert curve is not None
    assert curve.predict(30.0) == pytest.approx(naslund_height(30.0))


def test_naslund_fit_failure_message_is_accurate():
    """The failure must describe the real cause, not guess at 'too few pairs'."""
    sp_trees = [Tree(species=PINE, diameter_cm=20.0, height_m=15.0) for _ in range(5)]
    stand = Stand(plots=[CircularPlot(id=1, area_m2=500.0, trees=sp_trees)])
    with pytest.raises(ValueError, match="span a range of diameters"):
        stand.impute_heights("naslund")


def test_naslund_exponent_fit_recovers_a_known_exponent():
    """Fitting the exponent must recover a curve built with p = 3."""

    def cubic(d):
        """Näslund curve with exponent 3."""
        return 1.3 + d**3 / (4.0 + 0.4 * d) ** 3

    diameters = [8.0, 12.0, 16.0, 20.0, 26.0, 32.0, 40.0]
    curve = NaslundHeightCurve.fit(diameters, [cubic(d) for d in diameters], fit_exponent=True)
    assert curve is not None
    assert curve.exponent == pytest.approx(3.0, abs=1e-3)
    assert curve.predict(30.0) == pytest.approx(cubic(30.0), rel=1e-6)


# ---------------------------------------------------------------------------
# Angle-count tallies
# ---------------------------------------------------------------------------


def test_angle_count_rejects_tally_and_diameters_that_disagree():
    """Basal area comes from the count and stems from the diameters.

    If they describe different sets of trees the two are mutually inconsistent:
    a five-tree tally with three diameters produced a QMD of 32 cm for a stand
    where every tallied tree measured 25 cm.
    """
    with pytest.raises(ValueError, match="tallied 5.0 time"):
        AngleCount(
            ba_factor=2.0,
            species=[PINE],
            value=[5.0],
            diameters_cm=[[25.0, 25.0, 25.0]],
        )


def test_angle_count_consistent_tally_gives_the_measured_qmd():
    """With one diameter per tallied tree, QMD is the diameter they all share."""
    record = AngleCount(
        ba_factor=2.0,
        species=[PINE],
        value=[3.0],
        diameters_cm=[[25.0, 25.0, 25.0]],
    )
    basal_area, stems = AngleCountAggregator([record]).aggregate_stand_metrics()
    qmd = math.sqrt(40000.0 * float(basal_area[PINE]) / (math.pi * float(stems[PINE])))
    assert qmd == pytest.approx(25.0)


def test_angle_count_merge_rejects_disagreeing_slope_or_occlusion():
    """Both set the point's per-hectare correction, so they cannot be merged away."""
    base = dict(ba_factor=2.0, species=[PINE], value=[3.0], point_id="P1")
    with pytest.raises(ValueError, match="Inconsistent slope"):
        AngleCountAggregator(
            [AngleCount(**base, slope=0.0), AngleCount(**base, slope=0.5)]
        ).merge_by_point_id()
    with pytest.raises(ValueError, match="Inconsistent occlusion"):
        AngleCountAggregator(
            [AngleCount(**base, occlusion=0.0), AngleCount(**base, occlusion=0.5)]
        ).merge_by_point_id()


def test_angle_count_slope_correction_is_the_secant():
    """A 45-degree slope (rise/run = 1) scales the estimate by sqrt(2)."""
    level = AngleCount(ba_factor=2.0, species=[PINE], value=[4.0], point_id="A")
    sloping = AngleCount(ba_factor=2.0, species=[PINE], value=[4.0], point_id="B", slope=1.0)
    level_ba, _ = AngleCountAggregator([level]).aggregate_stand_metrics()
    slope_ba, _ = AngleCountAggregator([sloping]).aggregate_stand_metrics()
    assert float(slope_ba[PINE]) == pytest.approx(float(level_ba[PINE]) * math.sqrt(2.0))
