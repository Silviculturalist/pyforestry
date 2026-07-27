"""Foundational provenance and introspection contracts.

The :class:`SourceReference` dataclass and the :class:`Describable` /
:class:`FormulaModuleDescriptor` protocols describe *what* a component is — its
identity, bibliographic provenance, species applicability, and units —
independent of any simulation runtime. They live at the ``base`` level because
formula/domain modules across every region expose them (for example a module's
``DESCRIPTOR``), so nothing above ``base`` should have to reach into the
simulation package for this vocabulary.

This is the only import path for these names. :mod:`pyforestry.simulation.contracts`
holds what the *runtime* defines (:class:`~pyforestry.simulation.contracts.SimulationPreset`)
and deliberately does not re-export this vocabulary, so that an equation module
never has to import from the simulation tier to describe itself.
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


@dataclass(frozen=True)
class ImputedValue:
    """A modelled value for one attribute, with its provenance.

    Lives here rather than next to the imputers because
    :class:`~pyforestry.base.helpers.tree.Tree` stores these, and a leaf data
    class must not depend on the imputation package that fills them in.

    Attributes:
        attribute: The attribute this value stands in for, e.g. ``"height_m"``.
        value: The modelled value, in the attribute's own units.
        imputer_id: ``component_id`` of the imputer that produced it.
        source: The publication behind that imputer. A user-supplied callable
            carries the ``"(none)"``/year-0 sentinel, so an uncited value is
            visibly uncited rather than silently unattributed.
    """

    attribute: str
    value: float
    imputer_id: str
    source: SourceReference

    def __post_init__(self) -> None:
        """Reject a non-finite or unnamed value."""
        if not self.attribute:
            raise ValueError("attribute must be a non-empty name.")
        if self.value != self.value or self.value in (float("inf"), float("-inf")):
            raise ValueError(f"Imputed {self.attribute} must be finite, got {self.value!r}.")

    @property
    def is_cited(self) -> bool:
        """Whether this value traces to a publication rather than a bare callable."""
        return self.source.author != "(none)"

    def __float__(self) -> float:
        """Return the value, so an ImputedValue can be used in arithmetic."""
        return float(self.value)


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
    models (the ``adapters/`` and ``systems/`` tiers). A ``"model"`` descriptor
    may set ``domain`` to the scientific domain it belongs to (e.g. ``"growth"``,
    since its module path lives under ``adapters/``) and list the formula
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
    "ImputedValue",
    "SourceReference",
]
