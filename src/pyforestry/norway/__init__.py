"""Norway regional package for equations and model APIs."""

from importlib import import_module
from typing import TYPE_CHECKING

from .helpers import tree_species_extension as _  # noqa: F401

__all__ = ["bark", "volume", "siteindex", "taper", "growth", "blocks", "simulation"]

if TYPE_CHECKING:  # pragma: no cover - typing only
    from . import bark, blocks, growth, simulation, siteindex, taper, volume  # noqa: F401


def __getattr__(name: str):
    """Lazy-load Norway subpackages."""
    if name in __all__:
        module = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """List the Norway subpackages for ``dir()`` and tab-completion."""
    return sorted(__all__)
