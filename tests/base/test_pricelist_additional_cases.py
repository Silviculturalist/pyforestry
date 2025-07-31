import pytest

from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.base.pricelist import (
    LengthCorrections,
    Pricelist,
    PulpPricelist,
    TimberPriceForDiameter,
    TimberPricelist,
    create_pricelist_from_data,
)


def _minimal_price_data():
    return {
        "Common": {
            "PulpLogDiameterRange": [5, 60],
            "TopDiameter": 5,
            "HarvestResiduePrice": 10,
            "FuelwoodLogPrice": 20,
            "HighStumpHeight": 0,
            "PulpwoodLengthRange": [30, 50],
            "SawlogLengthRange": [31, 55],
            "PulpwoodPrices": {"pine": 200},
        },
        "pine": {
            "VolumeType": "m3to",
            "DiameterPrices": {10: [1, 2, 3]},
            "MaxHeight": {"Butt": 5, "Middle": 5, "Top": 5},
        },
    }


def test_timber_price_and_length_corrections():
    tpd = TimberPriceForDiameter(10, 20, 30)
    assert tpd.price_for_log_part(99) == 0

    lc = LengthCorrections({10: {31: 1, 35: 2}})
    assert lc.get_length_correction(10, None, 33) == 1
    assert lc.get_length_correction(10, None, 30) == 0
    assert lc.get_length_correction(20, None, 33) == 0


def test_get_timber_weight_defaults():
    tp = TimberPricelist(10, 20)
    weights = tp.getTimberWeight(tp.LogParts.Butt)
    assert weights.pulpwoodPercentage == 0.0
    assert weights.fuelWoodPercentage == 0.0
    assert weights.logCullPercentage == 0.0


def test_pulp_pricelist_lookup_and_defaults():
    pp = PulpPricelist()
    pp._prices = {
        "pinus sylvestris": 300,
        "pinus": 150,
    }
    assert pp.getPulpwoodPrice("pinus sylvestris") == 300
    assert pp.getPulpwoodPrice(TreeSpecies.Sweden.pinus_sylvestris) == 300

    pp._prices = {"pinus": 123}
    assert pp.getPulpwoodPrice(TreeSpecies.Sweden.pinus_sylvestris) == 123
    assert pp.getPulpwoodPrice("unknown species") == 200
    assert pp.getPulpwoodPrice("pinus") == 200


def test_pricelist_load_from_dict(monkeypatch):
    data = _minimal_price_data()
    pl = Pricelist()
    pl.load_from_dict(data)
    assert "pine" in pl.Timber

    with pytest.raises(KeyError):
        Pricelist().load_from_dict({})

    def boom(*_, **__):
        raise RuntimeError("boom")

    monkeypatch.setattr(Pricelist, "_load_species_specific_data", boom)
    with pytest.raises(ValueError, match="boom"):
        Pricelist().load_from_dict(data)


def test_create_pricelist_from_data_branches():
    data = _minimal_price_data()
    pl = create_pricelist_from_data(data, species_to_load=["pine"])
    assert set(pl.Timber) == {"pine"}

    with pytest.raises(ValueError):
        create_pricelist_from_data({}, species_to_load="pine")

    with pytest.raises(TypeError):
        create_pricelist_from_data(data, species_to_load=123)

    with pytest.raises(ValueError):
        create_pricelist_from_data(data, species_to_load="oak")
