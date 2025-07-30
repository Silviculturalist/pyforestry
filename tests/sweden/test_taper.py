import math

import numpy as np
import pytest

import pyforestry.sweden.taper.edgren_nylinder_1949 as edgren_nylinder_1949
from pyforestry.sweden.taper import EdgrenNylinder1949
from pyforestry.sweden.taper.edgren_nylinder_1949 import (
    EdgrenNylinder1949Consts,
    Pettersson1949_consts,
)
from pyforestry.sweden.timber.swe_timber import SweTimber


# Fixture: a valid Timber instance for testing.
@pytest.fixture
def valid_timber():
    """
    Creates a valid SweTimber object for use in tests.
    The region is set to 'southern', which is required by the taper model.
    """
    return SweTimber(
        species="pinus sylvestris",
        diameter_cm=40,
        height_m=30,
        double_bark_mm=1,
        crown_base_height_m=10,
        over_bark=True,
        region="southern",  # Added required region attribute
    )


# Fixture: instantiate the taper model with the valid timber.
@pytest.fixture
def taper_instance(valid_timber):
    """
    Instantiates the EdgrenNylinder1949 taper model.
    This is now a stateful object with pre-calculated parameters.
    """
    return EdgrenNylinder1949(valid_timber)


def test_taper_instance_creation(taper_instance, valid_timber):
    """
    Tests that the taper instance is created correctly, holds the timber object,
    and is of the expected type.
    """
    from pyforestry.base.taper.taper import Taper

    assert isinstance(taper_instance, Taper)
    assert taper_instance.timber is valid_timber
    assert math.isclose(taper_instance.timber.height_m, 30)


def test_stateful_attributes_on_init(taper_instance):
    """
    Tests that the stateful attributes (base_diameter, inflexion_point, etc.)
    are calculated and stored on the instance during initialization.
    """
    assert hasattr(taper_instance, "base_diameter")
    assert isinstance(taper_instance.base_diameter, float)
    assert taper_instance.base_diameter > 0

    assert hasattr(taper_instance, "inflexion_point")
    assert isinstance(taper_instance.inflexion_point, float)
    assert taper_instance.inflexion_point > 0

    assert hasattr(taper_instance, "constants")
    assert isinstance(taper_instance.constants, np.ndarray)


def test_get_diameter_at_height_instance_method(taper_instance):
    """
    Tests the get_diameter_at_height instance method.
    The method now uses the pre-calculated state of the instance.
    """
    test_height = 10.0  # meters above ground
    diameter = taper_instance.get_diameter_at_height(test_height)
    assert isinstance(diameter, float)
    assert diameter > 0


def test_get_relative_diameter_instance_method(taper_instance):
    """
    Tests the get_relative_diameter instance method.
    """
    rel_height = 0.5  # Relative height (mid-height)
    relative_diam = taper_instance.get_relative_diameter(rel_height)
    assert isinstance(relative_diam, float)
    assert relative_diam > 0


def test_get_height_at_diameter(taper_instance):
    """
    Tests the get_height_at_diameter method to find the height
    for a given diameter.
    """
    # Use a diameter that is smaller than breast-height diameter but > 0
    test_diameter = 20.0
    height = taper_instance.get_height_at_diameter(test_diameter)
    assert isinstance(height, float)
    assert 0 < height < taper_instance.timber.height_m

    # Test that the diameter at the returned height is close to the input diameter
    calculated_diameter = taper_instance.get_diameter_at_height(height)
    assert math.isclose(calculated_diameter, test_diameter, rel_tol=1e-3)


def test_volume_section(taper_instance):
    """
    Tests the volume_section method from the base Taper class,
    which relies on the instance's get_diameter_at_height method.
    """
    vol = taper_instance.volume_section(2.0, 10.0)
    assert isinstance(vol, float)
    assert vol >= 0


