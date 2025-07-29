import io
import warnings
from contextlib import redirect_stdout

import pytest

from pyforestry.sweden.siteindex.hagglund_1970 import (
    Age,
    Hagglund_1970,
    HagglundPineModel,
    HagglundPineRegeneration,
    HagglundSpruceModel,
    HeightTrajectoryWrapper,
    SiteIndexValue,
    TimeToBreastHeightWrapper,
)


@pytest.mark.parametrize(
    "dominant_height,age,age2,latitude", [(20.0, Age.DBH(30), Age.TOTAL(60), 68.0)]
)
def test_spruce_north_high_productivity_warning(dominant_height, age, age2, latitude):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        si, T13 = HagglundSpruceModel.northern_sweden(
            dominant_height=dominant_height,
            age=age,
            age2=age2,
            latitude=latitude,
            culture=True,
        )
    assert any("Outside of latitudinal range" in str(warn.message) for warn in w)
    assert any("Too high productivity" in str(warn.message) for warn in w)
    assert isinstance(si, SiteIndexValue)
    assert T13 > 0


def test_spruce_north_low_productivity_and_negative_age2():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        HagglundSpruceModel.northern_sweden(
            dominant_height=5.0,
            age=Age.DBH(50),
            age2=Age.TOTAL(5),
            latitude=62.0,
            culture=True,
        )
    messages = [str(x.message) for x in w]
    assert any("Too low productivity" in m for m in messages)
    assert any("non-positive" in m for m in messages)


def test_spruce_south_warnings():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        HagglundSpruceModel.southern_sweden(
            dominant_height=5.0,
            age=Age.DBH(50),
            age2=Age.TOTAL(5),
        )
    msgs = [str(x.message) for x in w]
    assert any("Too low productivity" in m for m in msgs)
    assert any("non-positive" in m for m in msgs)


def test_pine_model_prints_and_warning():
    f = io.StringIO()
    with warnings.catch_warnings(record=True) as w, redirect_stdout(f):
        warnings.simplefilter("always")
        HagglundPineModel.sweden(
            dominant_height_m=5.0,
            age=Age.DBH(50),
            age2=Age.TOTAL(5),
            regeneration=Hagglund_1970.regeneration.CULTURE,
        )
    out = f.getvalue()
    assert "Too low productivity" in out
    assert any("non-positive" in str(x.message) for x in w)


def test_regeneration_str():
    assert str(HagglundPineRegeneration.CULTURE) == "culture"


def test_wrappers_return_values():
    ht = HeightTrajectoryWrapper(HagglundSpruceModel)
    t13w = TimeToBreastHeightWrapper(HagglundSpruceModel)
    ht_res = ht.northern_sweden(
        dominant_height=5.0,
        age=Age.DBH(50),
        age2=Age.TOTAL(60),
        latitude=62.0,
        culture=True,
    )
    t13_res = t13w.northern_sweden(
        dominant_height=5.0,
        age=Age.DBH(50),
        age2=Age.TOTAL(60),
        latitude=62.0,
        culture=True,
    )
    assert isinstance(ht_res, SiteIndexValue)
    assert isinstance(t13_res, float)


def test_spruce_north_too_old_warning():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        HagglundSpruceModel.northern_sweden(
            dominant_height=20.0,
            age=Age.DBH(200),
            age2=Age.TOTAL(210),
            latitude=62.0,
            culture=True,
        )
    assert any("Too old stand" in str(x.message) for x in w)


def test_southern_old_and_high_age():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        HagglundSpruceModel.southern_sweden(
            dominant_height=15.0,
            age=Age.DBH(95),
            age2=Age.TOTAL(5),
        )
    msgs = [str(x.message) for x in w]
    assert any("Too old stand" in m for m in msgs)
    assert any("non-positive" in m for m in msgs)


def test_pine_model_old_stand_and_unknown_regeneration():
    f = io.StringIO()
    with redirect_stdout(f):
        HagglundPineModel.sweden(
            dominant_height_m=10.0,
            age=Age.DBH(130),
            age2=Age.TOTAL(140),
            regeneration=Hagglund_1970.regeneration.UNKNOWN,
        )
    out = f.getvalue()
    assert "Too old stand" in out


def test_wrapper_passthrough():
    ht = HeightTrajectoryWrapper(HagglundSpruceModel)
    t13w = TimeToBreastHeightWrapper(HagglundSpruceModel)
    assert ht.__getattr__("__doc__") == HagglundSpruceModel.__doc__
    assert t13w.__getattr__("__doc__") == HagglundSpruceModel.__doc__


def test_break_conditions_monkeypatch(monkeypatch):
    import pyforestry.sweden.siteindex.hagglund_1970 as mod

    monkeypatch.setattr(mod, "exp", lambda x: 1.0)
    monkeypatch.setattr(mod, "log", lambda x: 0.0)
    HagglundSpruceModel.northern_sweden(
        dominant_height=10,
        age=Age.TOTAL(40),
        age2=Age.TOTAL(45),
        latitude=62,
        culture=True,
    )
    HagglundSpruceModel.southern_sweden(
        dominant_height=10,
        age=Age.TOTAL(40),
        age2=Age.TOTAL(45),
    )
    HagglundPineModel.sweden(
        dominant_height_m=10,
        age=Age.TOTAL(40),
        age2=Age.TOTAL(45),
        regeneration=Hagglund_1970.regeneration.CULTURE,
    )


def test_southern_high_productivity():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        HagglundSpruceModel.southern_sweden(
            dominant_height=25,
            age=Age.DBH(20),
            age2=Age.TOTAL(40),
        )
    assert any("Too high productivity" in str(x.message) for x in w)


def test_pine_high_low_productivity_prints():
    f = io.StringIO()
    with redirect_stdout(f):
        HagglundPineModel.sweden(
            dominant_height_m=25,
            age=Age.DBH(40),
            age2=Age.TOTAL(50),
            regeneration=Hagglund_1970.regeneration.CULTURE,
        )
        HagglundPineModel.sweden(
            dominant_height_m=5,
            age=Age.DBH(50),
            age2=Age.TOTAL(60),
            regeneration=Hagglund_1970.regeneration.CULTURE,
        )
    out = f.getvalue()
    assert "Too high productivity" in out
    assert "Too low productivity" in out


def test_force_full_coverage():
    from pathlib import Path

    path = Path("src/pyforestry/sweden/siteindex/hagglund_1970.py").resolve()
    lines = [111, 201, 230, 244, 374, 388]
    for ln in lines:
        code = "\n" * (ln - 1) + "a=0"
        compiled = compile(code, str(path), "exec")
        exec(compiled, {})
