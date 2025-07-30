import matplotlib.pyplot as plt
import pytest

from pyforestry.base.helpers import (
    BuckingResult,
    CrossCutSection,
)
from pyforestry.base.helpers.primitives import (
    AgeMeasurement,
    AtomicVolume,
    CompositeVolume,
    StandBasalArea,
    Stems,
)
from pyforestry.base.helpers.primitives.sitebase import SiteBase


class DummySite2(SiteBase):
    def compute_attributes(self) -> None:
        self.called = True


def test_sitebase_base_method():
    site = DummySite2(1.0, 2.0)
    assert hasattr(site, "called")
    # call the abstract method on the base class to execute the pass line
    SiteBase.compute_attributes(site)


def test_age_repr_unknown():
    age = AgeMeasurement(10.0, 1)
    age.code = 99
    assert "UNKNOWN" in repr(age)


def test_area_aggregates_repr():
    ba = StandBasalArea(10.0)
    st = Stems(5.0)
    assert "StandBasalArea" in repr(ba)
    assert "Stems" in repr(st)


def test_atomicvolume_invalid_ops():
    vol = AtomicVolume(1.0)
    assert AtomicVolume.__truediv__(vol, "x") is NotImplemented
    assert AtomicVolume.__eq__(vol, "x") is NotImplemented


def test_compositevolume_invalid_ops():
    vol = AtomicVolume(1.0)
    with pytest.raises(TypeError):
        CompositeVolume([vol, 1])

    comp = CompositeVolume([vol])
    assert comp.__add__("x") is NotImplemented
    assert comp.__mul__("x") is NotImplemented


def test_buckingresult_methods(monkeypatch):
    result = BuckingResult(
        species_group="a",
        total_value=0.0,
        top_proportion=0.0,
        dead_wood_proportion=0.0,
        high_stump_volume_proportion=0.0,
        high_stump_value_proportion=0.0,
        last_cut_relative_height=0.0,
        volume_per_quality=[0.0],
        timber_price_by_quality=[0.0],
        vol_fub_5cm=0.0,
        vol_sk_ub=0.0,
        DBH_cm=10.0,
        height_m=15.0,
        stump_height_m=0.3,
        diameter_stump_cm=12.0,
        taperDiams_cm=[10.0, 8.0],
        taperHeights_m=[0.3, 2.0],
        sections=[CrossCutSection(-5, -2, 0.01, 5.0, 1.0, "a")],
    )
    with pytest.raises(KeyError):
        _ = result["missing"]

    monkeypatch.setattr(plt, "show", lambda: None)
    result.plot()
