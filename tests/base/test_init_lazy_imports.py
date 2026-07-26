import pytest

import pyforestry
from pyforestry.base import helpers


def test_top_level_lazy_imports():
    if "sweden" in pyforestry.__dict__:
        del pyforestry.__dict__["sweden"]
    sweden_mod = pyforestry.sweden
    assert sweden_mod.__name__ == "pyforestry.sweden"
    assert pyforestry.sweden is sweden_mod

    with pytest.raises(AttributeError):
        _ = pyforestry.not_a_module


def test_helpers_simulation_exports():
    growth_model = helpers.GrowthModel
    assert growth_model.__name__ == "GrowthModel"
    assert helpers.GrowthModel is growth_model

    with pytest.raises(AttributeError):
        _ = helpers.not_a_helper
