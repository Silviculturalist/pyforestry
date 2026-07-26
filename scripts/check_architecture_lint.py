"""Minimal architecture lint check (AL001-AL004).

Usage:
    python scripts/check_architecture_lint.py [--changed-only BASE_SHA]

Without --changed-only, checks all files. With --changed-only, checks only
files modified since BASE_SHA.

Exit code 0 = pass, 1 = violations found.
"""

from __future__ import annotations

import ast
import math
import subprocess
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src" / "pyforestry"

# ---------------------------------------------------------------------------
# AL001: No scientific coefficients in */adapters/
# ---------------------------------------------------------------------------

# An adapter binds published equations to the simulation runtime: it reads a
# Stand, calls kernels from a domain package, writes results back. It does not
# own numbers. A whole published growth-and-yield system does own its numbers,
# and lives in */systems/ (or a domain package, for a standalone equation).
#
# This rule used to be a Sweden-only budget of ten coefficients with a registry
# of seven exempted modules, because */blocks/ held both kinds of module in one
# directory and the check had no way to tell them apart. Splitting the directory
# removed the ambiguity, so the rule needs neither a registry nor a budget: any
# fitted coefficient found under */adapters/ is a coefficient in the wrong place,
# in either region.
AL001_ADAPTER_DIRECTORY = "adapters"

# Values that read like coefficients to a decimal-place test but are not fitted
# to anything: unit and scale factors. A regression coefficient is essentially
# never an exact power of ten, so excluding them costs no detection power.
_UNIT_FACTOR_MANTISSAS = frozenset({1.0, -1.0})


def _is_unit_factor(value: float) -> bool:
    """Return True for exact powers of ten (``1e-4``, ``0.001``, ``100.0``).

    These are the unit conversions an adapter legitimately carries -- cm² to m²,
    per-hectare scaling -- and no fitted coefficient lands on one.
    """
    if value == 0.0:
        return False
    exponent = math.log10(abs(value))
    if exponent != int(exponent):
        return False
    return abs(value) / 10 ** int(exponent) in _UNIT_FACTOR_MANTISSAS


def _scientific_coefficients(tree: ast.AST) -> list[tuple[int, float]]:
    """Return ``(lineno, value)`` for float literals that look fitted.

    Three or more significant decimals is the discriminator: regression
    coefficients look like ``0.0094`` or ``-0.42759``, whereas the constants an
    adapter legitimately carries (unit factors, ``0.5``, ``100.0``) do not.
    """
    found = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, float)):
            continue
        if _is_unit_factor(node.value):
            continue
        text = repr(node.value)
        if "." in text and len(text.split(".")[1].rstrip("0")) >= 3:
            found.append((node.lineno, node.value))
    return found


def check_al001(paths: list[Path]) -> list[str]:
    """Check that no adapter module carries scientific coefficient literals.

    Applies to every ``*/adapters/`` package in every region. There is no
    exception list: a module that needs to hold coefficients is a published
    system or a domain equation module, and belongs in ``*/systems/`` or a
    domain package respectively.
    """
    violations = []
    for path in paths:
        if path.suffix != ".py" or path.name == "__init__.py":
            continue
        if AL001_ADAPTER_DIRECTORY not in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):  # pragma: no cover - unreadable/invalid file
            continue
        coefficients = _scientific_coefficients(tree)
        if not coefficients:
            continue
        sites = ", ".join(f"line {lineno}: {value!r}" for lineno, value in coefficients[:5])
        if len(coefficients) > 5:
            sites += f", and {len(coefficients) - 5} more"
        relative = path.relative_to(SRC_ROOT).as_posix()
        violations.append(
            f"AL001: {relative} holds {len(coefficients)} scientific coefficient "
            f"literal(s) ({sites}). An adapter binds equations to the runtime; it does "
            "not own numbers. Move them into a domain package (e.g. */growth, */height, "
            "*/volume) or, if this is a whole published growth-and-yield system, into "
            "*/systems/."
        )
    return violations


# ---------------------------------------------------------------------------
# AL002: Equation modules must not import from simulation policy
# AL003: Adapter and system modules must not import from simulation policy
# ---------------------------------------------------------------------------

# Domain equation packages (must not depend on simulation policy).
EQUATION_PACKAGES = {
    "mortality",
    "siteindex",
    "volume",
    "bark",
    "biomass",
    "growth",
    "height",
    "ingrowth",
    "regeneration",
}

# Region-generic forbidden import patterns. Any region's simulation policy,
# presets, and orchestration packages are forbidden in equation and block modules,
# and so is the shared runtime's contracts module: the provenance vocabulary it used
# to re-export lives in ``pyforestry.base.contracts``, and an equation module that
# reaches up into the simulation tier for it inverts the dependency direction
# ARCHITECTURE.md defines (equations -> primitives; simulation -> equations).
FORBIDDEN_SIMULATION_SUFFIXES = (
    ".simulation.presets",
    ".simulation.policy",
    ".simulation.orchestration",
    ".simulation.contracts",
)


