# Adversarial structural review — `elfving_2010_2_claude`

Scope: package structure, ease of use, class structure, abstraction. Not science, not
citations (covered by the earlier reference review). 432 files / +93.8k lines vs `main`.

Every finding below was verified by executing it against the installed package, not by
reading alone. Probe scripts are quoted inline.

> **Status: closed, except where noted.** Every finding below is fixed; see
> `ARCHITECTURE_PROPOSAL.md` for the commit each landed in. Two are deliberate
> non-fixes, argued rather than deferred:
>
> * **B6** — the Sweden/Norway `management_rulesets` share a key whose value means
>   different things. Both are 20-line stubs; unifying them would standardise an
>   accident. Fix when either grows a real ruleset.
> * **C1 (part)** — the god class lost its filesystem work and its misleading name,
>   but `step()` still hand-codes its phase order. That order is scientifically
>   load-bearing (mortality before growth, so the stand calibration targets survived
>   basal area), so it needs its own change against the parity tests.
>
> The review's own suggested order was followed. Working through it surfaced four
> further defects it had not found — a diameter-class inventory keyed only by
> `"TOTAL"` reporting the stand as empty, two unseeded RNG fallbacks, and a module
> that could not be imported first — each made visible by the structure that
> replaced the thing being reviewed.

---

## A. Abstraction defects that produce wrong numbers

### A1. `SimulationContext` re-implements stand aggregation and disagrees with `Stand` by 2×

`base/simulation/core.py:407` `_recompute_metrics_tree_list` averages each species over
*the plots where that species occurs*, not over all plots. `Stand._compute_plot_mean_estimates`
was fixed for exactly this (absent-species over-count). The two are now divergent
implementations of the same quantity:

```
2 plots, 1 ha each. Plot A: one spruce. Plot B: one pine.

Stand.Stems        TOTAL = 1.0    picea = 0.5
SimulationContext  TOTAL = 2.0    picea = 1.0
```

Every model driven through a `SimulationContext` in `tree_list`/`spatial` mode reads the
inflated numbers. The magnitude scales with species mixture: a 4-species stand with
disjoint plots reads 4×.

**Fix:** delete the duplicate and delegate to the `Stand` aggregation, or extract one
shared estimator both call. There should be exactly one implementation of "stems per
hectare from a plot list" in this package.

### A2. `run_sweden_preset` — the mandated regional entrypoint — simulates nothing

`sweden/simulation/orchestration/runbook.py:65` `_summary_rows`:

```python
initial_volume = 120.0 + rng.random() * 80.0
growth_per_step = 1.8 + rng.random() * 1.7
```

No `Stand`, no `GrowthModel`, no `StageRuntime`, no equation. It writes
`run_manifest.json`, `scenario_summary.parquet` and a `quality_report.json` carrying a
`determinism_hash` — of noise. Observed output:

```
preset.stages()   : ('growth', 'disturbance', 'valuation')
guard_policy()    : {'clamp_net_volume_to_zero': True, 'reject_negative_inputs': True}
stand 1: initial_volume_m3 = 167.53   net_volume_m3 = 178.10
stand 2: initial_volume_m3 = 195.24   net_volume_m3 = 199.48
```

Those are plausible-looking m³/ha for a Swedish stand. Nothing in the artifact says they
are synthetic. `ARCHITECTURE.md § "Play-Ready Regional Simulation Presets"` points at this
path as the compliant one, and it is exported as `pyforestry.sweden.simulation.run_sweden_preset`.

**Fix:** either wire it to a real model, or rename and quarantine it
(`_artifact_contract_smoke`, private, not in `__all__`) so nobody mistakes the numbers for
a projection.

### A3. Every `GrowthModel` adapter breaks the base-class signature it inherits

All eight adapters override `build_context(self, stand, *, <own kwargs>, **kwargs)` and
then call `super().build_context(stand, mode_hint="…", **kwargs)`. The base declares
`mode_hint` as a public parameter, so passing it raises:

```
TypeError: GrowthModel.build_context() got multiple values for keyword argument 'mode_hint'
```

`example_api.md:979` — the repository's own worked example — does exactly this:

```python
ctx = model.build_context(stand, mode_hint="aggregate")   # TypeError
```

