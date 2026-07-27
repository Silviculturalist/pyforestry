"""Minimal architecture lint check (AL001-AL005).

Usage:
    python scripts/check_architecture_lint.py [--changed-only BASE_SHA]

Without --changed-only, checks all files. With --changed-only, checks only
files modified since BASE_SHA.

Exit code 0 = pass, 1 = blocking violations found.

The rule registry in ``governance/architecture/rules/architecture_lint_rules.yaml``
documents these rules; :func:`check_registry` fails the run when it and this
script disagree about which rules exist and whether each blocks. Nothing else kept
them in sync, and they had drifted: AL003 and AL004 were enforced here while
appearing in no rules file, and AL002 was registered ``advisory`` while ``main``
failed the build on it like every other rule.
"""

from __future__ import annotations

import ast
import math
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src" / "pyforestry"
RULES_FILE = REPO_ROOT / "governance" / "architecture" / "rules" / "architecture_lint_rules.yaml"

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


def _relative_to_src(path: Path) -> str | None:
    """Return ``path`` relative to ``src/pyforestry/``, or ``None`` if outside it.

    Every rule here is scoped to the package. In ``--changed-only`` mode the file
    list is every changed ``.py`` in the repo, so the checks must be able to say
    "not mine" about a test or a script rather than raising ``ValueError`` out of
    ``relative_to`` and taking the whole gate down with them.
    """
    try:
        return path.relative_to(SRC_ROOT).as_posix()
    except ValueError:
        return None


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
    return abs(value) / 10 ** int(exponent) == 1.0


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

    Applies to every ``*/adapters/`` package in every region, ``__init__.py``
    included. There is no exception list: a module that needs to hold
    coefficients is a published system or a domain equation module, and belongs
    in ``*/systems/`` or a domain package respectively. ``__init__.py`` used to
    be skipped with no rationale, which left the one file in each adapter package
    that the rule could not see -- a place to put coefficients where a blocking
    check would still report PASS.
    """
    violations = []
    for path in paths:
        if path.suffix != ".py":
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
        relative = _relative_to_src(path) or path.as_posix()
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

# Domain equation packages (must not depend on simulation policy). This is the
# set of directory names ARCHITECTURE.md Context 2 owns; keep it in step with the
# packages that actually exist, since a domain package missing from here is simply
# unchecked. ``taper`` was missing while ``sweden/taper`` and ``norway/taper``
# both shipped.
EQUATION_PACKAGES = {
    "bark",
    "biomass",
    "growth",
    "height",
    "ingrowth",
    "mortality",
    "regeneration",
    "siteindex",
    "taper",
    "volume",
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
# AL005: No model constructs its own random generator
# ---------------------------------------------------------------------------

# A generator built where it is used cannot be seeded by the run that owns it,
# cannot be checkpointed, and -- when two of them are seeded from the same scalar,
# as the Elfving composite once did -- makes the interleaving of draws across
# them an unwritten part of every result. Stochastic kernels take ``rng`` as a
# parameter; runs get theirs from ``ctx.rng.child(...)``.
AL005_CONSTRUCTORS = (
    ("random", "Random"),
    ("np.random", "default_rng"),
    ("numpy.random", "default_rng"),
    ("np.random", "RandomState"),
    ("numpy.random", "RandomState"),
    ("np.random", "SeedSequence"),
    ("numpy.random", "SeedSequence"),
)

# The RNG service is where generators are supposed to be built.
AL005_EXEMPT = ("simulation/services/keyed_rng.py", "simulation/services/rng_bundle.py")


def _constructor_name(node: ast.Call) -> str | None:
    """Return ``"module.attr"`` for a call like ``np.random.default_rng(...)``."""
    func = node.func
    if not isinstance(func, ast.Attribute):
        return None
    prefix_parts: list[str] = []
    current: ast.expr = func.value
    while isinstance(current, ast.Attribute):
        prefix_parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        prefix_parts.append(current.id)
    else:
        return None
    prefix = ".".join(reversed(prefix_parts))
    return f"{prefix}.{func.attr}"


def check_al005(paths: list[Path]) -> list[str]:
    """Check that no module outside the RNG service constructs a generator."""
    wanted = {f"{module}.{attr}" for module, attr in AL005_CONSTRUCTORS}
    violations = []
    for path in paths:
        if path.suffix != ".py":
            continue
        relative = _relative_to_src(path)
        if relative is None:
            continue
        if any(relative.endswith(exempt) for exempt in AL005_EXEMPT):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):  # pragma: no cover - unreadable/invalid file
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _constructor_name(node)
            if name in wanted:
                violations.append(
                    f"AL005: {relative}:{node.lineno} constructs a random generator "
                    f"({name}). A generator built where it is used cannot be seeded by "
                    "the run, cannot be checkpointed, and if a second one is seeded "
                    "from the same scalar the order in which the two are drawn from "
                    "silently becomes part of the result. Take rng as a parameter, or "
                    "ask the run for a keyed stream: ctx.rng.child('mortality')."
                )
    return violations


# ---------------------------------------------------------------------------
# Rule registry
# ---------------------------------------------------------------------------

#: Every rule this script enforces: id, the check, and whether a violation fails
#: the build. This is the executable half of the registry; the YAML at
#: :data:`RULES_FILE` is the documented half, and :func:`check_registry` fails
#: when the two disagree, because nothing else did.
RULES: tuple[tuple[str, str, object], ...] = (
    ("AL001", "blocking", check_al001),
    ("AL002", "blocking", check_al002),
    ("AL003", "blocking", check_al003),
    ("AL004", "blocking", check_al004),
    ("AL005", "blocking", check_al005),
)

_YAML_RULE_RE = re.compile(r"^  (AL\d{3}):\s*$")
_YAML_MODE_RE = re.compile(r"^    mode:\s*(\w+)")


def _registered_rules() -> dict[str, str]:
    """Return ``{rule_id: mode}`` as declared in the rules YAML.

    Parsed with two regexes rather than a YAML library so the gate needs no
    dependency the package does not already ship.
    """
    registered: dict[str, str] = {}
    current: str | None = None
    for line in RULES_FILE.read_text(encoding="utf-8").splitlines():
        rule_match = _YAML_RULE_RE.match(line)
        if rule_match:
            current = rule_match.group(1)
            continue
        mode_match = _YAML_MODE_RE.match(line)
        if mode_match and current is not None:
            registered.setdefault(current, mode_match.group(1))
    return registered


def check_registry() -> list[str]:
    """Check that the rules YAML and this script agree on rules and modes.

    Returns:
        One message per disagreement: a rule enforced but not registered, a rule
        registered but not enforced, or a rule whose declared mode is not the one
        ``main`` applies. A registry that does not describe the gate is worse than
        no registry, because it is read as though it does.
    """
    if not RULES_FILE.exists():  # pragma: no cover - registry is version-controlled
        return [f"REGISTRY: {RULES_FILE} is missing; it is the documented rule set."]
    registered = _registered_rules()
    enforced = {rule_id: mode for rule_id, mode, _check in RULES}
    problems = []
    for rule_id, mode in sorted(enforced.items()):
        if rule_id not in registered:
            problems.append(
                f"REGISTRY: {rule_id} is enforced by this script but not registered in "
                f"{RULES_FILE.name}. Add it, or stop enforcing it."
            )
        elif registered[rule_id] != mode:
            problems.append(
                f"REGISTRY: {rule_id} is registered as {registered[rule_id]!r} in "
                f"{RULES_FILE.name} but enforced as {mode!r}. An 'advisory' rule that "
                f"fails the build is not advisory."
            )
    for rule_id in sorted(registered):
        if rule_id not in enforced:
            problems.append(
                f"REGISTRY: {rule_id} is registered in {RULES_FILE.name} but this script "
                f"enforces nothing for it."
            )
    return problems


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

    blocking: list[str] = list(check_registry())
    advisory: list[str] = []
    for rule_id, mode, check in RULES:
        found = check(paths)  # type: ignore[operator]
        if not found:
            print(f"{rule_id}: PASS")
        elif mode == "blocking":
            blocking.extend(found)
        else:
            advisory.extend(found)

    if advisory:
        print("\nADVISORY (does not fail the build):")
        for message in advisory:
            print(f"  {message}")

    if blocking:
        print("\nVIOLATIONS FOUND:")
        for message in blocking:
            print(f"  {message}")
        print(f"\n{len(blocking)} blocking violation(s). FAIL.")
        return 1

    print("\nNo blocking violations. PASS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
