import math

import pytest
from pyproj import CRS
from shapely.geometry import Polygon

from pyforestry.base.helpers import (
    AngleCount,
    CircularPlot,
    Stand,
    StandBasalArea,
    Stems,
    Tree,
    parse_tree_species,
)


def test_repr_methods():
    """Ensure __repr__ methods provide simple strings."""
    plot = CircularPlot(id=1, radius_m=5.0, trees=[Tree(diameter_cm=25.0)])
    stand = Stand(plots=[plot])

    # Stand.__repr__ should contain area and number of plots
    rep = repr(stand)
    assert "n_plots=1" in rep

    # Accessor repr should mention the metric name
    ba_repr = repr(stand.BasalArea)
    assert "StandMetricAccessor" in ba_repr and "BasalArea" in ba_repr


def test_get_dominant_height_has_no_bias_correction():
    """The Monte-Carlo 'Matérn' correction was struck: est_bias is always 0."""
    assert not hasattr(Stand, "calculate_top_height_bias")
    sp = parse_tree_species("picea abies")
    plots = [
        CircularPlot(
            id=i,
            radius_m=10.0,
            trees=[
                Tree(species=sp, diameter_cm=30, height_m=20),
                Tree(species=sp, diameter_cm=25, height_m=18),
            ],
        )
        for i in (1, 2)
    ]
    result = Stand(plots=plots).get_dominant_height()
    assert result is not None
    assert result.est_bias == 0.0


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
    assert math.isclose(stand.BasalArea(sp).value, 8.0)


def test_accessor_value_and_precision():
    sp = parse_tree_species("picea abies")
    plot = CircularPlot(id=1, radius_m=5.0, trees=[Tree(species=sp, diameter_cm=25)])
    stand = Stand(plots=[plot])
    assert stand.BasalArea.value > 0
    assert stand.BasalArea.precision >= 0


def test_compute_plot_mean_estimates_parses_string_species():
    class DummyTree:
        def __init__(self, species, diameter_cm, weight_n=1.0):
            self.species = species
            self.diameter_cm = diameter_cm
            self.weight_n = weight_n

    plot = CircularPlot(id=1, radius_m=5.0, trees=[DummyTree("picea abies", 20.0)])
    stand = Stand(plots=[plot])
    stand._compute_plot_mean_estimates()
    sp = parse_tree_species("picea abies")
    assert sp in stand._metric_estimates["Stems"]


def test_geographic_polygon_area():
    poly = Polygon([(0, 0), (0, 0.01), (0.01, 0.01), (0.01, 0)])
    stand = Stand(polygon=poly, crs=CRS("EPSG:4326"))
    assert stand.area_ha and stand.area_ha > 0


def test_invalid_polygon_raises():
    poly = Polygon([(0, 0), (1, 1), (1, 0), (0, 1)])
    with pytest.raises(ValueError, match="Polygon is not valid"):
        Stand(polygon=poly, crs=CRS("EPSG:4326"))


def test_compute_qmd_special_cases():
    stand = Stand()
    sp1 = parse_tree_species("picea abies")
    sp2 = parse_tree_species("pinus sylvestris")
    stand._metric_estimates["BasalArea"] = {
        sp1: StandBasalArea(0.0, precision=0.0),
        sp2: StandBasalArea(0.0, precision=0.0),
        "TOTAL": StandBasalArea(0.0, precision=0.0),
    }
    stand._metric_estimates["Stems"] = {
        sp1: Stems(10.0, precision=1.0),
        sp2: Stems(0.0, precision=0.0),
        "TOTAL": Stems(10.0, precision=1.0),
    }
    stand._compute_qmd_estimates()
    qmd = stand._metric_estimates["QMD"]
    assert qmd[sp1].value == 0.0 and qmd[sp1].precision == 0.0
    assert qmd[sp2].value == 0.0 and qmd[sp2].precision == 0.0


