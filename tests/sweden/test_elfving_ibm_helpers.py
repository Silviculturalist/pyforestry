from pyforestry.sweden.models.elfving_ibm import _veg_code
from pyforestry.sweden.site.enums import Sweden


def test_veg_code():
    assert _veg_code(5) == 5
    assert _veg_code(Sweden.FieldLayer.LOW_HERB_WITH_SHRUBS_BLUEBERRY) == 5
