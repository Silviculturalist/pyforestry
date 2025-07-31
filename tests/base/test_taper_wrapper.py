import numpy as np
import pytest

from pyforestry.base.taper.taper import Taper
from pyforestry.base.timber import Timber


class DummyModel:
    def __init__(self):
        self.diam_calls = []
        self.height_calls = []

    def get_diameter_at_height(self, h):
        self.diam_calls.append(h)
        return h * 2

    def get_height_at_diameter(self, d):
        self.height_calls.append(d)
        return d / 2


@pytest.fixture
def timber():
    return Timber("pine", 10, 20, stump_height_m=0.5)


def test_get_diameter_at_height_bounds(timber):
    taper = Taper(timber, DummyModel())
    assert taper.get_diameter_at_height(-1) == 0.0
    assert taper.get_diameter_at_height(25) == 0.0


def test_get_diameter_at_height_none(monkeypatch, timber):
    model = DummyModel()
    taper = Taper(timber, model)
    monkeypatch.setattr(model, "get_diameter_at_height", lambda h: None)
    assert taper.get_diameter_at_height(5) == 0.0


def test_get_diameter_vectorised(timber):
    taper = Taper(timber, DummyModel())
    arr = np.array([-1, 0, 10, 25], dtype=float)
    res = taper.get_diameter_vectorised(arr)
    # Heights are adjusted by the stump height (0.5 m) before calling the model
    assert np.allclose(res, [0.0, 1.0, 21.0, 0.0])


def test_get_height_at_diameter(timber):
    model = DummyModel()
    taper = Taper(timber, model)
    result = taper.get_height_at_diameter(10)
    assert result == pytest.approx(10 / 2 - 0.5)
    assert model.height_calls == [10]


def test_get_height_at_diameter_none(monkeypatch, timber):
    model = DummyModel()
    taper = Taper(timber, model)
    monkeypatch.setattr(model, "get_height_at_diameter", lambda d: None)
    assert taper.get_height_at_diameter(10) == 0.0


def test_volume_section(monkeypatch, timber):
    model = DummyModel()
    taper = Taper(timber, model)
    called = {}

    def fake_integrate(h1, h2, instance):
        called["args"] = (h1, h2, instance)
        return 42.0

    monkeypatch.setattr(
        "pyforestry.base.timber.TimberVolumeIntegrator.integrate_volume",
        fake_integrate,
    )
    assert taper.volume_section(2.0, 5.0) == 42.0
    assert called["args"] == (2.0, 5.0, taper)


def test_volume_section_invalid_range(monkeypatch, timber):
    model = DummyModel()
    taper = Taper(timber, model)
    called = []

    def fake_integrate(h1, h2, instance):
        called.append(True)
        return 99.0

    monkeypatch.setattr(
        "pyforestry.base.timber.TimberVolumeIntegrator.integrate_volume",
        fake_integrate,
    )
    assert taper.volume_section(5.0, 5.0) == 0.0
    assert not called
