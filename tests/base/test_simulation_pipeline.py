"""The one scheduler: an ordered pipeline of steps over the whole stand.

Replaces the tests for ``SimulationSetup``/``TriggerSpec``/``ScheduledOp``. The
capabilities they covered -- fire on a condition, fire once, fire at a scheduled
time -- are all here, expressed as policies. What is *not* preserved is the
silent swallowing of a broken trigger, which has its own test below.
"""

import pytest

from pyforestry.base.helpers import CircularPlot, Stand, Tree
from pyforestry.base.simulation import (
    Action,
    ActionSpec,
    GrowthStep,
    ManagementStep,
    at_times,
    combine,
    run_pipeline,
    when,
)
from pyforestry.base.simulation.growth_model import ExampleStandGeneralModel


class _CountingModel(ExampleStandGeneralModel):
    """A model that only counts its own steps, so a test can see the ordering."""

    def update_step(self, ctx, dt):
        ctx.state["steps"] = ctx.state.get("steps", 0) + 1
        ctx.state["grown_years"] = ctx.state.get("grown_years", 0.0) + dt

    def available_actions(self):
        return {
            "bump": ActionSpec(
                name="bump",
                description="Increment a counter, so a test can see an action land.",
                fn=lambda ctx, by=1: ctx.state.__setitem__(
                    "counter", ctx.state.get("counter", 0) + by
                ),
                requires_modes=[],
            )
        }


def _ctx(model=None):
    model = model or _CountingModel()
    stand = Stand(
        area_ha=1.0,
        plots=[
            CircularPlot(
                id=1,
                area_m2=10_000.0,
                trees=[Tree(species="Picea abies", diameter_cm=20.0)],
            )
        ],
    )
    ctx = model.build_context(stand, mode_hint="tree_list")
    ctx.state["counter"] = 0
    return ctx


# ---------------------------------------------------------------------------
# The clock
# ---------------------------------------------------------------------------


def test_run_pipeline_advances_the_clock_by_whole_periods():
    ctx = _ctx()
    run_pipeline(ctx, (GrowthStep(),), years=10.0, step=5.0)
    assert ctx.state["t"] == pytest.approx(10.0)
    assert ctx.state["steps"] == 2


def test_a_trailing_remainder_runs_at_its_true_length():
    """Not rounded up to a whole step: a model that scales linearly with dt
    would otherwise grow the stand for years that did not happen."""
    ctx = _ctx()
    run_pipeline(ctx, (GrowthStep(),), years=12.0, step=5.0)
    assert ctx.state["t"] == pytest.approx(12.0)
    assert ctx.state["steps"] == 3
    assert ctx.state["grown_years"] == pytest.approx(12.0)
    assert ctx.state["last_dt"] == pytest.approx(2.0)


def test_run_pipeline_continues_from_the_contexts_own_clock():
    ctx = _ctx()
    run_pipeline(ctx, (GrowthStep(),), years=5.0, step=5.0)
    run_pipeline(ctx, (GrowthStep(),), years=5.0, step=5.0)
    assert ctx.state["t"] == pytest.approx(10.0)


def test_zero_years_runs_nothing():
    ctx = _ctx()
    run_pipeline(ctx, (GrowthStep(),), years=0.0, step=5.0)
    assert ctx.state.get("steps", 0) == 0


@pytest.mark.parametrize(
    ("years", "step", "match"),
    [(10.0, 0.0, "step must be positive"), (-1.0, 5.0, "years must not be negative")],
)
def test_run_pipeline_rejects_a_nonsense_clock(years, step, match):
    with pytest.raises(ValueError, match=match):
        run_pipeline(_ctx(), (GrowthStep(),), years=years, step=step)


# ---------------------------------------------------------------------------
# Policies: what triggers, schedules and rulesets all collapse into
# ---------------------------------------------------------------------------


def test_when_fires_on_every_step_the_predicate_holds():
    ctx = _ctx()
    policy = when(lambda c: c.state["t"] >= 5.0, Action(name="bump"))
    run_pipeline(ctx, (GrowthStep(), ManagementStep(policy)), years=15.0, step=5.0)
    # t is 5, 10, 15 after each growth step, so the predicate holds three times.
    assert ctx.state["counter"] == 3


