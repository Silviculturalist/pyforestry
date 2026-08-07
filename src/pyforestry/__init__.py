"""Top-level package for pyforestry.

The compact path to a projection -- you have a stand, you want it advanced::

    import pyforestry as pf

    result = pf.project(stand, model="elfving_2010", years=100, step=5, seed=42)

``pf.available_models()`` lists what ``model=`` accepts.

The other shape is a **composite pipeline**: you have a *site* rather than a
stand, and want one reconstructed and grown through a whole published workflow
(NYSKOG regeneration, young-stand growth, mortality, ingrowth, valuation).
``project`` cannot drive one, because a pipeline builds its own stand::

    from pyforestry.sweden.simulation.presets import get_pipeline

    pipeline = get_pipeline("elfving_2010_composite")
    table = pipeline.run_projection(site=site, n_steps=20)

``pf.available_pipelines()`` lists those. The two are named apart on purpose:
``"elfving_2010"`` is the growth model, ``"elfving_2010_composite"`` the whole
workflow around it, and the same string used to mean both.

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
    "available_pipelines": "pyforestry.projection",
    "Stand": "pyforestry.base.helpers",
    "Tree": "pyforestry.base.helpers",
    "CircularPlot": "pyforestry.base.helpers",
}

__all__ = [*_LAZY_SUBMODULES, *_LAZY_ATTRS]

if TYPE_CHECKING:  # pragma: no cover - for static checkers only
    from . import base, catalog, norway, simulation, sweden  # noqa: F401
    from .base.helpers import CircularPlot, Stand, Tree  # noqa: F401
    from .projection import (  # noqa: F401
        ProjectionResult,
        available_models,
        available_pipelines,
        project,
    )


def __getattr__(name: str) -> object:
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
