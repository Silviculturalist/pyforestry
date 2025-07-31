import pytest

from pyforestry.sweden.geo.geo import RetrieveGeoCode


def test_distance_and_codes():
    dist = RetrieveGeoCode.getDistanceToCoast(15, 60)
    assert dist == pytest.approx(296.072, abs=0.01)

    assert RetrieveGeoCode.getClimateCode(15, 60).name == "M3"
    assert RetrieveGeoCode.getCountyCode(15, 60).name == "OREBRO"

    assert RetrieveGeoCode.getClimateCode(12, 57) is None
    assert RetrieveGeoCode.getCountyCode(12, 57) is None
