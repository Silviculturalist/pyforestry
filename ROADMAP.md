# Pyforestry Vision and Rehaul Roadmap

## Executive Vision Snapshot

`pyforestry` is moving toward a contract-first simulation platform where:

- scientific kernels are explicit and auditable,
- simulation policy is composable and reproducible,
- regional growth happens by extension, not by core rewrites.

Strategic stance for this roadmap:

- Vision-first and non-timeboxed.
- Restructuring complete: equations in domain packages, building blocks in `/blocks/`, `formulas/` removed.
- Governance enforcement, determinism hardening, and catalog expansion are the current priorities.

Who this roadmap is for:

- Maintainers defining architecture and CI enforcement.
- Model contributors extracting kernels and adapters.
- Scenario developers building operational presets.
- Consumers who need stable interfaces and reproducible results.


### Normative status legend

This roadmap is strategic. `ARCHITECTURE.md` remains the canonical current policy.
To reduce policy-vs-vision ambiguity, normative language in this document uses status tags:

- `[CP]` Current Policy:
  - Already canonical in `ARCHITECTURE.md` or active repository policy.
- `[TD]` Target-State Directive:
  - Intended future-state behavior for rehaul alignment.
- `[IE]` Illustrative Example:
  - Pseudocode or operational examples; not a claim of current implementation.
- `[FAP]` Future Amendment Proposal:
  - Requested change to canonical policy in a future revision.

Interpretation defaults:

- If a statement in this roadmap is not explicitly tagged, treat it as `[TD]`.
- When any `[TD]` statement conflicts with canonical policy, `ARCHITECTURE.md` wins.


## Execution Spine (Now / Next / Later)

This spine is capability-sequenced and non-timeboxed. It is intended to reduce design churn
while preserving the roadmap's strategic posture.

- `Done` (restructuring complete):
  - Gates A-C achieved. `/models` renamed to `/blocks/`. `formulas/` dissolved and removed.
    Equations live in domain packages (`growth/`, `height/`, `mortality/`, etc.).
    Building blocks live in `/blocks/`. Sweden simulation package established.
- `Now` (machine-checked governance and invariants):
  - Gate D emphasis: promote architecture dependency checks to standard CI evidence.
  - Gate E emphasis: harden determinism/artifact checks as release-gating invariants.
- `Next` (scaled rollout):
  - Gate F emphasis: compatibility-facade lifecycle governance and expanded multi-region rollout.

Spine rule:

- This sequence is intentionally not date-based; progression depends on gate evidence and
  conformance outcomes.

## 1) North-Star Vision

`pyforestry` should operate as a layered scientific platform with strict separation of concerns:

- A scientific formula library with explicit unit-bearing contracts and source-traceable implementations.
- A simulation operating layer with policy-driven orchestration, reproducible execution, and pluggable runtime backends.
- A composable regional platform where each new region adds formula kernels, adapters, and presets without changing core orchestration logic.

This roadmap is vision-first and non-timeboxed. It defines target operating capabilities, not a dated delivery calendar.

### Vision principles

The target platform should optimize for these principles in all architecture decisions:

- Scientific fidelity:
  - Formula behavior is source-traceable, explicit in units, and validated against parity references.
- Reproducibility by default:
  - Identical inputs and seed lineage produce equivalent stochastic outcomes across execution modes.
- Composability over convenience coupling:
  - Regional extensions compose through contracts, not through shared mutable internals.
- Observability and auditability:
  - Every simulation outcome is linked to manifest, artifacts, telemetry, and policy decisions.
- Governance as code:
  - Architecture constraints are enforced by CI and not left as prose-only expectations.

### Product surfaces and user modes

The platform vision supports three user modes without duplicating core logic:

- Research mode (formula-centric):
  - Users compare and validate equation families with explicit kernel interfaces.
- Scenario mode (planning-centric):
  - Users run policy/scenario presets with stochastic replication and operational reporting.
- Platform mode (maintainer-centric):
  - Contributors extend regions and runtimes under import-boundary and policy-lint constraints.

The same contracts should connect all three modes, organized in two tiers:

- Introspection tier:
  - `Describable` and `FormulaModuleDescriptor` for provenance, catalog, and audit.
- Execution tier:
  - Equation functions (keyword-argument) in domain packages as scientific core.
  - `GrowthModel` in blocks as composable building-block runtime interface.
  - `SimulationPreset` as operational orchestration layer.
  - `ParityCase` as regression and scientific trust anchor.

### North-star outcomes (what success looks like in use)

The desired end-state is:

- A new region can be added without editing shared runtime orchestration code.
- A scenario can be configured once and executed equivalently in local, parallel, and pipeline environments.
- Stochastic runs produce reproducible uncertainty envelopes, not opaque random drift.
- Migration work can proceed aggressively while preserving explicit compatibility contracts.
- Architecture violations are detected automatically before merge.

### Explicit anti-goals

To keep the vision crisp, the roadmap does not aim for:

- A monolithic “do-everything” regional model file architecture.
- Hidden orchestration logic inside formula kernels.
- Runtime features that bypass determinism and provenance requirements.
- Growth-by-exception where policy violations accumulate without exit criteria.

### Capability scorecard (target-state quick read)

| Capability domain | Current position | Target position | Signal of completion |
|---|---|---|---|
| Formula ownership | **Complete.** Equations live in domain packages (`growth/`, `height/`, `mortality/`, `ingrowth/`, `regeneration/`, etc.). Building blocks in `blocks/`. `formulas/` removed. | Formula kernels isolated in domain packages | No equation internals in `blocks/`; parity tests cover extraction units |
| Scenario orchestration | **Established.** `sweden/simulation/` has presets (Elfving 2010, Soderberg 1986), policy (management and scenario rulesets), orchestration (runbook), and mortality engine. | First-class `sweden/simulation` policy and preset package | Sweden presets run end-to-end with declared policy contracts |
| Reproducibility | Seed usage exists; `KeyedRNG` infrastructure in place; protocol not yet package-standard | Determinism protocol and replay checks are standard | Same config/seed replays to equivalent outputs across process counts |
| Runtime scalability | Solid base runtime exists; runtime + policy split started | Runtime + policy split with explicit interfaces | Parallel execution, checkpoint recovery, and telemetry are preset-standard |
| Governance enforcement | Policy document-driven only; no CI architecture linting; no `governance/` directory | CI-enforced architecture, lint, and exception controls | Architecture-lint and invariant gates block violating PRs |
| Migration discipline | **Restructuring complete.** `/models` renamed to `/blocks/`. `formulas/` removed. Equations in domain packages. Internal concern separation varies by module. | Consistent kernel/feature separation across formula packages | Internal separation consistent; provenance descriptors on all modules |


### Shared terminology and canonical naming

To reduce interpretation drift across docs, code, and CI, the rehaul should use stable terms:

- `Equation` (or `Formula`):
  - An individually usable published function or coherent group of functions from one publication,
    living in a domain package. No scenario policy ownership. Optionally described by a
    `FormulaModuleDescriptor` for introspection.
- `Block`:
  - A composable building block assembled from equations, or a self-contained published model
    system. Lives in `<region>/blocks/`. May contain a `GrowthModel` subclass, a cross-domain
    reconstruction workflow, or a complete stand-level simulator. Implements `Describable`
    for provenance.
- `Simulation Runtime`:
  - Generic execution substrate (context lifecycle, stage engine, parallel dispatch, checkpointing).
- `Scenario Policy`:
  - Region/scenario-specific orchestration: stage ordering, action selection, seed policy, guards.
- `Simulation Preset`:
  - Runnable composition of runtime + growth model + scenario policy + deterministic config.
    Implements `SimulationPreset` protocol.
- `Parity Case`:
  - Reproducible reference vector used to validate behavior during extraction and optimization.
  - Implements `ParityCase` protocol.

Canonical naming rule:

- If a term is used in public interfaces, policy docs, and CI checks, it MUST keep identical naming.
- Aliases (for example, "engine policy" vs "scenario policy") should be treated as documentation debt and removed.
- Retired terms: `FormulaKernel` (replaced by `FormulaModuleDescriptor` + direct functions),
  `ModelAdapter` (replaced by `GrowthModel` + `Describable`).
- Renamed: `/models` -> `/blocks` (target). "Models" is ambiguous in forestry; "blocks"
  communicates compositional intent.


## 2) Current-State Reality

Current repo facts relevant to the rehaul:

- Sweden regional simulation package is active:
  - `src/pyforestry/sweden/simulation/` with presets, policy, orchestration, mortality, and data modules.
- `src/pyforestry/sweden/blocks/` contains composable building blocks:
  - `GrowthModel` adapters: `elfving_2010.py`, `soderberg_1986_growth.py`
  - Self-contained model systems: `eko1985/`, `eriksson_1976.py`
  - Cross-domain workflows: `elfving_1982.py`, `elfving1982_hugin.py`, `elfving_hagglund_1975.py`
  - Thin facade stubs delegating to domain packages for backward compatibility.
- Equations live in domain packages:
  - `sweden/growth/elfving_2010/` (kernels: ~348, features: ~439 LOC)
  - `sweden/height/nystrom_2000.py`, `soderberg_1992.py`
  - `sweden/ingrowth/wikberg_2004.py` (~1767 LOC)
  - `sweden/regeneration/elfving_1992.py`, `elfving_2010.py`
  - `sweden/mortality/naslund_1986.py` (~1012 LOC)
  - Plus established packages: `siteindex/`, `volume/`, `bark/`, `biomass/`
- `formulas/` directory has been removed. No legacy stubs remain.
- Simulation runtime is substantial and stable:
  - `src/pyforestry/base/simulation/`
  - `src/pyforestry/simulation/` (contracts, growth module, stand composite, services, valuation, DP)
- Tiered protocol strategy implemented in `simulation/contracts.py`:
  - `FormulaKernel`, `ModelAdapter`, and `ScenarioPolicy` retired.
  - `SimulationPreset` and `ParityCase` retained as execution protocols.
  - `Describable`, `FormulaModuleDescriptor`, `SourceReference` added for introspection.
  - All 7 `GrowthModel` subclasses implement `Describable`. 11 equation modules expose `DESCRIPTOR`.
  - Provenance report script (`scripts/provenance_report.py`) discovers and lists all components.
- CI enforces coverage (91%+, 1224+ tests) but not architecture conformance:
  - No `governance/` directory exists. Architecture linting rules (AL001-AL008) are document-only.

Strategic interpretation:

- Restructuring is complete. Equations, blocks, and presets are in their target locations.
- Introspection tier is operational: 18 components discoverable via provenance report.
- The largest remaining risk is governance hardening: AL001/AL002 run in CI but AL003-AL008 are still document-only.

### Vision gap summary

The highest-value gaps between current state and vision are:

- Enforcement gap (highest priority):
  - Architecture intent exists, but CI-level dependency and policy enforcement is still target-state.
  - No `governance/` directory, no architecture lint CI job, no exception registry.
- Consistency gap:
  - Internal concern separation varies: Elfving 2010 has kernel/feature separation in `growth/`;
    other blocks (`soderberg_1986_growth.py`, `eko1985/model.py`) remain monolithic.
