from pyforestry.base.pricelist import Pricelist as BasePricelist
from pyforestry.base.pricelist import create_pricelist_from_data as base_create
from pyforestry.sweden.pricelist import Pricelist, create_pricelist_from_data
from pyforestry.sweden.pricelist.data.mellanskog_2013 import Mellanskog_2013_price_data


def test_pricelist_reexports_and_functionality():
    assert Pricelist is BasePricelist

    pl1 = create_pricelist_from_data(
        Mellanskog_2013_price_data, species_to_load="pinus sylvestris"
    )
    pl2 = base_create(Mellanskog_2013_price_data, species_to_load="pinus sylvestris")

    assert isinstance(pl1, Pricelist)
    assert isinstance(pl2, Pricelist)
    # check one price value to ensure equality
    price1 = pl1.Timber["pinus sylvestris"][20].butt_price
    price2 = pl2.Timber["pinus sylvestris"][20].butt_price
    assert price1 == price2
