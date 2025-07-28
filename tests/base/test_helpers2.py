import pytest

from pyforestry.base.helpers import CircularPlot
from pyforestry.base.helpers.bucking import BuckingResult
from pyforestry.base.helpers.primitives import (
    AtomicVolume,
    CompositeVolume,
    TopHeightDefinition,
    TopHeightMeasurement,
)
from pyforestry.base.helpers.primitives.sitebase import SiteBase
from pyforestry.base.helpers.tree_species import parse_tree_species


class DummySite(SiteBase):
    computed: bool = False

    def compute_attributes(self) -> None:  # pragma: no cover - trivial
        self.computed = True


def test_sitebase_subclass():
    site = DummySite(1.0, 2.0)
    assert site.latitude == 1.0
    assert site.computed


def test_circularplot_area_mismatch():
    with pytest.raises(ValueError):
        CircularPlot(id=1, radius_m=10, area_m2=200)


def test_bucking_result_plot_empty():
    result = BuckingResult(
        species_group="spruce",
        total_value=0.0,
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
        taperDiams_cm=[10, 8],
        taperHeights_m=[0.3, 2.0],
        sections=[],
    )
    with pytest.raises(ValueError):
        result.plot()


def test_topheight_classes_repr():
    definition = TopHeightDefinition(nominal_n=150)
    meas = TopHeightMeasurement(30.0, definition)
    assert "TopHeightDefinition" in repr(definition)
    assert "TopHeightMeasurement" in repr(meas)


def test_volume_addition_and_repr():
    a1 = AtomicVolume(1.0, region="Sweden", species="pine", type="m3sk")
    a2 = AtomicVolume(2.0, region="Sweden", species="pine", type="m3sk")
    merged = a1 + a2
    assert isinstance(merged, AtomicVolume)
    assert merged.value == 3.0

    b = AtomicVolume(1.0, region="Norway", species="spruce", type="m3sk")
    comp = merged + b
    assert isinstance(comp, CompositeVolume)
    assert len(comp) == 2
    assert "CompositeVolume" in repr(comp)


def test_parse_tree_species_roundtrip():
    sp = parse_tree_species("picea abies")
    assert sp.full_name == "picea abies"
    again = parse_tree_species(sp)
    assert again is sp
