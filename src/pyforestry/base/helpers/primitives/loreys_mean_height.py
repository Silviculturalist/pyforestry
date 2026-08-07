"""Class representing Lorey's mean height (basal-area weighted mean height).

Lorey's mean height weights each tree's height by its basal area::

    HL = sum(g_i * h_i) / sum(g_i)

where ``g_i`` is the basal area of tree ``i`` and ``h_i`` its height.  Only
trees carrying a measured height contribute to both the numerator and the
denominator, so the result is the basal-area weighted mean of the *measured*
heights.  It is expressed in metres and carries an optional precision.
"""


class LoreysMeanHeight(float):
    """A basal-area weighted mean tree height.

    This subclass of :class:`float` stores Lorey's mean height in metres along
    with an associated measurement precision (typically a standard error).

    Parameters
    ----------
    value:
        The computed Lorey's mean height in metres. Must be non-negative.
    precision:
        Optional precision (standard error) of the estimate in metres.
    """

    __slots__ = "precision"

    def __new__(cls, value: float, precision: float = 0.0):
        """Create a new Lorey's mean height with optional precision."""
        if value < 0:
            raise ValueError("LoreysMeanHeight must be non-negative.")
        obj = float.__new__(cls, value)
        obj.precision = precision
        return obj

    @property
    def value(self) -> float:
        """Return the raw Lorey's mean height in metres."""
        return float(self)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """Return a readable representation of the height."""
        return f"LoreysMeanHeight({float(self):.2f} m, precision={self.precision:.2f} m)"
