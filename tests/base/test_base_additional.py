import pytest
from shapely.geometry import Polygon

from pyforestry.base.helpers import (
    Age,
    BuckingResult,
    CircularPlot,
    CrossCutSection,
    Stand,
    Tree,
    parse_tree_species,
)
from pyforestry.base.helpers.bucking import _TreeCache
from pyforestry.base.helpers.tree_species import get_tree_type_by_genus


def test_helpers_init_exports() -> None:
    from pyforestry.base.helpers import __all__ as helpers_all

    assert "Age" in helpers_all
    measurement = Age.TOTAL(5)
    assert measurement.code == Age.TOTAL.value


class DummyTaper:
    def __init__(self):
        self.diam_calls = 0
        self.h_calls = 0

    def get_diameter_at_height(self, height_m):
        self.diam_calls += 1
        return height_m * 2

    def get_height_at_diameter(self, diameter):
        self.h_calls += 1
        return diameter / 2


def test_tree_cache_caches_results():
    taper = DummyTaper()
    cache = _TreeCache()

    assert cache.diameter(taper, 10) == 2
    assert cache.diameter(taper, 10) == 2
    assert taper.diam_calls == 1

    assert cache.height(taper, 8) == 40
    assert cache.height(taper, 8) == 40
    assert taper.h_calls == 1


def test_bucking_result_mapping_and_plot(monkeypatch):
    shown = []
    import matplotlib.pyplot as plt

    monkeypatch.setattr(plt, "show", lambda: shown.append(True))

    section = CrossCutSection(0, 10, 0.1, 15, 5, "spruce")
    res = BuckingResult(
        species_group="spruce",
        total_value=1.0,
        top_proportion=0.0,
        dead_wood_proportion=0.0,
        high_stump_volume_proportion=0.0,
        high_stump_value_proportion=0.0,
        last_cut_relative_height=0.0,
        volume_per_quality=[0],
        timber_price_by_quality=[0],
        vol_fub_5cm=0.0,
        vol_sk_ub=0.0,
        DBH_cm=10,
        height_m=20,
        stump_height_m=0.3,
        diameter_stump_cm=12,
        taperDiams_cm=[15, 10],
        taperHeights_m=[0.3, 2.0],
        sections=[section],
    )

    assert res["species_group"] == "spruce"
    assert set(iter(res))
    assert len(res) > 0

    res.plot()
    assert shown


@pytest.mark.parametrize("attr", ["foo", "BAR"])
def test_standmetric_accessor_bad_attr(attr):
    stand = Stand()
    accessor = stand.BasalArea
    with pytest.raises(AttributeError):
        getattr(accessor, attr)


def test_thin_trees_polygon_and_uid():
    sp = parse_tree_species("picea abies")
    t1 = Tree(position=(0, 0), species=sp, uid="A")
    t2 = Tree(position=(5, 5), species=sp, uid="B")
    plot = CircularPlot(id=1, radius_m=10, trees=[t1, t2])
    stand = Stand(plots=[plot])

    poly = Polygon([(-1, -1), (6, -1), (6, 6), (-1, 6)])
    stand.thin_trees(uids=["B"], polygon=poly)

    remaining_uids = [tr.uid for tr in stand.plots[0].trees]
    assert remaining_uids == ["A"]


def test_thin_trees_angle_count_error():
    sp = parse_tree_species("picea abies")
    plot = CircularPlot(id=1, radius_m=5.0, AngleCount=[], trees=[Tree(species=sp)])
    stand = Stand(plots=[plot])
    stand.use_angle_count = True
    with pytest.raises(ValueError):
        stand.thin_trees()


def test_tree_species_parse_invalid():
    with pytest.raises(ValueError):
        parse_tree_species("unknown tree")


def test_get_tree_type_by_genus_unknown():
    with pytest.raises(ValueError):
        get_tree_type_by_genus("mystery")


def test_parse_tree_species_error_message():
    with pytest.raises(ValueError, match="Could not find species matching"):
        parse_tree_species("nope nope")


def test_get_tree_type_unknown_message():
    with pytest.raises(ValueError, match="Unknown tree type"):
        get_tree_type_by_genus("mysteryus")