Sites: `norway/blocks/{allen_2020,bollandsas,kuehne_2022,maleki_2022}.py`,
`sweden/blocks/{eriksson_1976,persson_1992,petterson_1955}.py`,
`sweden/blocks/eko1985/model.py`.

**Fix:** a model that dictates its own inventory mode should not expose `mode_hint`.
Move the mode onto `Requirements` (which already carries `inventory`) and have the base
`build_context` read it, so `mode_hint` becomes an override the base owns rather than a
parameter each subclass silently poisons.

### A4. A `tree_list` adapter's growth is silently discarded through the documented runtime path

`Bollandsas2008GrowthModel` requests `mode_hint="tree_list"`, keeps its class-state in
`ctx.attrs`, and publishes results with `ctx.set_aggregate_metrics(...)`. But
`SimulationContext.update_step` calls `_refresh_metrics()` afterwards, which for
`tree_list` mode recomputes everything from `ctx.plots` — which the model never touched.

```
before                       BA=3.9761  N=100.00
adapter.update_step(ctx, 5)  BA=4.1621  N=102.57   <- correct
ctx.update_step(5)           BA=3.8170  N=100.00   <- growth gone, BA moved to a different basis
```

The second call is the path `SimulationSetup`, `ExampleStandGeneralModel` and the docs all
use. No error, no warning.

**Fix:** `set_aggregate_metrics` in a non-aggregate mode is a category error — raise. Then
either give the adapter a real `dclass`/`aggregate` mode, or have it write back to
`ctx.plots`.

### A5. `inventory_origin` is inverted for every non-angle-count stand

`base/simulation/growth_model.py:304-314`:

```python
if stand.use_angle_count and mode in ("tree_list", "spatial"):
    attrs["inventory_origin"] = ("angle_count_pseudo_tree_list" if mode == "tree_list"
                                 else "angle_count_spatial_pseudo_tree_list")
    if mode == "tree_list":
        attrs["inventory_origin"] = "angle_count_pseudo_tree_list"   # dead, already set
else:
    attrs["inventory_origin"] = "angle_count_spatial_pseudo_tree_list"   # wrong
    attrs["angle_count_adapter"] = use_adapter or "auto"
```

Observed on a plain measured-tree stand in aggregate mode:

```
stand.use_angle_count : False
inventory_origin      : angle_count_spatial_pseudo_tree_list
angle_count_adapter   : auto
```

Provenance is a stated core value of this package; this records the opposite of the truth
for the common case. The `setdefault` on the next line for `diameter_class` is therefore
also dead.

### A6. Checkpoint saves RNG state; restore silently drops it

`SimulationContext.checkpoint` reads `getattr(self, "random_bundle", None)` and stores
`rng_state`. `from_checkpoint` guards on `hasattr(ctx, "random_bundle")` — but the
constructor never sets that attribute, so it is always `False` and the saved state is
discarded. Both paths swallow the failure with `except Exception: pass`. A restored run
is not reproducible and reports no problem.

### A7. `StandAction` signature-sniffing injects the RNG into an unrelated parameter

`stand_composite.py:82` `_analyse_handler` sets `accepts_rng_positional = True` for *any*
second positional parameter, whatever its name:

```python
def handler(part, intensity=0.25): ...
action.execute(part, rng)
# handler received intensity = KeyedRNG(path=('x',), seed=1220220935657997470…)
# action.requests_rng reported as: True
```

The handler's thinning intensity is replaced by an RNG object. Worse, `requests_rng=True`
makes `StandPart.apply_action` raise "requires RNG access" for a stage that does not
declare the `rng` effect — for a handler that never asked for one.

**Fix:** match on the parameter *name* only (`rng`, `io`), never on position.

### A8. `StandPart` metrics silently resolve to `0.0`, and constraints are enforced on them

`_metric_from_model` tries four duck-typed lookups and falls back to `0.0`:

```
model_view with no metric attributes:
  part.basal_area           : 0.0
  composite.total_basal_area: 0.0
```

`StandComposite.dispatch` enforces `budget` and `harvest_cap` against exactly these
numbers. A view that does not implement the (undeclared) metric protocol passes every
constraint.

