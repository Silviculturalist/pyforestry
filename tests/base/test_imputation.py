"""Tests for tree attribute imputation.

Covers the store on ``Tree``, the generic ``Stand.impute``, the registry, and the
provenance an imputed value must carry. The height numbers asserted here were
pinned from the pre-migration ``Stand.impute_heights`` implementation, so the
migration is provably behaviour-preserving.
"""

import copy
import inspect
import pathlib

import pytest

import pyforestry.base.helpers.tree
from pyforestry.base.competition import MeanHeightRadius, competition_indices
from pyforestry.base.helpers import CircularPlot, Stand, Tree
from pyforestry.base.helpers.primitives import Position
from pyforestry.base.imputation import (
    CallableImputer,
    ImputedValue,
    NaslundHeightImputer,
    available_attributes,
    imputers_for,
    register_imputer,
    resolve_imputer,
)

# Values produced by the pre-migration Stand.impute_heights("naslund") on the
# stand built by _stand() below. The migration must reproduce them exactly.
BASELINE_MISSING = {
    "u1": 13.277534300874601,
    "u2": 19.693318803254574,
    "u3": 24.135516943863426,
}
BASELINE_ALL = {
    "m1": 9.0734999775,
    "m2": 16.7896637212,
    "m3": 22.1076414395,
    "u1": 13.2775343009,
    "u2": 19.6933188033,
    "u3": 24.1355169439,
}


def _stand() -> Stand:
    """Three measured and three unmeasured trees on one 10 m plot."""
    trees = [
        Tree(position=(1.0, 1.0), diameter_cm=10.0, height_m=9.0, uid="m1"),
        Tree(position=(2.0, 2.0), diameter_cm=20.0, height_m=17.0, uid="m2"),
        Tree(position=(3.0, 3.0), diameter_cm=30.0, height_m=22.0, uid="m3"),
        Tree(position=(4.0, 1.0), diameter_cm=15.0, uid="u1"),
        Tree(position=(1.0, 4.0), diameter_cm=25.0, uid="u2"),
        Tree(position=(2.0, 4.0), diameter_cm=35.0, uid="u3"),
    ]
    return Stand(
        plots=[CircularPlot(id=1, position=Position(0.0, 0.0), radius_m=10.0, trees=trees)]
    )


def _by_uid(stand: Stand) -> dict:
    return {str(t.uid): t for t in (t for p in stand.plots for t in p.trees)}


# ---------------------------------------------------------------------------
# Migration equivalence
# ---------------------------------------------------------------------------


def test_impute_reproduces_the_pre_migration_heights():
    """Stand.impute("height_m") matches what impute_heights produced."""
    stand = _stand()
    assert stand.impute("height_m") == 3
    trees = _by_uid(stand)
    for uid, expected in BASELINE_MISSING.items():
        assert trees[uid].value_of("height_m") == pytest.approx(expected, abs=1e-12)


def test_impute_which_all_overwrite_reproduces_the_baseline():
    """which="all", overwrite=True also matches, including the measured trees."""
    stand = _stand()
    assert stand.impute("height_m", which="all", overwrite=True) == 6
    trees = _by_uid(stand)
    for uid, expected in BASELINE_ALL.items():
        assert trees[uid].imputed["height_m"].value == pytest.approx(expected, abs=1e-9)


def test_measured_values_are_never_overwritten():
    """A measurement stays the measurement, whatever is imputed alongside it."""
    stand = _stand()
    stand.impute("height_m", which="all", overwrite=True)
    trees = _by_uid(stand)
    assert trees["m1"].height_m == 9.0
    assert trees["m1"].value_of("height_m") == 9.0  # measured wins
    assert trees["m1"].provenance("height_m") == "measured"


def test_impute_skips_trees_that_already_have_a_value():
    """Default which="missing" leaves measured trees alone; overwrite=False keeps existing."""
    stand = _stand()
    assert stand.impute("height_m") == 3
    assert stand.impute("height_m") == 0  # nothing left to fill


# ---------------------------------------------------------------------------
# Resolution order on Tree
# ---------------------------------------------------------------------------


def test_value_of_resolution_order():
    """Measured wins by default; prefer= reverses or restricts."""
    tree = Tree(diameter_cm=20.0, height_m=15.0)
    tree.set_imputed("height_m", 14.0, NaslundHeightImputer())
    assert tree.value_of("height_m") == 15.0
    assert tree.value_of("height_m", prefer="imputed") == 14.0
    assert tree.value_of("height_m", prefer="measured_only") == 15.0
    assert tree.value_of("height_m", prefer="imputed_only") == 14.0


