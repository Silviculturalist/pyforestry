import numpy as np
import pytest

from pyforestry.base.helpers import Age, SiteIndexValue, enum_code
from pyforestry.sweden.site.enums import Sweden
from pyforestry.sweden.siteindex.sis import hagglund_lundmark_1979 as hlm
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


def test_dry_soil_swamp_adjustment_no_warning(capsys):
    params = _common_params()
    params.update(
        species="Picea abies",
        soil_moisture=Sweden.SoilMoistureEnum.DRY,
        ground_layer=Sweden.BottomLayer.SWAMP_MOSS,
        peat=False,
    )
    sis = Hagglund_Lundmark_1979_SIS(**params)
    out, _ = capsys.readouterr()
    assert "Warning: No coverage for Spruce" not in out
    assert isinstance(sis, SiteIndexValue)


@pytest.mark.parametrize(
    "soil_moisture,vegetation,ground_layer,lateral_water,soil_depth",
    [
        (
            Sweden.SoilMoistureEnum.MESIC,
            Sweden.FieldLayer.SEDGE_HIGH,
            Sweden.BottomLayer.BOGMOSS_TYPE,
            Sweden.SoilWater.SELDOM_NEVER,
            Sweden.SoilDepth.DEEP,
        ),
        (
            Sweden.SoilMoistureEnum.MESIC,
            Sweden.FieldLayer.SEDGE_HIGH,
            Sweden.BottomLayer.LICHEN_TYPE,
            Sweden.SoilWater.SELDOM_NEVER,
            Sweden.SoilDepth.DEEP,
        ),
        (
            Sweden.SoilMoistureEnum.MESIC,
            Sweden.FieldLayer.BROADLEAVED_GRASS,
            Sweden.BottomLayer.FRESH_MOSS,
            Sweden.SoilWater.SELDOM_NEVER,
            Sweden.SoilDepth.DEEP,
        ),
        (
            Sweden.SoilMoistureEnum.MESIC,
            Sweden.FieldLayer.BROADLEAVED_GRASS,
            Sweden.BottomLayer.FRESH_MOSS,
            Sweden.SoilWater.SELDOM_NEVER,
            Sweden.SoilDepth.SHALLOW,
        ),
        (
            Sweden.SoilMoistureEnum.MOIST,
            Sweden.FieldLayer.LOW_HERB_WITHOUT_SHRUBS,
            Sweden.BottomLayer.FRESH_MOSS,
            Sweden.SoilWater.SELDOM_NEVER,
            Sweden.SoilDepth.DEEP,
        ),
    ],
)
def test_pine_branches(
    soil_moisture,
    vegetation,
    ground_layer,
    lateral_water,
    soil_depth,
):
    params = _common_params()
    params.update(
        species="Pinus sylvestris",
        peat=False,
        soil_moisture=soil_moisture,
        vegetation=vegetation,
        ground_layer=ground_layer,
        lateral_water=lateral_water,
        soil_depth=soil_depth,
        soil_texture=Sweden.SoilTextureTill.SANDY,
    )
    sis = Hagglund_Lundmark_1979_SIS(**params)
    assert isinstance(sis, SiteIndexValue)
    assert 0 < float(sis) < 50


def test_invalid_coast_bool(capsys):
    params = _common_params()
    params.update(coast="no", species="Picea abies", peat=False)
    sis = Hagglund_Lundmark_1979_SIS(**params)
    out, _ = capsys.readouterr()
    assert "coast must be a bool: True or False" in out
    assert isinstance(sis, SiteIndexValue)


def test_invalid_limes_bool(capsys):
    params = _common_params()
    params.update(limes_norrlandicus="no", species="Picea abies", peat=False)
    sis = Hagglund_Lundmark_1979_SIS(**params)
    out, _ = capsys.readouterr()
    assert "limes_norrlandicus must be a bool: True or False" in out
    assert isinstance(sis, SiteIndexValue)


def test_mineral_soil_texture_zero():
    params = _common_params()
    params.update(species="Pinus sylvestris", peat=False, soil_texture=0)
    sis = Hagglund_Lundmark_1979_SIS(**params)
    assert isinstance(sis, SiteIndexValue)
    assert 0 < float(sis) < 50


