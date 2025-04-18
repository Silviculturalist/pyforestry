# Filename: Opdahl_1991.py
import math
import warnings
from typing import Union, Set, Optional
from Munin.Helpers.Primitives import Volume, Diameter_cm 
from Munin.Helpers.TreeSpecies import TreeName, parse_tree_species # Assuming these are in the path

# Define the species this function applies to
OPDAHL_1989_SPECIES: Set[TreeName] = {
    TreeName.populus_tremula
}

def opdahl_1989_volume_aspen_norway(
    height_m: float,
    diameter_cm: Union[Diameter_cm, float],
    species: Union[TreeName, str],
    bark_thickness_cm: Optional[float] = None, # Double bark thickness in cm (required if with_bark=False)
    with_bark: bool = True
) -> Volume:
    """
    Calculates tree volume for Aspen (Populus tremula) in Norway based on Opdahl & Skrøppa (1989).

    Can calculate volume over bark (default) or under bark if double bark
    thickness is provided.

    Args:
        height_m (float): Total tree height in meters.
        diameter_cm (Union[Diameter_cm, float]): Diameter at breast height (1.3m)
            over bark, in centimeters.
        species (Union[TreeName, str]): The species of the tree. Must be Populus tremula
            (or potentially P. tremula x tremuloides).
        bark_thickness_cm (Optional[float]): Double bark thickness at breast
            height in cm. Required if `with_bark` is False. Ignored if
            `with_bark` is True.
        with_bark (bool): If True (default), calculates volume over bark.
                          If False, calculates volume under bark using the
                          provided `bark_thickness_cm` to reduce the diameter.

    Returns:
        Volume: Estimated tree volume ('m3sk' type) in cubic decimeters (liters),
                tagged with region 'Norway' and the input species. Returns 0 volume
                if inputs are below thresholds or invalid.

    Raises:
        ValueError: If inputs are invalid (e.g., negative diameter/height, incorrect
                    species, missing bark thickness when `with_bark=False`).
        TypeError: If input types are incorrect.

    References:
        Opdahl, H. & Skrøppa, T. (1989). Avsmaling og volum hos osp (Popolus tremula L.)
        i Sør-Norge [Taper and volume of aspen (Populus tremula L.) in South Norway].
        Meddelelser fra Norsk institutt for skogforskning, 43(2), 42 s. Ås.
        Formula derived from C# code (TreeVolumeNorway.cs), appears to calculate m³ first:
        V_m3 = -0.04755 + (d_eff_cm * 0.00699) - (d_eff_cm^2 * 0.00023) + ((d_eff_cm^2 * h_m) * 0.00004)
        V_dm3 = V_m3 * 1000
        Where d_eff_cm = d_ob_cm (if with_bark=True) or d_ob_cm - bark_cm (if with_bark=False).

    Notes:
        - Assumes the volume type is 'm3sk'.
        - Returns volume in dm³ (liters).
    """
    # --- Input Validation ---
    if isinstance(diameter_cm, Diameter_cm): #
        if diameter_cm.measurement_height_m != 1.3:
             warnings.warn(f"Input 'diameter_cm' (Diameter_cm) has measurement height {diameter_cm.measurement_height_m}m, but the model assumes 1.3m.")
        if not diameter_cm.over_bark:
             raise ValueError("Input 'diameter_cm' (Diameter_cm) must be measured over bark for this function.")
        diam_ob_cm = float(diameter_cm) # Over Bark diameter
    elif isinstance(diameter_cm, (float, int)):
        diam_ob_cm = float(diameter_cm)
    else:
        raise TypeError("Input 'diameter_cm' must be a float, int, or Diameter_cm object.")

    if diam_ob_cm < 0:
        raise ValueError("Input 'diameter_cm' must be non-negative.")
    if height_m < 1.3: # C# checks against 1.3m minimum height
        # raise ValueError("Input 'height_m' must be >= 1.3 meters.")
        return Volume.Norway.dm3sk(0.0, species=TreeName.populus_tremula) # Return 0 if below BH

    # Species validation
    try:
        tree_species = parse_tree_species(species) #
        if tree_species not in OPDAHL_1989_SPECIES:
            raise ValueError(f"Species '{tree_species.full_name}' is not applicable for this function. Expected one of { {sp.full_name for sp in OPDAHL_1989_SPECIES} }.")
    except ValueError as e:
        raise ValueError(f"Invalid species input: {e}") from e

    # Bark and Diameter Under Bark Validation/Calculation
    diam_eff_cm = diam_ob_cm # Effective diameter used in the formula
    if not with_bark:
        if bark_thickness_cm is None:
            # Use Birch bark function as C# implies Aspen uses Birch bark model
            try:
                # Need to import the Birch bark function if it's separate
                from Munin.Bark.norway.Braastad_1966_birch_norway_bark_thickness import braastad_1966_birch_norway_bark_thickness
                bark_thickness_cm = braastad_1966_birch_norway_bark_thickness(diam_ob_cm, height_m)
                warnings.warn("Bark thickness for Aspen not provided, calculated using Braastad (1966) Birch model.")
            except ImportError:
                 raise ValueError("`bark_thickness_cm` (double bark thickness) must be provided when `with_bark` is False, and Birch bark function could not be imported to estimate it.")

        if not isinstance(bark_thickness_cm, (float, int)):
             raise TypeError("`bark_thickness_cm` must be a number.")
        if bark_thickness_cm < 0:
             raise ValueError("`bark_thickness_cm` cannot be negative.")

        diam_eff_cm = diam_ob_cm - float(bark_thickness_cm)
        # Check if diameter under bark became negative
        if diam_eff_cm < 0:
            return Volume.Norway.dm3sk(0.0, species=tree_species) #

    # Handle edge case: zero original diameter or effective diameter <= 0
    # C# checks diam < double.Epsilon for original diameter
    if diam_ob_cm <= 1e-9 or diam_eff_cm <= 0:
        return Volume.Norway.dm3sk(0.0, species=tree_species) #

    # --- Calculation ---
    d_eff = diam_eff_cm
    d_eff2 = d_eff * d_eff
    h = height_m

    # Calculate volume in m³ first, based on C# formula structure
    volume_m3 = (
        -0.04755
        + (d_eff * 0.00699)
        - (d_eff2 * 0.00023)
        + (d_eff2 * h * 0.00004)
    )

    # Convert volume from m³ to dm³ (liters)
    volume_dm3 = volume_m3 * 1000.0

    # Ensure non-negative volume (C# uses >= 1.0 check, we use >= 0.0)
    volume_dm3 = max(0.0, volume_dm3)

    # Return using Volume class factory
    # Assuming dm³ and type 'm3sk' - VERIFY THIS FROM SOURCE/CONTEXT
    return Volume.Norway.dm3sk(volume_dm3, species=tree_species)