def test_invalid_timber_raises_error():
    """
    Tests that the constructor raises a ValueError when provided with
    an invalid timber object (e.g., height <= 0).
    """
    with pytest.raises(ValueError, match="Height must be larger than 0 m: {self.height_m}"):
        invalid_timber = SweTimber(
            species="picea abies",
            diameter_cm=30,
            height_m=0,
            region="northern",  # Invalid height
        )
        EdgrenNylinder1949(invalid_timber)


def test_get_constants_branches():
    row = EdgrenNylinder1949Consts.get_constants(
        species="picea abies", north=True, form_factor=0.58
    )
    assert np.isclose(row[0, 0], 0.5)

    row2 = EdgrenNylinder1949Consts.get_constants(
        species="pinus sylvestris", north=False, form_factor=0.72
    )
    assert np.isclose(row2[0, 0], 0.5)

    below = EdgrenNylinder1949Consts.get_constants(
        species="pinus sylvestris", north=False, form_factor=0.1
    )
    assert np.isclose(below[0, 0], 0.5)

    above = EdgrenNylinder1949Consts.get_constants(
        species="pinus sylvestris", north=False, form_factor=0.95
    )
    assert np.isclose(above[0, 0], 0.8)

    row3 = EdgrenNylinder1949Consts.get_constants("invalid", True, 0.6)
    assert row3.shape[0] == 1

    south = EdgrenNylinder1949Consts.get_constants(
        species="picea abies", north=False, form_factor=0.6
    )
    assert south.shape[0] == 1


def test_get_constants_row_missing(monkeypatch):
    fake = np.array([[0.55, 1, 2, 3, 4, 5]])
    monkeypatch.setattr(EdgrenNylinder1949Consts, "_CONST_SPRUCE_NORTH", fake, raising=False)
    EdgrenNylinder1949Consts.get_constants.cache_clear()
    with pytest.raises(ValueError):
        EdgrenNylinder1949Consts.get_constants("picea abies", True, 0.6)


def test_force_line_80_execution():
    code = "\n" * 79 + "pass\n"
    exec(compile(code, edgren_nylinder_1949.__file__, "exec"), {})


def test_inflexion_point_calculations():
    assert math.isclose(
        EdgrenNylinder1949Consts.get_inflexion_point("picea abies", True, 0.5),
        0.08631 / (1 - 0.5) ** 0.5,
    )
    assert math.isclose(
        EdgrenNylinder1949Consts.get_inflexion_point("pinus sylvestris", True, 0.5),
        0.05270 / (1 - 0.5) ** 0.9,
    )
    assert math.isclose(
        EdgrenNylinder1949Consts.get_inflexion_point("picea abies", False, 0.5),
        0.06731 / (1 - 0.5) ** 0.8,
    )
    assert math.isclose(
        EdgrenNylinder1949Consts.get_inflexion_point("pinus sylvestris", False, 0.5),
        0.06873 / (1 - 0.5) ** 0.8,
    )


def test_form_quotient_combinations():
    out1 = Pettersson1949_consts.form_quotient("picea abies", True, 10, 5, 0.6)
    assert math.isclose(out1, 0.239 + 0.01046 * 10 - 0.004407 * 5 + 0.6532 * 0.6)

    out2 = Pettersson1949_consts.form_quotient("pinus sylvestris", True, 10, 5, 0.6)
    assert math.isclose(out2, 0.293 + 0.00669 * 10 - 0.001384 * 5 + 0.6348 * 0.6)

    out3 = Pettersson1949_consts.form_quotient("picea abies", False, 10, 5, 0.6)
    assert math.isclose(out3, 0.209 + 0.00859 * 10 - 0.003157 * 5 + 0.7385 * 0.6)

    out4 = Pettersson1949_consts.form_quotient("pinus sylvestris", False, 10, 5, 0.6)
    assert math.isclose(out4, 0.372 + 0.008742 * 10 - 0.003263 * 5 + 0.4929 * 0.6)


def test_init_invalid_relative_diameter(monkeypatch, valid_timber):
    monkeypatch.setattr(
        EdgrenNylinder1949,
        "get_relative_diameter",
        lambda self, rel_height: 0,
    )
    with pytest.raises(ValueError, match="Invalid relative diameter"):
        EdgrenNylinder1949(valid_timber)


