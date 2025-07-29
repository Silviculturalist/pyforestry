import pytest

from pyforestry.sweden.geo import RetrieveGeoCode
from pyforestry.sweden.site import Sweden, SwedishSite


@pytest.fixture(autouse=True)
def stub_geo(monkeypatch):
    monkeypatch.setattr(RetrieveGeoCode, "getCountyCode", lambda lon, lat: Sweden.County.GOTLAND)
    monkeypatch.setattr(RetrieveGeoCode, "getClimateCode", lambda lon, lat: Sweden.ClimateZone.M1)
    monkeypatch.setattr(RetrieveGeoCode, "getDistanceToCoast", lambda lon, lat: 10.0)
    monkeypatch.setattr(
        "pyforestry.sweden.site.swedish_site.eriksson_1986_humidity",
        lambda longitude, latitude, epsg=4326: 80.0,
    )
    monkeypatch.setattr(SwedishSite, "compute_attributes", SwedishSite.__post_init__)
    monkeypatch.setattr(SwedishSite, "__abstractmethods__", frozenset())


def test_minimal_inputs():
    site = SwedishSite(latitude=60.0, longitude=18.0)
    assert site.county == Sweden.County.GOTLAND
    assert site.climate_zone == Sweden.ClimateZone.M1
    assert site.humidity == 80.0
    assert site.distance_to_coast == 10.0
    assert site.temperature_sum_odin1983 is None
    assert site.sis_pine_100 is None
    assert site.sis_spruce_100 is None
    assert site.sis_birch_50 is None


def test_temperature_sum_with_altitude():
    site = SwedishSite(latitude=60.0, longitude=18.0, altitude=200.0)
    expected = 4835 - (57.6 * 60.0) - (0.9 * 200.0)
    assert site.temperature_sum_odin1983 == pytest.approx(expected)
    assert site.sis_pine_100 is None
    assert site.sis_spruce_100 is None


def test_full_inputs_compute_sis():
    site = SwedishSite(
        latitude=61.0,
        longitude=18.0,
        altitude=100.0,
        field_layer=Sweden.FieldLayer.BILBERRY,
        bottom_layer=Sweden.BottomLayer.FRESH_MOSS,
        soil_texture=Sweden.SoilTextureTill.SANDY,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        soil_depth=Sweden.SoilDepth.DEEP,
        soil_water=Sweden.SoilWater.SELDOM_NEVER,
        aspect=0.0,
        incline_percent=5.0,
        ditched=False,
    )
    assert site.temperature_sum_odin1983 is not None
    assert site.sis_pine_100 is not None
    assert site.sis_spruce_100 is not None
    assert site.sis_birch_50 is not None
    assert site.n_of_limes_norrlandicus is True
