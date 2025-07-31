import math

import geopandas as gpd
import pytest
from shapely.geometry import Point

from pyforestry.sweden.geo import (
    Moren_Perttu_radiation_1994,
    RetrieveGeoCode,
    eriksson_1986_humidity,
)
from pyforestry.sweden.site import Sweden


@pytest.fixture
def mock_gpd(monkeypatch):
    coast = gpd.GeoDataFrame(geometry=[Point(0, 0)], crs="EPSG:4326")
    climate = gpd.GeoDataFrame(
        {"KLIMZON_": [1]}, geometry=[Point(0, 0).buffer(1)], crs="EPSG:4326"
    )
    county = gpd.GeoDataFrame({"DLANSKOD": [1]}, geometry=[Point(0, 0).buffer(1)], crs="EPSG:4326")
    humidity = gpd.GeoDataFrame(
        {"humiditet": [75]}, geometry=[Point(0, 0).buffer(1)], crs="EPSG:4326"
    )

    def fake_read_file(path):
        path = str(path)
        if "coast" in path:
            return coast
        if "klimat" in path:
            return climate
        if "dlanskod" in path:
            return county
        if "humidity" in path:
            return humidity
        raise FileNotFoundError(path)

    def fake_sjoin(left, right, how, predicate):
        return left.assign(humiditet=[75])

    monkeypatch.setattr(gpd, "read_file", fake_read_file)
    monkeypatch.setattr(gpd, "sjoin", fake_sjoin)


def test_retrieve_geo(monkeypatch, mock_gpd):
    assert RetrieveGeoCode.getDistanceToCoast(0, 0) == 0
    assert RetrieveGeoCode.getClimateCode(0, 0) == Sweden.ClimateZone.M1
    assert RetrieveGeoCode.getCountyCode(0, 0) == Sweden.County.NORRBOTTENS_LAPPMARK

    empty = gpd.GeoDataFrame({"KLIMZON_": []}, geometry=[], crs="EPSG:4326")
    monkeypatch.setattr(gpd, "read_file", lambda path: empty)
    assert RetrieveGeoCode.getClimateCode(0, 0) is None
    assert RetrieveGeoCode.getCountyCode(0, 0) is None


def test_eriksson_humidity(monkeypatch, mock_gpd):
    assert eriksson_1986_humidity(0, 0) == 75
    with pytest.raises(ValueError):
        eriksson_1986_humidity(1_200_000, 60, epsg=3006)

    monkeypatch.setattr(gpd, "sjoin", lambda *a, **k: a[0])
    with pytest.raises(ValueError):
        eriksson_1986_humidity(0, 0)


def test_gorczynski_and_sums(monkeypatch):
    calc = Moren_Perttu_radiation_1994(
        latitude=60, altitude=100, july_avg_temp=20, jan_avg_temp=-10
    )
    expected = 1.7 * (20 - (-10)) / math.sin(math.radians(60)) - 20.4
    assert calc.get_gorczynski_continentality_index() == pytest.approx(expected)

    calc_bad_lat = Moren_Perttu_radiation_1994(
        latitude=91, altitude=0, july_avg_temp=10, jan_avg_temp=0
    )
    with pytest.raises(ValueError):
        calc_bad_lat.get_gorczynski_continentality_index()

    calc_no_temp = Moren_Perttu_radiation_1994(latitude=60, altitude=0)
    with pytest.raises(ValueError):
        calc_no_temp.get_gorczynski_continentality_index()

    calc = Moren_Perttu_radiation_1994(latitude=60, altitude=100)
    with pytest.raises(ValueError):
        calc.calculate_temperature_sum_1000m(99)
    with pytest.raises(ValueError):
        calc.calculate_growing_season_duration_1000m(99)
    with pytest.raises(ValueError):
        calc.calculate_temperature_sum_1500m(99)
    with pytest.raises(ValueError):
        calc.calculate_growing_season_duration_1500m(99)

    assert calc.calculate_temperature_sum_1000m(5) == pytest.approx(1216.38)
    assert calc.calculate_growing_season_duration_1000m(5) == pytest.approx(181.8)
    assert calc.calculate_temperature_sum_1500m(5) == pytest.approx(
        3635.3
        - 12.18 * 60
        - 0.444 * (60**2)
        + 0.04041 * 60 * 100
        - 3.343 * 100
        - 0.000040 * (100**2)
    )


def test_corrected_sum_branches(monkeypatch):
    calc = Moren_Perttu_radiation_1994(latitude=60, altitude=0)
    monkeypatch.setattr(calc, "calculate_temperature_sum_1000m", lambda t: 0)
    monkeypatch.setattr(calc, "calculate_temperature_sum_1500m", lambda t: 0)

    for val, expected in [
        (10, -100),
        (15, -50),
        (20, 0),
        (30, 50),
        (40, 100),
    ]:
        monkeypatch.setattr(calc, "get_gorczynski_continentality_index", lambda v=val: v)
        assert calc.get_corrected_temperature_sum(5, for_1500m_model=True) == expected


def test_ratio_functions():
    assert Moren_Perttu_radiation_1994.get_ratio_global_to_extraterrestrial_radiation_clear_sky(
        120, "North"
    ) == pytest.approx(0.79164)
    assert Moren_Perttu_radiation_1994.get_ratio_global_to_extraterrestrial_radiation_clear_sky(
        366, "South"
    ) == pytest.approx(2.528 + -0.010294 * 366 + 0.137e-4 * (366**2))
    with pytest.raises(ValueError):
        Moren_Perttu_radiation_1994.get_ratio_global_to_extraterrestrial_radiation_clear_sky(
            1, "Mars"
        )
    with pytest.raises(ValueError):
        Moren_Perttu_radiation_1994.get_ratio_global_to_extraterrestrial_radiation_clear_sky(
            400, "North"
        )

    assert Moren_Perttu_radiation_1994.get_ratio_global_to_extraterrestrial_radiation_average_sky(
        180, "South"
    ) == pytest.approx(0.246 + 0.243e-2 * 180 + -0.658e-5 * 180**2)
    with pytest.raises(ValueError):
        Moren_Perttu_radiation_1994.get_ratio_global_to_extraterrestrial_radiation_average_sky(
            1, "Mars"
        )

    calc = Moren_Perttu_radiation_1994(latitude=56, altitude=10)
    assert calc.calculate_global_radiation_sum_growing_season(5) == pytest.approx(
        7.2774 + -0.0782 * 56 + -0.00072 * 10
    )
    with pytest.raises(ValueError):
        calc.calculate_global_radiation_sum_growing_season(99)
