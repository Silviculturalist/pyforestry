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
        The height (m) of the tree if known.
    weight_n : float
        Number of trees represented by Tree object. Defaults to 1.0.
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
        uid: Optional[Union[int, str]] = None,
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
        uid : int | str | None, optional
            Optional unique identifier for the tree.
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
        self.uid = uid
        self.weight_n = weight_n

    def __repr__(self):
        """Return ``repr(self)`` including main attribute values."""
        return (
            f"Tree(species={self.species!r}, age={self.age}, "
            f"diameter_cm={self.diameter_cm}, height_m={self.height_m}, "
            f"position={self.position}, weight_n={self.weight_n}"
            f"uid={self.uid})"
        )
