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
