"""Price list datasets used for economic calculations."""

from .mellanskog_2013 import (
    MELLANSKOG_2013_IDENTITY,
    MELLANSKOG_2013_PRICE_DATA,
    Mellanskog_2013_price_data,
)

__all__ = [
    "MELLANSKOG_2013_IDENTITY",
    # The name the module's own docstring tells you to use. It was reachable only
    # by importing the submodule directly, because this package re-exported the
    # older spelling alone -- so following the documented idiom raised ImportError.
    "MELLANSKOG_2013_PRICE_DATA",
    # Kept: it is what the rest of the package and its tests still import.
    "Mellanskog_2013_price_data",
]
