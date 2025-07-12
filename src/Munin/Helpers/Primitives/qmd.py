"""
Module for computing and representing the quadratic mean diameter (QMD) of a stand.

The quadratic mean diameter is calculated as:

    QMD = sqrt((40000 * basal_area) / (pi * stems))

where:
    basal_area : float
        Basal area in square meters per hectare (m²/ha).
    stems : float
        Number of stems per hectare (stems/ha).

This module provides the `QuadraticMeanDiameter` class, a subclass of float
that carries both the QMD value (in centimeters) and an associated precision.
"""

from math import sqrt, pi

class QuadraticMeanDiameter(float):
    """
    A diameter measurement representing the quadratic mean diameter (QMD) in centimeters.

    This class subclasses `float` to store a QMD value while carrying an
    associated measurement precision. The QMD is defined as:

        QMD = sqrt((40000 * basal_area_m2_per_ha) / (pi * stems_per_ha))

    Attributes:
        precision (float): Uncertainty or precision of the QMD measurement (cm).
    """
    __slots__=('precision')
    def __new__(cls, value: float, precision: float = 0.0):
        """
        Create a new `QuadraticMeanDiameter` instance.

        Args:
            value (float): The computed QMD value in centimeters. Must be non-negative.
            precision (float, optional): The precision (uncertainty) of the QMD measurement in
                centimeters. Defaults to 0.0.

        Raises:
            ValueError: If `value` is negative.
            ValueError: If `precision` is negative.

        Returns:
            QuadraticMeanDiameter: A new instance with the specified value and precision.
        """
        if value < 0:
            raise ValueError("QuadraticMeanDiameter must be non-negative.")
        obj = float.__new__(cls, value)
        obj.precision = precision
        return obj

    @property
    def value(self) -> float:
        """
        Retrieve the raw QMD value.

        Returns:
            float: The QMD in centimeters.
        """
        return float(self)

    def __repr__(self):
        """
        Return the official string representation.

        Returns:
            str: String in the format
                "QuadraticMeanDiameter(<value> cm, precision=<precision> cm)".
        """
        return f"QuadraticMeanDiameter({float(self):.2f} cm, precision={self.precision:.2f} cm)"

    @staticmethod
    def compute_from(basal_area_m2_per_ha: float, stems_per_ha: float) -> "QuadraticMeanDiameter":
        """
        Compute QMD from basal area and stem count.

        This static method calculates the QMD using the formula:

            QMD = sqrt((40000 * basal_area_m2_per_ha) / (pi * stems_per_ha))

        Args:
            basal_area_m2_per_ha (float): Basal area in square meters per hectare.
            stems_per_ha (float): Number of stems per hectare.

        Raises:
            ValueError: If either `basal_area_m2_per_ha` or `stems_per_ha` is non-positive.

        Returns:
            QuadraticMeanDiameter: The computed QMD with default precision 0.0.
        """
        if basal_area_m2_per_ha <= 0:
            raise ValueError("Basal area must be positive.")
        if stems_per_ha <= 0:
            raise ValueError("Stem count must be positive.")

        raw_value = sqrt((40000.0 * basal_area_m2_per_ha) / (pi * stems_per_ha))
        return QuadraticMeanDiameter(raw_value)