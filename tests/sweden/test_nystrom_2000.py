import pytest

from pyforestry.base.helpers.primitives import Age
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.height.nystrom_2000 import (
    _field_layer_flags,
    _resolve_age_total,
    _soil_moisture_flags,
    sapling_height_growth_m,
)
from pyforestry.sweden.site.enums import Sweden


def _base_kwargs():
    return dict(
        height_m=3.2,
        age_bh_years=Age.DBH(8),
        mean_height_m=3.8,
        total_height_sqr_m2_per_ha=14500.0,
        total_height_sqr_std_m2_per_ha=2200.0,
        temperature_sum=1100.0,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        field_layer=Sweden.FieldLayer.BILBERRY,
        damage_index=0.2,
        edge_effect=0.0,
        edge_effect_alt=0.0,
        period_years=5.0,
    )


@pytest.mark.parametrize(
    ("species", "expected"),
    [
        (TreeSpecies.Sweden.pinus_sylvestris, 1.916399983223728),
        (TreeSpecies.Sweden.picea_abies, 1.7830147447069198),
        (TreeSpecies.Sweden.betula_pendula, 1.4426984114481738),
    ],
)
def test_nystrom_2000_species_snapshots(species, expected):
    out = sapling_height_growth_m(**_base_kwargs(), species=species)
    assert out == pytest.approx(expected, rel=1e-10, abs=1e-12)


def test_nystrom_2000_period_scaling():
    base = _base_kwargs()
    growth_5 = sapling_height_growth_m(**base, species=TreeSpecies.Sweden.pinus_sylvestris)
    growth_10 = sapling_height_growth_m(
        **{**base, "period_years": 10.0},
        species=TreeSpecies.Sweden.pinus_sylvestris,
    )
    assert growth_10 == pytest.approx(growth_5 * 2.0, rel=1e-12, abs=1e-12)


def test_nystrom_2000_rejects_non_dbh_age_measurement():
    with pytest.raises(TypeError):
        sapling_height_growth_m(
            **_base_kwargs(),
            species=TreeSpecies.Sweden.pinus_sylvestris,
            age_bh_years=Age.TOTAL(12),
        )


def test_nystrom_2000_rejects_invalid_age_type():
    with pytest.raises(TypeError):
        sapling_height_growth_m(
            **_base_kwargs(),
            species=TreeSpecies.Sweden.pinus_sylvestris,
            age_bh_years="8",
        )


def test_nystrom_2000_helper_flags_and_age_total() -> None:
    assert _field_layer_flags(None) == (0, 0)
    assert _field_layer_flags(Sweden.FieldLayer.HIGH_HERB_WITHOUT_SHRUBS) == (1, 0)
    assert _field_layer_flags(Sweden.FieldLayer.CROWBERRY) == (0, 1)

    assert _soil_moisture_flags(None) == (0, 0)
    assert _soil_moisture_flags(Sweden.SoilMoistureEnum.DRY) == (1, 0)
    assert _soil_moisture_flags(Sweden.SoilMoistureEnum.WET) == (0, 1)

    assert _resolve_age_total(height_m=1.2, age_bh_val=10.0) == pytest.approx(1.2)
    assert _resolve_age_total(height_m=2.0, age_bh_val=-2.0) == pytest.approx(2.3)


def test_nystrom_2000_accepts_numeric_age_and_none_flags() -> None:
    out = sapling_height_growth_m(
        **{
            **_base_kwargs(),
            "age_bh_years": 6,
            "field_layer": None,
            "soil_moisture": None,
            "period_years": 7.5,
        },
        species=TreeSpecies.Sweden.pinus_sylvestris,
    )
    assert out > 0.0
