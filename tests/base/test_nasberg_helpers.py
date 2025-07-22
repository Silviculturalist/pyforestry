import pytest

from pyforestry.base.pricelist import solutioncube  # noqa: F401
from pyforestry.base.taper import Taper
from pyforestry.base.timber_bucking.nasberg_1985 import (
    BuckingResult,
    CrossCutSection,
    Nasberg_1985_BranchBound,
    QualityType,
    _TreeCache,
)


class DummyTaper(Taper):
    def get_diameter_at_height(self, height_m):
        return height_m * 2

    def get_height_at_diameter(self, diameter):
        return diameter / 2


class CountingTaper(DummyTaper):
    def __init__(self):
        self.diameter_calls = 0
        self.height_calls = 0

    def get_diameter_at_height(self, height_m):
        self.diameter_calls += 1
        return super().get_diameter_at_height(height_m)

    def get_height_at_diameter(self, diameter):
        self.height_calls += 1
        return super().get_height_at_diameter(diameter)


def test_tree_cache():
    cache = _TreeCache()
    taper = CountingTaper()

    assert cache.diameter(taper, 10) == 2.0
    assert cache.height(taper, 6) == 30
    assert taper.diameter_calls == 1
    assert taper.height_calls == 1

    assert cache.diameter(taper, 10) == 2.0
    assert cache.height(taper, 6) == 30
    assert taper.diameter_calls == 1
    assert taper.height_calls == 1


def test_merge_sections():
    a = CrossCutSection(
        0,
        5,
        2.0,
        25,
        50,
        "pine",
        timber_proportion=0.5,
        pulp_proportion=0.3,
        cull_proportion=0.1,
        fuelwood_proportion=0.1,
        quality=QualityType.MiddleLog,
    )
    b = CrossCutSection(
        5,
        15,
        3.0,
        20,
        80,
        "pine",
        timber_proportion=0.2,
        pulp_proportion=0.5,
        cull_proportion=0.2,
        fuelwood_proportion=0.1,
        quality=QualityType.MiddleLog,
    )
    merged = Nasberg_1985_BranchBound._merge_sections(a, b)
    assert merged.start_point == 0
    assert merged.end_point == 15
    assert merged.volume == 5.0
    assert merged.top_diameter == 20
    assert merged.value == 130
    assert merged.timber_proportion == pytest.approx(0.32)
    assert merged.pulp_proportion == pytest.approx(0.42)
    assert merged.cull_proportion == pytest.approx(0.16)
    assert merged.fuelwood_proportion == pytest.approx(0.1)
    assert merged.quality == QualityType.MiddleLog


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


def test_bucking_result_plot(monkeypatch):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    shown = []
    monkeypatch.setattr(plt, "show", lambda: shown.append(True))

    res = BuckingResult(
        species_group="spruce",
        total_value=0,
        top_proportion=0.0,
        dead_wood_proportion=0.0,
        high_stump_volume_proportion=0.0,
        high_stump_value_proportion=0.0,
        last_cut_relative_height=0.0,
        volume_per_quality=[0] * 7,
        timber_price_by_quality=[0] * 7,
        vol_fub_5cm=0.0,
        vol_sk_ub=0.0,
        DBH_cm=10,
        height_m=20,
        stump_height_m=0.3,
        diameter_stump_cm=12,
        taperDiams_cm=[15, 10],
        taperHeights_m=[0.3, 2.0],
        sections=[CrossCutSection(0, 10, 0.1, 15, 5, "spruce")],
    )

    res.plot()
    assert shown


def test_bucking_result_plot_no_sections():
    res = BuckingResult(
        species_group="spruce",
        total_value=0,
        top_proportion=0.0,
        dead_wood_proportion=0.0,
        high_stump_volume_proportion=0.0,
        high_stump_value_proportion=0.0,
        last_cut_relative_height=0.0,
        volume_per_quality=[0] * 7,
        timber_price_by_quality=[0] * 7,
        vol_fub_5cm=0.0,
        vol_sk_ub=0.0,
        DBH_cm=10,
        height_m=20,
        stump_height_m=0.3,
        diameter_stump_cm=12,
        taperDiams_cm=[15, 10],
        taperHeights_m=[0.3, 2.0],
        sections=[],
    )
    with pytest.raises(ValueError):
        res.plot()
