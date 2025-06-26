import pytest
from Munin.Timber.SweTimber import SweTimber
from Munin.Taper.sweden.EdgrenNylinder1949 import EdgrenNylinder1949
from Munin.PriceList import create_pricelist_from_data
from Munin.PriceList.Data.Mellanskog_2013 import Mellanskog_2013_price_data
from Munin.TimberBucking.Nasberg_1985 import Nasberg_1985_BranchBound, BuckingConfig

@pytest.fixture
def test_log():
    return SweTimber(species='pinus sylvestris', diameter_cm=18, height_m=25)

@pytest.fixture
def test_pricelist():
    return create_pricelist_from_data(Mellanskog_2013_price_data, species_to_load='pinus sylvestris')

def test_nasberg_1985_branch_bound(test_log, test_pricelist):
    taper_model = EdgrenNylinder1949
    optimizer = Nasberg_1985_BranchBound(test_log, test_pricelist, taper_model)

    result = optimizer.calculate_tree_value(min_diam_dead_wood=99, config=BuckingConfig(save_sections=True))
    print(result)
    result.plot()
    assert result is not None, "Result should not be None"
    assert "total_value" in result, "Expected 'total_value' key in result"
    assert result["total_value"] >= 0, "Total value should be non-negative"
