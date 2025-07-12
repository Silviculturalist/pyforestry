from typing import Optional
from pyforestry.helpers.tree_species import TreeName

class StandBasalArea(float):
    """
    Represents basal area (m²/ha) for one or more species.

    Attributes:
    -----------
    species : TreeName | list[TreeName]
        The species (or list of species) to which this basal area applies.
    precision : float
        Standard deviation, standard error, or other measure of precision (if known).
    over_bark : bool
        True if the basal area is measured over bark.
    direct_estimate : bool
        True if this is a direct field estimate (e.g. from Bitterlich sampling).
    """

    __slots__ = ('species','precision','over_bark','direct_estimate')


    def __new__(cls,
                value: float,
                species: Optional[TreeName] = None,
                precision: float = 0.0,
                over_bark: bool = True,
                direct_estimate: bool = True):
        if value < 0:
            raise ValueError("StandBasalArea must be non-negative.")
        obj = float.__new__(cls, value)
        obj.species = species
        obj.precision = precision
        obj.over_bark = over_bark
        obj.direct_estimate = direct_estimate
        return obj
    
    @property
    def value(self) -> float:
        return float(self)

    def __repr__(self):
        return (f"StandBasalArea({float(self):.3f} m^2/ha, species={self.species}, "
                f"precision={self.precision}, over_bark={self.over_bark}, "
                f"direct_estimate={self.direct_estimate})")


class StandVolume(float):
    """
    Represents a volume (m³/ha, typically) of standing trees in a stand,
    optionally for a single species or multiple species.

    Attributes:
    -----------
    species : TreeName | list[TreeName]
        The species or list of species for which the volume is estimated.
    precision : float
        Standard deviation or other measure of precision (if known).
    over_bark : bool
        True if the volume is measured over bark.
    fn : callable | None
        An optional reference to the function or model used to derive the volume.
    """
    __slots__=('species','precision','over_bark','fn')
    def __new__(cls,
                value: float,
                species: Optional[TreeName] = None,
                precision: float = 0.0,
                over_bark: bool = True,
                fn=None):
        if value < 0:
            raise ValueError("StandVolume must be non-negative.")
        obj = float.__new__(cls, value)
        obj.species = species
        obj.precision = precision
        obj.over_bark = over_bark
        obj.fn = fn
        return obj
    
    @property
    def value(self) -> float:
        return float(self)

    def __repr__(self):
        f_str = self.fn.__name__ if callable(self.fn) else self.fn
        return (f"StandVolume({float(self):.3f} m^3/ha, species={self.species}, "
                f"precision={self.precision}, over_bark={self.over_bark}, fn={f_str})")


class Stems(float):
    """
    Represents the number of stems per hectare (stems/ha) for one or more species.

    Attributes:
    -----------
    species : TreeName | list[TreeName]
        The species (or list of species) to which this stems count applies.
    precision : float
        Standard deviation or similar measure of precision (if known).
    """
    __slots__=('species','precision')
    def __new__(cls,
                value: float,
                species: Optional[TreeName] = None,
                precision: float = 0.0):
        if value < 0:
            raise ValueError("Stems must be non-negative.")
        obj = float.__new__(cls, value)
        obj.species = species
        obj.precision = precision
        return obj

    @property
    def value(self) -> float:
        return float(self)
    
    def __repr__(self):
        return (f"Stems({float(self):.1f} stems/ha, species={self.species}, "
                f"precision={self.precision})")
