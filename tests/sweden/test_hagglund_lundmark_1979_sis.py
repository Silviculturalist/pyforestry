import numpy as np
import pytest

from pyforestry.base.helpers import Age, SiteIndexValue, enum_code
from pyforestry.sweden.site.enums import Sweden
from pyforestry.sweden.siteindex.sis.hagglund_lundmark_1979 import (
    Hagglund_Lundmark_1979_SIS,
)


def test_enum_code_with_enums():
    assert enum_code(Sweden.SoilMoistureEnum.DRY) == 1
    assert enum_code(Sweden.ClimateZone.K1) == "K1"


def test_enum_code_with_county():
    assert enum_code(Sweden.County.UPPSALA) == 16


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


def test_latitude_out_of_range_returns_nan(capsys):
    params = _common_params()
    params.update(latitude=50.0, species="Picea abies", peat=False)
    res = Hagglund_Lundmark_1979_SIS(**params)
    out, _ = capsys.readouterr()
    assert "latitude must be between (55.2, 69.1)" in out
    assert np.isnan(res)


def test_soil_depth_nan_requires_peat(capsys):
    params = _common_params()
    params.update(soil_depth=np.nan, species="Picea abies", peat=False)
    res = Hagglund_Lundmark_1979_SIS(**params)
    out, _ = capsys.readouterr()
    assert "soil_depth must be one of float: NA; int 1-5" in out
    assert np.isnan(res)


def test_invalid_dlan_prints_message(capsys):
    params = _common_params()
    params.update(dlan=0, species="Picea abies", peat=False)
    res = Hagglund_Lundmark_1979_SIS(**params)
    out, _ = capsys.readouterr()
    assert "dlan must be one of int: 1-31 or NA." in out
    assert np.isnan(res)


def test_invalid_lateral_water(capsys):
    params = _common_params()
    params.update(lateral_water=4, species="Picea abies", peat=False)
    res = Hagglund_Lundmark_1979_SIS(**params)
    out, _ = capsys.readouterr()
    assert "lateral_water must be int 1-3" in out
    assert np.isnan(res)


def test_invalid_climate_code(capsys):
    params = _common_params()
    params.update(climate_code="bad", species="Picea abies", peat=False)
    res = Hagglund_Lundmark_1979_SIS(**params)
    out, _ = capsys.readouterr()
    assert "climate_code must be one of float: NA; str: M1, M2, M3, K1, K2, K3" in out
    assert np.isnan(res)


def test_spruce_dry_soil_warning(capsys):
    params = _common_params()
    params.update(
        species="Picea abies",
        soil_moisture=Sweden.SoilMoistureEnum.DRY,
        ground_layer=Sweden.BottomLayer.LICHEN_TYPE,
        peat=False,
    )
    sis = Hagglund_Lundmark_1979_SIS(**params)
    out, _ = capsys.readouterr()
    assert "Warning: No coverage for Spruce on dry soils, switching to mesic." in out
    assert isinstance(sis, SiteIndexValue)


def test_sis_pine_mineral_soil():
    params = _common_params()
    params.update(species="Pinus sylvestris", peat=False)
    sis = Hagglund_Lundmark_1979_SIS(**params)
    assert isinstance(sis, SiteIndexValue)
    assert 0 < float(sis) < 50


def test_altitude_out_of_range_returns_nan(capsys):
    params = _common_params()
    params.update(altitude=2200.0, species="Picea abies", peat=False)
    res = Hagglund_Lundmark_1979_SIS(**params)
    out, _ = capsys.readouterr()
    assert "altitude must be between (0,2117)" in out
    assert np.isnan(res)


def test_invalid_gotland_bool(capsys):
    params = _common_params()
    params.update(gotland="no", species="Picea abies", peat=False)
    res = Hagglund_Lundmark_1979_SIS(**params)
    out, _ = capsys.readouterr()
    assert "Gotland must be a bool: True or False" in out
    assert np.isnan(res)


@pytest.mark.parametrize("species", ["Picea abies", "Pinus sylvestris"])
@pytest.mark.parametrize("latitude", [56.0, 60.0, 65.0])
@pytest.mark.parametrize("altitude", [0, 500, 1000])
@pytest.mark.parametrize(
    "soil_moisture",
    [Sweden.SoilMoistureEnum.MESIC, Sweden.SoilMoistureEnum.MESIC_MOIST],
)
def test_sis_valid_combinations(species, latitude, altitude, soil_moisture):
    """Run the SIS estimator over a grid of valid inputs."""
    params = _common_params()
    params.update(
        species=species,
        peat=False,
        latitude=latitude,
        altitude=altitude,
        soil_moisture=soil_moisture,
    )
    sis = Hagglund_Lundmark_1979_SIS(**params)
    assert isinstance(sis, SiteIndexValue)
    assert 0 < float(sis) < 50