**Fix:** declare a `Protocol` for the model view and fail on a view that does not satisfy
it, or return `None` and make the caller decide.

---

## B. Package structure

### B1. `SourceReference` is imported from two places, 48 modules each

```
from pyforestry.base.contracts       import SourceReference   — 48 modules
from pyforestry.simulation.contracts import SourceReference   — 48 modules
```

The `simulation.contracts` importers include ~40 pure equation modules:
`sweden/siteindex` (8), `sweden/mortality` (8), `sweden/volume` (7), `sweden/growth` (4),
`sweden/biomass` (3), `sweden/height` (2), `sweden/bark` (2), `sweden/regeneration`,
`sweden/ingrowth`.

`ARCHITECTURE.md` states the rule and `base/contracts.py:8` repeats it — *"nothing above
`base` should have to reach into the simulation package for this vocabulary"* — and it is
violated by half the codebase. `check_architecture_lint.py` exists to police exactly this
direction but its `FORBIDDEN_SIMULATION_SUFFIXES` lists only `.presets/.policy/.orchestration`,
so `AL002: PASS` is reported on a clean run.

**Fix:** one-line codemod to `base.contracts`, drop the re-export from
`simulation.contracts` (or keep it but add `.simulation.contracts` to the forbidden list
for equation modules so the lint tells the truth).

### B2. `pyforestry.simulation` is 1,501 lines of public API with zero production consumers

Outside its own package and its own tests, the whole tier has **two** callers:

| subsystem | production consumers |
|---|---|
| `stage_runtime`, `stand_composite` | `sweden/blocks/eko1985/engine.py` |
| `presets` | the two regional `_common.py` stubs |
| `model_view` (`InventoryView`, `SpatialTreeView`, `StandMetricView`) | **none** |
| `valuation` (`VolumeConnector`, `StandRemovalLedger`, `TreeRemoval`, `PieceRecord`, …) | **none** |
| `services` (`KeyedRNG`, `RandomBundle`, `TelemetryPublisher`, `CheckpointSerializer`, `ParallelRunner`) | **none** |
| `dp` (`DeterministicAdapter`, `simulate_one_step_pure`, `encode/decode_model_views`) | **none** |

1,501 lines of source + 1,104 lines of tests, 42 names in `__all__`, exercised only by
tests written against them. The tests give coverage numbers without demonstrating the
abstractions fit anything.

**Fix:** pick one — either drive the flagship Elfving composite through this runtime
(which would prove or disprove the design), or move it to a branch until something needs
it. Shipping it as public API commits you to its interface.

### B3. The RNG service has no consumers; every model rolls its own

`KeyedRNG`/`RandomBundle` appear only inside `pyforestry/simulation`. Actual randomness:

```
base/simulation/adapters.py:168,344              random.Random(seed)
sweden/ingrowth/wikberg_2004.py:1351             random.Random()
sweden/mortality/fridman_stahl_2001.py:275,372   random.Random()
sweden/simulation/mortality/engine.py:232        np.random.default_rng(...)
sweden/simulation/orchestration/runbook.py:80    random.Random(seed)
sweden/simulation/presets/elfving_2010_composite.py:199-200, 286-287
                                                 np.random.default_rng(...)  AND  random.Random(...)
```

