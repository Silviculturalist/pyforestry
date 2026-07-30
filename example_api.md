# Example API v2: Presets, Mixed Models, Portfolio Runs, and Optimization

> **Status: aspirational design sketch. Almost nothing here exists.**
>
> This document proposes an API; it does not describe one. `StandState`,
> `SimContext`, `Preset`, `ModelRouter`, `ConfigBundle`, `Event`, `Cycle`,
> `simulate_stand`, `simulate_portfolio`, `optimize_policy`, `NotebookSession`
> and `SimulationService` are **not implemented**, and the `forestsim/` layout in
> §15 is not this package's layout. The `*/models` packages it refers to were
> renamed to `*/blocks`, then split into `*/systems` (whole published G&Y
> systems) and `*/adapters` (runtime glue).
>
> For what the package actually offers today, read `ARCHITECTURE.md` (the
> canonical current policy), `ROADMAP.md` (direction, with `[CP]`/`[TD]` status
> tags) and `ARCHITECTURE_PROPOSAL.md` (the concrete next moves, several of which
> supersede sections here). The only runnable code below is §18.3, which uses the
> real `Eriksson1976Model` API.

## Implementation Status (Current vs Target)

Current implementation (repository state):

- Regional `*/adapters` modules expose simulation-facing model bindings;
  `*/systems` holds whole published growth-and-yield systems.
- Sweden and Norway both execute their `SimulationPreset` configurations through
  `run_sweden_scenario(...)` / `run_norway_scenario(...)`, which project real
  stands with the Elfving (2010) and Kuehne (2022) models and write the three
  artifacts. `run_sweden_preset(...)`, which emitted the artifact contract from
  synthetic numbers and ran no model, is gone; see `STRUCTURAL_REVIEW.md` A2 for
  what it was.
- Optimization contracts in this document are target-facing and not implemented
  as runtime entrypoints.

Target architecture (this document):

- Keep `*/adapters` as thin typed bindings.
- Keep formula internals and coefficient-heavy kernels outside `*/adapters`.
  (Both are now enforced by AL001 rather than asserted here.)
- Stabilize unified runtime/preset/optimizer contracts across regions.

## 1) Use a 4-layer architecture, not just 2

### A) Model Catalog Layer

Purpose: discoverable equations and typed scientific components.

- `models/` contains equation families and typed interfaces.
- Model code remains independent from scenario orchestration.
- Models expose typed I/O and optional callable predictors.

### B) Runtime Layer

Purpose: state transitions and deterministic execution.

- `sim/state.py`: mutable stand state
- `sim/context.py`: mostly immutable runtime dependencies
- `sim/events/`: state transition events
- `sim/steps/`: cycle steps that propose/apply events
- `sim/engine.py`: single-stand and portfolio runners

### C) Preset Layer

Purpose: user-defined scenario bundles.

- `sim/presets/`: built-in presets
- `sim/preset_schema.py`: typed contract for custom presets
- `sim/preset_loader.py`: YAML/JSON + Python hook loading

### D) Optimization Layer

Purpose: search and decision support.

- `sim/objectives/`: NPV, harvest stability, risk-adjusted return
- `sim/constraints/`: hard and soft constraints
- `sim/optimize/`: GA, random search, Bayesian, etc.

## 2) Core runtime primitives

### `StandState`

Mutable, per-stand evolving state.

Suggested fields:

- identity: `stand_id`, `owner_id`, `region`, `site_class`
- time: `year`, `age`, `step_index`
- structure: trees/cohorts/diameter classes
- derived: `ba`, `qmd`, `vol`, `si`, `carbon`, `cash`
- lifecycle: `regen_status`, `last_clearcut_year`, `rotation_id`
- event log references: `event_ids`

### `SimContext`

Mostly immutable dependencies for one run.

Suggested fields:

- `clock`: timestep and calendar definitions
- `rng`: deterministic stream manager
- `configs`: resolved config bundle
- `market`: price/assortment providers
- `weather`: weather provider and scenario mapping
- `registry`: model/event/policy registries
- optional: telemetry, storage, logger

### `Event`

Deterministic state transition contract.

```text
Event.apply(state, ctx) -> EventResult
```

`EventResult` should include:

- updated state deltas
- removals/damage payloads
- generated follow-up events
- diagnostics and warnings

## 3) Make presets first-class and user-extensible

Users should be able to bring their own presets without editing package internals.

### `Preset` contract