def test_compute_plot_mean_estimates_skip_and_parse():
    plot = CircularPlot(
        id=1,
        radius_m=5.0,
        trees=[Tree(species=None), Tree(species="picea abies", diameter_cm=20)],
    )
    stand = Stand(plots=[plot])
    stand._compute_plot_mean_estimates()
    sp = parse_tree_species("picea abies")
    assert sp in stand._metric_estimates["Stems"]
    assert "TOTAL" in stand._metric_estimates["Stems"]


class EmptyIterable:
    def __iter__(self):
        return iter([])

    def __bool__(self):
        return True


def test_get_dominant_height_no_plots():
    assert Stand().get_dominant_height() is None


def test_get_dominant_height_empty_iter():
    stand = Stand()
    stand.plots = EmptyIterable()
    assert stand.get_dominant_height() is None


class NaNPlot(CircularPlot):
    @property
    def area_ha(self):
        return float("nan")


def test_get_dominant_height_mode_no_subplots():
    p1 = NaNPlot(id=1, radius_m=5.0)
    p2 = CircularPlot(id=2, radius_m=6.0)
    st = Stand(plots=[p1, p2])
    assert st.get_dominant_height() is None


def test_get_dominant_height_no_heights():
    sp = parse_tree_species("picea abies")
    t1 = Tree(species=sp, diameter_cm=30, height_m=None)
    plot = CircularPlot(id=1, radius_m=10, trees=[t1])
    st = Stand(plots=[plot])
    assert st.get_dominant_height() is None


def test_get_dominant_height_mode_tie_uses_first_area():
    sp = parse_tree_species("picea abies")
    p1 = CircularPlot(
        id=1,
        radius_m=5.0,
        trees=[Tree(species=sp, diameter_cm=30, height_m=20)],
    )
    p2 = CircularPlot(
        id=2,
        radius_m=6.0,
        trees=[Tree(species=sp, diameter_cm=25, height_m=18)],
    )
    st = Stand(plots=[p1, p2])
    result = st.get_dominant_height()
    assert result is not None
    assert result.value > 0


def test_get_dominant_height_all_skipped():
    sp = parse_tree_species("picea abies")
    p1 = CircularPlot(
        id=1,
        radius_m=10,
        trees=[
            Tree(species=sp, diameter_cm=30, height_m=None),
            Tree(species=sp, diameter_cm=25, height_m=20),
        ],
    )
    p2 = CircularPlot(
        id=2,
        radius_m=10,
        trees=[
            Tree(species=sp, diameter_cm=30, height_m=None),
            Tree(species=sp, diameter_cm=25, height_m=18),
        ],
    )
    st = Stand(plots=[p1, p2])
    assert st.get_dominant_height() is None


def test_get_dominant_height_precision_zero():
    sp = parse_tree_species("picea abies")
    p = CircularPlot(
        id=1,
        radius_m=10,
        trees=[
            Tree(species=sp, diameter_cm=25, height_m=20),
            Tree(species=sp, diameter_cm=20, height_m=None),
        ],
    )
    st = Stand(plots=[p])
    result = st.get_dominant_height()
    assert result is not None
    assert result.precision == 0.0


def test_thin_trees_polygon_only():
    sp = parse_tree_species("picea abies")
    inside = Tree(species=sp, diameter_cm=20, position=(0, 0), uid="in")
    outside = Tree(species=sp, diameter_cm=20, position=(100, 0), uid="out")
    plot = CircularPlot(id=1, radius_m=10, trees=[inside, outside])
    stand = Stand(plots=[plot])
    _ = stand.QMD.TOTAL
    poly = Polygon([(-5, -5), (5, -5), (5, 5), (-5, 5)])
    stand.thin_trees(polygon=poly)
    uids = [t.uid for t in stand.plots[0].trees]
    assert uids == ["out"]
    assert "QMD" not in stand._metric_estimates


