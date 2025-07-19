from typing import List, Union

from pyforestry.base.helpers.tree_species import TreeName


class TopHeightDefinition:
    """
    Defines how the 'top height' (dominant height) is conceptually measured in a stand:
    - nominal_n: number of top trees in 1.0 hectare to average
    - nominal_area_ha: the area basis for that count
    """

    def __init__(self, nominal_n: int = 100, nominal_area_ha: float = 1.0):
        self.nominal_n = nominal_n
        self.nominal_area_ha = nominal_area_ha

    def __repr__(self):
        return f"TopHeightDefinition(nominal_n={self.nominal_n}, area_ha={self.nominal_area_ha})"


class TopHeightMeasurement(float):
    """
    A float-like class that stores the measured top (dominant) height of a stand.

    Attributes:
    -----------
    definition : TopHeightDefinition
        The definition used to identify the top height (e.g. top 100 trees per ha).
    species : TreeName | list[TreeName]
        The species or species mixture that this top height applies to.
    precision : float
        An estimate of precision (e.g. standard error) of the top height.
    est_bias : float
        Any known or estimated bias that might be subtracted (or added) from the measurement.
    """

    __slots__ = ("definition", "species", "precision", "est_bias")

    def __new__(
        cls,
        value: float,
        definition: TopHeightDefinition,
        species: Union[TreeName, List[TreeName], None] = None,
        precision: float = 0.0,
        est_bias: float = 0.0,
    ):
        if value < 0:
            raise ValueError("TopHeightMeasurement cannot be negative.")
        obj = float.__new__(cls, value)
        obj.definition = definition
        obj.species = species
        obj.precision = precision
        obj.est_bias = est_bias
        return obj

    @property
    def value(self) -> float:
        return float(self)

    def __repr__(self):
        return (
            f"TopHeightMeasurement({float(self):.2f} m, definition={self.definition}, "
            f"species={self.species}, precision={self.precision}, est_bias={self.est_bias})"
        )
