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
- Use **Black** and **Ruff** for code formatting and linting. Configuration for both tools is stored in `pyproject.toml`.
- Formatting should follow the same settings used in CI (`black` with a line length of 99 and `ruff` with `select = ["E", "F", "W", "I", "B"]`).
- You may run `ruff . --fix` and `black .` to automatically apply fixes.

## Pre‑Commit (Before Completing a Task)
1. Ensure the code is formatted:
   ```bash
   ruff . --fix
   black .
   ```
2. Run tests with coverage. Match the CI configuration from `.github/workflows/ci.yml`:
   ```bash
   pytest --cov=pyforestry --cov-report=xml --cov-report=html --cov-fail-under=50
   ```
   The coverage threshold is enforced in `codecov.yml` (50%).

Only finish a task when all steps above succeed.
