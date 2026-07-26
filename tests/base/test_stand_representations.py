"""``Stand`` holds every representation, and the simulation context holds a ``Stand``.

The context used to carry a second copy of the state -- its own metric store, its
own diameter-class inventory, its own plot-to-stand estimator. These tests assert
the properties that replaced it: one store, all four representations on ``Stand``,
and writes rejected outside the representation that can hold them.
"""

import pytest

from pyforestry.base.helpers import CircularPlot, Stand, Tree
from pyforestry.base.helpers.primitives import StandBasalArea, Stems
from pyforestry.base.helpers.tree_species import parse_tree_species
from pyforestry.base.simulation import SimulationContext
from pyforestry.base.simulation.growth_model import ExampleStandGeneralModel

PICEA = parse_tree_species("picea abies")
PINUS = parse_tree_species("pinus sylvestris")


def _two_species_stand() -> Stand:
    """One spruce on plot A, one pine on plot B -- the A1 divergence case."""
    return Stand(
        area_ha=2.0,
        plots=[
            CircularPlot(id=1, area_m2=10_000.0, trees=[Tree(species=PICEA, diameter_cm=20.0)]),
            CircularPlot(id=2, area_m2=10_000.0, trees=[Tree(species=PINUS, diameter_cm=20.0)]),
        ],
    )


# ---------------------------------------------------------------------------
# One state
# ---------------------------------------------------------------------------


def test_context_metrics_are_the_stands_metrics_not_a_copy():
    """Not "the two agree" -- there is one dict, so they cannot disagree."""
    ctx = ExampleStandGeneralModel().build_context(_two_species_stand(), mode_hint="tree_list")
    for metric in ("Stems", "BasalArea"):
        assert ctx._metrics[metric] is ctx.stand._metric_estimates[metric]


def test_context_no_longer_carries_a_second_estimator():
    ctx = ExampleStandGeneralModel().build_context(_two_species_stand(), mode_hint="tree_list")
    for gone in (
        "_dclass",
        "_recompute_metrics_tree_list",
        "_recompute_metrics_dclass",
        "_normalize_dclass_inventory",
        "_normalize_aggregate_metrics",
        "_recompute_qmd",
    ):
        assert not hasattr(ctx, gone), f"SimulationContext still carries {gone}"


def test_context_stand_is_a_sandbox():
    """A run may mutate its stand without touching the inventory it was built from."""
    original = _two_species_stand()
    ctx = ExampleStandGeneralModel().build_context(original, mode_hint="tree_list")
    assert ctx.stand is not original
    ctx.stand.thin_trees(rule=lambda tree: tree.species == PICEA)
    assert sum(len(p.trees) for p in original.plots) == 2
    assert sum(len(p.trees) for p in ctx.stand.plots) == 1


# ---------------------------------------------------------------------------
# The representations
# ---------------------------------------------------------------------------


def test_tree_list_is_the_default_representation():
    assert _two_species_stand().representation == "tree_list"


def test_from_aggregate_metrics_derives_qmd():
    stand = Stand.from_aggregate_metrics(
        {"BasalArea": {"TOTAL": StandBasalArea(25.0)}, "Stems": {"TOTAL": Stems(800.0)}},
        area_ha=1.0,
    )
    assert stand.representation == "aggregate"
    assert float(stand.BasalArea) == pytest.approx(25.0)
    assert float(stand.Stems) == pytest.approx(800.0)
    assert float(stand.QMD) == pytest.approx(19.947, abs=1e-3)


def test_from_diameter_classes_reduces_to_metrics():
    stand = Stand.from_diameter_classes(
        {PICEA: {"bin_mids_cm": [10.0, 20.0], "n_per_ha": [300.0, 200.0]}},
        area_ha=1.0,
    )
    assert stand.representation == "diameter_class"
    assert float(stand.Stems) == pytest.approx(500.0)
    # 300 * pi * 0.05^2 + 200 * pi * 0.10^2
    assert float(stand.BasalArea) == pytest.approx(
        300 * 3.141592653589793 * 0.05**2 + 200 * 3.141592653589793 * 0.10**2
    )