- Operational gap:
  - Determinism protocol, artifact contracts, and runbook invariants are defined in roadmap but not yet package-standard.
- Location gap (partially resolved):
  - Sweden simulation package is active with presets, policy, orchestration, and mortality.
  - Coverage is still incomplete for data adapters and reporting.

### Why now

Governance enforcement should happen now because:

- Extraction is done -- the structural foundation supports enforcement without blocking feature work.
- The contract protocols in `contracts.py` are drifting from actual patterns and risk becoming dead code.
- Parity fixtures and coverage infrastructure already exist, reducing the cost of adding conformance checks.
- Without CI enforcement, new contributions may inadvertently re-introduce the patterns the extraction eliminated.

## 3) Operational Contexts

The operating model should be defined through explicit contexts with ownership boundaries.

| Context | Purpose | Owns | Must Not Own | Current Paths | Target Paths |
|---|---|---|---|---|---|
| Data Contract Context | Stable cross-domain data contracts and units | Typed primitives, inventory contracts, metric containers | Scenario policy, orchestration routing, model family decisions | `src/pyforestry/base/helpers/`, `src/pyforestry/base/helpers/primitives/` | Same paths; hardened as strict dependency root |
| Formula Kernel Context | Scientific equation implementation | Coefficients, source-specific equation logic, formula-local guards | Global seed policy, stage ordering, scenario routing | `src/pyforestry/sweden/growth/`, `mortality/`, `siteindex/`, `volume/`, `bark/`, `biomass/`, `height/`, `ingrowth/`, `regeneration/` | Regional domain packages outside `/blocks` and outside simulation policy packages |
| Block Context (regional `/blocks`) | Composable building blocks: GrowthModel adapters, self-contained model systems, cross-domain reconstruction workflows | Block assembly, context binding, compatibility entrypoints | Long-lived orchestration policy | `src/pyforestry/sweden/blocks/` | `src/pyforestry/<region>/blocks/` with domain equations in domain packages |
| Simulation Runtime Context | Generic simulation execution mechanics | Context lifecycle, staged execution, dispatch runtime, checkpointing, parallel execution, engine hints | Region-specific scientific coefficients, equation internals | `src/pyforestry/base/simulation/`, `src/pyforestry/simulation/` | Same paths; refined into stable runtime substrate |
| Scenario Policy Context | Domain and scenario-specific sequencing decisions | Seed strategy, stage/ruleset policy, operation order, non-formula environmental guards | Formula internals and coefficient ownership | `src/pyforestry/sweden/simulation/` (presets, policy, orchestration, mortality) | Regional presets: `src/pyforestry/<region>/simulation/` with explicit policy contracts |
| Verification and Parity Context | Reproducibility and regression confidence | Reference vectors, parity harnesses, contract-level behavior checks | Production orchestration and model implementation ownership | `tests/sweden/test_rehaul_parity_harness.py`, `tests/sweden/fixtures/mortality/mortality_reference_cases.json`, broader `tests/` | Region-aware parity suites and architecture conformance checks |
| Integration and Consumer Context | User-facing composition and workflows | Notebooks, app glue, external pipeline composition | Core runtime internals, formula ownership | `docs/source/notebooks/`, external consumer code | Published presets and stable consumer APIs over adapters |
| Platform and Governance Context | Rule enforcement and architecture hygiene | Policy docs, CI checks, exception registry, contribution alignment | Formula or runtime feature implementation | `ARCHITECTURE.md`, `CONTRIBUTING.md`, CI config | Unified architecture governance with enforced conformance checks |


### Current-to-target context bridge (`ARCHITECTURE.md` -> roadmap model)

The canonical architecture policy currently defines five contexts. This roadmap expands
operational resolution to eight contexts for execution planning.

| Current context (`ARCHITECTURE.md`) | Target context(s) in roadmap | Status | Migration note |
|---|---|---|---|
| Context 1: Data Contract Context | Data Contract Context | `[CP -> TD]` direct mapping | No ownership change; tighten enforcement and dependency checks. |
| Context 2: Formula Context | Formula Kernel Context | `[CP -> TD]` naming refinement | Formula ownership is outside `/models`; next step is clarifying kernel contracts and consistent internal separation. |
| Context 3: Model API Context (`/models`) | Block Context (`/blocks`) | `[CP]` complete | `/models` renamed to `/blocks/`. `formulas/` dissolved and removed. Equations in domain packages. Blocks contain GrowthModel adapters, self-contained systems, and cross-domain workflows. |
| Context 4: Simulation Policy + Runtime Context | Simulation Runtime Context + Scenario Policy Context | `[FAP]` roadmap split proposal | Preserve canonical ownership now; split into two named contexts in next policy revision. |
| Context 5: Integration/Application Context | Integration and Consumer Context | `[CP -> TD]` direct mapping | Keep consumer composition separate from formula/runtime internals. |
| (No dedicated canonical context yet) | Verification and Parity Context | `[TD]` roadmap extension | Treat parity harnesses as first-class operational context for enforcement. |
| (No dedicated canonical context yet) | Platform and Governance Context | `[TD]` roadmap extension | Operationalizes policy linting, exceptions, and CI governance controls. |

Bridge rule:

- This table does not override canonical policy; it is a roadmap execution decomposition.

### Context interaction map (target-state data/control flow)

```text
Data Contracts
    ↓
Formula Kernels
    ↓
Model Adapters ───────┐
    ↓                 │
Simulation Runtime ◀──┤ Scenario Policy
    ↓                 │
Integration/Consumers ┘

Verification/Parity and Platform/Governance act as cross-cutting controls over all layers.
```

### Context handoff contracts

| Producer context | Consumer context | Contract artifact | Must hold true | Disallowed coupling |
|---|---|---|---|---|
| Data Contract | Formula Kernel | Typed input entities (units + required fields) | Unit invariants validated before equation execution | Formula kernels reaching into scenario flags to reinterpret base units |
| Formula Kernel | Model Adapter | Kernel function/class interfaces and typed outputs | Kernel outputs are deterministic for identical inputs | Adapter mutates kernel coefficients at runtime |
| Model Adapter | Simulation Runtime | Runtime model API (`grow5`, context update hooks, action registry) | Adapter remains policy-neutral and side-effect scoped | Runtime hardcodes region-specific species logic |
| Scenario Policy | Simulation Runtime | Ruleset/action streams and stage ordering config | Policy decisions are explicit and auditable | Policy bypasses action registry and edits internals directly |
| Simulation Runtime | Integration/Consumer | Structured artifacts + telemetry + summaries | Run manifest and required output schemas are complete | Consumer reads internal runtime mutable state directly |
| Verification/Parity | All execution contexts | Reference cases, invariant checks, replay checks | Parity and deterministic replay are required merge gates for extraction | Treating parity checks as optional for refactor PRs |


### Ownership model (RACI by context)

A scalable architecture also needs explicit human ownership boundaries.

| Context | Accountable (A) | Responsible (R) | Consulted (C) | Informed (I) |
|---|---|---|---|---|
| Data Contract Context | Platform architecture maintainer | Data contract maintainers | Formula and runtime maintainers | Integrations and scenario teams |
| Formula Kernel Context | Regional scientific lead | Formula maintainers | Verification/parity maintainers | Runtime and consumer teams |
| Model Adapter Context | Regional model API maintainer | Adapter maintainers | Runtime maintainers | Scenario and consumer teams |
| Simulation Runtime Context | Runtime lead maintainer | Runtime/core simulation team | Adapter and scenario maintainers | Regional maintainers |
| Scenario Policy Context | Regional scenario lead | Scenario preset maintainers | Runtime and formula maintainers | Consumer and ops teams |
| Verification and Parity Context | Verification lead | Test/parity maintainers | Formula and runtime maintainers | All contributors |
| Integration and Consumer Context | Product/integration owner | Notebook/app maintainers | Runtime and scenario maintainers | Maintainer group |
| Platform and Governance Context | Repo governance owner | CI/policy maintainers | All context owners | All contributors |

RACI guardrails:

- A PR that changes multiple contexts SHOULD list the accountable owner for each touched context.
- No context SHOULD be merged without at least one explicitly accountable maintainer.
- Exception ownership MUST map to the accountable owner in this table.


## 4) Scalability Architecture

Scalability must be explicit across five dimensions.

### Model Scalability

- Current state:
  - Sweden `blocks/` contains GrowthModel adapters and model systems; new equations land in domain packages.
  - Remaining concern: extraction depth varies -- some formula packages have kernel/feature separation
    (Elfving 2010), while most are flat monolithic files.
- Target state:
  - New formulas land in formula-kernel packages and are exposed through thin adapters only.
  - Consistent internal concern separation across all formula packages.
- Non-negotiable guardrail:
  - Adding a formula MUST NOT require edits to core runtime orchestration modules.

### Regional Scalability

- Current state:
  - Sweden simulation policy package exists at `src/pyforestry/sweden/simulation/` with presets,
    policy, orchestration, mortality, and data subpackages.
  - Norway exists as a formula-and-adapter package but does not yet have a simulation package.
  - Norway `/models` use a different pattern (explicit `GrowthModel` subclasses with imports)
    than Sweden's facade delegation. The two regions follow different adapter conventions.
- Target state:
  - New region support requires only:
    - formula kernels
    - blocks under `src/pyforestry/<region>/blocks/`
    - presets under `src/pyforestry/<region>/simulation/`
  - Consistent adapter pattern across regions.
- Non-negotiable guardrail:
  - Adding a region MUST NOT force region-specific branching into shared runtime core.

### Execution Scalability

- Current state:
  - Runtime capabilities exist with parallel execution and ensemble runners. Scenario contracts
    are not yet standardized as preset interfaces across regions.
- Target state:
  - A single scenario contract can run with Python execution, engine hints (Numba/JAX), and parallel workers.
- Non-negotiable guardrail:
  - Execution backend choice MUST NOT alter semantic scenario behavior.

### Team Scalability

- Current state:
  - Context ownership boundaries are clear in documentation. Facade-based `/models` reduce
    merge conflict probability. No CI enforcement of dependency direction yet.
- Target state:
  - Each context has clear ownership boundaries and allowed dependency direction, enforced by CI.
- Non-negotiable guardrail:
  - No module may own both formula internals and scenario orchestration policy.

### Quality Scalability

- Current state:
  - Architecture conformance is documented but not yet enforced by tooling.
  - Parity tests exist for some extraction units (Elfving 1982, Elfving 2010) but not all.
  - Test coverage is strong (91%+) with CI ratcheting.
- Target state:
  - Parity harnesses plus architecture checks gate structural drift as module count grows.
- Non-negotiable guardrail:
  - New architecture violations must be blocked or explicitly exception-registered.

### Capacity envelopes and execution profiles

