# test_simulation_expanded.py
import math
from types import SimpleNamespace

import pytest

from pyforestry.base.helpers import (
    PICEA_ABIES,
    AngleCount,
    CircularPlot,
    SiteBase,
    Stand,
    StandBasalArea,
    Stems,
    Tree,
    parse_tree_species,
)
from pyforestry.base.simulation import (
    ContextEnsemble,
    ExampleStandGeneralModel,
    GrowthModel,
    PythonEngine,
    Requirements,
)
from pyforestry.base.simulation.adapters import (
    AdapterRegistry,
    AngleCountToDiameterClassAdapter,
    AngleCountToPseudoTreesAdapter,
    AngleCountToSpatialPseudoTreesAdapter,
    TreeListToDiameterClassAdapter,
    TreeListToSpatialAdapter,
)
from pyforestry.base.simulation.ensemble import _engine_from_hint

# ----------------------------- Test fixtures ---------------------------------


def _tree_list_stand(with_positions=False):
    plots = [
        CircularPlot(
            id=1,
            area_m2=200.0,
            trees=[
                Tree(
                    species="Picea abies",
                    diameter_cm=20.0,
                    height_m=16.0,
                    weight_n=5,
                    position=(1.0, 2.0) if with_positions else None,
                ),
                Tree(
                    species="Picea abies",
                    diameter_cm=18.0,
                    height_m=14.0,
                    weight_n=4,
                    position=(2.0, 1.0) if with_positions else None,
                ),
            ],
        ),
    ]
    return Stand(area_ha=1.0, plots=plots)


def _ac_stand():
    # Diameters are supplied so stems/ha (and hence QMD) are derivable, which the
    # angle-count adapters need.
    ac1 = AngleCount(
        ba_factor=2.0, value=[10], species=[PICEA_ABIES], point_id="p1", diameters_cm=[[20.0] * 10]
    )
    ac2 = AngleCount(
        ba_factor=2.0, value=[12], species=[PICEA_ABIES], point_id="p2", diameters_cm=[[20.0] * 12]
    )
    p1 = CircularPlot(id=1, area_m2=200.0, AngleCount=[ac1])
    p2 = CircularPlot(id=2, area_m2=200.0, AngleCount=[ac2])
    return Stand(area_ha=1.0, plots=[p1, p2])


class _DummySite(SiteBase):
    def compute_attributes(self) -> None:
        pass


# --------------------------- Your existing tests -----------------------------


def test_build_modes_and_adapters():
    model = ExampleStandGeneralModel()
    ac = _ac_stand()
    # 1) diameter_class from Angle-Count
    ok, missing = model.can_build(ac, allow_adapters=True, mode_hint="diameter_class")
    assert ok, missing
    ctx_dc = model.build_context(ac, mode_hint="diameter_class")
    assert ctx_dc.mode == "diameter_class"
    assert pytest.approx(float(ac.BasalArea)) == float(ctx_dc.metrics["BasalArea"]["TOTAL"])
    assert pytest.approx(float(ac.Stems)) == float(ctx_dc.metrics["Stems"]["TOTAL"])
    ctx_dc.do("thin_smallest_classes", fraction=0.1)

    # 2) spatial pseudo from Angle-Count (opt-in)
    ctx_sp = model.build_context(ac, mode_hint="spatial", adapter_kwargs={"seed": 42})
    assert ctx_sp.mode in ("spatial", "aggregate")
    if ctx_sp.mode == "spatial":
        ctx_sp.do("thin_fraction", fraction=0.05)


