import importlib

import pytest

import pyforestry


def test_top_level_lazy_export_includes_norway():
    assert "norway" in pyforestry.__all__
    norway_mod = pyforestry.norway
    assert norway_mod.__name__ == "pyforestry.norway"


def test_norway_subpackage_exports():
    norway = importlib.import_module("pyforestry.norway")
    assert set(norway.__all__) == {
        "adapters",
        "bark",
        "volume",
        "siteindex",
        "taper",
        "growth",
        "simulation",
    }

    bark = importlib.import_module("pyforestry.norway.bark")
    assert "hansen_2023_norway_spruce_norway_bark_thickness" in bark.__all__

    siteindex = importlib.import_module("pyforestry.norway.siteindex")
    assert "Sharma2011" in siteindex.__all__

    taper = importlib.import_module("pyforestry.norway.taper")
    assert taper.__all__ == ["Hansen2023"]

    growth = importlib.import_module("pyforestry.norway.growth")
    assert "maleki_2022_stand_volume" in growth.__all__

    models = importlib.import_module("pyforestry.norway.adapters")
    assert set(models.__all__) == {
        "Allen2020Model",
        "Allen2020Config",
        "Allen2020GrowthModel",
        "KuehnePineModel",
        "KuehnePineAdapterConfig",
        "KuehnePineGrowthModel",
        "Bollandsas2008",
        "Bollandsas2008AdapterConfig",
        "Bollandsas2008GrowthModel",
        "Maleki2022ModelNorway",
        "Maleki2022Config",
        "Maleki2022GrowthModel",
    }


def test_norway_has_no_top_level_compatibility_shim():
    """``pyforestry.norway.bollandsas`` was a re-export of the adapter, nothing else.

    ARCHITECTURE.md states that no facade delegation stubs remain; this asserts it
    for the one that outlived the claim. The model is reachable as
    ``pyforestry.norway.adapters.bollandsas_2008``.
    """
    with pytest.raises(ImportError):
        importlib.import_module("pyforestry.norway.bollandsas")


def test_norway_lazy_getattr_loads_subpackages_and_rejects_unknowns():
    norway = importlib.import_module("pyforestry.norway")
    for name in norway.__all__:
        if name in norway.__dict__:
            delattr(norway, name)
        module = getattr(norway, name)
        assert module.__name__ == f"pyforestry.norway.{name}"
    unknown = "unknown_subpackage"
    with pytest.raises(AttributeError):
        getattr(norway, unknown)
