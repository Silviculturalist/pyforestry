import math

from pyforestry.base.helpers import Tree, TreeSpecies
from pyforestry.sweden.mortality.naslund_1986 import (
    AspenCausalAgent,
    BirchCausalAgent,
    ContortaCausalAgent,
    DamageDegree,
    Naslund1986DamageModel,
    PineCausalAgent,
    SaplingSpeciesGroup,
    SpruceCausalAgent,
)


def test_damage_proportion_pine():
    stems = {
        SaplingSpeciesGroup.PINE: 1000.0,
        SaplingSpeciesGroup.SPRUCE: 0.0,
        SaplingSpeciesGroup.CONTORTA: 0.0,
        SaplingSpeciesGroup.BIRCH: 0.0,
        SaplingSpeciesGroup.ASPEN: 0.0,
        SaplingSpeciesGroup.OTHER_BROADLEAF: 0.0,
        SaplingSpeciesGroup.LARCH: 0.0,
    }
    mean_heights = {sg: (2.0 if sg == SaplingSpeciesGroup.PINE else 0.0) for sg in stems}

    site_index_pine_m = 20.0
    site_index_spruce_m = 22.0
    latitude_deg = 60.0
    altitude_m = 100.0
    climate_index = 50.0 * latitude_deg + altitude_m

    mean_height_pine_larch = 2.0
    prop_pine = 1.0
    stems_pine_larch = 1000.0
    total_stems = 1000.0
    mean_height_leaf = 0.0
    total_mean_height = 2.0

    ln_moose = -0.21 * mean_height_pine_larch + -1.36 * prop_pine + 0.07 * mean_height_leaf + -0.58
    ln_whip = -1.85 * prop_pine + 1.3e-04 * total_stems + 0.11 * total_mean_height + -2.73
    ln_snowblight = (
        -0.21 * mean_height_pine_larch
        + -3.91e-04 * stems_pine_larch
        + 1.55e-03 * climate_index
        + -6.90
    )
    ln_snow = -1.46 * prop_pine + 0.09 * total_mean_height + -2.54
    ln_other = -1.13 * prop_pine + -2.31e-04 * total_stems + -0.07 * site_index_pine_m + 0.71

    total = 0.0
    for ln_damage in [ln_moose, ln_whip, ln_snowblight, ln_snow, ln_other]:
        exp_val = math.exp(ln_damage)
        total += exp_val / (exp_val + 1.0)

    result = Naslund1986DamageModel.damage_proportions(
        stems=stems,
        mean_heights=mean_heights,
        site_index_pine_m=site_index_pine_m,
        site_index_spruce_m=site_index_spruce_m,
        latitude_deg=latitude_deg,
        altitude_m=altitude_m,
    )
    assert math.isclose(result[SaplingSpeciesGroup.PINE], total, rel_tol=1e-9)


def test_risk_of_damage_contorta():
    risks = Naslund1986DamageModel.risk_of_damage(
        species_group=SaplingSpeciesGroup.CONTORTA,
        height_m=2.0,
    )
    assert len(risks) == 3
    assert all(r >= 0.0 for r in risks)


def test_damage_degree_pine_moose_sums_to_one():
    mean_height_pine_larch = 2.0
    prop_pine = 1.0
    stems_pine_larch = 1000.0
    total_stems = 1000.0
    mean_height_leaf = 0.0
    total_mean_height = 2.0
    site_index_pine_m = 20.0
    climate_index = 50.0 * 60.0 + 100.0

    moose_damage_prop = Naslund1986DamageModel.moose_damage_prop_pine(
        mean_height_pine_larch=mean_height_pine_larch,
        prop_pine=prop_pine,
        stems_pine_larch=stems_pine_larch,
        total_stems=total_stems,
        mean_height_leaf=mean_height_leaf,
        total_mean_height=total_mean_height,
        site_index_pine_m=site_index_pine_m,
        climate_index=climate_index,
    )

    degree = Naslund1986DamageModel.damage_degree(
        species_group=SaplingSpeciesGroup.PINE,
        causal_agent=PineCausalAgent.MOOSE.value,
        height_m=2.0,
        moose_damage_prop=moose_damage_prop,
    )
    assert math.isclose(sum(degree), 1.0, rel_tol=1e-9)


