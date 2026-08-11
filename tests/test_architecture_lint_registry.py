"""The rule registry and the gate that enforces it must describe the same rules.

``governance/architecture/rules/architecture_lint_rules.yaml`` is read as the
record of what the architecture gate enforces. Nothing kept it in step with
``scripts/check_architecture_lint.py``, and the two had drifted in both
directions: AL003 and AL004 were enforced while appearing in no rules file, and
AL002 was registered ``advisory`` while the script failed the build on it like
every other rule. These tests are the thing that was missing.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_architecture_lint.py"


def _load_lint_module():
    """Import the lint script as a module, since ``scripts/`` is not a package."""
    spec = importlib.util.spec_from_file_location("_architecture_lint", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def lint():
    return _load_lint_module()


def test_registry_and_script_agree(lint) -> None:
    """No rule is enforced without being registered, or registered without effect."""
    assert lint.check_registry() == []


def test_every_registered_rule_declares_a_mode(lint) -> None:
    """A rule with no mode is a rule whose blocking behaviour is unstated."""
    registered = lint._registered_rules()
    assert registered, "the rules file parsed to nothing; the parser or the file moved"
    assert all(mode in {"blocking", "advisory"} for mode in registered.values())


def test_registry_drift_is_reported(lint, monkeypatch) -> None:
    """An unregistered rule fails the gate rather than passing silently."""
    monkeypatch.setattr(
        lint,
        "RULES",
        lint.RULES + (("AL999", "blocking", lambda paths: []),),
    )
    problems = lint.check_registry()
    assert any("AL999" in problem for problem in problems)


def test_mode_drift_is_reported(lint, monkeypatch) -> None:
    """A rule registered advisory but enforced blocking fails the gate."""
    monkeypatch.setattr(
        lint,
        "RULES",
        tuple(
            (rule_id, "advisory" if rule_id == "AL001" else mode, check)
            for rule_id, mode, check in lint.RULES
        ),
    )
    problems = lint.check_registry()
    assert any("AL001" in problem and "advisory" in problem for problem in problems)


def test_al005_skips_files_outside_src(lint, tmp_path) -> None:
    """A changed test or script is skipped, not a crash.

    ``--changed-only`` hands every changed ``.py`` in the repo to each check.
    AL005 called ``relative_to(SRC_ROOT)`` unguarded, so one changed test file
    raised ``ValueError`` and took the whole gate down.
    """
    outside = tmp_path / "test_something.py"
    outside.write_text("import random\nrng = random.Random(1)\n", encoding="utf-8")
    assert lint.check_al005([outside]) == []


def test_al001_covers_adapter_package_inits(lint, tmp_path) -> None:
    """``__init__.py`` under ``adapters/`` is checked like any other module."""
    adapters = tmp_path / "adapters"
    adapters.mkdir()
    init = adapters / "__init__.py"
    init.write_text("COEFFICIENT = 0.42759\n", encoding="utf-8")
    violations = lint.check_al001([init])
    assert len(violations) == 1
    assert "AL001" in violations[0]