def test_unspeciated_diameter_class_inventory_is_not_an_empty_stand():
    """Regression: an inventory keyed only by ``"TOTAL"`` used to report zero.

    The species keys were summed and the result written over ``"TOTAL"``, so a
    distribution that *was* the total was replaced by the sum of no species. This
    is the shape ``build_context`` falls back to whenever it cannot bin a tree
    list, which meant a diameter-class model driven from an aggregate stand read
    a stand of nothing and reported it as a successful build.
    """
    stand = Stand.from_diameter_classes(
        {"TOTAL": {"bin_mids_cm": [16.0], "n_per_ha": [600.0]}}, area_ha=1.0
    )
    assert float(stand.Stems) == pytest.approx(600.0)
    assert float(stand.BasalArea) == pytest.approx(600 * 3.141592653589793 * 0.08**2)
    assert float(stand.QMD) == pytest.approx(16.0, abs=1e-6)


def test_diameter_class_fallback_context_reports_the_stand_it_was_built_from():
    """The same regression, through the path that produces it."""
    source = Stand(area_ha=1.0, plots=[])
    source._metric_estimates = {
        "BasalArea": {"TOTAL": StandBasalArea(12.0)},
        "Stems": {"TOTAL": Stems(600.0)},
    }
    ctx = ExampleStandGeneralModel().build_context(source, mode_hint="diameter_class")
    assert ctx.mode == "diameter_class"
    assert float(ctx.metrics["Stems"]["TOTAL"]) == pytest.approx(600.0)
    assert float(ctx.metrics["BasalArea"]["TOTAL"]) == pytest.approx(12.0, rel=1e-3)


# ---------------------------------------------------------------------------
# Writes are rejected outside the representation that can hold them
# ---------------------------------------------------------------------------


def test_aggregate_write_on_a_tree_list_stand_raises():
    stand = _two_species_stand()
    with pytest.raises(RuntimeError, match="requires representation"):
        stand.set_aggregate_metrics(ba_total=10.0, stems_total=100.0)


def test_diameter_class_write_on_an_aggregate_stand_raises():
    stand = Stand.from_aggregate_metrics(
        {"BasalArea": {"TOTAL": StandBasalArea(25.0)}, "Stems": {"TOTAL": Stems(800.0)}}
    )
    with pytest.raises(RuntimeError, match="requires representation"):
        stand.set_diameter_classes({})


def test_thinning_a_stand_that_holds_no_trees_raises():
    stand = Stand.from_aggregate_metrics(
        {"BasalArea": {"TOTAL": StandBasalArea(25.0)}, "Stems": {"TOTAL": Stems(800.0)}}
    )
    with pytest.raises(RuntimeError, match="requires representation"):
        stand.thin_trees(uids=["t1"])


def test_reading_plots_off_an_aggregate_context_raises():
    source = Stand(area_ha=1.0, plots=[])
    source._metric_estimates = {
        "BasalArea": {"TOTAL": StandBasalArea(12.0)},
        "Stems": {"TOTAL": Stems(600.0)},
    }
    ctx = ExampleStandGeneralModel().build_context(source, mode_hint="aggregate")
    with pytest.raises(AttributeError, match="holds no plots"):
        _ = ctx.plots


# ---------------------------------------------------------------------------
# The per-species publication path
# ---------------------------------------------------------------------------


def test_set_species_metrics_derives_totals_when_none_supplied():
    stand = Stand.from_aggregate_metrics(
        {"BasalArea": {"TOTAL": StandBasalArea(1.0)}, "Stems": {"TOTAL": Stems(1.0)}}
    )
    stand.set_species_metrics(
        basal_area={PICEA: StandBasalArea(9.0), PINUS: StandBasalArea(6.0)},
        stems={PICEA: Stems(250.0), PINUS: Stems(150.0)},
    )
    assert float(stand.BasalArea) == pytest.approx(15.0)
    assert float(stand.Stems) == pytest.approx(400.0)


