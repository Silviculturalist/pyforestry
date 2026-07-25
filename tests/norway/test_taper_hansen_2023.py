import pytest

from pyforestry.base.timber import Timber
from pyforestry.norway.taper import Hansen2023


def test_hansen_taper_basic_behaviour():
    taper = Hansen2023(Timber(species="picea abies", diameter_cm=30.0, height_m=25.0))

    assert taper.get_diameter_at_height(0.0) > 0.0
    assert taper.get_diameter_at_height(30.0) == 0.0
    assert taper.get_diameter_at_height(-1.0) == 0.0

    h_for_small_diameter = taper.get_height_at_diameter(5.0)
    assert h_for_small_diameter is not None
    assert 0.0 <= h_for_small_diameter <= taper.timber.height_m


def test_hansen_taper_api_validation_and_errors():
    with pytest.raises(ValueError):
        Hansen2023(Timber(species="unknown", diameter_cm=30.0, height_m=25.0))
    with pytest.raises(ValueError):
        Hansen2023.validate(Timber(species="picea abies", diameter_cm=0.0, height_m=25.0))

    taper = Hansen2023(Timber(species="pine", diameter_cm=30.0, height_m=25.0))
    with pytest.raises(NotImplementedError):
        taper.get_diameter_at_height(5.0, with_bark=False)
    with pytest.raises(NotImplementedError):
        taper.get_height_at_diameter(5.0, with_bark=False)
    with pytest.raises(ValueError):
        taper.get_diameter_at_height("5")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        taper.get_height_at_diameter(-1.0)


def test_hansen_taper_height_lookup_edge_cases(monkeypatch):
    taper = Hansen2023(Timber(species="birch", diameter_cm=30.0, height_m=25.0))
    assert taper.get_height_at_diameter(0.0) == pytest.approx(25.0)
    assert taper.get_height_at_diameter(100.0) == 0.0

    class _FailedResult:
        success = False
        x = 0.0

    monkeypatch.setattr(
        "pyforestry.norway.taper.hansen_2023.minimize_scalar",
        lambda *a, **k: _FailedResult(),
    )
    assert taper.get_height_at_diameter(5.0) is None