```text
Preset:
  id: str
  describe() -> PresetMetadata
  model_router() -> ModelRouter
  cycle() -> Cycle
  config_bundle() -> ConfigBundle
  policy_factory() -> ManagementPolicy
  objective() -> Objective | None
  constraints() -> list[Constraint]
  reporters() -> list[Reporter]
```

### Custom preset inputs

Support both:

- declarative preset file (`yaml` or `json`)
- Python preset class (advanced use)

Recommended: declarative presets can reference registered plugin IDs.

## 4) Support heterogeneous models by design

Different stands should be able to use different model bundles in one simulation.

### `ModelRouter`

```text
model_router.select(stand_state, ctx) -> ModelBundle
```

`ModelBundle` might contain:

- growth model
- mortality model
- disturbance model
- regeneration model
- valuation model or connector

Routing keys can include:

- region
- species composition
- inventory type
- management regime
- age range

## 5) Add scoped config resolution

Users need weather, price, regeneration, and management configs at different scopes.

### `ConfigBundle`

```text
ConfigBundle:
  global
  scenario
  stand_overrides
  step_overrides
```

Resolution order:

1. step override
2. stand override
3. scenario config
4. global default

Typed config families:

- `WeatherConfig`
- `MarketConfig`
- `PriceListConfig`
- `RegenerationConfig`
- `DisturbanceConfig`
- `ValuationConfig`
- `PolicyConfig`

## 6) Make regeneration lifecycle explicit

Regeneration should not be hidden behind ad-hoc logic.

Recommended flow:

- `Clearcut` emits `RegenerationRequired`
- `RegenerationManager` (or policy) schedules `Plant` / `NaturalRegeneration`
- post-regeneration checks enforce stocking/species targets

Example event chain:

```text
Clearcut -> RegenerationRequired -> SitePrep -> Plant -> RegenEstablished
```

## 7) Separate proposing from applying events

Keep policy and hazard modules pure and testable.

- `PolicyStep`: proposes management events
- `HazardStep`: proposes disturbance events
- `ApplyEventsStep`: applies events
- `GrowStep`: runs growth/mortality/ingrowth models
- `ValuationStep`: values removals and costs
- `SummaryStep`: emits outputs

Default cycle:

```text
default_cycle = [
  PolicyStep(),
  ApplyEventsStep(),
  HazardStep(),
  ApplyEventsStep(),
  GrowStep(),
  ValuationStep(),
  SummaryStep(),
]
```

## 8) Portfolio API for wood supply and holding analysis

Add explicit portfolio entrypoints.

```text
simulate_stand(stand, preset, horizon, seed) -> StandResult
simulate_portfolio(stands, preset, horizon, seed, executor) -> PortfolioResult
resume_run(checkpoint) -> Result
replay_events(event_log, initial_state) -> Result
```

`PortfolioResult` should include:

- stand-level trajectories
- portfolio aggregates per time step
- harvest flow and mill supply views
- valuation outputs (NPV, cashflow, terminal value)
- constraint violations and diagnostics

## 9) Optimization API for policy search

Users should be able to optimize management decisions against objectives.

```text
optimize_policy(
  stands,
  preset,
  optimizer,
  objective,
  constraints,
  seed,
) -> OptimizationResult
```

### Objective and constraint contracts

```text
Objective.evaluate(portfolio_result) -> float
Constraint.check(portfolio_result) -> ConstraintResult
```

Use both:

- hard constraints (must pass)
- soft constraints (penalty terms)

Typical variables for GA:

- thinning intensity and timing by stand class
- clearcut threshold rules
- species choice at regeneration
- risk controls under weather/market scenarios

### 9.1 Example: optimize a thinning management agent to maximize timber volume

Use a parameterized thinning agent, then let the optimizer search its parameter space.
The objective below maximizes harvested timber (`m3sk`) over the full horizon.

