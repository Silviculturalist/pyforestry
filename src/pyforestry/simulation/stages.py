"""Turning a scenario's stage *names* into the steps a run executes.

``ScenarioConfig.stages()`` returns ``("growth", "disturbance", "valuation")`` --
names, in the order they run. :func:`build_pipeline` resolves each to a
:class:`~pyforestry.base.simulation.pipeline.Step`. Until it existed, the names
were recorded into a manifest and nothing ran them, which is most of why the
whole configuration tier executed nothing.

Two of the four stages are the runtime's own (:class:`GrowthStep`,
:class:`~pyforestry.simulation.valuation.step.ValuationStep`). Two are defined
here because they are what a *scenario* adds on top of a published model:

* :class:`ScenarioDisturbanceStep` -- an annual disturbance rate, scaled by any
  :data:`~pyforestry.simulation.forcing.DISTURBANCE` forcing. None of the growth
  models in this package predicts windthrow, fire or bark beetle, so this is an
  addition to the model rather than a distortion of it.
* :class:`ScenarioGrowthStep` -- growth, with any
  :data:`~pyforestry.simulation.forcing.GROWTH` forcing applied to the period's
  *increment*. This one **is** a distortion of a published model's prediction,
  which is why it is a separate named stage, why it is an exact no-op when
  nothing forces growth, why the forcing is recorded in the run manifest, and
  why it refuses to run on a representation where "the increment" is not a
  well-defined thing to scale.

Every step reads its forcings at the period's calendar year, which
:class:`CalendarStep` stamps onto the context. That is what lets a forcing be a
year-by-year series -- a weather correction, an inflation index -- rather than
one number for the run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional, Sequence

from pyforestry.base.helpers.primitives import Age, AgeMeasurement
from pyforestry.base.simulation.core import SimulationContext
from pyforestry.base.simulation.pipeline import Action, GrowthStep, ManagementStep, Step
from pyforestry.simulation.forcing import (
    CALENDAR_YEAR_KEY,
    DISTURBANCE,
    GROWTH,
    THINNING,
    ForcingSet,
    period_year,
)
from pyforestry.simulation.policy import ManagementPlan
from pyforestry.simulation.valuation.removals import StandRemovalLedger
from pyforestry.simulation.valuation.step import ValuationStep
from pyforestry.simulation.valuation.volume import ValuationSettings

__all__ = [
    "BY_AGE",
    "BY_CALENDAR",
    "CALENDAR_YEAR_KEY",
    "STAND_AGE_KEY",
    "STAND_SPECIES_KEY",
    "STAND_START_AGE_KEY",
    "THINNINGS_FIRED_KEY",
    "MeanTree",
    "MeanTreeReporter",
    "STAGE_BUILDERS",
    "CalendarStep",
    "ScenarioDisturbanceStep",
    "ScenarioGrowthStep",
    "StageContext",
    "ThinningSchedule",
    "ThinningStep",
    "build_pipeline",
    "known_stages",
    "period_age",
    "period_year",
]

#: A thinning schedule counted in stand age -- the recommended one.
BY_AGE = "age"
#: A thinning schedule counted in calendar years.
BY_CALENDAR = "calendar"


#: Where a step records the volume it removed, so the run's summary can report
#: harvest and disturbance separately without either step knowing about the other.
REMOVED_BY_STAGE_KEY = "removed_volume_m3_per_ha_by_stage"

#: Where a run records the species a stand's mean-tree removals are priced as.
#: Set from :attr:`~pyforestry.simulation.scenario.StandUnit.species`.
STAND_SPECIES_KEY = "stand_species"

#: The age the stand starts the projection at, as an
#: :class:`~pyforestry.base.helpers.primitives.AgeMeasurement` so it says whether
#: it is counted from the seed or from breast height. Set per stand by
#: :func:`~pyforestry.simulation.scenario.run_scenario`.
STAND_START_AGE_KEY = "stand_start_age"

#: The age the stand has reached in the period currently running, stamped by
#: :class:`CalendarStep` in the same measure its start age was given in.
STAND_AGE_KEY = "stand_age"

#: Where :class:`ThinningStep` records the ages or years its thinnings actually
#: fired at, so a run can be asked what it did rather than what it was asked for.
THINNINGS_FIRED_KEY = "thinnings_fired"


def period_age(ctx: SimulationContext) -> Optional[AgeMeasurement]:
    """Return the stand's age at the start of the period currently running.

    ``None`` for a run that never said how old its stands were, which is every
    run that does not schedule by age.
    """
    age = ctx.attrs.get(STAND_AGE_KEY)
    return age if isinstance(age, AgeMeasurement) else None


@dataclass(frozen=True)
class MeanTree:
    """The representative stem a stand without individual stems can be bucked as.

    Attributes:
        species: What it is.
        diameter_cm: Its diameter, normally the stand's quadratic mean diameter.
        height_m: Its height. Lorey's mean height where the stand has one -- a
            model that predicts only *dominant* height does not, and substituting
            that overstates the stem.
        stems_removed: How many such stems the removal takes out, per hectare.
    """

    species: Any
    diameter_cm: float
    height_m: float
    stems_removed: float


#: How a run reads its stand's mean tree, given the fraction being removed.
MeanTreeReporter = Callable[[SimulationContext, float], Optional[MeanTree]]


@dataclass(frozen=True)
class ThinningSchedule:
    """When a scenario thins, in a measure that means the same thing everywhere.

    A projection's own clock -- ``ctx.state["t"]`` -- is elapsed years from
    wherever the model started, and *where a model starts it is the model's
    business*: the Elfving (2010) adapter starts at zero, the Kuehne (2022) one at
    the stand's total age. Scheduling against it therefore meant two different
    things in the two regions under one parameter name and one sentence of
    documentation, and asking Norway to thin at ``15`` -- fifteen years in --
    silently did nothing at all, because that clock began at 40.

    So a schedule says what its numbers are. Either:

    * **by age** (:data:`BY_AGE`) -- the recommended one, because a silvicultural
      prescription is a statement about how old the stand is, not about when the
      analyst pressed start. The points are
      :class:`~pyforestry.base.helpers.primitives.AgeMeasurement`, so they also
      say whether they are counted from the seed or from breast height.
    * **by calendar year** (:data:`BY_CALENDAR`) -- for a schedule tied to
      something outside the stand, and read against the same calendar a
      :mod:`~pyforestry.simulation.forcing` series is.

    Attributes:
        basis: :data:`BY_AGE` or :data:`BY_CALENDAR`.
        points: The ages or years to thin at, sorted.
        age_measure: ``Age.TOTAL`` or ``Age.DBH`` for an age schedule; ``None``
            for a calendar one.
    """

    basis: str
    points: tuple[float, ...] = ()
    age_measure: Optional[Age] = None

    def __post_init__(self) -> None:
        """Sort the points and check the basis carries what it needs."""
        if self.basis not in (BY_AGE, BY_CALENDAR):
            raise ValueError(f"basis must be {BY_AGE!r} or {BY_CALENDAR!r}, got {self.basis!r}.")
        if self.basis == BY_AGE and self.age_measure is None:
            raise ValueError(
                "An age schedule must say which age it means. Build its points with "
                "Age.TOTAL(...) or Age.DBH(...), which carry that."
            )
        object.__setattr__(self, "points", tuple(sorted(float(p) for p in self.points)))

    @classmethod
    def by_age(cls, ages: Sequence[AgeMeasurement]) -> "ThinningSchedule":
        """Build an age schedule from measurements that agree on what age they are.

        Raises:
            TypeError: If a point is a bare number. ``40`` does not say whether it
                is counted from the seed or from breast height, and the two differ
                by the years a stand took to reach 1.3 m.
            ValueError: If the points mix total and breast-height ages.
        """
        measures = set()
        for age in ages:
            if not isinstance(age, AgeMeasurement):
                raise TypeError(
                    f"A thinning age must say which age it is, got {age!r}. Use "
                    "Age.TOTAL(60) for age from the seed or Age.DBH(47) for age at "
                    "breast height -- they differ by the time the stand took to reach "
                    "1.3 m, which is a decade on a poor site."
                )
            measures.add(age.code)
        if len(measures) > 1:
            raise ValueError(
                "A thinning schedule cannot mix total and breast-height ages: "
                f"{[float(a) for a in ages]} were given in both measures. Convert them "
                "to one."
            )
        measure = Age(measures.pop()) if measures else Age.TOTAL
        return cls(basis=BY_AGE, points=tuple(float(a) for a in ages), age_measure=measure)

    @classmethod
    def by_calendar(cls, years: Sequence[float]) -> "ThinningSchedule":
        """Build a calendar-year schedule, read against the run's ``start_year``."""
        return cls(basis=BY_CALENDAR, points=tuple(float(y) for y in years))

    def __bool__(self) -> bool:
        """Whether this schedule thins at all."""
        return bool(self.points)

    def as_manifest(self) -> Mapping[str, Any]:
        """Return this schedule as a manifest record."""
        return {
            "basis": self.basis,
            "age_measure": self.age_measure.name if self.age_measure is not None else None,
            "points": list(self.points),
        }