def test_when_once_disarms_after_firing():
    ctx = _ctx()
    policy = when(lambda c: c.state["t"] >= 5.0, Action(name="bump"), once=True)
    run_pipeline(ctx, (GrowthStep(), ManagementStep(policy)), years=15.0, step=5.0)
    assert ctx.state["counter"] == 1


def test_at_times_fires_on_the_scheduled_clock_values():
    ctx = _ctx()
    policy = at_times([5.0, 15.0], Action(name="bump", params={"by": 10}))
    run_pipeline(ctx, (GrowthStep(), ManagementStep(policy)), years=20.0, step=5.0)
    assert ctx.state["counter"] == 20


def test_combine_runs_every_policy_in_order():
    ctx = _ctx()
    policy = combine(
        when(lambda c: True, Action(name="bump", params={"by": 1})),
        when(lambda c: True, Action(name="bump", params={"by": 100})),
    )
    run_pipeline(ctx, (ManagementStep(policy),), years=5.0, step=5.0)
    assert ctx.state["counter"] == 101


def test_a_policy_may_return_nothing():
    ctx = _ctx()
    run_pipeline(ctx, (ManagementStep(lambda c: ()),), years=5.0, step=5.0)
    assert ctx.state["counter"] == 0


# ---------------------------------------------------------------------------
# Ordering: the pipeline is the schedule
# ---------------------------------------------------------------------------


def test_step_order_is_the_pipeline_order():
    order = []

    class _Recording:
        def __init__(self, name):
            self.name = name

        def run(self, ctx, dt):
            order.append(self.name)

    run_pipeline(_ctx(), (_Recording("a"), _Recording("b")), years=5.0, step=5.0)
    assert order == ["a", "b"]

    order.clear()
    run_pipeline(_ctx(), (_Recording("b"), _Recording("a")), years=5.0, step=5.0)
    assert order == ["b", "a"]


def test_management_before_growth_sees_the_pre_growth_stand():
    ctx = _ctx()
    seen = []
    policy = when(
        lambda c: True,
        Action(name="observe", apply=lambda c: seen.append(c.state.get("steps", 0))),
    )
    run_pipeline(ctx, (ManagementStep(policy), GrowthStep()), years=10.0, step=5.0)
    # The management step ran before each growth step, so it saw 0 then 1.
    assert seen == [0, 1]


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def test_a_named_action_is_dispatched_through_the_models_capabilities():
    ctx = _ctx()
    Action(name="bump", params={"by": 7})(ctx)
    assert ctx.state["counter"] == 7
    assert any(entry.op == "action:bump" for entry in ctx.history)


def test_an_undeclared_named_action_raises():
    ctx = _ctx()
    with pytest.raises(KeyError, match="not available for this model"):
        Action(name="not_a_capability")(ctx)


def test_a_raw_callable_action_is_recorded_like_a_declared_one():
    ctx = _ctx()
    Action(name="custom", apply=lambda c: c.state.__setitem__("touched", True))(ctx)
    assert ctx.state["touched"] is True
    assert any(entry.op == "action:custom" for entry in ctx.history)


# ---------------------------------------------------------------------------
# The failure that used to be swallowed
# ---------------------------------------------------------------------------


def test_a_broken_policy_raises_instead_of_being_written_into_the_history():
    """``SimulationSetup`` caught every trigger exception and appended a
    ``trigger_error`` row, so a management rule that was broken from the first
    step produced a full run of plausible numbers and a note nobody read."""

    def _broken(ctx):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        run_pipeline(_ctx(), (ManagementStep(_broken),), years=5.0, step=5.0)


def test_a_broken_action_raises_too():
    def _explode(ctx):
        raise ValueError("bad thinning")

    policy = when(lambda c: True, Action(name="boom", apply=_explode))
    with pytest.raises(ValueError, match="bad thinning"):
        run_pipeline(_ctx(), (ManagementStep(policy),), years=5.0, step=5.0)