def test_value_of_falls_back_when_one_side_is_absent():
    """Either preference falls back to the other source rather than returning None."""
    only_imputed = Tree(diameter_cm=20.0)
    only_imputed.set_imputed("height_m", 14.0, NaslundHeightImputer())
    assert only_imputed.value_of("height_m") == 14.0

    only_measured = Tree(diameter_cm=20.0, height_m=15.0)
    assert only_measured.value_of("height_m", prefer="imputed") == 15.0
    assert only_measured.value_of("height_m", prefer="imputed_only") is None


def test_value_of_returns_none_when_neither_source_has_a_value():
    assert Tree(diameter_cm=20.0).value_of("height_m") is None
    assert Tree(diameter_cm=20.0).provenance("height_m") is None


def test_value_of_rejects_an_unknown_preference():
    with pytest.raises(ValueError, match="Unknown prefer"):
        Tree(diameter_cm=20.0, height_m=15.0).value_of("height_m", prefer="whatever")


def test_value_of_works_for_an_attribute_tree_does_not_declare():
    """The case that motivated the design: Marklund needs crown_base_height_m."""
    tree = Tree(diameter_cm=20.0, height_m=15.0)
    assert tree.value_of("crown_base_height_m") is None
    tree.set_imputed(
        "crown_base_height_m", 6.0, CallableImputer("crown_base_height_m", lambda t: 6.0)
    )
    assert tree.value_of("crown_base_height_m") == 6.0
    assert tree.provenance("crown_base_height_m") == "imputed"


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def test_imputed_height_records_naslund():
    """An imputed height names the curve that produced it."""
    stand = _stand()
    stand.impute("height_m")
    tree = _by_uid(stand)["u1"]
    entry = tree.imputed["height_m"]
    assert isinstance(entry, ImputedValue)
    assert entry.attribute == "height_m"
    assert entry.imputer_id == "naslund_height_imputer"
    assert entry.source.author.startswith("Näslund")
    assert entry.source.year == 1936
    assert entry.is_cited is True
    assert tree.imputed_source("height_m") is entry.source


def test_callable_imputer_is_recorded_as_uncited():
    """A lambda has no publication, and the value says so."""
    stand = _stand()
    assigned = stand.impute("crown_radius_m", lambda t: 0.15 * float(t.diameter_cm))
    assert assigned == 6
    entry = _by_uid(stand)["m1"].imputed["crown_radius_m"]
    assert entry.value == pytest.approx(1.5)
    assert entry.is_cited is False
    assert entry.source.author == "(none)"
    assert entry.source.year == 0


def test_imputed_source_is_none_for_a_measured_attribute():
    tree = Tree(diameter_cm=20.0, height_m=15.0)
    assert tree.imputed_source("height_m") is None


def test_imputed_value_rejects_a_non_finite_value():
    with pytest.raises(ValueError, match="finite"):
        ImputedValue("height_m", float("nan"), "x", NaslundHeightImputer().source)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_knows_height():
    assert "height_m" in available_attributes()
    assert imputers_for("height_m") == ["naslund"]


def test_resolve_accepts_name_instance_callable_and_default():
    assert isinstance(resolve_imputer("height_m"), NaslundHeightImputer)
    assert isinstance(resolve_imputer("height_m", "auto"), NaslundHeightImputer)
    assert isinstance(resolve_imputer("height_m", "naslund"), NaslundHeightImputer)
    instance = NaslundHeightImputer()
    assert resolve_imputer("height_m", instance) is instance
    assert isinstance(resolve_imputer("crown_radius_m", lambda t: 1.0), CallableImputer)


def test_resolve_rejects_an_imputer_for_the_wrong_attribute():
    with pytest.raises(ValueError, match="produces 'height_m', not"):
        resolve_imputer("crown_radius_m", NaslundHeightImputer())


def test_unregistered_attribute_without_a_spec_is_a_keyerror():
    with pytest.raises(KeyError, match="No imputer registered"):
        resolve_imputer("crown_radius_m")


def test_measured_source_is_rejected_with_an_explanation():
    """ "measured" is a height *source*, not an imputer; the error must say why."""
    with pytest.raises(ValueError, match="cannot fill in one that is missing"):
        resolve_imputer("height_m", "measured")


def test_unknown_name_lists_the_registered_ones():
    with pytest.raises(KeyError, match="Unknown imputer"):
        resolve_imputer("height_m", "nonesuch")


def test_register_imputer_adds_an_attribute():
    """A third-party imputer can be registered for a new attribute."""
    register_imputer(
        "test_attribute_m", "constant", lambda: CallableImputer("test_attribute_m", lambda t: 42.0)
    )
    try:
        assert "test_attribute_m" in available_attributes()
        assert resolve_imputer("test_attribute_m").impute(Tree(diameter_cm=10.0), {}) == 42.0
    finally:
        from pyforestry.base.imputation import registry

        registry._REGISTRY.pop("test_attribute_m", None)