def test_adapter_registry_and_angle_count_adapters():
    from pyforestry.base.simulation.adapters import (
        Adapter,
        AdapterRegistry,
        AngleCountToDiameterClassAdapter,
        AngleCountToPseudoTreesAdapter,
        TreeListToDiameterClassAdapter,
    )

    with pytest.raises(NotImplementedError):
        Adapter().can_adapt(Stand())
    with pytest.raises(NotImplementedError):
        Adapter().adapt(Stand())

    stand = Stand(plots=[])
    stand.use_angle_count = False
    assert not AngleCountToPseudoTreesAdapter().can_adapt(stand)

    stand.use_angle_count = True
    stand._metric_estimates = {
        "BasalArea": {"TOTAL": StandBasalArea(10.0)},
        "Stems": {"TOTAL": Stems(100.0)},
    }
    adapter = AngleCountToPseudoTreesAdapter(replicas_per_species=4)
    out = adapter.adapt(stand, replicas_per_species=0)
    plot = out["plots"][0]
    assert len(plot.trees) == adapter.replicas_per_species

    sp = parse_tree_species("picea abies")
    stand2 = Stand(plots=[])
    stand2.use_angle_count = True
    stand2._metric_estimates = {
        "BasalArea": {sp: StandBasalArea(5.0, species=sp), "TOTAL": StandBasalArea(5.0)},
        "Stems": {sp: Stems(0.0, species=sp), "TOTAL": Stems(0.0)},
    }
    out2 = AngleCountToPseudoTreesAdapter().adapt(stand2)
    assert out2["plots"][0].trees == []

    stand3 = Stand(plots=[])
    stand3.use_angle_count = True
    stand3._metric_estimates = {
        "BasalArea": {sp: StandBasalArea(0.0, species=sp), "TOTAL": StandBasalArea(10.0)},
        "Stems": {sp: Stems(0.0, species=sp), "TOTAL": Stems(100.0)},
    }
    out3 = AngleCountToDiameterClassAdapter().adapt(stand3)
    assert "TOTAL" in out3["dclass"]

    stand4 = Stand(
        plots=[CircularPlot(id=1, radius_m=5.0, trees=[Tree(species=None, diameter_cm=None)])]
    )
    tree_adapter = TreeListToDiameterClassAdapter()
    assert tree_adapter.can_adapt(stand4)
    out4 = tree_adapter.adapt(stand4)
    assert "dclass" in out4

    registry = AdapterRegistry.default()
    spatial_adapters = registry.find_for("spatial")
    assert any(adapter.target_mode == "spatial" for adapter in spatial_adapters)


def test_growth_model_base_methods():
    """The base class is abstract; its non-abstract defaults still work."""
    with pytest.raises(TypeError, match="abstract"):
        GrowthModel()

    class Minimal(GrowthModel):
        def requirements(self):
            return Requirements()

        def update_step(self, ctx, dt):
            return None

    model = Minimal()
    assert model.default_attrs() == {}
    assert model.available_actions() == {}
    assert model.requirements().native_step_years is None


def test_growth_model_can_build_branches():
    class ReqModel(ExampleStandGeneralModel):
        def requirements(self) -> Requirements:
            return Requirements(inventory="spatial", require_site=True, require_top_height=True)

    req_model = ReqModel()
    plot = CircularPlot(
        id=1,
        area_m2=200.0,
        trees=[Tree(species="Picea abies", diameter_cm=20.0, height_m=None, weight_n=1.0)],
    )
    stand = Stand(area_ha=1.0, plots=[plot])
    ok, missing = req_model.can_build(stand, allow_adapters=False)
    assert not ok
    assert "site" in missing
    assert "top_height" in missing
    assert any("spatial" in item for item in missing)

    model = ExampleStandGeneralModel()

    class DummyStand:
        use_angle_count = False
        plots = []
        site = None

        def get_dominant_height(self):
            return None

        @property
        def BasalArea(self):
            raise RuntimeError("no aggregates")

        @property
        def Stems(self):
            raise RuntimeError("no aggregates")

    dummy = DummyStand()
    ok, missing = model.can_build(dummy, mode_hint="tree_list", allow_adapters=False)
    assert not ok
    assert "tree_list" in missing

    ok, missing = model.can_build(dummy, mode_hint="diameter_class", allow_adapters=False)
    assert not ok
    assert any("diameter_class" in item for item in missing)

    ok, missing = model.can_build(dummy, mode_hint="aggregate", allow_adapters=False)
    assert not ok
    assert any("aggregates" in item for item in missing)

    ok, missing = model.can_build(dummy, allow_adapters=False)
    assert not ok
    # `can_build` reports the mode `build_context` would actually choose. For an
    # "either" model on a stand with no trees that is "aggregate", so the message
    # names the aggregates it lacks rather than the old disjunction "tree_list or
    # aggregates", which described a choice the builder had already made.
    assert any("aggregates" in item for item in missing)

    ok, missing = model.can_build(_ac_stand(), allow_adapters=True, mode_hint="spatial")
    assert ok

    pos_stand = _tree_list_stand(with_positions=True)
    ok, missing = model.can_build(pos_stand, allow_adapters=False, mode_hint="spatial")
    assert ok


