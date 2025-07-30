import numpy as np
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


def test_marklund_1988_invalid_species():
    """Unknown species should raise ``ValueError``."""
    with pytest.raises(ValueError):
        Marklund_1988(species="invalid")


def test_marklund_1988_invalid_component():
    """Invalid biomass component should raise ``ValueError``."""
    with pytest.raises(ValueError):
        Marklund_1988(species="picea abies", component="invalid", diameter_cm=20)


def test_marklund_1988_timber_component():
    """Passing a ``SweTimber`` instance should work for component calls."""
    pine = SweTimber(
        species="pinus sylvestris",
        diameter_cm=25,
        height_m=18,
        crown_base_height_m=9,
    )
    val = Marklund_1988(pine, component="stem")
    assert isinstance(val, float)
    assert val == pytest.approx(169.7327, rel=1e-4)


def test_petersson_stahl_known_examples():
    birch = PeterssonStahl2006.below_ground_biomass("birch", 5, diameter_cm=30)
    pine = PeterssonStahl2006.below_ground_biomass(
        "pine", 5, diameter_cm=25, age_at_breast_height=40
    )
    spruce = PeterssonStahl2006.below_ground_biomass("spruce", 2, diameter_cm=20)
    assert birch == pytest.approx(120.2875, rel=1e-4)
    assert pine == pytest.approx(60.65037, rel=1e-4)
    assert spruce == pytest.approx(47.35046, rel=1e-4)


def test_petersson_stahl_invalid_species():
    with pytest.raises(ValueError):
        PeterssonStahl2006.below_ground_biomass("invalid", 5, diameter_cm=20)


def test_petersson_stahl_invalid_root_detail():
    with pytest.raises(ValueError):
        PeterssonStahl2006.below_ground_biomass("birch", 3, diameter_cm=20)


def test_petersson_stahl_second_model(monkeypatch):
    def fail_first(*args, **kwargs):
        raise TypeError

    monkeypatch.setattr(PeterssonStahl2006, "pine_root_5mm_1", fail_first)

    result = PeterssonStahl2006.below_ground_biomass(
        "pine", 5, diameter_cm=25, age_at_breast_height=40
    )
    expected = np.exp(PeterssonStahl2006.pine_root_5mm_2(25 * 10, 40)) / 1000
    assert result == pytest.approx(expected)


def test_petersson_stahl_individual_models():
    """Ensure each static biomass function returns expected log values."""
    assert PeterssonStahl2006.birch_root_2mm(200) == pytest.approx(
        6.17080 + 10.01111 * (200 / (200 + 225))
    )

    assert PeterssonStahl2006.pine_root_5mm_3(150, 80, 1) == pytest.approx(
        3.50127 + 10.96210 * (150 / (150 + 113)) + 0.00250 * 80 - 0.37595 * 1
    )

    assert PeterssonStahl2006.pine_root_2mm_1(100) == pytest.approx(
        3.44275 + 11.06537 * (100 / (100 + 113))
    )

    assert PeterssonStahl2006.pine_root_2mm_2(100, 40) == pytest.approx(
        3.62193 + 11.07117 * (100 / (100 + 113)) - 0.05029 * 100 / 40
    )

    assert PeterssonStahl2006.pine_root_2mm_3(100, 50, 0) == pytest.approx(
        3.56553 + 10.96370 * (100 / (100 + 113)) + 0.00236 * 50 - 0.38089 * 0
    )

    assert PeterssonStahl2006.spruce_root_5mm_1(150) == pytest.approx(
        4.52965 + 10.57571 * (150 / (150 + 142))
    )

    assert PeterssonStahl2006.spruce_root_5mm_2(150, 80) == pytest.approx(
        4.60559 + 10.60542 * (150 / (150 + 142)) - 0.02489 * 150 / 80
    )

    assert PeterssonStahl2006.spruce_root_5mm_3(150, 80, 35, 10, 1) == pytest.approx(
        4.98414
        + 9.89245 * (150 / (150 + 142))
        - 0.03411 * 150 / 80
        - 0.00769 * 35
        + 0.00317 * 10
        - 0.23375 * 1
    )

    assert PeterssonStahl2006.spruce_root_2mm_2(120, 70) == pytest.approx(
        4.69287 + 10.45700 * (120 / (120 + 138)) - 0.03057 * 120 / 70
    )

    assert PeterssonStahl2006.spruce_root_2mm_3(120, 40, 20, 8, 1) == pytest.approx(
        5.00171
        + 9.89713 * (120 / (120 + 138))
        - 0.03653 * 40
        - 0.00636 * 20
        + 0.00261 * 8
        - 0.21705 * 1
    )


def test_petersson_stahl_error_handling():
    """Invalid inputs should raise informative errors."""
    with pytest.raises(ValueError, match="Invalid species"):
        PeterssonStahl2006.below_ground_biomass("oak", 2, diameter_cm=30)

    with pytest.raises(ValueError, match="Invalid root_detail"):
        PeterssonStahl2006.below_ground_biomass("birch", 3, diameter_cm=30)

    with pytest.raises(ValueError, match="No suitable function"):
        PeterssonStahl2006.below_ground_biomass(
            "pine",
            5,
            diameter_cm="bad",
            age_at_breast_height="bad",
            age_basal_area_weighted="bad",
            dry_soil="bad",
        )
