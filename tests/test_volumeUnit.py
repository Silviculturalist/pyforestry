import pytest
from Munin.Helpers.Base import Volume

# Test equality of volumes with different units and regions
def test_volume_equality():
    assert Volume.Sweden.dm3sk(1000) == Volume.Norway.m3sk(1)  # 1000 dm³ = 1 m³
    assert Volume.Sweden.m3sk(10) == Volume.Finland.dm3sk(10000)  # 10 m³ = 10000 dm³
    assert Volume.Sweden.km3sk(0.00000001) == Volume.Norway.m3sk(10)  # 0.00000001 km³ = 10 m³
    assert Volume.Sweden.Pm3sk(1).m3() == 1e45  # 1 Pm³ = 1e45 m³
    assert Volume.Sweden.cm3sk(1e6) == Volume.Norway.m3sk(1)  # 1e6 cm³ = 1 m³
    assert Volume.Sweden.mm3sk(1e9) == Volume.Finland.m3sk(1)  # 1e9 mm³ = 1 m³

# Test addition operation with same type, different regions
def test_volume_addition():
    v1 = Volume.Sweden.m3sk(1)
    v2 = Volume.Norway.m3sk(1)
    result = v1 + v2
    assert result == Volume.Sweden.m3sk(2)  # 1 m³ + 1 m³ = 2 m³
    assert str(result) == "Volume(2.0000 m3, region='Sweden', species='unknown', type='m3sk')"

# Test that operations with different types raise ValueError
def test_volume_incompatible_types():
    v1 = Volume.Sweden.m3sk(1)
    v3 = Volume.Sweden.m3to(1)
    with pytest.raises(ValueError) as exc_info:
        v1 + v3
    assert str(exc_info.value) == "Incompatible volume types: m3sk vs m3to"

# Test string representation of volumes
def test_volume_repr():
    assert str(Volume.Sweden.dm3sk(1000)) == "Volume(1.0000 m3, region='Sweden', species='unknown', type='m3sk')"
    assert str(Volume.Norway.m3sk(1)) == "Volume(1.0000 m3, region='Norway', species='unknown', type='m3sk')"
    assert str(Volume.Sweden.km3sk(0.00000001)) == "Volume(10.0000 m3, region='Sweden', species='unknown', type='m3sk')"
    assert str(Volume.Sweden.km3sk(-0.00000001)) == "Volume(-10.0000 m3, region='Sweden', species='unknown', type='m3sk')"
    assert str(Volume.Sweden.Pm3sk(1)) == "Volume(1.0000 Pm3, region='Sweden', species='unknown', type='m3sk')"

