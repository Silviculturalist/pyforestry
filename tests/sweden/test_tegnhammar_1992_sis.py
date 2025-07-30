import pytest

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


def test_ditched_message_and_effect(capsys):
    params = dict(
        latitude=60.0,
        longitude=18.0,
        altitude=100.0,
        vegetation=Sweden.FieldLayer.BILBERRY,
        ground_layer=Sweden.BottomLayer.FRESH_MOSS,
        aspect_main=0,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        soil_depth=Sweden.SoilDepth.DEEP,
        soil_texture=Sweden.SoilTextureTill.SANDY,
        peat_humification=Sweden.PeatHumification.NONE,
    )

    si_ditch = tegnhammar_1992_adjusted_spruce_si_by_stand_variables(
        **params,
        ditched=True,
    )
    out, _ = capsys.readouterr()
    assert "Ditched only defined for peat or moist soils" in out

    si_no_ditch = tegnhammar_1992_adjusted_spruce_si_by_stand_variables(
        **params,
        ditched=False,
    )

    assert float(si_ditch) == float(si_no_ditch)


def test_peat_humification_levels(monkeypatch):
    """Peat humification flags should influence the site index."""
    from pyforestry.sweden.geo.geo import RetrieveGeoCode

    monkeypatch.setattr(RetrieveGeoCode, "getDistanceToCoast", lambda self, lon, lat: 0)

    params = dict(
        latitude=58.0,
        longitude=18.0,
        altitude=100.0,
        vegetation=Sweden.FieldLayer.BILBERRY,
        ground_layer=Sweden.BottomLayer.FRESH_MOSS,
        aspect_main=0,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        soil_depth=Sweden.SoilDepth.DEEP,
        soil_texture=Sweden.SoilTextureTill.PEAT,
        humidity=80.0,
        lateral_water=Sweden.SoilWater.SELDOM_NEVER,
    )

    base = float(
        tegnhammar_1992_adjusted_spruce_si_by_stand_variables(
            peat_humification=Sweden.PeatHumification.NONE,
            **params,
        )
    )
    low = float(
        tegnhammar_1992_adjusted_spruce_si_by_stand_variables(
            peat_humification=Sweden.PeatHumification.LOW,
            **params,
        )
    )
    medium = float(
        tegnhammar_1992_adjusted_spruce_si_by_stand_variables(
            peat_humification=Sweden.PeatHumification.MEDIUM,
            **params,
        )
    )
    high = float(
        tegnhammar_1992_adjusted_spruce_si_by_stand_variables(
            peat_humification=Sweden.PeatHumification.HIGH,
            **params,
        )
    )

    assert base - low == pytest.approx(22.450707 / 100)
    assert base - medium == pytest.approx(10.735284 / 100)
    assert base - high == pytest.approx(2.872332 / 100)


def test_adjusted_si_formula():
    """Validate the helper function used for age adjustment."""
    from pyforestry.sweden.siteindex.sis.tegnhammar_1992 import (
        tegnhammar_1992_adjusted_si_spruce,
    )

    sih = 20.0
    dominant_age = 35.0
    latitude = 60.0
    expected = ((sih * 10) + (3.89 - 0.0498 * latitude) * (dominant_age - 15)) / 10

    assert tegnhammar_1992_adjusted_si_spruce(sih, dominant_age, latitude) == pytest.approx(
        expected
    )
