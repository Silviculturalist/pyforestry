import importlib

EXPECTED = {"Timber", "TimberVolumeIntegrator"}


def test_all_exports():
    mod = importlib.import_module("pyforestry.base.timber")
    assert set(mod.__all__) == EXPECTED
    for name in EXPECTED:
        assert hasattr(mod, name)
