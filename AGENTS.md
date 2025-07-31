# AGENT Instructions

## Environment Setup (On Task Start)
1. Upgrade `pip` and install dev and documentation dependencies:
   ```bash
   pip install --upgrade pip
   pip install -e '.[dev]'
   pip install -r docs/requirements.txt
   ```
   These commands ensure that all testing, linting and documentation tools listed in `pyproject.toml` and `docs/requirements.txt` are available.

## Ongoing Work
- Use **Ruff** for code formatting and linting. Configuration lives in `pyproject.toml`.
- Formatting should follow the same settings used in CI (line length 99 and `select = ["E", "F", "W", "I", "B"]`).
- You may run `ruff check . --fix` and `ruff format .` to automatically apply fixes.

## Pre‑Commit (Before Completing a Task)
1. Ensure the code is formatted:
   ```bash
   ruff check . --fix
   ruff format .
   ```
2. Run tests with coverage. Match the CI configuration from `.github/workflows/ci.yml`:
   ```bash
   pytest --cov=pyforestry --cov-report=xml --cov-report=html --cov-fail-under=50
   ```
   The coverage threshold is enforced in `codecov.yml` (50%).

3. For pull requests targeting `dev`, ensure all changed or new Python files have
   **at least 90%** test coverage and **90%** docstring coverage:
   ```bash
   python scripts/check_changed_file_coverage.py $(git merge-base HEAD origin/dev)
   ```
   The CI workflow runs the same script and will fail if any modified file falls
   below these levels.

4. Do not create superfluous test files. Aim to keep test code neatly organised 
   by subject. Always check to see if there already is a file with relevant tests.  

Only finish a task when all steps above succeed.