def test_growth_model_build_context_branches(monkeypatch):
    import pyforestry.base.simulation.adapters as adapters

    model = ExampleStandGeneralModel()
    ac = _ac_stand()

    with pytest.raises(ValueError, match="Adapter"):
        model.build_context(ac, mode_hint="tree_list", use_adapter="missing_adapter")

    stand = Stand(plots=[])
    stand.use_angle_count = True
    stand._metric_estimates = {
        "BasalArea": {"TOTAL": StandBasalArea(10.0)},
        "Stems": {"TOTAL": Stems(100.0)},
    }

    class DummyRegistry:
        def get(self, name):
            return None

    monkeypatch.setattr(adapters.AdapterRegistry, "default", staticmethod(lambda: DummyRegistry()))
    ctx = model.build_context(stand, mode_hint="tree_list")
    assert ctx.mode == "aggregate"

    tree_stand = _tree_list_stand(with_positions=False)
    ctx2 = model.build_context(tree_stand, mode_hint="spatial")
    assert ctx2.mode == "tree_list"

    stand3 = Stand(plots=[CircularPlot(id=1, radius_m=5.0, trees=[])])
    stand3._metric_estimates = {
        "BasalArea": {"TOTAL": StandBasalArea(10.0)},
        "Stems": {"TOTAL": Stems(100.0)},
    }
    ctx3 = model.build_context(stand3, mode_hint="diameter_class")
    assert ctx3.mode == "diameter_class"
    assert ctx3.diameter_classes["TOTAL"]["bin_mids_cm"]

    stand4 = Stand(plots=[])
    stand4.use_angle_count = True
    stand4._metric_estimates = {
        "BasalArea": {"TOTAL": StandBasalArea(12.0)},
        "Stems": {"TOTAL": Stems(110.0)},
    }
    ctx4 = model.build_context(stand4)
    assert ctx4.mode == "aggregate"

    stand5 = _tree_list_stand()
    ctx5 = model.build_context(stand5)
    assert ctx5.mode == "tree_list"


def test_example_model_diameter_class_update_step():
    model = ExampleStandGeneralModel()
    stand = Stand(plots=[])
    stand._metric_estimates = {
        "BasalArea": {"TOTAL": StandBasalArea(8.0)},
        "Stems": {"TOTAL": Stems(200.0)},
    }
    ctx = model.build_context(stand, mode_hint="diameter_class")
    before = ctx.diameter_classes["TOTAL"]["bin_mids_cm"][0]
    ctx.update_step(1.0)
    after = ctx.diameter_classes["TOTAL"]["bin_mids_cm"][0]
    assert after > before


def test_example_model_mortality_and_thinning_branches():
    model = ExampleStandGeneralModel()
    agg_ctx = model.build_context(_tree_list_stand(), mode_hint="aggregate")
    agg_ctx.set_aggregate_metrics(ba_total=10.0, stems_total=100.0)
    model._act_apply_mortality_rate(agg_ctx, rate=0.1)
    assert float(agg_ctx.metrics["Stems"]["TOTAL"]) < 100.0

    with pytest.raises(ValueError):
        model._act_apply_mortality_rate(agg_ctx, rate=1.5)

    tree = Tree(species="Picea abies", diameter_cm=20.0, weight_n=None)
    stand = Stand(plots=[CircularPlot(id=1, area_m2=200.0, trees=[tree])])
    tree_ctx = model.build_context(stand, mode_hint="tree_list")
    model._act_apply_mortality_rate(tree_ctx, rate=0.2)
    assert tree_ctx.plots[0].trees[0].weight_n == pytest.approx(0.8)

    with pytest.raises(ValueError):
        model._act_thin_fraction(tree_ctx, fraction=1.0)

    empty_ctx = model.build_context(
        Stand(plots=[CircularPlot(id=2, area_m2=200.0, trees=[])]),
        mode_hint="tree_list",
    )
    model._act_thin_fraction(empty_ctx, fraction=0.5)


def test_example_model_thin_smallest_classes_branches():
    model = ExampleStandGeneralModel()
    agg_ctx = model.build_context(_tree_list_stand(), mode_hint="aggregate")
    with pytest.raises(RuntimeError):
        model._act_thin_smallest_classes(agg_ctx, fraction=0.2)

    stand = Stand(plots=[])
    stand._metric_estimates = {
        "BasalArea": {"TOTAL": StandBasalArea(8.0)},
        "Stems": {"TOTAL": Stems(100.0)},
    }
    dclass_ctx = model.build_context(stand, mode_hint="diameter_class")
    with pytest.raises(ValueError):
        model._act_thin_smallest_classes(dclass_ctx, fraction=1.0)

    dclass_ctx.set_diameter_class(
        {"TOTAL": {"bin_mids_cm": [10.0, 20.0], "n_per_ha": [50.0, 50.0]}}
    )
    model._act_thin_smallest_classes(dclass_ctx, fraction=0.2)
    assert dclass_ctx.diameter_classes["TOTAL"]["n_per_ha"][1] == pytest.approx(50.0)


def test_spatial_from_tree_list():
    model = ExampleStandGeneralModel()
    st = _tree_list_stand(with_positions=False)
    ok, missing = model.can_build(st, allow_adapters=True, mode_hint="spatial")
    assert ok, missing
    ctx = model.build_context(st, mode_hint="spatial")
    assert ctx.mode == "spatial"
    assert all(getattr(t, "position", None) is not None for p in ctx.plots for t in p.trees)