def _is_equation_module(path: Path) -> bool:
    """Return True if path is inside a domain equation package."""
    parts = path.parts
    for pkg in EQUATION_PACKAGES:
        if pkg in parts:
            return True
    return False


def _is_model_module(path: Path) -> bool:
    """Return True if path is inside an adapters/ or systems/ package."""
    return "adapters" in path.parts or "systems" in path.parts


def _is_forbidden_import(module_name: str) -> bool:
    """Return True if the import target is a simulation policy/preset/orchestration module."""
    for suffix in FORBIDDEN_SIMULATION_SUFFIXES:
        # Match e.g. "pyforestry.sweden.simulation.presets" or
        # "pyforestry.norway.simulation.policy.management_rulesets"
        if suffix in module_name:
            return True
    return False


def _extract_imports(path: Path) -> list[str]:
    """Extract all import module names from a Python file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return []
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def check_al002(paths: list[Path]) -> list[str]:
    """Check that equation modules do not import from simulation policy."""
    violations = []
    for path in paths:
        if not path.suffix == ".py":
            continue
        if not _is_equation_module(path):
            continue
        for module_name in _extract_imports(path):
            if _is_forbidden_import(module_name):
                violations.append(
                    f"AL002: {path.name} imports {module_name} "
                    f"(equation modules must not import from simulation policy)"
                )
    return violations


def check_al003(paths: list[Path]) -> list[str]:
    """Check that adapter and system modules do not import from simulation policy."""
    violations = []
    for path in paths:
        if not path.suffix == ".py":
            continue
        if not _is_model_module(path):
            continue
        for module_name in _extract_imports(path):
            if _is_forbidden_import(module_name):
                violations.append(
                    f"AL003: {path.name} imports {module_name} "
                    f"(adapter and system modules must not import from simulation policy)"
                )
    return violations


# ---------------------------------------------------------------------------
# AL004: No generated placeholder docstrings
# ---------------------------------------------------------------------------

# Fingerprints of a docstring generator that was run over this codebase. Each
# states only that a parameter is a parameter, that a callable returns, or that
# runtime plumbing belongs to the runtime -- while satisfying the docstring
# coverage gate, which measures presence rather than content. 161 of them
# accumulated on the package's most important classes, where `help()` was worse
# than nothing because the output looked documented.
GENERATED_DOCSTRING_MARKERS = (
    "Parameter for `",
    "Result produced by this callable",
    "Internal pyforestry simulation architecture and runtime contracts",
)


def check_al004(paths: list[Path]) -> list[str]:
    """Check that no generated placeholder docstrings have been reintroduced."""
    violations = []
    for path in paths:
        if path.suffix != ".py":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:  # pragma: no cover - unreadable file
            continue
        for marker in GENERATED_DOCSTRING_MARKERS:
            count = text.count(marker)
            if count:
                violations.append(
                    f"AL004: {path.name} contains {count} generated placeholder "
                    f"docstring(s) ({marker!r}). Docstring coverage measures presence; "
                    "write what the callable does, what its arguments mean, and what "
                    "it returns -- or leave it undocumented and let the gate say so."
                )
    return violations


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def get_changed_files(base_sha: str) -> list[Path]:
    """Return list of Python files changed since base_sha."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", base_sha, "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    repo_root = Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )
    return [
        repo_root / line.strip()
        for line in result.stdout.splitlines()
        if line.strip().endswith(".py")
    ]


def get_all_files() -> list[Path]:
    """Return all Python files under src/pyforestry/."""
    return list(SRC_ROOT.rglob("*.py"))


def main() -> int:
    """Run architecture lint checks."""
    if "--changed-only" in sys.argv:
        idx = sys.argv.index("--changed-only")
        base_sha = sys.argv[idx + 1]
        paths = get_changed_files(base_sha)
        scope_label = f"changed files since {base_sha[:8]}"
    else:
        paths = get_all_files()
        scope_label = "all files"

    print(f"Architecture lint ({scope_label}): {len(paths)} files")
    print()

    violations = []
    violations.extend(check_al001(paths))
    violations.extend(check_al002(paths))
    violations.extend(check_al003(paths))
    violations.extend(check_al004(paths))

    if violations:
        print("VIOLATIONS FOUND:")
        for v in violations:
            print(f"  {v}")
        print(f"\n{len(violations)} violation(s). FAIL.")
        return 1
    else:
        for rule in ("AL001", "AL002", "AL003", "AL004"):
            print(f"{rule}: PASS")
        print("\nNo violations. PASS.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
