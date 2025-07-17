import math

import pytest

from pyforestry.base.helpers.primitives.qmd import QuadraticMeanDiameter


def test_qmd_compute_from_valid():
    qmd = QuadraticMeanDiameter.compute_from(20, 500)
    expected = math.sqrt((40000 * 20) / (math.pi * 500))
    assert isinstance(qmd, QuadraticMeanDiameter)
    assert math.isclose(qmd.value, expected, rel_tol=1e-6)


def test_qmd_compute_from_invalid():
    with pytest.raises(ValueError):
        QuadraticMeanDiameter.compute_from(0, 100)
    with pytest.raises(ValueError):
        QuadraticMeanDiameter.compute_from(10, 0)


def test_qmd_repr_and_negative():
    qmd = QuadraticMeanDiameter(12.345, precision=0.5)
    assert repr(qmd) == "QuadraticMeanDiameter(12.35 cm, precision=0.50 cm)"
    with pytest.raises(ValueError):
        QuadraticMeanDiameter(-1)
