import pytest

from pyforestry.base.helpers import Tree
from pyforestry.simulation.valuation.removals import (
    CohortRemoval,
    StandRemovalLedger,
    TreeRemoval,
    _merge_metadata,
    _normalise_species,
)


def make_tree(**kwargs):
    params = {
        "species": "Picea abies",
        "diameter_cm": 25.0,
        "height_m": 20.0,
    }
    params.update(kwargs)
    return Tree(**params)


def test_defaults_to_tree_weight_when_available():
    tree = make_tree(weight_n=2.5)
    removal = TreeRemoval(cohort_id="cohort", species="Picea abies", tree=tree)
    assert removal.weight == pytest.approx(2.5)


def test_defaults_to_one_when_tree_weight_missing():
    tree = make_tree(weight_n=None)
    removal = TreeRemoval(cohort_id="cohort", species="Picea abies", tree=tree)
    assert removal.weight == pytest.approx(1.0)


def test_zero_weight_raises_value_error():
    tree = make_tree(weight_n=0)
    with pytest.raises(ValueError, match="Removal weights must be positive"):
        TreeRemoval(cohort_id="cohort", species="Picea abies", tree=tree)


def test_missing_cohort_identifier_raises():
    tree = make_tree()
    with pytest.raises(ValueError, match="cohort identifier"):
        TreeRemoval(cohort_id="", species="Picea abies", tree=tree)


def test_tree_removal_requires_tree_instance():
    with pytest.raises(TypeError, match="TreeRemoval expects a Tree"):
        TreeRemoval(cohort_id="cohort", species="Picea abies", tree=object())


def test_missing_diameter_or_height_raise_errors():
    tree_no_diameter = make_tree(diameter_cm=None)
    removal_diameter = TreeRemoval(
        cohort_id="cohort",
        species="Picea abies",
        tree=tree_no_diameter,
    )
    with pytest.raises(ValueError, match="diameter measurements"):
        _ = removal_diameter.diameter_cm

    tree_no_height = make_tree(height_m=None)
    removal_height = TreeRemoval(cohort_id="cohort", species="Picea abies", tree=tree_no_height)
    with pytest.raises(ValueError, match="height measurements"):
        _ = removal_height.height_m


def test_stump_height_prefers_metadata_then_tree_attribute():
    tree = make_tree()
    removal_metadata = TreeRemoval(
        cohort_id="cohort",
        species="Picea abies",
        tree=tree,
        metadata={"stump_height_m": 0.6},
    )
    assert removal_metadata.stump_height_m == pytest.approx(0.6)

    tree.stump_height_m = 0.4
    removal_tree_value = TreeRemoval(cohort_id="cohort", species="Picea abies", tree=tree)
    assert removal_tree_value.stump_height_m == pytest.approx(0.4)


def test_to_timber_copies_optional_metadata():
    tree = make_tree()
    removal = TreeRemoval(
        cohort_id="cohort",
        species="Picea abies",
        tree=tree,
        metadata={"double_bark_mm": 10, "extra": "ignored"},
    )
    timber = removal.to_timber()
    assert timber.double_bark_mm == 10


def test_cohort_removal_records_tree_and_metadata_merge():
    tree = make_tree(weight_n=1.5)
    cohort = CohortRemoval(identifier="c1", species="Picea abies", metadata={"base": 1})
    removal = cohort.record_tree(tree, metadata={"extra": 2})
    assert removal.metadata["base"] == 1
    assert removal.metadata["extra"] == 2
    assert cohort.tree_count == 1
    assert cohort.total_weight == pytest.approx(1.5)


def test_stand_ledger_add_and_retrieve_cohorts():
    tree = make_tree()
    ledger = StandRemovalLedger(stand_id="stand")
    ledger.add_cohort("c1", species="Picea abies", metadata={"base": 1})
    assert ledger.metadata["stand_id"] == "stand"
    again = ledger.add_cohort("c1", species="Picea abies", metadata={"extra": 2})
    assert again.metadata["extra"] == 2
    removal = ledger.record_tree("c1", tree, metadata={"more": 3})
    assert removal.metadata["more"] == 3
    assert ledger.tree_count == 1
    assert ledger.total_weight == pytest.approx(1.0)


def test_stand_ledger_requires_species_for_new_cohort():
    tree = make_tree(species=None)
    ledger = StandRemovalLedger()
    with pytest.raises(ValueError, match="Species must be provided"):
        ledger.record_tree("new", tree)


def test_stand_ledger_rejects_species_mismatch():
    tree = make_tree()
    ledger = StandRemovalLedger()
    ledger.add_cohort("c1", species="Picea abies")
    with pytest.raises(ValueError, match="does not match cohort species"):
        ledger.record_tree("c1", tree, species="Pinus sylvestris")


def test_stand_ledger_extend_merges_cohorts():
    tree_one = make_tree(weight_n=2.0)
    tree_two = make_tree(weight_n=3.0)
    source_cohort = CohortRemoval(identifier="c1", species="Picea abies")
    source_cohort.record_tree(tree_one)
    ledger = StandRemovalLedger()
    ledger.extend([source_cohort])
    assert ledger.tree_count == 1

    other_cohort = CohortRemoval(identifier="c1", species="Picea abies")
    other_cohort.record_tree(tree_two)
    ledger.extend([other_cohort])
    assert ledger.tree_count == 2
    assert ledger.total_weight == pytest.approx(5.0)


def test_merge_metadata_and_normalise_species_helpers():
    combined = _merge_metadata(None, {"a": 1}, {"b": 2})
    assert combined == {"a": 1, "b": 2}

    with pytest.raises(TypeError):
        _normalise_species(123)
