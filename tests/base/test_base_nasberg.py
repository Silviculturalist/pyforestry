from math import pi

import pytest

from pyforestry.base.pricelist import create_pricelist_from_data
from pyforestry.base.timber import Timber
from pyforestry.base.timber_bucking.nasberg_1985 import Nasberg_1985_BranchBound

PRICE_DATA = {
    "Common": {
        "PulpLogDiameterRange": [5, 70],
        "TopDiameter": 5,
        "HarvestResiduePrice": 10,
        "FuelwoodLogPrice": 20,
        "HighStumpHeight": 0,
        "PulpwoodLengthRange": [3.0, 3.2],
        "SawlogLengthRange": [3.1, 3.3],
        "PulpwoodPrices": {"pine": 200},
    },
    "pine": {
        "VolumeType": "m3to",
        "DiameterPrices": {10: [50, 60, 70], 12: [55, 65, 75]},
        "LengthCorrectionsPercent": {10: {31: 1}, 12: {31: 2}},
        "MaxHeight": {"Butt": 50, "Middle": 60, "Top": 70},
    },
}


def _expected_value(diam, length_dm, part_index):
    base = PRICE_DATA["pine"]["DiameterPrices"][diam][part_index]
    corr = PRICE_DATA["pine"]["LengthCorrectionsPercent"][diam][31]
    r = (diam / 100) * 0.5
    vf = pi * r * r * (length_dm / 10)
    return (base + corr) * 100.0 * vf


def test_build_value_table_shape_and_values():
    pricelist = create_pricelist_from_data(PRICE_DATA, species_to_load="pine")
    timber = Timber(species="pine", diameter_cm=12, height_m=10)
    nb = Nasberg_1985_BranchBound(timber, pricelist)

    table = nb._build_value_table()
    assert table.shape == (
        nb._maxDiameterTimberLog + 1,
        len(nb._moduler),
        4,
    )
    idx = nb._mod_ix[31]
    expected = _expected_value(12, 31, 0)
    assert table[12, idx, 1] == pytest.approx(expected)