def test_thin_trees_polygon_missing_positions():
    sp = parse_tree_species("picea abies")
    tree = Tree(species=sp, diameter_cm=20, uid="nopos")
    plot = CircularPlot(id=1, radius_m=10, trees=[tree])
    stand = Stand(plots=[plot])
    poly = Polygon([(-5, -5), (5, -5), (5, 5), (-5, 5)])

    stand.thin_trees(polygon=poly)
    assert [t.uid for t in stand.plots[0].trees] == ["nopos"]


def test_estimate_top_height_none_with_too_few_measured_heights():
    """Every plot has too few measured heights for its size, so the result is None."""
    plots = [
        CircularPlot(id=1, radius_m=5.0, trees=[Tree(diameter_cm=10)]),
        CircularPlot(id=2, radius_m=6.0, trees=[Tree(diameter_cm=10, height_m=15)]),
        CircularPlot(id=3, radius_m=7.0, trees=[Tree(diameter_cm=10)]),
    ]
    assert Stand(plots=plots).estimate_top_height("garcia_u") is None


def test_estimate_top_height_measured_vs_curve_when_top_trees_lack_heights():
    """When the thickest trees lack measured heights, the legacy strict estimator
    returns None, while estimate_top_height uses the heights it has (or a curve).

    The plots must be at least as large as the 0.01 ha reference cell for García's
    estimators to be defined at all: the reference-cell occupancy comes from the
    plot's stem count, so a plot smaller than one cell is not identifiable however
    many heights it carries.
    """
    sp = parse_tree_species("picea abies")

    def naslund_height(diameter_cm: float) -> float:
        """A monotone height-diameter curve, so a Näslund fit is well posed."""
        return 1.3 + diameter_cm**2 / (1.0 + 0.22 * diameter_cm) ** 2

    def make_plot(plot_id: int, diameters: list[float]) -> CircularPlot:
        """Plot whose two thickest trees carry no measured height."""
        ordered = sorted(diameters)
        trees = [
            Tree(
                species=sp,
                diameter_cm=d,
                height_m=None if d in ordered[-2:] else naslund_height(d),
            )
            for d in diameters
        ]
        return CircularPlot(id=plot_id, radius_m=10.0, trees=trees)

    # 0.0314 ha plots holding 10 stems each -> a reference cell holds ~3.2 trees,
    # and 8 measured heights per plot are ample to resolve it.
    p1 = make_plot(1, [12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0, 26.0, 28.0, 30.0])
    p2 = make_plot(2, [13.0, 15.0, 17.0, 19.0, 21.0, 23.0, 25.0, 27.0, 29.0, 31.0])
    stand = Stand(plots=[p1, p2])

    # Legacy strict estimator: the top-by-diameter trees have no height -> None.
    assert stand.get_dominant_height() is None
    # Flexible estimator uses the measured heights that do exist.
    measured_est = stand.estimate_top_height("garcia_u")
    assert measured_est is not None
    # A fitted curve gives the thick trees interpolated heights, so it also works.
    curve_est = stand.estimate_top_height("garcia_u", height_source="naslund")
    assert curve_est is not None
    # The curve estimate reflects the thick trees, so it exceeds the measured one.
    assert float(curve_est) > float(measured_est)


def test_estimate_top_height_after_polygon_thin():
    """Polygon thinning removing all trees yields None."""
    sp = parse_tree_species("picea abies")
    p = CircularPlot(
        id=1,
        radius_m=10,
        trees=[
            Tree(species=sp, diameter_cm=30, height_m=20, position=(0, 0)),
            Tree(species=sp, diameter_cm=20, height_m=18, position=(1, 1)),
        ],
    )
    stand = Stand(plots=[p])
    poly = Polygon([(-1, -1), (-1, 2), (2, 2), (2, -1)])
    stand.thin_trees(polygon=poly)
    assert stand.estimate_top_height() is None
