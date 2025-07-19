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
   make html -C docs
   ```
4. **Commit** your changes with clear, concise messages.
5. **Push** your branch and open a **Pull Request** against `dev`.
6. Ensure your PR does not decrease the values in `coverage_threshold.txt` or
   `docstring_threshold.txt`. Increasing them is encouraged and will raise the
   baseline for future contributions.
7. **Respond** to any review feedback. Once all checks pass and reviewers approve, a maintainer will merge your PR into `dev`.

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

Thank you for helping make pyforestry even better!
