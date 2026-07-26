# Contributing to pyforestry

First off, thank you for considering contributing to pyforestry! We welcome contributions from the community. Please take a moment to read and follow our [Code of Conduct](CODE_OF_CONDUCT.md) before getting started.

Our workflow uses a dedicated **`dev`** branch for ongoing work. All feature branches
should be based on `dev` and pull requests should target `dev`. The `main` branch is reserved for stable releases.

---

## Prerequisites

* **Python ≥ 3.10**
* **Git** & a **GitHub** account
* (Optional) A virtual environment tool (e.g., `venv`, `conda`)

1. Clone the repository and switch to the `dev` branch (our default development branch):

   ```bash
   git clone https://github.com/Silviculturalist/pyforestry.git
   cd pyforestry
   git checkout dev
   ```
2. Install core and development dependencies:

   ```bash
   pip install --upgrade pip
   pip install -e .[dev]
   ```

   This installs both runtime requirements and dev tools including **pytest**, **pytest-cov**, **docstr-coverage**, **coverage**, **ruff**, **sphinx**, **pydata-sphinx-theme**, and **myst-parser**.

---

## Editor Integration (VS Code)

To automatically format and lint on save, add or update `.vscode/settings.json` in your project root:

```jsonc
{
  // Format Python with Ruff on save
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    // Also run Ruff’s auto-fixes on save
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "always"
    }
  }
}
```

This setup invokes Ruff for both code formatting and lint fixes.

---

## Pre‑commit Hooks

We use **pre-commit** to catch issues before commits. Install and set up hooks once:

```bash
pip install pre-commit
pre-commit install
```

Our `.pre-commit-config.yaml` runs the following:

* Trailing-whitespace, end-of-file-fixer, YAML syntax checks, and large-file checks
* `ruff --fix` and `ruff format` for consistent formatting and lint fixes

To manually run all hooks against every file:

```bash
pre-commit run --all-files
```

---

## Testing & Coverage

All tests live under the `tests/` directory. To run them locally:

```bash
pytest
```

To measure coverage:

```bash
coverage run -m pytest
coverage report    # summary in terminal
coverage html      # detailed report in htmlcov/
```

Our CI records the current coverage levels in the files
`coverage_threshold.txt` and `docstring_threshold.txt`.
Each pull request must keep coverage at least at these values – ideally it
should improve them.  The thresholds will gradually rise as the project
matures, with a long-term goal of **90%** test and documentation coverage.
Releases merged into `main` must not decrease coverage.

### Validate Changed File Coverage

After running tests, verify that modified modules retain high coverage:

```bash
python scripts/check_changed_file_coverage.py $(git merge-base HEAD origin/dev)
```

If any listed file is below **90%** test or docstring coverage, add more tests or
documentation before submitting your pull request.

---

## Documentation

We use **Sphinx** (with **nbsphinx**, **myst-parser**, and the **pydata-sphinx-theme** theme) to build documentation. Install docs dependencies (also listed in `requirements.txt`):

```bash
pip install -r requirements.txt
```

Build the docs:

```bash
make html -C docs
```

Preview the output in `docs/build/html` before submitting a PR.

---

## Submitting Changes

1. **Fork** the repo on GitHub and create a new branch from `dev` (e.g., `feature/xyz`).
2. **Implement** your changes, and **add or update tests**.
3. **Run** the formatters, tests, and documentation build locally:

   ```bash
   ruff check . --fix
   ruff format .
   pytest --cov=pyforestry --cov-report=xml --cov-report=html
   docstr-coverage src/pyforestry
   python scripts/check_changed_file_coverage.py $(git merge-base HEAD origin/dev)
   make html -C docs
   ```
   The coverage script ensures any changed modules maintain at least
   90% test and docstring coverage before opening a pull request.
4. **Commit** your changes with clear, concise messages.
5. **Push** your branch and open a **Pull Request** against `dev`.
6. Ensure your PR does not decrease the values in `coverage_threshold.txt` or
   `docstring_threshold.txt`. Increasing them is encouraged and will raise the
   baseline for future contributions.
7. **Respond** to any review feedback. Once all checks pass and reviewers approve, a maintainer will merge your PR into `dev`.
8. For modeling modules, confirm in the PR description that your implementation follows the
   `Directory Structure` and `Modeling Conventions` sections below, or explain any justified exceptions.

> **Note**
> When `dev` is merged into `main` for a release, coverage on `main` must remain above **80%** for both tests and documentation.

---

## Code Style & Docstrings

