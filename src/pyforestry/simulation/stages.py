"""Turning a scenario's stage *names* into the steps a run executes.

``ScenarioConfig.stages()`` returns ``("growth", "disturbance", "valuation")`` --
names, in the order they run. :func:`build_pipeline` resolves each to a
:class:`~pyforestry.base.simulation.pipeline.Step`. Until it existed, the names
were recorded into a manifest and nothing ran them, which is most of why the
whole configuration tier executed nothing.

Two of the four stages are the runtime's own (:class:`GrowthStep`,
:class:`~pyforestry.simulation.valuation.step.ValuationStep`). Two are defined
here because they are what a *scenario* adds on top of a published model:

* :class:`ScenarioDisturbanceStep` -- an annual disturbance rate scaled by the
  scenario's ``disturbance_factor``. None of the growth models in this package
  predicts windthrow, fire or bark beetle, so this is an addition to the model
  rather than a distortion of it.
* :class:`ScenarioGrowthStep` -- growth, with the scenario's ``growth_factor``
  applied to the period's *increment*. This one **is** a distortion of a
  published model's prediction, which is why it is a separate named stage, why
  it is an exact no-op at 1.0, why the factor is recorded in the run manifest,
  and why it refuses to run on a representation where "the increment" is not a
  well-defined thing to scale.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping, Optional, Sequence

from pyforestry.base.simulation.core import SimulationContext
from pyforestry.base.simulation.pipeline import Action, GrowthStep, ManagementStep, Step
from pyforestry.simulation.policy import ManagementPlan, ScenarioFactors
from pyforestry.simulation.valuation.removals import StandRemovalLedger
from pyforestry.simulation.valuation.step import ValuationStep
from pyforestry.simulation.valuation.volume import ValuationSettings

__all__ = [
    "STAGE_BUILDERS",
    "ScenarioDisturbanceStep",
    "ScenarioGrowthStep",
    "StageContext",
    "ThinningStep",
    "build_pipeline",
    "known_stages",
]

#: Where a step records the volume it removed, so the run's summary can report
#: harvest and disturbance separately without either step knowing about the other.
REMOVED_BY_STAGE_KEY = "removed_volume_m3_per_ha_by_stage"


def record_removal(ctx: SimulationContext, stage: str, volume_m3_per_ha: float) -> None:
    """Add ``volume_m3_per_ha`` to what ``stage`` has removed over the run."""
    ledger = ctx.attrs.setdefault(REMOVED_BY_STAGE_KEY, {})
    ledger[stage] = float(ledger.get(stage, 0.0)) + float(volume_m3_per_ha)


@dataclass(frozen=True)
class StageContext:
    """Everything a stage builder may consult when constructing its step.

    Args:
        management: The scenario's management plan, if it declares one.
        factors: The scenario's growth and disturbance overlays.
        guard_policy: Non-formula guard flags declared by the configuration.
        valuation: Price list, taper and bucking settings, when the run supplies
            them. A ``"valuation"`` stage without them is an error rather than a
            silently skipped stage.
        volume: How to read the stand's standing volume, in m³/ha.
        disturbance_rate_per_year: The scenario's base annual disturbance rate,
            before ``factors.disturbance_factor``. Zero -- the default -- makes
            the disturbance stage an exact no-op.
        thin_at_years: Clock times at which the management stage thins. Empty --
            the default -- makes it an exact no-op.
    """

    volume: Callable[[SimulationContext], float]
    management: Optional[ManagementPlan] = None
    factors: ScenarioFactors = field(default_factory=ScenarioFactors)
    guard_policy: Mapping[str, object] = field(default_factory=dict)
    valuation: Optional[ValuationSettings] = None
    disturbance_rate_per_year: float = 0.0
    thin_at_years: tuple[float, ...] = ()


@dataclass(frozen=True)
class ScenarioGrowthStep:
    """Advance the model, then apply the scenario's growth factor to the increment.

    At ``growth_factor == 1.0`` this is exactly :class:`GrowthStep`: the model's
    own prediction, untouched. Above or below, the period's increment is scaled
    and the stand is rewritten -- a scenario device, not science, which is why
    :func:`build_pipeline` only ever produces this step when a factor other than
    1.0 was configured, and why the manifest records the value.

    Only aggregate stands can be adjusted this way: scaling "the increment" means
    scaling one basal-area and one stem number. On a tree list the same idea
    would mean redistributing growth across trees, which is a modelling decision
    and belongs to a model.
    """

    growth_factor: float = 1.0
    name: str = "growth"

    def run(self, ctx: SimulationContext, dt: float) -> None:
        """Grow one period, scaling the increment by the scenario factor.

        Raises:
            ValueError: If a factor other than 1.0 is configured for a stand that
                is not in aggregate mode.
        """
        if self.growth_factor == 1.0:
            ctx.update_step(dt)
            return
        if ctx.mode != "aggregate":
            raise ValueError(
                f"growth_factor={self.growth_factor!r} cannot be applied to a "
                f"{ctx.mode!r} stand: scaling 'the increment' is only well defined "
                "for aggregate basal area and stems. Use 1.0, run this scenario on an "
                "aggregate model, or express the effect inside a model variant."
            )
        ba_before = float(ctx.metrics["BasalArea"]["TOTAL"])
        stems_before = float(ctx.metrics["Stems"]["TOTAL"])
        ctx.update_step(dt)
        ba_after = float(ctx.metrics["BasalArea"]["TOTAL"])
        stems_after = float(ctx.metrics["Stems"]["TOTAL"])
        ctx.set_aggregate_metrics(
            ba_total=ba_before + (ba_after - ba_before) * self.growth_factor,
            stems_total=stems_before + (stems_after - stems_before) * self.growth_factor,
        )


@dataclass(frozen=True)
class ScenarioDisturbanceStep:
    """Remove a scenario-driven share of the stand each period.

    ``rate_per_year * factor`` compounded over the period, applied to stems and
    basal area alike. This is not any published model's mortality: those are in
    ``<region>/mortality/`` and run inside the models that own them. This is the
    windthrow-and-fire term a *scenario* adds, and it is zero unless a run asks
    for it.

    The rate is the caller's. This package ships none, for either region: a
    disturbance rate is a finding -- from a risk model, or from an inventory of
    observed damage -- and inventing one here would put a number under a
    scenario's name with nothing behind it. The manifest records whatever the run
    was given.
    """

    rate_per_year: float = 0.0
    factor: float = 1.0
    name: str = "disturbance"

    @property
    def effective_rate_per_year(self) -> float:
        """The annual rate actually applied, after the scenario factor."""
        return float(self.rate_per_year) * float(self.factor)

    def run(self, ctx: SimulationContext, dt: float) -> None:
        """Remove the period's disturbance share, recording the volume lost."""
        rate = self.effective_rate_per_year
        if rate <= 0.0:
            return
        removed_fraction = 1.0 - max(0.0, 1.0 - rate) ** float(dt)
        _remove_fraction(
            ctx,
            self.name,
            removed_fraction,
            {"rate_per_year": rate},
            merchantable=False,
        )