def test_invalid_soil_moisture(capsys):
    params = _common_params()
    params.update(soil_moisture=6, species="Picea abies", peat=False)
    res = Hagglund_Lundmark_1979_SIS(**params)
    out, _ = capsys.readouterr()
    assert "soil_moisture must be int 1 - 5" in out
    assert np.isnan(res)


def test_invalid_ground_layer(capsys):
    params = _common_params()
    params.update(ground_layer=7, species="Picea abies", peat=False)
    res = Hagglund_Lundmark_1979_SIS(**params)
    out, _ = capsys.readouterr()
    assert "ground_layer must be int 1-6" in out
    assert np.isnan(res)


def test_invalid_vegetation(capsys):
    params = _common_params()
    params.update(vegetation=19, species="Picea abies", peat=False)
    res = Hagglund_Lundmark_1979_SIS(**params)
    out, _ = capsys.readouterr()
    assert "Vegetation must be int 1-18" in out
    assert np.isnan(res)


def test_invalid_soil_texture(capsys):
    params = _common_params()
    params.update(soil_texture=10, species="Picea abies", peat=False)
    res = Hagglund_Lundmark_1979_SIS(**params)
    out, _ = capsys.readouterr()
    assert "soil_texture must be int 0-10" in out
    assert np.isnan(res)


def test_invalid_soil_depth_range(capsys):
    params = _common_params()
    params.update(soil_depth=6, species="Picea abies", peat=False)
    res = Hagglund_Lundmark_1979_SIS(**params)
    out, _ = capsys.readouterr()
    assert "soil_depth must be one of float: NA; int 1-5" in out
    assert np.isnan(res)


def test_invalid_incline_percent(capsys):
    params = _common_params()
    params.update(incline_percent=150.0, species="Picea abies", peat=False)
    res = Hagglund_Lundmark_1979_SIS(**params)
    out, _ = capsys.readouterr()
    assert "incline_percent must be float 0-100" in out
    assert np.isnan(res)


def test_invalid_aspect(capsys):
    params = _common_params()
    params.update(aspect=400.0, species="Picea abies", peat=False)
    res = Hagglund_Lundmark_1979_SIS(**params)
    out, _ = capsys.readouterr()
    assert "Aspect must be float 0-360" in out
    assert np.isnan(res)


def test_invalid_peat_bool(capsys):
    params = _common_params()
    params.update(peat="yes", species="Picea abies")
    res = Hagglund_Lundmark_1979_SIS(**params)
    out, _ = capsys.readouterr()
    assert "Peat must be a bool: True or False" in out
    assert np.isnan(res)


def test_warn_nfi_adjustment_bool(capsys):
    params = _common_params()
    params.update(nfi_adjustments="no", species="Picea abies", peat=False)
    sis = Hagglund_Lundmark_1979_SIS(**params)
    out, _ = capsys.readouterr()
    assert "nfi_adjustments must be a bool: True or False" in out
    assert isinstance(sis, SiteIndexValue)


def test_spruce_change_to_pine_branch(capsys):
    params = _common_params()
    params.update(
        species="Picea abies",
        peat=False,
        soil_depth=Sweden.SoilDepth.SHALLOW,
        lateral_water=Sweden.SoilWater.SELDOM_NEVER,
        vegetation=Sweden.FieldLayer.SEDGE_HIGH,
        ground_layer=Sweden.BottomLayer.SWAMP_MOSS,
    )
    sis = Hagglund_Lundmark_1979_SIS(**params)
    capsys.readouterr()
    assert isinstance(sis, SiteIndexValue)
    assert 0 < float(sis) < 50


def test_spruce_on_peat_branch():
    params = _common_params()
    params.update(
        species="Picea abies",
        peat=True,
        soil_texture=Sweden.SoilTextureTill.PEAT,
        lateral_water=Sweden.SoilWater.LONGER_PERIODS,
        soil_moisture=Sweden.SoilMoistureEnum.MOIST,
        ground_layer=Sweden.BottomLayer.SWAMP_MOSS,
    )
    sis = Hagglund_Lundmark_1979_SIS(**params)
    assert isinstance(sis, SiteIndexValue)
    assert 0 < float(sis) < 50