```python
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ThinningGenome:
    thin1_age: int
    thin2_age: int
    thin3_age: int
    thin1_outtake_pct: float
    thin2_outtake_pct: float
    thin3_outtake_pct: float


class MaxTimberObjective:
    objective_id = "maximize_harvested_timber_m3sk"

    def evaluate(self, result: PortfolioResult) -> float:
        # No discounting: maximize physical harvested timber only.
        return sum(float(row.get("harvested_volume_m3sk", 0.0)) for row in result.portfolio_rows)


class ThinningAgent:
    policy_id = "optimized_thinning_agent"

    def __init__(self, genome: ThinningGenome) -> None:
        self.genome = genome

    def decide(self, state: StandState, ctx: SimContext) -> Sequence[Event]:
        schedule = (
            (self.genome.thin1_age, self.genome.thin1_outtake_pct),
            (self.genome.thin2_age, self.genome.thin2_outtake_pct),
            (self.genome.thin3_age, self.genome.thin3_outtake_pct),
        )
        events: list[Event] = []
        age = int(round(state.age))
        for trigger_age, outtake_pct in schedule:
            if age == trigger_age:
                events.append(ThinEvent(percent=outtake_pct))
        return events


ga = GeneticAlgorithm(
    search_space={
        "thin1_age": IntRange(30, 50),
        "thin2_age": IntRange(45, 70),
        "thin3_age": IntRange(60, 90),
        "thin1_outtake_pct": FloatRange(10.0, 35.0),
        "thin2_outtake_pct": FloatRange(10.0, 35.0),
        "thin3_outtake_pct": FloatRange(5.0, 30.0),
    },
    population_size=96,
    generations=60,
    crossover_rate=0.9,
    mutation_rate=0.12,
    maximize=True,
)

# NOTE: `GeneticAlgorithm`, `RandomSearch`, `BayesianOptimizer`,
# `IntRange`, and `FloatRange` are optimizer implementations that satisfy
# the `Optimizer` protocol in this document.

ga_result = optimize_policy(
    stands=stands,
    preset=timber_preset,  # policy_factory consumes candidate params as ThinningGenome
    optimizer=ga,
    objective=MaxTimberObjective(),
    constraints=[
        MinResidualBasalArea(min_m2_per_ha=10.0),
        MaxSingleThinPercent(max_percent=40.0),
    ],
    seed=2026,
)

best_agent = ThinningAgent(ThinningGenome(**ga_result.best_params))
```

### 9.2 Same agent with non-GA optimizers

The agent and objective stay identical; only the optimizer changes.

```python
random_result = optimize_policy(
    stands=stands,
    preset=timber_preset,
    optimizer=RandomSearch(search_space=ga.search_space, budget=2500, maximize=True),
    objective=MaxTimberObjective(),
    constraints=[],
    seed=2026,
)

bayes_result = optimize_policy(
    stands=stands,
    preset=timber_preset,
    optimizer=BayesianOptimizer(search_space=ga.search_space, budget=500, maximize=True),
    objective=MaxTimberObjective(),
    constraints=[],
    seed=2026,
)
```

This keeps the API stable: one `optimize_policy(...)` entrypoint, swappable optimizers,
and a policy artifact (`best_params`) that can be persisted as a thinning agent.

## 10) Data import and adapter contracts

For wood supply users, define ingestion as a stable API.

- `InventoryDataset` schema with unit metadata and provenance
- adapters for tree list, plot inventory, stand-level aggregates
- validation report with coercions, missing fields, and assumptions

Suggested entrypoint:

```text
load_inventory_dataset(path, schema, unit_map) -> list[StandState]
```

## 11) Reporting and artifacts

Define an artifact-first reporting interface so both planning and optimization runs produce consistent outputs.

- `EventLog` (audit trail)
- `StandTrajectoryTable`
- `PortfolioSummaryTable`
- `ConstraintReport`
- `OptimizationTrace`
- optional exports: parquet/csv/json

## 12) Determinism and reproducibility rules

- no global mutable state
- all randomness from keyed streams derived from `(master_seed, stand_id, stage, event)`
- event logs are replayable
- results independent of task scheduling order

## 13) Public API surface recommendation

Keep user-facing API compact:

- state/context: `StandState`, `SimContext`
- presets: `Preset`, `PresetLoader`, `register_preset`
- runtime: `Event`, `Cycle`, `default_cycle`, `simulate_stand`, `simulate_portfolio`
- configs: `ConfigBundle`, typed config classes
- valuation: `PriceList`, `MarketProvider`, `ValuationConfig`
- optimization: `optimize_policy`, `Objective`, `Constraint`
- results: `StandResult`, `PortfolioResult`, `OptimizationResult`

## 14) Two concrete user workflows

### Workflow A: Wood supply and holding valuation

1. Import inventory.
2. Choose or define preset (`market_scenario`, `weather_scenario`, `policy`).
3. Route models per stand via `ModelRouter`.
4. Simulate portfolio over horizon.
5. Evaluate supply profile, NPV, and risk metrics.

