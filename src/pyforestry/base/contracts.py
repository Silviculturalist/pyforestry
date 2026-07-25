"""Foundational provenance and introspection contracts.

The :class:`SourceReference` dataclass and the :class:`Describable` /
:class:`FormulaModuleDescriptor` protocols describe *what* a component is — its
identity, bibliographic provenance, species applicability, and units —
independent of any simulation runtime. They live at the ``base`` level because
formula/domain modules across every region expose them (for example a module's
``DESCRIPTOR``), so nothing above ``base`` should have to reach into the
simulation package for this vocabulary.

The simulation runtime re-exports these names from
:mod:`pyforestry.simulation.contracts` for convenience and backward
compatibility.

Source:
    Internal pyforestry architecture and runtime contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Protocol, Sequence, Tuple


@dataclass(frozen=True)
class SourceReference:
    """Bibliographic provenance for a scientific formula or model."""

    author: str
    year: int
    title: str
    appendix: str = ""
    note: str = ""


class Describable(Protocol):
    """Any component that declares its identity and provenance."""

    @property
    def component_id(self) -> str:
        """Stable identifier for this component."""
        ...

    @property
    def source(self) -> SourceReference:
        """Bibliographic provenance for this component."""
        ...


class FormulaModuleDescriptor(Protocol):
    """Introspection contract for a formula module (not per-function).

    Each formula package may expose a module-level ``DESCRIPTOR`` object
    implementing this protocol. The descriptor sits next to the kernel
    functions, not around them; kernel function signatures are not changed.
    """

    @property
    def component_id(self) -> str:
        """Stable identifier for this formula module."""
        ...

    @property
    def source(self) -> SourceReference:
        """Bibliographic provenance for this formula module."""
        ...

    @property
    def species_groups(self) -> Mapping[str, frozenset[str]]:
        """Species groups and their constituent species identifiers."""
        ...

    @property
    def units(self) -> Mapping[str, str]:
        """Unit contract mapping parameter/output names to unit strings."""
        ...

    @property
    def kernel_names(self) -> Sequence[str]:
        """Public function names exposed by this formula module."""
        ...


@dataclass(frozen=True)
class FormulaDescriptor:
    """Concrete, declarative :class:`FormulaModuleDescriptor` for formula modules.

    A module publishes its introspection metadata with minimal boilerplate::

        DESCRIPTOR = FormulaDescriptor(
            component_id="brandel_1990_volume",
            source=SourceReference(author="Brandel, G.", year=1990, title="..."),
            kernel_names=("BrandelVolume",),
        )

    ``species_groups`` should use full scientific names (e.g. ``"Pinus sylvestris"``)
    so the catalog's species filter matches cleanly.

    ``kind`` distinguishes the two tiers the catalog surfaces: ``"formula"`` for
    equation/kernel modules (the default) and ``"model"`` for composed, runnable
    model adapters (the ``blocks/`` tier). A ``"model"`` descriptor may set
    ``domain`` to the scientific domain it belongs to (e.g. ``"growth"``, since
    its module path lives under ``blocks/``) and list the formula
    ``component_id``s it ``composes``.
    """

    component_id: str
    source: SourceReference
    species_groups: Mapping[str, frozenset[str]] = field(default_factory=dict)
    units: Mapping[str, str] = field(default_factory=dict)
    kernel_names: Tuple[str, ...] = ()
    kind: str = "formula"
    domain: Optional[str] = None
    composes: Tuple[str, ...] = ()


__all__ = [
    "Describable",
    "FormulaDescriptor",
    "FormulaModuleDescriptor",
    "SourceReference",
]
