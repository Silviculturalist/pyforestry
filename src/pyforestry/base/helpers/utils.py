"""Miscellaneous helper utilities."""

import warnings
from typing import Union


def enum_code(value: Union[int, float, bool, str]) -> Union[int, float, bool, str]:
    """Return numeric or label from an enum member or dataclass."""
    if hasattr(value, "value"):
        inner = value.value
        if hasattr(inner, "code"):
            if inner.__class__.__name__ == "ClimateZoneData":
                return inner.label
            return inner.code
        if hasattr(inner, "label"):
            return inner.label
    if hasattr(value, "code"):
        if value.__class__.__name__ == "ClimateZoneData":
            return value.label
        return value.code
    if hasattr(value, "label"):
        return value.label
    return value


def warn_proportion(name: str, value: float) -> None:
    """Warn when a proportion is outside [0, 1].

    Nothing about this is regional -- a species proportion is a proportion in any
    country -- but it lived in ``pyforestry.sweden._model_input_normalization``
    beside the genuinely Swedish normalisers. Norway had no way to reach it that
    did not import from Sweden, and this package has no cross-region imports.

    Args:
        name: The argument being checked, for the message.
        value: The proportion, expected in [0, 1].
    """
    if not (0.0 <= value <= 1.0):
        warnings.warn(
            f"{name}={value} is outside [0, 1]; results may be extrapolated.",
            stacklevel=2,
        )
