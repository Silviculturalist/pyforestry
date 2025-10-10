from collections import Counter

import pytest
from pyproj import CRS

from pyforestry.base.helpers.plot import CircularPlot
from pyforestry.base.helpers.primitives.age import Age, AgeMeasurement
from pyforestry.base.helpers.primitives.cartesian_position import Position
from pyforestry.base.helpers.primitives.diameter_cm import Diameter_cm
from pyforestry.base.helpers.tree import Tree
from pyforestry.base.helpers.tree_species import BETULA_PENDULA, PINUS_SYLVESTRIS
from pyforestry.simulation.checkpointing import (
    restore_plot,
    restore_stand,
    restore_tree,
    serialize_tree,
    snapshot_plot,
    snapshot_stand,
)


def test_serialize_restore_tree_round_trip():
    tree = Tree(
        position=Position(10.0, 20.0, 3.0, crs=CRS.from_epsg(3006)),
        species=PINUS_SYLVESTRIS,
        age=Age.TOTAL(80),
        diameter_cm=Diameter_cm(25.3, over_bark=False, measurement_height_m=0.65),
        height_m=22.4,
        weight_n=3.0,
        uid=1234,
    )

    payload = serialize_tree(tree)
    restored = restore_tree(payload)

    assert restored.uid == tree.uid
    assert restored.weight_n == pytest.approx(tree.weight_n)
    assert restored.height_m == pytest.approx(tree.height_m)
    assert isinstance(restored.diameter_cm, Diameter_cm)
    assert float(restored.diameter_cm) == pytest.approx(float(tree.diameter_cm))
    assert restored.diameter_cm.over_bark is False
    assert restored.diameter_cm.measurement_height_m == pytest.approx(0.65)
    assert restored.species == tree.species
    assert isinstance(restored.position, Position)
    assert restored.position.X == pytest.approx(tree.position.X)
    assert restored.position.Y == pytest.approx(tree.position.Y)
    assert restored.position.Z == pytest.approx(tree.position.Z)
    assert restored.position.crs.to_epsg() == tree.position.crs.to_epsg()
    assert restored.age == tree.age


def test_snapshot_restore_stand_mixed_species():
    plot_a = CircularPlot(
        id="a",
        radius_m=10.0,
        trees=[
            Tree(
                position=Position(1.0, 2.0),
                species=PINUS_SYLVESTRIS,
                age=Age.DBH,
                diameter_cm=Diameter_cm(18.0),
                height_m=15.2,
                weight_n=2.0,
                uid="a1",
            ),
            Tree(
                position=Position(2.5, 4.0),
                species=BETULA_PENDULA,
                age=40.0,
                diameter_cm=20.0,
                height_m=18.1,
                weight_n=1.0,
                uid="a2",
            ),
        ],
    )

    plot_b = CircularPlot(
        id="b",
        radius_m=12.0,
        trees=[
            Tree(
                position=Position(5.0, 1.0, 0.5),
                species=BETULA_PENDULA,
                age=Age.TOTAL(55),
                diameter_cm=Diameter_cm(30.0, measurement_height_m=1.5),
                height_m=None,
                weight_n=0.75,
                uid="b1",
            ),
            Tree(
                position=None,
                species=None,
                age=None,
                diameter_cm=None,
                height_m=None,
                weight_n=1.0,
                uid="b2",
            ),
        ],
    )

    stand_snapshots = snapshot_stand(type("MockStand", (), {"plots": [plot_a, plot_b]})())
    assert len(stand_snapshots) == 4

    restored = restore_stand(snapshot.to_dict() for snapshot in stand_snapshots)

    original_trees = plot_a.trees + plot_b.trees
    assert [tree.uid for tree in restored] == [tree.uid for tree in original_trees]

    original_species = Counter(
        tree.species.code if tree.species else None for tree in original_trees
    )
    restored_species = Counter(tree.species.code if tree.species else None for tree in restored)
    assert restored_species == original_species

    original_plot_snapshot = snapshot_plot(plot_a)
    restored_plot = restore_plot(original_plot_snapshot)
    assert [tree.uid for tree in restored_plot] == [tree.uid for tree in plot_a.trees]


def test_snapshot_stand_uses_iterator():
    class IterableStand:
        def __init__(self, plots):
            self.plots = plots

        def __iter__(self):
            return iter(self.plots)

    plot = CircularPlot(
        id="iter",
        radius_m=8.0,
        trees=[Tree(uid="iter-tree")],
    )
    snapshots = snapshot_stand(IterableStand([plot]))
    assert len(snapshots) == 1
    assert snapshots[0].to_dict()["uid"] == "iter-tree"


def test_restore_tree_handles_incomplete_metadata():
    base_tree = Tree(
        species=PINUS_SYLVESTRIS,
        age=Age.TOTAL(45),
        diameter_cm=Diameter_cm(21.0),
    )

    payload = serialize_tree(base_tree)

    string_species_tree = Tree(uid="string-species")
    string_species_tree.species = "Pinus sylvestris"
    string_payload = serialize_tree(string_species_tree)
    assert string_payload["species"]["code"] is None
    assert string_payload["species"]["full_name"] == "Pinus sylvestris"

    code_removed = payload | {"species": {"code": None, "full_name": base_tree.species.full_name}}
    restored_from_name = restore_tree(code_removed)
    assert restored_from_name.species == base_tree.species

    invalid_species = payload | {"species": {"code": "NOPE", "full_name": "not real"}}
    restored_invalid_species = restore_tree(invalid_species)
    assert restored_invalid_species.species is None

    missing_measurement = payload | {
        "age": {"kind": "measurement", "value": None, "code": Age.TOTAL.value}
    }
    restored_missing_measurement = restore_tree(missing_measurement)
    assert restored_missing_measurement.age is None

    fallback_measurement = payload | {
        "age": {"kind": "mystery", "value": 12.0, "code": Age.DBH.value}
    }
    restored_fallback_age = restore_tree(fallback_measurement)
    assert isinstance(restored_fallback_age.age, AgeMeasurement)
    assert float(restored_fallback_age.age) == pytest.approx(12.0)
    assert restored_fallback_age.age.code == Age.DBH.value

    bad_numeric_age = payload | {"age": {"kind": "numeric", "value": None, "code": None}}
    restored_bad_numeric_age = restore_tree(bad_numeric_age)
    assert restored_bad_numeric_age.age is None

    non_numeric_value = payload | {"age": {"kind": "weird", "value": "oops", "code": None}}
    restored_non_numeric_age = restore_tree(non_numeric_value)
    assert restored_non_numeric_age.age is None

    missing_diameter_value = payload | {"diameter_cm": {"kind": "numeric", "value": None}}
    restored_missing_diameter = restore_tree(missing_diameter_value)
    assert restored_missing_diameter.diameter_cm is None

    invalid_diameter_value = payload | {"diameter_cm": {"kind": "numeric", "value": "bad"}}
    restored_invalid_diameter = restore_tree(invalid_diameter_value)
    assert restored_invalid_diameter.diameter_cm is None
