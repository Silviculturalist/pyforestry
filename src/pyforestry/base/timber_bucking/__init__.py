"""Timber bucking utilities."""

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
    """Lazily proxy attributes from the ``nasberg_1985`` package."""
    if name in __all__:
        module = import_module(".nasberg_1985", __name__)
        return getattr(module, name)
    raise AttributeError(name)