def test_ensemble_batch_writeback():
    model = ExampleStandGeneralModel()
    st = _tree_list_stand()
    # Build aggregate contexts with known totals
    ctxs = []
    for _ in range(8):
        ctx = model.build_context(st, mode_hint="aggregate")
        ctx.set_aggregate_metrics(ba_total=20.0, stems_total=1200.0)
        ctxs.append(ctx)
    ens = ContextEnsemble(ctxs, model=model)
    for _ in range(3):
        ens.update_step(dt=1.0)
    for c in ctxs:
        assert float(c.metrics["BasalArea"]["TOTAL"]) > 20.0
        assert float(c.metrics["Stems"]["TOTAL"]) < 1200.0


def test_context_checkpoint_round_trip_tree_list():
    model = ExampleStandGeneralModel()
    ctx = model.build_context(_tree_list_stand(), mode_hint="tree_list")
    ctx.update_step(0.5)
    cp = ctx.checkpoint()
    restored_ctx = type(ctx).from_checkpoint(model, cp)
    assert restored_ctx.mode == ctx.mode
    assert restored_ctx.state["t"] == pytest.approx(ctx.state["t"])
    assert float(restored_ctx.metrics["BasalArea"]["TOTAL"]) == pytest.approx(
        float(ctx.metrics["BasalArea"]["TOTAL"])
    )
    assert restored_ctx.attrs == ctx.attrs


def test_context_checkpoint_round_trip_aggregate():
    model = ExampleStandGeneralModel()
    ctx = model.build_context(_tree_list_stand(), mode_hint="aggregate")
    ctx.set_aggregate_metrics(ba_total=12.0, stems_total=400.0)
    ctx.update_step(1.0)
    cp = ctx.checkpoint()
    restored_ctx = type(ctx).from_checkpoint(model, cp)
    expected_ba = 12.0 * (1.0 + model.ba_rel)
    expected_n = 400.0 * (1.0 - model.mort)
    assert restored_ctx.mode == "aggregate"
    assert float(restored_ctx.metrics["BasalArea"]["TOTAL"]) == pytest.approx(expected_ba)
    assert float(restored_ctx.metrics["Stems"]["TOTAL"]) == pytest.approx(expected_n)


# -------------------------- New/expanded coverage ----------------------------


def test_metrics_is_copy_not_view():
    """Mutating the returned mapping must not affect the internal store."""
    model = ExampleStandGeneralModel()
    ctx = model.build_context(_tree_list_stand(), mode_hint="aggregate")
    ctx.set_aggregate_metrics(ba_total=30.0, stems_total=900.0)
    m1 = ctx.metrics  # snapshot 1
    m2 = ctx.metrics  # snapshot 2
    # Same values, different objects — proves it's a copy each time
    assert m1 is not m2
    assert m1.keys() == m2.keys()
    assert m1["Stems"] is not m2["Stems"]
    # Now change the *internal* store; a new snapshot should change, old should not
    ctx.set_aggregate_metrics(ba_total=31.0, stems_total=901.0)
    assert float(m1["Stems"]["TOTAL"]) == pytest.approx(900.0)
    assert float(ctx.metrics["Stems"]["TOTAL"]) == pytest.approx(901.0)


def test_qmd_recomputed_from_ba_and_n():
    """QMD should match sqrt((40000 * BA) / (pi * N))."""
    model = ExampleStandGeneralModel()
    ctx = model.build_context(_tree_list_stand(), mode_hint="aggregate")
    BA, N = 25.0, 1000.0
    ctx.set_aggregate_metrics(ba_total=BA, stems_total=N)
    qmd = float(ctx.metrics["QMD"]["TOTAL"])
    expected = math.sqrt((40000.0 * BA) / (math.pi * N))
    assert qmd == pytest.approx(expected, rel=1e-9)


def test_action_mode_gating_thin_smallest_requires_dclass():
    """thin_smallest_classes must be rejected outside diameter_class mode."""
    model = ExampleStandGeneralModel()
    ctx = model.build_context(_tree_list_stand(), mode_hint="tree_list")
    with pytest.raises(RuntimeError):
        ctx.do("thin_smallest_classes", fraction=0.1)


def test_dclass_normalize_mismatch_raises():
    """_normalize_dclass_inventory should reject mismatched arrays."""
    model = ExampleStandGeneralModel()
    ctx = model.build_context(_tree_list_stand(), mode_hint="diameter_class")
    bad = {"X": {"bin_mids_cm": [10.0, 12.0], "n_per_ha": [100.0]}}
    with pytest.raises(ValueError):
        ctx.set_diameter_class(bad)