@dataclass(frozen=True)
class CalendarStep:
    """Stamp the period's calendar year and the stand's age, then advance both.

    A projection's clock is elapsed years from wherever the model started, and
    some models start it at the stand's age. A forcing series is keyed by
    calendar year, and a silvicultural prescription by stand age. This is the one
    place all of them are reconciled: the run says which calendar year it begins
    in and how old each stand is, and every step afterwards reads
    :func:`period_year` or :func:`period_age` rather than the raw clock.

    Both are stamped at the *start* of the period, so a step reading either gets
    the year and age the period begins at, whatever order the stages run in. That
    is why scheduling no longer depends on whether management is placed before or
    after growth, which the elapsed clock quietly did.

    The stand's start age comes off the context rather than this step, because one
    pipeline runs every stand and real inventory is not all one age.

    First in the pipeline, and installed by :func:`build_pipeline` rather than
    named in a configuration's ``stages()``: which years a run covers is a
    property of the run, not of the scenario's science.
    """

    start_year: float
    name: str = "calendar"

    def run(self, ctx: SimulationContext, dt: float) -> None:
        """Stamp this period's year and stand age, then move both on by ``dt``."""
        current = ctx.attrs.get(CALENDAR_YEAR_KEY)
        ctx.attrs[CALENDAR_YEAR_KEY] = (
            float(self.start_year) if current is None else float(current) + float(dt)
        )

        start_age = ctx.attrs.get(STAND_START_AGE_KEY)
        if isinstance(start_age, AgeMeasurement):
            reached = ctx.attrs.get(STAND_AGE_KEY)
            ctx.attrs[STAND_AGE_KEY] = (
                start_age
                if not isinstance(reached, AgeMeasurement)
                # A year of elapsed time adds a year to age from the seed and to age
                # at breast height alike, so the measure carries through untouched.
                else AgeMeasurement(float(reached) + float(dt), reached.code)
            )