| Execution profile | Typical workload | Preferred dispatch model | Required controls |
|---|---|---|---|
| `dev-single` | Local debugging, tens of stands | Single-process deterministic runner | Full manifest + deterministic replay on same machine |
| `team-batch` | Hundreds to low thousands of stands | Multiprocessing with deterministic partitioning | Seed lineage logging + invariant checks + checkpointing |
| `cluster-ensemble` | Large stochastic ensembles across scenarios | Process pool workers with optional thread fan-out for I/O | Stable chunk IDs, artifact contract completeness, retry/quarantine protocol |

Profile guardrails:

- Moving from one profile to another MUST NOT change scenario semantics.
- Partitioning logic MUST be deterministic and derived from stable identifiers.
- Process-count changes MUST preserve semantic equivalence under replay tolerance policy.

### Resource isolation and backpressure policy

To keep stochastic campaign runs stable at scale:

- Runtime workers SHOULD emit heartbeat telemetry at a fixed cadence.
- Dispatcher SHOULD cap in-flight contexts per worker to avoid memory spikes.
- Checkpoint writes SHOULD be staggered with jitter to avoid I/O burst contention.
- Failed contexts SHOULD move to a quarantine queue with reproducible retry metadata.


### Scalability fitness metrics (must be measurable)

| Dimension | Leading indicator | Failing signal | Required response |
|---|---|---|---|
| Model scalability | New kernel added with no runtime edits | Runtime core touched for formula-only change | Reject or redesign integration seam |
| Regional scalability | New region adds presets/adapters only | Region-specific branch added in shared runtime | Introduce region extension point and remove branch |
| Execution scalability | Throughput scales with worker count while preserving semantics | Process-count change causes semantic output drift | Block release path and investigate determinism protocol |
| Team scalability | Low cross-context PR conflict rate | Frequent merge conflicts in mixed-ownership files | Split seams and reassign ownership boundaries |
| Quality scalability | Parity/invariant pass rate remains stable as modules grow | Regressions rise with extraction volume | Slow extraction batch size and harden parity coverage |

Fitness metric rule:

- Each major extraction wave SHOULD report these indicators in the PR or release notes.
- Any failing signal SHOULD trigger an architecture review before further expansion.

### Vision-driven decision hierarchy

When tradeoffs appear, decisions should follow this precedence order:

1. Scientific integrity and reproducibility.
2. Architectural boundary correctness.
3. Backward compatibility strategy (explicit facades and deprecation lifecycle).
4. Runtime throughput and convenience.

Interpretation:

- Performance optimizations are encouraged, but not if they violate deterministic replay or boundary contracts.
- Compatibility is important, but not as a justification for indefinite mixed-module ownership.
- Fast delivery is valuable, but architecture debt must remain measurable, owned, and exit-bound.

### Decision rubric for contentious changes

For architecture-affecting PRs, reviewers should require explicit answers to:

1. Does this change improve or erode formula/policy boundary clarity?
2. Can this behavior be replayed deterministically with seed and manifest?
3. Is any compatibility debt introduced, and does it include an exit plan?
4. Are observability and artifact contracts preserved?
5. Would this decision make adding the next region easier or harder?

A change that fails questions 1 or 2 should not merge without an approved architecture exception.

## 5) Improvements Proposed for ARCHITECTURE.md

The following policy upgrades should be requested in a future `ARCHITECTURE.md` revision:

- Add a `Current vs Target` matrix per context.
- Add an explicit dependency-direction matrix defining allowed imports by context.
- Add an exception register template with owner, rationale, and exit criteria for each exception.
- Split current `Simulation Policy + Runtime` into two explicitly named contexts:
  - `Simulation Runtime Context`
  - `Scenario Policy Context`
- Add a policy-lints section describing CI-enforced architecture checks.
- Add a breaking-change posture section clarifying when API breaks are permitted for rehaul.
- Add contributor-alignment guidance requiring `CONTRIBUTING.md` references to remain consistent with architecture policy.

## 6) Rehaul Directives

### Completed directives

- Equations relocated to domain packages (`growth/`, `height/`, `ingrowth/`, `regeneration/`, `mortality/`).
- Building blocks relocated to `blocks/` (adapters, self-contained systems, reconstruction workflows).
- `/models` renamed to `/blocks` across Sweden and Norway. `formulas/` removed.
- Tiered protocol strategy implemented. Provenance descriptors on all components.
- Governance lint (AL001/AL002) wired into CI.

### Active directives

- Expand CI architecture conformance beyond AL001/AL002 (Gate D).
- Add parity tests for largest blocks (eko1985, soderberg1986, wikberg2004).
- Internal concern separation for monolithic blocks.
- Wire `Describable` into presets for nestable provenance chains.
- Implement minimal artifact output (`run_manifest.json`) from one preset (Gate E).

### Target directory strategy (`[TD]`)

The organizing principle is **reachability, not taxonomy**. Each published function should be:

1. Individually importable and documented.
2. Discoverable in a domain-natural location.
3. Composable into larger building blocks without duplication.

The directory a function lives in matters less than whether someone can find it, understand it,
and use it at whatever level they need -- single equation, building block, or full preset.

#### Three levels of composition

| Level | Description | Location |
|---|---|---|
| **Equations** | Individually usable published functions. Each is a coherent group from one publication. | Domain packages: `<region>/growth/`, `mortality/`, `siteindex/`, `volume/`, `bark/`, `biomass/`, `height/`, `ingrowth/`, `regeneration/` |
| **Blocks** | Composable building blocks assembled from equations or published as self-contained model systems. Includes GrowthModel adapters, cross-domain reconstruction workflows, and complete stand-level simulators. | `<region>/blocks/` `<region>/blocks/` |
| **Presets** | Runnable scenario compositions wiring blocks and equations into end-to-end simulation pipelines. | `<region>/simulation/presets/` |

#### Why "blocks" instead of "models"

Every equation in forestry is technically a "model" (Elfving 2010 model, Söderberg 1986 model).
The name "blocks" communicates the compositional intent: these are assembled building blocks, not
the equations themselves. A block might be:

- A `GrowthModel` adapter composing growth equations from `growth/` with features from `siteindex/`
  (e.g., Elfving 2010 growth block).
- A self-contained published model system where growth, mortality, and volume are
  interdependent and calibrated together (e.g., Eko 1985, Eriksson 1976).
- A cross-domain reconstruction workflow combining height, species composition, and
  imputation equations (e.g., NYSKOG from Elfving 1982).

#### Completed `formulas/` dissolution

The `formulas/` directory has been dissolved and removed. All content relocated:

| Former location | Content type | Current location |
|---|---|---|
| `elfving2010/kernels.py`, `features.py` | Growth equations | `growth/elfving_2010/` |
| `elfving_2010.py` (GrowthModel) | Adapter block | `blocks/elfving_2010.py` |
| `soderberg_1986_growth.py` | Growth block | `blocks/soderberg_1986_growth.py` |
| `soderberg_1992_height.py` | Height equations | `height/soderberg_1992.py` |
| `wikberg_2004_ingrowth.py` | Ingrowth equations | `ingrowth/wikberg_2004.py` |
| `naslund_1986.py` | Damage equations | `mortality/naslund_1986.py` |
| `nystrom_2000.py` | Height equations | `height/nystrom_2000.py` |
| `elfving_2010_regeneration.py`, `elfving_1992.py` | Regeneration equations | `regeneration/` |
| `elfving_1982.py`, `elfving1982_hugin.py` | Reconstruction workflow | `blocks/` |
| `elfving_hagglund_1975.py`, `nystrom_soderberg_1987.py` | Reconstruction helpers | `blocks/` |
| `eko1985/`, `eriksson_1976.py` | Self-contained systems | `blocks/` |

## 7) Target Public Interfaces and Type Contracts

### Protocol adoption strategy: Tiered introspection + execution (Option H)

`[CP]` Existing execution interfaces (`GrowthModel`, keyword-argument formula functions,
`SimulationPreset`, `ParityCase`) remain canonical. No wrapping or re-signing of execution
interfaces is required.

`[TD]` The protocol strategy separates two concerns that were previously conflated:

- **Introspection protocols** describe *what a component is*: identity, provenance, species
  applicability, units. These enable catalogs, audit reports, and provenance tracking without
  touching execution interfaces.
- **Execution protocols** describe *how a component runs*. These are the existing working
  interfaces (`GrowthModel`, direct function calls, `SimulationPreset`) which remain unchanged.

Design rationale:

- Formula functions stay as keyword-argument functions. This preserves IDE discoverability,
  type safety, and alignment with published equation notation.
- `GrowthModel` stays as the execution protocol for models. Its mode-negotiation, validation,
  and action-registry mechanics are mature and used across two regions.
- The mapping-style `FormulaKernel.compute()` protocol is retired. It conflated introspection
  (name, version, units) with an execution interface that no formula implements.
- Introspection metadata is added *alongside* components, not *around* them.

### Introspection tier (`[TD]`)

Target introspection contracts for `simulation/contracts.py`:

```python
@dataclass(frozen=True)
class SourceReference:
    """Bibliographic provenance for a scientific formula or model."""
    author: str
    year: int
    title: str
    appendix: str = ""
    note: str = ""

class Describable(Protocol):
    """Any component that declares its identity and provenance."""
    @property
    def component_id(self) -> str: ...
    @property
    def source(self) -> SourceReference: ...

class FormulaModuleDescriptor(Protocol):
    """Introspection contract for a formula module (not per-function)."""
    @property
    def component_id(self) -> str: ...
    @property
    def source(self) -> SourceReference: ...
    @property
    def species_groups(self) -> Mapping[str, frozenset[str]]: ...
    @property
    def units(self) -> Mapping[str, str]: ...
    @property
    def kernel_names(self) -> Sequence[str]: ...
```

Adoption pattern for formula modules:

- Each formula package exposes a module-level `DESCRIPTOR` object implementing
  `FormulaModuleDescriptor`. The descriptor sits next to the kernel functions,
  not around them. Kernel function signatures are not changed.
- Example: `sweden/growth/elfving_2010/__init__.py` exports `DESCRIPTOR`
  with source, species groups, units, and kernel names.

Adoption pattern for models:

- `GrowthModel` gains two properties: `component_id` and `source` (satisfying
  `Describable`). Subclasses override these with model-specific provenance.
- No changes to `requirements()`, `build_context()`, `update_step()`, or
  `available_actions()`.

Adoption pattern for presets:

- `SwedenScenarioPreset` already implements `SimulationPreset`. Add `Describable`
  properties (`component_id`, `source`) for catalog integration.

### Execution tier (`[CP]` existing, `[TD]` refinements)

| Interface | Status | Role | Location |
|---|---|---|---|
| `GrowthModel` | `[CP]` Canonical execution protocol for models. | Mode negotiation, context building, stepping, actions. | `src/pyforestry/base/simulation/growth_model.py` |
| Formula functions | `[CP]` Direct keyword-argument functions. | Pure scientific equations. Called by model `update_step()` and presets. | Domain packages (`growth/`, `mortality/`, `siteindex/`, etc.) |
| `SimulationPreset` | `[CP]` Working execution protocol. | Seed strategy, stages, rulesets, guards, required artifacts. | `src/pyforestry/simulation/contracts.py` |
| `ParityCase` | `[CP]` Test-utility protocol. | Reproducible reference vectors for regression trust. | `src/pyforestry/simulation/contracts.py` |

