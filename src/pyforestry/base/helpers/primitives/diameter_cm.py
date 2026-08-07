"""Diameter primitives and conversion helpers.

This module defines the ``Diameter_cm`` value object and helper functions for
converting between diameter and basal-area representations. The formulas mirror
the standard geometric relationships used in forestry growth calculations.

Source:
    Standard basal-area geometry for diameter/basal-area conversion
    workflows in ``pyforestry``.
"""

from __future__ import annotations

from math import pi, sqrt


class Diameter_cm(float):
    """
    A diameter measurement in centimeters, with metadata.

    This class subclasses `float` to store a diameter value (cm) while
    also carrying:

    Attributes:
        over_bark (bool): Whether the diameter is measured over bark.
        measurement_height_m (float): Height at which the diameter was measured (in meters).
    """

    # Declare the new instance attributes in __slots__
    __slots__ = ("over_bark", "measurement_height_m")

    def __new__(cls, value: float, over_bark: bool = True, measurement_height_m: float = 1.3):
        """
        Create a new `Diameter_cm` instance.

        Args:
            value (float): Diameter value in centimeters. Must be non-negative.
            over_bark (bool, optional): Whether the diameter is measured over bark.
                Defaults to True.
            measurement_height_m (float, optional): Height at which the diameter is
                measured, in meters. Must be non-negative. Defaults to 1.3.

        Raises:
            ValueError: If `value` is negative.
            ValueError: If `measurement_height_m` is negative.

        Returns:
            Diameter_cm: A new instance with the specified value and metadata.
        """
        if value < 0:
            raise ValueError("Diameter must be non-negative.")
        if measurement_height_m < 0:
            raise ValueError("measurement_height_m must be >= 0 m!")

        # Create the instance using the parent's __new__
        obj = super().__new__(cls, value)

        # Now, these assignments are valid and understood by linters
        obj.over_bark = over_bark
        obj.measurement_height_m = measurement_height_m

        return obj

    @property
    def value(self) -> float:
        """
        Return the raw diameter value as a float.

        Returns:
            float: The diameter in centimeters.
        """
        return float(self)

    def __repr__(self):
        """
        Return the canonical string representation.

        Returns:
            str: String in the format
                "Diameter_cm(value, over_bark=..., measurement_height_m=...)".
        """
        return (
            f"Diameter_cm({float(self)}, over_bark={self.over_bark}, "
            f"measurement_height_m={self.measurement_height_m})"
        )


def diameter_to_basal_area_cm2(diameter_cm: float) -> float:
    """Compute basal area (cm²) from diameter (cm).

    Source:
        Standard basal-area geometry (area = pi * d^2 / 4).

    Args:
        diameter_cm (float): Diameter at breast height in centimeters.

    Returns:
        float: Basal area in cm².

    Raises:
        ValueError: If ``diameter_cm`` is negative.
    """
    if diameter_cm < 0:
        raise ValueError("diameter_cm must be non-negative.")
    return (pi / 4.0) * (diameter_cm**2)


def basal_area_cm2_to_diameter_cm(basal_area_cm2: float) -> float:
    """Compute diameter (cm) from basal area (cm²).

    Source:
        Standard basal-area geometry (area = pi * d^2 / 4).

    Args:
        basal_area_cm2 (float): Basal area in cm².

    Returns:
        float: Diameter in centimeters.

    Raises:
        ValueError: If ``basal_area_cm2`` is negative.
    """
    if basal_area_cm2 < 0:
        raise ValueError("basal_area_cm2 must be non-negative.")
    return sqrt(4.0 * basal_area_cm2 / pi)


def diameter_growth_to_basal_area_growth_cm2(
    diameter_cm: float, diameter_growth_cm: float
) -> float:
    """Convert diameter growth (cm) to basal area growth (cm²).

    Source:
        Standard basal-area geometry (area = pi * d^2 / 4).

    Args:
        diameter_cm (float): Current diameter (cm).
        diameter_growth_cm (float): Diameter increment (cm).

    Returns:
        float: Basal area growth (cm²).

    Raises:
        ValueError: If inputs are negative.
    """
    if diameter_cm < 0:
        raise ValueError("diameter_cm must be non-negative.")
    if diameter_growth_cm < 0:
        raise ValueError("diameter_growth_cm must be non-negative.")
    return (pi / 4.0) * ((diameter_cm + diameter_growth_cm) ** 2 - diameter_cm**2)


def basal_area_growth_cm2_to_diameter_growth_cm(
    diameter_cm: float, basal_area_growth_cm2: float
) -> float:
    """Convert basal area growth (cm²) to diameter growth (cm).

    Source:
        Standard basal-area geometry (d = sqrt(4 * area / pi)).

    Args:
        diameter_cm (float): Current diameter (cm).
        basal_area_growth_cm2 (float): Basal area growth (cm²).

    Returns:
        float: Diameter increment (cm).

    Raises:
        ValueError: If inputs are negative.
    """
    if diameter_cm < 0:
        raise ValueError("diameter_cm must be non-negative.")
    if basal_area_growth_cm2 < 0:
        raise ValueError("basal_area_growth_cm2 must be non-negative.")
    return sqrt((4.0 * basal_area_growth_cm2 / pi) + diameter_cm**2) - diameter_cm


__all__ = [
    "Diameter_cm",
    "diameter_to_basal_area_cm2",
    "basal_area_cm2_to_diameter_cm",
    "diameter_growth_to_basal_area_growth_cm2",
    "basal_area_growth_cm2_to_diameter_growth_cm",
]
