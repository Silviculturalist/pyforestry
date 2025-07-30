import pytest

from pyforestry.base.helpers.tree_species import (
    ALNUS_GLUTINOSA,
    ALNUS_INCANA,
    RegionalGenusGroup,
    TreeGenus,
    TreeName,
    TreeSpecies,
    parse_tree_species,
)


def test_individual_species_full_name():
    sp = TreeSpecies.Sweden.picea_abies
    assert sp.full_name == "picea abies"


def test_tree_type():
    sp_conifer = TreeSpecies.Sweden.picea_abies
    sp_deciduous = TreeSpecies.Sweden.quercus_robur
    assert sp_conifer.tree_type == "Coniferous"
    assert sp_deciduous.tree_type == "Deciduous"


def test_regional_genus_group_alnus():
    alnus_group = TreeSpecies.Sweden.alnus
    # Check that the group is a RegionalGenusGroup and includes both species.
    species_names = {sp.full_name for sp in alnus_group}
    expected = {"alnus glutinosa", "alnus incana"}
    assert species_names == expected


def test_unknown_species_access():
    with pytest.raises(AttributeError):
        _ = TreeSpecies.Sweden.non_existent_species


def test_regional_genus_group_membership():
    alnus_group = TreeSpecies.Sweden.alnus
    # Verify that individual species are in the alnus group.
    assert ALNUS_GLUTINOSA in alnus_group
    assert ALNUS_INCANA in alnus_group


def test_parse_tree_species():
    assert parse_tree_species("pInus sylvestris") == TreeSpecies.Sweden.pinus_sylvestris


def test_regional_genus_group_repr():
    genus = TreeGenus(name="Testus", code="TEST")
    sp1 = TreeName(genus=genus, species_name="alpha", code="ALP")
    sp2 = TreeName(genus=genus, species_name="beta", code="BET")
    group = RegionalGenusGroup(genus.name, [sp1, sp2])
    out = repr(group)
    assert out.startswith("RegionalGenusGroup(Testus:")
    assert "alpha" in out and "beta" in out
