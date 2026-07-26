"""Swedish growth models, organised as one subpackage per publication.

This package is a namespace container: each model lives in its own subpackage
(``elfving_2010``, ``soderberg_1986``) and exposes a ``DESCRIPTOR``
(:class:`~pyforestry.simulation.contracts.FormulaModuleDescriptor`) plus its
kernel functions. The two descriptors are re-exported here under
``ELFVING_2010`` and ``SODERBERG_1986`` for discovery and introspection. They
resolve lazily via :pep:`562` ``__getattr__`` so that importing one growth model
does not pull in the other.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

__all__ = ["ELFVING_2010", "SODERBERG_1986"]

# Public descriptor name -> model subpackage providing ``DESCRIPTOR``.
_DESCRIPTOR_MODULES = {
    "ELFVING_2010": "elfving_2010",
    "SODERBERG_1986": "soderberg_1986",
}

if TYPE_CHECKING:  # pragma: no cover - typing only
    from pyforestry.base.contracts import FormulaModuleDescriptor

    ELFVING_2010: FormulaModuleDescriptor
    SODERBERG_1986: FormulaModuleDescriptor


def __getattr__(name: str):
    """Lazily resolve a growth-model descriptor by its public name."""
    module_name = _DESCRIPTOR_MODULES.get(name)
    if module_name is not None:
        module = import_module(f"{__name__}.{module_name}")
        return module.DESCRIPTOR
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    """Return the public descriptor names for ``dir()``."""
    return sorted(__all__)