def test_spruce_missing_texture_replacement():
    params1 = _common_params()
    params1.update(
        species="Picea abies",
        peat=False,
        soil_texture=0,
        soil_depth=Sweden.SoilDepth.DEEP,
    )
    sis_missing = Hagglund_Lundmark_1979_SIS(**params1)

    params2 = _common_params()
    params2.update(
        species="Picea abies",
        peat=False,
        soil_texture=Sweden.SoilTextureTill.BOULDER,
        soil_depth=Sweden.SoilDepth.SHALLOW,
    )
    sis_replaced = Hagglund_Lundmark_1979_SIS(**params2)

    assert float(sis_missing) == pytest.approx(float(sis_replaced), rel=1e-6)


def test_spruce_lichen_reclassification():
    params1 = _common_params()
    params1.update(
        species="Picea abies",
        peat=False,
        soil_moisture=Sweden.SoilMoistureEnum.MOIST,
        ground_layer=Sweden.BottomLayer.LICHEN_TYPE,
        vegetation=Sweden.FieldLayer.BILBERRY,
    )
    sis_auto = Hagglund_Lundmark_1979_SIS(**params1)

    params2 = _common_params()
    params2.update(
        species="Picea abies",
        peat=False,
        soil_moisture=Sweden.SoilMoistureEnum.MOIST,
        ground_layer=Sweden.BottomLayer.SWAMP_MOSS,
        vegetation=Sweden.FieldLayer.HORSETAIL,
    )
    sis_manual = Hagglund_Lundmark_1979_SIS(**params2)

    assert float(sis_auto) == pytest.approx(float(sis_manual), rel=1e-6)


def test_spruce_wet_no_lateral_water_adjustment():
    params1 = _common_params()
    params1.update(
        species="Picea abies",
        peat=False,
        soil_moisture=Sweden.SoilMoistureEnum.WET,
        lateral_water=Sweden.SoilWater.SELDOM_NEVER,
    )
    sis_wet = Hagglund_Lundmark_1979_SIS(**params1)

    params2 = _common_params()
    params2.update(
        species="Picea abies",
        peat=False,
        soil_moisture=Sweden.SoilMoistureEnum.MOIST,
        lateral_water=Sweden.SoilWater.LONGER_PERIODS,
        ground_layer=Sweden.BottomLayer.SWAMP_MOSS,
    )
    sis_moist = Hagglund_Lundmark_1979_SIS(**params2)

    assert float(sis_wet) == pytest.approx(0.7 * float(sis_moist), rel=1e-6)


def test_spruce_gravel_texture_branch():
    params1 = _common_params()
    params1.update(
        species="Picea abies",
        peat=False,
        soil_depth=Sweden.SoilDepth.SHALLOW,
        soil_texture=Sweden.SoilTextureTill.SANDY,
        lateral_water=Sweden.SoilWater.LONGER_PERIODS,
    )
    sis_gravel = Hagglund_Lundmark_1979_SIS(**params1)

    params2 = _common_params()
    params2.update(
        species="Picea abies",
        peat=False,
        soil_depth=Sweden.SoilDepth.SHALLOW,
        soil_texture=Sweden.SoilTextureTill.GRAVEL,
        lateral_water=Sweden.SoilWater.LONGER_PERIODS,
    )
    sis_manual = Hagglund_Lundmark_1979_SIS(**params2)

    assert float(sis_gravel) == pytest.approx(float(sis_manual), rel=1e-6)


def test_spruce_change_to_pine_deepsoil():
    params_k3 = _common_params()
    params_k3.update(
        species="Picea abies",
        peat=False,
        soil_texture=Sweden.SoilTextureTill.BOULDER,
        soil_depth=Sweden.SoilDepth.DEEP,
        lateral_water=Sweden.SoilWater.SELDOM_NEVER,
        ground_layer=Sweden.BottomLayer.LICHEN_TYPE,
        vegetation=Sweden.FieldLayer.HIGH_HERB_WITHOUT_SHRUBS,
        climate_code=Sweden.ClimateZone.K3,
    )
    sis_k3 = Hagglund_Lundmark_1979_SIS(**params_k3)

    params_k1 = params_k3.copy()
    params_k1["climate_code"] = Sweden.ClimateZone.K1
    sis_k1 = Hagglund_Lundmark_1979_SIS(**params_k1)

    assert float(sis_k3) > float(sis_k1)


