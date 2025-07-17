import pytest
from pyforestry.base.helpers import Age, SiteIndexValue
from pyforestry.sweden.site.enums import Sweden
from pyforestry.sweden.siteindex.sis.hagglund_lundmark_1979 import (
    Hagglund_Lundmark_1979_SIS,
    _county_code,
    _enum_code,
)


def test_enum_code_with_enums():
    assert _enum_code(Sweden.SoilMoistureEnum.DRY) == 1
    assert _enum_code(Sweden.ClimateZone.K1) == "K1"


def test_county_code_helper():
    assert _county_code(Sweden.County.UPPSALA) == 16


def _common_params():
    return dict(
        latitude=60.0,
        altitude=100.0,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        ground_layer=Sweden.BottomLayer.FRESH_MOSS,
        vegetation=Sweden.FieldLayer.BILBERRY,
        soil_texture=Sweden.SoilTextureTill.SANDY,
        climate_code=Sweden.ClimateZone.K1,
        lateral_water=Sweden.SoilWater.SELDOM_NEVER,
        soil_depth=Sweden.SoilDepth.DEEP,
        incline_percent=5.0,
        aspect=0.0,
        ditched=False,
        gotland=False,
        coast=False,
        limes_norrlandicus=False,
        nfi_adjustments=True,
        dlan=Sweden.County.UPPSALA,
    )


def test_sis_spruce_with_enums():
    params = _common_params()
    params.update(species="Picea abies", peat=False)
    sis = Hagglund_Lundmark_1979_SIS(**params)
    assert isinstance(sis, SiteIndexValue)
    assert sis.reference_age == Age.TOTAL(100)
    assert 0 < float(sis) < 50


def test_sis_with_county_enum():
    params = _common_params()
    params.update(species="Picea abies", peat=False, dlan=Sweden.County.VASTMANLAND)
    sis = Hagglund_Lundmark_1979_SIS(**params)
    assert isinstance(sis, SiteIndexValue)
    assert 0 < float(sis) < 50


def test_sis_pine_on_peat():
    params = _common_params()
    params.update(
        species="Pinus sylvestris",
        peat=True,
        soil_texture=Sweden.SoilTextureTill.PEAT,
        lateral_water=Sweden.SoilWater.LONGER_PERIODS,
        soil_moisture=Sweden.SoilMoistureEnum.MOIST,
    )
    sis = Hagglund_Lundmark_1979_SIS(**params)
    assert isinstance(sis, SiteIndexValue)
    assert 0 < float(sis) < 50


def test_invalid_species_raises():
    params = _common_params()
    params.update(species="Unknown", peat=False)
    with pytest.raises(ValueError):
        Hagglund_Lundmark_1979_SIS(**params)