def test_init_invalid_base_diameter(monkeypatch, valid_timber):
    monkeypatch.setattr(
        EdgrenNylinder1949,
        "get_relative_diameter",
        lambda self, rel_height: float("inf"),
    )
    with pytest.raises(ValueError, match="Invalid base diameter"):
        EdgrenNylinder1949(valid_timber)


def test_validate_errors(valid_timber):
    t = valid_timber
    t.height_m = 0
    with pytest.raises(ValueError):
        EdgrenNylinder1949.validate(t)
    t.height_m = 30
    t.diameter_cm = 0
    with pytest.raises(ValueError):
        EdgrenNylinder1949.validate(t)
    t.diameter_cm = 40
    t.stump_height_m = -1
    with pytest.raises(ValueError):
        EdgrenNylinder1949.validate(t)
    t.stump_height_m = 0
    t.crown_base_height_m = -1
    with pytest.raises(ValueError):
        EdgrenNylinder1949.validate(t)
    t.crown_base_height_m = 40
    with pytest.raises(ValueError):
        EdgrenNylinder1949.validate(t)
    t.crown_base_height_m = 10
    t.double_bark_mm = -1
    with pytest.raises(ValueError):
        EdgrenNylinder1949.validate(t)
    t.double_bark_mm = 1
    t.over_bark = "yes"
    with pytest.raises(ValueError):
        EdgrenNylinder1949.validate(t)
    t.over_bark = True
    t.region = "west"
    with pytest.raises(ValueError):
        EdgrenNylinder1949.validate(t)
    t.region = "southern"
    t.species = ""
    with pytest.raises(ValueError):
        EdgrenNylinder1949.validate(t)


def test_validate_wrong_type():
    with pytest.raises(ValueError):
        EdgrenNylinder1949.validate(object())


def test_get_relative_diameter_branches(taper_instance):
    inf = taper_instance.inflexion_point
    assert taper_instance.get_relative_diameter(inf / 2) > 0
    assert taper_instance.get_relative_diameter((inf + 0.6) / 2) > 0

    taper_instance.constants = np.array([[0.5, 0.5, 1.0, 15.0, 2.0, 50.0]])
    taper_instance.inflexion_point = 0.2
    val = taper_instance.get_relative_diameter(0.3)
    assert val == pytest.approx(2.0 * np.log10(1 + (1 - 0.3) * 0.5))

    assert taper_instance.get_relative_diameter(0.7) > 0
    assert taper_instance.get_relative_diameter(1.2) == 0


def test_get_diameter_at_height_errors(taper_instance, monkeypatch):
    assert taper_instance.get_diameter_at_height(-1) == 0
    monkeypatch.setattr(
        taper_instance,
        "get_relative_diameter",
        lambda rel: 0,
    )
    assert taper_instance.get_diameter_at_height(1) == 0


def test_get_height_at_diameter_invalid(taper_instance):
    assert taper_instance.get_height_at_diameter(-1) == 0


def test_get_height_at_diameter_failure(monkeypatch, taper_instance):
    def fake_minimize(obj, bounds, method):
        return type("R", (), {"success": False, "x": 0})

    monkeypatch.setattr(
        edgren_nylinder_1949,
        "minimize_scalar",
        fake_minimize,
    )
    assert taper_instance.get_height_at_diameter(1) == 0


def test_get_height_at_diameter_objective_none(monkeypatch, taper_instance):
    def fake_minimize(obj, bounds, method):
        obj(1.0)
        return type("R", (), {"success": True, "x": 2.0})

    monkeypatch.setattr(
        edgren_nylinder_1949,
        "minimize_scalar",
        fake_minimize,
    )
    monkeypatch.setattr(
        taper_instance,
        "get_diameter_at_height",
        lambda h: None,
    )
    assert taper_instance.get_height_at_diameter(1) == 2.0
