import pytest

from pyforestry.base.timber.timber_base import Timber, TimberVolumeIntegrator


class DummyTaper:
    """Simple taper object providing diameters."""

    def __init__(self, diameter):
        self._diameter = diameter

    def get_diameter_at_height(self, height_m: float):
        return self._diameter


def test_validate_height_positive():
    # Regression: the message used a plain (non-f) string, so it emitted the literal
    # "{self.height_m}" instead of the value. It must interpolate the actual height.
    with pytest.raises(ValueError) as exc:
        Timber(species="pine", diameter_cm=10, height_m=0)
    msg = str(exc.value)
    assert "Height must be larger than 0 m: 0" in msg
    assert "{self.height_m}" not in msg


def test_validate_diameter_non_negative():
    # Same non-f-string bug on the diameter message.
    with pytest.raises(ValueError) as exc:
        Timber(species="pine", diameter_cm=-1, height_m=10)
    msg = str(exc.value)
    assert "Diameter must be larger than or equal to 0 cm: -1" in msg
    assert "{self.diameter_cm}" not in msg


def test_validate_crown_base_below_height():
    pattern = r"Crown base height \(5 m\) cannot be higher than tree height: 4 m"
    with pytest.raises(ValueError, match=pattern):
        Timber(
            species="pine",
            diameter_cm=10,
            height_m=4,
            crown_base_height_m=5,
        )


def test_validate_stump_height_non_negative():
    with pytest.raises(ValueError, match="Stump height must be larger or equal to 0 m: -0.1"):
        Timber(species="pine", diameter_cm=10, height_m=10, stump_height_m=-0.1)


def test_cylinder_volume_integrand_none():
    taper = DummyTaper(None)
    area = TimberVolumeIntegrator.cylinder_volume_integrand(1.0, taper)
    assert area == 0.0


def test_cylinder_volume_integrand_area():
    taper = DummyTaper(10.0)
    area = TimberVolumeIntegrator.cylinder_volume_integrand(1.0, taper)
    expected = pytest.approx(3.141592653589793 * (0.05**2))
    assert area == expected


def test_integrate_volume_invalid_range():
    taper = DummyTaper(10.0)
    assert TimberVolumeIntegrator.integrate_volume(5.0, 2.0, taper) == 0.0


def test_integrate_volume_constant_diameter():
    taper = DummyTaper(10.0)
    vol = TimberVolumeIntegrator.integrate_volume(0.0, 10.0, taper)
    expected = pytest.approx(3.141592653589793 * (0.05**2) * 10.0)
    assert vol == expected
