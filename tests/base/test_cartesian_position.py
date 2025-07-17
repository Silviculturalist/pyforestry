import math

import pytest

from pyforestry.base.helpers.primitives.cartesian_position import Position


def test_from_polar_and_repr():
    pos = Position.from_polar(1.0, math.pi / 2)
    assert pytest.approx(pos.X, rel=1e-6) == 0.0
    assert pytest.approx(pos.Y, rel=1e-6) == 1.0
    assert pos.Z == 0.0
    assert pos.crs is None
    assert repr(pos) == f"Position(X={pos.X}, Y={pos.Y}, Z={pos.Z}, crs={pos.crs})"


def test_set_position_variants():
    pos = Position(1, 2, 3)
    assert Position._set_position(pos) is pos
    assert Position._set_position(None) is None

    pos_xy = Position._set_position((4, 5))
    assert isinstance(pos_xy, Position)
    assert pos_xy.X == 4 and pos_xy.Y == 5 and pos_xy.Z == 0.0

    pos_xyz = Position._set_position((6, 7, 8))
    assert pos_xyz.Z == 8

    with pytest.raises(ValueError):
        Position._set_position((1, 2, 3, 4))
    with pytest.raises(TypeError):
        Position._set_position([1, 2])
