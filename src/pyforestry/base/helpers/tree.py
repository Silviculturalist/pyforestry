"""Classes for representing individual and aggregated tree records."""

from typing import Optional, Union

from .primitives import Age, Diameter_cm, Position
from .tree_species import TreeName, parse_tree_species


class Tree:
    """
    A spatially explicit single tree: (x, y, [z]) in a coordinate system + attributes.

    Attributes:
    -----------
    position : Position | tuple[float,float] | tuple[float,float,float] | None
        The location of the tree in some coordinate system.
    species : TreeName | str | None
        The species of the tree (or a string name to be parsed).
    age : Age | float | None
        The age of the tree. If an Age enum is used, it wraps the value in AgeMeasurement.
    diameter_cm : Diameter_cm | float | None
        The diameter (cm) if known. If a float is passed, it can be coerced to a Diameter_cm.
    height_m : float | None
        The *measured* height (m) of the tree if known. This is authoritative and
        is never overwritten by a modelled/interpolated value.
    predicted_height_m : float | None
        An *interpolated* height (m) assigned from a height-diameter curve (e.g.
        via ``Stand.impute_heights``). Kept separate from ``height_m`` so a
        modelled height is never mistaken for a measurement.
    weight_n : float
        Number of trees represented by Tree object. Defaults to 1.0.
    is_overstorey : bool | None
        Optional flag indicating overstorey status. If None, overstorey
        classification is left to downstream models.
    mortality : float | None
        Optional mortality fraction (0-1) applied to the tree record.
    crown_radius_m : float | None
        Optional horizontal crown (or influence-zone) radius in metres. Used by
        the influence-zone overlap competition indices; see
        :mod:`pyforestry.base.competition`. Left ``None`` unless measured or
        supplied by a crown model.
    uid : int | None
        A unique identifier for the Tree object.
    """

    def __init__(
        self,
        position: Optional[Union[Position, tuple, None]] = None,
        species: Optional[Union[TreeName, str]] = None,
        age: Optional[Union[Age, float]] = None,
        diameter_cm: Optional[Union[Diameter_cm, float]] = None,
        height_m: Optional[float] = None,
        weight_n: Optional[float] = 1.0,
        is_overstorey: Optional[bool] = None,
        mortality: Optional[float] = None,
        uid: Optional[Union[int, str]] = None,
        predicted_height_m: Optional[float] = None,
        crown_radius_m: Optional[float] = None,
    ):
        """Create a Tree instance with optional attributes.

        Parameters
        ----------
        position : Position | tuple | None, optional
            Tree location in a coordinate system.
        species : TreeName | str | None, optional
            Species identifier or name string.
        age : Age | float | None, optional
            Age value or ``Age`` enumeration.
        diameter_cm : Diameter_cm | float | None, optional
            Diameter at breast height in centimetres.
        height_m : float | None, optional
            Tree height in metres.
        weight_n : float
            Number of trees represented by Tree object. Defaults to 1.0.
        is_overstorey : bool | None, optional
            Optional flag indicating overstorey status.
        mortality : float | None, optional
            Optional mortality fraction (0-1) for this tree record.
        uid : int | str | None, optional
            Optional unique identifier for the tree.
        predicted_height_m : float | None, optional
            Optional interpolated height (m) from a height-diameter curve.
        crown_radius_m : float | None, optional
            Optional crown/influence-zone radius (m) for the influence-zone
            competition indices.
        """
        self.position = Position._set_position(position)

        # Convert string species → TreeSpecies if parseable
        if isinstance(species, str):
            self.species = parse_tree_species(species)
        else:
            self.species = species

        # If `age` is e.g. float or Age, store as is (for more advanced usage,
        # you might unify to an AgeMeasurement).
        self.age = age

        # If `diameter_cm` is a float, you could coerce to a default Diameter_cm( ... )
        # or just store as float. For now, store as given:
        self.diameter_cm = diameter_cm
        self.height_m = height_m
        self.predicted_height_m = predicted_height_m
        self.uid = uid
        self.weight_n = weight_n
        self.is_overstorey = is_overstorey
        self.mortality = mortality
        self.crown_radius_m = crown_radius_m

    @property
    def height_provenance(self) -> Optional[str]:
        """Return ``"measured"``, ``"predicted"`` or ``None`` for the height.

        A measured height (``height_m``) always takes precedence over an
        interpolated one (``predicted_height_m``).
        """
        if self.height_m is not None:
            return "measured"
        if self.predicted_height_m is not None:
            return "predicted"
        return None

    def effective_height_m(self, prefer: str = "measured") -> Optional[float]:
        """Return a usable height, choosing between measured and predicted.

        Parameters
        ----------
        prefer:
            ``"measured"`` (default) returns the measurement, falling back to the
            predicted height; ``"predicted"`` returns the interpolated height,
            falling back to the measurement; ``"measured_only"`` /
            ``"predicted_only"`` return just that source (or ``None``).
        """
        measured = self.height_m
        predicted = self.predicted_height_m
        if prefer == "measured":
            return measured if measured is not None else predicted
        if prefer == "predicted":
            return predicted if predicted is not None else measured
        if prefer == "measured_only":
            return measured
        if prefer == "predicted_only":
            return predicted
        raise ValueError(f"Unknown prefer={prefer!r}")

    def __repr__(self):
        """Return ``repr(self)`` including main attribute values."""
        return (
            f"Tree(species={self.species!r}, age={self.age}, "
            f"diameter_cm={self.diameter_cm}, height_m={self.height_m}, "
            f"predicted_height_m={self.predicted_height_m}, "
            f"position={self.position}, weight_n={self.weight_n}, "
            f"is_overstorey={self.is_overstorey}, mortality={self.mortality}, "
            f"uid={self.uid})"
        )