### Protocols retired by this strategy

| Former protocol | Reason retired | Replaced by |
|---|---|---|
| `FormulaKernel` | `compute(Mapping) -> Mapping` conflicts with the keyword-argument function pattern. No implementation existed. | `FormulaModuleDescriptor` (introspection only) + direct function calls (execution). |
| `ModelAdapter` | Simplified subset of `GrowthModel` missing critical methods (`requirements`, `can_build`, `default_attrs`). No implementation existed. | `GrowthModel` (execution) + `Describable` (introspection). |
| `ScenarioPolicy` | `evaluate() -> Sequence[ActionEvent]` pattern. No implementation existed; actual policy modules are static lookup dicts. | Deferred. Re-introduce when a real action-streaming policy layer is built. |

### Retained contracts and data types

The following non-protocol types in `simulation/contracts.py` are retained:

- `StageContract` -- used by simulation stages.
- `ActionEvent` -- used by orchestration and policy modules.
- `AssertionResult` -- used by parity test infrastructure.

### Current-equivalent references for target pseudocode APIs

| Target name in roadmap examples | Current nearest module/path | Current availability | Gap to close |
|---|---|---|---|
| `SwedenBaselinePreset` | `src/pyforestry/sweden/simulation/presets/_common.py`, `baseline.py` | Available via `build_baseline_preset()` and `run_sweden_preset(...)` | Expand preset catalog and scenario policy coverage beyond MVP |
| `BaselineRuleset` | `src/pyforestry/sweden/simulation/policy/management_rulesets.py`, `scenario_rulesets.py` | Available as explicit Sweden policy modules (baseline only) | Promote rule validation + governance checks from target to CI-standard evidence; add further scenarios only with sourced factors |
| `load_inventory_dataset` | `src/pyforestry/sweden/simulation/data/dataset_adapters.py`, `schema.py` | Partial MVP availability | Extend to canonical inventory ingest/validation API for external datasets |
| `Elfving2010Model` | `src/pyforestry/sweden/blocks/elfving_2010.py` | `GrowthModel` adapter composing `growth/elfving_2010/` equations | Add `Describable` properties (`component_id`, `source`) |
| `StepRunner` | `base/simulation/growth_model.py` + `simulation/services/parallel_runner.py` | No standalone `StepRunner` object | Define stage-runner abstraction or document current runtime loop as canonical |
| `ResultCollector` | Result aggregation patterns in tests/notebooks | No canonical collector class | Define artifact-first collector API in regional simulation reporting package |


### Units strategy (`[TD]`)

Preferred package-wide units approach for rehaul alignment:

- Use unit-bearing primitives at API boundaries where primitives exist.
- For float-based interfaces, require explicit unit suffix naming (for example `diameter_cm`, `height_m`, `site_index_dm`).
- Apply runtime unit validation at adapter/preset boundaries before kernel execution.

Disallowed pattern:

- Parallel competing unit systems inside the same module or interface family.

Units rule:

- Unit semantics must be either type-enforced or runtime-validated; documentation-only unit assumptions are insufficient for new target-state contracts.

### Determinism and parity thresholds (default `[TD]`)

Default thresholds should be explicit and centrally configurable:

- Canonical override path (target):
  - `governance/simulation/determinism_thresholds.yaml`
- Recommended default thresholds:
  - `byte_stability_required: true` for scoped artifacts only.
  - `byte_stability.scope_artifacts: ["scenario_summary.parquet"]`
  - `byte_stability.sort_keys.scenario_summary: ["scenario", "year", "run_group"]`
  - `byte_stability.fixed_dtypes_required: true`
  - `semantic_stability.scope_artifacts: ["run_level_timeseries.parquet", "stand_outcomes.parquet", "event_log.parquet", "quality_report.json"]`
  - `cross_process.max_relative_delta: 1e-6` for deterministic summary metrics.
  - `cross_process.max_absolute_delta: 1e-9` for scalar invariants.
  - `parity.max_relative_error: 5e-3` (0.5%) unless stricter source-specific bounds are defined.
  - `parity.max_absolute_error: 1e-6` for near-zero metrics.

Determinism implementation constraints:

- Canonical ordering:
  - Rows MUST be sorted by canonical keys before writing scoped byte-stable artifacts.
  - Aggregation/reduction order MUST be deterministic for reproducibility-critical summaries.
- Serialization stability:
  - Dtypes MUST be locked for contract artifacts.
  - Writer engine and major format library versions SHOULD be fixed for replay-sensitive pipelines.
  - Non-semantic metadata (for example volatile timestamps in artifact metadata) SHOULD be normalized or excluded for byte-stable outputs.

Threshold governance:

- `[CP]` Existing test tolerances remain authoritative until centralized config is adopted.
- `[TD]` New extraction units should reference explicit threshold IDs rather than ad hoc numeric literals.


### Formula kernel boundary FAQ (`[TD]`)

| Edge case | Belongs to context | Must not own |
|---|---|---|
| Feature engineering transforms required to evaluate an equation family | Formula Kernel Context (if transform is equation-local and source-grounded) | Scenario-level policy transforms dependent on run strategy |
| Numerical solvers used only to evaluate a model equation | Formula Kernel Context | Runtime scheduling/dispatch behavior |
| Data cleaning for ingestion quality and missing-field normalization | Data Contract / Integration contexts | Formula kernel ownership of dataset sanitation policy |
| Guard rails based on scenario context (for example storm-policy clamps not defined by source equation) | Scenario Policy Context | Formula kernel ownership of scenario policy and orchestration decisions |

Boundary rule:

- If logic depends on scenario-stage or campaign policy intent, it belongs outside the formula kernel.

### Artifact schema evolution policy (default `[TD]`)

Schema versioning and compatibility rules:

- Schema registry path (target):
  - `governance/simulation/artifact_schema_registry.yaml`
- Evolution rules:
  - Additive column additions -> MINOR version bump; existing required columns remain unchanged.
  - Required field removal/rename/type change -> MAJOR version bump.
  - Backward-compatible optional metadata additions -> PATCH or MINOR as documented in registry.
- Deprecation window:
  - Breaking schema changes require at least one documented deprecation cycle and at least two tagged releases before old schema retirement.
- Required migration documentation:
  - `docs/source/migrations/<artifact_schema_version>.md`
  - Must include old/new columns, compatibility notes, and upgrade examples.

### Appendix index for implementation detail

To keep this section decision-complete but concise, deep operational examples are moved to appendices:

- Appendix A: Sweden Operational Blueprint (`[IE]`)
  - Includes run configuration, dataset import, rulesets, stochastic loop, dispatch, checkpointing, and results flow.
- Appendix B: Rehaul Execution and Governance Detail (`[TD]`)
  - Includes extraction DoD, lint catalog, manifests, output contracts, dual-run migration protocol.


## 8) Governance and Enforcement

To operationalize this roadmap, governance should move from documentation-only to enforceable controls.

### Governance principles

- `[CP]` `ARCHITECTURE.md` remains canonical policy.
- `[TD]` `ROADMAP.md` defines strategic direction and proposed policy evolution.
- `[CP]` Any policy exception must be explicit, owned, and exit-bound.
- `[TD]` Normative status tags (`[CP]`, `[TD]`, `[IE]`, `[FAP]`) govern roadmap interpretation.

### How to use this roadmap

Use this document as an operating guide, not only as reference text:

- For architecture planning:
  - Start with `Operational Contexts`, `Vision-driven decision hierarchy`, and lint rules (`AL001`-`AL008`).
- For module extraction work:
  - Follow `Extraction blueprint`, then satisfy `Definition-of-done` gates.
- For scenario preset implementation:
  - Apply the Sweden example contracts: determinism, artifacts, invariants, KPI checks.
- For review and CI governance:
  - Treat `Capability progression gates` as promotion criteria from advisory to blocking checks.

Ownership loop:

- `ARCHITECTURE.md` defines current policy.
- `ROADMAP.md` proposes strategic hardening and future policy amendments.
- CI rules operationalize accepted policy.

### Change taxonomy and review protocol

Architecture-affecting work should be classified explicitly in every PR.

| Change class | Typical examples | Required review depth | Minimum merge gates |
|---|---|---|---|
| `C0` Documentation-only | Policy clarifications, examples, wording updates | 1 maintainer | Docs consistency checks |
| `C1` Internal extraction (non-breaking) | Move formula internals out of `/models` behind unchanged adapter APIs | Maintainer + domain reviewer | Parity pass + architecture-lint pass + no API drift |
| `C2` Contract extension | Add optional fields to manifests/artifacts/interfaces | Maintainer + runtime reviewer | Backward compatibility proof + deterministic replay pass |
| `C3` Behavioral policy shift | New stage ordering/ruleset semantics | Maintainer + scenario-policy reviewer | Scenario regression suite + explicit policy delta note |
| `C4` Breaking contract change | Remove facade, rename public adapter API | Maintainer quorum + release owner | Migration guide + deprecation history + major-version posture alignment |

Review protocol requirements:

- PRs MUST declare one change class (`C0`-`C4`).
- PRs in `C2`-`C4` MUST include a contract-delta section (inputs, outputs, compatibility notes).
- PRs touching extraction seams MUST reference an extraction unit and DoD gate output.

### Exception register lifecycle (target)

Every accepted exception should be tracked with operational metadata:

- `exception_id`
- owner (team/person)
- violating rule IDs
- rationale and scope
- mitigation in place
- explicit exit criteria
- review cadence

Exception governance rules:

- Exceptions without owner or exit criteria MUST NOT merge.
- Exceptions should expire automatically unless renewed with evidence.
- Expired exceptions should fail CI in blocking mode.

### Lint promotion matrix (advisory -> blocking)

| Rule ID | Advisory trigger | Blocking trigger |
|---|---|---|
| `AL001` | Existing mixed `/models` internals detected | New formula internals added to `/models` in changed files |
| `AL002` | Legacy forbidden edges observed | Any new forbidden import edge introduced |
| `AL003` | Scenario policy outside target path in legacy modules | New policy logic added outside simulation policy context |
| `AL004` | Exception register format incomplete | Non-conforming change without valid exception entry |
| `AL005` | Replay drift under investigation | Reproducibility check fails for merged-path presets |
| `AL006` | Missing optional artifact fields | Missing required artifact file or required manifest field |
| `AL007` | Deprecated facade without complete docs | Deprecated facade changed without warning + migration target |
| `AL008` | Soft contradiction in docs | Direct contradiction among policy/governance docs in changed scope |




### Governance rollout phases (`[TD]`)

To reduce process overhead, governance should be introduced in stages tied to gates and evidence artifacts.

- Phase 1 (Gates A-C achieved; Gate D focus):
  - Create `governance/` directory with rule definitions and exception registry schema.
  - Implement basic import-boundary CI check (`AL001`, `AL002`) for changed files.
  - All other lint rules advisory.
- Phase 2 (Gate D-E transition):
  - Enforce exception registry requirements for newly introduced exceptions.
  - Add determinism and artifact checks for Sweden presets in CI.
