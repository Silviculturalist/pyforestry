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
and every seed -- so a summary row can be read back against the construction that
produced it without rerunning anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from pyforestry.base.helpers.stand import Stand
from pyforestry.base.simulation.core import SimulationContext
from pyforestry.base.simulation.growth_model import GrowthModel
from pyforestry.base.simulation.pipeline import run_pipeline
from pyforestry.simulation.artifacts import ScenarioArtifacts, git_revision, write_artifacts
from pyforestry.simulation.forcing import ForcingSet
from pyforestry.simulation.policy import ManagementPlan
from pyforestry.simulation.presets import ScenarioConfig, stable_seed
from pyforestry.simulation.provenance import as_manifest_entries, collect_provenance
from pyforestry.simulation.stages import (
    REMOVED_BY_STAGE_KEY,
    StageContext,
    build_pipeline,
)
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
    """One stand in a scenario run, with the id its summary row is keyed by."""

    stand_id: int
    stand: Stand


@dataclass(frozen=True)
class ScenarioRunResult:
    """What a scenario run produced.

    Attributes:
        artifacts: The three written files.
        rows: The summary rows, as written.
        manifest: The manifest payload, as written.
        contexts: One finished context per stand, in stand order, for a caller
            that wants the history rather than the summary.
    """

    artifacts: ScenarioArtifacts
    rows: tuple[Mapping[str, Any], ...]
    manifest: Mapping[str, Any]
    contexts: tuple[SimulationContext, ...] = field(default=())


def _stand_seed(scenario_seed: int, stand_id: int) -> int:
    """Derive a stand's seed from the scenario's, so order cannot affect it."""
    return stable_seed(scenario_seed, stand_id)


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
    disturbance_rate_per_year: float = 0.0,
    thin_at_years: Sequence[float] = (),
    start_year: float = 0.0,
    forcings: Optional[ForcingSet] = None,
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
            configuration declares a ``"valuation"`` stage.
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

    Returns:
        The artifacts, the rows, the manifest and the finished contexts.

    Raises:
        ValueError: If ``n_steps`` is not positive, no stands were given, a stage
            name is unknown, or a guard rejects an input.
    """
    if n_steps <= 0:
        raise ValueError(f"n_steps must be > 0, got {n_steps!r}.")
    if not stands:
        raise ValueError("A scenario run needs at least one stand.")

    scenario_seed = int(config.seed_strategy(global_seed=global_seed))
    guard_policy = dict(config.guard_policy())
    management = _resolved_management(config)
    applied_forcings = config.forcings().merge(forcings or ForcingSet())

    stage_context = StageContext(
        volume=volume,
        management=management,
        forcings=applied_forcings,
        guard_policy=guard_policy,
        valuation=valuation,
        disturbance_rate_per_year=disturbance_rate_per_year,
        thin_at_years=tuple(float(t) for t in thin_at_years),
    )
    pipeline = build_pipeline(config.stages(), stage_context, start_year=start_year)

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
        "stages": list(config.stages()),
        "rulesets_applied": _rulesets_applied(config),
        "forcings_applied": applied_forcings.as_manifest(),
        "guard_policy": {key: value for key, value in guard_policy.items()},
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
    )
