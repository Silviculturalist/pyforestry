import pytest

from pyforestry.base.helpers.primitives.topheight import (
    TopHeightDefinition,
    TopHeightMeasurement,
)
from pyforestry.base.helpers.tree_species import parse_tree_species


def test_topheight_definition_repr():
    thd = TopHeightDefinition(nominal_n=150, nominal_area_ha=2.0)
    assert thd.nominal_n == 150
    assert thd.nominal_area_ha == 2.0
    assert repr(thd) == "TopHeightDefinition(nominal_n=150, area_ha=2.0)"


def test_topheight_measurement_creation_and_value():
    definition = TopHeightDefinition()
    species = parse_tree_species("picea abies")
    thm = TopHeightMeasurement(24.5, definition, species, precision=0.2, est_bias=0.1)
    assert float(thm) == 24.5
    assert thm.value == 24.5
    assert thm.definition is definition
    assert thm.species == species
    assert thm.precision == 0.2
    assert thm.est_bias == 0.1
    assert "TopHeightMeasurement(24.50 m" in repr(thm)


def test_topheight_measurement_negative_value():
    definition = TopHeightDefinition()
    with pytest.raises(ValueError):
        TopHeightMeasurement(-1.0, definition)
