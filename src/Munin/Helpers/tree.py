# ------------------------------------------------------------------------------
# Tree classes
# ------------------------------------------------------------------------------
from typing import Optional, Union
from Munin.helpers.tree_species import TreeName, parse_tree_species
from Munin.helpers.primitives import Position, Diameter_cm, Age 

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
    def __init__(self,
                 position: Optional[Union[Position, tuple, None]] = None,
                 species: Optional[Union[TreeName, str]] = None,
                 age: Optional[Union[Age, float]] = None,
                 diameter_cm: Optional[Union[Diameter_cm, float]] = None,
                 height_m: Optional[float] = None):
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

    def __repr__(self):
        return (f"SingleTree(species={self.species}, age={self.age}, "
                f"diameter_cm={self.diameter_cm}, height_m={self.height_m}, "
                f"position={self.position})")


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
    def __init__(self,
                 position: Optional[Union[Position, tuple, None]] = None,
                 species: Optional[Union[TreeName, str]] = None,
                 age: Optional[Union[Age, float]] = None,
                 diameter_cm: Optional[Union[Diameter_cm, float]] = None,
                 height_m: Optional[float] = None,
                 weight: float = 1.0):
        self.position = Position._set_position(position)

        if isinstance(species, str):
            self.species = parse_tree_species(species)
        else:
            self.species = species

        self.age = age
        self.diameter_cm = diameter_cm
        self.height_m = height_m
        self.weight = weight

    def __repr__(self):
        return (f"RepresentationTree(species={self.species}, age={self.age}, "
                f"diameter_cm={self.diameter_cm}, height_m={self.height_m}, weight={self.weight})")
