import pytest

from pyforestry.sweden.biomass import Marklund_1988, PeterssonStahl2006
from pyforestry.sweden.timber import SweTimber


def test_marklund_1988_full_dict():
    pine = SweTimber(
        species="pinus sylvestris",
        diameter_cm=25,
        height_m=18,
        crown_base_height_m=9,
    )
    res = Marklund_1988(pine)
    assert isinstance(res, dict)
    assert set(res.keys()) == {
        "stem",
        "stem_wood",
        "stem_bark",
        "living_branches",
        "needles",
        "dead_branches",
        "stump_root_system",
        "stump",
    }
    assert res["stem"] == pytest.approx(169.7327, rel=1e-4)
    assert res["stump"] == pytest.approx(28.7951, rel=1e-4)


def test_marklund_1988_component_matches_dict():
    pine = SweTimber(
        species="pinus sylvestris",
        diameter_cm=25,
        height_m=18,
        crown_base_height_m=9,
    )
    full = Marklund_1988(pine)
    stem = Marklund_1988(pine, component="stem")
    assert stem == pytest.approx(full["stem"])


def test_marklund_1988_spruce_stem_only():
    val = Marklund_1988(
        species="picea abies",
        component="stem",
        diameter_cm=20,
    )
    assert isinstance(val, float)
    assert val == pytest.approx(99.42837, rel=1e-5)


def test_petersson_stahl_known_examples():
    birch = PeterssonStahl2006.below_ground_biomass("birch", 5, diameter_cm=30)
    pine = PeterssonStahl2006.below_ground_biomass(
        "pine", 5, diameter_cm=25, age_at_breast_height=40
    )
    spruce = PeterssonStahl2006.below_ground_biomass("spruce", 2, diameter_cm=20)
    assert birch == pytest.approx(120.2875, rel=1e-4)
    assert pine == pytest.approx(60.65037, rel=1e-4)
    assert spruce == pytest.approx(47.35046, rel=1e-4)
