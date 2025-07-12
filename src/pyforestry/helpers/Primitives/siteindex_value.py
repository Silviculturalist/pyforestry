# ------------------------------------------------------------------------------
# SiteIndexValue: float with metadata
# ------------------------------------------------------------------------------
from typing import Callable
from pyforestry.helpers.tree_species import TreeName
from pyforestry.helpers.primitives import AgeMeasurement 

class SiteIndexValue(float):

    __slots__=('reference_age','species','fn')
    def __new__(cls,
                value: float,
                reference_age: AgeMeasurement, # Expects AgeMeasurement
                species: set[TreeName], #Potentially more than one, e.g. Betula pendula, Betula pubescens.
                fn: Callable):

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
        fn_name = self.fn.__name__ if hasattr(self.fn, '__name__') else str(self.fn)
        # Represent the set of species clearly
        species_repr = "{" + ", ".join(sorted(repr(s) for s in self.species)) + "}" # Sort for consistent repr
        return (f"SiteIndexValue({float(self)}, reference_age={self.reference_age}, "
                f"species={species_repr}, fn={fn_name})") # Use the set repr
