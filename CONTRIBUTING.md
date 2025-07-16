# Contributing to pyforestry

First off, thank you for considering contributing to pyforestry! We welcome contributions from the community. Please take a moment to read and follow our [Code of Conduct](CODE_OF_CONDUCT.md) before getting started.

---

## Prerequisites

* **Python ≥ 3.10**
* **Git** & a **GitHub** account
* (Optional) A virtual environment tool (e.g., `venv`, `conda`)

1. Clone the repository and switch to the `main` branch:

   ```bash
   git clone https://github.com/Silviculturalist/pyforestry.git
   cd pyforestry
   git checkout main
   ```
2. Install core and development dependencies:

   ```bash
   pip install --upgrade pip
   pip install -e .[dev]
   ```

   This installs both runtime requirements and dev tools including **pytest**, **pytest-cov**, **docstr-coverage**, **coverage**, **black**, **ruff**, **sphinx**, **furo**, and **myst-parser**.

---

## Editor Integration (VS Code)

To automatically format and lint on save, add or update `.vscode/settings.json` in your project root:

```jsonc
{
  // Format Python with Black on save
  "[python]": {
    "editor.defaultFormatter": "ms-python.python",
    "editor.formatOnSave": true,
    // Also run Ruff’s auto-fixes on save
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "always"
    }
  }
}
```

This setup invokes Black for code formatting and Ruff for import sorting, removing unused names, and other lint fixes.

---

## Pre‑commit Hooks

We use **pre-commit** to catch issues before commits. Install and set up hooks once:

```bash
pip install pre-commit
pre-commit install
```

Our `.pre-commit-config.yaml` runs the following:

* Trailing-whitespace, end-of-file-fixer, YAML syntax checks, and large-file checks
* `ruff --fix` for lint auto-fixing
* Black for consistent formatting

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

We enforce a **50% minimum** coverage threshold on both the project and on new code via GitHub Actions CI and the `codecov.yml` settings.

---

## Documentation

We use **Sphinx** (with **nbsphinx**, **myst-parser**, and the **furo** theme) to build documentation. Install docs dependencies (also listed in `requirements.txt`):

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

1. **Fork** the repo on GitHub and create a new branch from `main` (e.g., `feature/xyz`).
2. **Implement** your changes, and **add or update tests**.
3. **Run**:

   * `pre-commit run --all-files`
   * `pytest`
   * `coverage html`
   * `make html -C docs`
4. **Commit** your changes with clear, concise messages.
5. **Push** your branch and open a **Pull Request** against `main`.
6. **Respond** to any review feedback. Once all checks pass and reviewers approve, a maintainer will merge your PR.

---

## Code Style & Docstrings

* Follow **PEP 8** ([https://peps.python.org/pep-0008/](https://peps.python.org/pep-0008/)).
* We rely on **Black** for formatting and **Ruff** for linting (import sorting, bug finding, etc.)
* Use **Google-style docstrings** for all public functions, classes, and modules. Docstrings should include:

  * A brief description
  * Arguments and types
  * Return values and types
  * Examples where appropriate

Thank you for helping make pyforestry even better!
