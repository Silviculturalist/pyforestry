"""Running a scenario configuration over real stands, and recording how.

This is what closes the gap the configuration tier carried from the start: a
:class:`~pyforestry.simulation.presets.ScenarioConfig` declared a seed strategy,
an ordered list of stage names, rulesets and a guard policy, and nothing executed
any of them. The harness that consumed it filled its artifacts with a seeded
random walk and stamped them ``synthetic: true``.

:func:`run_scenario` executes all four. It resolves ``stages()`` into steps via
:mod:`pyforestry.simulation.stages`, seeds each stand from ``seed_strategy()``,
steps a real :class:`~pyforestry.base.simulation.growth_model.GrowthModel` through
:func:`~pyforestry.base.simulation.pipeline.run_pipeline`, applies the guard
policy, and writes the volume balance each stand actually produced.

The manifest is the point. It records which models ran with which citations,
which stages in which order, which ruleset values were applied, the guard policy,
which price list the money is in, the discount rate and every seed -- so a summary
row can be read back against the construction that produced it without rerunning
anything.

The discount rate is here rather than on :meth:`ScenarioRunResult.net_present_value`
because the summary carries a net present value, and a figure in an artifact has
to have been discounted at a rate the artifact records. As a call argument it was
whatever the reader happened to pass, which is fine for exploring and useless in a
file. A run that prices its removals must now state a rate -- ``0.0`` states that
a krona at the end of the horizon is worth a krona now, which is a preference like
any other -- or declare a
:data:`~pyforestry.simulation.forcing.DISCOUNT` forcing for one that varies by
year. The method remains, for asking the same run what it would be worth at
another rate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from pyforestry.base.helpers.stand import Stand
from pyforestry.base.pricelist import PricelistIdentity
from pyforestry.base.simulation.core import SimulationContext
from pyforestry.base.simulation.growth_model import GrowthModel
from pyforestry.base.simulation.pipeline import run_pipeline
from pyforestry.simulation.artifacts import ScenarioArtifacts, git_revision, write_artifacts
from pyforestry.simulation.forcing import DISCOUNT, ForcingSet, stated_choice
from pyforestry.simulation.policy import ManagementPlan
from pyforestry.simulation.presets import ScenarioConfig, stable_seed
from pyforestry.simulation.provenance import (
    as_manifest_entries,
    as_manifest_source,
    collect_provenance,
)
from pyforestry.simulation.stages import (
    REMOVED_BY_STAGE_KEY,
    STAND_SPECIES_KEY,
    MeanTreeReporter,
    StageContext,
    build_pipeline,
)
from pyforestry.simulation.valuation.cashflow import CashFlow, cash_flows_of, net_present_value
from pyforestry.simulation.valuation.volume import ValuationSettings

__all__ = [
    "ScenarioRunResult",
    "StandUnit",
    "run_scenario",
]

#: Where a model publishes the stand volume it last computed. Useful to a reader
#: of a finished context; **not** a volume reporter, because it only moves when
#: the model steps -- a thinning between steps leaves it stale, which is how a
#: run first reported harvest and disturbance as zero while the volume they
#: removed silently reappeared inside "growth".
STAND_VOLUME_ATTR = "stand_volume_m3_per_ha"


@dataclass(frozen=True)
class StandUnit:
    """One stand in a scenario run, with the id its summary row is keyed by.

    Args:
        stand_id: The id its summary row is keyed by.
        stand: The inventory to project.
        species: What the stand is, for pricing removals an *aggregate* model
            produces. Such a model steps a whole-stand basal area, and
            ``Stand.set_aggregate_metrics`` drops species detail by design --
            a total genuinely has none -- so the species cannot be recovered from
            the metrics after the first step. Whoever built the stand knows it;
            this is where they say so. Unnecessary for a tree list, where every
            stem carries its own.
    """

    stand_id: int
    stand: Stand
    species: Optional[Any] = None


@dataclass(frozen=True)
class ScenarioRunResult:
    """What a scenario run produced.

    Attributes:
        artifacts: The three written files.
        rows: The summary rows, as written.
        manifest: The manifest payload, as written.
        contexts: One finished context per stand, in stand order, for a caller
            that wants the history rather than the summary.
        forcings: The forcings this run applied, kept so a horizon calculation
            can read a year-varying discount rate off the same set.
        discount_rate: The flat rate the run was configured with, and the one its
            summary's ``net_present_value`` column was discounted at. ``None``
            when a :data:`~pyforestry.simulation.forcing.DISCOUNT` forcing
            supplied the rate instead, or when the run priced nothing.
    """

    artifacts: ScenarioArtifacts
    rows: tuple[Mapping[str, Any], ...]
    manifest: Mapping[str, Any]
    contexts: tuple[SimulationContext, ...] = field(default=())
    forcings: ForcingSet = field(default_factory=ForcingSet)
    discount_rate: Optional[float] = None

    @property
    def start_year(self) -> float:
        """The calendar year the projection began in."""
        return float(self.manifest["start_year"])

    def cash_flows(self) -> tuple[tuple[int, tuple[CashFlow, ...]], ...]:
        """Return each stand's revenue by year, as ``(stand_id, flows)``.

        Empty for a run that never harvested, or one whose configuration declares
        no valuation stage.
        """
        return tuple(
            (int(row["stand_id"]), tuple(cash_flows_of(ctx.attrs)))
            for row, ctx in zip(self.rows, self.contexts, strict=False)
        )

    def net_present_value(
        self,
        *,
        discount_rate: Optional[float] = None,
        base_year: Optional[float] = None,
    ) -> dict[int, float]:
        """Return each stand's discounted revenue over the horizon, by stand id.

        The revenue in each entry is already nominal -- a
        :data:`~pyforestry.simulation.forcing.PRICE` forcing was applied in the
        year it was earned -- so discounting it here completes the pair: prices
        move the money, the discount rate moves it in time, and the manifest
        records both separately.

        Args:
            discount_rate: A flat annual rate. Defaults to the rate the run was
                configured with, so calling this with no arguments reproduces the
                summary's ``net_present_value`` column. Pass one to ask what the
                same run would be worth at a different rate. Ignored if the run
                applied a :data:`~pyforestry.simulation.forcing.DISCOUNT` forcing,
                which may vary by year.
            base_year: The year to express the total in. Defaults to the run's
                first, which is the year the summary column is expressed in.

        Returns:
            Stand id to net present value. Zero for a stand that earned nothing.
        """
        rate = self.discount_rate if discount_rate is None else discount_rate
        base = self.start_year if base_year is None else float(base_year)
        return {
            stand_id: net_present_value(
                flows,
                base_year=base,
                discount_rate=rate,
                forcings=self.forcings,
            )
            for stand_id, flows in self.cash_flows()
        }


def _stand_seed(scenario_seed: int, stand_id: int) -> int:
    """Derive a stand's seed from the scenario's, so order cannot affect it."""
    return stable_seed(scenario_seed, stand_id)


def _check_discounting(
    *,
    values_removals: bool,
    discount_rate: Optional[float],
    from_forcing: bool,
) -> None:
    """Reject a run whose discounting and whose valuation stage disagree.

    Raises:
        ValueError: If a run that prices its removals states no rate to discount
            them at, or a run that prices nothing states one anyway. The first
            would put a net present value in an artifact with nothing behind it;
            the second would put a rate in the manifest that discounted nothing,
            which reads as though it had.
    """
    if values_removals and discount_rate is None and not from_forcing:
        raise ValueError(
            "This scenario declares a 'valuation' stage, so its summary carries a net "
            "present value -- and that needs a rate to discount at. Pass "
            "discount_rate=, or declare a DISCOUNT forcing for a rate that varies by "
            "year. discount_rate=0.0 is a legitimate answer: it states that a krona at "
            "the end of the horizon is worth a krona now. There is no default, because "
            "a rate is a stated preference and no default would be anyone's."
        )
    if not values_removals and discount_rate is not None:
        raise ValueError(
            f"discount_rate={discount_rate!r} was given, but this scenario declares no "
            "'valuation' stage, so nothing is priced and there would be nothing to "
            "discount. Recording the rate in the manifest would say the run applied "
            "it. Add 'valuation' to the configuration's stages, or drop the argument."
        )


def _valuation_manifest(
    *,
    values_removals: bool,
    discount_rate: Optional[float],
    from_forcing: bool,
    base_year: float,
    identity: Optional[PricelistIdentity],
) -> dict[str, Any]:
    """Record what the summary's money columns were produced by.

    Two things produce them, and both belong here. The **price list** is where the
    money comes from -- what a cubic metre fetched, and in what currency -- so
    ``price_list`` names it, states its currency and carries its citation. Without
    it a revenue figure is a bare number: comparable with another run's only if
    both were priced against the same table, which nothing recorded. The
    **discount rate** then moves that money in time.

    The two are cited differently, because they are different kinds of thing. A
    discount rate is a decision rather than a finding, so it takes the
    ``(none)``/year-0 sentinel :func:`~pyforestry.simulation.forcing.stated_choice`
    builds -- the same way a thinning intensity does. A price list is regional
    market data with a publisher and a year, so it carries a real citation; a run
    that priced against its own table says *that* in the same sentinel form,
    through :data:`~pyforestry.base.pricelist.UNATTRIBUTED_PRICELIST_IDENTITY`.

    A rate that came from a forcing is already cited in ``forcings_applied``, and
    is pointed at from here rather than copied. ``price_list`` is ``None`` for a
    run that priced nothing, for the reason ``discount_rate`` is: naming a list a
    run never used would read as though it had.
    """
    return {
        "valued": values_removals,
        "base_year": float(base_year),
        "price_list": (
            None
            if identity is None
            else {
                "name": identity.name,
                "currency": identity.currency,
                "source": as_manifest_source(identity.source),
            }
        ),
        "discount_rate": None if discount_rate is None else float(discount_rate),
        "discount_from_forcing": from_forcing,
        "discount_source": (
            None
            if discount_rate is None
            else as_manifest_source(stated_choice(f"{discount_rate:g} annual discount rate"))
        ),
    }


def _rulesets_applied(config: ScenarioConfig) -> dict[str, Any]:
    """Resolve the configuration's rulesets to the values this run used."""
    applied: dict[str, Any] = {}
    for concern, ruleset in config.rulesets().items():
        value = ruleset()
        applied[concern] = value.as_mapping() if hasattr(value, "as_mapping") else value
    return applied