* Follow **PEP 8** ([https://peps.python.org/pep-0008/](https://peps.python.org/pep-0008/)).
* We rely on **Ruff** for formatting and linting (import sorting, bug finding, etc.)
* Use **Google-style docstrings** for all public functions, classes, and modules. Docstrings should include:

  * A brief description
  * Arguments and types
  * Return values and types
  * Examples where appropriate
* Document all public dataclass fields and expand abbreviations on first use.
* Prefer full words in public APIs (avoid acronym-only names).

## Modeling Conventions (Equations)

* Prefer module-level functions with explicit arguments (equation-first). When multiple fixed variants exist, keep each as its own function and optionally add a thin dispatcher.
* Use classes when state or caching is necessary (e.g., taper models with precomputation).
  Thin class facades are also acceptable for discoverability or backward compatibility when
  formula logic remains explicit and testable.
* If a `Timber`/`SweTimber` wrapper is provided, keep it minimal and delegate to the explicit-args formula function.
* Encode units in parameter names and docstrings (e.g., `diameter_cm`, `height_m`, `site_index_dm`).
* Inline coefficients directly in equations; avoid coefficient arrays/tuples or index-based lookups.
* Use `TreeSpecies` enums or canonical species strings; group species sets at module level.
* Guard logs/divisions, clamp outputs where the source implies bounds, and use `warnings.warn` for out-of-range inputs instead of `print`.
* Docstrings for equations should include Source, Applicability/valid ranges, Units, and Examples when helpful.
* Prefer scalar `math` for scalar formulas; use `numpy` only when you explicitly want vectorized behavior.
* Tests should be table-driven where possible and compare floats with `pytest.approx`.
* Prefer primitives from `pyforestry.base.helpers.primitives` (e.g., `SiteIndexValue`,
  `QuadraticMeanDiameter`, `Diameter_cm`, `StandBasalArea`) when available. If accepting floats,
  document units and reference definitions (e.g., H100 for site index).
* If a model is species-specific, make the input explicit (`site_index_pine_m`, `site_index_spruce_m`)
  or validate metadata on `SiteIndexValue`.
* Avoid exposing both raw and derived variables in public APIs; compute derived terms internally.

### Directory Structure (Equations / Blocks / Presets)

The codebase is organized in four composition levels:

| Level | Location | Description |
|---|---|---|
| **Equations** | `<region>/growth/`, `mortality/`, `siteindex/`, `volume/`, `bark/`, `biomass/`, `height/`, `ingrowth/`, `regeneration/` | Individually usable published functions. Each module is a coherent group from one publication. |
| **Systems** | `<region>/systems/` | Whole published growth-and-yield systems reproduced end to end (e.g., Ekö 1985, Eriksson 1976). These carry their own coefficients, because their parts were fitted together. |
| **Adapters** | `<region>/adapters/` | `GrowthModel` bindings and cross-domain reconstruction workflows (e.g., NYSKOG). Glue: **no scientific coefficient literals**. |
| **Presets** | `<region>/simulation/presets/` | Runnable scenario compositions wiring models and equations into end-to-end simulation pipelines. |

When adding new code:

* **New equations** go in domain packages (`growth/`, `mortality/`, `siteindex/`, etc.).
* **A whole published G&Y system** whose equations only agree with the printed yield tables
  when used together goes in `<region>/systems/`.
* **New adapters** (GrowthModel bindings, multi-equation workflows) go in `<region>/adapters/`.
* **New presets** go in `<region>/simulation/presets/`.
* Do not place coefficients in `adapters/`. AL001 fails the build on any float with three or
  more significant decimals that is not a unit factor, in either region, with no exception
  list -- because there are always two right answers instead: a domain package, or `systems/`.

Recommended equation references:

* `src/pyforestry/sweden/mortality/root_rot_thor_stahl_stenlid_2005.py`
* `src/pyforestry/sweden/siteindex/hagglund_1970.py`
* `src/pyforestry/sweden/growth/elfving_2010/kernels.py`

Recommended model references:

* `src/pyforestry/sweden/adapters/elfving_2010.py` (GrowthModel binding composing domain equations)
* `src/pyforestry/sweden/systems/eko1985/` (self-contained stand-level model system)

### Prefer

* Equation logic that is easy to follow from inputs to output.
* Species/region routing separated from formula computation where practical.
* Public APIs with explicit units and clear typed/domain inputs when available.
* Validation and extrapolation handling at API boundaries using `warnings.warn` and
  `ValueError`.
* Thin class facades for discoverability/compatibility only, with equation logic kept
  explicit and testable.

### Avoid

* Large nested coefficient registries plus string-key routing as the primary architecture
  for new modules.
* Branch-heavy mega-functions that combine dispatch, validation, and all species/region
  equations in one place.
* Public parameters that are accepted but not used in published equations, unless clearly
  documented as compatibility-only.
* Placing coefficients in `adapters/` -- individual equations should live in domain packages
  and be composed by the adapter; a whole published system goes in `systems/`.

## Naming Conventions

Follow these guidelines when naming modules and objects:

* **Packages and modules:** use `snake_case` and keep names short but descriptive. Domain packages like `base` or `sweden` should be entirely lowercase.
* **Classes:** use `CapWords` (PascalCase).
* **Functions, methods and variables:** use `snake_case`.
* **Constants:** use `UPPER_CASE`.
* Prefer descriptive names for public attributes (e.g., `mean_diameter_cm` over `mean_dbh_cm`,
  `number_ingrowth_trees` over `n_ingrowth`); keep abbreviations for internal locals only.
* For boolean or indicator fields, prefer suffixes like `_indicator` or `_flag`.
* Prefix implementation details with a single underscore to mark them as private.
* Consider defining ``__all__`` in modules to clearly state the public API.

Thank you for helping make pyforestry even better!
