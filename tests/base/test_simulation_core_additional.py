from __future__ import annotations

import types

import numpy as np
import pytest

from pyforestry.base.helpers import PICEA_ABIES, AngleCount, CircularPlot, Stand, Tree
from pyforestry.base.helpers.primitives import StandBasalArea, Stems
from pyforestry.base.simulation.adapters import Adapter, AdapterRegistry
from pyforestry.base.simulation.core import ActionSpec, SimulationContext
from pyforestry.base.simulation.ensemble import (
    BatchEngine,
    ContextEnsemble,
    PythonEngine,
    _engine_from_hint,
    _optional_jax_engine,
    _optional_numba_engine,
)
from pyforestry.base.simulation.growth_model import (
    ExampleStandGeneralModel,
    GrowthModel,
    Requirements,
)


def _ac_stand():
    # Diameters are supplied so stems/ha (and hence QMD) are derivable, which the
    # angle-count adapters need.
    ac1 = AngleCount(
        ba_factor=2.0, value=[10], species=[PICEA_ABIES], point_id="p1", diameters_cm=[[20.0] * 10]
    )
    plot = CircularPlot(id=1, area_m2=200.0, AngleCount=[ac1])
    return Stand(area_ha=1.0, plots=[plot])


class DummyModel(GrowthModel):
    def requirements(self) -> Requirements:
        return Requirements(inventory="either")

    def update_step(self, ctx, dt):  # type: ignore[override]
        ctx.state["t"] = ctx.state.get("t", 0.0) + dt


def test_adapter_base_methods_raise():
    adapter = Adapter()
    with pytest.raises(NotImplementedError):
        adapter.can_adapt(None)
    with pytest.raises(NotImplementedError):
        adapter.adapt(None)


def test_optional_engines(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "numba", types.SimpleNamespace())
    monkeypatch.setitem(__import__("sys").modules, "jax", types.SimpleNamespace())
    assert isinstance(_optional_numba_engine(), PythonEngine)
    assert isinstance(_optional_jax_engine(), PythonEngine)
    assert isinstance(_engine_from_hint("numba"), PythonEngine)
    assert isinstance(_engine_from_hint("jax"), PythonEngine)


