import math

import pytest

from pyforestry.base.helpers.tree_species import TreeSpecies, parse_tree_species
from pyforestry.sweden.mortality import _common as common
from pyforestry.sweden.mortality.types import (
    MortalitySiteConditions as MortalitySiteState,
)
from pyforestry.sweden.mortality.types import (
    MortalityStandConditions as MortalityStandState,
)
from pyforestry.sweden.mortality.types import (
    MortalityTreeRecord as MortalityTreeState,
)
from pyforestry.sweden.site.enums import Sweden


def test_probability_helpers_cover_core_branches() -> None:
    assert common.clamp_probability(-1.0) == 0.0
    assert common.clamp_probability(2.0) == 1.0
    assert common.combined_probability(0.2, 0.3) == pytest.approx(0.44)
    assert common.logistic(10.0) == pytest.approx(0.9999546021312976)
    assert common.logistic(-10.0) == pytest.approx(0.0000453978687024)


def test_scale_probability_from_5_years_validates_and_warns() -> None:
    assert common.scale_probability_from_5_years(0.3, 5.0) == pytest.approx(0.3)
    assert common.scale_probability_from_5_years(0.0, 4.0) == 0.0
    assert common.scale_probability_from_5_years(1.0, 4.0) == 1.0
    with pytest.raises(ValueError):
        common.scale_probability_from_5_years(0.3, 0.0)
    with pytest.warns(UserWarning):
        scaled = common.scale_probability_from_5_years(0.3, 0.5)
    assert 0.0 < scaled < 0.3


def test_site_and_region_code_resolvers() -> None:
    enum_site = MortalitySiteState(
        latitude_deg=60.0,
        altitude_m=200.0,
        site_index_m=24.0,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        field_layer=Sweden.FieldLayer.BILBERRY,
    )
    code_site = MortalitySiteState(
        latitude_deg=60.0,
        altitude_m=200.0,
        site_index_m=24.0,
        soil_moisture=4,
        vegetation_type_code=7,
    )
    empty_site = MortalitySiteState(
        latitude_deg=60.0,
        altitude_m=200.0,
        site_index_m=24.0,
        soil_moisture=2,
    )

    assert common.resolve_soil_moisture_code(enum_site) == 2
    assert common.resolve_soil_moisture_code(code_site) == 4
    assert common.resolve_vegetation_code(code_site) == 7
    assert common.resolve_vegetation_code(enum_site) == int(Sweden.FieldLayer.BILBERRY.value.code)
    assert common.resolve_vegetation_code(empty_site) == 0
    assert common.normalize_part_of_sweden("Northern") == "north"
    assert common.normalize_part_of_sweden("central") == "middle"
    assert common.normalize_part_of_sweden("south") == "south"
    with pytest.warns(UserWarning):
        assert common.normalize_part_of_sweden("invalid-region") == "middle"


def test_species_parsing_and_grouping_helpers() -> None:
    pine = parse_tree_species("pinus sylvestris")
    spruce = parse_tree_species("picea abies")
    birch = parse_tree_species("betula pendula")
    aspen = parse_tree_species("populus tremula")
    oak = parse_tree_species("quercus robur")
    beech = parse_tree_species("fagus sylvatica")
    southern = parse_tree_species("ulmus glabra")
    other = parse_tree_species("alnus glutinosa")

    assert common.parse_species(pine) == pine
    assert common.parse_species("pinus sylvestris") == pine
    assert common.species_key("pinus sylvestris") == "pinus sylvestris"
    assert common.species_group(pine) == "pine"
    assert common.species_group(spruce) == "spruce"
    assert common.species_group(birch) == "birch"
    assert common.species_group(aspen) == "aspen"
    assert common.species_group(oak) == "oak"
    assert common.species_group(beech) == "beech"
    assert common.species_group(southern) == "southern_broadleaf"
    assert common.species_group(other) == "other_broadleaf"
    assert common.calibration_group(other) == "other"


