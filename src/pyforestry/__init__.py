"""Top-level package for pyforestry.

The compact path to a projection::

    import pyforestry as pf

    result = pf.project(stand, model="elfving_2010", years=100, step=5, seed=42)

Everything else is lazily loaded on first access, so importing the package costs
almost nothing until you reach for a region.
"""

from importlib import import_module
from typing import TYPE_CHECKING

_LAZY_SUBMODULES = ("base", "simulation", "sweden", "norway", "catalog")
_LAZY_ATTRS = {
    "project": "pyforestry.projection",
    "ProjectionResult": "pyforestry.projection",
    "available_models": "pyforestry.projection",
    "Stand": "pyforestry.base.helpers",
    "Tree": "pyforestry.base.helpers",
    "CircularPlot": "pyforestry.base.helpers",
}

__all__ = [*_LAZY_SUBMODULES, *_LAZY_ATTRS]

if TYPE_CHECKING:  # pragma: no cover - for static checkers only
    from . import base, catalog, norway, simulation, sweden  # noqa: F401
    from .base.helpers import CircularPlot, Stand, Tree  # noqa: F401
    from .projection import ProjectionResult, available_models, project  # noqa: F401


def __getattr__(name):
    """Lazily load a subpackage, or a name from the compact front door."""
    if name in _LAZY_SUBMODULES:
        module = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    origin = _LAZY_ATTRS.get(name)
    if origin is not None:
        attr = getattr(import_module(origin), name)
        globals()[name] = attr
        return attr
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """List the lazily-available names for ``dir()`` and tab completion."""
    return sorted(__all__)
