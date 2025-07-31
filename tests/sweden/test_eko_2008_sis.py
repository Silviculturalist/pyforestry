import pytest

from pyforestry.base.helpers import Age, SiteIndexValue
from pyforestry.sweden.site.enums import Sweden
from pyforestry.sweden.siteindex.sis.eko_2008 import eko_pm_2008_estimate_si_birch


def test_eko_pm_2008_returns_siteindexvalue():
    si = eko_pm_2008_estimate_si_birch(
        altitude=100.0,
        latitude=60.0,
        vegetation=Sweden.FieldLayer.BILBERRY,
        ground_layer=Sweden.BottomLayer.FRESH_MOSS,
        lateral_water=Sweden.SoilWater.SELDOM_NEVER,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
    )
    assert isinstance(si, SiteIndexValue)
    assert si.reference_age == Age.DBH(50)
    assert 0 < float(si) < 50


@pytest.mark.parametrize(
    "latitude,soil_moisture,expected",
    [
        (61.0, Sweden.SoilMoistureEnum.MESIC, 19.768),
        (61.0, Sweden.SoilMoistureEnum.MOIST, 19.21),
        (59.0, Sweden.SoilMoistureEnum.MESIC, 17.643),
        (59.0, Sweden.SoilMoistureEnum.MOIST, 18.676),
    ],
)
def test_eko_pm_2008_branch_values(latitude, soil_moisture, expected):
    si = eko_pm_2008_estimate_si_birch(
        altitude=100.0,
        latitude=latitude,
        vegetation=Sweden.FieldLayer.BILBERRY,
        ground_layer=Sweden.BottomLayer.FRESH_MOSS,
        lateral_water=Sweden.SoilWater.SELDOM_NEVER,
        soil_moisture=soil_moisture,
    )
    assert isinstance(si, SiteIndexValue)
    assert float(si) == pytest.approx(expected, rel=1e-6)


def test_eko_pm_2008_invalid_soil_moisture():
    with pytest.raises(ValueError):
        eko_pm_2008_estimate_si_birch(
            altitude=100.0,
            latitude=59.0,
            vegetation=Sweden.FieldLayer.BILBERRY,
            ground_layer=Sweden.BottomLayer.FRESH_MOSS,
            lateral_water=Sweden.SoilWater.SELDOM_NEVER,
            soil_moisture=Sweden.SoilMoistureEnum.DRY,
        )
