"""Every module publishes its provenance the same way.

There were two idioms. Fifty modules used the declarative
:class:`~pyforestry.base.contracts.FormulaDescriptor`; thirty-four -- all of them
Sweden, none of Norway -- hand-rolled a ``_Descriptor`` class of five
``@property`` methods, none annotated, none documented, most deferring the
``SourceReference`` import into the property body to dodge a cycle that does not
exist (``base.contracts`` imports nothing from this package).

``FormulaDescriptor`` exists precisely so a module publishes this "with minimal
boilerplate". These tests are what stops the second idiom coming back.
"""

from __future__ import annotations

import ast
import importlib
import warnings
from pathlib import Path

import pytest

from pyforestry.base.contracts import FormulaDescriptor, FormulaModuleDescriptor

SRC = Path(__file__).resolve().parents[1] / "src" / "pyforestry"


def test_every_descriptor_is_a_formula_descriptor() -> None:
    """No module hand-rolls the descriptor protocol."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from pyforestry import catalog

        entries = catalog.list_models()

    assert entries, "discovery found nothing; the catalog or its roots moved"

    for entry in entries:
        descriptor = importlib.import_module(entry.module).DESCRIPTOR
        assert isinstance(descriptor, FormulaDescriptor), (
            f"{entry.module} publishes a hand-rolled descriptor. Use FormulaDescriptor: "
            "it is the same five fields without five @property methods, and it is what "
            "every other module in the package uses."
        )


#: Classes whose name ends in "Descriptor" but which describe something other than
#: a formula module. The valuation ones describe a set of removals to price.
_NON_PROVENANCE_DESCRIPTORS = {
    "FormulaDescriptor",
    "FormulaModuleDescriptor",
    "VolumeDescriptor",
    "EmptyVolumeDescriptor",
    "TreeVolumeDescriptor",
    "BulkVolumeDescriptor",
}


def test_no_module_defines_a_provenance_descriptor_class() -> None:
    """The source text, not just the resolved object -- an unimported one still rots."""
    offenders = []
    for path in SRC.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - not expected in-tree
            continue
        for node in ast.walk(tree):
            if not (isinstance(node, ast.ClassDef) and node.name.endswith("Descriptor")):
                continue
            if node.name in _NON_PROVENANCE_DESCRIPTORS:
                continue
            offenders.append(f"{path.relative_to(SRC).as_posix()}:{node.lineno} {node.name}")
    assert offenders == [], "hand-rolled descriptor classes: " + ", ".join(offenders)


def _type_checking_line_ranges(tree: ast.Module) -> list[range]:
    """Line ranges covered by ``if TYPE_CHECKING:`` blocks."""
    ranges = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        name = test.id if isinstance(test, ast.Name) else getattr(test, "attr", None)
        if name == "TYPE_CHECKING":
            ranges.append(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    return ranges


def test_source_reference_is_imported_at_module_scope() -> None:
    """``base.contracts`` has no pyforestry imports, so there is no cycle to defer.

    Twenty-six modules deferred this import into a function body and seventy-two
    did not -- the split ran *within* packages, with ``mortality/elfving_2013.py``
    importing at the top and ``mortality/soderberg_1986.py`` inside a property.
    An import under ``if TYPE_CHECKING:`` is not a deferred runtime import and is
    allowed.
    """
    offenders = []
    for path in SRC.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover
            continue
        type_checking = _type_checking_line_ranges(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.module != "pyforestry.base.contracts":
                continue
            if node.col_offset == 0:
                continue
            if any(node.lineno in span for span in type_checking):
                continue
            offenders.append(f"{path.relative_to(SRC).as_posix()}:{node.lineno}")
    assert offenders == [], "deferred imports of the provenance vocabulary: " + ", ".join(
        offenders
    )


def test_the_protocol_and_the_catalog_agree_on_the_contract() -> None:
    """The declared contract is the used contract.

    ``FormulaModuleDescriptor`` declared five members; the catalog read eight,
    with ``kind``, ``domain`` and ``composes`` fetched via ``getattr`` defaults.
    A descriptor could satisfy the published protocol in full and still be unable
    to declare itself a model.
    """
    from pyforestry import catalog

    declared = {
        name
        for name in vars(FormulaModuleDescriptor)
        if not name.startswith("_") and isinstance(vars(FormulaModuleDescriptor)[name], property)
    }
    assert set(catalog._DESCRIPTOR_ATTRS) == declared
    assert declared <= {f.name for f in FormulaDescriptor.__dataclass_fields__.values()}


@pytest.mark.parametrize("field", ["kind", "domain", "composes"])
def test_formula_descriptor_supplies_the_catalog_fields(field: str) -> None:
    """The concrete descriptor answers every member the catalog asks for."""
    from pyforestry.base.contracts import SourceReference

    descriptor = FormulaDescriptor(
        component_id="x",
        source=SourceReference(author="A", year=1, title="t"),
    )
    assert hasattr(descriptor, field)
