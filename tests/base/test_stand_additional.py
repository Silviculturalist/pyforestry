import math

from pyforestry.base.helpers import (
    AngleCount,
    CircularPlot,
    RepresentationTree,
    Stand,
    parse_tree_species,
)


def test_repr_methods():
    """Ensure __repr__ methods provide simple strings."""
    plot = CircularPlot(id=1, radius_m=5.0, trees=[RepresentationTree(diameter_cm=25.0)])
    stand = Stand(plots=[plot])

    # Stand.__repr__ should contain area and number of plots
    rep = repr(stand)
    assert "n_plots=1" in rep

    # Accessor repr should mention the metric name
    ba_repr = repr(stand.BasalArea)
    assert "StandMetricAccessor" in ba_repr and "BasalArea" in ba_repr


def test_calculate_top_height_bias():
    """calculate_top_height_bias returns finite results for small simulations."""
    bias, pct = Stand.calculate_top_height_bias(
        r=3.0,
        m=2,
        n_trees=50,
        n_simulations=50,
        nominal_top_n=5,
        nominal_area=1000.0,
        sigma=5.0,
    )
    assert math.isfinite(bias)
    assert math.isfinite(pct)


def test_append_plot_with_angle_count():
    sp = parse_tree_species("picea abies")
    plot1 = CircularPlot(
        id=1,
        radius_m=5.0,
        AngleCount=[AngleCount(ba_factor=2.0, value=[3], species=[sp], point_id="P1")],
    )
    stand = Stand(plots=[plot1])
    # Add another plot with AngleCount data and ensure aggregation uses angle count
    plot2 = CircularPlot(
        id=2,
        radius_m=5.0,
        AngleCount=[AngleCount(ba_factor=2.0, value=[5], species=[sp], point_id="P2")],
    )
    stand.append_plot(plot2)
    assert stand.use_angle_count
    ba_sp = stand.BasalArea(parse_tree_species("picea abies"))
    assert math.isclose(ba_sp.value, 8.0)  # mean of counts * BAF