def record_removal(ctx: SimulationContext, stage: str, volume_m3_per_ha: float) -> None:
    """Add ``volume_m3_per_ha`` to what ``stage`` has removed over the run."""
    ledger = ctx.attrs.setdefault(REMOVED_BY_STAGE_KEY, {})
    ledger[stage] = float(ledger.get(stage, 0.0)) + float(volume_m3_per_ha)


@dataclass(frozen=True)
class StageContext:
    """Everything a stage builder may consult when constructing its step.

    Args:
        management: The scenario's management plan, if it declares one.
        forcings: The named multipliers this run applies, read at the period's
            calendar year. An empty set -- the default -- leaves every model's
            own prediction exactly as it is.
        guard_policy: Non-formula guard flags declared by the configuration.
        valuation: Price list, taper and bucking settings, when the run supplies
            them. A ``"valuation"`` stage without them is an error rather than a
            silently skipped stage.
        records_removals: Whether a thinning writes to the valuation ledger. True
            exactly when the configuration declares a ``"valuation"`` stage --
            which is what reads it. Keying this off the *settings* instead filled
            a ledger nobody would price for any run that passed a price list to a
            configuration that values nothing.
        volume: How to read the stand's standing volume, in m³/ha.
        disturbance_rate_per_year: The base annual disturbance rate, before any
            :data:`~pyforestry.simulation.forcing.DISTURBANCE` forcing. Zero --
            the default -- makes the disturbance stage an exact no-op.
        schedule: When the management stage thins, in stand age or calendar
            years. Empty -- the default -- makes it an exact no-op.
        mean_tree: How to read the representative stem of a stand that holds no
            individual ones, so an aggregate model's thinning can be bucked.
            Only the run knows this: a model that predicts dominant height has no
            mean height, and guessing one here would put a bias in every price.
    """

    volume: Callable[[SimulationContext], float]
    management: Optional[ManagementPlan] = None
    forcings: ForcingSet = field(default_factory=ForcingSet)
    guard_policy: Mapping[str, object] = field(default_factory=dict)
    valuation: Optional[ValuationSettings] = None
    records_removals: bool = False
    disturbance_rate_per_year: float = 0.0
    schedule: ThinningSchedule = field(default_factory=lambda: ThinningSchedule(basis=BY_CALENDAR))
    mean_tree: Optional["MeanTreeReporter"] = None


