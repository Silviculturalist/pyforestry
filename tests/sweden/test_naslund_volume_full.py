import pytest

from pyforestry.sweden.timber.swe_timber import SweTimber
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


@pytest.mark.parametrize(
    "over_bark,with_extra", [(True, True), (True, False), (False, True), (False, False)]
)
def test_volume_branches_pine_southern(over_bark, with_extra):
    tree = make_tree(
        "pinus sylvestris",
        over_bark=over_bark,
        crown_base_height_m=10 if with_extra else None,
        double_bark_mm=5 if with_extra else None,
    )
    assert NaslundVolume._southern_pine_volume(tree) > 0


@pytest.mark.parametrize(
    "over_bark,with_extra", [(True, True), (True, False), (False, True), (False, False)]
)
def test_volume_branches_pine_northern(over_bark, with_extra):
    tree = make_tree(
        "pinus sylvestris",
        region="northern",
        over_bark=over_bark,
        crown_base_height_m=10 if with_extra else None,
        double_bark_mm=5 if with_extra else None,
    )
    assert NaslundVolume._northern_pine_volume(tree) > 0


@pytest.mark.parametrize(
    "over_bark,with_crown", [(True, True), (True, False), (False, True), (False, False)]
)
def test_volume_branches_spruce_southern(over_bark, with_crown):
    tree = make_tree(
        "picea abies",
        over_bark=over_bark,
        crown_base_height_m=10 if with_crown else None,
    )
    assert NaslundVolume._southern_spruce_volume(tree) > 0


@pytest.mark.parametrize(
    "over_bark,with_crown", [(True, True), (True, False), (False, True), (False, False)]
)
def test_volume_branches_spruce_northern(over_bark, with_crown):
    tree = make_tree(
        "picea abies",
        region="northern",
        over_bark=over_bark,
        crown_base_height_m=10 if with_crown else None,
    )
    assert NaslundVolume._northern_spruce_volume(tree) > 0


@pytest.mark.parametrize(
    "over_bark,with_db", [(True, True), (True, False), (False, True), (False, False)]
)
def test_volume_branches_birch_southern(over_bark, with_db):
    tree = make_tree(
        "betula",
        over_bark=over_bark,
        double_bark_mm=5 if with_db else None,
    )
    assert NaslundVolume._southern_birch_volume(tree) > 0


@pytest.mark.parametrize(
    "over_bark,with_extra", [(True, True), (True, False), (False, True), (False, False)]
)
def test_volume_branches_birch_northern(over_bark, with_extra):
    tree = make_tree(
        "betula",
        region="northern",
        over_bark=over_bark,
        crown_base_height_m=10 if with_extra else None,
        double_bark_mm=5 if with_extra else None,
    )
    assert NaslundVolume._northern_birch_volume(tree) > 0


@pytest.mark.parametrize(
    "over_bark,with_extra", [(True, True), (True, False), (False, True), (False, False)]
)
def test_form_factor_branches_pine_southern(over_bark, with_extra):
    result = NaslundFormFactor._southern_pine_form_factor(
        20,
        25,
        5 if with_extra else None,
        10 if with_extra else None,
        over_bark,
    )
    assert isinstance(result, float)


@pytest.mark.parametrize(
    "over_bark,with_extra", [(True, True), (True, False), (False, True), (False, False)]
)
def test_form_factor_branches_pine_northern(over_bark, with_extra):
    result = NaslundFormFactor._northern_pine_form_factor(
        20,
        25,
        5 if with_extra else None,
        10 if with_extra else None,
        over_bark,
    )
    assert isinstance(result, float)


@pytest.mark.parametrize(
    "over_bark,with_crown", [(True, True), (True, False), (False, True), (False, False)]
)
def test_form_factor_branches_spruce_southern(over_bark, with_crown):
    result = NaslundFormFactor._southern_spruce_form_factor(
        20,
        25,
        10 if with_crown else None,
        over_bark,
    )
    assert isinstance(result, float)


@pytest.mark.parametrize(
    "over_bark,with_crown", [(True, True), (True, False), (False, True), (False, False)]
)
def test_form_factor_branches_spruce_northern(over_bark, with_crown):
    result = NaslundFormFactor._northern_spruce_form_factor(
        20,
        25,
        10 if with_crown else None,
        over_bark,
    )
    assert isinstance(result, float)


@pytest.mark.parametrize(
    "over_bark,with_db", [(True, True), (True, False), (False, True), (False, False)]
)
def test_form_factor_branches_birch_southern(over_bark, with_db):
    result = NaslundFormFactor._southern_birch_form_factor(
        20,
        25,
        5 if with_db else None,
        over_bark,
    )
    assert isinstance(result, float)


@pytest.mark.parametrize(
    "over_bark,with_extra", [(True, True), (True, False), (False, True), (False, False)]
)
def test_form_factor_branches_birch_northern(over_bark, with_extra):
    result = NaslundFormFactor._northern_birch_form_factor(
        20,
        25,
        5 if with_extra else None,
        10 if with_extra else None,
        over_bark,
    )
    assert isinstance(result, float)


def test_calculate_not_implemented(monkeypatch):
    tree = make_tree("betula")
    tree.species = "unknown"
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
