"""Näsberg (1985) branch-and-bound bucking algorithm."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "Nasberg_1985_BranchBound",
    "BuckingConfig",
    "CrossCutSection",
    "BuckingResult",
    "QualityType",
    "_TreeCache",
]


def __getattr__(name: str) -> Any:
    """Lazily import submodules to avoid circular dependencies."""
    if name in __all__:
        module_map = {
            "Nasberg_1985_BranchBound": "algorithm",
            "BuckingConfig": "config",
            "CrossCutSection": "crosscut",
            "BuckingResult": "result",
            "_TreeCache": "cache",
        }
        if name == "QualityType":
            from pyforestry.base.helpers.bucking import QualityType

            return QualityType
        module = import_module(f"{__name__}.{module_map[name]}")
        return getattr(module, name)
    raise AttributeError(name)
