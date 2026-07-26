"""Schema checks for the documentation notebooks.

The docs build executes these notebooks (``nbsphinx_execute = "always"``), so a
malformed one breaks the build rather than merely rendering oddly. These tests
catch the malformation before that happens.

They skip when ``nbformat`` is unavailable: it arrives with Jupyter rather than
as a declared test dependency, and a minimal test environment should not fail
for lacking it.
"""

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