def test_tree_list_context_strips_anglecount_and_references_live_trees():
    """Tree-list contexts should drop AngleCount tallies but keep live tree references."""
    model = ExampleStandGeneralModel()
    # Build a tree-list plot that *also* has AngleCount tallies.
    ac = AngleCount(ba_factor=2.0, value=[10], species=[PICEA_ABIES], point_id="px")
    p = CircularPlot(
        id=9,
        area_m2=200.0,
        AngleCount=[ac],
        trees=[Tree(species="Picea abies", diameter_cm=20.0, weight_n=1.0)],
    )
    st = Stand(area_ha=1.0, plots=[p])
    st.use_angle_count = False
    ctx = model.build_context(st, mode_hint="tree_list")
    assert all(len(pp.AngleCount) == 0 for pp in ctx.plots)
    assert ctx.plots[0].trees[0] is st.plots[0].trees[0]

    before = float(st.plots[0].trees[0].diameter_cm or 0.0)
    ctx.update_step(1.0)
    after = float(st.plots[0].trees[0].diameter_cm or 0.0)
    assert after > before


def test_to_pandas_history_shape_and_values():
    """History rows -> DataFrame columns and content."""
    model = ExampleStandGeneralModel()
    ctx = model.build_context(_tree_list_stand(), mode_hint="aggregate")
    ctx.set_aggregate_metrics(ba_total=10.0, stems_total=100.0)
    ctx.do("fertilize", years=1.0)
    ctx.update_step(0.5)
    df = ctx.to_pandas()
    assert {"t", "op", "ba_total", "n_total", "qmd_total_cm"}.issubset(set(df.columns))


class _DummySite(SiteBase):
    def compute_attributes(self) -> None:
        return None


class _RequirementsModel(GrowthModel):
    def requirements(self) -> Requirements:
        return Requirements(require_site=True, require_top_height=True, inventory="aggregate")

    def update_step(self, ctx, dt):  # type: ignore[override]
        ctx.state["t"] = ctx.state.get("t", 0.0) + dt


def test_growth_model_can_build_requirements():
    model = _RequirementsModel()
    stand = Stand(area_ha=1.0, plots=[])
    ok, missing = model.can_build(stand)
    assert not ok
    assert "site" in missing
    assert "top_height" in missing

    stand_ok = Stand(
        area_ha=1.0,
        plots=[
            CircularPlot(id=1, area_m2=200.0, trees=[Tree(species="Picea abies", height_m=15.0)])
        ],
        site=_DummySite(latitude=60.0, longitude=15.0),
    )
    ok, missing = model.can_build(stand_ok)
    assert ok
    assert missing == []


def test_growth_model_can_build_tree_list_and_spatial():
    model = ExampleStandGeneralModel()
    ok, missing = model.can_build(_tree_list_stand(), mode_hint="tree_list", allow_adapters=False)
    assert ok
    assert missing == []

    ok, missing = model.can_build(_ac_stand(), mode_hint="spatial", allow_adapters=True)
    assert ok
    assert missing == []


def test_growth_model_build_context_invalid_adapter():
    model = ExampleStandGeneralModel()
    stand = _ac_stand()
    stand._metric_estimates = {}

    with pytest.raises(ValueError):
        model.build_context(stand, mode_hint="tree_list", use_adapter="missing_adapter")

    with pytest.raises(ValueError):
        model.build_context(
            stand, mode_hint="tree_list", use_adapter="angle_count_pseudo_tree_list"
        )


def test_grow_is_gone_and_update_step_is_the_only_name():
    """The deprecated alias is removed, not merely warned about.

    ``grow`` existed three times -- on SimulationContext, on GrowthModel, and
    re-implemented verbatim on ExampleStandGeneralModel -- alongside a
    ``hasattr(model, "update_step")`` shim in update_step that could not fire
    once update_step became abstract.
    """
    model = ExampleStandGeneralModel()
    ctx = model.build_context(_tree_list_stand(), mode_hint="aggregate")

    assert not hasattr(model, "grow")
    assert not hasattr(ctx, "grow")
    assert not hasattr(_RequirementsModel(), "grow")


def test_adapter_registry_and_engines():
    registry = AdapterRegistry.default()
    assert registry.get("missing") is None
    assert registry.find_for("tree_list")

    assert _engine_from_hint("numpy").__class__.__name__ == "PythonEngine"
    assert _engine_from_hint(PythonEngine()).__class__.__name__ == "PythonEngine"
    with pytest.raises(ValueError):
        _engine_from_hint("unknown_backend")
    with pytest.raises(TypeError):
        _engine_from_hint(123)


def test_angle_count_pseudo_trees_adapter_replicas_and_total():
    stand = _ac_stand()
    adapter = AngleCountToPseudoTreesAdapter(replicas_per_species=3)
    out = adapter.adapt(stand, replicas_per_species=0)
    plot = out["plots"][0]
    assert len(plot.trees) == 3

    stand_total = _ac_stand()
    stand_total._metric_estimates = {
        "BasalArea": {"TOTAL": StandBasalArea(10.0, species=None)},
        "Stems": {"TOTAL": Stems(100.0, species=None)},
    }
    out_total = adapter.adapt(stand_total)
    plot_total = out_total["plots"][0]
    assert all(t.species is None for t in plot_total.trees)