def _resolved_management(config: ScenarioConfig) -> Optional[ManagementPlan]:
    """Return the management plan this configuration declares, if any."""
    management: Optional[ManagementPlan] = None
    for concern, ruleset in config.rulesets().items():
        value = ruleset()
        if isinstance(value, ManagementPlan):
            management = value
        else:  # pragma: no cover - RulesetFn is typed to ManagementPlan
            raise TypeError(
                f"Ruleset {concern!r} returned {type(value).__name__}; a ruleset returns "
                "a ManagementPlan. Anything imposed from outside the models is a "
                "forcing, declared through ScenarioConfig.forcings()."
            )
    return management


def run_scenario(
    config: ScenarioConfig,
    *,
    build_model: Callable[[], GrowthModel],
    stands: Sequence[StandUnit],
    volume: Callable[[SimulationContext], float],
    global_seed: int,
    n_steps: int,
    step_years: Optional[float] = None,
    output_dir: Path,
    attrs: Optional[Mapping[str, Any]] = None,
    valuation: Optional[ValuationSettings] = None,
    discount_rate: Optional[float] = None,
    disturbance_rate_per_year: float = 0.0,
    thin_at_years: Sequence[float] = (),
    start_year: float = 0.0,
    forcings: Optional[ForcingSet] = None,
    mean_tree: Optional[MeanTreeReporter] = None,
) -> ScenarioRunResult:
    """Run ``config`` over ``stands`` and write the three artifacts.

    Args:
        config: The scenario configuration. Its ``stages()``, ``rulesets()``,
            ``guard_policy()`` and ``seed_strategy()`` are all executed.
        build_model: Builds a fresh model per stand. A model may carry per-run
            state, so stands must not share one.
        stands: The stands to project, each with the id its row is keyed by.
        volume: Standing volume of the stand *as it currently is*, in m³/ha,
            evaluated on demand. It must be a function of the context's present
            state: a reporter that reads a value the model cached at its last
            step cannot see a thinning, and every cubic metre a removal takes out
            reappears in the growth column. Required, with no default, for that
            reason.
        global_seed: The run's seed. Each stand's is derived from it through
            ``config.seed_strategy()``, so the summary does not depend on the
            order the stands were evaluated in.
        n_steps: Number of periods to project.
        step_years: Period length. Defaults to the model's declared
            ``native_step_years``, and to 5 years for a model that declares none.
        output_dir: Where the artifacts go; created if absent.
        attrs: Extra model attributes, merged into every stand's context.
        valuation: Price list, taper and bucking settings. Required if the
            configuration declares a ``"valuation"`` stage. The price list's
            :class:`~pyforestry.base.pricelist.PricelistIdentity` goes into the
            manifest, so give it one: it is what says what currency the summary's
            money is in and whose prices earned it.
        discount_rate: The annual rate the summary's net present value is
            discounted at, e.g. ``0.03``. Required if the configuration declares
            a ``"valuation"`` stage and no
            :data:`~pyforestry.simulation.forcing.DISCOUNT` forcing supplies a
            year-varying one; rejected if it declares no such stage, since then
            there is nothing to discount. ``0.0`` states no time preference. It
            is a decision rather than a finding, and the manifest records it as
            one.
        disturbance_rate_per_year: The annual share of the stand a scenario
            disturbance removes, before ``ScenarioFactors.disturbance_factor``.
            **The caller supplies this and it has no default source.** None of
            these growth models predicts windthrow, fire or bark beetle, and this
            package ships no disturbance rate for any region -- a rate belongs to
            a risk model or an inventory of observed damage, and there is neither
            here yet. Zero, the default, makes the stage an exact no-op; anything
            else is the analyst's number and is recorded in the manifest as such.
        thin_at_years: Clock times at which the management stage thins.
        start_year: Calendar year the projection begins in. Every period stamps
            its own year onto the context, and that is the year a forcing series
            is read at, so a weather correction given as ``{2014: 1.04, ...}``
            lines up with the run.
        forcings: Named values the run reads for the period it is in -- a weather
            correction, a disturbance factor, a price index. Merged after the
            configuration's own, so a caller's forcing composes with rather than
            replaces it. This package ships none: each is a claim about the
            world, and every one a run applies is recorded in its manifest with
            its citation.
        mean_tree: How to read the representative stem of a stand that holds no
            individual ones, so an aggregate model's thinning can still be
            bucked. Required to value such a run: only the caller knows which
            height its model predicts, and a model that gives dominant height has
            no mean height to substitute.

    Returns:
        The artifacts, the rows, the manifest and the finished contexts.

    Raises:
        ValueError: If ``n_steps`` is not positive, no stands were given, a stage
            name is unknown, the discounting and the valuation stage disagree, or
            a guard rejects an input.
    """
    if n_steps <= 0:
        raise ValueError(f"n_steps must be > 0, got {n_steps!r}.")
    if not stands:
        raise ValueError("A scenario run needs at least one stand.")

    scenario_seed = int(config.seed_strategy(global_seed=global_seed))
    guard_policy = dict(config.guard_policy())
    management = _resolved_management(config)
    applied_forcings = config.forcings().merge(forcings or ForcingSet())

    stage_names = tuple(config.stages())
    values_removals = "valuation" in stage_names
    discount_from_forcing = DISCOUNT in applied_forcings.names()

    stage_context = StageContext(
        volume=volume,
        management=management,
        forcings=applied_forcings,
        guard_policy=guard_policy,
        valuation=valuation,
        disturbance_rate_per_year=disturbance_rate_per_year,
        thin_at_years=tuple(float(t) for t in thin_at_years),
        mean_tree=mean_tree,
    )
    # After the pipeline, so a run that declares a valuation stage and supplies
    # neither a price list nor a rate is told about the price list first: without
    # one there is no revenue, and the rate is a refinement on revenue.
    pipeline = build_pipeline(stage_names, stage_context, start_year=start_year)
    _check_discounting(
        values_removals=values_removals,
        discount_rate=discount_rate,
        from_forcing=discount_from_forcing,
    )

    rows: list[dict[str, Any]] = []
    contexts: list[SimulationContext] = []
    models_run: dict[str, Any] = {}
    step = float(step_years) if step_years is not None else None

    for unit in stands:
        model = build_model()
        if step is None:
            step = float(model.requirements().native_step_years or 5.0)

        stand_seed = _stand_seed(scenario_seed, unit.stand_id)
        ctx = model.build_context(
            unit.stand,
            seed=stand_seed,
            attrs=dict(attrs) if attrs else None,
        )
        ctx.attrs["_volume_reporter"] = volume
        ctx.attrs["stand_id"] = unit.stand_id
        if unit.species is not None:
            ctx.attrs[STAND_SPECIES_KEY] = unit.species

        initial_volume = float(volume(ctx))
        if guard_policy.get("reject_negative_inputs") and initial_volume < 0.0:
            raise ValueError(
                f"Stand {unit.stand_id} starts at {initial_volume} m3/ha, and this "
                "scenario's guard policy rejects negative inputs."
            )

        run_pipeline(ctx, pipeline, years=step * n_steps, step=step)

        removed = dict(ctx.attrs.get(REMOVED_BY_STAGE_KEY, {}))
        harvested = float(removed.get("management", 0.0))
        disturbed = float(removed.get("disturbance", 0.0))
        net_volume = float(volume(ctx))
        if guard_policy.get("clamp_net_volume_to_zero"):
            net_volume = max(0.0, net_volume)
        # Derived from the clamped net so the row's identity closes exactly; the
        # manifest records that the clamp was in force.
        gross_growth = net_volume - initial_volume + harvested + disturbed

        # Empty unless a valuation stage priced a removal, so both figures are
        # 0.0 for a run that declares no such stage -- which is what ``valued``
        # is in the row to distinguish from a run that priced its removals and
        # found them worth nothing.
        flows = tuple(cash_flows_of(ctx.attrs))
        nominal_revenue = float(sum(flow.amount for flow in flows))

        rows.append(
            {
                "stand_id": int(unit.stand_id),
                "scenario_id": config.scenario_id,
                "stand_seed": int(stand_seed),
                "initial_volume_m3": initial_volume,
                "gross_growth_m3": gross_growth,
                "disturbance_loss_m3": disturbed,
                "harvested_m3": harvested,
                "net_volume_m3": net_volume,
                "valued": values_removals,
                "nominal_revenue": nominal_revenue,
                "net_present_value": net_present_value(
                    flows,
                    base_year=float(start_year),
                    discount_rate=discount_rate,
                    forcings=applied_forcings,
                ),
            }
        )
        contexts.append(ctx)
        models_run.update(collect_provenance(model))

    manifest = {
        "preset_id": config.preset_id,
        "scenario_id": config.scenario_id,
        "region": config.region,
        "global_seed": int(global_seed),
        "scenario_seed": scenario_seed,
        "processes": 1,
        "n_steps": int(n_steps),
        "step_years": float(step or 0.0),
        "n_stands": len(stands),
        "required_artifacts": list(config.required_artifacts()),
        "stages": list(stage_names),
        "rulesets_applied": _rulesets_applied(config),
        "forcings_applied": applied_forcings.as_manifest(),
        "guard_policy": {key: value for key, value in guard_policy.items()},
        "valuation": _valuation_manifest(
            values_removals=values_removals,
            discount_rate=discount_rate,
            from_forcing=discount_from_forcing,
            base_year=float(start_year),
            # Only for a run that priced something. A valuation stage cannot reach
            # here without settings -- build_pipeline refuses that above -- and a
            # price list supplied to a configuration that never values anything
            # earned nothing, so recording it would misreport what the run did.
            identity=(
                valuation.pricelist.identity if values_removals and valuation is not None else None
            ),
        ),
        "start_year": float(start_year),
        "disturbance_rate_per_year": float(disturbance_rate_per_year),
        "thin_at_years": [float(t) for t in thin_at_years],
        "models_run": as_manifest_entries(models_run),
        "provenance": {
            "git_revision": git_revision(),
            "config_component_id": config.component_id,
        },
    }

    artifacts = write_artifacts(output_dir=output_dir, manifest=manifest, rows=rows)
    return ScenarioRunResult(
        artifacts=artifacts,
        rows=tuple(rows),
        manifest=manifest,
        contexts=tuple(contexts),
        forcings=applied_forcings,
        discount_rate=discount_rate,
    )
