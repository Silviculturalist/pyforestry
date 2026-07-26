"""Dsl utilities and interfaces."""

# pyforestry/base/simulation/dsl.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Literal

from .core import SimulationContext

CheckPhase = Literal["pre", "post"]


@dataclass
class TriggerSpec:
    """A condition to test each step, and the action to run when it holds.

    ``once=True`` disarms the trigger after it first fires.
    """

    name: str
    check_phase: CheckPhase
    predicate: Callable[[SimulationContext], bool]
    action: Callable[[SimulationContext], None]
    once: bool = False
    _armed: bool = field(default=True, init=False, repr=False)


@dataclass
class ScheduledOp:
    """An action to run at one fixed point on the simulation clock."""

    name: str
    t: float
    fn: Callable[[SimulationContext], None]


@dataclass
class SimulationSetup:
    """A fixed-step run: a clock, plus triggers and scheduled operations."""

    start_t: float
    end_t: float
    dt: float
    triggers: List[TriggerSpec] = field(default_factory=list)
    schedule: List[ScheduledOp] = field(default_factory=list)

    def run(self, ctx: SimulationContext) -> None:
        """Step ``ctx`` from ``start_t`` to ``end_t``, firing triggers and schedule."""
        ctx.state["t"] = self.start_t
        while ctx.state["t"] < self.end_t - 1e-12:
            self._eval_triggers(ctx, phase="pre")
            ctx.update_step(self.dt)
            for s in [s for s in self.schedule if abs(s.t - ctx.state["t"]) < 1e-9]:
                pre = ctx.snapshot()
                s.fn(ctx)
                post = ctx.snapshot()
                ctx._append_history("scheduled_op", {"name": s.name, "t": s.t}, pre, post)
            self._eval_triggers(ctx, phase="post")

    def _eval_triggers(self, ctx: SimulationContext, phase: CheckPhase) -> None:
        """Fire every armed trigger whose predicate holds in ``phase``."""
        for trg in self.triggers:
            if trg.check_phase != phase or not trg._armed:
                continue
            try:
                if trg.predicate(ctx):
                    pre = ctx.snapshot()
                    trg.action(ctx)
                    post = ctx.snapshot()
                    ctx._append_history(
                        "trigger_fired", {"name": trg.name, "phase": phase}, pre, post
                    )
                    if trg.once:
                        trg._armed = False
            except Exception as e:
                pre = ctx.snapshot()
                post = ctx.snapshot()
                ctx._append_history(
                    "trigger_error", {"name": trg.name, "error": str(e)}, pre, post
                )
