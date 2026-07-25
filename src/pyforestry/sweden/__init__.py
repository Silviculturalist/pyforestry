"""Sweden regional package for equations and model APIs.

Importing this package registers the Swedish tree-species extension and exposes
its domain subpackages (``volume``, ``siteindex``, ``mortality``, …) for lazy,
tab-completable access.
"""

from importlib import import_module
from typing import TYPE_CHECKING

from .helpers import tree_species_extension as _  # noqa: F401

__all__ = [
    "bark",
    "biomass",
    "blocks",
    "geo",
    "growth",
    "height",
    "helpers",
    "ingrowth",
    "misc",
    "mortality",
    "pricelist",
    "regeneration",
    "simulation",
    "site",
    "siteindex",
    "taper",
    "timber",
    "volume",
]

if TYPE_CHECKING:  # pragma: no cover - typing only
    from . import (  # noqa: F401
        bark,
        biomass,
        blocks,
        geo,
        growth,
        height,
        helpers,
        ingrowth,
        misc,
        mortality,
        pricelist,
        regeneration,
        simulation,
        site,
        siteindex,
        taper,
        timber,
        volume,
    )


def __getattr__(name: str):
    """Lazy-load a Sweden subpackage on first access."""
    if name in __all__:
        module = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """List the Sweden subpackages for ``dir()`` and tab-completion."""
    return sorted(__all__)
