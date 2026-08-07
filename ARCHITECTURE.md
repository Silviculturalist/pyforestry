# pyforestry Architecture Responsibility Policy

## Purpose and Non-Goals

### Purpose
This document defines ownership boundaries across `pyforestry` so simulation composition is
scalable, reproducible, and implementation decisions remain explicit.

### Non-Goals
This document is not:
- A formula catalog.
- A full migration pull request.
- A runtime implementation specification.

## Five Contexts and Ownership Matrix

The architecture is split into five contexts. Each context has strict boundaries.

### Context 1: Data Contract Context

- Owns:
  - Stable data structures and primitives shared across domains.
  - Canonical units, metric containers, and helper abstractions.
- Must define:
  - Type-level contracts that formula and simulation layers consume.
  - Minimal validation needed to protect type and unit correctness.
- Must not define:
  - Formula selection policy.
  - Scenario sequencing logic.
  - Orchestration managers.
- Primary package paths:
  - `src/pyforestry/base/helpers/`
  - `src/pyforestry/base/helpers/primitives/`

### Context 2: Formula Context

- Owns:
  - Scientific equations, coefficients, and model-local guards.
  - Equation-local dispatch where required by published model variants.
- Must define:
  - Explicit unit-bearing function/class interfaces for each equation family.
  - Source-grounded constraints local to that equation.
- Must not define:
  - Global simulation seed strategy.
  - Cross-model orchestration.
  - Scenario rulesets.
- Primary package paths:
  - Domain packages outside `*/adapters`, `*/systems` and `*/simulation`, for example:
    - `src/pyforestry/sweden/growth/`
    - `src/pyforestry/sweden/mortality/`
    - `src/pyforestry/sweden/siteindex/`
    - `src/pyforestry/sweden/volume/`
    - `src/pyforestry/sweden/bark/`
    - `src/pyforestry/sweden/biomass/`
    - `src/pyforestry/sweden/height/`
    - `src/pyforestry/sweden/ingrowth/`
    - `src/pyforestry/sweden/regeneration/`

### Context 3: Model Context (regional `/adapters` and `/systems`)

Two kinds of module live here, in separate directories because the question you
ask of each is different: a system is checked against its publication, an
adapter against the runtime contract.

- `*/adapters/` owns:
  - `GrowthModel` bindings that compose domain equations into simulation-facing APIs.
  - Cross-domain reconstruction workflows (e.g., NYSKOG).
  - No scientific coefficient literals. AL001 enforces this in both regions with
    no exception list; the alternatives (`*/systems/`, a domain package) are
    well-defined, so an exception would only record a misfiling.
- `*/systems/` owns:
  - Whole published growth-and-yield systems reproduced end to end (Eriksson 1976,
    Persson 1992, Petterson 1955, Ekö 1985, Elfving & Hägglund 1975).
  - Their coefficients, and the `GrowthModel` that drives them: the parts of these
    systems were fitted together and only reproduce the printed yield tables when
    used together, so a self-contained system owns its own interface.
- Must define:
  - Simulation-facing interfaces that bind runtime contracts to domain equations.
- Must not define:
  - New standalone equations (these belong in domain packages).
  - Long-lived orchestration policy.
  - Scenario rulesets.
- Primary package paths:
  - `src/pyforestry/<region>/adapters/`
  - `src/pyforestry/sweden/systems/` (Norway ships no whole system yet)

### Context 4: Simulation Policy + Runtime Context

- Owns:
  - Simulation execution contracts, staged runtimes, and orchestration.
  - Global policy: seeds, stage ordering, dispatch behavior, and rulesets.
- Must define:
  - Temporal stepping and operation ordering.
  - Policy dispatch across stages and model APIs.
  - Non-formula environment guards and cross-model constraints.
- Must not define:
  - Formula internals for scientific models.
  - Region-specific equation coefficients.
- Primary package paths:
  - Shared runtime:
    - `src/pyforestry/base/simulation/`
    - `src/pyforestry/simulation/`
  - Regional scenario configuration and orchestration:
    - `src/pyforestry/<region>/simulation/`, one per region, each with
      `policy/`, `presets/` and `orchestration/`. Sweden additionally holds the
      composite pipelines; Norway ships none yet.

#### Engine tiers within the simulation runtime

The simulation runtime has two distinct tiers. They compose; they do not
compete:

- **Model-adapter tier — `GrowthModel`** (`src/pyforestry/base/simulation/`).
  Per-stand biometric stepping: a scientific model builds a `SimulationContext`
  from a `Stand` and advances it via `update_step(ctx, dt)`. Every regional
  model adapter subclasses it (`Elfving2010Model`, `Soderberg1986Model`,
  `Eriksson1976Model`, `Eko1985Model`, and the Norway models). Presets drive
  this tier directly; it is the stable scientific-model interface.

