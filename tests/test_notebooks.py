"""Schema and API checks for the documentation notebooks.

The docs build executes these notebooks (``nbsphinx_execute = "always"``), so a
malformed *or stale* one breaks the build rather than merely rendering oddly.
These tests catch both before that happens: the schema checks look at the file
structure, and :func:`test_notebook_imports_resolve` resolves every name the
notebooks import from ``pyforestry``, which is how a rename in the library shows
up here. Executing the notebooks would catch more, but costs minutes; resolving
their imports costs milliseconds and covers the failure that actually keeps
happening.

They skip when ``nbformat`` is unavailable: it arrives with Jupyter rather than
as a declared test dependency, and a minimal test environment should not fail
for lacking it.
"""

import ast
import importlib
import json
import pathlib

import pytest

NOTEBOOK_DIR = pathlib.Path(__file__).resolve().parents[1] / "docs" / "source" / "notebooks"
NOTEBOOKS = sorted(NOTEBOOK_DIR.rglob("*.ipynb"))

# ``execution_count`` and ``outputs`` describe the result of running a cell, so
# the schema permits them only on code cells. Some notebook editors add them to
# markdown cells, which renders fine but fails validation.
CODE_ONLY_KEYS = ("execution_count", "outputs")


def _ids(paths):
    return [p.relative_to(NOTEBOOK_DIR).as_posix() for p in paths]


def test_notebooks_are_discovered():
    """Guard against the glob silently matching nothing."""
    assert NOTEBOOKS, f"no notebooks found under {NOTEBOOK_DIR}"


@pytest.mark.parametrize("path", NOTEBOOKS, ids=_ids(NOTEBOOKS))
def test_notebook_matches_the_nbformat_schema(path):
    """Every notebook validates, so the docs build cannot trip over one."""
    nbformat = pytest.importorskip("nbformat")
    nbformat.validate(nbformat.read(str(path), as_version=4))


@pytest.mark.parametrize("path", NOTEBOOKS, ids=_ids(NOTEBOOKS))
def test_only_code_cells_carry_execution_metadata(path):
    """No markdown or raw cell carries code-cell-only keys.

    Checked separately from schema validation because this is the specific way
    these notebooks have gone wrong before, and the schema error it produces
    ("Additional properties are not allowed") does not say which cell or file.
    """
    notebook = json.loads(path.read_text(encoding="utf-8"))
    offenders = [
        (index, cell.get("cell_type"), key)
        for index, cell in enumerate(notebook["cells"])
        if cell.get("cell_type") != "code"
        for key in CODE_ONLY_KEYS
        if key in cell
    ]
    assert not offenders, (
        f"{path.name}: {len(offenders)} code-only key(s) on non-code cells: {offenders}. "
        "Remove 'execution_count' and 'outputs' from markdown and raw cells."
    )


def _pyforestry_imports(path: pathlib.Path):
    """Yield ``(module, name)`` for every pyforestry name a notebook imports.

    ``name`` is ``None`` for a plain ``import pyforestry.x``. Cells that do not
    parse (IPython magics and the like) are skipped rather than failed on: this
    test is about stale API references, not notebook syntax.
    """
    notebook = json.loads(path.read_text(encoding="utf-8"))
    for cell in notebook["cells"]:
        if cell.get("cell_type") != "code":
            continue
        try:
            tree = ast.parse("".join(cell["source"]))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("pyforestry"):
                for alias in node.names:
                    yield node.module, alias.name
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("pyforestry"):
                        yield alias.name, None


@pytest.mark.parametrize("path", NOTEBOOKS, ids=_ids(NOTEBOOKS))
def test_notebook_imports_resolve(path):
    """Every pyforestry name a notebook imports still exists.

    The docs build runs these notebooks, so a renamed function turns into a red
    build. Resolving the imports catches that in milliseconds.
    """
    missing = []
    for module_name, attribute in _pyforestry_imports(path):
        try:
            module = importlib.import_module(module_name)
        except ImportError as exc:  # pragma: no cover - a broken import is the failure
            missing.append(f"{module_name} ({exc})")
            continue
        if attribute is None:
            continue
        if not hasattr(module, attribute):
            try:
                importlib.import_module(f"{module_name}.{attribute}")
            except ImportError:
                missing.append(f"{module_name}.{attribute}")
    assert not missing, (
        f"{path.name} imports names that no longer exist: {missing}. "
        "The docs build executes this notebook, so this would fail the build."
    )