- Phase 3 (Gate E-F hardening):
  - Expand blocking rules beyond `AL001`/`AL002` as evidence stabilizes.
  - Govern facade deprecation lifecycle.

Rollout evidence rule:

- Each phase transition should reference gate evidence under `governance/architecture/gates/capability_gate_evidence.md`.

### Concrete governance artifacts and CI entrypoints (`[TD]`)

To operationalize lint/governance intent, roadmap rules should map to concrete repository artifacts.

| Governance concern | Target artifact path | Purpose | CI/command entrypoint |
|---|---|---|---|
| Architecture lint rules (`AL001`-`AL008`) | `governance/architecture/rules/architecture_lint_rules.yaml` | Canonical lint rule definitions and scope patterns | `python -m pyforestry.tools.archlint --rules governance/architecture/rules/architecture_lint_rules.yaml` |
| Exception register | `governance/architecture/exceptions/architecture_exceptions.yaml` | Declared, owned, exit-bound policy exceptions | `python -m pyforestry.tools.archlint --exceptions governance/architecture/exceptions/architecture_exceptions.yaml` |
| Exception schema | `governance/architecture/exceptions/architecture_exceptions.schema.json` | Validates required exception fields | `python -m pyforestry.tools.validate_exceptions governance/architecture/exceptions/architecture_exceptions.yaml` |
| Determinism thresholds | `governance/simulation/determinism_thresholds.yaml` | Central replay/parity tolerance configuration | `pytest -m determinism` |
| Artifact schema registry | `governance/simulation/artifact_schema_registry.yaml` | Schema version ownership and compatibility posture | `pytest -m artifact_schema` |
| Capability gate evidence | `governance/architecture/gates/capability_gate_evidence.md` | Gate A-F status evidence and references | Review gate during release checklist |
| CI workflow | `.github/workflows/architecture-governance.yml` | Runs architecture lint + docs consistency + replay checks | GitHub Actions `architecture-governance` job |

Operationalization rule:

- Until these artifacts exist, rules remain roadmap directives (`[TD]`) and must be treated as implementation backlog, not as already-enforced policy.

### Governance operating cadence

Governance should be continuous and lightweight rather than episodic.

- Per PR:
  - Enforce change classification (`C0`-`C4`) and relevant rule gates.
- Per extraction unit:
  - Publish DoD gate output and exception deltas.
- Per release candidate:
  - Run deterministic replay checks across process-count variants.
  - Reconcile policy docs (`ARCHITECTURE.md`, `ROADMAP.md`, `CONTRIBUTING.md`).
- Per major architecture increment:
  - Review exception register burn-down and promote additional advisory rules to blocking.

Cadence rule:

- If governance checks are skipped for any increment, that increment MUST be considered unstable.

### Enforcement model (target)

- Architecture conformance checks in CI:
  - detect new formula-heavy additions under `/models`
  - detect forbidden cross-context import directions
  - detect undocumented exceptions
  - validate Sweden preset invariants and required artifacts in integration tests
- Pull request template alignment:
  - require context classification for changed modules
  - require policy exception declaration when applicable
  - require explicit deprecation note for compatibility-facade changes
- Documentation consistency checks:
  - reject policy contradictions between `ARCHITECTURE.md` and `CONTRIBUTING.md`
- Verification controls:
  - maintain parity harness coverage for migrated modules during extraction.
  - add deterministic replay checks for stochastic scenario presets.


### Minimal viable Sweden preset (Gate B)

Minimum deliverable for Gate B should be intentionally small and execution-first.

Current status snapshot:

- `[CP]` Gate B baseline is implemented in this repository:
  - Sweden simulation package exists at `src/pyforestry/sweden/simulation/`.
  - Preset `baseline` is runnable. (A `storm_risk_high` scenario preset existed and was
    removed: its growth and disturbance multipliers were invented, with no publication or
    other source behind them. Disturbance scenarios remain a target, but must arrive with a
    source for their factors.)
  - Elfving 2010 composite preset (~1538 LOC) is the primary operational preset with
    regeneration, young-stand growth, mature growth, mortality, and valuation stages.
  - Soderberg 1986 composite preset (~159 LOC) provides a second model family.
- Remaining Gate B gaps:
  - Required output artifacts (`run_manifest.json`, `scenario_summary.parquet`,
    `quality_report.json`) are not yet emitted by presets. Presets return Python objects.
  - Determinism replay tests are not yet implemented as formal cross-process checks.

Required scope (remaining):

- Artifact-first output from at least one preset (minimum: `run_manifest.json`).
- One replay determinism test for the preset.
- One artifact contract/schema test for required outputs.

Explicitly optional at MVP stage:

- Advanced telemetry expansion.
- Full checkpoint orchestration.
- Multi-profile optimization beyond baseline execution profile.

### Capability progression gates (non-timeboxed)

| Gate | Prerequisites | Exit evidence required | Status | Primary owner context |
|---|---|---|---|---|
| Gate A: No new `/models` violations | None | `AL001` pass for changed files; no unauthorized mixed ownership expansion | **Achieved.** All `/models` are thin facades. | Platform and Governance + Model Adapter |
| Gate B: Sweden simulation presets established | Gate A | Preset package skeleton under `src/pyforestry/sweden/simulation/` with explicit policy contracts | **Achieved.** Presets, policy, orchestration, mortality, data subpackages active. | Scenario Policy |
| Gate C: Extraction pathways for largest mixed modules | Gates A-B | Extraction blueprint entries mapped to active work items and parity coverage links | **Achieved.** Equations in domain packages; blocks in `/blocks`; `formulas/` removed. | Formula Kernel + Model Adapter |
| Gate D: Dependency rules machine-checked | Gates A-C | CI job validates context import-direction constraints with rule evidence | **Not started.** No CI architecture linting exists. No `governance/` directory. | Platform and Governance |
| Gate E: Determinism and artifact invariants enforced | Gates B-D | Replay checks + artifact contract checks pass for Sweden stochastic presets | **Not started.** `KeyedRNG` infrastructure exists but no replay checks or artifact output in presets. | Simulation Runtime + Verification |
| Gate F: Compatibility facade lifecycle governed | Gates C-E | Facade deprecation metadata, migration notes, and planned removal criteria tracked and reviewed | **Not started.** Facades exist but have no deprecation warnings or removal timeline. | Model Adapter + Platform and Governance |

Gate dependency rule:

- A gate is not considered achieved unless prerequisites are already satisfied and evidence is linked in governance artifacts.


## 9) Risks and Countermeasures

| Risk | Why it matters | Countermeasure |
|---|---|---|
| Governance enforcement stalls | Without CI enforcement, architecture rules are prose-only and new contributions may re-introduce violations | Prioritize Gate D: create `governance/` directory and add basic import-boundary CI check |
| Protocol adoption drift | Contract protocols diverge further from actual patterns and become dead code | Decide protocol strategy: adapt protocols to match current patterns or refactor implementations |
| Consumer dependencies on facade behavior | Facade delegation may differ subtly from original behavior | Maintain parity tests for facades; plan deprecation lifecycle with migration notes |
| Policy-document drift | Strategy and policy can diverge over time | Keep `ARCHITECTURE.md` canonical and require roadmap proposals to reference policy deltas explicitly |
| Runtime-policy conflation persists | Without clean separation and enforcement, rehaul gains erode | Split scenario policy from runtime concerns and enforce with dependency checks |
| Over-fragmentation | Excessive decomposition can create operational overhead | Extract by concern boundaries with interface contracts, not by arbitrary micro-splits |
| Stochastic nondeterminism under parallel execution | Undermines reproducibility and trust in scenario comparisons | Enforce determinism protocol and replay checks across process-count variations |
| Silent action contract drift | Rulesets can emit invalid actions that fail late | Schema-validate action events pre-dispatch and fail fast with run metadata |
| Checkpoint corruption or partial writes | Recovery may restore invalid state and poison outputs | Use atomic checkpoint writes plus checkpoint integrity validation before restore |


### Operational tripwires and escalation responses

| Tripwire | Trigger condition | Severity class | Immediate response owner | Initial response SLA | Escalation SLA | Rollback / cutover criteria |
|---|---|---|---|---|---|---|
| Determinism tripwire | Same config/seed diverges across process counts | `SEV-1` | Runtime + Verification owners | <= 4 hours | <= 24 hours to architecture owners | Freeze cutover immediately; resume only after replay pass and root-cause closure |
| Parity tripwire | Extraction unit exceeds reference tolerance thresholds | `SEV-1` | Formula + Verification owners | <= 4 hours | <= 24 hours to regional scientific lead | Block merge/cutover; rollback to compatibility facade until parity restored |
| Governance tripwire | New forbidden import edge or undocumented exception | `SEV-2` | Platform/Governance owner | <= 1 business day | <= 2 business days to maintainer quorum | CI remains failing; no merge until exception/governance correction |
| Artifact tripwire | Required artifact missing or schema mismatch | `SEV-2` | Scenario Policy + Integration owners | <= 1 business day | <= 2 business days to runtime owner | Mark run invalid; quarantine outputs; rerun only after schema-compliant artifacts generated |
| Throughput tripwire | Campaign runtime exceeds agreed envelope without semantic regressions | `SEV-3` | Runtime + Operations owners | <= 2 business days | <= 5 business days to architecture owner | Tune dispatch/chunking; hold scaling cutover until throughput and determinism both pass |

Incident governance rule:

- Severity class and SLA compliance must be logged in the run diagnostics artifact and referenced in gate evidence.


## 10) Definition of Success

This roadmap is successful when the package operates according to capability-state outcomes:

- Completeness:
  - `ROADMAP.md` preserves all required vision, context, scalability, and governance sections.
- Architecture integrity:
  - Operational contexts remain explicit and mapped to current and target paths.
- Policy evolution readiness:
  - `ARCHITECTURE.md` improvement proposals are concrete and implementation-ready.
- Practical rehaul direction:
  - Aggressive directives remain path-specific and tied to real high-pressure modules.
- API clarity:
  - Tiered protocol strategy (introspection + execution) is adopted and non-ambiguous.
  - Introspection tier: `Describable`, `FormulaModuleDescriptor`, `SourceReference`.
  - Execution tier: `GrowthModel`, `SimulationPreset`, `ParityCase`, formula functions.
- Consistency:
  - Roadmap statements do not contradict current `ARCHITECTURE.md` hard rules unless presented as explicit future policy amendments.
- Operational solidity:
  - Sweden preset determinism protocol, invariants, and artifact contract are all enforceable via automated checks.
- Governance maturity:
  - CI blocks forbidden dependency edges and undocumented architectural exceptions.
- Migration discipline:
  - Compatibility facades follow explicit deprecation lifecycle with observable exit criteria.

### Success scorecard (measurable capability thresholds)