- **Scheduling tier — `run_pipeline`** (`src/pyforestry/base/simulation/pipeline.py`).
  Runs an ordered sequence of `Step`s over the **whole stand**, one period at a
  time. Management is one type — `Policy = Callable[[ctx], Sequence[Action]]` —
  and everything that used to be a separate mechanism is a policy: a trigger is
  a policy with an `if` (`when`), a schedule is a policy with a clock comparison
  (`at_times`), a ruleset is a policy that reads a config.

These tiers compose rather than replace one another: a `GrowthStep` calls
`ctx.update_step(dt)`, which calls the model. The unit of scheduling is the
stand, not a part of one, because every model in this package couples its parts
to each other — Ekö 1985 through competition and cross-species mortality,
Elfving through whole-stand basal-area calibration. A step that wants cohorts
loops over them itself.

`run_pipeline` is the only scheduler. The composite pipelines' `step()` and
`run_projection()` call it rather than iterating their own `Step` tuples, so the
clock has one owner; `ContextEnsemble` is not a third scheduler but a batch
executor over many contexts, and delegates each context's period to the same
place.

This replaced three schedulers that did not know about each other:
`ctx.update_step(years, management={...})`, `SimulationSetup(triggers=...)`, and
`StageRuntime` over a `StandComposite` of `StandPart`s. `StageRuntime` scheduled
*parts*, so its only consumer had to make N−1 of every N stage invocations inert
with a latch and bypassed the dispatch machinery entirely for thinning; and
`SimulationSetup` caught every exception a trigger raised and wrote it into the
history as a row, so a management rule that was broken from the first step
produced a full run of plausible numbers.

Contracts are split by audience:

- Provenance/introspection vocabulary (`SourceReference`, `Describable`,
  `FormulaModuleDescriptor`) lives in `src/pyforestry/base/contracts.py`, because
  formula/domain modules across every region expose it; nothing above `base`
  reaches into the simulation package for it.
- Simulation-specific contracts (`SimulationPreset`) live in
  `src/pyforestry/simulation/contracts.py`. `ParityCase` and `AssertionResult`
  were removed: protocols with no implementer and no caller.

### Context 5: Integration/Application Context

- Owns:
  - Notebook/application composition, scenario setup, and external integration glue.
  - Product-specific pipelines and deployment-specific concerns.
- Must define:
  - Concrete scenario configurations and execution intents.
  - Environment- and consumer-facing integration boundaries.
- Must not define:
  - New formula internals.
  - Reusable core runtime contracts better placed in package simulation layers.
- Primary package paths:
  - `docs/source/notebooks/`
  - External consumer codebases and application layers using `pyforestry`.

## Hard Rules

The following rules are mandatory:

1. Global seed MUST be defined in simulation policy/global context.
2. Species group definitions outside formula internals MUST be defined in simulation context.
3. Selection of functions and invocation timing MUST be defined in simulation context.
4. Operation order outside formula bodies MUST be defined in simulation context.
5. Orchestration managers MUST NOT live outside simulation context packages.
6. Non-formula-specific environment constraints (including clamping) MUST belong to simulation context.
7. Rulesets MUST be defined and applied in simulation global context.

## `/adapters` and `/systems` Policy

- `src/pyforestry/<region>/adapters/` contains `GrowthModel` bindings and
  cross-domain reconstruction workflows. An adapter MUST NOT carry scientific
  coefficient literals: AL001 fails the build on any it finds, in either region,
  with no exception list and no budget.
- `src/pyforestry/<region>/systems/` contains whole published growth-and-yield
  systems, which MAY carry their own coefficients and MAY ship the `GrowthModel`
  that drives them.
- An individual published equation that stands on its own belongs in a domain
  package (`growth/`, `mortality/`, `volume/`, …), not in either of these.
- Both contain real code. No facade delegation stubs remain;
  `install_formula_facade` has been removed, and so has the last compatibility
  re-export, `norway/bollandsas.py`.

## Transitional Exceptions

- **`ctx.attrs` as a model input contract.** A model declares what it needs as a
  typed `Inputs` dataclass, resolved once when the context is built, so a missing
  or mistyped input fails there and by name. `Elfving2010Model` is the only
  adopter. Söderberg 1986, Ekö 1985, Eriksson 1976 and all four Norway models
  still read `ctx.attrs` by string key, where a mistyped name is
  indistinguishable from a site that has none of that value and surfaces only as
  a default -- or an exception -- once a kernel reaches for it. Typed `Inputs` is
  the contract new models MUST use; `ctx.attrs` is not removed and cannot be
  until those seven are migrated, which is per-model work and is not scheduled.

