"""Plots the top-height estimators cannot answer for, and how they say so.

Every estimator here returns ``None`` for a plot it cannot describe rather than a
number it cannot defend -- no area, no measured height, an order statistic that
falls outside the sample, fewer than two diameters to take a standard deviation
of. ``compute_top_height`` then averages over the plots that *did* answer, so a
``None`` is a plot dropping out of the mean, not a stand-wide failure. None of
those exits had a test.
"""

from __future__ import annotations

from math import pi

import pytest

from pyforestry.base.helpers import CircularPlot, Tree
from pyforestry.base.helpers.top_height import _effective_area_ha, compute_top_height
from pyforestry.base.helpers.tree_species import parse_tree_species

PINE = parse_tree_species("pinus sylvestris")

REFERENCES = ("mean_of_largest", "garcia_u", "garcia_pp")


def _radius_for(area_m2: float) -> float:
    return (area_m2 / pi) ** 0.5


def _plot(area_m2: float, dh_pairs, **kwargs) -> CircularPlot:
    trees = [Tree(species=PINE, diameter_cm=d, height_m=h) for d, h in dh_pairs]
    return CircularPlot(id=1, radius_m=_radius_for(area_m2), trees=trees, **kwargs)


#: Enough trees on 500 m2 for every estimator to resolve the top of the
#: distribution. Four is not: Garcia's order statistic then falls outside the
#: sample, which is one of the exits under test.
_TWELVE_TREES = [(18.0 + i, 16.0 + 0.5 * i) for i in range(12)]


def _ordinary_plot(plot_id: int = 1) -> CircularPlot:
    plot = _plot(500.0, _TWELVE_TREES)
    plot.id = plot_id
    return plot


class TestPlotsThatCannotAnswer:
    @pytest.mark.parametrize("reference", REFERENCES)
    def test_a_plot_with_no_tree_carrying_a_height(self, reference: str) -> None:
        plot = CircularPlot(
            id=1,
            radius_m=_radius_for(500.0),
            trees=[Tree(species=PINE, diameter_cm=20.0)],
        )
        with pytest.warns(UserWarning, match="No plot could supply"):
            assert compute_top_height([plot], reference=reference) is None

    @pytest.mark.parametrize("reference", REFERENCES)
    def test_a_plot_with_no_trees_at_all(self, reference: str) -> None:
        plot = CircularPlot(id=1, radius_m=_radius_for(500.0), trees=[])
        with pytest.warns(UserWarning, match="No plot could supply"):
            assert compute_top_height([plot], reference=reference) is None

    def test_a_plot_whose_trees_carry_no_diameter_cannot_rank_by_diameter(self) -> None:
        """``mean_of_largest`` by diameter needs one to sort on."""
        plot = CircularPlot(
            id=1,
            radius_m=_radius_for(500.0),
            trees=[Tree(species=PINE, height_m=18.0), Tree(species=PINE, height_m=20.0)],
        )
        with pytest.warns(UserWarning, match="No plot could supply"):
            assert compute_top_height([plot], reference="mean_of_largest", by="diameter") is None
        # By height it can: the heights are their own sort key.
        by_height = compute_top_height([plot], reference="mean_of_largest", by="height", n=1)
        assert by_height is not None
        assert float(by_height) == pytest.approx(20.0)


class TestOcclusion:
    def test_a_partly_occluded_plot_is_measured_over_the_area_that_was_seen(self) -> None:
        """A boundary plot's density must not be diluted by area nobody looked at."""
        whole = compute_top_height([_plot(500.0, _TWELVE_TREES)], reference="garcia_u")
        occluded = compute_top_height(
            [_plot(500.0, _TWELVE_TREES, occlusion=0.5)], reference="garcia_u"
        )

        assert whole is not None and occluded is not None
        assert _effective_area_ha(_plot(500.0, _TWELVE_TREES, occlusion=0.5)) == pytest.approx(
            0.025
        )
        # The same trees on half the area is twice the density, so the reference
        # cell holds more of them and the estimate climbs.
        assert float(occluded) > float(whole)

    def test_a_plot_that_saw_nothing_falls_back_to_its_nominal_area(self) -> None:
        """A share of nought scales nothing up, so the plot's own area stands.

        ``CircularPlot`` refuses ``occlusion=1.0`` outright, so this exit is only
        reachable for a caller supplying its own plot-like object -- which the
        estimator accepts, being duck-typed on ``area_ha``/``occlusion``.
        """

        class _Blind:
            area_ha = 0.05
            occlusion = 1.0

        assert _effective_area_ha(_Blind()) == pytest.approx(0.05)

    def test_a_plot_with_no_area_cannot_be_measured_at_all(self) -> None:
        class _Arealess:
            area_ha = 0.0
            occlusion = 0.0

        assert _effective_area_ha(_Arealess()) is None


class TestDiameterReferences:
    def test_the_percentile_reference_reads_a_curve_at_one_diameter(self) -> None:
        """With one tree the percentile is that tree, whatever ``p`` asks for."""
        plot = _plot(500.0, [(20.0, 18.0)])
        estimate = compute_top_height(
            [plot], reference="percentile", height_source=lambda d: 0.9 * d, percentile=90.0
        )
        assert estimate is not None
        assert float(estimate) == pytest.approx(18.0)

    def test_mean_plus_k_sigma_needs_two_diameters_to_have_a_sigma(self) -> None:
        one_tree = _plot(500.0, [(20.0, 18.0)])
        with pytest.warns(UserWarning, match="No plot could supply"):
            assert (
                compute_top_height(
                    [one_tree], reference="mean_plus_k_sigma", height_source=lambda d: 0.9 * d
                )
                is None
            )

        two_trees = _plot(500.0, [(20.0, 18.0), (30.0, 24.0)])
        estimate = compute_top_height(
            [two_trees], reference="mean_plus_k_sigma", height_source=lambda d: 0.9 * d, k=1.0
        )
        assert estimate is not None


class TestAveragingOverPlots:
    def test_a_plot_that_cannot_answer_drops_out_of_the_mean(self) -> None:
        """Not a stand-wide ``None``: the plots that answered still describe it."""
        answering = _ordinary_plot()
        silent = CircularPlot(id=2, radius_m=_radius_for(500.0), trees=[])

        alone = compute_top_height([answering], reference="garcia_u")
        with pytest.warns(UserWarning, match="excluded from the stand mean"):
            both = compute_top_height([answering, silent], reference="garcia_u")

        assert both is not None
        assert float(both) == pytest.approx(float(alone))

    def test_when_no_plot_can_answer_the_stand_gets_none_and_a_reason(self) -> None:
        silent = CircularPlot(id=1, radius_m=_radius_for(500.0), trees=[])

        with pytest.warns(UserWarning, match="No plot could supply"):
            assert compute_top_height([silent], reference="garcia_u") is None

    def test_an_unknown_reference_is_refused_by_name(self) -> None:
        with pytest.raises(ValueError, match="reference"):
            compute_top_height([_ordinary_plot()], reference="dominant_height")
