class Diameter_cm(float):
    """
    Diameter, in centimeters, stored as a float but including additional metadata:
      - over_bark (bool): whether the diameter is measured over bark.
      - measurement_height_m (float): height at which diameter is measured (default: 1.3 m).
    """
    # Declare the new instance attributes in __slots__
    __slots__ = ('over_bark', 'measurement_height_m')

    def __new__(cls, value: float, over_bark: bool = True, measurement_height_m: float = 1.3):
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
        """Returns the pure float value of the diameter."""
        return float(self)

    def __repr__(self):
        # Note: Accessing self.over_bark is now perfectly valid
        return (f"Diameter_cm({float(self)}, over_bark={self.over_bark}, "
                f"measurement_height_m={self.measurement_height_m})")
