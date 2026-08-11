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

        def update_step(self, dt):
            delta = 0.0
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

    # Restoring sys.modules is not enough: the reload below binds DummyContext
    # into the runner's own namespace, and nothing puts the real one back. Undone
    # by hand, in this order, because monkeypatch's teardown runs after the test
    # body and would restore sys.modules only once the reload had already taken.
    parallel = importlib.import_module("pyforestry.simulation.services.parallel_runner")
    original = sys.modules["pyforestry.base.simulation"]
    sys.modules["pyforestry.base.simulation"] = fake_module
    try:
        importlib.reload(parallel)

        model = DummyModel()
        contexts = [DummyContext(model, 0.0), DummyContext(model, 1.5)]
        results = parallel.run_parallel(contexts, dt=1.0, steps=2, processes=1)

        assert [ctx.value for ctx in results] == [2.0, 3.5]
    finally:
        sys.modules["pyforestry.base.simulation"] = original
        importlib.reload(parallel)


def test_the_stub_test_above_puts_the_real_context_back():
    """It reloads the runner against a fake module; the fake must not outlive it.

    It did: every later test in this file ran against ``DummyContext``, so the
    one that checks a seeded context survives the worker boundary passed alone
    and failed in the file.
    """
    from pyforestry.base.simulation import SimulationContext
    from pyforestry.simulation.services import parallel_runner

    assert parallel_runner.SimulationContext is SimulationContext


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


def test_run_parallel_telemetry(monkeypatch):
    from pyforestry.simulation.services import parallel_runner

    class DummyCtx:
        def __init__(self):
            self.telemetry = types.SimpleNamespace(events=["evt"])

        def update_step(self, dt):  # noqa: ARG002
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
        telemetry_sink=sink,
    )
    assert out
    assert events


def test_a_seeded_context_survives_the_worker_boundary():
    """The run's keyed RNG and the parallel runner used to rule each other out.

    ``build_context(..., seed=N)`` gives a context a ``RandomBundle``; its
    checkpoint then carries ``rng_state``; and the worker restored that
    checkpoint with no bundle to put it in, which ``from_checkpoint`` refuses --
    correctly, since resuming on a fresh stream would diverge in silence. So
    every seeded context raised ``Parallel simulation failed for context 0``, and
    every test here built its contexts unseeded.

    A checkpoint now records the bundle's root seed as well as its per-stream
    states, so it can rebuild an equivalent bundle where no caller can hand one
    over.
    """
    from pyforestry.simulation.services import run_parallel

    stand = Stand(
        area_ha=1.0,
        plots=[CircularPlot(id=1, area_m2=200.0, trees=[Tree(species="Picea abies")])],
    )
    model = ExampleStandGeneralModel()
    ctx = model.build_context(stand, mode_hint="aggregate", seed=42)

    restored = run_parallel([ctx], dt=0.5, steps=1, processes=1)

    assert len(restored) == 1
    assert restored[0].random_bundle is not None
    # The same stream, not a fresh one: both draw the same next number.
    assert restored[0].rng.child("mortality").random() == ctx.rng.child("mortality").random()


def test_a_checkpoint_that_cannot_restore_its_rng_still_refuses():
    """Only a checkpoint carrying the seed can rebuild the bundle itself."""
    from pyforestry.base.simulation.core import SimulationContext

    stand = Stand(
        area_ha=1.0,
        plots=[CircularPlot(id=1, area_m2=200.0, trees=[Tree(species="Picea abies")])],
    )
    model = ExampleStandGeneralModel()
    checkpoint = model.build_context(stand, mode_hint="aggregate", seed=42).checkpoint()
    checkpoint.pop("rng_seed")

    with pytest.raises(ValueError, match="no random_bundle was supplied"):
        SimulationContext.from_checkpoint(model, checkpoint)