| Capability area | Minimum success signal |
|---|---|
| Boundary enforcement | `AL001`-`AL004` run in blocking mode for changed files without manual bypass |
| Reproducibility | Deterministic replay checks pass for Sweden presets across at least two process-count settings |
| Extraction progress | **Achieved.** Full restructuring complete. Equations in domain packages, blocks in `/blocks/`, `formulas/` removed. Next: internal concern separation and parity tests for largest blocks. |
| Policy consistency | No unresolved contradictions between `ARCHITECTURE.md`, `ROADMAP.md`, and `CONTRIBUTING.md` |
| Runtime resilience | Checkpoint recovery succeeds in fault-injection tests without artifact corruption |
| Consumer readiness | Required output artifacts are sufficient to drive planner and maintainer views without internal runtime access |


### Rehaul go/no-go checklist (release readiness)

- Boundary checks:
  - `AL001`-`AL008` pass at required enforcement level.
- Determinism checks:
  - Replay stability verified across at least two worker-count settings.
- Parity checks:
  - Extraction-unit parity and comparator gates pass.
- Artifact checks:
  - Required outputs and schema versions are complete and valid.
- Governance checks:
  - Exception register entries are owned, unexpired, and exit-bound.
- Consumer checks:
  - Planner, maintainer, and operations views render from artifact-only inputs.

Readiness rule:

- Any failed checklist item implies `NO-GO` until corrected or explicitly exception-approved.


## Appendix A) Sweden Operational Blueprint (`[IE]`)

### Detailed Sweden example (target-state operating flow) `[IE]`

The following is a concrete, end-to-end target-state example for Sweden. It is
architecture-level pseudocode, but intentionally detailed enough to guide
implementation decisions for globals, ingestion, stochastic execution, policy,
parallel dispatch, checkpointing, and result presentation.

Interpretation note:

- This appendix is illustrative (`[IE]`) and does not claim current API availability.
- Do not copy/paste this appendix as canonical runtime API.
- Prefer `pyforestry.sweden.simulation.templates` once available (planned target path).
- For current nearest implementations and migration gaps, see Section 7:
  `Current-equivalent references for target pseudocode APIs`.

#### 0) Target Sweden simulation package layout

```text
src/pyforestry/sweden/simulation/
  __init__.py
  presets/
    baseline.py
  policy/
    management_rulesets.py
    scenario_rulesets.py
  data/
    dataset_adapters.py
    schema.py
  orchestration/
    runbook.py
  reporting/
    summarize.py
    charts.py
```

Operational intent:

- Policy and orchestration move into `sweden/simulation/`.
- `sweden/blocks/` holds composable building blocks.
- Individual equations live in domain packages (`growth/`, `mortality/`, etc.).

#### A) Set globals and run configuration

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd

from pyforestry.base.simulation import ContextEnsemble, SimulationContext
from pyforestry.simulation.services import run_parallel
from pyforestry.sweden.blocks.elfving_2010 import Elfving2010Model

@dataclass(frozen=True)
class RunConfig:
    global_seed: int
    dt_years: float
    n_steps: int
    n_stochastic_runs: int
    processes: int
    checkpoint_every: int
    output_dir: Path

CONFIG = RunConfig(
    global_seed=20260206,
    dt_years=5.0,
    n_steps=20,
    n_stochastic_runs=200,
    processes=8,
    checkpoint_every=2,
    output_dir=Path("outputs/sweden"),
)

SCENARIOS = ("baseline",)
```

Operational intent:

- All globals are explicit and immutable.
- Reproducibility starts with a single seed root.

#### B) Import dataset and enforce input schema

```python
required_columns = {
    "stand_id",
    "plot_id",
    "species",
    "diameter_cm",
    "age_years",
    "latitude_deg",
    "longitude_deg",
}

inventory = pd.read_parquet("data/sweden/nfi_plot_inventory.parquet")
missing = required_columns - set(inventory.columns)
if missing:
    raise ValueError(f"Missing required dataset columns: {sorted(missing)}")

def build_stand_from_group(group: pd.DataFrame):
    # Target-state adapter:
    # dataset rows -> pyforestry Stand + Site + attrs used by presets
    return sweden_inventory_group_to_stand(group)

stands = [
    build_stand_from_group(group)
    for _, group in inventory.groupby("stand_id", sort=False)
]
```

Operational intent:

- Dataset contract validation is explicit and fails fast.
- Data-to-stand translation is adapter logic, not formula logic.

#### C) Define management rulesets and scenario rulesets

```python
Ruleset = Callable[[SimulationContext, dict], Iterable[tuple[str, dict]]]

def thinning_ruleset(ctx: SimulationContext, state: dict):
    if float(ctx.metrics["BasalArea"]["TOTAL"]) > 30.0 and state["years_since_thin"] >= 10.0:
        yield ("thin_fraction", {"fraction": 0.18})

def fertilization_ruleset(ctx: SimulationContext, state: dict):
    if state["year"] in (20.0, 40.0):
        yield ("fertilize", {"years": 10.0})

management_ruleset_registry: dict[str, Ruleset] = {
    "thinning": thinning_ruleset,
    "fertilization": fertilization_ruleset,
}

def scenario_ruleset(ctx: SimulationContext, scenario_name: str, state: dict):
    events: list[tuple[str, dict]] = []
    if scenario_name == "example_disturbance_scenario":
        # Illustrative only. pyforestry ships no disturbance scenario: any such
        # multiplier has to come from a source, not be chosen to look plausible.
        events.append(("apply_disturbance", {"multiplier": 1.5, "year": state["year"]}))
    return events
```

Operational intent:

- Management rulesets own silviculture policy.
- Scenario rulesets own disturbance policy (the disturbance example above is hypothetical).
- Neither owns formula internals.

#### D) Build stochastic replicas per scenario

```python
import hashlib

model = Elfving2010Model()
contexts = []
meta = []

def stable_run_seed(global_seed: int, stand_id: str, scenario_name: str, run_id: int) -> int:
    # Deterministic seed derivation for replay and multiprocessing consistency.
    key = f"{global_seed}|{str(stand_id).strip()}|{scenario_name.strip()}|{run_id}".encode("utf-8")
    digest = hashlib.sha256(key).digest()
    return int.from_bytes(digest[:8], "big") & 0xFFFFFFFF

for stand in stands:
    stand_id = getattr(stand, "id", "unknown")
    for scenario_name in SCENARIOS:
        for run_id in range(CONFIG.n_stochastic_runs):
            ctx = model.build_context(stand, mode_hint="tree_list")
            run_seed = stable_run_seed(CONFIG.global_seed, str(stand_id), scenario_name, run_id)
            ctx.attrs.update(
                {
                    "global_seed": CONFIG.global_seed,
                    "run_seed": run_seed,
                    "stand_id": stand_id,
                    "scenario": scenario_name,
                }
            )
            contexts.append(ctx)
            meta.append({"stand_id": stand_id, "scenario": scenario_name, "run_id": run_id})

ensemble = ContextEnsemble(contexts=contexts, model=model)
```

Operational intent:

- Stochastic runs are explicit context replicas.
- Seed derivation is deterministic per stand/scenario/run triple.

#### E) Step-wise update loop with multiprocessing and telemetry

```python
telemetry_rows = []

def telemetry_sink(idx: int, events: list[object]) -> None:
    for event in events:
        telemetry_rows.append({"context_idx": idx, "event": event})

def dispatcher(idx: int, ctx: SimulationContext) -> int:
    # Target policy: bucket by stand size / workload hints rather than naive round-robin.
    bucket = int(ctx.attrs.get("workload_bucket", idx))
    return bucket % CONFIG.processes

for step_idx in range(CONFIG.n_steps):
    year = (step_idx + 1) * CONFIG.dt_years
    management_payload = []

    for ctx, row in zip(ensemble.contexts, meta, strict=True):
        state = {
            "year": year,
            "years_since_thin": float(ctx.state.get("years_since_thin", 0.0)),
        }
        actions = []
        for _name, fn in management_ruleset_registry.items():
            actions.extend(fn(ctx, state))
        actions.extend(scenario_ruleset(ctx, row["scenario"], state))
        management_payload.append({"pre": (), "mid": tuple(actions), "post": ()})

    run_parallel(
        ensemble,
        dt=CONFIG.dt_years,
        steps=1,
        processes=CONFIG.processes,
        management=management_payload,
        dispatcher=dispatcher,
        telemetry_sink=telemetry_sink,
        write_back=True,
        include_history=False,
    )
```

Operational intent:

- Updates are explicit and step-wise.
- Rulesets are re-evaluated every step and every stochastic context.
- Multiprocessing uses deterministic dispatch strategy and captures telemetry.

#### F) Checkpointing and restart strategy

```python
def write_checkpoint(step_idx: int, context_idx: int, checkpoint: dict) -> None:
    # Target-state storage adapter: parquet/json/object store.
    persist_checkpoint(step_idx=step_idx, context_idx=context_idx, payload=checkpoint)

if (step_idx + 1) % CONFIG.checkpoint_every == 0:
    for context_idx, ctx in enumerate(ensemble.contexts):
        cp = ctx.checkpoint(include_history=False)
        write_checkpoint(step_idx, context_idx, cp)

# Recovery pattern:
# model = Elfving2010Model()
# restored_contexts = [SimulationContext.from_checkpoint(model, cp) for cp in read_last_checkpoints()]
# ensemble = ContextEnsemble(contexts=restored_contexts, model=model)
```

Operational intent:

- Long stochastic runs are restartable without recomputing from year 0.
- Checkpoint cadence is explicit in global config.

#### G) Collect, aggregate, and present results

```python
rows = []
for ctx, row in zip(ensemble.contexts, meta, strict=True):
    snap = ctx.snapshot()
    rows.append(
        {
            "stand_id": row["stand_id"],
            "scenario": row["scenario"],
            "run_id": row["run_id"],
            "year": float(snap["t"]),
            "basal_area_m2_ha": float(snap["metrics_total"]["BasalArea"]),
            "stems_ha": float(snap["metrics_total"]["Stems"]),
            "qmd_cm": float(snap["metrics_total"]["QMD"]),
        }
    )

results = pd.DataFrame(rows)
summary = (
    results.groupby(["scenario", "year"], as_index=False)
    .agg(
        mean_ba=("basal_area_m2_ha", "mean"),
        p05_ba=("basal_area_m2_ha", lambda s: s.quantile(0.05)),
        p50_ba=("basal_area_m2_ha", lambda s: s.quantile(0.50)),
        p95_ba=("basal_area_m2_ha", lambda s: s.quantile(0.95)),
        mean_stems=("stems_ha", "mean"),
    )
)

