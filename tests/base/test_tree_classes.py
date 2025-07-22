from pyforestry.base.helpers.primitives.cartesian_position import Position
from pyforestry.base.helpers.tree import Tree
from pyforestry.base.helpers.tree_species import parse_tree_species


def test_single_tree_init_and_repr():
    tree = Tree(
        position=(1.0, 2.0),
        species="picea abies",
        age=5,
        diameter_cm=30.0,
        height_m=20.0,
        uid="T1",
    )
    assert isinstance(tree.position, Position)
    assert tree.species.genus.name == "Picea"
    rep = repr(tree)
    assert "Tree" in rep and "T1" in rep


def test_representation_tree_parsing_and_weight():
    sp = parse_tree_species("pinus sylvestris")
    rep_tree = Tree((3, 4), sp, weight=2.5)
    assert rep_tree.weight == 2.5
    assert rep_tree.position.X == 3
    assert "Tree" in repr(rep_tree)