### Workflow B: Genetic algorithm for management policy

1. Define policy parameterization.
2. Define objective (`maximize NPV`, optionally risk-adjusted).
3. Add constraints (`harvest band`, `min habitat`, `operability`).
4. Run `optimize_policy(...)`.
5. Export best policy and thinning guides by stand class.

## 15) Minimal package layout

```text
forestsim/
  models/
  sim/
    state.py
    context.py
    engine.py
    cycle.py
    events/
    steps/
    presets/
    configs/
    valuation/
    objectives/
    constraints/
    optimize/
    results/
    io/
```

---

This version keeps your typed model identity while making portfolio analysis and policy optimization first-class citizens, including user-authored presets, mixed-model routing, and regeneration-aware lifecycle handling.

## 16) Implementation-ready protocol stubs

Use these stubs as the concrete v1 contracts for implementation.

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable


# --------------------------- Core runtime contracts ---------------------------

@runtime_checkable
class Event(Protocol):
    event_id: str
    name: str

    def apply(self, state: "StandState", ctx: "SimContext") -> "EventResult":
        ...


@dataclass(frozen=True)
class EventResult:
    follow_up_events: tuple[Event, ...] = ()
    removals_payload: Mapping[str, Any] = field(default_factory=dict)
    diagnostics: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class StandState:
    stand_id: str
    region: str
    site_class: str
    year: int
    age: float
    metrics: dict[str, float] = field(default_factory=dict)
    lifecycle: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    event_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SimContext:
    seed: int
    configs: Mapping[str, Any]
    market: Mapping[str, Any]
    weather: Mapping[str, Any]
    registry: Mapping[str, Any]


class CycleStep(Protocol):
    name: str
    def run(self, state: StandState, ctx: SimContext) -> tuple[StandState, tuple[Event, ...]]:
        ...


@dataclass(frozen=True)
class Cycle:
    steps: tuple[CycleStep, ...]
```

```python
# ------------------------------- Preset contracts -----------------------------

@runtime_checkable
class ModelRouter(Protocol):
    def select(self, state: StandState, ctx: SimContext) -> "ModelBundle":
        ...


@dataclass(frozen=True)
class ModelBundle:
    growth_model: Any
    mortality_model: Any | None = None
    disturbance_model: Any | None = None
    regeneration_model: Any | None = None
    valuation_model: Any | None = None


@dataclass(frozen=True)
class ConfigBundle:
    global_config: Mapping[str, Any] = field(default_factory=dict)
    scenario_config: Mapping[str, Any] = field(default_factory=dict)
    stand_overrides: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    step_overrides: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)


class ManagementPolicy(Protocol):
    policy_id: str
    def decide(self, state: StandState, ctx: SimContext) -> Sequence[Event]:
        ...


class Preset(Protocol):
    preset_id: str

    def model_router(self) -> ModelRouter:
        ...

    def cycle(self) -> Cycle:
        ...

    def config_bundle(self) -> ConfigBundle:
        ...

    def policy_factory(self) -> ManagementPolicy:
        ...

    def objective(self) -> "Objective | None":
        ...

    def constraints(self) -> Sequence["Constraint"]:
        ...

    def reporters(self) -> Sequence["Reporter"]:
        ...
```

```python
# -------------------------- Optimization and reporting ------------------------

class Objective(Protocol):
    objective_id: str
    def evaluate(self, result: "PortfolioResult") -> float:
        ...


@dataclass(frozen=True)
class ConstraintResult:
    passed: bool
    violation: float = 0.0
    details: Mapping[str, Any] = field(default_factory=dict)


class Constraint(Protocol):
    constraint_id: str
    hard: bool
    def check(self, result: "PortfolioResult") -> ConstraintResult:
        ...


class Reporter(Protocol):
    reporter_id: str
    def emit(self, result: "PortfolioResult", output_dir: str) -> None:
        ...


class Optimizer(Protocol):
    optimizer_id: str
    def run(self, fn, *, seed: int) -> Mapping[str, Any]:
        ...


@dataclass(frozen=True)
class StandResult:
    stand_id: str
    yearly_rows: tuple[Mapping[str, Any], ...]
    event_log: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class PortfolioResult:
    stand_results: tuple[StandResult, ...]
    portfolio_rows: tuple[Mapping[str, Any], ...]
    diagnostics: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OptimizationResult:
    best_params: Mapping[str, Any]
    best_score: float
    trace: tuple[Mapping[str, Any], ...]
