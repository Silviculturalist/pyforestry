from pyforestry.base.helpers import Age, SiteIndexValue
from pyforestry.sweden.site.enums import Sweden
from pyforestry.sweden.siteindex.sis.tegnhammar_1992_adjusted_spruce_si_by_stand_variables import (
    tegnhammar_1992_adjusted_spruce_si_by_stand_variables,
)


def test_tegnhammar_si_returns_siteindexvalue():
    si = tegnhammar_1992_adjusted_spruce_si_by_stand_variables(
        latitude=60.0,
        longitude=18.0,
        altitude=100.0,
        vegetation=Sweden.FieldLayer.BILBERRY,
        ground_layer=Sweden.BottomLayer.FRESH_MOSS,
        aspect_main=0,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        soil_depth=Sweden.SoilDepth.DEEP,
        soil_texture=Sweden.SoilTextureTill.SANDY,
    )
    assert isinstance(si, SiteIndexValue)
    assert si.reference_age == Age.TOTAL(100)
    assert 0 < float(si) < 50
