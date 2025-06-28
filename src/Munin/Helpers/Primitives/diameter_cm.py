"""Module for handling diameter measurements and conversions.

This module provides functions and classes to represent tree
stem diameters in centimeters and to perform unit conversions,
calculations of basal area per tree, and validation of inputs.

Classes:
    Diameter: Represents a diameter measurement in cm with optional unit conversion.

Functions:
    diameter_to_basal_area: Compute basal area (cm²) from diameter.
"""


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
    __slots__ = ('over_bark', 'measurement_height_m')

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
            raise ValueError('measurement_height_m must be >= 0 m!')
        
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
        return (f"Diameter_cm({float(self)}, over_bark={self.over_bark}, "
                f"measurement_height_m={self.measurement_height_m})")