The flagship preset carries **two** independent generators seeded from one scalar, so
draw order across the numpy and stdlib streams is an implicit part of the result.
`ARCHITECTURE.md` Hard Rule 1 ("Global seed MUST be defined in simulation policy/global
context") and `example_api.md §12` ("all randomness from keyed streams derived from
`(master_seed, stand_id, stage, event)`") are both unmet.

### B4. `SimulationPreset` is a five-method protocol that drives nothing

`guard_policy()` and `rulesets()` are **never called** anywhere in `src/`. `stages()` and
`required_artifacts()` are only serialised into a manifest. `seed_strategy()` seeds A2's
random walk. The protocol has no runtime.

Compounding it: `SimulationPreset` is a `Protocol` used as a concrete base class
(`ScenarioPresetBase(SimulationPreset)`), so its method bodies are docstrings that return
`None`. A subclass that forgets `stages()` fails later at `list(None)`, not at definition.
Use `abc.ABC` + `@abstractmethod` if it is a base class; keep `Protocol` if it is a shape.

### B5. Two unrelated things are called "preset" in one package

`sweden/simulation/presets/` contains:

- `SwedenScenarioPreset` — frozen dataclass, implements `SimulationPreset`, drives the A2 mock.
- `Elfving2010CompositePreset` / `Soderberg1986CompositePreset` — stateful 1,625-line
  simulators with `initialize()/step()/run_projection()`, implementing none of that protocol.

They share a package, a name, and nothing else. `get_preset(scenario_id)` is typed
`-> SwedenScenarioPreset` and only knows `"baseline"`, so the one discovery entrypoint
returns the mock and cannot reach either real simulator.

**Fix:** rename. `ScenarioConfig` vs `CompositeModel` (or `Pipeline`) would make the two
concepts unmistakable, and `get_preset` should either cover both or be dropped.

### B6. Norway/Sweden policy duplication with silently divergent semantics

`{sweden,norway}/simulation/policy/management_rulesets.py` both return
`{"thinning_ratio": …}`:

| | Sweden | Norway |
|---|---|---|
| `baseline` value | `0.20` | `1.0` |
| meaning | proportion harvested | multiplier |
| unknown scenario | `ValueError` | silently `1.0` |

Same key, same declared contract, incompatible units and error policy. `_stable_seed`
also diverges gratuitously (16 hex chars + `& 0x7FFFFFFF` vs 8 hex chars, unmasked).
`norway/simulation/__init__.py` is a bare docstring with no exports, unlike Sweden's.

### B7. Leftover facade contradicting the architecture doc

`ARCHITECTURE.md`: *"No facade delegation stubs remain; `install_formula_facade` has been
removed."* But `norway/bollandsas.py` is exactly that:

```python
"""Compatibility import path for the Bollandsas (2008) Norway model."""
from pyforestry.norway.blocks.bollandsas import Bollandsas2008
```

It is the only module at the Norway top level, and `check_architecture_lint.py:91` still
branches on `install_formula_facade` — dead code that can never fire, keeping a removed
concept alive in the tooling.

### B8. `base/helpers` re-exports the simulation runtime

`base/helpers/__init__.py:49-67` lazily re-exports 17 names from `base.simulation`
(`GrowthModel`, `SimulationContext`, `BatchEngine`, every adapter). The docstring on
`__getattr__` says why: *"to avoid import cycles at module import time."*

So Context 1 (Data Contract) advertises Context 4 (Simulation Runtime) as its own API,
and `pyforestry.base.helpers.GrowthModel` and `pyforestry.base.simulation.GrowthModel` are
two supported spellings of one class. The import cycle is the real problem; the re-export
hides it and blurs the ownership matrix the whole document is built on.

Same file: `_TreeCache` — a private name — is in `__all__`, and a file-level
`# ruff: noqa: F401, F403, F405` disables unused/star-import checks for the module.

### B9. `pandas` is an undeclared runtime dependency

Imported at module scope in five `src/` modules (`base/simulation/core.py`,
`base/simulation/ensemble.py`, `base/pricelist/solutioncube.py`,
`sweden/simulation/orchestration/runbook.py`,
`sweden/simulation/presets/elfving_2010_composite.py`) and returned from public APIs
(`SimulationContext.to_pandas`, `run_projection`). `pyproject.toml` `dependencies` lists
numpy, tqdm, xarray, scipy, geopandas, shapely, pyproj — no pandas. It installs today only
because geopandas pulls it in transitively.

### B10. `example_api.md` documents a package that does not exist

Repo-root design doc describing a `forestsim/` layout, `*/models` (renamed to `/blocks` on
this branch), and `StandState` / `SimContext` / `Preset` / `simulate_stand` /
`optimize_policy` / `NotebookSession` / `SimulationService` — none of which exist. Its one
runnable-looking example (§18.3) raises `TypeError` (A3). It sits beside `ARCHITECTURE.md`
and `ROADMAP.md` with no status marker, unlike `ROADMAP.md` which at least tags
`[CP]/[TD]/[IE]/[FAP]`.

### B11. Module basename collisions

`simulation` exists at four levels (`base.simulation`, `simulation`, `sweden.simulation`,
`norway.simulation`); `presets` at three; `contracts`, `helpers`, `blocks`, `growth`,
`policy`, `data`, `engine`, `height`, `volume`, `taper`, `_common`, `baseline`,
`management_rulesets`, `scenario_rulesets` at two or more.

Some are deliberate (`blocks/elfving_2010.py` adapter vs `growth/elfving_2010/` equations —
though nothing in the *name* tells you which you imported). Others are avoidable:
`norway/blocks/bollandsas.py` drops the year that `allen_2020`, `kuehne_2022`,
`maleki_2022` all carry.

Consequence already visible: `tests/` needs `--import-mode=importlib` in `addopts` because
region test basenames collide.

---

## C. Class structure

### C1. `Elfving2010CompositePreset` is a god class

1,625 lines, ~50 methods, 30+ imported subsystems, one class. It owns regeneration, NYSKOG
reconstruction, young-stand growth, mature growth, mortality prediction, mortality
realisation, ingrowth, height/bark imputation, taper, bucking, valuation, DataFrame
reporting — **and filesystem I/O**
(`ensure_recommended_valuation_solution_cube_file`, `generate_recommended_valuation_solution_cube`,
`_load_solution_cube`), which is Context 5 work inside a Context 4 class.

It also carries 12 mutable `_last_*` fields used purely to smuggle values from the step
into `_snapshot_row`. Those are a return value that has been turned into state.

**Fix:** the phases are already separable — `_apply_nystrom_young_growth`,
`_predict_mortality`, `_realize_mortality`, `_apply_ingrowth`,
`_apply_soderberg_height_and_bark` are each a stage. That is precisely what `StageRuntime`
is for (B2). Splitting valuation out into a `Valuator` and the cube management into a
module-level function would remove ~400 lines and all the I/O.

### C2. `SimulationContext` is used as a throwaway attribute bag

`_rebuild_context` builds a fresh `CircularPlot` + `Stand` + `SimulationContext` **twice
per `step()`**, uses it to carry 12 stringly-typed keys into the model, and discards it:

```python
ctx.attrs.update({"site_index_m": …, "dominant_species": …, "temperature_sum_dd": …,
                  "latitude_deg": …, "altitude_m": …, "distance_to_coast_km": …,
                  "field_estimated_basal_area_m2_ha": …,
                  "thinned_0_10_years": False, "thinned_11_25_years": False,
                  "thinned_11_30_years": False})
```

`ctx.history` — the class's audit trail, and its stated reason to exist — is thrown away
every step. This is the "ad-hoc dict plumbing" `example_api.md §18` says the design
replaces; the typed `Eriksson1976StepInput` it proposes is the right shape.

### C3. `Tree.uid` exists and is unused; the flagship uses `id(tree)` instead

`Tree` declares `uid: int | str | None`. Nothing populates it. `elfving_2010_composite.py`
therefore keys its per-step bookkeeping on CPython object identity —
`_young_tree_ids() -> set[int]`, `young_dbh_after_nystrom = {id(tree): …}`. Safe only
because the list holds references for the duration; unusable for checkpointing,
serialisation or cross-step tracking, which is what the field was for.

### C4. `StageRuntime` is per-part; its only real model is whole-stand

`Eko1985GrowthStage` subclasses `Stage`, is handed one `part` at a time by
`run_cycle`, ignores it, reaches back through `module.composite` for the whole stand, and
uses an `_armed` latch so the work happens on the first of N invocations and the rest are
inert. It also back-references its owner (`self._stand = stand`) — `EngineStand` owns the
stage, the stage owns `EngineStand`.

That is a per-part iteration model wrapped around a simultaneous-update model. Thinning in
the same engine bypasses the runtime entirely (`composite.dispatch(..., policy="broadcast")`),
and there is no `ManagementStage` in its stage list — so the affordance/ruleset/dispatch
machinery is unused by its only consumer.

### C5. `_run_part` silently bypasses management for late-ordered stages

`stage.managed = True` only takes effect if the stage sorts *before* the `ManagementStage`
(order 20). A managed `ActionStage` with `order = 25` lands in `pending`, is skipped by the
management branch (already passed), and is executed unfiltered by
`_apply_without_management` at the end of the cycle. The ruleset is silently skipped.

### C6. `ValuationStage._locate_ledger` searches six places

`view.removal_ledger` → `view.removals` → `view.ledger` → `view.get_removal_ledger()` →
`part.context["valuation"]["ledger"]` → `part.context["removal_ledger"]`, then `None`.
Six conventions is zero conventions. Declare one (a `Protocol` method) and fail on views
that do not implement it.

### C7. Interface enforcement is absent and inconsistent

- `GrowthModel` is a plain class. `requirements()` and `update_step()` raise
  `NotImplementedError` at call time, not definition time. Not an `ABC`.
- `GrowthModel.source` defaults to `SourceReference(author="unknown", year=0, title="unknown")`.
  A model that forgets provenance gets a plausible-looking fake instead of an error — in a
  package whose selling point is traceability. `ExampleStandGeneralModel`, the reference
  implementation contributors copy, is exactly this case.
- `Stage.run` has an empty body (silently does nothing) while `ActionStage.build_actions`
  raises `NotImplementedError`. Two styles in one hierarchy.
- `SimulationPreset` is a `Protocol` used as a base class (B4).

### C8. `StandPart.context` is typed `Mapping` and mutated as `MutableMapping`

```
annotation: Mapping[str, Any]
ValuationStage.run: part.context.setdefault(...)  and  part.context["cash"] = ...
```

`Mapping` has neither. The type is documentation that contradicts the code; a type checker
run over this file would reject the runtime's own stage.

### C9. `Tree` normalises two of four constructor inputs

`position` is normalised through `Position._set_position`, `species` through
`parse_tree_species`. `diameter_cm` and `age` are stored raw, with shipped TODO comments
saying they should not be:

```python
# If `age` is e.g. float or Age, store as is (for more advanced usage,
# you might unify to an AgeMeasurement).
self.age = age
# If `diameter_cm` is a float, you could coerce to a default Diameter_cm( ... )
self.diameter_cm = diameter_cm
```

The cost is paid everywhere else: `float(getattr(t, "diameter_cm", 0.0) or 0.0)` appears
throughout the codebase because callers cannot rely on the type.

### C10. Private-state access in the reference example

`ExampleStandGeneralModel` — the template implementers are meant to copy — reads
`ctx._dclass` directly in three methods. Whatever the intended public API for
diameter-class inventory is, the canonical example teaches reaching past it.

### C11. `StandMetricView.supported_metrics` does not filter

```python
return tuple(name for name in self._SUPPORTED if hasattr(self._stand.__class__, name))
```

All four are unconditional class-level properties, so this always returns all four
regardless of what the stand can actually produce. Separately, `HL` (Lorey's height) is
computed by `Stand` and stored in `_metric_estimates` but is missing from `_SUPPORTED`, so
the view cannot expose it.

### C12. `catalog._discover` swallows every import error

Three `except Exception: return`/`continue` blocks. A model whose module raises on import
silently vanishes from `catalog.list_models()` / `find()` / `search()` with no diagnostic —
the failure mode is a model that "does not exist". Collect the exceptions and expose them
(`catalog.discovery_errors()`), or at minimum `warnings.warn`.

---

## D. Ease of use

### D1. 161 content-free docstrings, driven by the coverage gate

```
"Parameter for `X`."                                            109 occurrences
"Result produced by this callable."                              52
"Source: Internal pyforestry simulation architecture and …"      81
                                                       across    18 files
```

`docstring_threshold.txt` = 90. The gate measures presence, so it is satisfied by:

```python
def can_build(self, stand, *, allow_adapters=True, mode_hint=None):
    """Can build.

    Args:
        stand: Parameter for `GrowthModel.can_build`.
        allow_adapters: Parameter for `GrowthModel.can_build`.
        mode_hint: Parameter for `GrowthModel.can_build`.

    Returns:
        Result produced by this callable.
    """
```

`help(GrowthModel.can_build)` is worse than no docstring: it looks documented. These sit on
the *most important* classes in the package — `GrowthModel`, `SimulationContext`,
`StageRuntime`, `StandComposite`, `StandAction`.

This is a choice, not a constraint: `base/competition/api.py` and `base/imputation/` in the
same branch have excellent prose (see §E).

### D2. Mixed docstring conventions

220 Google-style `Args:` sections vs 26 numpydoc `Parameters\n----------` sections — the
split runs through neighbouring modules (`base/helpers/tree.py` numpydoc,
`base/helpers/stand.py` mixed, `base/simulation/*` Google). Pick one and put it in
`CONTRIBUTING.md`.

### D3. The README's headline example is untyped and undiscoverable

```python
print(stand.BasalArea.TOTAL.value)
```

`BasalArea` returns a `StandMetricAccessor` whose `.TOTAL` resolves through `__getattr__`.
No IDE completion, no type checking, no way to discover `.TOTAL` short of reading the
source. It is the first code a new user runs.

### D4. `dt` semantics are inconsistent across models

`GrowthModel.update_step(ctx, dt)` takes years. `Bollandsas2008GrowthModel` raises unless
`dt` is a whole multiple of 5. `Eko1985` steps 5 years. `Elfving2010CompositePreset` takes
`dt_years` (different parameter name) defaulting to 5. Nothing on `Requirements` declares a
model's native step, so the only way to learn it is to trigger the exception.

**Fix:** add `native_step_years: float | None` to `Requirements`.

### D5. Minor

- `norway/simulation/__init__.py` exports nothing while `sweden/simulation/__init__.py`
  exports 22 names — asymmetric discovery.
- `GrowthModel.can_build` checks `require_top_height` via `get_dominant_height()` only,
  ignoring the configurable `estimate_top_height` subsystem this branch added.
- `SimulationContext.metrics` is documented "read-only copy" but returns a shallow copy;
  the `Stems`/`StandBasalArea` values are shared and mutable.
- Untracked `tmp/Persson_1992.py` currently makes `ruff check .` fail with 7 errors. Add
  `tmp/` to `.gitignore`.
- `imputation/registry.py` stores the default under the magic key `"__default__"` in the
  same dict as real names, so `imputers_for` must filter it and
  `register_imputer(attr, "__default__", …)` would corrupt the registry. A separate
  `_DEFAULTS` dict removes the coupling.

---

## E. What is right

These are the benchmark; the criticisms above are "make the rest look like this".

- **`base/competition/`** — one entry point (`competition_indices`), clean split across
  `geometry`/`indices`/`neighbourhood`/`selection`/`sources`, and a module docstring that
  explains *why* (two neighbourhoods per tree, when edge correction is and is not valid,
  why ratio indices are not scaled). Every non-obvious decision is argued in place.
- **`base/imputation/`** — the `Imputer` protocol, `CallableImputer` provenance wrapper, and
  a registry with genuinely helpful errors (`_REJECTED` explains why `"measured"` cannot
  impute a missing height instead of saying "unknown name").
- **Import direction is clean**: no `base` → region imports, no region → region imports.
  The layering that matters most is intact.
- **Lazy top-level `__getattr__`** on `pyforestry`, `pyforestry.sweden` with `__dir__` for
  tab completion — good ergonomics, cheap import.
- **`catalog`** is a genuinely useful discovery layer: 83 models, 15 domains, findable
  without knowing the import path.
- **`FormulaDescriptor` / `SourceReference`** as a declarative, uniform provenance
  convention across 49 modules.

---

## Suggested order

| # | Item | Why first |
|---|---|---|
| 1 | A1 aggregation divergence | silently wrong numbers, 2× |
| 2 | A4 + A3 `build_context` contract | silently wrong numbers + documented example is broken |
| 3 | A2 rename/quarantine `run_sweden_preset` | synthetic m³ presented as output |
| 4 | A5, A6, A7, A8 | small, local, each a silent failure |
| 5 | B1 `SourceReference` codemod + widen AL002 | one-line change, removes a 48-module split |
| 6 | B9 declare `pandas` | one line |
| 7 | B10 mark `example_api.md` aspirational, fix §18.3 | it is the doc people read first |
| 8 | D1 replace the 161 generated docstrings | on the classes that matter most |
| 9 | B2 decide the fate of `pyforestry.simulation` | 1,501 lines of public API with no caller |
| 10 | C1 split `Elfving2010CompositePreset` | best done *after* 9 decides the target runtime |
