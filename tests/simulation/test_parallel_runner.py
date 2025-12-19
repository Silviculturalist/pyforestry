import importlib
import sys
import types


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
    setattr(fake_module, "SimulationContext", DummyContext)
    setattr(fake_module, "ContextEnsemble", DummyEnsemble)
    monkeypatch.setitem(sys.modules, "pyforestry.base.simulation", fake_module)

    parallel = importlib.import_module("pyforestry.simulation.services.parallel_runner")
    importlib.reload(parallel)

    model = DummyModel()
    contexts = [DummyContext(model, 0.0), DummyContext(model, 1.5)]
    results = parallel.run_parallel(contexts, dt=1.0, steps=2, processes=1)

    assert [ctx.value for ctx in results] == [2.0, 3.5]
