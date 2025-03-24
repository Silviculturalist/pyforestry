#import pytest
#from Munin.Timber.SweTimber import SweTimber
#from Munin.Taper.EdgrenNylinder1949 import EdgrenNylinder1949
#from Munin.PriceList import create_pricelist
#from Munin.PriceList.Data.Mellanskog_2013 import Mellanskog_2013_price_data
#from Munin.TimberBucking.Nasberg_1985 import Nasberg_1985_BranchBound
#
#my_pricelist = create_pricelist(Mellanskog_2013_price_data)
#
#my_log = SweTimber(species='pinus sylvestris',diameter_cm=18,height_m=25)
#
#def test_Naslund_1985():
    #result= Nasberg_1985_BranchBound(my_log,my_pricelist,EdgrenNylinder1949).calculate_tree_value(min_diam_dead_wood=99,save_sections=True)
    #assert result is not None