```

```python
# ------------------------------ Engine entrypoints ----------------------------

def simulate_stand(
    stand: StandState,
    preset: Preset,
    *,
    horizon_years: int,
    seed: int,
) -> StandResult:
    ...


def simulate_portfolio(
    stands: Sequence[StandState],
    preset: Preset,
    *,
    horizon_years: int,
    seed: int,
    executor: str = "process",  # {"process", "thread", "serial"}
) -> PortfolioResult:
    ...


def optimize_policy(
    stands: Sequence[StandState],
    preset: Preset,
    *,
    optimizer: Optimizer,
    objective: Objective,
    constraints: Sequence[Constraint],
    seed: int,
) -> OptimizationResult:
    ...
```

## 17) Execution Modes (Notebook + Container Service)

Use one core runtime and expose two orchestration surfaces.

### 17.1 Shared execution profile

```python
from dataclasses import dataclass
from typing import Literal, Mapping, Any

ExecutionMode = Literal["interactive", "batch", "service"]


@dataclass(frozen=True)
class ExecutionProfile:
    mode: ExecutionMode
    emit_progress: bool = True
    persist_checkpoints: bool = False
    checkpoint_interval_steps: int = 0
    fail_fast: bool = True
    max_workers: int = 1
    metadata: Mapping[str, Any] = None
```

### 17.2 Notebook orchestration interface

Goals:

- incremental stepping
- interactive inspection of state and events
- optional continuation from checkpoints

```python
from dataclasses import dataclass
from typing import Sequence, Mapping, Any


@dataclass
class NotebookSession:
    run_id: str
    preset: Preset
    states: list[StandState]
    ctx: SimContext
    year_index: int = 0

    def step(self, years: int = 1) -> PortfolioResult:
        ...

    def run_to_end(self, horizon_years: int) -> PortfolioResult:
        ...

    def checkpoint(self) -> Mapping[str, Any]:
        ...

    @classmethod
    def resume(cls, payload: Mapping[str, Any]) -> "NotebookSession":
        ...


def start_notebook_session(
    stands: Sequence[StandState],
    preset: Preset,
    *,
    seed: int,
) -> NotebookSession:
    ...
```

Recommended notebook helpers:

- `result_to_dataframe(result) -> dict[str, Any]`
- `plot_portfolio(result, metric: str) -> Any`
- `compare_runs(results: Sequence[PortfolioResult]) -> Any`

### 17.3 Container service orchestration interface

Goals:

- async job lifecycle
- stateless workers
- persisted artifacts/checkpoints
- cancellation and status polling

```python
from dataclasses import dataclass
from typing import Literal, Mapping, Any, Sequence

JobStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]


@dataclass(frozen=True)
class RunRequest:
    preset_id: str
    seed: int
    horizon_years: int
    execution_profile: ExecutionProfile
    stand_refs: Sequence[str]  # IDs in inventory store/object storage
    config_overrides: Mapping[str, Any] = None


@dataclass(frozen=True)
class RunHandle:
    job_id: str
    status: JobStatus
    submitted_at: str
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class JobSummary:
    job_id: str
    status: JobStatus
    progress: float
    diagnostics: Mapping[str, Any]
    artifact_uri: str | None = None
    checkpoint_uri: str | None = None


class SimulationService(Protocol):
    def submit_run(self, request: RunRequest) -> RunHandle:
        ...

    def get_status(self, job_id: str) -> JobSummary:
        ...

    def cancel(self, job_id: str) -> None:
        ...

    def resume(self, checkpoint_uri: str) -> RunHandle:
        ...

    def get_artifacts(self, job_id: str) -> Mapping[str, str]:
        ...
```

### 17.4 Service worker contract

Container workers should run a pure function and emit deterministic artifacts.

```python
def run_job(request: RunRequest) -> JobSummary:
    # 1) Load stands from stand_refs
    # 2) Resolve preset + config bundle
    # 3) Execute simulate_portfolio(...)
    # 4) Persist artifacts + optional checkpoint
    # 5) Return JobSummary with artifact URIs
    ...