def test_pine_on_peat_without_adjustments():
    params1 = _common_params()
    params1.update(
        species="Pinus sylvestris",
        peat=True,
        soil_texture=Sweden.SoilTextureTill.PEAT,
        lateral_water=Sweden.SoilWater.LONGER_PERIODS,
        soil_moisture=Sweden.SoilMoistureEnum.MOIST,
        ground_layer=Sweden.BottomLayer.SWAMP_MOSS,
        nfi_adjustments=False,
        coast=False,
        limes_norrlandicus=True,
    )
    sis_no_adj = Hagglund_Lundmark_1979_SIS(**params1)

    params1["nfi_adjustments"] = True
    sis_adj = Hagglund_Lundmark_1979_SIS(**params1)

    assert sis_no_adj != sis_adj


def test_pine_latitude_altitude_extremes():
    params = _common_params()
    params.update(
        species="Pinus sylvestris",
        peat=False,
        soil_moisture=Sweden.SoilMoistureEnum.MOIST,
        vegetation=Sweden.FieldLayer.HIGH_HERB_WITHOUT_SHRUBS,
        ground_layer=Sweden.BottomLayer.FRESH_MOSS,
        soil_depth=Sweden.SoilDepth.DEEP,
        soil_texture=Sweden.SoilTextureTill.SANDY,
        lateral_water=Sweden.SoilWater.SELDOM_NEVER,
        altitude=0.0,
        latitude=55.2,
    )
    low = Hagglund_Lundmark_1979_SIS(**params)

    params.update(altitude=2110.0, latitude=69.0)
    high = Hagglund_Lundmark_1979_SIS(**params)

    assert low != high


def test_nfi_adjustments_sets_flags():
    params1 = _common_params()
    params1.update(
        species="Picea abies",
        peat=False,
        nfi_adjustments=True,
        coast=False,
        limes_norrlandicus=False,
    )
    sis_auto = Hagglund_Lundmark_1979_SIS(**params1)

    params2 = params1.copy()
    params2.update(coast=True, limes_norrlandicus=True)
    sis_manual = Hagglund_Lundmark_1979_SIS(**params2)

    assert float(sis_auto) == pytest.approx(float(sis_manual), rel=1e-6)


def test_spruce_negative_sis_raises(monkeypatch):
    monkeypatch.setattr(hlm, "exp", lambda x: -1.0)
    params = _common_params()
    params.update(species="Picea abies", peat=False)
    with pytest.raises(ValueError, match="SIS estimated < 0"):
        hlm.NFI_SIS_SPRUCE(**params)


def test_pine_excessive_sis_raises(monkeypatch):
    monkeypatch.setattr(hlm, "exp", lambda x: 1e6)
    params = _common_params()
    params.update(species="Pinus sylvestris", peat=False)
    with pytest.raises(ValueError, match="SIS estimated > 50"):
        hlm.NFI_SIS_PINE(**params)


def test_invalid_soil_moisture_spruce_raises():
    params = _common_params()
    params.update(species="Picea abies", peat=False, soil_moisture=6)
    with pytest.raises(ValueError, match="No SIS method found"):
        hlm.NFI_SIS_SPRUCE(**params)


def test_invalid_soil_moisture_pine_raises():
    params = _common_params()
    params.update(species="Pinus sylvestris", peat=False, soil_moisture=0)
    with pytest.raises(ValueError, match="No SIS method found"):
        hlm.NFI_SIS_PINE(**params)


def test_pine_adjustment_floor(monkeypatch):
    monkeypatch.setattr(hlm, "exp", lambda x: 1.0)
    params = _common_params()
    params.update(
        species="Pinus sylvestris",
        peat=False,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        vegetation=Sweden.FieldLayer.BILBERRY,
        ground_layer=Sweden.BottomLayer.SWAMP_MOSS,
    )
    params_low = params.copy()
    params_low.update(altitude=0.0)
    sis_low = Hagglund_Lundmark_1979_SIS(**params_low)
    params_high = params.copy()
    params_high.update(altitude=100.0)
    sis_high = Hagglund_Lundmark_1979_SIS(**params_high)

    assert float(sis_low) == pytest.approx(float(sis_high), rel=1e-6)


