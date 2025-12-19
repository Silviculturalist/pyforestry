import pytest

from pyforestry.sweden.geo.humidity.eriksson_1986 import eriksson_1986_humidity


@pytest.mark.filterwarnings(
    "ignore:Conversion of an array with ndim > 0 to a scalar is deprecated.*:DeprecationWarning"
)
def test_humidity_basic():
    assert eriksson_1986_humidity(15, 60) == 75.0

    # Valid SWEREF99TM coordinates
    assert eriksson_1986_humidity(500000, 6651411, epsg=3006) == 75.0

    with pytest.raises(ValueError):
        eriksson_1986_humidity(1_200_000, 60, epsg=3006)