@dataclass(frozen=True)
class ScenarioGrowthStep:
    """Advance the model, then apply this period's growth forcing to the increment.

    With no forcing on :data:`~pyforestry.simulation.forcing.GROWTH` this is
    exactly :class:`GrowthStep`: the model's own prediction, untouched. With one,
    the period's increment is scaled and the stand rewritten -- a scenario
    device, not science, which is why it is a distinct named step and why the
    manifest records the forcing that drove it.

    The factor is read per period, so a weather correction given as a series
    (``{2014: 1.04, 2015: 1.02, ...}``) scales each period by its own year.

    Only aggregate stands can be adjusted this way: scaling "the increment" means
    scaling one basal-area and one stem number. On a tree list the same idea
    would mean redistributing growth across trees, which is a modelling decision
    and belongs to a model.
    """

    forcings: ForcingSet = field(default_factory=ForcingSet)
    name: str = "growth"

    def run(self, ctx: SimulationContext, dt: float) -> None:
        """Grow one period, scaling the increment by this year's growth forcing.

        Raises:
            ValueError: If a forcing other than 1.0 applies to a stand that is
                not in aggregate mode.
        """
        factor = self.forcings.multiplier(GROWTH, period_year(ctx)) if self.forcings else 1.0
        if factor == 1.0:
            ctx.update_step(dt)
            return
        if ctx.mode != "aggregate":
            raise ValueError(
                f"A growth forcing of {factor!r} cannot be applied to a {ctx.mode!r} "
                "stand: scaling 'the increment' is only well defined for aggregate "
                "basal area and stems. Drop the forcing, run this scenario on an "
                "aggregate model, or express the effect inside a model variant."
            )
        ba_before = float(ctx.metrics["BasalArea"]["TOTAL"])
        stems_before = float(ctx.metrics["Stems"]["TOTAL"])
        ctx.update_step(dt)
        ba_after = float(ctx.metrics["BasalArea"]["TOTAL"])
        stems_after = float(ctx.metrics["Stems"]["TOTAL"])
        ctx.set_aggregate_metrics(
            ba_total=ba_before + (ba_after - ba_before) * factor,
            stems_total=stems_before + (stems_after - stems_before) * factor,
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
    forcings: ForcingSet = field(default_factory=ForcingSet)
    name: str = "disturbance"

    def rate_in(self, year: float) -> float:
        """The annual rate applied in ``year``, after any disturbance forcing."""
        factor = self.forcings.multiplier(DISTURBANCE, year) if self.forcings else 1.0
        return float(self.rate_per_year) * factor

    def run(self, ctx: SimulationContext, dt: float) -> None:
        """Remove the period's disturbance share, recording the volume lost."""
        if self.rate_per_year <= 0.0:
            return
        rate = self.rate_in(period_year(ctx))
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
    """Remove the scenario's thinning fraction, once, when the schedule falls due.

    ``ManagementStep`` is the general mechanism -- a policy proposes actions and
    this is one policy's worth of it -- expressed as a step because a scenario's
    management is a fraction and a schedule rather than a callable a caller
    writes.

    A scheduled point falls due in the period whose span **contains** it, rather
    than in a period that begins exactly on it. Matching exactly meant that a
    thinning asked for anywhere off the period grid -- age 24 of a run stepping
    five years from 0 -- did nothing whatsoever, wrote a summary reporting no
    harvest and no revenue, and passed the artifact contract, because a run that
    harvests nothing legitimately earns nothing. There was no way to tell it from
    a scenario that had deliberately not thinned.
    """

    thinning_ratio: float
    schedule: ThinningSchedule = field(default_factory=lambda: ThinningSchedule(basis=BY_CALENDAR))
    forcings: ForcingSet = field(default_factory=ForcingSet)
    #: Whether to record what was removed for pricing. False when the pipeline
    #: has no valuation stage: a ledger nobody reads is wasted work.
    records_removals: bool = False
    #: How to read the mean stem of a stand that holds no individual ones.
    mean_tree: Optional["MeanTreeReporter"] = None
    name: str = "management"

    def ratio_in(self, year: float) -> float:
        """The fraction removed in ``year``, after any thinning forcing.

        Clamped to 1.0: a forcing that would take more than the stand holds takes
        the stand.
        """
        factor = self.forcings.multiplier(THINNING, year) if self.forcings else 1.0
        return min(1.0, float(self.thinning_ratio) * factor)

    def _due(self, ctx: SimulationContext, dt: float) -> Optional[float]:
        """Return the scheduled point this period covers, or ``None``.

        Raises:
            RuntimeError: If an age schedule is running against a stand whose age
                was never declared, which :func:`run_scenario` refuses earlier.
        """
        if self.schedule.basis == BY_AGE:
            reached = period_age(ctx)
            if reached is None:
                raise RuntimeError(
                    "This run thins by stand age but no stand age was declared, so "
                    "there is nothing to compare the schedule against. Pass "
                    "start_age= to run_scenario, or an age on each StandUnit."
                )
            now = float(reached)
        else:
            now = period_year(ctx)
        # Half-open, so a point on a period boundary falls due in exactly one
        # period and never in two.
        for point in self.schedule.points:
            if now <= point < now + float(dt):
                return point
        return None

    def run(self, ctx: SimulationContext, dt: float) -> None:
        """Thin if this period's span covers one of the scheduled points."""
        if not self.schedule or self.thinning_ratio <= 0.0:
            return
        due = self._due(ctx, dt)
        if due is None:
            return
        ratio = self.ratio_in(period_year(ctx))
        _remove_fraction(
            ctx,
            self.name,
            ratio,
            {"thinning_ratio": ratio, "scheduled_at": due},
            merchantable=self.records_removals,
            mean_tree_reporter=self.mean_tree,
        )
        # What it actually did, beside what it was asked for: a point inside a
        # period fires at the period's start, and the difference is the run's to
        # see rather than infer from the step length.
        fired = ctx.attrs.setdefault(THINNINGS_FIRED_KEY, [])
        fired.append(
            {
                "basis": self.schedule.basis,
                "scheduled_at": due,
                "fired_at": float(period_age(ctx)) if self.schedule.basis == BY_AGE else None,
                "calendar_year": period_year(ctx),
                "ratio": ratio,
            }
        )


def _standing_volume(ctx: SimulationContext) -> float:
    """Read the volume reporter the run installed on the context."""
    reporter = ctx.attrs.get("_volume_reporter")
    if reporter is None:  # pragma: no cover - run_scenario always installs one
        raise RuntimeError("No volume reporter is installed on this context.")
    return float(reporter(ctx))


def _ledger_for(ctx: SimulationContext) -> StandRemovalLedger:
    """Return the run's removal ledger, creating it on first use."""
    ledger = ctx.attrs.get(ValuationStep.LEDGER_KEY)
    if not isinstance(ledger, StandRemovalLedger):
        ledger = StandRemovalLedger(stand_id=str(ctx.attrs.get("stand_id", "")))
        ctx.attrs[ValuationStep.LEDGER_KEY] = ledger
    return ledger


def _record_removed(
    ctx: SimulationContext,
    stage: str,
    removed_fraction: float,
    volume_removed_m3: float,
    mean_tree: Optional["MeanTree"],
) -> None:
    """Add what a removal took out to the run's removal ledger.

    This is what connects the two halves of the valuation design: a step thins,
    and :class:`~pyforestry.simulation.valuation.step.ValuationStep` prices what
    it removed. Without it the ledger stayed empty, so a pipeline that declared a
    valuation stage priced nothing and reported it as zero.

    Both kinds of stand can say something, and both are bucked. A tree list gives
    stems. An aggregate stand gives its *mean* stem and how many came out, which
    is bucked once and scaled -- because a stand-level model still has a
    quadratic mean diameter, and that is a real tree.
    """
    ledger = _ledger_for(ctx)
    cohort = f"{stage}@{float(ctx.state.get('t', 0.0)):g}"

    if ctx.holds_tree_list():
        skipped = 0.0
        for plot in ctx.plots:
            for tree in plot.trees:
                weight = float(tree.weight_n or 0.0) * removed_fraction
                if tree.species is None or tree.diameter_cm is None or tree.height_m is None:
                    # Nothing to buck it from. Its volume may still have been
                    # counted as harvested -- that depends on the run's volume
                    # reporter, and one that imputes heights will count it -- so
                    # the ledger says how many stems it could not price rather
                    # than reporting a smaller harvest as simply worth less.
                    skipped += max(0.0, weight)
                    continue
                if weight <= 0.0:
                    continue
                ledger.record_tree(cohort, tree, weight=weight)
        if skipped > 0.0:
            ledger.metadata["stems_without_dimensions"] = (
                float(ledger.metadata.get("stems_without_dimensions", 0.0)) + skipped
            )
        return

    if volume_removed_m3 <= 0.0 or mean_tree is None:
        return
    ledger.record_mean_tree(
        cohort,
        species=mean_tree.species,
        diameter_cm=mean_tree.diameter_cm,
        height_m=mean_tree.height_m,
        stems=mean_tree.stems_removed,
        volume_m3=volume_removed_m3,
        metadata={"from": "aggregate stand; bucked at its mean tree"},
    )


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
    mean_tree_reporter: Optional["MeanTreeReporter"] = None,
) -> None:
    """Remove ``fraction`` of the stand under ``stage``, recording what it took.

    The volume goes to the run's per-stage ledger so the summary can report
    harvest and disturbance apart, and the operation goes to ``ctx.history``
    through :class:`Action`, so a caller reading the context sees it too.

    Args:
        merchantable: Whether what was removed reaches the valuation ledger. A
            thinning produces logs to price; a windthrow produces loss, so
            sending disturbance there would report a stand as having *earned*
            what a storm took. False also when the pipeline has no valuation
            stage at all.
        mean_tree_reporter: How to read the representative stem of a stand that
            holds no individual ones. Required to price an aggregate model's
            thinning.
    """
    if fraction <= 0.0:
        return
    before = _standing_volume(ctx)
    # Stems are read before the removal, while they are still there; the mean
    # tree likewise, since scaling the stand changes the stem count it reports.
    # The volume removed is only known afterwards. Hence both sides of the action.
    mean_tree = None
    if merchantable:
        if ctx.holds_tree_list():
            _record_removed(ctx, stage, fraction, 0.0, None)
        elif mean_tree_reporter is not None:
            mean_tree = mean_tree_reporter(ctx, fraction)

    Action(name=stage, params=dict(params), apply=lambda c: _scale_stand(c, 1.0 - fraction))(ctx)
    removed_volume = max(0.0, before - _standing_volume(ctx))

    if merchantable and not ctx.holds_tree_list():
        _record_removed(ctx, stage, fraction, removed_volume, mean_tree)
    record_removal(ctx, stage, removed_volume)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def _build_growth(stage: StageContext) -> Step:
    """``"growth"``: the model, with a growth forcing if the run declares one."""
    if GROWTH not in stage.forcings.names():
        return GrowthStep()
    return ScenarioGrowthStep(forcings=stage.forcings)


