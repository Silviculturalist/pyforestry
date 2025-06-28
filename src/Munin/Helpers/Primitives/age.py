from enum import Enum

# --- Age Enum ---
class Age(Enum):
    TOTAL = 1
    DBH = 2

    def __call__(self, value: float) -> 'AgeMeasurement': # Use forward reference string
        return AgeMeasurement(value, self.value)

# --- AgeMeasurement Class ---
class AgeMeasurement(float):

    __slots__ = ('code')

    def __new__(cls, value: float, code: int):
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
        return float(self)

    def __repr__(self):
        # Ensure Age enum lookup is safe
        age_type = 'UNKNOWN'
        try:
            age_type = Age(self.code).name
        except ValueError:
            pass # Keep 'UNKNOWN' if code not in enum
        return f"AgeMeasurement({float(self)}, code={self.code} [{age_type}])"

    def __eq__(self, other):
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