def test_angle_count_spatial_adapter_positions():
    stand = _ac_stand()
    adapter = AngleCountToSpatialPseudoTreesAdapter(replicas_per_species=2)
    out = adapter.adapt(stand, seed=7)
    plot = out["plots"][0]
    assert all(t.position is not None for t in plot.trees)


def test_diameter_class_adapters_and_tree_list_spatial():
    stand = _ac_stand()
    adapter = AngleCountToDiameterClassAdapter()
    out = adapter.adapt(stand)
    assert out["dclass"]

    stand_no_trees = Stand(area_ha=1.0, plots=[])
    stand_no_trees._metric_estimates = {
        "BasalArea": {"TOTAL": StandBasalArea(12.0, species=None)},
        "Stems": {"TOTAL": Stems(600.0, species=None)},
    }
    dclass = TreeListToDiameterClassAdapter().adapt(stand_no_trees)
    assert "TOTAL" in dclass["dclass"]

    stand_tree_list = _tree_list_stand(with_positions=False)
    spatial_out = TreeListToSpatialAdapter().adapt(stand_tree_list, seed=5)
    assert all(t.position is not None for p in spatial_out["plots"] for t in p.trees)


def test_apply_mortality_rate_in_dclass_scales_totals():
    model = ExampleStandGeneralModel()
    ctx = model.build_context(_ac_stand(), mode_hint="diameter_class")
    n0 = float(ctx.metrics["Stems"]["TOTAL"])
    ctx.do("apply_mortality_rate", rate=0.25)
    n1 = float(ctx.metrics["Stems"]["TOTAL"])
    assert n1 == pytest.approx(n0 * (1.0 - 0.25))


def test_thin_fraction_tree_list_reduces_stems():
    model = ExampleStandGeneralModel()
    ctx = model.build_context(_tree_list_stand(with_positions=True), mode_hint="tree_list")
    n0 = float(ctx.metrics["Stems"]["TOTAL"])
    ctx.do("thin_fraction", fraction=0.5)
    n1 = float(ctx.metrics["Stems"]["TOTAL"])
    assert n1 == pytest.approx(n0 * 0.5, rel=1e-12)


def test_spatial_adapter_seed_makes_positions_deterministic():
    """Adapter should be deterministic for a given seed."""
    model = ExampleStandGeneralModel()
    st1 = _tree_list_stand(with_positions=False)
    st2 = _tree_list_stand(with_positions=False)
    ctx1 = model.build_context(st1, mode_hint="spatial", adapter_kwargs={"seed": 1234})
    ctx2 = model.build_context(st2, mode_hint="spatial", adapter_kwargs={"seed": 1234})

    def _xy_list(ctx):
        coords = []
        for p in ctx.plots:
            for t in p.trees:
                pos = getattr(t, "position", None)
                # Prove to the type checker and the test that position exists
                assert pos is not None, "expected a position on every tree in spatial mode"
                # Support both tuple-like (x, y) and attribute (.x, .y) forms
                try:
                    x, y = pos  # tuple-like
                except Exception:
                    x, y = pos.x, pos.y
                coords.append((float(x), float(y)))
        return coords

    pos1 = _xy_list(ctx1)
    pos2 = _xy_list(ctx2)
    assert pos1 == pos2


def test_ensemble_batch_engine_path_and_logging():
    """Exercise the ContextEnsemble batch path by advertising a batch engine."""

    class BatchyModel(ExampleStandGeneralModel):
        def has_batch_engine(self):  # <- makes agg_ctxs non-empty
            return True

        # vectorized step used by PythonEngine
        def batch_grow_step(self, ba, n, dt, fert_mask):
            growth = self.ba_rel + self.fert_boost * fert_mask  # fert_mask ∈ {0,1}
            new_ba = ba * (1.0 + growth * dt)
            new_n = n * (1.0 - self.mort * dt)
            return new_ba, new_n

    model = BatchyModel()
    ctxs = []
    for i in range(4):
        ctx = model.build_context(_tree_list_stand(), mode_hint="aggregate")
        ctx.set_aggregate_metrics(ba_total=20.0, stems_total=1000.0)
        # mark half as fertilized so fert_mask=1.0
        ctx.attrs["fertilized_remaining_years"] = 1.0 if i % 2 == 0 else 0.0
        ctxs.append(ctx)

    ens = ContextEnsemble(ctxs, model=model)
    ens.update_step(dt=1.0)

    # writeback happened and history was logged via _log_external_update("update_step", ...)
    for i, c in enumerate(ctxs):
        hist_ops = [h.op for h in c.history]
        assert "update_step" in hist_ops
        ba = float(c.metrics["BasalArea"]["TOTAL"])
        # fertilized contexts grew faster
        if i % 2 == 0:
            assert ba > 20.0 * (1.0 + model.ba_rel)  # got the +fert_boost
        else:
            assert ba == pytest.approx(20.0 * (1.0 + model.ba_rel))


