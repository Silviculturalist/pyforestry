import pytest

from pyforestry.base.helpers.primitives.area_aggregates import (
    StandBasalArea,
    StandVolume,
    Stems,
)
from pyforestry.base.helpers.tree_species import parse_tree_species


def test_standvolume_creation_and_repr():
    sp = parse_tree_species("picea abies")
    vol = StandVolume(120.5, species=sp, precision=1.2, over_bark=False, fn=len)
    assert vol.value == 120.5
    assert vol.species == sp
    assert not vol.over_bark
    assert "StandVolume" in repr(vol)
    assert "len" in repr(vol)


@pytest.mark.parametrize("cls,value", [(StandVolume, -1), (StandBasalArea, -2), (Stems, -3)])
def test_negative_values_raise(cls, value):
    with pytest.raises(ValueError):
        cls(value)