# ---------------------------------------------------------------------------
# Errors and interop
# ---------------------------------------------------------------------------


def test_impute_reports_an_unfittable_curve():
    """One measured pair cannot define a curve, and the error explains why."""
    stand = Stand(
        plots=[
            CircularPlot(
                id=1,
                radius_m=10.0,
                trees=[Tree(diameter_cm=20.0, height_m=15.0), Tree(diameter_cm=25.0)],
            )
        ]
    )
    with pytest.raises(ValueError, match="Could not fit an imputer"):
        stand.impute("height_m")


def test_impute_rejects_an_unknown_which():
    with pytest.raises(ValueError, match="Unknown which"):
        _stand().impute("height_m", which="some")


def test_unfitted_height_imputer_refuses_to_run():
    with pytest.raises(RuntimeError, match="must be fit"):
        NaslundHeightImputer().impute(Tree(diameter_cm=20.0), {})


def test_imputed_values_survive_deepcopy():
    """The simulation checkpointer deepcopies stands; provenance must round-trip."""
    stand = _stand()
    stand.impute("height_m")
    clone = copy.deepcopy(stand)
    original = _by_uid(stand)["u1"].imputed["height_m"]
    copied = _by_uid(clone)["u1"].imputed["height_m"]
    assert copied.value == original.value
    assert copied.imputer_id == original.imputer_id
    assert copied.source.author == original.source.author


def test_competition_uses_imputed_heights():
    """MeanHeightRadius needs heights; imputed ones must count."""
    stand = _stand()
    stand.impute("height_m")
    plot = stand.plots[0]
    results = competition_indices(
        plot, indices=["Heg"], selector=MeanHeightRadius(0.4, min_size_ratio=0.3)
    )
    assert results and all("Heg" in r.indices for r in results)


def test_imputation_is_discoverable_in_the_catalog():
    """The package publishes an honest DESCRIPTOR: mechanism, not model."""
    from pyforestry import catalog

    entry = catalog.describe("tree_attribute_imputation")
    assert entry.region == "base"
    assert entry.domain == "imputation"
    assert entry.source.author == "(none)"
    assert entry.source.year == 0
    # `composes` names catalogued models, so it points at the curve itself,
    # not at the imputer id that wraps it.
    assert "naslund_1936_height_curve" in entry.composes
    catalogued = {model.component_id for model in catalog.list_models()}
    assert set(entry.composes) <= catalogued


def test_tree_repr_shows_imputed_attributes():
    tree = Tree(diameter_cm=20.0)
    tree.set_imputed("height_m", 14.0, NaslundHeightImputer())
    assert "imputed=['height_m']" in repr(tree)


# ---------------------------------------------------------------------------
# Layering and argument handling
# ---------------------------------------------------------------------------


def test_imputed_value_lives_in_contracts_so_tree_stays_a_leaf():
    """``helpers.tree`` must not depend on the package that fills its map.

    ``ImputedValue`` sits in ``base.contracts`` -- which imports nothing from the
    package -- so ``Tree`` can store one without pulling in ``base.imputation``,
    which imports ``base.helpers.height_models`` right back.
    """
    from pyforestry.base import contracts
    from pyforestry.base.contracts import ImputedValue as FromContracts
    from pyforestry.base.imputation import ImputedValue as FromImputation

    assert FromContracts is FromImputation
    assert "ImputedValue" in contracts.__all__

    source = pathlib.Path(inspect.getfile(pyforestry.base.helpers.tree)).read_text(
        encoding="utf-8"
    )
    assert "pyforestry.base.imputation" not in source


def test_impute_rejects_kwargs_it_cannot_apply():
    """Constructor kwargs alongside a built imputer would be silently discarded."""
    stand = _stand()
    with pytest.raises(TypeError, match="already-built imputer"):
        stand.impute("height_m", NaslundHeightImputer(), naslund_exponent="auto")
    with pytest.raises(TypeError, match="already-built imputer"):
        stand.impute("crown_radius_m", lambda t: 1.0, naslund_exponent="auto")
    # Naming a registered imputer is exactly the case kwargs are for.
    assert stand.impute("height_m", "naslund", naslund_exponent="auto") > 0


def test_registered_names_reject_the_height_source_spellings():
    """'measured' is a height *source*, not something that can impute."""
    stand = _stand()
    for name in ("measured", "measured+imputed"):
        with pytest.raises(ValueError, match="cannot fill in one that is missing"):
            stand.impute("height_m", name)
