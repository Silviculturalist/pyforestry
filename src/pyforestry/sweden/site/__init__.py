"""Init   utilities and interfaces.

Source: Swedish forestry domain models and helper implementations curated in pyforestry.
"""

from .enums import Sweden

__all__ = ["SwedishSite", "Sweden"]


def __getattr__(name):
    """Getattr.

    Source:
        Swedish forestry domain models and helper implementations curated in pyforestry.
    """
    if name == "SwedishSite":
        from .swedish_site import SwedishSite

        return SwedishSite
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
