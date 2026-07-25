"""Top-level package for pyforestry."""

from importlib import import_module
from typing import TYPE_CHECKING

__all__ = ["base", "simulation", "sweden", "norway", "catalog"]

if TYPE_CHECKING:  # pragma: no cover - for static checkers only
    from . import base, catalog, norway, simulation, sweden  # noqa: F401


def __getattr__(name):
    """Lazily load top-level regional/runtime subpackages and the model catalog."""
    if name in __all__:
        module = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