def test_context_ensemble_engine_hint_selection():
    model = ExampleStandGeneralModel()
    ctx = model.build_context(_tree_list_stand(), mode_hint="aggregate")
    ens = ContextEnsemble([ctx], model=model, engine="numpy")
    assert isinstance(ens.engine, PythonEngine)
    with pytest.raises(ValueError):
        ContextEnsemble([ctx], model=model, engine="unknown_backend")


def test_ensemble_engine_helpers(monkeypatch):
    import builtins

    import numpy as np

    from pyforestry.base.simulation import ensemble as ens_mod

    class DummyEngine(ens_mod.BatchEngine):
        def grow(self, model, vec, dt, extra=None):  # type: ignore[override]
            return vec

    dummy = DummyEngine()
    assert ens_mod._engine_from_hint(dummy) is dummy
    assert isinstance(ens_mod._engine_from_hint("numpy"), ens_mod.PythonEngine)

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in {"numba", "jax"}:
            raise ImportError("blocked")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert ens_mod._optional_numba_engine() is None
    assert ens_mod._optional_jax_engine() is None
    assert isinstance(ens_mod._engine_from_hint("numba"), ens_mod.PythonEngine)
    assert isinstance(ens_mod._engine_from_hint("jax"), ens_mod.PythonEngine)

    with pytest.raises(ValueError):
        ens_mod._engine_from_hint("unknown")
    with pytest.raises(TypeError):
        ens_mod._engine_from_hint(123)
    with pytest.raises(NotImplementedError):
        ens_mod.BatchEngine().grow(
            object(),
            {"ba": np.array([1.0]), "n": np.array([2.0])},
            dt=1.0,
        )

    engine = ens_mod.PythonEngine()
    out = engine.grow(object(), {"ba": np.array([1.0]), "n": np.array([2.0])}, dt=1.0)
    assert float(out["ba"][0]) == 1.0
    assert float(out["n"][0]) == 2.0


def test_context_ensemble_steps_every_context_and_reports_one_table():
    model = ExampleStandGeneralModel()
    ctxs = []
    for _i in range(2):
        ctx = model.build_context(_tree_list_stand(), mode_hint="aggregate")
        ctx.set_aggregate_metrics(ba_total=12.0, stems_total=300.0)
        ctxs.append(ctx)

    ens = ContextEnsemble(ctxs, model=model)
    ens.update_step(dt=0.5)
    ens.update_step(dt=0.5)
    ens.do("fertilize", years=1.0)

    df = ens.to_pandas()
    assert "context_id" in df.columns


def test_parallel_runner_round_trip():
    model = ExampleStandGeneralModel()
    ctxs = []
    for i in range(3):
        ctx = model.build_context(_tree_list_stand(), mode_hint="aggregate")
        ctx.set_aggregate_metrics(ba_total=10.0 + i, stems_total=100.0 + i * 10.0)
        ctxs.append(ctx)

    ens = ContextEnsemble(ctxs, model=model)

    # Run two steps in parallel; should preserve order and update totals
    from pyforestry.simulation.services import run_parallel

    updated = run_parallel(ens, dt=1.0, steps=2, processes=1)
    assert len(updated) == len(ctxs)

    for original, restored in zip(ctxs, updated, strict=False):
        assert float(restored.metrics["BasalArea"]["TOTAL"]) > float(
            original.metrics["BasalArea"]["TOTAL"]
        )
        assert float(restored.metrics["Stems"]["TOTAL"]) < float(
            original.metrics["Stems"]["TOTAL"]
        )
    # ensemble contexts were replaced when write_back=True
    assert ens.contexts[0] is updated[0]


def test_parallel_runner_write_back_optional_and_dispatcher():
    model = ExampleStandGeneralModel()
    ctxs = []
    for _i in range(4):
        ctx = model.build_context(_tree_list_stand(), mode_hint="aggregate")
        ctx.set_aggregate_metrics(ba_total=10.0, stems_total=100.0)
        ctxs.append(ctx)

    def dispatcher(idx, _ctx):
        return idx % 2  # ensure deterministic grouping

    from pyforestry.simulation.services import run_parallel

    updated = run_parallel(
        ctxs,
        dt=0.5,
        steps=1,
        processes=2,
        write_back=False,
        dispatcher=dispatcher,
    )
    # Original list unchanged
    assert ctxs[0] is not updated[0]
    # Updated values reflect growth
    assert float(updated[0].metrics["BasalArea"]["TOTAL"]) > float(
        ctxs[0].metrics["BasalArea"]["TOTAL"]
    )


