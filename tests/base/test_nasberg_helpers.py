# Import solutioncube first so nasberg_1985 is fully initialised
from pyforestry.base.pricelist import solutioncube  # noqa: F401
from pyforestry.base.timber_bucking.nasberg_1985 import (
    BuckingResult,
    CrossCutSection,
    Nasberg_1985_BranchBound,
    _TreeCache,
)


class DummyTaper:
    def get_diameter_at_height(self, h):
        return h * 2

    def get_height_at_diameter(self, d):
        return d / 2


def test_tree_cache():
    cache = _TreeCache()
    taper = DummyTaper()
    assert cache.diameter(taper, 10) == 2.0
    assert cache.diameter(taper, 10) == 2.0  # cached
    assert cache.height(taper, 4) == 20
    assert cache.height(taper, 4) == 20  # cached


def test_merge_sections():
    a = CrossCutSection(0, 10, 1.0, 20, 50, "pine")
    b = CrossCutSection(10, 20, 1.0, 15, 40, "pine")
    merged = Nasberg_1985_BranchBound._merge_sections(a, b)
    assert merged.start_point == 0
    assert merged.end_point == 20
    assert merged.volume == 2.0


def test_bucking_result_mapping():
    res = BuckingResult(
        species_group="spruce",
        total_value=100.0,
        top_proportion=0.1,
        dead_wood_proportion=0.0,
        high_stump_volume_proportion=0.0,
        high_stump_value_proportion=0.0,
        last_cut_relative_height=1.0,
        volume_per_quality=[0] * 7,
        timber_price_by_quality=[0] * 7,
        vol_fub_5cm=1.0,
        vol_sk_ub=1.0,
        DBH_cm=20,
        height_m=30,
        stump_height_m=0.3,
        diameter_stump_cm=25,
        taperDiams_cm=[30],
        taperHeights_m=[0.3],
    )
    assert len(res) > 0
    assert res["species_group"] == "spruce"
    assert "total_value" in list(res)