CONFIG.output_dir.mkdir(parents=True, exist_ok=True)
results.to_parquet(CONFIG.output_dir / "run_level_timeseries.parquet", index=False)
summary.to_parquet(CONFIG.output_dir / "scenario_summary.parquet", index=False)
pd.DataFrame(telemetry_rows).to_parquet(CONFIG.output_dir / "telemetry_events.parquet", index=False)
```

Presentation targets:

- Notebook trajectory plots (`p05/p50/p95`) by scenario.
- Final-year scenario delta table (baseline vs storm-risk).
- Replicate-level diagnostics for outlier runs and model debugging.

Operational intent:

- Result artifacts are explicit and portable.
- Quantile summaries communicate stochastic spread for decision support.

#### H) End-to-end responsibility split in this example

- Globals, scenario definitions, management and storm-risk rulesets: Scenario Policy context.
- Dataset import, schema checks, and presentation artifacts: Integration/Application context.
- Step execution, multiprocessing, telemetry, checkpointing: Simulation Runtime context.
- Equation internals and calibration math: Formula Kernel context.
- Runtime-compatible API bridge (`build_context`, update calls): Model Adapter context.

#### I) Hybrid concurrency model (threads + multiprocessing)

Target-state execution should use concurrency by workload type:

- Thread-level parallelism for I/O-heavy ingestion and stand materialization.
- Process-level parallelism for CPU-heavy simulation stepping.

```python
from concurrent.futures import ThreadPoolExecutor

groups = [group for _, group in inventory.groupby("stand_id", sort=False)]
with ThreadPoolExecutor(max_workers=16) as pool:
    stands = list(pool.map(build_stand_from_group, groups))

# Then run process-based simulation:
run_parallel(
    ensemble,
    dt=CONFIG.dt_years,
    steps=1,
    processes=CONFIG.processes,
    management=management_payload,
    dispatcher=dispatcher,
    telemetry_sink=telemetry_sink,
)
```

Operational intent:

- Threads accelerate loading and transformation without CPU-process overhead.
- Processes isolate stochastic simulation workers and scale compute deterministically.

#### J) Failure modes, quarantine, and recovery behavior

Target-state runbook must define deterministic failure handling:

```python
quarantined = []

for step_idx in range(CONFIG.n_steps):
    try:
        run_parallel(
            ensemble,
            dt=CONFIG.dt_years,
            steps=1,
            processes=CONFIG.processes,
            management=management_payload,
            dispatcher=dispatcher,
            telemetry_sink=telemetry_sink,
            write_back=True,
        )
    except RuntimeError as exc:
        # Degrade gracefully: keep run alive, mark affected batch, persist diagnostics.
        quarantined.append({"step_idx": step_idx, "error": str(exc)})
        persist_run_error(step_idx=step_idx, message=str(exc))
        continue
```

Failure policy requirements:

- A failed worker batch MUST NOT silently poison aggregate outputs.
- Quarantined contexts MUST be excluded from final aggregates unless explicitly restored.
- All exceptions MUST be persisted to a run-level diagnostics artifact.
- Restart MUST be supported from last valid checkpoint boundary.

#### K) Artifact contract for reproducibility

The Sweden preset should emit a standard artifact set on every run:

| Artifact | Required fields | Purpose |
|---|---|---|
| `run_manifest.json` | `global_seed`, config hash, scenario set, model version, git revision | Reproducibility anchor and provenance |
| `run_level_timeseries.parquet` | `stand_id`, `scenario`, `run_id`, `year`, core metrics | Full stochastic trajectory data |
| `scenario_summary.parquet` | scenario/year mean + quantiles | Decision and reporting layer |
| `telemetry_events.parquet` | context index, stage, event payload, timestamp | Runtime diagnosis and profiling |
| `errors.parquet` | step, context, exception class, message, traceback hash | Failure audit and quarantine logic |
| `checkpoints/` | serialized context checkpoints | Crash recovery and deterministic replay |

Operational intent:

- Artifact outputs are contract-driven, not ad hoc notebook outputs.
- Every decision table can be traced back to stochastic run provenance.

#### L) Operational KPIs and acceptance checks for Sweden preset

Minimum run-quality checks for a production-ready preset:

- Reproducibility KPI:
  - Same seed + same inputs MUST produce byte-stable summary outputs.
- Throughput KPI:
  - Process dispatch overhead should remain below an agreed budget per step.
- Stability KPI:
  - Quarantined context rate should remain below a defined threshold.
- Quality KPI:
  - Baseline and storm-risk scenarios should produce expected directional divergence.
- Governance KPI:
  - No architecture-rule violations introduced by preset implementation paths.

Example acceptance gate output:

```text
RUN STATUS: PASS
reproducibility: PASS
throughput_budget: PASS
quarantine_rate: PASS
scenario_divergence_check: PASS
architecture_conformance: PASS
```

#### M) Determinism protocol (non-negotiable)

To keep stochastic simulations scientifically auditable, the Sweden preset
must follow a deterministic execution protocol:

- Seed lineage:
  - Global seed MUST be recorded in `run_manifest.json`.
  - Context seed MUST be a pure function of `(global_seed, stand_id, scenario, run_id)`.
  - Python built-in `hash()` MUST NOT be used for simulation seeding.
  - Seed-input normalization (for example UTF-8 encoding and trimmed identifier strings) MUST be stable across platforms.
  - Seed derivation must use explicit-width integer handling (for example masked `uint32`) to avoid platform drift.
- Ordering:
  - Input stands MUST be sorted deterministically before context generation.
  - Scenario iteration order MUST be explicit and stable.
  - Management/scenario actions MUST be sorted or consistently generated before dispatch.
- Parallel replay:
  - Dispatcher function MUST be deterministic for identical context attrs.
  - Any backend-specific nondeterminism MUST be surfaced as a failed reproducibility KPI.
- Serialization:
  - Checkpoints and summaries MUST use stable field ordering and explicit dtype handling.

Determinism validation checks:

- Re-run same config twice and assert byte stability for scoped artifacts
  (default: `scenario_summary.parquet`) with canonical ordering and fixed dtypes.
- Re-run with identical config but different process count and assert semantic equivalence
  for non-byte-scoped artifacts within thresholds defined in Section 7
  (`Determinism and parity thresholds`) and configured via
  `governance/simulation/determinism_thresholds.yaml`.

#### N) Policy contract for actions and rulesets

Rulesets should be contract-driven to avoid accidental API drift.

Action contract (target shape):

```python
# (action_name, kwargs)
ActionEvent = tuple[str, dict]
```

Ruleset contract:

```python
Ruleset = Callable[[SimulationContext, dict], Iterable[ActionEvent]]
```

Ruleset requirements:

- Action names MUST map to registered `SimulationContext.do(...)` actions for the active model.
- Action kwargs MUST be schema-validated before dispatch.
- Rulesets MUST be side-effect free outside their returned action stream.
- Scenario rulesets MUST NOT mutate formula internals directly.

Pre-dispatch validation checks:

- Unknown action name -> hard error with scenario/run context metadata.
- Missing required kwargs -> hard error.
- Forbidden phase usage -> hard error.

#### O) Architecture dependency-direction rules (CI target)

The rehaul should enforce import directionality, not just path naming:

- `Formula Kernel` MAY import:
  - data contracts and primitives
  - formula-local utilities
- `Formula Kernel` MUST NOT import:
  - `pyforestry.simulation.*` orchestration policy modules
  - regional preset modules
- `Model Adapter` MAY import:
  - formula kernels
  - runtime contracts (`base/simulation`)
- `Model Adapter` MUST NOT import:
  - integration/reporting modules
- `Scenario Policy` MAY import:
  - adapters and runtime contracts
- `Scenario Policy` MUST NOT import:
  - formula coefficient internals directly

Proposed CI enforcement (vision):

- Static import boundary checker with allow/deny module regex rules.
- Block PRs that introduce new forbidden import edges.

#### P) Compatibility and deprecation policy for aggressive rehaul

Because this roadmap is aggressive, compatibility must still be explicit:

- Compatibility facade rule:
  - Legacy `/models` entrypoints MAY remain as forwarding facades during extraction.
- Deprecation signaling rule:
  - Facades MUST emit explicit deprecation warnings with migration target path.
- Removal rule:
  - Facades are removable only after:
    - parity checks pass on target modules
    - replacement path is documented
    - deprecation notice has existed for at least one documented release cycle.

Documentation obligations for each deprecation:

- Old API location
- New API location
- Behavioral differences (if any)
- Example migration snippet

#### Q) Sweden preset runbook invariants

A Sweden preset should be considered valid only if all invariants hold:

- Context invariant:
  - Each context has `stand_id`, `scenario`, `run_seed`, and valid mode metadata.
- Time invariant:
  - `t` advances exactly `dt_years` per successful step.
- Metrics invariant:
  - Required totals (`BasalArea`, `Stems`, `QMD`) remain finite and non-NaN.
- Quarantine invariant:
  - Quarantined runs are explicitly flagged and excluded from default summaries.
- Artifact invariant:
  - All required artifact files exist and contain required columns.
- Provenance invariant:
  - Run manifest includes config hash, git revision, and model identifier.

Invariant failure behavior:

- Any invariant violation moves run status to `FAIL`.
- Failures must include machine-readable diagnostics and human-readable summary.

## Appendix B) Rehaul Execution and Governance Detail (`[TD]`)

#### R) Extraction blueprint for highest-pressure Sweden modules

Restructuring is complete. Equations are in domain packages, building blocks in `/blocks`.
`formulas/` has been removed. The table below records the current state and remaining
internal separation work.

| Module | Status | Current location | Internal separation | Remaining work |
|---|---|---|---|---|
| `eko_1985` | **Complete.** | `sweden/blocks/eko1985/` (model, engine, site_context) | Partially separated. | Consider extracting pure equations to `growth/`. Add parity tests. |
| `soderberg_1986_growth` | **Complete.** | `sweden/blocks/soderberg_1986_growth.py` (~1908 LOC) | Not separated: monolithic file. | Extract equations to `growth/soderberg_1986/`. Add parity tests. |
| `wikberg_2004_ingrowth` | **Complete.** | `sweden/ingrowth/wikberg_2004.py` (~1767 LOC) | Not separated: monolithic file. | Consider kernel/feature split. Add parity tests. |
| `elfving_1982` | **Complete.** | `sweden/blocks/elfving_1982.py` + `elfving1982_hugin.py` | Separated: formulas vs wrappers. | Parity tests exist. |
| `elfving_2010` | **Complete.** | Equations in `sweden/growth/elfving_2010/` (kernels, features). Adapter in `sweden/blocks/elfving_2010.py`. | **Best-separated**: reference pattern. | Parity tests exist. DESCRIPTOR present. |
| `soderberg_1992_height` | **Complete.** | `sweden/height/soderberg_1992.py` (~1341 LOC) | Not separated: monolithic file. | Consider kernel split. |

Remaining work:

- Pursue consistent internal concern separation using Elfving 2010 (`growth/elfving_2010/`) as reference.
- Add dedicated parity tests for eko1985, soderberg1986, and wikberg2004 blocks.

#### S) Definition-of-done for each extraction unit

Every extraction unit (module seam, function family, or adapter split) must satisfy all checks:

- Behavior:
  - Existing parity vectors pass with unchanged tolerance policy.
- API:
  - Public signatures remain backward-compatible unless explicitly marked as planned break.
- Architecture:
  - New code follows context ownership rules and dependency-direction constraints.
- Determinism:
  - Stochastic replay checks remain stable across process-count variations.
- Documentation:
  - `ARCHITECTURE.md`/`ROADMAP.md` references and migration notes are updated.
- Deprecation:
  - Any compatibility facade has explicit warning and migration target.
- Observability:
  - Telemetry and artifact outputs remain complete and schema-valid.

Definition-of-done gate output (target):

```text
EXTRACTION UNIT: sweden/blocks/soderberg_1986_growth (internal concern separation)
parity: PASS
api_compat: PASS
architecture_rules: PASS
determinism: PASS
docs_sync: PASS
deprecation_contract: PASS
telemetry_artifacts: PASS
UNIT STATUS: PASS
```

Current DoD status:
- Parity: partial (tests exist for elfving1982, elfving2010; missing for soderberg1986, wikberg2004, eko1985).
- API compatibility: achieved. Consumer imports via  work.
- Architecture rules: AL001/AL002 enforced in CI.
- Determinism: not yet tested.
- Docs sync: ROADMAP, ARCHITECTURE, CONTRIBUTING aligned.
- Deprecation:  removed. No legacy stubs remain.

#### T) Architecture-lint rule catalog (CI target)

The roadmap should be backed by rule IDs so failures are actionable.

| Rule ID | Rule | Scope | Fail condition (example) |
|---|---|---|---|
| `AL001` | No new formula-heavy internals in `*/blocks` | Changed files under `src/pyforestry/*/blocks/` | New equation kernels added directly in `/blocks` |
| `AL002` | Context dependency direction must be valid | Python import graph for changed modules | Formula kernel imports scenario policy or integration/reporting modules |
| `AL003` | Scenario policy must reside in simulation policy packages | New ruleset/dispatch logic | Policy logic added in formula kernel or adapter internals |
| `AL004` | Exception registry required for non-conforming modules | PR metadata + policy files | Architectural exception introduced without owner + exit criteria |
| `AL005` | Determinism protocol must hold for stochastic presets | Sweden preset replay checks | Same seed/config produces different summary output |
| `AL006` | Required artifact contract must be complete | Integration outputs | Missing `run_manifest.json` or required output parquet artifacts |
| `AL007` | Deprecation lifecycle required for compatibility facades | Changed adapter facades | Deprecated path exists without warning and migration target |
| `AL008` | Documentation-policy consistency | `ARCHITECTURE.md`, `ROADMAP.md`, `CONTRIBUTING.md` | Contradictory guidance on `/models` ownership or allowed patterns |

Reference CI reporting format:

```text
ARCH-LINT REPORT
AL001: PASS
AL002: FAIL (forbidden import edge: sweden.growth.foo -> pyforestry.simulation.growth_module)
AL003: PASS
AL004: PASS
AL005: PASS
AL006: PASS
AL007: PASS
AL008: PASS
RESULT: FAIL
```

Lint adoption policy:

- Start in advisory mode for existing violations.
- Block only on newly introduced violations.
- Promote advisory checks to blocking checks as migration progresses.


AL001 detection strategy (target implementation detail):

- Path-based checks:
  - Flag new or modified files under `src/pyforestry/*/blocks/` for adapter-only conformance checks.
- AST/regex heuristics:
  - Detect likely coefficient-heavy internals via large numeric dict/list literals,
    dense coefficient constant clusters, and equation-style assignment density.
- Import-direction checks:
  - Deny imports from formula-internal packages into integration/reporting layers and enforce adapter boundaries.
- Optional annotation support:
  - Allow explicit adapter-only marker comments/docstring tags for modules that intentionally remain thin.

False-positive handling:

- If AL001 flags an acceptable edge case, the PR must include a scoped exception entry with owner,
  rationale, mitigation, and exit criteria in the exception register.


#### U) Scenario bundle contract and reproducibility manifest

Every Sweden preset run should be started from an explicit scenario bundle artifact:

- `global_config.yaml`:
  - Region, model adapter, time-step cadence, global seed, execution profile.
- `dataset_manifest.json`:
  - Input source URI, schema version, filtering assumptions, checksum.
- `scenario_policy.yaml`:
  - Ordered stages, management rulesets, scenario rulesets, guard policies.
- `runtime_profile.yaml`:
  - Worker count, chunking strategy, retry limits, checkpoint cadence.

Run manifest minimum shape (target):

```json
{
  "run_id": "sweden-baseline-2026-001",
  "region": "sweden",
  "model_adapter": "Elfving2010ModelAdapter",
  "global_seed": 1729,
  "scenario_set": ["baseline", "storm_high"],
  "dataset": {
    "uri": "s3://.../sweden_inventory.parquet",
    "checksum": "sha256:...",
    "schema_version": "inventory_v2"
  },
  "runtime": {
    "profile": "team-batch",
    "workers": 12,
    "chunk_strategy": "stable_hash_v1"
  },
  "policy_hash": "sha256:...",
  "git_revision": "<commit>",
  "started_at": "<timestamp>"
}
```

Manifest guardrails:

- Manifest fields required for replay MUST be present before simulation starts.
- Missing checksum, policy hash, or seed lineage MUST fail fast.

#### V) Results presentation blueprint (consumer-facing)

Sweden preset outputs should be presentation-ready without ad hoc post-processing.

Required output artifacts (target):

- `scenario_summary.parquet`:
  - One row per `(scenario, year, run_group)` with key forestry metrics and uncertainty bounds.
- `stand_outcomes.parquet`:
  - One row per `(stand_id, scenario, run_id, year)` for drill-down analysis.
- `event_log.parquet`:
  - Ordered action/ruleset events with deterministic event IDs.
- `quality_report.json`:
  - Invariant status, replay check status, quarantined run counts.

Presentation contract:

- Summary table MUST support side-by-side comparison of baseline vs stress scenarios.
- Output schema versions MUST be explicit and semver-tagged per Section 7
  (`Artifact schema evolution policy`).
- Consumer notebooks and dashboards SHOULD rely only on artifact schemas, not runtime internals.

Example stakeholder views:

- Planner view:
  - Scenario delta chart (`storm_high` vs `baseline`) with P10/P50/P90 volume trajectories.
- Model-maintainer view:
  - Parity and determinism health panel for extraction candidate modules.
- Operations view:
  - Worker throughput, retry/quarantine counts, and checkpoint recovery success rate.


#### W) End-to-end orchestration reference pseudocode (Sweden)

The target-state execution flow should be runnable from a single, explicit preset entrypoint.

```python
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import get_context