def test_tree_metrics_helpers_validate_inputs() -> None:
    tree = MortalityTreeState(species=TreeSpecies.Sweden.pinus_sylvestris, diameter_cm=20.0)
    assert common.stems_per_tree(tree, 2.0) == 2.0
    assert common.tree_basal_area_cm2(tree) == pytest.approx(math.pi * 10.0 * 10.0)

    tree_with_ba = MortalityTreeState(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        diameter_cm=20.0,
        basal_area_cm2=50.0,
    )
    assert common.tree_basal_area_cm2(tree_with_ba) == 50.0

    with pytest.raises(ValueError):
        common.stems_per_tree(
            MortalityTreeState(
                species=TreeSpecies.Sweden.pinus_sylvestris,
                diameter_cm=20.0,
            ),
            0.0,
        )
    with pytest.raises(ValueError):
        common.tree_basal_area_cm2(
            MortalityTreeState(
                species=TreeSpecies.Sweden.pinus_sylvestris,
                diameter_cm=20.0,
                basal_area_cm2=0.0,
            )
        )
    with pytest.raises(ValueError):
        common.tree_basal_area_cm2(
            MortalityTreeState(species=TreeSpecies.Sweden.pinus_sylvestris, diameter_cm=0.0)
        )


def test_species_basal_area_and_mortality_fraction_aggregation() -> None:
    trees = [
        MortalityTreeState(
            species=TreeSpecies.Sweden.pinus_sylvestris,
            diameter_cm=20.0,
            stems_per_tree=100.0,
            age_total_years=50.0,
        ),
        MortalityTreeState(
            species=TreeSpecies.Sweden.picea_abies,
            diameter_cm=18.0,
            stems_per_tree=120.0,
            age_total_years=70.0,
        ),
    ]
    stand_with_species_map = MortalityStandState(
        plot_area_m2=300.0,
        species_basal_area_m2_ha={
            "pine": 12.0,
            "picea abies": 9.0,
            "not-a-species": 3.0,
        },
    )
    by_group_from_map = common.species_basal_area_m2_ha_by_group(
        trees=trees,
        stand_conditions=stand_with_species_map,
        default_stems_per_tree=1.0,
    )
    assert by_group_from_map["pine"] == pytest.approx(12.0)
    assert by_group_from_map["spruce"] == pytest.approx(9.0)
    assert by_group_from_map["other_broadleaf"] == pytest.approx(3.0)

    stand_no_species_map = MortalityStandState(plot_area_m2=300.0)
    by_group_from_trees = common.species_basal_area_m2_ha_by_group(
        trees=trees,
        stand_conditions=stand_no_species_map,
        default_stems_per_tree=1.0,
    )
    assert by_group_from_trees["pine"] > 0.0
    assert by_group_from_trees["spruce"] > 0.0

    with pytest.raises(ValueError):
        common.species_mortality_fraction_from_tree_probabilities(
            trees=trees,
            tree_probabilities=[0.1],
        )

    species_fractions = common.species_mortality_fraction_from_tree_probabilities(
        trees=trees,
        tree_probabilities=[0.2, 0.4],
        default_stems_per_tree=1.0,
        use_calibration_groups=False,
    )
    calibration_fractions = common.species_mortality_fraction_from_tree_probabilities(
        trees=trees,
        tree_probabilities=[0.2, 0.4],
        default_stems_per_tree=1.0,
        use_calibration_groups=True,
    )
    assert species_fractions["pinus sylvestris"] == pytest.approx(0.2)
    assert calibration_fractions["pine"] == pytest.approx(0.2)
    assert calibration_fractions["spruce"] == pytest.approx(0.4)


def test_mean_tree_age_resolution_paths() -> None:
    trees_with_age = [
        MortalityTreeState(
            species=TreeSpecies.Sweden.pinus_sylvestris,
            diameter_cm=20.0,
            age_total_years=40.0,
        ),
        MortalityTreeState(
            species=TreeSpecies.Sweden.picea_abies,
            diameter_cm=18.0,
            age_total_years=60.0,
        ),
    ]
    trees_without_age = [
        MortalityTreeState(species=TreeSpecies.Sweden.pinus_sylvestris, diameter_cm=20.0),
    ]

    assert common.mean_tree_age_years(trees_with_age, 80.0) == pytest.approx(50.0)
    assert common.mean_tree_age_years(trees_without_age, 80.0) == pytest.approx(80.0)
    with pytest.raises(ValueError):
        common.mean_tree_age_years(trees_without_age, None)