@pytest.mark.parametrize(
    "vegetation",
    [
        Sweden.FieldLayer.LOW_HERB_WITHOUT_SHRUBS,
        Sweden.FieldLayer.LINGONBERRY,
    ],
)
def test_pine_peat_ditched_vegetation(vegetation):
    params = _common_params()
    params.update(
        species="Pinus sylvestris",
        peat=True,
        soil_texture=Sweden.SoilTextureTill.PEAT,
        lateral_water=Sweden.SoilWater.LONGER_PERIODS,
        soil_moisture=Sweden.SoilMoistureEnum.MOIST,
        ground_layer=Sweden.BottomLayer.SWAMP_MOSS,
        vegetation=vegetation,
        ditched=True,
    )
    sis = Hagglund_Lundmark_1979_SIS(**params)
    assert isinstance(sis, SiteIndexValue)
    assert 0 < float(sis) < 50


def test_pine_groundlayer_altitude_branch():
    params = _common_params()
    params.update(
        species="Pinus sylvestris",
        peat=False,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        vegetation=Sweden.FieldLayer.SEDGE_HIGH,
        ground_layer=Sweden.BottomLayer.LICHEN_TYPE,
        lateral_water=Sweden.SoilWater.LONGER_PERIODS,
        soil_depth=Sweden.SoilDepth.DEEP,
        altitude=400.0,
        incline_percent=20.0,
    )
    sis = Hagglund_Lundmark_1979_SIS(**params)
    assert isinstance(sis, SiteIndexValue)
    assert 0 < float(sis) < 50


def test_pine_climate_code_dlan_branch():
    params = _common_params()
    params.update(
        species="Pinus sylvestris",
        peat=False,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        vegetation=Sweden.FieldLayer.BROADLEAVED_GRASS,
        ground_layer=Sweden.BottomLayer.FRESH_MOSS,
        soil_depth=Sweden.SoilDepth.DEEP,
        climate_code=Sweden.ClimateZone.M2,
        dlan=Sweden.County.UPPSALA,
    )
    sis = Hagglund_Lundmark_1979_SIS(**params)
    assert isinstance(sis, SiteIndexValue)
    assert 0 < float(sis) < 50


@pytest.mark.parametrize(
    "ground_layer",
    [
        Sweden.BottomLayer.LICHEN_TYPE,
        Sweden.BottomLayer.LICHEN_RICH,
    ],
)
def test_pine_dry_groundlayer_branches(ground_layer):
    params = _common_params()
    params.update(
        species="Pinus sylvestris",
        peat=False,
        soil_moisture=Sweden.SoilMoistureEnum.DRY,
        vegetation=Sweden.FieldLayer.HIGH_HERB_WITHOUT_SHRUBS,
        ground_layer=ground_layer,
        climate_code=Sweden.ClimateZone.K3,
        soil_depth=Sweden.SoilDepth.DEEP,
    )
    sis = Hagglund_Lundmark_1979_SIS(**params)
    assert isinstance(sis, SiteIndexValue)
    assert 0 < float(sis) < 50


def test_pine_final_adjustment_flags():
    base = _common_params()
    base.update(
        species="Pinus sylvestris",
        peat=False,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        soil_depth=Sweden.SoilDepth.DEEP,
    )
    neg = base.copy()
    neg.update(vegetation=Sweden.FieldLayer.BROADLEAVED_GRASS, latitude=55.2, altitude=0.0)
    pos = base.copy()
    pos.update(
        vegetation=Sweden.FieldLayer.SEDGE_HIGH,
        ground_layer=Sweden.BottomLayer.LICHEN_TYPE,
        latitude=69.0,
        altitude=1000.0,
        incline_percent=20.0,
    )
    sis_neg = Hagglund_Lundmark_1979_SIS(**neg)
    sis_pos = Hagglund_Lundmark_1979_SIS(**pos)
    assert sis_neg != sis_pos


def test_pine_negative_sis_raises(monkeypatch):
    monkeypatch.setattr(hlm, "exp", lambda x: -1.0)
    params = _common_params()
    params.update(species="Pinus sylvestris", peat=False)
    with pytest.raises(ValueError, match="SIS estimated < 0"):
        hlm.NFI_SIS_PINE(**params)


