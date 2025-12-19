import importlib
import sys
import types

import pytest

from pyforestry.base.helpers import CircularPlot, Stand, Tree
from pyforestry.base.simulation import ExampleStandGeneralModel


def test_parallel_runner_with_stub_context(monkeypatch):
    class DummyModel:
        pass

    class DummyContext:
        def __init__(self, model, value):
            self.model = model
            self.value = float(value)
            self.history = []
            self.telemetry = None

        def update_step(self, dt, management=None):
            delta = management.get("delta", 0.0) if management else 0.0
            self.value += dt + delta
            self.history.append(self.value)

        def checkpoint(self, include_history=False, history_tail=None):
            payload = {"value": self.value}
            if include_history:
                if history_tail is None:
                    payload["history"] = list(self.history)
                else:
                    payload["history"] = list(self.history[-history_tail:])
            return payload

        @classmethod
        def from_checkpoint(cls, model, checkpoint):
            ctx = cls(model, checkpoint.get("value", 0.0))
            ctx.history = list(checkpoint.get("history", []))
            return ctx

    class DummyEnsemble:
        def __init__(self, contexts):
            self.contexts = list(contexts)

    fake_module = types.ModuleType("pyforestry.base.simulation")
    fake_module.SimulationContext = DummyContext
    fake_module.ContextEnsemble = DummyEnsemble
    monkeypatch.setitem(sys.modules, "pyforestry.base.simulation", fake_module)

    parallel = importlib.import_module("pyforestry.simulation.services.parallel_runner")
    importlib.reload(parallel)

    model = DummyModel()
    contexts = [DummyContext(model, 0.0), DummyContext(model, 1.5)]
    results = parallel.run_parallel(contexts, dt=1.0, steps=2, processes=1)

    assert [ctx.value for ctx in results] == [2.0, 3.5]


def test_parallel_runner_pool_path(monkeypatch):
    from pyforestry.simulation.services import parallel_runner as parallel

    class DummyPool:
        def __init__(self, processes):
            self.processes = processes

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starmap(self, fn, args):
            return [fn(*item) for item in args]

    monkeypatch.setattr(parallel.mp, "Pool", DummyPool)

    model = ExampleStandGeneralModel()
    stand = Stand(
        area_ha=1.0,
        plots=[CircularPlot(id=1, area_m2=200.0, trees=[Tree(species="Picea abies")])],
    )
    ctxs = [model.build_context(stand, mode_hint="aggregate") for _ in range(2)]
    updated = parallel.run_parallel(ctxs, dt=0.5, steps=1, processes=2)
    assert len(updated) == 2


def test_run_parallel_empty_and_missing_model():
    from pyforestry.simulation.services import run_parallel

    assert run_parallel([], dt=1.0) == []

    class NoModel:
        pass

    with pytest.raises(ValueError):
        run_parallel([NoModel()], dt=1.0)


def test_run_parallel_management_and_telemetry(monkeypatch):
    from pyforestry.simulation.services import parallel_runner

    class DummyCtx:
        def __init__(self):
            self.telemetry = types.SimpleNamespace(events=["evt"])

        def update_step(self, dt, management=None):  # noqa: ARG002
            return None

        def checkpoint(self, include_history=False, history_tail=None):  # noqa: ARG002
            return {}

    class DummyOriginal:
        def __init__(self, model):
            self.model = model

        def checkpoint(self, include_history=False, history_tail=None):  # noqa: ARG002
            return {}

    monkeypatch.setattr(
        parallel_runner.SimulationContext, "from_checkpoint", lambda model, cp: DummyCtx()
    )

    events = []

    def sink(idx, payload):  # noqa: ARG001
        events.append(payload)

    ctxs = [DummyOriginal(object())]
    out = parallel_runner.run_parallel(
        ctxs,
        dt=1.0,
        steps=1,
        processes=1,
        management=[{"x": 1}],
        telemetry_sink=sink,
    )
    assert out
    assert events
