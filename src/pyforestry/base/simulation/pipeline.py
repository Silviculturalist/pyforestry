"""One scheduler: an ordered pipeline of steps over the whole stand.

There used to be three, and none knew the others existed:
``ctx.update_step(years, management={"pre": [...], "post": [...]})``,
``SimulationSetup(triggers=..., schedule=...).run(ctx)``, and ``StageRuntime`` with
``ManagementStage`` and rulesets. The flagship composite used none of them and
hand-coded its ordering in ``step()``, which was the honest admission that none of
the three fit.

Two things were wrong with the ones that went.

**They scheduled the wrong unit.** ``StageRuntime`` handed a stage one *part* at a
time, but every real model here steps the whole stand: Ekö 1985 couples every
cohort to every other, and Elfving calibrates against whole-stand basal area. Its
only consumer therefore carried an ``_armed`` latch so that the work happened on
the first of N invocations and the remaining N-1 were inert. Here the unit of work
is the stand, and a step that wants cohorts loops over them itself.

**Management was three mechanisms.** A phase dict of action names, a list of
trigger objects, and a ruleset tier that its own consumer never used. All three
are the same thing -- decide what to do, then do it -- so management is now one
type::

    Policy = Callable[[SimulationContext], Sequence[Action]]

A trigger is a policy with an ``if`` (:func:`when`); a schedule is a policy with a
clock comparison (:func:`at_times`); a ruleset is a policy that reads a config.
:func:`combine` puts several together.

A policy that raises, raises. ``SimulationSetup`` caught every exception from a
trigger and wrote it into the history as a ``trigger_error`` row, so a management
rule that was broken from the first step produced a full run of plausible numbers
and a note nobody read.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, List, Mapping, Optional, Protocol, Sequence, Tuple

from .core import SimulationContext

__all__ = [
    "Action",
    "GrowthStep",
    "ManagementStep",
    "Policy",
    "Step",
    "at_times",
    "combine",
    "run_pipeline",
    "when",
]


# ---------------------------------------------------------------------------
# Management
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Action:
    """One management operation, proposed by a policy and applied by a step.

    Name a capability the model declares in ``available_actions()`` and it is
    dispatched through :meth:`SimulationContext.do`, which gates it on the
    inventory mode and records it in the history. Supply ``apply`` instead for an
    operation the model does not declare; the recording is the same, the gating
    is yours.
    """

    name: str
    params: Mapping[str, Any] = field(default_factory=dict)
    apply: Optional[Callable[[SimulationContext], None]] = None

    def __call__(self, ctx: SimulationContext) -> None:
        """Apply this action to ``ctx``, recording it in the history either way."""
        if self.apply is None:
            ctx.do(self.name, **dict(self.params))
            return
        pre = ctx.snapshot()
        self.apply(ctx)
        ctx._refresh_metrics()
        post = ctx.snapshot()
        ctx._append_history(f"action:{self.name}", {"params": dict(self.params)}, pre, post)


#: What management is. Everything that used to be a trigger, a schedule entry, a
#: phase dict or a ruleset is one of these.
Policy = Callable[[SimulationContext], Sequence[Action]]


def combine(*policies: Policy) -> Policy:
    """Return a policy proposing everything ``policies`` propose, in order."""

    def _combined(ctx: SimulationContext) -> Sequence[Action]:
        actions: List[Action] = []
        for policy in policies:
            actions.extend(policy(ctx) or ())
        return tuple(actions)

    return _combined


def when(
    predicate: Callable[[SimulationContext], bool],
    action: Callable[[SimulationContext], Sequence[Action]] | Action,
    *,
    once: bool = False,
) -> Policy:
    """Propose ``action`` on each step where ``predicate`` holds.

    This is what a ``TriggerSpec`` was, minus the ``check_phase`` field (a policy
    runs where you put it in the pipeline) and minus the exception swallowing.
    With ``once=True`` it disarms after firing, which needs mutable state, so the
    returned closure is not reusable across runs -- build a fresh one per run.
    """
    fired = [False]

    def _policy(ctx: SimulationContext) -> Sequence[Action]:
        if once and fired[0]:
            return ()
        if not predicate(ctx):
            return ()
        fired[0] = True
        if isinstance(action, Action):
            return (action,)
        return tuple(action(ctx) or ())

    return _policy


def at_times(
    times: Iterable[float],
    action: Callable[[SimulationContext], Sequence[Action]] | Action,
    *,
    tolerance: float = 1e-9,
) -> Policy:
    """Propose ``action`` whenever the clock reaches one of ``times``.

    This is what a ``ScheduledOp`` was. The comparison is against ``ctx.state["t"]``
    with a tolerance, because a schedule written in whole years and a clock
    accumulated by repeated addition do not land on the same float.
    """
    scheduled = tuple(float(t) for t in times)

    def _policy(ctx: SimulationContext) -> Sequence[Action]:
        now = float(ctx.state.get("t", 0.0))
        if not any(abs(now - t) <= tolerance for t in scheduled):
            return ()
        if isinstance(action, Action):
            return (action,)
        return tuple(action(ctx) or ())

    return _policy


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


class Step(Protocol):
    """One phase of a period, applied to the whole stand.

    A step that needs to work cohort by cohort loops over them itself. That is
    the inversion: the runtime schedules stands, not parts, because every model
    in this package couples its parts to each other.
    """

    name: str

    def run(self, ctx: SimulationContext, dt: float) -> None:
        """Advance ``ctx`` through this phase of a ``dt``-year period."""
        ...


@dataclass(frozen=True)
class ManagementStep:
    """Ask a policy what to do, then do it."""

    policy: Policy
    name: str = "management"

    def run(self, ctx: SimulationContext, dt: float) -> None:
        """Apply every action the policy proposes for this step."""
        for action in self.policy(ctx) or ():
            action(ctx)


@dataclass(frozen=True)
class GrowthStep:
    """Advance the model by one period."""

    name: str = "growth"

    def run(self, ctx: SimulationContext, dt: float) -> None:
        """Run the context's model for ``dt`` years."""
        ctx.update_step(dt)