@dataclass(frozen=True)
class ThinningStep:
    """Remove the scenario's thinning fraction, once, when the trigger fires.

    ``ManagementStep`` is the general mechanism -- a policy proposes actions and
    this is one policy's worth of it -- expressed as a step because a scenario's
    management is a fraction and a schedule rather than a callable a caller
    writes.
    """

    thinning_ratio: float
    at_years: tuple[float, ...] = ()
    name: str = "management"
    tolerance: float = 1e-9

    def run(self, ctx: SimulationContext, dt: float) -> None:
        """Thin if the clock has reached one of the scheduled times."""
        if not self.at_years or self.thinning_ratio <= 0.0:
            return
        now = float(ctx.state.get("t", 0.0))
        if not any(abs(now - t) <= self.tolerance for t in self.at_years):
            return
        _remove_fraction(
            ctx,
            self.name,
            float(self.thinning_ratio),
            {"thinning_ratio": float(self.thinning_ratio)},
            merchantable=True,
        )


def _standing_volume(ctx: SimulationContext) -> float:
    """Read the volume reporter the run installed on the context."""
    reporter = ctx.attrs.get("_volume_reporter")
    if reporter is None:  # pragma: no cover - run_scenario always installs one
        raise RuntimeError("No volume reporter is installed on this context.")
    return float(reporter(ctx))


def _record_removed_trees(ctx: SimulationContext, stage: str, removed_fraction: float) -> None:
    """Add the stems a removal took out to the run's removal ledger.

    This is what connects the two halves of the valuation design: a step thins,
    and :class:`~pyforestry.simulation.valuation.step.ValuationStep` prices what
    it removed. Without it the ledger stayed empty, so a pipeline that declared a
    valuation stage priced nothing and reported it as zero.

    Only meaningful for a tree list -- there is nothing to buck in an aggregate
    basal area -- so an aggregate or diameter-class run simply records no pieces
    and its valuation stage stays quiet.
    """
    if not ctx.holds_tree_list():
        return
    ledger = ctx.attrs.get(ValuationStep.LEDGER_KEY)
    if not isinstance(ledger, StandRemovalLedger):
        ledger = StandRemovalLedger(stand_id=str(ctx.attrs.get("stand_id", "")))
        ctx.attrs[ValuationStep.LEDGER_KEY] = ledger
    cohort = f"{stage}@{float(ctx.state.get('t', 0.0)):g}"
    for plot in ctx.plots:
        for tree in plot.trees:
            if tree.species is None or tree.diameter_cm is None or tree.height_m is None:
                continue
            weight = float(tree.weight_n or 0.0) * removed_fraction
            if weight <= 0.0:
                continue
            ledger.record_tree(cohort, tree, weight=weight)


