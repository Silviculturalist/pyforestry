from enum import Enum

# --- Age Enum ---
class Age(Enum):
    """
    Enumeration of age measurement types.

    Attributes:
        TOTAL (Age): Total age measurement.
        DBH (Age): Diameter at breast height age measurement.
    """
    TOTAL = 1
    DBH = 2

    def __call__(self, value: float) -> 'AgeMeasurement': # Use forward reference string
        """
        Create an AgeMeasurement for this age type.

        Args:
            value (float): Measured age value; must be non-negative.

        Returns:
            AgeMeasurement: Instance with given value and this age code.

        Raises:
            ValueError: If value is negative.
        """
        return AgeMeasurement(value, self.value)

# --- AgeMeasurement Class ---
class AgeMeasurement(float):
    """
    A float subclass representing an age measurement with type code.

    Attributes:
        code (int): Age enum code corresponding to measurement type.
    """

    __slots__ = ('code')

    def __new__(cls, value: float, code: int):
        """
        Create a new AgeMeasurement.

        Args:
            value (float): Age value; must be non-negative.
            code (int): Numeric code from Age enum.

        Returns:
            AgeMeasurement: New instance with assigned code.

        Raises:
            ValueError: If value is negative or code invalid.
        """
        if value < 0:
            raise ValueError("Age must be non-negative.")
        # Ensure code is valid using the Age enum definition
        if code not in [m.value for m in Age]: # Check against Age enum values
             raise ValueError(f"Invalid age code: {code}. Must be one of {[m.value for m in Age]}.")
        obj = super().__new__(cls, value)
        obj.code = code
        return obj

    @property
    def value(self) -> float:
        """
        Get the measurement value as a float.

        Returns:
            float: The age value.
        """
        return float(self)

    def __repr__(self):
        """
        String representation including code and type name.

        Returns:
            str: Formatted repr string.
        """
        # Ensure Age enum lookup is safe
        age_type = 'UNKNOWN'
        try:
            age_type = Age(self.code).name
        except ValueError:
            pass # Keep 'UNKNOWN' if code not in enum
        return f"AgeMeasurement({float(self)}, code={self.code} [{age_type}])"

    def __eq__(self, other):
        """
        Equality comparison.

        Compares both value and code for AgeMeasurement instances,
        or value alone when comparing to a number.

        Args:
            other (AgeMeasurement|float|int): Object to compare.

        Returns:
            bool: True if equal.
        """
        if isinstance(other, AgeMeasurement):
            # *** Crucial: Compare both value and code ***
            return float(self) == float(other) and self.code == other.code
        elif isinstance(other, (float, int)):
            # Comparison with plain number only checks value
            return float(self) == float(other)
        return NotImplemented

    def __ne__(self, other):
        equal = self.__eq__(other)
        return NotImplemented if equal is NotImplemented else not equal