def test_damage_proportions_handles_empty_stands() -> None:
    stems = {group: 0.0 for group in SaplingSpeciesGroup}
    mean_heights = {group: 0.0 for group in SaplingSpeciesGroup}
    result = Naslund1986DamageModel.damage_proportions(
        stems=stems,
        mean_heights=mean_heights,
        site_index_pine_m=20.0,
        site_index_spruce_m=22.0,
        latitude_deg=60.0,
        altitude_m=100.0,
    )
    assert all(value == 0.0 for value in result.values())


def test_damage_proportions_from_trees_covers_species_groups() -> None:
    trees = [
        Tree(species=TreeSpecies.Sweden.pinus_sylvestris, height_m=2.0, weight_n=40.0),
        Tree(species=TreeSpecies.Sweden.picea_abies, height_m=1.9, weight_n=35.0),
        Tree(species=TreeSpecies.Sweden.pinus_contorta, height_m=2.2, weight_n=20.0),
        Tree(species=TreeSpecies.Sweden.betula_pendula, height_m=1.8, weight_n=25.0),
        Tree(species=TreeSpecies.Sweden.populus_tremula, height_m=1.7, weight_n=15.0),
    ]
    result = Naslund1986DamageModel.damage_proportions_from_trees(
        trees,
        site_index_pine_m=20.0,
        site_index_spruce_m=22.0,
        latitude_deg=61.0,
        altitude_m=120.0,
        expansion_factor=2.0,
    )
    assert set(result) == {
        SaplingSpeciesGroup.PINE,
        SaplingSpeciesGroup.SPRUCE,
        SaplingSpeciesGroup.CONTORTA,
        SaplingSpeciesGroup.BIRCH,
        SaplingSpeciesGroup.ASPEN,
    }
    assert all(value >= 0.0 for value in result.values())


def test_risk_of_damage_and_damage_degree_cover_all_species() -> None:
    assert (
        Naslund1986DamageModel.risk_of_damage(
            species_group=SaplingSpeciesGroup.PINE,
            height_m=0.0,
        )
        == []
    )

    pine_risk = Naslund1986DamageModel.risk_of_damage(
        species_group=SaplingSpeciesGroup.PINE,
        height_m=2.0,
    )
    spruce_risk = Naslund1986DamageModel.risk_of_damage(
        species_group=SaplingSpeciesGroup.SPRUCE,
        height_m=2.0,
    )
    birch_risk = Naslund1986DamageModel.risk_of_damage(
        species_group=SaplingSpeciesGroup.BIRCH,
        height_m=2.0,
    )
    aspen_risk = Naslund1986DamageModel.risk_of_damage(
        species_group=SaplingSpeciesGroup.ASPEN,
        height_m=2.0,
    )
    contorta_risk = Naslund1986DamageModel.risk_of_damage(
        species_group=SaplingSpeciesGroup.CONTORTA,
        height_m=2.0,
    )
    assert len(pine_risk) == 5
    assert len(spruce_risk) == 3
    assert len(birch_risk) == 2
    assert len(aspen_risk) == 2
    assert len(contorta_risk) == 3

    pine_degree = Naslund1986DamageModel.damage_degree(
        species_group=SaplingSpeciesGroup.PINE,
        causal_agent=PineCausalAgent.WHIP.value,
        height_m=2.0,
        moose_damage_prop=0.2,
    )
    spruce_degree = Naslund1986DamageModel.damage_degree(
        species_group=SaplingSpeciesGroup.SPRUCE,
        causal_agent=SpruceCausalAgent.REMAINDER.value,
        height_m=2.0,
    )
    birch_degree = Naslund1986DamageModel.damage_degree(
        species_group=SaplingSpeciesGroup.BIRCH,
        causal_agent=BirchCausalAgent.REMAINDER.value,
        height_m=2.0,
        moose_damage_prop=0.2,
    )
    aspen_degree = Naslund1986DamageModel.damage_degree(
        species_group=SaplingSpeciesGroup.ASPEN,
        causal_agent=AspenCausalAgent.MOOSE.value,
        height_m=2.0,
    )
    contorta_degree = Naslund1986DamageModel.damage_degree(
        species_group=SaplingSpeciesGroup.CONTORTA,
        causal_agent=ContortaCausalAgent.REMAINDER.value,
        height_m=2.0,
    )
    fallback_degree = Naslund1986DamageModel.damage_degree(
        species_group=SaplingSpeciesGroup.OTHER_BROADLEAF,
        causal_agent=DamageDegree.MINOR.value,
        height_m=2.0,
    )
    for degree in [
        pine_degree,
        spruce_degree,
        birch_degree,
        aspen_degree,
        contorta_degree,
        fallback_degree,
    ]:
        assert math.isclose(sum(degree), 1.0, rel_tol=1e-9)