from pyforestry.sweden.simulation.presets import SwedenBaselinePreset
from pyforestry.sweden.simulation.policy import BaselineRuleset, StormHighRuleset
from pyforestry.sweden.simulation.dataset import load_inventory_dataset
from pyforestry.sweden.blocks.elfving_2010 import Elfving2010ModelAdapter
from pyforestry.simulation.runtime import SimulationContext, StepRunner
from pyforestry.simulation.results import ResultCollector

GLOBAL_SEED = 1729
SCENARIOS = ["baseline", "storm_high"]
N_REPLICAS = 64
N_PROCESSES = 12

# 1) Dataset ingest + schema contract check
inventory = load_inventory_dataset(
    uri="s3://inputs/sweden_inventory.parquet",
    schema="inventory_v2",
    enforce_checksum=True,
)

# 2) Build preset and adapters
model = Elfving2010ModelAdapter()
preset = SwedenBaselinePreset(
    global_seed=GLOBAL_SEED,
    model_adapter=model,
    management_rulesets={"baseline": BaselineRuleset()},
    scenario_rulesets={"storm_high": StormHighRuleset()},
)

# 3) Create deterministic context replicas
contexts = []
for stand in sorted(inventory.stands, key=lambda s: s.stand_id):
    for scenario in SCENARIOS:
        for run_id in range(N_REPLICAS):
            run_seed = preset.seed_for(stand.stand_id, scenario, run_id)
            contexts.append(
                SimulationContext.from_stand(
                    stand=stand,
                    scenario=scenario,
                    run_id=run_id,
                    run_seed=run_seed,
                    model=model,
                )
            )

# 4) Stage-level update loop
runner = StepRunner(
    stages=preset.stages(),
    guard_policy=preset.guard_policy(),
    action_registry=preset.action_registry(),
)

# 5) Hybrid dispatch: threads for input/output, processes for simulation compute
with ThreadPoolExecutor(max_workers=4) as io_pool:
    io_pool.submit(preset.write_run_manifest)

    with get_context("spawn").Pool(processes=N_PROCESSES) as pool:
        completed = pool.imap_unordered(runner.run_context, contexts, chunksize=16)

        collector = ResultCollector()
        for result in completed:
            collector.ingest(result)

# 6) Persist required artifacts + stakeholder views
collector.write_artifacts(output_dir="artifacts/sweden_baseline")
collector.write_summary_views(
    planner_view=True,
    maintainer_view=True,
    operations_view=True,
)
```

Operational expectations from this flow:

- Global seed, scenario policy, and stage ordering are preset-owned and reproducible.
- Formula kernels stay isolated behind adapter interfaces.
- Dispatch strategy can scale independently from scientific semantics.
- All outputs are artifact-driven and presentation-ready.

#### X) Output schema contract (minimum required columns)

| Artifact | Required columns | Purpose | Contract rule |
|---|---|---|---|
| `scenario_summary.parquet` | `scenario`, `year`, `run_group`, `volume_p10`, `volume_p50`, `volume_p90`, `basal_area_mean`, `stems_mean` | Scenario-level planning summaries | MUST be reproducible for identical config + seed |
| `stand_outcomes.parquet` | `stand_id`, `scenario`, `run_id`, `year`, `volume`, `basal_area`, `stems`, `qmd`, `status` | Stand-level diagnostics and drill-down | MUST include failed/quarantined status markers |
| `event_log.parquet` | `event_id`, `timestamp`, `stand_id`, `scenario`, `run_id`, `stage`, `action_name`, `action_kwargs` | Audit trail for policy actions and stage transitions | MUST preserve deterministic ordering keys |
| `quality_report.json` | `invariant_pass`, `replay_pass`, `quarantine_count`, `checkpoint_restore_pass`, `rule_violations` | Machine-readable quality and reproducibility report | MUST be emitted for every completed campaign |

#### Y) Dual-run migration protocol (legacy vs rehaul)

To enable aggressive extraction without blind cutover, run both paths during transition:

- Shadow mode:
  - Execute legacy adapter path and extracted path on the same scenario bundle.
- Comparator mode:
  - Compare parity vectors, summary deltas, and event-level rule application traces.
- Cutover mode:
  - Promote extracted path only after comparator thresholds pass and exceptions are closed.

Comparator gates (target):

- Metric deltas remain within parity thresholds defined in Section 7 (`Determinism and parity thresholds`).
- Determinism checks pass for both legacy and extracted path.
- Output schema contracts are identical or versioned according to Section 7
  (`Artifact schema evolution policy`).
- Consumer-facing reports show no critical regression.

Cutover guardrail:

- No compatibility facade should be removed until dual-run comparator gates pass.

Assumptions preserved in this roadmap:

- This is a vision-first, non-timeboxed document.
- Refactor posture is aggressive.
- Sweden is the first concrete rehaul template.
- `ARCHITECTURE.md` remains canonical policy.
- This document itself performs no code migration.
