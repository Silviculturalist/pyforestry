from typing import Union

import pytest

# It's clearer to import both classes for the tests
from pyforestry.base.helpers.primitives import AtomicVolume, CompositeVolume

# A type hint for scalars
Numeric = Union[int, float]

# --- Test AtomicVolume ---


def test_atomic_volume_equality_across_metadata():
    """
    Tests that two AtomicVolumes are equal (==) if their value is the same,
    even if their region or other metadata differs.
    This assumes you have implemented a custom __eq__ method.
    """
    # Assuming __eq__ is implemented to compare v.value
    assert AtomicVolume(value=1.0, region="Sweden") == AtomicVolume(value=1.0, region="Norway")
    assert AtomicVolume(value=10.0, species="picea abies") == AtomicVolume(
        value=10.0, species="pinus sylvestris"
    )


def test_atomic_volume_unit_conversions():
    """Tests the factory methods and the .to() conversion."""
    # Using the .from_unit() and .to() methods for clarity
    assert AtomicVolume.from_unit(1000, "dm3").value == 1.0  # 1000 dm³ = 1 m³
    assert AtomicVolume.from_unit(10, "m3").to("dm3") == 10000
    assert AtomicVolume.from_unit(1e6, "cm3").value == 1.0


def test_atomic_volume_repr():
    """Tests the string representation of an AtomicVolume."""
    # The __repr__ uses the actual class name 'AtomicVolume' and formats to 2 decimal places
    vol = AtomicVolume(value=12.345, region="Sweden", species="picea abies", type="m3sk")
    expected_repr = "AtomicVolume(12.35 m3, type='m3sk', species='picea abies', region='Sweden')"
    assert repr(vol) == expected_repr


# --- Test CompositeVolume and Interactions ---


def test_addition_of_compatible_atomic_volumes():
    """
    Tests that adding two compatible AtomicVolumes (same type, region, species)
    results in a single, summed AtomicVolume.
    """
    v1 = AtomicVolume(value=10, region="Sweden", species="picea abies", type="m3sk")
    v2 = AtomicVolume(value=5, region="Sweden", species="picea abies", type="m3sk")
    result = v1 + v2

    # The result should be another AtomicVolume
    assert isinstance(result, AtomicVolume)
    assert result.value == 15
    assert result.region == "Sweden"
    assert result.species == "picea abies"


def test_addition_of_incompatible_atomic_volumes_creates_composite():
    """
    Tests that adding two incompatible AtomicVolumes (e.g., different regions)
    correctly creates a CompositeVolume that preserves the original data.
    """
    v_sweden = AtomicVolume(value=10, region="Sweden", species="picea abies", type="m3sk")
    v_norway = AtomicVolume(value=5, region="Norway", species="picea abies", type="m3sk")

    result = v_sweden + v_norway

    # 1. The result must be a CompositeVolume
    assert isinstance(result, CompositeVolume)

    # 2. The total value should be the sum
    assert result.value == 15.0

    # 3. The underlying metadata should be preserved
    assert result.regions == {"Sweden", "Norway"}
    assert result.species_composition == {"picea abies": 15.0}
    assert len(result) == 2  # It contains two distinct components


def test_composite_volume_repr():
    """Tests the string representation of a CompositeVolume."""
    v1 = AtomicVolume(10, region="Sweden", type="m3sk")
    v2 = AtomicVolume(5, region="Norway", type="m3sk")
    composite = v1 + v2

    expected_repr = "CompositeVolume(total=15.00 m3, type='m3sk', components=2)"
    assert repr(composite) == expected_repr


def test_addition_with_incompatible_types_raises_value_error():
    """
    Tests that creating a CompositeVolume from AtomicVolumes with different `type`
    (e.g., 'm3sk' vs 'm3to') raises a ValueError.
    """
    v_m3sk = AtomicVolume(value=1, type="m3sk")
    v_m3to = AtomicVolume(value=1, type="m3to")  # A different, hypothetical type

    with pytest.raises(ValueError) as exc_info:
        # The error is raised when the CompositeVolume is created inside the __add__ method
        v_m3sk + v_m3to

    # Check that the error message from CompositeVolume.__init__ is correct
    assert str(exc_info.value) == "All volumes in a composite must have the same 'type'."


def test_atomic_volume_negative_value_error():
    """AtomicVolume should reject negative values."""

    with pytest.raises(ValueError):
        AtomicVolume(value=-1)


def test_atomic_volume_invalid_region_for_type():
    """A region not allowed for the volume type should raise an error."""

    with pytest.raises(ValueError):
        AtomicVolume(value=1, region="Germany", type="m3sk")


def test_atomic_volume_math_operations():
    """Multiplication and division helpers return new scaled volumes."""

    v = AtomicVolume(value=10, region="Sweden", type="m3sk")
    assert (v * 2).value == 20
    assert (2 * v).value == 20
    assert (v / 2).value == 5


def test_composite_volume_scalar_multiplication():
    """CompositeVolume should scale all components by a scalar."""

    v1 = AtomicVolume(10, region="Sweden", type="m3sk")
    v2 = AtomicVolume(5, region="Sweden", type="m3sk")
    comp = CompositeVolume([v1, v2])

    scaled = comp * 2
    assert isinstance(scaled, CompositeVolume)
    assert scaled.value == 30

    scaled_rmul = 2 * comp
    assert scaled_rmul.value == 30


def test_atomic_volume_divide_by_zero():
    """Division by zero should raise ``ZeroDivisionError``."""

    with pytest.raises(ZeroDivisionError):
        AtomicVolume(value=10) / 0


def test_atomic_volume_from_unit_invalid_unit():
    """Unknown units should raise ``ValueError``."""

    with pytest.raises(ValueError):
        AtomicVolume.from_unit(1, "unknown")


def test_atomic_volume_invalid_operand_add():
    """Adding a non-volume via ``__add__`` returns ``NotImplemented``."""

    assert AtomicVolume.__add__(AtomicVolume(1), 1) is NotImplemented


def test_atomic_volume_invalid_scalar_mul():
    """Non-numeric multiplication should return ``NotImplemented``."""

    assert AtomicVolume.__mul__(AtomicVolume(1), "a") is NotImplemented


def test_composite_volume_addition_cases():
    """CompositeVolume should handle adding volumes and other composites."""

    v1 = AtomicVolume(1)
    v2 = AtomicVolume(2)
    v3 = AtomicVolume(3)
    comp = CompositeVolume([v1, v2])

    new_comp = comp + v3
    assert isinstance(new_comp, CompositeVolume)
    assert new_comp.value == 6
    assert len(new_comp) == 1

    comp2 = CompositeVolume([v3])
    merged = comp + comp2
    assert isinstance(merged, CompositeVolume)
    assert merged.value == 6
    assert len(merged) == 1