def _scale_stand(ctx: SimulationContext, survived: float) -> None:
    """Scale the stand down to ``survived`` of its stems, in whatever it holds.

    Removing a share of a stand is a property of the *representation*, not of any
    model: it is the same arithmetic on aggregate metrics, on per-tree weights and
    on diameter-class counts. Doing it here rather than through
    ``ctx.do("apply_mortality_rate")`` is what lets a scenario thin any model --
    that action is declared by exactly one model in this package, the reference
    example, so dispatching through it would have limited scenarios to that one.
    """
    if ctx.mode == "aggregate":
        ctx.scale_stems(survived)
    elif ctx.holds_tree_list():
        for plot in ctx.plots:
            for tree in plot.trees:
                weight = tree.weight_n
                tree.weight_n = (1.0 if weight is None else float(weight)) * survived
    else:
        classes = ctx.diameter_classes
        for record in classes.values():
            record["n_per_ha"] = [float(n) * survived for n in record["n_per_ha"]]
        ctx.set_diameter_class(classes)


def _remove_fraction(
    ctx: SimulationContext,
    stage: str,
    fraction: float,
    params: Mapping[str, float],
    *,
    merchantable: bool,
) -> None:
    """Remove ``fraction`` of the stand under ``stage``, recording what it took.

    The volume goes to the run's per-stage ledger so the summary can report
    harvest and disturbance apart, and the operation goes to ``ctx.history``
    through :class:`Action`, so a caller reading the context sees it too.

    Args:
        merchantable: Whether the removed stems reach the valuation ledger. A
            thinning produces logs to price; a windthrow produces loss. Sending
            disturbance to the valuation would report a stand as having *earned*
            what a storm took.
    """
    if fraction <= 0.0:
        return
    before = _standing_volume(ctx)
    if merchantable:
        _record_removed_trees(ctx, stage, fraction)
    Action(name=stage, params=dict(params), apply=lambda c: _scale_stand(c, 1.0 - fraction))(ctx)
    record_removal(ctx, stage, max(0.0, before - _standing_volume(ctx)))


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def _build_growth(stage: StageContext) -> Step:
    """``"growth"``: the model, with the scenario's growth factor if it has one."""
    if stage.factors.growth_factor == 1.0:
        return GrowthStep()
    return ScenarioGrowthStep(growth_factor=stage.factors.growth_factor)


def _build_disturbance(stage: StageContext) -> Step:
    """``"disturbance"``: the scenario's disturbance term, zero unless configured."""
    return ScenarioDisturbanceStep(
        rate_per_year=stage.disturbance_rate_per_year,
        factor=stage.factors.disturbance_factor,
    )


def _build_management(stage: StageContext) -> Step:
    """``"management"``: a no-op unless the scenario declares a thinning plan."""
    if stage.management is None:
        return ManagementStep(policy=lambda _ctx: (), name="management")
    return ThinningStep(
        thinning_ratio=stage.management.thinning_ratio,
        at_years=stage.thin_at_years,
    )


def _build_valuation(stage: StageContext) -> Step:
    """``"valuation"``: price what the period removed.

    Raises:
        ValueError: If the configuration declares this stage but the run supplied
            no valuation settings. Skipping it silently would report a run as
            having valued its removals at nothing.
    """
    if stage.valuation is None:
        raise ValueError(
            "This scenario declares a 'valuation' stage but the run supplied no "
            "ValuationSettings. Pass valuation=ValuationSettings(...) to run_scenario, "
            "or drop the stage from the configuration."
        )
    return ValuationStep(stage.valuation)


#: Stage name -> the step it builds. A configuration naming anything else fails
#: at pipeline construction, with the known names listed.
STAGE_BUILDERS: dict[str, Callable[[StageContext], Step]] = {
    "growth": _build_growth,
    "disturbance": _build_disturbance,
    "management": _build_management,
    "valuation": _build_valuation,
}


def known_stages() -> tuple[str, ...]:
    """Return every stage name :func:`build_pipeline` can resolve, sorted."""
    return tuple(sorted(STAGE_BUILDERS))


def build_pipeline(stages: Sequence[str], stage_context: StageContext) -> tuple[Step, ...]:
    """Resolve stage names into the ordered steps a period runs.

    Args:
        stages: The configuration's ``stages()``, in order.
        stage_context: What the builders may consult.

    Returns:
        One step per name, in the same order.

    Raises:
        ValueError: If a name is not a known stage.
    """
    steps: list[Step] = []
    for name in stages:
        try:
            builder = STAGE_BUILDERS[name]
        except KeyError:
            raise ValueError(
                f"Unknown stage {name!r}. Known stages: {', '.join(known_stages())}."
            ) from None
        steps.append(builder(stage_context))
    return tuple(steps)