Completed migrations:

- All Sweden `/models` modules extracted and relocated to domain packages or the
  model tier.
- Mortality orchestration moved from `sweden/mortality/manager.py` to
  `sweden/simulation/mortality/engine.py`.
- `/models` renamed to `/blocks` across Sweden and Norway, then split into
  `/systems` (science) and `/adapters` (glue). The split retired AL001's
  registry of seven exempted modules and its Sweden-only scoping: both existed
  only because one directory held both kinds of module.
- Eko 1985 was re-expressed on a shared `StandComposite` + `StageRuntime`
  runtime, then moved off it: that runtime scheduled parts and Ekö steps whole
  stands, so the wrapper cost three types and an `_armed` latch and bought
  nothing. `EngineStand` iterates its own cohorts.
- Provenance/introspection contracts moved to `base/contracts.py`; the orchestration
  runtime `GrowthModule` renamed to `StageRuntime`; both are now removed along with
  `StandComposite`, `StandPart`, `SimulationSetup` and `CheckpointSerializer`,
  replaced by `run_pipeline` (~2,500 lines net).

Active package paths:

- Regional simulation presets/orchestration: `src/pyforestry/<region>/simulation/`
- Shared orchestration runtime: `src/pyforestry/simulation/`, `src/pyforestry/base/simulation/`

## Dispatch and Single-Responsibility Rules

- There MUST be one dispatch layer per concern:
  - Formula dispatch.
  - Simulation-stage dispatch.
  - Scenario-policy dispatch.
- A module MUST NOT own both:
  - Scientific equation internals, and
  - Scenario orchestration policy.

Allowed example:
- Formula in `src/pyforestry/sweden/mortality/root_rot_thor_stahl_stenlid_2005.py`
  with simulation policy in `src/pyforestry/simulation/` or `src/pyforestry/sweden/simulation/`.

Disallowed example:
- A single module that both implements formula coefficients and controls global stage/ruleset
  orchestration.

## Play-Ready Regional Simulation Presets

Runnable regional presets MUST live under:
- `src/pyforestry/<region>/simulation/`

Two unrelated things live in that package, and the distinction matters. They no
longer share a name:

- **Scenario configuration** (`ScenarioConfig`, one class in
  `src/pyforestry/simulation/presets.py` that each region subclasses) is
  *configuration*: a seed strategy, an ordered list of stage names, ruleset
  callables and a required-artifact list. It satisfies the `SimulationPreset`
  contract below, and `run_scenario()` executes all four of those: `stages()`
  resolves to `Step` objects through `simulation/stages.py`, `rulesets()` and
  `guard_policy()` are applied, and `seed_strategy()` seeds each stand. This is
  the tier that was to either grow a runtime or be deleted along with the mock
  runbook it fed; it grew one.
- **Composite pipelines** (`CompositePipeline`, with `Elfving2010Pipeline` and
  `Soderberg1986Pipeline` as siblings of it) are the runnable ones: stateful
  `initialize()`/`step()`/`run_projection()` objects that drive published models
  over a real `Stand`. They implement none of the `SimulationPreset` contract,
  and cannot: they build their own stand from a site rather than advancing one
  handed to them, which is also why `pyforestry.project(stand, ...)` cannot drive
  one. `get_pipeline()` reaches them, keyed by their own `component_id`s
  (`"elfving_2010_composite"`), so no name means both a pipeline and the
  growth model it drives.

`CompositePipeline` owns the eleven-phase period both pipelines run; a subclass
supplies the mature growth model and its provenance. Neither pipeline is the
other's base class, which one of them used to be.

The two tiers answer different questions and both are runnable. A pipeline is a
*published workflow* — one stand, one composite of named models, the period fixed
by the science. A scenario is a *study* — many stands, a stage order and rulesets
chosen by the analyst, and a manifest recording every choice so the summary can
be read back. `<region>/simulation/orchestration/` is the regional entry point
into the second; both regions have one.

Minimum preset contract:

- Seed handling:
  - Accept and persist a global seed strategy.
- Stage/ruleset declaration:
  - Declare stages and rulesets explicitly.
- Operation ordering:
  - Declare execution order outside formula internals.
- Environment guards:
  - Apply non-formula constraints (for example clamping and compatibility limits) in simulation
    policy.

## Migration Guardrails

- New work MUST follow this target architecture immediately.
- Legacy modules MAY remain temporarily but MUST NOT expand non-compliant responsibilities.
- Refactors SHOULD preserve public API behavior unless explicitly announced otherwise.
- This policy defines governance boundaries; it does not itself change runtime API signatures.

