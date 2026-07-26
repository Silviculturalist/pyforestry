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
  - Regional simulation presets/orchestration (target):
    - `src/pyforestry/<region>/simulation/`

#### Engine tiers within the simulation runtime

The simulation runtime has two distinct tiers. They compose; they do not
compete:

- **Model-adapter tier — `GrowthModel`** (`src/pyforestry/base/simulation/`).
  Per-stand biometric stepping: a scientific model builds a `SimulationContext`
  from a `Stand` and advances it via `update_step(ctx, dt)`. Every regional
  model adapter subclasses it (`Elfving2010Model`, `Soderberg1986Model`,
  `Eriksson1976Model`, `Eko1985Model`, and the Norway models). Presets drive
  this tier directly; it is the stable scientific-model interface.

- **Orchestration tier — `StageRuntime`** (`src/pyforestry/simulation/`; formerly
  `GrowthModule`, still importable under that deprecated alias). Runs ordered
  `Stage`s (growth → management → disturbance → valuation) over a
  `StandComposite` of `StandPart`s, with the shared RNG/telemetry/checkpoint
  services. It sequences growth together with management, disturbance, and
  valuation across multi-part stands.

These tiers compose rather than replace one another. The reference example is
Eko 1985: `Eko1985Model` is a `GrowthModel`, and internally it carries its
species cohorts as `StandPart` model views inside a `StandComposite` and runs
its whole-stand growth step as a stage inside a `StageRuntime`. A `StageRuntime`
growth stage ultimately drives model growth — it does not supersede the
`GrowthModel` interface.

Contracts are split by audience:

- Provenance/introspection vocabulary (`SourceReference`, `Describable`,
  `FormulaModuleDescriptor`) lives in `src/pyforestry/base/contracts.py`, because
  formula/domain modules across every region expose it; nothing above `base`
  reaches into the simulation package for it.
- Simulation-specific contracts (`StageContract`, `SimulationPreset`,
  `ParityCase`, …) live in `src/pyforestry/simulation/contracts.py`, which also
  re-exports the base provenance types for convenience.

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

No active transitional exceptions are currently registered in this document.

Completed migrations:

- All Sweden `/models` modules extracted and relocated to domain packages or the
  model tier.
- Mortality orchestration moved from `sweden/mortality/manager.py` to
  `sweden/simulation/mortality/engine.py`.
- `/models` renamed to `/blocks` across Sweden and Norway, then split into
  `/systems` (science) and `/adapters` (glue). The split retired AL001's
  registry of seven exempted modules and its Sweden-only scoping: both existed
  only because one directory held both kinds of module.
- Eko 1985 re-expressed on the shared `StandComposite` + `StageRuntime` runtime
  (the flagship example of the two engine tiers above).
- Provenance/introspection contracts moved to `base/contracts.py`; the orchestration
  runtime `GrowthModule` renamed to `StageRuntime` (old name kept as a deprecated alias).

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

Two unrelated things currently answer to "preset" in that package, and the
distinction matters:

- **Scenario presets** (`SwedenScenarioPreset`, `NorwayScenarioPreset`) are
  *configuration*: a seed strategy, an ordered list of stage names, ruleset
  callables and a required-artifact list. They satisfy the `SimulationPreset`
  contract below. Nothing executes them yet — `guard_policy()` and `rulesets()`
  have no runtime caller, and `stages()` is recorded into a manifest rather than
  run. `emit_scenario_artifact_contract(...)` exercises the *artifact* contract
  from synthetic numbers and runs no model; its output is a schema fixture.
- **Composite pipelines** (`Elfving2010CompositePreset`,
  `Soderberg1986CompositePreset`) are the runnable ones: stateful
  `initialize()`/`step()`/`run_projection()` objects that drive published models
  over a real `Stand`. They implement none of the `SimulationPreset` contract.

Closing that gap — one preset concept with one runtime — is the subject of
`ARCHITECTURE_PROPOSAL.md` Moves 3 and 9.

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

