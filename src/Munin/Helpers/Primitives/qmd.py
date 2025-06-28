class QuadraticMeanDiameter(float):
    """
    Represents the quadratic mean diameter (in centimeters) with an associated precision.
    
    The value is computed as:
        QMD = sqrt((40000 * BasalArea) / (pi * Stems))
    where BasalArea is in m²/ha and Stems is in stems/ha.
    """
    __slots__=('precision')
    def __new__(cls, value: float, precision: float = 0.0):
        if value < 0:
            raise ValueError("QuadraticMeanDiameter must be non-negative.")
        obj = float.__new__(cls, value)
        obj.precision = precision
        return obj

    @property
    def value(self) -> float:
        return float(self)

    def __repr__(self):
        return f"QuadraticMeanDiameter({float(self):.2f} cm, precision={self.precision:.2f} cm)"
