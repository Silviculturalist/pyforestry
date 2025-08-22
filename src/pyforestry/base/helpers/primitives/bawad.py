"""Class representing the basal-area weighted mean diameter (BAWAD).

BAWAD is defined as the ratio of the sum of cubed diameters to the sum
of squared diameters for a collection of trees::

    BAWAD = sum(D^3) / sum(D^2)

It is expressed in centimetres and carries an optional precision
attribute.
"""


class BasalAreaWeightedDiameter(float):
    """A diameter measurement weighted by basal area.

        This subclass of :class:`float` stores the basal-area weighted mean
    diameter in centimetres along with an associated measurement
    precision.

        Parameters
        ----------
        value:
            The computed BAWAD value in centimetres. Must be non-negative.
        precision:
            Optional precision (standard error) of the measurement in
            centimetres.
    """

    __slots__ = "precision"

    def __new__(cls, value: float, precision: float = 0.0):
        if value < 0:
            raise ValueError("BasalAreaWeightedDiameter must be non-negative.")
        obj = float.__new__(cls, value)
        obj.precision = precision
        return obj

    @property
    def value(self) -> float:
        """Return the raw BAWAD value in centimetres."""
        return float(self)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """Return a readable representation of the diameter."""
        return (
            f"BasalAreaWeightedDiameter({float(self):.2f} cm, precision={self.precision:.2f} cm)"
        )