def test_parallel_runner_history_tail_preserved():
    model = ExampleStandGeneralModel()
    ctx = model.build_context(_tree_list_stand(), mode_hint="aggregate")
    ctx.set_aggregate_metrics(ba_total=10.0, stems_total=100.0)
    from pyforestry.simulation.services import run_parallel

    updated = run_parallel(
        [ctx],
        dt=1.0,
        steps=1,
        write_back=False,
        include_history=True,
        history_tail=1,
    )
    assert len(updated[0].history) == 1


def test_parallel_runner_raises_on_error():
    class FailingModel(ExampleStandGeneralModel):
        def update_step(self, ctx, dt):  # type: ignore[override]
            raise RuntimeError("boom")

    model = FailingModel()
    ctx = model.build_context(_tree_list_stand(), mode_hint="aggregate")
    from pyforestry.simulation.services import run_parallel

    with pytest.raises(RuntimeError, match="Parallel simulation failed"):
        run_parallel([ctx], dt=1.0)


def test_parallel_runner_empty_contexts_returns_empty():
    from pyforestry.simulation.services import run_parallel

    assert run_parallel([], dt=1.0) == []


def test_parallel_runner_missing_model_raises():
    class NoModel:
        pass

    from pyforestry.simulation.services import run_parallel

    with pytest.raises(ValueError, match="model"):
        run_parallel([NoModel()], dt=1.0)


def test_parallel_runner_pool_branch(monkeypatch):
    import pyforestry.simulation.services.parallel_runner as pr
    from pyforestry.simulation.services import run_parallel

    class DummyPool:
        def __init__(self, processes):
            self.processes = processes

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starmap(self, fn, iterable):
            return [fn(*args) for args in iterable]

    monkeypatch.setattr(pr.mp, "Pool", DummyPool)

    model = ExampleStandGeneralModel()
    ctxs = []
    for _i in range(2):
        ctx = model.build_context(_tree_list_stand(), mode_hint="aggregate")
        ctx.set_aggregate_metrics(ba_total=10.0, stems_total=100.0)
        ctxs.append(ctx)

    updated = run_parallel(
        ctxs,
        dt=0.5,
        steps=1,
        processes=2,
        write_back=False,
    )
    assert len(updated) == len(ctxs)


def test_parallel_runner_telemetry_sink(monkeypatch):
    import pyforestry.simulation.services.parallel_runner as pr
    from pyforestry.simulation.services import run_parallel

    original = pr.SimulationContext.from_checkpoint

    def patched(cls, model, checkpoint):
        ctx = original(model, checkpoint)
        ctx.telemetry = SimpleNamespace(events=[{"event": "ok"}])
        return ctx

    monkeypatch.setattr(pr.SimulationContext, "from_checkpoint", classmethod(patched))

    model = ExampleStandGeneralModel()
    ctx = model.build_context(_tree_list_stand(), mode_hint="aggregate")
    ctx.set_aggregate_metrics(ba_total=10.0, stems_total=100.0)

    collected = []

    def sink(idx, events):
        collected.append((idx, events))

    run_parallel([ctx], dt=1.0, steps=1, write_back=False, telemetry_sink=sink)
    assert collected == [(0, [{"event": "ok"}])]


def test_adapter_draws_come_from_the_run_seed_not_a_hard_coded_one():
    """A stochastic adapter is part of the run, so the run's seed must reach it.

    ``build_context`` acquired the inventory before it opened the run's
    ``RandomBundle``, so an angle-count stand converted to ``spatial`` got its
    pseudo-positions from ``_adapter_rng``'s hard-coded fallback: every seed gave
    the same coordinates, and the draws sat outside the bundle a checkpoint
    captures. ``_adapter_rng``'s docstring already named ``ctx.rng.child(...)`` as
    the thing to pass; nothing passed it.
    """
    model = ExampleStandGeneralModel()

    def positions(**kwargs):
        ctx = model.build_context(_ac_stand(), mode_hint="spatial", **kwargs)
        return [
            (round(t.position.X, 9), round(t.position.Y, 9))
            for plot in ctx.stand.plots
            for t in plot.trees
            if getattr(t, "position", None) is not None
        ]

    assert positions(seed=11), "expected the adapter to place trees"
    assert positions(seed=11) != positions(seed=99)
    # Seedless construction stays reproducible, and an explicit adapter seed still
    # pins the coordinates -- injecting an rng beside it would silently ignore it,
    # because _adapter_rng prefers rng over seed.
    assert positions() == positions()
    assert positions(seed=11, adapter_kwargs={"seed": 42}) == positions(
        seed=99, adapter_kwargs={"seed": 42}
    )
