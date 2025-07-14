# codefolder/MaximumAnnualIncrement.py (Modification)
from pyforestry.base.helpers.primitives import SiteIndexValue
from pyforestry.base.helpers.tree_species import TreeSpecies, TreeName
from pyforestry.sweden.site.swedish_site import Sweden

def hagglund_1981_SI_to_productivity(
    h100_input: SiteIndexValue,
    main_species: TreeName,
    vegetation: Sweden.FieldLayer,
    altitude: float,
    county: Sweden.County # Changed type hint to the Enum
) -> float:
    """
    Calculate smoothed productivity estimates in m3sk (cu.m.) from Hägglund 1981.

    Parameters:
        h100_input (SiteIndexValue): Estimated stand top height object (must be H100, i.e., reference_age value must be 100).
        main_species (TreeName): Main species (e.g., TreeSpecies.Sweden.picea_abies).
        vegetation (Sweden.FieldLayer): Vegetation enum member.
        altitude (float): Altitude in meters above sea level.
        county (Sweden.County): Swedish county enum member.

    Returns:
        float: Mean volume growth in m3sk / ha yr-1 at the time of culmination.

    Raises:
        ValueError: If h100_input.reference_age value is not 100, or if H100 value is not positive.
        TypeError: If input types are incorrect.
    """

    # Define sets of county codes for easier checking
    NORTHERN_COUNTY_CODES = {
        Sweden.County.NORRBOTTENS_LAPPMARK,
        Sweden.County.NORRBOTTENS_KUSTLAND,
        Sweden.County.VASTERBOTTENS_LAPPMARK,
        Sweden.County.VASTERBOTTENS_KUSTLAND,
        Sweden.County.VASTERNORRLAND_ANGERMANLANDS,
        Sweden.County.VASTERNORRLAND_MEDELPADS,
        Sweden.County.JAMTLAND_JAMTLANDS,
        Sweden.County.JAMTLAND_HARJEDALENS,
        Sweden.County.KOPPARBERG_SALEN_IDRE
    }

    MIDDLE_COUNTY_CODES = {
        Sweden.County.KOPPARBERG_OVRIGA,
        Sweden.County.GAVLEBORG_HALSINGLANDS,
        Sweden.County.GAVLEBORG_OVRIGA,
        Sweden.County.VARMLAND    
    }

    # Validate inputs
    # Check if the numeric value of the reference_age is 100
    if h100_input.reference_age != 100:
         # Raise ValueError instead of warning
         raise ValueError(f"Input SiteIndexValue must have a reference_age value of 100 (H100). Received: {h100_input.reference_age}") #

    H100 = float(h100_input) # Extract the float value for calculations
    if H100 <= 0:
        raise ValueError("H100 value must be positive.") #

    if not isinstance(main_species, TreeName):
         raise TypeError("main_species must be a TreeName object.") #

    if not isinstance(vegetation, Sweden.FieldLayer):
        raise TypeError("vegetation must be a Sweden.FieldLayer enum member.") #

    if not isinstance(county, Sweden.County):
        raise TypeError("county must be a Sweden.County enum member.") #

    # --- rest of the function remains the same ---
    veg_code = vegetation.value.code
    county_code = county.value.code # Get the integer code from the enum

    F1 = 0.72 + (H100 / 130)
    F2 = 0.70 + (H100 / 100)
    fun = None

    # Determine function based on species, county code, vegetation code, and altitude
    if main_species == TreeSpecies.Sweden.picea_abies:
        if county_code in NORTHERN_COUNTY_CODES:
            fun = "d" if veg_code <= 9 else "e"
        elif county_code in MIDDLE_COUNTY_CODES:
            fun = "b" if veg_code <= 9 else "c"
        else: # Southern Sweden assumed otherwise
            fun = "a"
    elif main_species == TreeSpecies.Sweden.pinus_sylvestris:
        # For Pine: Northern Sweden with altitude >= 200 meters
        fun = "g" if county_code in NORTHERN_COUNTY_CODES and altitude >= 200 else "f"

    if fun is None:
        # Use county label in error message for clarity
        raise TypeError(f"Unrecognized combination for species {main_species.full_name}, county {county.value.label}, veg_code {veg_code}")

    # Calculate bonitet (same logic as before)
    bon = 0.0
    if fun == "a":
        bon = (0.57207 + 0.22166 * H100 + 0.0050164 * H100 ** 2) * F1
    elif fun == "b":
        bon = (1.28417 + 0.31060 * H100 + 0.0020048 * H100 ** 2) * F1
    elif fun == "c":
        bon = (-0.42289 + 0.17735 * H100 + 0.0050580 * H100 ** 2) * F1
    elif fun == "d":
        bon = (-0.75761 + 0.24393 * H100 + 0.0014564 * H100 ** 2) * F2
    elif fun == "e":
        bon = (-0.59224 + 0.21765 * H100 + 0.0011391 * H100 ** 2) * F2
    elif fun == "f":
        bon = (-0.39456 + 0.16469 * H100 + 0.0047191 * H100 ** 2) * F2
    elif fun == "g":
        bon = (0.099227 + 0.067873 * H100 + 0.0066316 * H100 ** 2) * F2
    else:
        raise TypeError(f"Internal error: function code '{fun}' not recognized.")

    return bon