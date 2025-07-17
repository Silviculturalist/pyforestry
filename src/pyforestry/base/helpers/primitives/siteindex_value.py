"""Representation of site index values with metadata.

This module defines :class:`SiteIndexValue`, a lightweight class used to store
site index measurements along with key contextual information.  A site index is
commonly expressed as a height (in meters) for a given tree species at a
specified reference age and is often derived from empirical functions.  The
class in this module subclasses :class:`float` so that it behaves like a numeric
value while also carrying:

``reference_age``
    The :class:`~pyforestry.base.helpers.primitives.AgeMeasurement` the value
    refers to.
``species``
    A set of :class:`~pyforestry.base.helpers.tree_species.TreeName` objects for
    which the site index applies.
``fn``
    The callable that was used to compute the value, if applicable.

These additional attributes make it easier to keep track of how the site index
was produced when using it in analyses or passing it between functions.
"""

from typing import Callable
from pyforestry.base.helpers.tree_species import TreeName
from pyforestry.base.helpers.primitives import AgeMeasurement

class SiteIndexValue(float):
    """Site index value with associated metadata.

    This class stores a numeric site index while also tracking the reference
    age, species, and function used to derive the value.  It subclasses
    :class:`float` so it can be used directly in numeric operations.

    Attributes
    ----------
    reference_age : AgeMeasurement
        The age at which the site index is defined.
    species : set[TreeName]
        One or more tree species that the site index represents.
    fn : Callable
        The function that produced the value, allowing the computation to be
        traced back.
    """

    __slots__ = ("reference_age", "species", "fn")

    def __new__(
        cls,
        value: float,
        reference_age: AgeMeasurement,
        species: set[TreeName],
        fn: Callable,
    ):
        """Create a :class:`SiteIndexValue` instance.

        Parameters
        ----------
        value : float
            The numeric site index value; must be non-negative.
        reference_age : AgeMeasurement
            Age measurement object describing the reference age.
        species : set[TreeName]
            Set of species that the site index applies to. The set must not be
            empty and all items must be :class:`TreeName` instances.
        fn : Callable
            Callable that was used to compute ``value``.

        Returns
        -------
        SiteIndexValue
            The newly created instance.

        Raises
        ------
        TypeError
            If ``reference_age`` is not an :class:`AgeMeasurement` or if
            ``species`` is not a set of :class:`TreeName` objects.
        ValueError
            If ``value`` is negative or ``species`` is empty.
        """

        # Check type of reference_age
        if not isinstance(reference_age, AgeMeasurement):
            raise TypeError(f"reference_age must be an AgeMeasurement object, not {type(reference_age)}")
        
        # --- Validate the species set ---
        if not isinstance(species, set):
            raise TypeError(f"species must be a set, not {type(species)}")
        if not species: # Check if the set is empty
             raise ValueError("species set cannot be empty.")
        for item in species:
            if not isinstance(item, TreeName):
                raise TypeError(f"All items in the species set must be TreeName objects, found {type(item)}")

        if value < 0:
            raise ValueError("Site index value must be non-negative.")

        obj = super().__new__(cls, value)
        obj.reference_age = reference_age # Store the object
        obj.species = species
        obj.fn = fn
        return obj

    def __repr__(self):
        """Return ``repr(self)`` with metadata included."""
        fn_name = self.fn.__name__ if hasattr(self.fn, "__name__") else str(self.fn)
        # Represent the set of species clearly
        species_repr = "{" + ", ".join(sorted(repr(s) for s in self.species)) + "}"
        return (
            f"SiteIndexValue({float(self)}, reference_age={self.reference_age}, "
            f"species={species_repr}, fn={fn_name})"
        )