#: Management, then growth. The order that every model in this package already
#: hand-coded: you thin the stand you have, then grow what is left.
DEFAULT_PIPELINE: Tuple[Step, ...] = (GrowthStep(),)


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------


def run_pipeline(
    ctx: SimulationContext,
    pipeline: Sequence[Step],
    *,
    years: float,
    step: float,
    start_t: Optional[float] = None,
) -> SimulationContext:
    """Run ``pipeline`` over ``ctx`` for ``years``, one ``step``-year period at a time.

    The runner owns the clock. It decides the period lengths up front and stamps
    ``ctx.state["t"]`` after each one, rather than looping until the clock passes
    the end: a pipeline with no growth step -- management only, or a pipeline
    under construction -- would never advance the clock and would run forever.
    Stamping also removes the drift that accumulates from adding ``dt`` to itself
    twenty times.

    Args:
        ctx: The run's context. Stepped in place and returned.
        pipeline: Steps in the order they run within each period.
        years: Total length of the projection.
        step: Length of one period. A trailing remainder shorter than ``step`` is
            run at its true length rather than rounded up, so a model that scales
            linearly with ``dt`` does not grow the stand for years that did not
            happen.
        start_t: Clock value to start from. Defaults to the context's current
            ``t``, so a projection can be continued.

    Returns:
        ``ctx``, advanced.

    Raises:
        ValueError: If ``step`` is not positive or ``years`` is negative.
    """
    if step <= 0:
        raise ValueError(f"step must be positive, got {step!r}.")
    if years < 0:
        raise ValueError(f"years must not be negative, got {years!r}.")

    t0 = float(ctx.state.get("t", 0.0)) if start_t is None else float(start_t)
    ctx.state["t"] = t0

    periods: List[float] = []
    remaining = float(years)
    while remaining > 1e-9:
        dt = min(float(step), remaining)
        periods.append(dt)
        remaining -= dt

    elapsed = 0.0
    for dt in periods:
        for stage in pipeline:
            stage.run(ctx, dt)
        elapsed += dt
        ctx.state["t"] = t0 + elapsed
    return ctx