@pytest.mark.parametrize(
    "lateral", [Sweden.SoilWater.SHORTER_PERIODS, Sweden.SoilWater.LONGER_PERIODS]
)
def test_spruce_lateral_water_and_ditched(lateral):
    params = _common_params()
    params.update(
        species="Picea abies",
        peat=False,
        soil_moisture=Sweden.SoilMoistureEnum.MOIST,
        vegetation=Sweden.FieldLayer.HIGH_HERB_WITHOUT_SHRUBS,
        ground_layer=Sweden.BottomLayer.FRESH_MOSS,
        lateral_water=lateral,
        ditched=True,
    )
    sis = Hagglund_Lundmark_1979_SIS(**params)
    assert isinstance(sis, SiteIndexValue)
    assert 0 < float(sis) < 50


@pytest.mark.parametrize(
    "vegetation",
    [
        Sweden.FieldLayer.HIGH_HERB_WITHOUT_SHRUBS,
        Sweden.FieldLayer.NO_FIELD_LAYER,
        Sweden.FieldLayer.LOW_HERB_WITHOUT_SHRUBS,
    ],
)
def test_spruce_moist_vegetation_branches(vegetation):
    params = _common_params()
    params.update(
        species="Picea abies",
        peat=False,
        soil_moisture=Sweden.SoilMoistureEnum.MOIST,
        vegetation=vegetation,
        ground_layer=Sweden.BottomLayer.FRESH_MOSS,
        lateral_water=Sweden.SoilWater.SHORTER_PERIODS,
        ditched=True,
    )
    sis = Hagglund_Lundmark_1979_SIS(**params)
    assert isinstance(sis, SiteIndexValue)
    assert 0 < float(sis) < 50


def test_spruce_gotland_reduction():
    base = _common_params()
    base.update(species="Picea abies", peat=False)
    normal = Hagglund_Lundmark_1979_SIS(**base)
    base["gotland"] = True
    gotland = Hagglund_Lundmark_1979_SIS(**base)
    assert gotland < normal


@pytest.mark.parametrize(
    "vegetation",
    [
        Sweden.FieldLayer.BILBERRY,
        Sweden.FieldLayer.LINGONBERRY,
        Sweden.FieldLayer.POOR_SHRUB,
    ],
)
def test_pine_mesic_high_vegetation_variants(vegetation):
    params = _common_params()
    params.update(
        species="Pinus sylvestris",
        peat=False,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        vegetation=vegetation,
        ground_layer=Sweden.BottomLayer.FRESH_MOSS,
        soil_depth=Sweden.SoilDepth.DEEP,
        lateral_water=Sweden.SoilWater.LONGER_PERIODS,
    )
    sis = Hagglund_Lundmark_1979_SIS(**params)
    assert isinstance(sis, SiteIndexValue)
    assert 0 < float(sis) < 50


def test_pine_mesic_shallow_ground_layer():
    params = _common_params()
    params.update(
        species="Pinus sylvestris",
        peat=False,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        vegetation=Sweden.FieldLayer.SEDGE_HIGH,
        ground_layer=Sweden.BottomLayer.LICHEN_TYPE,
        soil_depth=Sweden.SoilDepth.DEEP,
        lateral_water=Sweden.SoilWater.LONGER_PERIODS,
        altitude=400.0,
        incline_percent=15.0,
    )
    sis = Hagglund_Lundmark_1979_SIS(**params)
    assert isinstance(sis, SiteIndexValue)
    assert 0 < float(sis) < 50


def test_pine_wet_longer_periods():
    params = _common_params()
    params.update(
        species="Pinus sylvestris",
        peat=False,
        soil_moisture=Sweden.SoilMoistureEnum.WET,
        ground_layer=Sweden.BottomLayer.SWAMP_MOSS,
        vegetation=Sweden.FieldLayer.NO_FIELD_LAYER,
        lateral_water=Sweden.SoilWater.LONGER_PERIODS,
    )
    sis = Hagglund_Lundmark_1979_SIS(**params)
    assert isinstance(sis, SiteIndexValue)
    assert 0 < float(sis) < 50


def test_pine_gotland_reduction():
    base = _common_params()
    base.update(species="Pinus sylvestris", peat=False)
    normal = Hagglund_Lundmark_1979_SIS(**base)
    base["gotland"] = True
    gotland = Hagglund_Lundmark_1979_SIS(**base)
    assert gotland < normal