def test_optional_engines_import_fail(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in ("numba", "jax"):
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert _optional_numba_engine() is None
    assert _optional_jax_engine() is None


def test_growth_model_can_build_modes():
    model = DummyModel()
    stand = Stand(
        area_ha=1.0,
        plots=[CircularPlot(id=1, area_m2=200.0, trees=[Tree(species="Picea abies")])],
    )
    ok, missing = model.can_build(stand, allow_adapters=False, mode_hint="spatial")
    assert not ok
    assert any("spatial" in item for item in missing)

    stand_pos = Stand(
        area_ha=1.0,
        plots=[
            CircularPlot(
                id=2,
                area_m2=200.0,
                trees=[Tree(species="Picea abies", position=(1.0, 2.0))],
            )
        ],
    )
    ok, missing = model.can_build(stand_pos, allow_adapters=False, mode_hint="spatial")
    assert ok
    assert missing == []

    class FakeStand:
        use_angle_count = False
        plots = []
        site = None

        def get_dominant_height(self):  # noqa: D401 - test helper
            return None

        @property
        def BasalArea(self):
            raise RuntimeError("no BA")

        @property
        def Stems(self):
            raise RuntimeError("no stems")

    ok, missing = model.can_build(FakeStand(), allow_adapters=False, mode_hint="diameter_class")
    assert not ok
    assert any("diameter_class" in item for item in missing)

    fake_ac = FakeStand()
    fake_ac.use_angle_count = True
    ok, missing = model.can_build(fake_ac, allow_adapters=False, mode_hint="tree_list")
    assert not ok
    assert "tree_list" in missing

    stand_angle = _ac_stand()
    ok, missing = model.can_build(stand_angle, allow_adapters=True, mode_hint="tree_list")
    assert ok
    assert missing == []

    fake_any = FakeStand()
    ok, missing = model.can_build(fake_any, allow_adapters=False)
    assert not ok
    assert any("tree_list or aggregates" in item for item in missing)


def test_growth_model_base_methods_raise():
    model = GrowthModel()
    with pytest.raises(NotImplementedError):
        model.requirements()
    with pytest.raises(NotImplementedError):
        model.update_step(None, 1.0)
    assert model.available_actions() == {}


def test_build_context_angle_count_fallback(monkeypatch):
    model = ExampleStandGeneralModel()
    stand = _ac_stand()

    class DummyRegistry:
        def get(self, name):  # noqa: ARG002 - test helper
            return None

    monkeypatch.setattr(AdapterRegistry, "default", lambda: DummyRegistry())
    ctx = model.build_context(stand, mode_hint="tree_list")
    assert ctx.mode == "aggregate"


def test_build_context_spatial_missing_adapter(monkeypatch):
    model = ExampleStandGeneralModel()
    stand = Stand(
        area_ha=1.0,
        plots=[
            CircularPlot(
                id=1, area_m2=200.0, trees=[Tree(species="Picea abies", diameter_cm=10.0)]
            )
        ],
    )

    class DummyRegistry:
        def get(self, name):  # noqa: ARG002 - test helper
            return None

    monkeypatch.setattr(AdapterRegistry, "default", lambda: DummyRegistry())
    ctx = model.build_context(stand, mode_hint="spatial")
    assert ctx.mode == "tree_list"


def test_build_context_diameter_class_fallback():
    model = ExampleStandGeneralModel()
    stand = Stand(area_ha=1.0, plots=[])
    stand._metric_estimates = {
        "BasalArea": {"TOTAL": StandBasalArea(12.0, species=None)},
        "Stems": {"TOTAL": Stems(600.0, species=None)},
    }
    ctx = model.build_context(stand, mode_hint="diameter_class")
    assert ctx.mode == "diameter_class"
    assert ctx.diameter_classes["TOTAL"]["bin_mids_cm"]


def test_build_context_angle_count_origin():
    model = ExampleStandGeneralModel()
    stand = _ac_stand()
    ctx = model.build_context(stand, mode_hint="tree_list")
    assert ctx.attrs["inventory_origin"] == "angle_count_pseudo_tree_list"


def test_build_context_use_adapter_path():
    model = ExampleStandGeneralModel()
    stand = _ac_stand()
    ctx = model.build_context(
        stand, mode_hint="tree_list", use_adapter="angle_count_pseudo_tree_list"
    )
    assert ctx.mode == "tree_list"


def test_build_context_mode_selection_default():
    model = ExampleStandGeneralModel()
    stand = Stand(area_ha=1.0, plots=[])
    ctx = model.build_context(stand)
    assert ctx.mode == "aggregate"


def test_build_context_angle_count_default_mode():
    model = ExampleStandGeneralModel()
    stand = _ac_stand()
    ctx = model.build_context(stand)
    assert ctx.mode == "aggregate"


def test_build_context_uses_requirements_inventory():
    class SpatialModel(DummyModel):
        def requirements(self) -> Requirements:
            return Requirements(inventory="spatial")

    model = SpatialModel()
    stand = Stand(
        area_ha=1.0,
        plots=[
            CircularPlot(
                id=1,
                area_m2=200.0,
                trees=[Tree(species="Picea abies", position=(1.0, 2.0))],
            )
        ],
    )
    ctx = model.build_context(stand)
    assert ctx.mode == "spatial"


def test_simulation_context_action_gating_and_phases():
    model = DummyModel()
    metrics = {
        "BasalArea": {"TOTAL": StandBasalArea(10.0, species=None)},
        "Stems": {"TOTAL": Stems(100.0, species=None)},
    }
    ctx = SimulationContext(
        mode="aggregate",
        area_ha=1.0,
        site=None,
        origin_ref=None,
        inventory={"metrics": metrics},
        initial_state={},
        model=model,
        initial_attrs={},
    )

    def noop(context):  # noqa: ARG001 - test helper
        return None

    def available():
        return {
            "only_tree": ActionSpec(
                name="only_tree",
                description="",
                fn=noop,
                params={},
                requires_modes=["tree_list"],
            ),
            "phase_ok": ActionSpec(
                name="phase_ok",
                description="",
                fn=noop,
                params={},
                allowed_phases=["pre"],
            ),
            "legacy_tree": ActionSpec(
                name="legacy_tree",
                description="",
                fn=noop,
                params={},
                requires_tree_list=True,
            ),
        }

    model.available_actions = available  # type: ignore[assignment]

    with pytest.raises(KeyError):
        ctx.do("missing")
    with pytest.raises(RuntimeError, match="requires mode"):
        ctx.do("only_tree")
    with pytest.raises(RuntimeError, match="not permitted"):
        ctx.do("phase_ok", phase="post")
    with pytest.raises(RuntimeError, match="requires mode"):
        ctx.do("legacy_tree")


def test_simulation_context_invalid_mode():
    with pytest.raises(ValueError):
        SimulationContext(
            mode="invalid",
            area_ha=1.0,
            site=None,
            origin_ref=None,
            inventory={"metrics": {}},
            initial_state={},
            model=DummyModel(),
            initial_attrs={},
        )


def test_simulation_context_management_tuple_and_scale_stems():
    model = DummyModel()
    metrics = {
        "BasalArea": {"TOTAL": StandBasalArea(10.0, species=None)},
        "Stems": {"TOTAL": Stems(100.0, species=None)},
    }
    ctx = SimulationContext(
        mode="aggregate",
        area_ha=1.0,
        site=None,
        origin_ref=None,
        inventory={"metrics": metrics},
        initial_state={},
        model=model,
        initial_attrs={},
    )

    def noop(context):  # noqa: ARG001 - test helper
        return None

    model.available_actions = lambda: {  # type: ignore[assignment]
        "noop": ActionSpec(name="noop", description="", fn=noop, params={})
    }
    ctx.update_step(1.0, management={"pre": [("noop", {})], "post": ["noop"]})
    ctx.scale_stems(0.5)
    assert float(ctx.metrics["Stems"]["TOTAL"]) == pytest.approx(50.0)


def test_simulation_context_metrics_come_from_its_stand():
    """A tree-list context reports exactly what its stand reports.

    The context used to carry a second estimator, and this test covered its edge
    paths. There is only one estimator now, so the property worth asserting is
    that the context is a view of the stand rather than a parallel calculation.
    """
    model = DummyModel()
    plot = CircularPlot(
        id=1,
        area_m2=200.0,
        trees=[
            Tree(species=None, diameter_cm=10.0),
            Tree(species="Picea abies", diameter_cm=20.0, weight_n=2.0),
        ],
    )
    ctx = SimulationContext(
        mode="tree_list",
        area_ha=1.0,
        site=None,
        origin_ref=None,
        inventory={"plots": [plot]},
        initial_state={},
        model=model,
        initial_attrs={},
    )
    assert "TOTAL" in ctx.metrics["Stems"]
    assert float(ctx.metrics["Stems"]["TOTAL"]) == pytest.approx(float(ctx.stand.Stems))
    assert float(ctx.metrics["BasalArea"]["TOTAL"]) == pytest.approx(float(ctx.stand.BasalArea))
    assert float(ctx.metrics["QMD"]["TOTAL"]) == pytest.approx(float(ctx.stand.QMD))


def test_simulation_context_qmd_is_zero_without_measurable_trees():
    """A stand of trees with no diameters has no QMD to report, not a crash."""
    model = DummyModel()
    empty_plot = CircularPlot(id=2, area_m2=200.0, trees=[Tree(species=None)])
    ctx = SimulationContext(
        mode="tree_list",
        area_ha=1.0,
        site=None,
        origin_ref=None,
        inventory={"plots": [empty_plot]},
        initial_state={},
        model=model,
        initial_attrs={},
    )
    assert float(ctx.metrics["QMD"]["TOTAL"]) == 0.0


def test_simulation_context_checkpoint_dclass_and_rng_restore():
    model = DummyModel()
    ctx = SimulationContext(
        mode="diameter_class",
        area_ha=1.0,
        site=None,
        origin_ref=None,
        inventory={"dclass": {"TOTAL": {"bin_mids_cm": [], "n_per_ha": []}}},
        initial_state={},
        model=model,
        initial_attrs={},
    )

    class Bundle:
        """A minimal snapshot/restore bundle."""

        def __init__(self):
            self.state = {"draws": 3}
            self.restored = None

        def snapshot(self):
            return dict(self.state)

        def restore(self, state):
            self.restored = state

    # A round trip must actually carry the RNG state across. This used to be dead:
    # checkpoint() stored rng_state, but from_checkpoint() guarded on
    # hasattr(ctx, "random_bundle") -- which the constructor never set -- so the
    # state was silently dropped and a resumed stochastic run diverged in silence.
    bundle = Bundle()
    ctx.random_bundle = bundle
    ctx.history.append(object())
    payload = ctx.checkpoint(include_history=True)
    assert payload["rng_state"] == {"draws": 3}

    target = Bundle()
    restored = SimulationContext.from_checkpoint(model, payload, random_bundle=target)
    assert target.restored == {"draws": 3}
    assert restored.random_bundle is target

    # Resuming a stochastic checkpoint with nowhere to put the state is an error,
    # not a quiet fresh stream.
    with pytest.raises(ValueError, match="no random_bundle was supplied"):
        SimulationContext.from_checkpoint(model, payload)

    # A checkpoint without RNG state restores fine without a bundle.
    ctx.random_bundle = None
    plain = ctx.checkpoint()
    assert "rng_state" not in plain
    assert SimulationContext.from_checkpoint(model, plain).random_bundle is None


def test_simulation_context_dclass_qmd_zero():
    model = DummyModel()
    ctx = SimulationContext(
        mode="diameter_class",
        area_ha=1.0,
        site=None,
        origin_ref=None,
        inventory={"dclass": {"TOTAL": {"bin_mids_cm": [], "n_per_ha": []}}},
        initial_state={},
        model=model,
        initial_attrs={},
    )
    assert float(ctx.metrics["QMD"]["TOTAL"]) == 0.0


def test_example_model_action_branches():
    model = ExampleStandGeneralModel()
    stand = Stand(area_ha=1.0, plots=[])
    stand._metric_estimates = {
        "BasalArea": {"TOTAL": StandBasalArea(10.0, species=None)},
        "Stems": {"TOTAL": Stems(100.0, species=None)},
    }
    ctx = model.build_context(stand, mode_hint="aggregate")
    with pytest.raises(ValueError):
        ctx.do("apply_mortality_rate", rate=-0.1)
    ctx.do("apply_mortality_rate", rate=0.1)
    with pytest.raises(RuntimeError):
        model._act_thin_smallest_classes(ctx, 0.1)
    with pytest.raises(RuntimeError):
        ctx.do("thin_smallest_classes", fraction=0.2)

    stand_tree = Stand(
        area_ha=1.0,
        plots=[CircularPlot(id=1, area_m2=200.0, trees=[Tree(species="Picea abies")])],
    )
    ctx_tree = model.build_context(stand_tree, mode_hint="tree_list")
    ctx_tree.plots[0].trees[0].weight_n = None
    ctx_tree.do("apply_mortality_rate", rate=0.1)
    with pytest.raises(ValueError):
        ctx_tree.do("thin_fraction", fraction=1.0)

    stand_empty = Stand(area_ha=1.0, plots=[CircularPlot(id=2, area_m2=200.0, trees=[])])
    ctx_empty = model.build_context(stand_empty, mode_hint="tree_list")
    ctx_empty.do("thin_fraction", fraction=0.5)

    ctx_dclass = model.build_context(_ac_stand(), mode_hint="diameter_class")
    with pytest.raises(ValueError):
        ctx_dclass.do("thin_smallest_classes", fraction=1.0)
    ctx_dclass.do("thin_smallest_classes", fraction=0.1)
    model.update_step(ctx_dclass, 1.0)

    ctx_custom = SimulationContext(
        mode="diameter_class",
        area_ha=1.0,
        site=None,
        origin_ref=None,
        inventory={"dclass": {"TOTAL": {"bin_mids_cm": [10.0, 20.0], "n_per_ha": [50.0, 50.0]}}},
        initial_state={},
        model=model,
        initial_attrs={},
    )
    model._act_thin_smallest_classes(ctx_custom, 0.1)


def test_context_ensemble_engine_paths():
    model = ExampleStandGeneralModel()
    stand = Stand(area_ha=1.0, plots=[])
    stand._metric_estimates = {
        "BasalArea": {"TOTAL": StandBasalArea(10.0, species=None)},
        "Stems": {"TOTAL": Stems(100.0, species=None)},
    }
    ctx = model.build_context(stand, mode_hint="aggregate")

    ens = ContextEnsemble([ctx], model=model)
    ens.engine = None
    with pytest.raises(RuntimeError):
        ens.update_step(1.0)

    ens.engine = PythonEngine()
    ens.update_step(1.0, management={"pre": []})
    ens.do("fertilize", years=1.0)
    df = ens.to_pandas()
    assert "context_id" in df.columns
    with pytest.raises(ValueError):
        ens.update_step(1.0, management=[None, None])


def test_batch_engine_not_implemented():
    engine = BatchEngine()
    with pytest.raises(NotImplementedError):
        engine.grow(None, {}, 1.0)


def test_python_engine_without_batch_step():
    engine = PythonEngine()
    out = engine.grow(object(), {"ba": np.array([1.0]), "n": np.array([2.0])}, 1.0)
    assert "ba" in out and "n" in out


def test_adapter_branch_coverage():
    stand = Stand(area_ha=1.0, plots=[])
    assert not AdapterRegistry().get("missing")

    adapter = AdapterRegistry().get("angle_count_pseudo_tree_list")
    assert adapter is not None
    assert adapter.can_adapt(stand) is False

    stand_angle = _ac_stand()
    species_key = next(
        key for key in stand_angle._metric_estimates["BasalArea"].keys() if key != "TOTAL"
    )
    stand_angle._metric_estimates["Stems"][species_key] = Stems(0.0, species=species_key)
    out = adapter.adapt(stand_angle, replicas_per_species=1)
    plot = out["plots"][0]
    assert plot.trees

    dclass_adapter = AdapterRegistry().get("angle_count_to_diameter_class")
    assert dclass_adapter is not None
    stand_angle._metric_estimates["Stems"][species_key] = Stems(0.0, species=species_key)
    dclass = dclass_adapter.adapt(stand_angle)
    assert dclass["dclass"]

    tree_adapter = AdapterRegistry().get("tree_list_to_diameter_class")
    assert tree_adapter is not None
    stand_tree = Stand(
        area_ha=1.0,
        plots=[
            CircularPlot(id=1, area_m2=200.0, trees=[Tree(species="Picea abies")]),
        ],
    )
    stand_tree.plots[0].trees[0].diameter_cm = None
    assert tree_adapter.can_adapt(stand_tree) is True
    out = tree_adapter.adapt(stand_tree)
    assert out["dclass"]
