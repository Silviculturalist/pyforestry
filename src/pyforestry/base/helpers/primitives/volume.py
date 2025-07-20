from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Set, Union

# A type hint for scalars
Numeric = Union[int, float]


@dataclass(frozen=True, eq=False)
class AtomicVolume:
    """
    Represents a single, indivisible volume measurement for a specific species and region.
    This is the fundamental building block.
    """

    value: float = field(metadata={"unit": "m3"})
    region: str = "Sweden"
    species: str = "unknown"
    type: str = "m3sk"

    # --- (Class constants and validation are the same as before) ---
    UNIT_CONVERSION: ClassVar[Dict[str, float]] = {"m3": 1.0, "dm3": 1e-3, "cm3": 1e-6}
    TYPE_REGIONS: ClassVar[Dict[str, List[str]]] = {"m3sk": ["Sweden", "Finland", "Norway"]}

    def __post_init__(self):
        if self.value < 0:
            raise ValueError("Volume value must be non-negative.")
        allowed_regions = self.TYPE_REGIONS.get(self.type)
        if allowed_regions and self.region not in allowed_regions:
            raise ValueError(f"Region '{self.region}' is not valid for type '{self.type}'.")

    # --- (Factory and conversion methods are the same) ---
    @classmethod
    def from_unit(cls, value: float, unit: str, **kwargs) -> AtomicVolume:
        if unit not in cls.UNIT_CONVERSION:
            raise ValueError(f"Unit '{unit}' not recognized.")
        return cls(value=(value * cls.UNIT_CONVERSION[unit]), **kwargs)

    def to(self, unit: str) -> float:
        return self.value / self.UNIT_CONVERSION[unit]

    # --- INTELLIGENT ADDITION ---
    def __add__(self, other: Any) -> Union[AtomicVolume, CompositeVolume]:
        """
        Handles addition.
        - If 'other' is compatible, merges into a new AtomicVolume.
        - If 'other' is incompatible, creates a CompositeVolume.
        """
        if not isinstance(other, AtomicVolume):
            return NotImplemented

        # Check for compatibility to merge
        is_compatible = (
            self.type == other.type
            and self.region == other.region
            and self.species == other.species
        )

        if is_compatible:
            # Merge into a new, larger AtomicVolume
            return AtomicVolume(self.value + other.value, self.region, self.species, self.type)
        else:
            # Incompatible: form a CompositeVolume
            return CompositeVolume([self, other])

    # --- (Multiplication/Division are the same) ---
    def __mul__(self, scalar: Numeric) -> AtomicVolume:
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return AtomicVolume(self.value * scalar, self.region, self.species, self.type)

    def __rmul__(self, scalar: Numeric) -> AtomicVolume:
        return self.__mul__(scalar)

    def __truediv__(self, scalar: Numeric) -> AtomicVolume:
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        if scalar == 0:
            raise ZeroDivisionError("Cannot divide Volume by zero.")
        return AtomicVolume(self.value / scalar, self.region, self.species, self.type)

    def __repr__(self):
        return (
            f"AtomicVolume({self.value:.2f} m3, "
            f"type='{self.type!r}', "
            f"species='{self.species!r}', "
            f"region='{self.region!r}')"
        )

    # Inside the AtomicVolume class

    def __eq__(self, other: Any) -> bool:
        """
        Two volumes are considered equal if their absolute value is the same,
        regardless of their metadata (region, species, type).
        """
        if isinstance(other, (AtomicVolume, CompositeVolume)):
            # Compare based on the total numeric value
            return self.value == other.value
        return NotImplemented


class CompositeVolume:
    """
    Represents a collection of AtomicVolume objects.
    It preserves all underlying information while providing aggregate views.
    """

    def __init__(self, volumes: List[AtomicVolume]):
        if not all(isinstance(v, AtomicVolume) for v in volumes):
            raise TypeError("CompositeVolume can only contain AtomicVolume objects.")

        # Enforce that all volumes in a composite must be of the same 'type'
        first_type = volumes[0].type
        if not all(v.type == first_type for v in volumes):
            raise ValueError("All volumes in a composite must have the same 'type'.")

        self._volumes = self._simplify(volumes)

    def _simplify(self, volumes: List[AtomicVolume]) -> List[AtomicVolume]:
        """Internal helper to merge compatible volumes upon creation."""
        # This is an advanced optimization to keep the list minimal
        # For example, if adding [A, B] and [A, C], we want [2A, B, C]
        registry = defaultdict(float)
        for vol in volumes:
            # Create a unique key for compatible volumes
            key = (vol.type, vol.region, vol.species)
            registry[key] += vol.value

        # Reconstruct the minimal list of AtomicVolumes
        return [
            AtomicVolume(value, region, species, type)
            for (type, region, species), value in registry.items()
        ]

    @property
    def value(self) -> float:
        """The total summed value of all component volumes."""
        return sum(v.value for v in self._volumes)

    @property
    def type(self) -> str:
        """The shared type of all component volumes."""
        return self._volumes[0].type if self._volumes else "N/A"

    @property
    def regions(self) -> Set[str]:
        """A set of all unique regions represented in the composite."""
        return {v.region for v in self._volumes}

    @property
    def species_composition(self) -> Dict[str, float]:
        """
        Returns a dictionary detailing the total volume for each species.
        This directly answers your request to preserve component information.
        """
        composition = defaultdict(float)
        for v in self._volumes:
            composition[v.species] += v.value
        return dict(composition)

    def __add__(self, other: Any) -> CompositeVolume:
        if isinstance(other, AtomicVolume):
            return CompositeVolume(self._volumes + [other])
        elif isinstance(other, CompositeVolume):
            return CompositeVolume(self._volumes + other._volumes)
        return NotImplemented

    def __mul__(self, scalar: Numeric) -> CompositeVolume:
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        # Multiply each component volume individually
        return CompositeVolume([v * scalar for v in self._volumes])

    def __rmul__(self, scalar: Numeric) -> CompositeVolume:
        return self.__mul__(scalar)

    def __len__(self) -> int:
        return len(self._volumes)

    def __repr__(self) -> str:
        return (
            f"CompositeVolume(total={self.value:.2f} m3, "
            f"type='{self.type}', components={len(self)})"
        )
