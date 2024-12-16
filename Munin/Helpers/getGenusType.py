# Tree species Coniferous or Broadleaf helper
import re #regex
import warnings


def get_tree_type(species:str):
    """
    Determines if a tree species is deciduous or coniferous.

    Parameters:
    species (str): The Latin name of the species (e.g., "picea abies").

    Returns:
    str: "Deciduous", "Coniferous", or None (with a warning).
    """
    species = species.lower() #ensure all characters lower-case 

        # Static lists of known genera
    DECIDUOUS_LIST = [
        "betula", "alnus", "populus", "sorbus", "salix", "ulmus",
        "fraxinus", "carpinus", "quercus", "tilia", "fagus",
        "prunus", "acer", "robinia", "corylus", "aesculus"
    ]
    CONIFEROUS_LIST = [
        "abies", "picea", "larix", "pseudotsuga", "tsuga", "pinus",
        "seqouia", "sequoiadendron", "chamaecyparis", "cupressaceae",
        "juniperus", "thuja", "taxus", "cedrus", "cathaya",
        "pseudolarix", "keteleeria", "nothotsuga"
    ]

    # Extract the genus name (assumes the first part of the name)
    genus_match = re.match(r"^[a-z]+", species)
    if not genus_match:
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
