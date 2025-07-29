import pytest

from pyforestry.sweden.timber import SweTimber
from pyforestry.sweden.volume.naslund_1947 import NaslundFormFactor, NaslundVolume


def make_tree(species, region="southern", **kwargs):
    params = dict(
        diameter_cm=25,
        height_m=20,
        over_bark=True,
        crown_base_height_m=10,
        double_bark_mm=5,
    )
    params.update(kwargs)
    return SweTimber(species=species, region=region, **params)


# --- Volume methods ---------------------------------------------------------
@pytest.mark.parametrize(
    "method,species,region",
    [
        (NaslundVolume._southern_pine_volume, "pinus sylvestris", "southern"),
        (NaslundVolume._southern_spruce_volume, "picea abies", "southern"),
        (NaslundVolume._southern_birch_volume, "betula", "southern"),
        (NaslundVolume._northern_pine_volume, "pinus sylvestris", "northern"),
        (NaslundVolume._northern_spruce_volume, "picea abies", "northern"),
        (NaslundVolume._northern_birch_volume, "betula", "northern"),
    ],
)
def test_volume_methods_positive_and_increasing(method, species, region):
    small = make_tree(species, region=region, diameter_cm=20)
    large = make_tree(species, region=region, diameter_cm=25)
    v_small = method(small)
    v_large = method(large)
    assert v_small > 0
    assert v_small < v_large


# --- Form factor methods ----------------------------------------------------
@pytest.mark.parametrize(
    "method,args",
    [
        (NaslundFormFactor._southern_pine_form_factor, (20, 25, 5, 10)),
        (NaslundFormFactor._southern_spruce_form_factor, (20, 25, 10)),
        (NaslundFormFactor._southern_birch_form_factor, (20, 25, 5)),
        (NaslundFormFactor._northern_pine_form_factor, (20, 25, 5, 10)),
        (NaslundFormFactor._northern_spruce_form_factor, (20, 25, 10)),
        (NaslundFormFactor._northern_birch_form_factor, (20, 25, 5, 10)),
    ],
)
def test_form_factor_methods_relationship(method, args):
    over = method(*args, True)
    under = method(*args, False)
    if method is NaslundFormFactor._northern_pine_form_factor:
        assert over < 0 < under < 1
    else:
        assert 0 < over < 1
        assert 0 < under < 1
        assert over > under


# --- Error paths ------------------------------------------------------------
def test_volume_calculate_unsupported_species(monkeypatch):
    tree = make_tree("betula")
    tree.species = "unknown"
    monkeypatch.setattr(tree, "validate", lambda: None)
    with pytest.raises(NotImplementedError):
        NaslundVolume.calculate(tree)


def test_volume_calculate_unsupported_region(monkeypatch):
    tree = make_tree("betula")
    tree.region = "central"
    monkeypatch.setattr(tree, "validate", lambda: None)
    with pytest.raises(NotImplementedError):
        NaslundVolume.calculate(tree)


def test_form_factor_invalid_species():
    with pytest.raises(ValueError):
        NaslundFormFactor.calculate(
            species="invalid",
            height_m=20,
            diameter_cm=25,
        )


def test_form_factor_invalid_region():
    with pytest.raises(ValueError):
        NaslundFormFactor.calculate(
            species="picea abies",
            height_m=20,
            diameter_cm=25,
            region="central",
        )
