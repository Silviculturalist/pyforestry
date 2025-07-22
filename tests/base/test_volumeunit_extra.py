import pytest

from pyforestry.base.helpers.primitives import AtomicVolume, CompositeVolume


def test_scalar_operations():
    vol = AtomicVolume(2.0)
    assert (vol * 3).value == 6
    assert (3 * vol).value == 6
    assert (vol / 2).value == 1


def test_error_paths_and_validation():
    with pytest.raises(ValueError):
        AtomicVolume(-1)
    with pytest.raises(ValueError):
        AtomicVolume(1, region="USA", type="m3sk")  # invalid region for type
    with pytest.raises(ValueError):
        AtomicVolume.from_unit(1, "unknown")
    vol = AtomicVolume(1)
    with pytest.raises(ZeroDivisionError):
        vol / 0
    with pytest.raises(TypeError):
        vol + 1


def test_composite_len_and_repr():
    c = CompositeVolume([AtomicVolume(1), AtomicVolume(2)])
    # identical volumes merge to a single component
    assert len(c) == 1
    # Ensure __repr__ contains useful information
    out = repr(c)
    assert "CompositeVolume(total=3.00" in out
