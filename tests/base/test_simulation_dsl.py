from pyforestry.base.simulation.dsl import ScheduledOp, SimulationSetup, TriggerSpec


class DummyContext:
    def __init__(self):
        self.state = {"t": 0.0, "counter": 0}
        self.history = []

    def update_step(self, dt):
        self.state["t"] += dt

    def snapshot(self):
        return dict(self.state)

    def _append_history(self, op, meta, pre, post):
        self.history.append({"op": op, "meta": meta, "pre": pre, "post": post})


def test_simulation_setup_runs_triggers_and_schedule():
    ctx = DummyContext()

    def pre_action(context):
        context.state["counter"] += 1

    def post_action(context):
        context.state["counter"] += 10

    def scheduled_action(context):
        context.state["counter"] += 100

    setup = SimulationSetup(
        start_t=0.0,
        end_t=2.0,
        dt=1.0,
        triggers=[
            TriggerSpec(
                name="pre_once",
                check_phase="pre",
                predicate=lambda c: c.state["t"] >= 0.0,
                action=pre_action,
                once=True,
            ),
            TriggerSpec(
                name="post_each",
                check_phase="post",
                predicate=lambda c: c.state["t"] >= 1.0,
                action=post_action,
            ),
        ],
        schedule=[
            ScheduledOp(name="mid_step", t=1.0, fn=scheduled_action),
        ],
    )

    setup.run(ctx)

    assert ctx.state["t"] == 2.0
    assert ctx.state["counter"] == 121
    ops = [entry["op"] for entry in ctx.history]
    assert ops.count("trigger_fired") == 3
    assert ops.count("scheduled_op") == 1


def test_trigger_error_is_recorded():
    ctx = DummyContext()

    def bad_predicate(_):
        raise RuntimeError("boom")

    setup = SimulationSetup(
        start_t=0.0,
        end_t=1.0,
        dt=1.0,
        triggers=[
            TriggerSpec(
                name="bad",
                check_phase="pre",
                predicate=bad_predicate,
                action=lambda _: None,
            )
        ],
    )

    setup._eval_triggers(ctx, phase="pre")
    assert ctx.history
    assert ctx.history[0]["op"] == "trigger_error"