def _build_disturbance(stage: StageContext) -> Step:
    """``"disturbance"``: the scenario's disturbance term, zero unless configured."""
    return ScenarioDisturbanceStep(
        rate_per_year=stage.disturbance_rate_per_year,
        forcings=stage.forcings,
    )


def _build_management(stage: StageContext) -> Step:
    """``"management"``: a no-op unless the scenario declares a thinning plan."""
    if stage.management is None:
        return ManagementStep(policy=lambda _ctx: (), name="management")
    return ThinningStep(
        thinning_ratio=stage.management.thinning_ratio,
        schedule=stage.schedule,
        forcings=stage.forcings,
        records_removals=stage.records_removals,
        mean_tree=stage.mean_tree,
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
    return ValuationStep(settings=stage.valuation, forcings=stage.forcings)


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


def build_pipeline(
    stages: Sequence[str],
    stage_context: StageContext,
    *,
    start_year: Optional[float] = None,
) -> tuple[Step, ...]:
    """Resolve stage names into the ordered steps a period runs.

    Args:
        stages: The configuration's ``stages()``, in order.
        stage_context: What the builders may consult.
        start_year: Calendar year the run begins in. When given, a
            :class:`CalendarStep` is prepended so year-by-year forcings can be
            read; it is not one of the configuration's stages, because which
            years a run covers belongs to the run rather than to the scenario.

    Returns:
        One step per name, in the same order, after the calendar step if any.

    Raises:
        ValueError: If a name is not a known stage.
    """
    steps: list[Step] = []
    if start_year is not None:
        steps.append(CalendarStep(start_year=float(start_year)))
    for name in stages:
        try:
            builder = STAGE_BUILDERS[name]
        except KeyError:
            raise ValueError(
                f"Unknown stage {name!r}. Known stages: {', '.join(known_stages())}."
            ) from None
        steps.append(builder(stage_context))
    return tuple(steps)
