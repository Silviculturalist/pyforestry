"""Translate H100 site index values to expected productivity.

This module implements the smoothed equations from Hägglund (1981) to convert
H100 estimates to mean annual volume growth at the time of culmination. The
function :func:`hagglund_1981_si_to_productivity` is the public entry point and
accepts enumerated inputs for vegetation type, county and tree species.
"""

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers.primitives import SiteIndexValue
from pyforestry.base.helpers.tree_species import TreeName, TreeSpecies
from pyforestry.sweden.site.enums import Sweden
from pyforestry.sweden.siteindex.validation import validate_hagglund_1970_h100_site_index


def hagglund_1981_si_to_productivity(
    h100_input: SiteIndexValue,
    main_species: TreeName,
    vegetation: Sweden.FieldLayer,
    altitude: float,
    county: Sweden.County,  # Changed type hint to the Enum
) -> float:
    """
    Calculate smoothed productivity estimates in m3sk (cu.m.) from Hägglund 1981.

    Parameters:
        h100_input (SiteIndexValue):
            Estimated stand top height object. Must be H100, meaning
            ``reference_age`` equals 100.
        main_species (TreeName): Main species (e.g., ``TreeSpecies.Sweden.picea_abies``).
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
        Sweden.County.KOPPARBERG_SALEN_IDRE,
    }

    MIDDLE_COUNTY_CODES = {
        Sweden.County.KOPPARBERG_OVRIGA,
        Sweden.County.GAVLEBORG_HALSINGLANDS,
        Sweden.County.GAVLEBORG_OVRIGA,
        Sweden.County.VARMLAND,
    }

    validate_hagglund_1970_h100_site_index(
        h100_input,
        param_name="h100_input",
        expected_species=main_species,
        allowed_species={
            TreeSpecies.Sweden.picea_abies,
            TreeSpecies.Sweden.pinus_sylvestris,
        },
    )

    site_index_h100_m = float(h100_input)
    if site_index_h100_m <= 0:
        raise ValueError("H100 value must be positive.")  #

    if not isinstance(vegetation, Sweden.FieldLayer):
        raise TypeError("vegetation must be a Sweden.FieldLayer enum member.")  #

    if not isinstance(county, Sweden.County):
        raise TypeError("county must be a Sweden.County enum member.")  #

    # --- rest of the function remains the same ---
    veg_code = vegetation.value.code

    spruce_smoothing_factor = 0.72 + (site_index_h100_m / 130)
    pine_smoothing_factor = 0.70 + (site_index_h100_m / 100)
    function_key = None

    # Determine function based on species, county code, vegetation code, and altitude
    if main_species == TreeSpecies.Sweden.picea_abies:
        if county in NORTHERN_COUNTY_CODES:
            function_key = "d" if veg_code <= 9 else "e"
        elif county in MIDDLE_COUNTY_CODES:
            function_key = "b" if veg_code <= 9 else "c"
        else:  # Southern Sweden assumed otherwise
            function_key = "a"
    elif main_species == TreeSpecies.Sweden.pinus_sylvestris:
        # For Pine: Northern Sweden with altitude >= 200 meters
        function_key = "g" if county in NORTHERN_COUNTY_CODES and altitude >= 200 else "f"

    if function_key is None:
        # Use county label in error message for clarity
        raise TypeError(
            "Unrecognized combination for species "
            f"{main_species.full_name}, county {county.value.label}, veg_code {veg_code}"
        )

    # Calculate bonitet (same logic as before)
    bon = 0.0
    if function_key == "a":
        bon = (
            0.57207 + 0.22166 * site_index_h100_m + 0.0050164 * site_index_h100_m**2
        ) * spruce_smoothing_factor
    elif function_key == "b":
        bon = (
            1.28417 + 0.31060 * site_index_h100_m + 0.0020048 * site_index_h100_m**2
        ) * spruce_smoothing_factor
    elif function_key == "c":
        bon = (
            -0.42289 + 0.17735 * site_index_h100_m + 0.0050580 * site_index_h100_m**2
        ) * spruce_smoothing_factor
    elif function_key == "d":
        bon = (
            -0.75761 + 0.24393 * site_index_h100_m + 0.0014564 * site_index_h100_m**2
        ) * pine_smoothing_factor
    elif function_key == "e":
        bon = (
            -0.59224 + 0.21765 * site_index_h100_m + 0.0011391 * site_index_h100_m**2
        ) * pine_smoothing_factor
    elif function_key == "f":
        bon = (
            -0.39456 + 0.16469 * site_index_h100_m + 0.0047191 * site_index_h100_m**2
        ) * pine_smoothing_factor
    elif function_key == "g":
        bon = (
            0.099227 + 0.067873 * site_index_h100_m + 0.0066316 * site_index_h100_m**2
        ) * pine_smoothing_factor
    else:
        raise TypeError(f"Internal error: function code '{function_key}' not recognized.")

    return bon


DESCRIPTOR = FormulaDescriptor(
    component_id="hagglund_1981_siteindex",
    source=SourceReference(
        author="Hägglund, B.",
        year=1981,
        title="Site index to productivity (mean annual volume growth at culmination) translation",
    ),
    species_groups={
        "spruce": frozenset({"Picea abies"}),
        "pine": frozenset({"Pinus sylvestris"}),
    },
    units={},
    kernel_names=("hagglund_1981_si_to_productivity",),
)
