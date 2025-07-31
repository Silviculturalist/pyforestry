from math import pi

import pytest

from pyforestry.base.pricelist.pricelist import (
    LengthRange,
    Pricelist,
    TimberPriceForDiameter,
    TimberPricelist,
)
from pyforestry.base.taper.taper import Taper
from pyforestry.base.timber.timber_base import Timber
from pyforestry.base.timber_bucking.nasberg_1985 import (
    BuckingConfig,
    Nasberg_1985_BranchBound,
    QualityType,
)


class SimpleTaper(Taper):
    """Constant-diameter taper returning simple volumes."""

    def __init__(self, timber: Timber, diameter: float, height_at_diam: float):
        self.diameter = diameter
        self.had = height_at_diam
        super().__init__(timber, self)

    def get_diameter_at_height(self, height_m: float) -> float:  # type: ignore[override]
        return self.diameter if 0 <= height_m <= self.had else 0.0

    def get_height_at_diameter(self, diameter: float) -> float:  # type: ignore[override]
        return self.had

    def volume_section(self, h1_m: float, h2_m: float) -> float:  # type: ignore[override]
        radius = self.diameter / 200  # cm to m, radius
        return max(0.0, h2_m - h1_m) * pi * radius * radius


def make_pricelist() -> Pricelist:
    pl = Pricelist()
    tp = TimberPricelist(15, 15, volume_type="m3fub")
    tp.set_price_for_diameter(15, TimberPriceForDiameter(10, 10, 10))
    pl.Timber["pine"] = tp
    pl.PulpLogLength = LengthRange(2.0, 2.0)
    pl.TimberLogLength = LengthRange(2.0, 2.0)
    pl.Pulp._prices["pine"] = 1
    pl.LogCullPrice = 0
    pl.FuelWoodPrice = 0
    return pl


class Weights:
    pulpwoodPercentage = 20.0
    fuelWoodPercentage = 10.0
    logCullPercentage = 10.0


def test_downgrading_and_section_merge(monkeypatch):
    t = Timber("pine", 15, 6, stump_height_m=0)
    pl = make_pricelist()

    Pricelist.getPulpWoodWasteProportion = lambda self, s: 0.0  # type: ignore[attr-defined]
    Pricelist.getPulpwoodFuelwoodProportion = lambda self, s: 0.0  # type: ignore[attr-defined]

    nb = Nasberg_1985_BranchBound(t, pl, lambda timber: SimpleTaper(timber, 15, t.height_m))
    monkeypatch.setattr(nb._timber_prices, "getTimberWeight", lambda part: Weights())

    res = nb.calculate_tree_value(
        min_diam_dead_wood=16, config=BuckingConfig(use_downgrading=True, save_sections=True)
    )

    idx = QualityType.ButtLog.value
    assert res.total_value == pytest.approx(2.8628, rel=1e-4)
    assert res.volume_per_quality[idx] == pytest.approx(0.10603, rel=1e-4)
    assert res.timber_price_by_quality[idx] == pytest.approx(10.0, rel=1e-6)

    assert res.sections is not None
    assert len(res.sections) == 1
    section = res.sections[0]
    assert section.start_point == 0
    assert section.end_point == 60
    assert section.volume == pytest.approx(0.10603, rel=1e-4)
    assert section.value == pytest.approx(2.8628, rel=1e-4)
