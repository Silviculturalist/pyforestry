"""Minimal architecture lint check (AL001 + AL002).

Usage:
    python scripts/check_architecture_lint.py [--changed-only BASE_SHA]

Without --changed-only, checks all files. With --changed-only, checks only
files modified since BASE_SHA.

Exit code 0 = pass, 1 = violations found.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src" / "pyforestry"

# ---------------------------------------------------------------------------
# AL001: No formula-heavy internals in */models/
# ---------------------------------------------------------------------------

# Facade modules must contain only install_formula_facade and nothing else.
# Currently scoped to Sweden where facade pattern is enforced.
# Norway blocks use a different adapter pattern (explicit GrowthModel subclasses).
AL001_SCOPE = SRC_ROOT / "sweden" / "blocks"

# A block module may legitimately hold equations only when it is one of the
# self-contained published model systems ARCHITECTURE.md (Context 3) names. Every
# other block module must delegate its equations to a domain package; a new entry
# here is an architecture decision, not a lint tweak, and anything that does not
# belong on this list belongs in the exception register with an owner and exit
# criteria (governance/architecture/exceptions/architecture_exceptions.yaml).
AL001_SELF_CONTAINED_MODEL_SYSTEMS = frozenset(
    {
        "eko1985/cohorts.py",
        "eko1985/engine.py",
        "elfving_hagglund_1975.py",
        "eriksson_1976.py",
        "nystrom_soderberg_1987.py",
        "persson_1992.py",
        "petterson_1955.py",
    }
)

# Below this many scientific coefficient literals a module is treated as an
# adapter that merely passes a few constants through, not an equation kernel.
AL001_COEFFICIENT_BUDGET = 10


def _scientific_coefficient_count(tree: ast.AST) -> int:
    """Count float literals precise enough to be fitted model coefficients.

    Three or more significant decimals is the discriminator: regression
    coefficients look like ``0.0094`` or ``-0.42759``, whereas the constants an
    adapter legitimately carries (unit factors, ``0.5``, ``100.0``) do not.
    """
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, float):
            text = repr(node.value)
            if "." in text and len(text.split(".")[1].rstrip("0")) >= 3:
                count += 1
    return count


def check_al001(paths: list[Path]) -> list[str]:
    """Check that model/block modules are either thin facades or legitimate blocks.

    A module under */models/ (future */blocks/) must be one of:
    - A thin facade using install_formula_facade (no class/function definitions).
    - A legitimate block: a self-contained model system, GrowthModel adapter, or
      cross-domain reconstruction workflow. These may contain classes and functions.

    The rule prevents accidental introduction of new formula-heavy code in modules
    that are supposed to be facades while allowing real block content.
    """
    violations = []
    for path in paths:
        if path.name.startswith("_") or path.name == "__init__.py":
            continue
        # AL001 currently scoped to Sweden models only
        try:
            path.relative_to(AL001_SCOPE)
        except ValueError:
            continue
        text = path.read_text(encoding="utf-8")
        # Modules using install_formula_facade must stay thin
        if "install_formula_facade" in text:
            if "class " in text:
                violations.append(f"AL001: {path.name} is a facade but contains class definitions")
            if "\ndef " in text:
                violations.append(
                    f"AL001: {path.name} is a facade but contains function definitions"
                )
            continue

        # Every other block module is a legitimate block only so long as it does
        # not carry the equations itself. Blocks compose domain equations; the
        # coefficients belong in a domain package (ARCHITECTURE.md Context 2).
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError:
            continue
        coefficients = _scientific_coefficient_count(tree)
        if coefficients <= AL001_COEFFICIENT_BUDGET:
            continue
        relative = path.relative_to(AL001_SCOPE).as_posix()
        if relative in AL001_SELF_CONTAINED_MODEL_SYSTEMS:
            continue
        violations.append(
            f"AL001: {relative} holds {coefficients} scientific coefficient literals "
            "but is not a registered self-contained model system. Move the equations "
            "into a domain package (e.g. */growth, */regeneration, */height) and keep "
            "the block as the composing facade."
        )
    return violations


# ---------------------------------------------------------------------------
# AL002: Equation modules must not import from simulation policy
# AL003: Block modules must not import from simulation policy
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
# presets, and orchestration packages are forbidden in equation and block modules.
FORBIDDEN_SIMULATION_SUFFIXES = (
    ".simulation.presets",
    ".simulation.policy",
    ".simulation.orchestration",
)


def _is_equation_module(path: Path) -> bool:
    """Return True if path is inside a domain equation package."""
    parts = path.parts
    for pkg in EQUATION_PACKAGES:
        if pkg in parts:
            return True
    return False


def _is_block_module(path: Path) -> bool:
    """Return True if path is inside a blocks/ package."""
    return "blocks" in path.parts


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
    """Check that block modules do not import from simulation policy."""
    violations = []
    for path in paths:
        if not path.suffix == ".py":
            continue
        if not _is_block_module(path):
            continue
        for module_name in _extract_imports(path):
            if _is_forbidden_import(module_name):
                violations.append(
                    f"AL003: {path.name} imports {module_name} "
                    f"(block modules must not import from simulation policy)"
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

    if violations:
        print("VIOLATIONS FOUND:")
        for v in violations:
            print(f"  {v}")
        print(f"\n{len(violations)} violation(s). FAIL.")
        return 1
    else:
        print("AL001: PASS")
        print("AL002: PASS")
        print("AL003: PASS")
        print("\nNo violations. PASS.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
