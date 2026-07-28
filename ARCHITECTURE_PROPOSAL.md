# Architectural improvements for `pyforestry`

Companion to `STRUCTURAL_REVIEW.md`. That document lists defects; this one proposes the
structure that makes most of them unrepresentable. Each move is independently shippable
and ordered so no step depends on a later one.

> **Status: all ten moves shipped; three had exit conditions this table originally
> overstated.** Both forks were decided as recommended — `Stand` is the state;
> `services` and `valuation` stayed, `model_view` and `dp` went. The five state
> representations are one, and the seven concepts a projection needed are
> `pf.project(...)`.
>
> A later adversarial pass found that three moves had been marked done against
> conditions written into their own text that were not yet met. Two are now
> closed; the third is recorded as what it is:
>
> - **Move 3 ("one scheduler")** — `run_pipeline` shipped, but the flagship did not
>   use it: `Elfving2010Pipeline.step()` iterated its own `Step` tuple and
>   `run_projection` looped over `step()`, so the package had two schedulers and
>   the composite used the other. Both now call `run_pipeline` (`375c78d`).
> - **Move 2 ("delete `ctx.attrs` as an interface")** — typed `Inputs` shipped and
>   has exactly one adopter, `Elfving2010Model`. Söderberg 1986, Ekö 1985,
>   Eriksson 1976 and all four Norway models still read `ctx.attrs`. The contract
>   exists and is the recommended one; `ctx.attrs` is not deleted and will not be
>   until those models are migrated, which is not scheduled.
> - **Move 9 ("`ScenarioConfig` either grows a runtime or is deleted along with the
>   mock runbook")** — the rename shipped, the tier did neither, and the
>   duplication between the two regions' copies went first (`98cd15c`). The
>   decision was then taken to wire it: `run_scenario()` executes `stages()`,
>   `rulesets()`, `guard_policy()` and `seed_strategy()` over real models, the
>   synthetic harness is deleted, and both regions have an entry point
>   (`d0d7666`). **Closed.**
>
> | Move | Landed in |
> |---|---|
> | 5 — one provenance import path | `194855d` |
> | 7 — `Tree.uid` populated | `118f168` |
> | 10 — docstring gate measures content (`AL004`) | `8045492` |
> | 1 — one state object | `550bd49` (estimator), `90605c6` (container) |
> | 4 — `blocks/` → `systems/` + `adapters/` | `78c3fd0` |
> | 2 — typed model inputs | `7fb7eaf` |
> | 3 — one pipeline | `6cb0f1b` |
> | 6 — one keyed RNG, injected (`AL005`) | `4ece3c9` |
> | 9 — "preset" renamed; C1's file I/O lifted | `d0df6b8` |
> | 8 — `pf.project(...)` | `e403e3d` |
> | 3/9 — the composites re-expressed as pipelines | `dc6be12` |
>
> C1's other half followed, in `e5d2777..dc6be12`: `Elfving2010Pipeline.step()` is
> now an ordered tuple of `Step` objects instead of 65 lines of hand-coded phases,
> each stating in its own docstring what it must follow and why. The twelve
> `_last_*` fields became one per-period record, and the three context rebuilds per
> period became one context per run — the pipeline's tree list *is* the context's
> plot list — so `ctx.history` survives a step for the first time. Söderberg came
> with it: its `_rebuild_context` override shrank to the one dict it actually
> changed, which is the confirmation that the abstraction fits more than one model.
> Proved pure against a fixture pinning four whole projection tables, every column
> and row, to 1e-9.
>
> Six bugs surfaced that the review had not found, each of which the new structure
> made visible: a diameter-class inventory keyed only by `"TOTAL"` reported the
> stand as empty (so a diameter-class model driven from an aggregate stand read a
> stand of nothing and reported success); `run_pipeline` written the obvious way
> hangs on a pipeline with no growth step; two unseeded `random.Random()` fallbacks
> made stochastic ingrowth and mortality silently irreproducible;
> `import pyforestry.base.aggregation` as a program's first import failed outright;
> the young-stand phase stopped running once a stand outgrew it, leaving the last
> young period's damage figures standing in every later snapshot row; and
> `AgeMeasurement`, `TopHeightMeasurement` and `SiteIndexValue` could not be
> deep-copied, so `pf.project` raised `TypeError` on any stand whose trees carried
> an age — the stand its own growth models are written for.
>
> **What remained, B6 (the Sweden/Norway ruleset divergence), was closed in
> `fd51233`** -- not by standardising two stubs but because wiring the runtime
> made the divergence load-bearing: the same key named a fraction in one region
> and a multiplier in the other, and one region defaulted silently where the
> other raised.

---

## The diagnosis in one line

**Five things model stand state and three things schedule time.** Nearly every defect in
the review is a consequence of that, not an independent bug.

### Five state representations

| # | Type | Where | Owns metrics? |
|---|---|---|---|
| 1 | `Stand` | `base/helpers/stand.py` | yes — plot-mean estimator with SE, species components, groups |
| 2 | `SimulationContext` | `base/simulation/core.py` | yes — its own `_metrics`, `_dclass`, own estimator |
| 3 | `StandComposite` / `StandPart` | `simulation/stand_composite.py` | yes — `_metric_from_model` duck-typed over 4 lookups |
| 4 | `EngineStand` / `EngineStandPart` | `sweden/blocks/eko1985/engine.py` | yes — `ba`/`qmd`/`stems`/`hk`/`vol` on the cohort |
| 5 | `list[Tree]` + rebuilt `Stand` | `elfving_2010_composite.py` | rebuilds #1 twice per step, discards it |

Two of these already disagree numerically by 2× (review A1). The rest of the fallout:

- A4 — `set_aggregate_metrics` writes to #2's store; `_refresh_metrics` overwrites it from #2's plots.
- A8 — #3 can't find metrics on an arbitrary view, so it returns `0.0`, and budget caps run on that.
- C2 — #5 exists because #2 can't hold the state, only carry it.
- C3 — #5 keys bookkeeping on `id(tree)` because no representation owns tree identity.
- C11 — `StandMetricView` is a sixth accessor bridging #1 into the #3 world.

### Three schedulers

```python
ctx.update_step(years, management={"pre": [...], "mid": [...], "post": [...]})   # core.py
SimulationSetup(triggers=[...], schedule=[...]).run(ctx)                          # dsl.py
StageRuntime(composite, stages=[...], management_rulesets={...}).run_cycle()      # stage_runtime.py
```

None knows the others exist. `SimulationSetup.run` reaches into `ctx._append_history` and
swallows every trigger exception into a history row. `StageRuntime`'s management tier is
unused even by its one consumer. The flagship composite uses none of them — it hand-codes
the ordering in `step()`, which is the honest admission that none of the three fit.

---

## Move 1 — One state object *(highest payoff, do first)*

**`Stand` is the state. `SimulationContext` stops owning metrics.**

`Stand` already proves it can hold a representation without trees: `_apply_angle_count_metrics`
populates `_metric_estimates` directly from tallies, no tree list. Generalise that.

```
base/aggregation/            # NEW — the single estimator, pure functions, no classes
    __init__.py              #   metrics(representation) -> MetricSet
    tree_list.py             #   the plot-mean estimator (SE, species components, groups)
    diameter_class.py
    aggregate.py
    angle_count.py
```

`Stand` gains an explicit `representation` and delegates to it:

```python
@dataclass
class Stand:
    site: Site | None
    area_ha: float | None
    representation: TreeList | DiameterClass | Aggregate | AngleCount
    top_height_definition: TopHeightDefinition
    attrs: dict[str, Any]
    # metric accessors unchanged: stand.BasalArea.TOTAL, stand.Stems(species), ...
```

`SimulationContext` becomes what its name says — the run's context, not a second stand:

```python
@dataclass
class SimulationContext:
    stand: Stand              # the one state
    clock: Clock              # t, dt, step_index
    rng: KeyedRNG             # injected, keyed (Move 6)
    history: list[Event]
    inputs: ModelInputs       # typed, resolved once (Move 2)
```

**Deleted:** `SimulationContext._metrics`, `_dclass`, `_recompute_metrics_tree_list`,
`_recompute_metrics_dclass`, `_normalize_*`, `set_aggregate_metrics`, `scale_stems`,
`set_diameter_class`, `metrics`, `StandMetricView`, `StandPart._metric_from_model`.
Mutation moves onto `Stand` (`stand.apply_mortality(rate)`, `stand.replace_representation(...)`),
where the estimator lives.

**Closes:** A1 (by construction — one estimator), A4, A8, C2, C11, and the `_dclass`
private-access in the reference model (C10).

**Cost:** touches `Stand`, `SimulationContext`, all 11 adapters (mechanically:
`ctx.metrics["BasalArea"]["TOTAL"]` → `ctx.stand.BasalArea.TOTAL`), and the eko1985 engine.
Test-visible only where A1's numbers were being asserted — and those assertions are wrong today.

---

## Move 2 — Typed model inputs; delete `ctx.attrs` as an interface

`ctx.attrs` is the real input contract for every model, and it is an untyped dict. The
flagship writes twelve keys into it twice per step (`site_index_m`, `dominant_species`,
`temperature_sum_dd`, `latitude_deg`, `altitude_m`, `distance_to_coast_km`,
`field_estimated_basal_area_m2_ha`, three `thinned_*` flags…) — several of which
`SwedishSite` already holds as typed attributes, re-derived by hand as floats.

```python
@dataclass(frozen=True)
class Elfving2010Inputs:
    site_index_m: float
    dominant_species: TreeName
    temperature_sum_dd: float
    latitude_deg: float
    altitude_m: float
    distance_to_coast_km: float
    thinned_0_10_years: bool = False
    thinned_11_25_years: bool = False

class Elfving2010Model(GrowthModel):
    Inputs = Elfving2010Inputs
    def resolve_inputs(self, stand: Stand, clock: Clock) -> Elfving2010Inputs: ...
    def update_step(self, ctx: SimulationContext, dt: float) -> None:
        x = ctx.inputs   # typed; no .get(), no default, no KeyError mid-step
```

Resolution happens once, in `build_context`. A missing input is a named error there rather
than a silent `.get(key, default)` twenty frames deep.

**Bonus:** `Inputs` field names *are* the unit contract the `FormulaDescriptor.units` map
currently duplicates by hand, and they give `catalog` something introspectable — "which
models can I run on the data I have?" becomes answerable.

**Closes:** C2. Makes A5 moot (inventory provenance becomes a typed field on the
representation, not an attrs string set by an inverted `if`).

---

## Move 3 — One scheduler: an ordered pipeline over the whole stand

Every real model in this repo already steps the **whole stand**, not a part: Eko couples
every cohort to every other; Elfving calibrates against whole-stand basal area. The
per-part iteration in `StageRuntime` is why its only consumer needs an `_armed` latch to
make N−1 invocations inert (review C4).

Invert it. The unit of work is the stand; a step that wants cohorts loops over them itself.

```python
class Step(Protocol):
    name: str
    def run(self, ctx: SimulationContext, dt: float) -> None: ...

DEFAULT_PIPELINE = (
    ManagementStep(policy),     # proposes + applies actions
    GrowthStep(model),
    MortalityStep(engine),
    IngrowthStep(model),
    ValuationStep(connector),
    RecordStep(),               # one snapshot row per step
)

result = project(stand, pipeline=DEFAULT_PIPELINE, years=100, step=5, seed=42)
```

That is exactly what `Elfving2010CompositePreset.step()` hand-codes today — five phases in
a fixed order plus a snapshot. Making it the runtime turns the god class (C1) into six
small steps and gives every other composite the same shape for free.

**Deleted:** `StageRuntime`, `Stage`, `ActionStage`, `StageAction`, `ManagementStage`,
`Ruleset`, `StandComposite`, `StandPart`, `StandAction`, `DispatchRecord`, `DispatchResult`,
`StageContract`, `SimulationSetup`, `TriggerSpec`, `ScheduledOp`, and
`SimulationContext.update_step(management=...)`. That is ~1,000 lines of the 1,501 with no
production consumer (review B2).

**Management** becomes a plain callable, which is all `example_api.md` ever asked for:

```python
Policy = Callable[[SimulationContext], Sequence[Action]]
```

Triggers (`SimulationSetup`) and rulesets (`ManagementStage`) are both just policies with
an `if`.

**Closes:** A7, C4, C5, C6, B2, B4, and the silent trigger-exception swallowing in `dsl.py`.

**Decision needed:** this deletes public API. Given 0 production consumers and a `0.0.1`
version with a "*very early* development, use at your own risk" README, I'd delete outright
rather than deprecate.

---

## Move 4 — Split `blocks/` into `systems/` (science) and `adapters/` (glue)

`blocks/` means two unrelated things, and the two regions use it differently:

| | lines | contents |
|---|---|---|
| `sweden/blocks/` | 10,353 | five whole published G&Y systems + two adapters |
| `norway/blocks/` | 742 | four adapters, ~185 lines each |

`AL001_SELF_CONTAINED_MODEL_SYSTEMS` is the exception list that admits this, and AL001 is
scoped to Sweden only because Norway "uses a different pattern". They aren't different
patterns; they're different *things* sharing a directory.

```
sweden/
  growth/  volume/  mortality/  height/  …     # individual published equations
  systems/                                     # whole published G&Y systems
    eriksson_1976/   persson_1992/   petterson_1955/
    eko1985/         elfving_hagglund_1975/
  adapters/                                    # GrowthModel glue. NO coefficients. Ever.
    eriksson_1976.py  eko1985.py  elfving_2010.py  soderberg_1986.py  …
```

Now the rule has no exceptions: **`adapters/` contains no scientific coefficient literals**,
full stop. AL001 loses its registry, its `install_formula_facade` dead branch (review B7),
and its Sweden-only scoping — it becomes ~10 lines applying to both regions.

It also fixes the name collision systematically instead of case by case: `growth/X/` or
`systems/X/` is always the science, `adapters/X.py` is always the runtime binding, and you
can tell which you imported from the path.

**Closes:** B7, most of B11, and removes a governance exception register.

---

## Move 5 — One provenance vocabulary, one import path

`SourceReference` is imported 48× from `base.contracts` and 48× from `simulation.contracts`;
~40 of the latter are pure equation modules reaching into the simulation tier for a
dataclass — which `ARCHITECTURE.md` and `base/contracts.py:8` both forbid in prose.

Promote the vocabulary out of `base` entirely, since it isn't base-specific:

```
pyforestry/contracts.py      # SourceReference, Describable, FormulaDescriptor,
                             # FormulaModuleDescriptor, ImputedValue
```

Drop the re-export from `simulation/contracts.py` (keep only genuinely
simulation-scoped types there), codemod the 48 imports, and add `.simulation.` to the
forbidden-import list for equation modules so the lint stops reporting `AL002: PASS` on a
violation it was written to catch.

**Closes:** B1. Removes one of the two `contracts` basenames (B11).

---

## Move 6 — One RNG, injected

`KeyedRNG`/`RandomBundle` exist and have zero consumers. Meanwhile `wikberg_2004`,
`fridman_stahl_2001`, the mortality engine, the adapters and the runbook each construct
their own generator, and the flagship composite carries **two** (numpy + stdlib) seeded
from one scalar — so draw interleaving across the two streams is an unwritten part of every
result.

Put one on the context and pass it down:

```python
ctx.rng.child("mortality").child(species)     # deterministic, path-keyed, independent
```

Rules: no model constructs a generator; every stochastic kernel takes `rng` as a parameter;
the seed lives on the run, not on a config dataclass.

**Decision needed:** `KeyedRNG` (exists, path-derived, composable) vs standardising on
`np.random.Generator` + `SeedSequence.spawn` (stdlib-adjacent, familiar, well-tested).
Either is defensible; the current situation — a keyed service nobody uses plus five ad-hoc
generators — is not. I'd keep `KeyedRNG` since it's written and tested, and back it with
`SeedSequence` internally.

**Closes:** B3. Makes A6 (dropped checkpoint RNG state) a real fix rather than a
resurrection of dead code.

---

## Move 7 — Tree identity

Populate `Tree.uid` at construction (monotonic counter, or caller-supplied). Key all
bookkeeping on it. Today the field exists, is never populated, and the flagship therefore
uses `id(tree)` — which cannot survive serialisation, checkpointing, or cross-step tracking,
which is what the field is for.

Precondition for meaningful checkpointing and for mortality/ingrowth bookkeeping that
outlives one call frame.

**Closes:** C3.

---

## Move 8 — A compact front door

Running one projection currently requires knowing `Eriksson1976Model`, `StandInit`,
`ThinningProgram`, `build_context`, `mode_hint`, `SimulationSetup`,
`Eriksson1976ManagementSchedule` — seven concepts, one of which raises `TypeError` when used
as documented.

```python
import pyforestry as pf

stand  = pf.Stand(plots=[...], site=site)
result = pf.project(stand, model="elfving_2010", years=100, step=5, seed=42)

result.table          # DataFrame, one row per step
result.stand          # final state
result.provenance     # every component's SourceReference
```

`model=` resolves through the existing `catalog`, which is the natural payoff for having
built it. The typed constructors stay available for advanced use — this is the 90% path,
not a replacement.

---

## Move 9 — Naming: "preset" means two things

`sweden/simulation/presets/` holds a frozen config dataclass implementing an inert protocol
*and* two 1,600-line stateful simulators implementing nothing. Rename:

- `SwedenScenarioPreset` → `ScenarioConfig` (it is configuration: seed, stage names, rulesets, artifacts)
- `Elfving2010CompositePreset` → `Elfving2010Pipeline`, and express it as a Move 3 pipeline

Then `get_preset()` either covers both or goes away. After Move 3, the `ScenarioConfig`
protocol either grows a runtime or is deleted along with the mock runbook (review A2).

---

## Move 10 — Make the docstring gate measure content

`docstring_threshold.txt = 90` is satisfied by 161 generated docstrings on the package's
most important classes. Replace or supplement the coverage gate with a grep-level check
that fails on the generator's fingerprints — `"Parameter for \`"`, `"Result produced by this
callable"`, `"^<Name>\.$"` summaries. Coverage measures presence; this measures that
somebody wrote something.

---

## Two forks worth deciding before starting

**Fork A — is `Stand` mutable state, or does simulation get its own `StandState`?**

Recommendation: **`Stand` is the state.** It already carries plots, trees, site, area,
attrs, the estimator, top-height and imputation; a parallel `StandState` recreates all of
it and re-opens the divergence that caused A1. The objection — "an inventory record should
be immutable" — is answerable with an explicit `stand.evolve(...) -> Stand` returning a new
instance, which also makes checkpointing trivial. Take the objection seriously enough to
make evolution explicit; don't take it seriously enough to build a sixth representation.

**Fork B — how much of `pyforestry.simulation` survives Move 3?**

Recommendation: **keep `services` (rng, telemetry, checkpoint) and `valuation`, delete the
rest.** `valuation` (`StandRemovalLedger`, `VolumeConnector`, `PieceRecord`) is a real
domain concept with a real design; it has no consumer only because nothing yet harvests
through the runtime — a Move 3 `ValuationStep` gives it one. `model_view` and `dp` are
speculative and go.

---

## Order

| # | Move | Depends on | Payoff |
|---|---|---|---|
| 1 | Single provenance import path (Move 5) | — | one codemod, closes B1, unblocks a truthful lint |
| 2 | Split `blocks/` → `systems/` + `adapters/` (Move 4) | — | pure file moves, removes the governance exception register |
| 3 | Populate `Tree.uid` (Move 7) | — | small, precondition for 5 and 6 |
| 4 | **One state object (Move 1)** | 3 | the big one — closes A1/A4/A8/C2/C10/C11 |
| 5 | Typed model inputs (Move 2) | 4 | closes C2 properly; feeds the catalog |
| 6 | **One pipeline (Move 3)** | 4, 5 | closes A7/C4/C5/C6/B2/B4; deletes ~1,000 lines |
| 7 | Inject the RNG (Move 6) | 6 | closes B3; makes A6 fixable |
| 8 | Re-express the composites as pipelines (Moves 3, 9) | 6 | closes C1 — the god class becomes six steps |
| 9 | `pf.project(...)` front door (Move 8) | 6 | the ergonomic payoff |
| 10 | Docstring gate (Move 10) | — | do any time |

Steps 1–3 are safe, mechanical, and land independently of the design questions. The forks
only need answering before step 4.

### What not to do

- **Don't rename `base/`.** Churn without payoff; the layering under it is already clean
  (no `base`→region imports, no region→region imports).
- **Don't deprecate rather than delete** at `0.0.1` with a "use at your own risk" README.
  Aliases for API nobody imports are pure carrying cost.
- **Don't unify Sweden and Norway policy modules** before either has a real ruleset. Today
  they are 20-line stubs whose only shared key means different things in each; unifying
  stubs standardises an accident.
- **Don't touch `base/competition/` or `base/imputation/`.** They are the target shape.
