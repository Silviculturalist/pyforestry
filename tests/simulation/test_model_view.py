"""Tests for the simulation-facing model view abstractions."""

import math

import pytest

from pyforestry.base.helpers import CircularPlot, Stand, Tree
from pyforestry.base.helpers.primitives import Position
from pyforestry.base.helpers.tree_species import parse_tree_species
from pyforestry.simulation import InventoryView, SpatialTreeView, StandMetricView


@pytest.fixture
def demo_stand():
    """Provide a stand with two plots and mixed-species trees for testing."""

    sp_picea = parse_tree_species("picea abies")
    sp_pinus = parse_tree_species("pinus sylvestris")

    plot_one = CircularPlot(
        id=1,
        radius_m=5.0,
        trees=[
            Tree(position=Position(10, 10), species=sp_picea, diameter_cm=25, weight_n=2),
            Tree(position=Position(11, 10), species=sp_pinus, diameter_cm=30, weight_n=1),
        ],
    )
    plot_two = CircularPlot(
        id=2,
        radius_m=5.0,
        trees=[
            Tree(position=Position(20, 20), species=sp_picea, diameter_cm=20, weight_n=1),
            Tree(position=Position(21, 20), species=sp_pinus, diameter_cm=35, weight_n=2),
        ],
    )
    return Stand(plots=[plot_one, plot_two])


def test_stand_metric_view_delegates_accessors(demo_stand):
    """StandMetricView should mirror Stand metric accessors and totals."""

    view = StandMetricView(demo_stand)

    assert view.requires_stand_metrics is True
    assert view.requires_plots is True
    assert view.requires_trees is True
    assert "BasalArea" in view.supported_metrics

    ba_accessor = view.metric("BasalArea")
    assert math.isclose(float(ba_accessor), float(demo_stand.BasalArea))

    stems_species = view.by_species("Stems", "picea abies")
    assert math.isclose(stems_species.value, demo_stand.Stems("picea abies").value)

    with pytest.raises(KeyError):
        view.metric("NotAMetric")


def test_stand_metric_view_rejects_empty_stand():
    """A stand without plots cannot be adapted to StandMetricView."""

    with pytest.raises(ValueError):
        StandMetricView(Stand(plots=[]))


def test_inventory_view_iteration(demo_stand):
    """InventoryView should iterate plots and trees in declaration order."""

    view = InventoryView(demo_stand)

    assert view.requires_stand_metrics is False
    assert view.requires_plots is True
    assert view.requires_trees is True
    assert view.plot_count == len(demo_stand.plots)

    assert list(view.iter_plots()) == demo_stand.plots

    expected_trees = [tree for plot in demo_stand.plots for tree in plot.trees]
    assert list(view.iter_trees()) == expected_trees


def test_inventory_view_requires_plots():
    """InventoryView should reject stands without circular plots."""

    with pytest.raises(ValueError):
        InventoryView(Stand(plots=[]))


def test_spatial_tree_view_coordinates():
    """SpatialTreeView should expose position, species and weight metadata."""

    tree = Tree(position=Position(100.0, 200.0, 10.0), species="picea abies", weight_n=3)
    view = SpatialTreeView(tree)

    assert view.requires_stand_metrics is False
    assert view.requires_plots is False
    assert view.requires_trees is True
    assert view.requires_spatial_coordinates is True

    assert view.coordinates == (100.0, 200.0, 10.0)
    assert view.species.full_name == "picea abies"
    assert math.isclose(view.weight, 3.0)


def test_spatial_tree_view_requires_position():
    """Trees without spatial positions should be rejected by the view."""

    tree = Tree(species="picea abies", weight_n=1.0)
    with pytest.raises(ValueError):
        SpatialTreeView(tree)
