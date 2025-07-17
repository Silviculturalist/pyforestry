from .enums import Sweden

__all__ = ["SwedishSite", "Sweden"]


def __getattr__(name):
    if name == "SwedishSite":
        from .swedish_site import SwedishSite

        return SwedishSite
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