```

### 17.5 Determinism and portability requirements

- no process-local global state in models, policies, providers
- run identity: `run_id`, `seed`, `preset_hash`, `input_hash`, `code_version`
- all external providers are interface-injected and serializable by ID/config
- notebook and service must call the same core `simulate_*` APIs

## 18) Concrete Example: Eriksson1976 Under the New API

This example keeps the model wrapper thin for users/docs while keeping strict
typed boundaries around formula inputs and outputs.

### 18.1 Typed formula boundary (Formula Context)

```python
from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class Eriksson1976StepInput:
    bh_age_years: float
    stems_per_ha: float
    basal_area_m2_per_ha: float
    dominant_height_dm: float
    site_class: int
    growth_scaling: Literal[1, 2, 3]
    thinning: "ThinningRequest | None" = None


@dataclass(frozen=True)
class Eriksson1976StepOutput:
    next_bh_age_years: float
    stems_per_ha: float
    basal_area_m2_per_ha: float
    volume_m3sk_per_ha: float
    self_thinning_stems_removed: float = 0.0


class Eriksson1976Formula(Protocol):
    def step(self, x: Eriksson1976StepInput, *, years: float) -> Eriksson1976StepOutput:
        ...
```

Notes:

- Inputs/outputs are explicit and frozen.
- Illegal combinations fail at construction time or type-check time.
- Formula internals stay out of `*/adapters`.

### 18.2 Thin model adapter (Model API Context)

```python
from pyforestry.base.simulation import GrowthModel, Requirements, SimulationContext


class Eriksson1976Adapter(GrowthModel):
    """Thin runtime adapter around a typed Eriksson 1976 formula core."""

    def __init__(self, *, formula: Eriksson1976Formula, init: StandInit, program: ThinningProgram):
        self.formula = formula
        self.init = init
        self.program = program

    def requirements(self) -> Requirements:
        return Requirements(inventory="aggregate")

    def update_step(self, ctx: SimulationContext, dt: float) -> None:
        step_input = Eriksson1976StepInput(
            bh_age_years=float(ctx.state["t"]),
            stems_per_ha=float(ctx.metrics["Stems"]["TOTAL"]),
            basal_area_m2_per_ha=float(ctx.metrics["BasalArea"]["TOTAL"]),
            dominant_height_dm=float(ctx.attrs["h_dom_dm"]),
            site_class=int(ctx.attrs["site_class"]),
            growth_scaling=self.init.growth_scaling,
            thinning=ctx.state.pop("eriksson_1976_pending_thinning", None),
        )
        y = self.formula.step(step_input, years=dt)
        ctx.state["t"] = y.next_bh_age_years
        ctx.set_aggregate_metrics(
            ba_total=y.basal_area_m2_per_ha,
            stems_total=y.stems_per_ha,
        )
```

This preserves a stable, user-facing `GrowthModel` while delegating all
equation logic to typed formula objects. The existing `Eriksson1976Model`
can expose this behavior without changing its public constructor.

### 18.3 User-facing run (same ergonomics as today)

```python
from pyforestry.base.helpers import CircularPlot, Stand, Tree, TreeSpecies
from pyforestry.base.simulation import SimulationSetup
from pyforestry.sweden.systems.eriksson_1976 import (
    Eriksson1976ManagementSchedule,
    Eriksson1976Model,
    StandInit,
    ThinningProgram,
)

stand = Stand(
    plots=[
        CircularPlot(
            id="p1",
            area_m2=400.0,
            trees=[
                Tree(
                    species=TreeSpecies.Sweden.picea_abies,
                    diameter_cm=22.0,
                    weight_n=120.0,
                )
            ],
        )
    ]
)

init = StandInit(
    region="north",
    h100_m=24.0,
    start_bh_age=35.0,
    final_bh_age=90.0,
    stems=1800.0,
    basal_area=22.0,
)
program = ThinningProgram(
    interval_type="age",
    first_trigger=45.0,
    intervals=[10.0, 10.0, 0.0],
    outtakes=[20.0, 15.0, 0.0],
    outtake_type="percent",
)

model = Eriksson1976Model(init=init, program=program, track_history=True)
ctx = model.build_context(stand)  # mode comes from Eriksson1976Model.requirements()

schedule = Eriksson1976ManagementSchedule(program=program)
schedule.initialize(ctx)

SimulationSetup(
    start_t=float(ctx.state["t"]),
    end_t=90.0,
    dt=5.0,
    triggers=schedule.triggers(),
).run(ctx)
```

Result:

- User API stays compact (`StandInit`, `ThinningProgram`, `Eriksson1976Model`).
- Runtime orchestration lives in simulation setup/schedules.
- Formula safety comes from strict typed contracts, not ad-hoc dict plumbing.