def test_damage_model_wrapper_methods_return_probabilities() -> None:
    moose_pine = Naslund1986DamageModel.moose_damage_prop_pine(
        mean_height_pine_larch=2.0,
        prop_pine=0.6,
        stems_pine_larch=600.0,
        total_stems=1000.0,
        mean_height_leaf=1.4,
        total_mean_height=1.8,
        site_index_pine_m=20.0,
        climate_index=3100.0,
    )
    moose_birch = Naslund1986DamageModel.moose_damage_prop_birch(
        mean_height_birch=2.0,
        prop_pine=0.5,
        prop_birch=0.3,
        stems_birch=300.0,
    )
    moose_contorta = Naslund1986DamageModel.moose_damage_prop_contorta(
        mean_height_contorta=2.0,
        stems_contorta=200.0,
        latitude_deg=62.0,
    )
    assert 0.0 <= moose_pine <= 1.0
    assert 0.0 <= moose_birch <= 1.0
    assert 0.0 <= moose_contorta <= 1.0

    assert (
        0.0
        <= Naslund1986DamageModel._damage_prop_pine(
            mean_height_pine_larch=2.0,
            prop_pine=0.6,
            stems_pine_larch=600.0,
            total_stems=1000.0,
            mean_height_leaf=1.4,
            total_mean_height=1.8,
            site_index_pine_m=20.0,
            climate_index=3100.0,
            moose_factor=1.0,
            snow_blight_factor=1.0,
            snow_break_factor=1.0,
            whip_factor=1.0,
            other_factor=1.0,
        )
        <= 1.0
    )
    assert (
        0.0
        <= Naslund1986DamageModel._damage_prop_spruce(
            mean_height_spruce=2.0,
            stems_spruce=300.0,
            prop_spruce=0.3,
            sum_height_leaf=250.0,
            mean_height_leaf=1.5,
            climate_index=3100.0,
            site_index_spruce_m=22.0,
            whip_factor=1.0,
            frost_factor=1.0,
            other_factor=1.0,
        )
        <= 1.0
    )
    assert (
        0.0
        <= Naslund1986DamageModel._damage_prop_contorta(
            mean_height_contorta=2.0,
            stems_contorta=200.0,
            latitude_deg=62.0,
            moose_factor=1.0,
            vole_factor=1.0,
            other_factor=1.0,
        )
        <= 1.0
    )
    assert (
        0.0
        <= Naslund1986DamageModel._damage_prop_birch(
            mean_height_birch=2.0,
            prop_pine=0.5,
            prop_birch=0.3,
            stems_birch=300.0,
            moose_factor=1.0,
            other_factor=1.0,
        )
        <= 1.0
    )
    assert (
        0.0
        <= Naslund1986DamageModel._damage_prop_aspen(
            mean_height_aspen=2.0,
            prop_pine=0.5,
            prop_other_leaf=0.2,
            stems_aspen=100.0,
            total_mean_height=1.8,
            moose_factor=1.0,
            other_factor=1.0,
        )
        <= 1.0
    )

    assert math.isclose(
        sum(Naslund1986DamageModel._degree_pine(2.0, PineCausalAgent.MOOSE.value, 0.2)),
        1.0,
        rel_tol=1e-9,
    )
    assert math.isclose(
        sum(Naslund1986DamageModel._degree_spruce(2.0, SpruceCausalAgent.FROST.value)),
        1.0,
        rel_tol=1e-9,
    )
    assert math.isclose(
        sum(Naslund1986DamageModel._degree_birch(2.0, BirchCausalAgent.MOOSE.value, 0.2)),
        1.0,
        rel_tol=1e-9,
    )
    assert math.isclose(
        sum(Naslund1986DamageModel._degree_aspen(2.0, AspenCausalAgent.REMAINDER.value)),
        1.0,
        rel_tol=1e-9,
    )
    assert math.isclose(
        sum(Naslund1986DamageModel._degree_contorta(2.0, ContortaCausalAgent.VOLE.value)),
        1.0,
        rel_tol=1e-9,
    )