def test_set_species_metrics_respects_a_supplied_total():
    """A partial breakdown must not shrink the stand to the species it lists.

    Basal area may be known per species while stems are only known for the
    species that were tallied; the caller knows that, and this method does not.
    """
    stand = Stand.from_aggregate_metrics(
        {"BasalArea": {"TOTAL": StandBasalArea(1.0)}, "Stems": {"TOTAL": Stems(1.0)}}
    )
    stand.set_species_metrics(
        basal_area={"TOTAL": StandBasalArea(20.0), PICEA: StandBasalArea(9.0)},
        stems={"TOTAL": Stems(500.0), PICEA: Stems(250.0)},
    )
    assert float(stand.BasalArea) == pytest.approx(20.0)
    assert float(stand.Stems) == pytest.approx(500.0)


def test_set_species_metrics_omits_qmd_for_a_species_it_cannot_define():
    stand = Stand.from_aggregate_metrics(
        {"BasalArea": {"TOTAL": StandBasalArea(1.0)}, "Stems": {"TOTAL": Stems(1.0)}}
    )
    stand.set_species_metrics(
        basal_area={PICEA: StandBasalArea(9.0), PINUS: StandBasalArea(6.0)},
        stems={PICEA: Stems(250.0)},  # no pine stems
    )
    qmd = stand._metric_estimates["QMD"]
    assert PICEA in qmd
    assert PINUS not in qmd


def test_context_forwards_species_metrics_to_its_stand():
    source = Stand(area_ha=1.0, plots=[])
    source._metric_estimates = {
        "BasalArea": {"TOTAL": StandBasalArea(12.0)},
        "Stems": {"TOTAL": Stems(600.0)},
    }
    ctx = ExampleStandGeneralModel().build_context(source, mode_hint="aggregate")
    ctx.set_species_metrics(
        basal_area={PICEA: StandBasalArea(9.0)},
        stems={PICEA: Stems(250.0)},
    )
    assert float(ctx.stand.BasalArea) == pytest.approx(9.0)
    assert float(ctx.metrics["BasalArea"]["TOTAL"]) == pytest.approx(9.0)


def test_scale_stems_clamps_at_zero():
    stand = Stand.from_aggregate_metrics(
        {"BasalArea": {"TOTAL": StandBasalArea(25.0)}, "Stems": {"TOTAL": Stems(800.0)}}
    )
    stand.scale_stems(-1.0)
    assert float(stand.Stems) == 0.0
    assert float(stand.BasalArea) == 0.0


def test_set_diameter_classes_rejects_mismatched_arrays():
    stand = Stand.from_diameter_classes({"TOTAL": {"bin_mids_cm": [10.0], "n_per_ha": [1.0]}})
    with pytest.raises(ValueError, match="length mismatch"):
        stand.set_diameter_classes({"TOTAL": {"bin_mids_cm": [10.0, 20.0], "n_per_ha": [1.0]}})


def test_context_checkpoint_round_trips_a_diameter_class_stand():
    source = Stand(area_ha=1.0, plots=[])
    source._metric_estimates = {
        "BasalArea": {"TOTAL": StandBasalArea(12.0)},
        "Stems": {"TOTAL": Stems(600.0)},
    }
    model = ExampleStandGeneralModel()
    ctx = model.build_context(source, mode_hint="diameter_class")
    restored = SimulationContext.from_checkpoint(model, ctx.checkpoint())
    assert restored.diameter_classes == ctx.diameter_classes
    assert float(restored.metrics["Stems"]["TOTAL"]) == pytest.approx(
        float(ctx.metrics["Stems"]["TOTAL"])
    )
