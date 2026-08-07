import math

import pytest

from pyforestry.base.helpers import Age, SiteIndexValue, TreeSpecies
from pyforestry.sweden.ingrowth.wikberg_2004 import (
    IngrowthSpeciesGroup,
    Wikberg2004Ingrowth,
    ingrowth_predict,
)
from pyforestry.sweden.site.enums import Sweden
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970


def _group_map(value: float) -> dict[IngrowthSpeciesGroup, float]:
    return {group: value for group in IngrowthSpeciesGroup}


def _group_int_map(value: int) -> dict[IngrowthSpeciesGroup, int]:
    return {group: value for group in IngrowthSpeciesGroup}


def test_ingrowth_gating_returns_zero():
    result = ingrowth_predict(
        site_index_m=20.0,
        basal_area_m2_ha=15.0,
        qmd_cm=10.0,  # gating threshold
        mean_age_excl_overstorey_years=80.0,
        temperature_sum_dd=800.0,
        latitude_deg=60.0,
        altitude_m=100.0,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        soil_texture=Sweden.SoilTextureTill.SANDY,
        soil_water=Sweden.SoilWater.SELDOM_NEVER,
        bottom_layer=Sweden.BottomLayer.FRESH_MOSS,
        field_layer=Sweden.FieldLayer.BILBERRY,
        gotland=0,
        species_ba_m2_ha=_group_map(0.0),
        species_presence_10cm=_group_int_map(0),
    )

    assert all(val == 0.0 for val in result.number_ingrowth_trees.values())
    assert all(val == 0.0 for val in result.number_small_trees.values())
    assert all(val == 0.0 for val in result.probability_small_trees.values())
    assert result.ingrown_trees == []


def test_ingrowth_deterministic_matches_expected_relation():
    species_ba = _group_map(0.0)
    species_ba[IngrowthSpeciesGroup.SPRUCE] = 15.0
    species_presence = _group_int_map(0)
    species_presence[IngrowthSpeciesGroup.SPRUCE] = 1

    result = ingrowth_predict(
        site_index_m=20.0,
        basal_area_m2_ha=20.0,
        qmd_cm=14.0,
        mean_age_excl_overstorey_years=80.0,
        temperature_sum_dd=900.0,
        latitude_deg=60.0,
        altitude_m=100.0,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        soil_texture=Sweden.SoilTextureTill.SANDY,
        soil_water=Sweden.SoilWater.SELDOM_NEVER,
        bottom_layer=Sweden.BottomLayer.FRESH_MOSS,
        field_layer=Sweden.FieldLayer.BILBERRY,
        gotland=0,
        species_ba_m2_ha=species_ba,
        species_presence_10cm=species_presence,
        ingrowth_species=[IngrowthSpeciesGroup.SPRUCE],
        deterministic=True,
    )

    prob = result.probability_small_trees[IngrowthSpeciesGroup.SPRUCE]
    num_small = result.number_small_trees[IngrowthSpeciesGroup.SPRUCE]
    num_ingrowth = result.number_ingrowth_trees[IngrowthSpeciesGroup.SPRUCE]
    assert math.isclose(num_ingrowth, prob * num_small, rel_tol=1e-9)


def test_resolve_site_index_rejects_wrong_species():
    birch_site_index = SiteIndexValue(
        20.0,
        reference_age=Age.TOTAL(100),
        species={TreeSpecies.Sweden.betula_pendula},
        fn=Hagglund_1970.height_trajectory.pinus_sylvestris.sweden,
    )
    with pytest.raises(ValueError, match="site_index_m\\.species"):
        Wikberg2004Ingrowth._resolve_site_index_m(birch_site_index)


def test_resolve_site_index_rejects_unknown_function_origin():
    pine_site_index = SiteIndexValue(
        20.0,
        reference_age=Age.TOTAL(100),
        species={TreeSpecies.Sweden.pinus_sylvestris},
        fn=lambda *_: None,
    )
    with pytest.raises(ValueError, match="site_index_m\\.fn"):
        Wikberg2004Ingrowth._resolve_site_index_m(pine_site_index)
