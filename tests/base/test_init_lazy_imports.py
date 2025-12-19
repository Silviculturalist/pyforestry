import pytest

import pyforestry
from pyforestry.base import helpers


def test_top_level_lazy_imports():
    sweden_mod = getattr(pyforestry, "sweden")
    assert sweden_mod.__name__ == "pyforestry.sweden"
    assert getattr(pyforestry, "sweden") is sweden_mod

    with pytest.raises(AttributeError):
        getattr(pyforestry, "not_a_module")


def test_helpers_simulation_exports():
    sim_setup = getattr(helpers, "SimulationSetup")
    assert sim_setup.__name__ == "SimulationSetup"
    assert getattr(helpers, "SimulationSetup") is sim_setup

    with pytest.raises(AttributeError):
        getattr(helpers, "not_a_helper")
