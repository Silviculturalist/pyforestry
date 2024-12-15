# Tree species Coniferous or Broadleaf helper
import re #regex
import warnings


def get_tree_type(species):
    """
    Determines if a tree species is deciduous or coniferous.

    Parameters:
    species (str): The Latin name of the species (e.g., "Picea abies").

    Returns:
    str: "Deciduous", "Coniferous", or None (with a warning).
    """

        # Static lists of known genera
    DECIDUOUS_LIST = [
        "Betula", "Alnus", "Populus", "Sorbus", "Salix", "Ulmus",
        "Fraxinus", "Carpinus", "Quercus", "Tilia", "Fagus",
        "Prunus", "Acer", "Robinia", "Corylus", "Aesculus"
    ]
    CONIFEROUS_LIST = [
        "Abies", "Picea", "Larix", "Pseudotsuga", "Tsuga", "Pinus",
        "Seqouia", "Sequoiadendron", "Chamaecyparis", "Cupressaceae",
        "Juniperus", "Thuja", "Taxus", "Cedrus", "Cathaya",
        "Pseudolarix", "Keteleeria", "Nothotsuga"
    ]
    # Extract the genus name (assumes the first part of the name)
    genus_match = re.match(r"^[A-Z][a-z]*", species)
    if not genus_match:
        warnings.warn("Did you remember to capitalize the genus name?")
        return None

    genus = genus_match.group(0)

    # Check against coniferous and deciduous lists
    if genus in CONIFEROUS_LIST:
        return "Coniferous"
    elif genus in DECIDUOUS_LIST:
        return "Deciduous"
    else:
        warnings.warn("Unknown species.")
        return None

# Examples
#print(get_tree_type("Picea abies"))  # Outputs: "Coniferous"
#print(get_tree_type("Pisum sativum"))  # Warns and outputs: None
#print(get_tree_type("Betula pendula"))  # Outputs: "Deciduous"
#print(get_tree_type("UnknownSpecies"))  # Warns and outputs: None
