from pyforestry.base.helpers.tree_species import TreeSpecies, parse_tree_species


def test_norway_species_extension_registers_region():
    import pyforestry.norway  # noqa: F401

    assert TreeSpecies.Norway.picea_abies.full_name == "picea abies"
    assert TreeSpecies.Norway.pinus_sylvestris.full_name == "pinus sylvestris"
    assert TreeSpecies.Norway.betula_pendula.full_name == "betula pendula"
    assert TreeSpecies.Norway.populus_tremula.full_name == "populus tremula"


def test_norway_genus_groups_and_parse():
    import pyforestry.norway  # noqa: F401

    betula_group = TreeSpecies.Norway.betula
    names = {species.full_name for species in betula_group}
    assert names == {"betula pendula", "betula pubescens"}
    assert parse_tree_species("Picea abies") == TreeSpecies.Norway.picea_abies
