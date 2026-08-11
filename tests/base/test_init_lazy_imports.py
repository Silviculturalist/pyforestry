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


def test_helpers_redirects_simulation_names_to_their_real_home():
    with pytest.raises(AttributeError, match="pyforestry.base.simulation"):
        _ = helpers.GrowthModel

    with pytest.raises(AttributeError, match="has no attribute"):
        _ = helpers.not_a_helper

    # The data contract itself is unaffected.
    assert helpers.Stand.__name__ == "Stand"
