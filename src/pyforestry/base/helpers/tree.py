"""Classes for representing individual and aggregated tree records."""

from typing import Optional, Union

from .primitives import Age, Diameter_cm, Position
from .tree_species import TreeName, parse_tree_species


class Tree:
    """
    Base class for all tree objects. You can expand this to include common fields/methods
    that should exist on any type of tree.
    """

    pass


class SingleTree(Tree):
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
    """

    def __init__(
        self,
        position: Optional[Union[Position, tuple, None]] = None,
        species: Optional[Union[TreeName, str]] = None,
        age: Optional[Union[Age, float]] = None,
        diameter_cm: Optional[Union[Diameter_cm, float]] = None,
        height_m: Optional[float] = None,
        uid: Optional[Union[int, str]] = None,
    ):
        """Create a SingleTree instance with optional attributes.

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

    def __repr__(self):
        """Return ``repr(self)`` including main attribute values."""
        return (
            f"SingleTree(species={self.species!r}, age={self.age}, "
            f"diameter_cm={self.diameter_cm}, height_m={self.height_m}, "
            f"position={self.position}, uid={self.uid})"
        )


class RepresentationTree(Tree):
    """
    A "multiplicity" tree, i.e. a single record that represents multiple identical trees
    on a plot (spatially implicit or partially explicit).

    Attributes:
    -----------
    position : Position | tuple[float,float] | tuple[float,float,float] | None
        Location if relevant (often None or the plot center).
    species : TreeName | str | None
        Species of the tree(s).
    age : Age | float | None
        Age of the tree(s).
    diameter_cm : Diameter_cm | float | None
        Diameter of the tree(s).
    height_m : float | None
        Height of the tree(s).
    weight : float
        Number of stems represented by this single record (e.g. 1, or 5).
    """

    def __init__(
        self,
        position: Optional[Union[Position, tuple, None]] = None,
        species: Optional[Union[TreeName, str]] = None,
        age: Optional[Union[Age, float]] = None,
        diameter_cm: Optional[Union[Diameter_cm, float]] = None,
        height_m: Optional[float] = None,
        weight: float = 1.0,
        uid: Optional[Union[int, str]] = None,
    ):
        """Create a record that represents multiple identical trees.

        Parameters
        ----------
        position : Position | tuple | None, optional
            Location for the group of trees.
        species : TreeName | str | None, optional
            Species identifier for the trees.
        age : Age | float | None, optional
            Age value shared by all trees.
        diameter_cm : Diameter_cm | float | None, optional
            Diameter at breast height in centimetres.
        height_m : float | None, optional
            Height in metres for the trees.
        weight : float, optional
            Number of stems this record represents. Defaults to ``1.0``.
        uid : int | str | None, optional
            Optional unique identifier for the record.
        """
        self.position = Position._set_position(position)

        if isinstance(species, str):
            self.species = parse_tree_species(species)
        else:
            self.species = species

        self.age = age
        self.diameter_cm = diameter_cm
        self.height_m = height_m
        self.weight = weight
        self.uid = uid

    def __repr__(self):
        """Return ``repr(self)`` summarizing key attribute values."""
        return (
            f"RepresentationTree(species={self.species}, age={self.age}, "
            f"diameter_cm={self.diameter_cm}, height_m={self.height_m}, "
            f"weight={self.weight}, uid={self.uid})"
        )
