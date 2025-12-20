from __future__ import annotations

from pyforestry.simulation.services import RandomBundle, TelemetryPublisher


def test_keyed_rng_helpers():
    bundle = RandomBundle(42)
    rng = bundle.rng_for("a")
    _ = rng.randint(1, 3)
    _ = rng.uniform(0.0, 1.0)
    child = rng.child(["b", "c"])
    assert child.path[-2:] == ("b", "c")

    state = rng.state
    rng.jumpahead(2)
    rng.state = state


def test_telemetry_publisher_sink_and_clear():
    events = []

    def sink(event):
        events.append(event)

    telemetry = TelemetryPublisher(model_id=None, seed=7, sink=sink)
    telemetry.publish("test.event", {"payload": 1})
    assert events
    assert telemetry.events[0].payload["metadata"]["seed"] == 7
    telemetry.clear()
    assert telemetry.events == []
