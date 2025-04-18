import math
import warnings
from typing import Union, Set, Optional
from Munin.Helpers.Primitives import Volume, Diameter_cm 
from Munin.Helpers.TreeSpecies import TreeName, parse_tree_species 

# Define the species this function applies to
BRAASTAD_1966_SPECIES: Set[TreeName] = {
    TreeName.betula_pendula, 
    TreeName.betula_pubescens 
}

def braastad_1966_birch_volume_norway(
    height_m: float,
    diameter_cm: Union[Diameter_cm, float],
    species: Union[TreeName, str],
    bark_thickness_cm: Optional[float] = None, # Double bark thickness in cm (required if with_bark=False)
    with_bark: bool = True
) -> Volume:
    """
    Calculates tree volume for Birch in Norway based on Braastad (1966).

    Can calculate volume over bark (default) or under bark if double bark
    thickness is provided.

    Args:
        height_m (float): Total tree height in meters.
        diameter_cm (Union[Diameter_cm, float]): Diameter at breast height (1.3m)
            over bark, in centimeters.
        species (Union[TreeName, str]): The species of the tree. Must be one of
            Betula pendula or Betula pubescens.
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
        Braastad, H. (1966). Volumtabeller for bjørk [Volume tables for birch].
        Meddelelser fra Det norske Skogforsøksvesen, 21(77?), 23-? pp.
        Formula (V in dm³, d in cm, h in m, bark = double bark thickness in cm):
        V = -1.25409 + 0.12739*d_eff^2 + 0.03166*d_eff^2*h + 0.0009752*d_eff*h^2
            - 0.01226*h^2 - 0.004214*d_eff^2*(bark*10)
        Where d_eff = d (if with_bark=True) or d - bark (if with_bark=False).
        The bark*10 term confirms the formula expects double bark thickness in mm here.

    Notes:
        - Aligns with C# TreeVolumeNorway.CalcTreeVol for Birch.
        - Assumes the volume type is 'm3sk'. Needs verification.
        - Returns volume in dm³ (liters).
    """
    # --- Input Validation ---
    if isinstance(diameter_cm, Diameter_cm): #
        if diameter_cm.measurement_height_m != 1.3:
             warnings.warn(f"Input 'diameter_cm' (Diameter_cm) has measurement height {diameter_cm.measurement_height_m}m, but the model assumes 1.3m.")
        # Ensure Diameter_cm object is over bark if used as the primary diameter
        if not diameter_cm.over_bark:
             raise ValueError("Input 'diameter_cm' (Diameter_cm) must be measured over bark for this function.")
        diam_ob_cm = float(diameter_cm)
    elif isinstance(diameter_cm, (float, int)):
        diam_ob_cm = float(diameter_cm)
    else:
        raise TypeError("Input 'diameter_cm' must be a float, int, or Diameter_cm object.")

    if diam_ob_cm < 0:
        raise ValueError("Input 'diameter_cm' must be non-negative.")
    if height_m < 1.3:
        raise ValueError("Input 'height_m' must be >= 1.3 meters.")

    # Species validation
    try:
        tree_species = parse_tree_species(species) #
        if tree_species not in BRAASTAD_1966_SPECIES:
            raise ValueError(f"Species '{tree_species.full_name}' is not applicable for this function. Expected one of { {sp.full_name for sp in BRAASTAD_1966_SPECIES} }.")
    except ValueError as e:
        raise ValueError(f"Invalid species input: {e}") from e

    # Bark and Diameter Under Bark Validation/Calculation
    diam_eff_cm = diam_ob_cm # Effective diameter used in the formula
    double_bark_cm_input = 0.0 # Bark thickness expected by formula (double, cm)

    if not with_bark:
        if bark_thickness_cm is None:
            raise ValueError("`bark_thickness_cm` (double bark thickness) must be provided when `with_bark` is False.")
        if not isinstance(bark_thickness_cm, (float, int)):
             raise TypeError("`bark_thickness_cm` must be a number.")
        if bark_thickness_cm < 0:
             raise ValueError("`bark_thickness_cm` cannot be negative.")

        double_bark_cm_input = float(bark_thickness_cm)
        diam_eff_cm = diam_ob_cm - double_bark_cm_input
        # Check if diameter under bark became negative
        if diam_eff_cm < 0:
            return Volume.Norway.dm3sk(0.0, species=tree_species) # Return zero volume
    else:
         # Need bark thickness for the formula term even if calculating OB volume.
         # The C# code passes t.BarkThicknessArray[period] regardless of withBark flag.
         # This implies the Birch formula *always* needs the bark input.
         if bark_thickness_cm is None:
             raise ValueError("`bark_thickness_cm` (double bark thickness) must be provided for the Birch volume formula.")
         if not isinstance(bark_thickness_cm, (float, int)):
             raise TypeError("`bark_thickness_cm` must be a number.")
         if bark_thickness_cm < 0:
             raise ValueError("`bark_thickness_cm` cannot be negative.")
         double_bark_cm_input = float(bark_thickness_cm)


    # Handle edge case: zero original diameter or effective diameter <= 0
    if diam_ob_cm <= 0 or diam_eff_cm <= 0:
        return Volume.Norway.dm3sk(0.0, species=tree_species) #

    # --- Calculation ---
    d2 = diam_eff_cm * diam_eff_cm
    h2 = height_m * height_m
    # Formula expects double bark thickness *in mm* for the last term
    double_bark_mm_term = double_bark_cm_input * 10.0

    volume_dm3 = (
        -1.25409
        + 0.12739 * d2
        + 0.03166 * d2 * height_m
        + 0.0009752 * diam_eff_cm * h2
        - 0.01226 * h2
        - 0.004214 * d2 * double_bark_mm_term # Use mm value here
    )

    # Ensure non-negative volume (C# uses >= 1.0 check, we use >= 0.0)
    volume_dm3 = max(0.0, volume_dm3)

    # Return using Volume class factory
    return Volume.Norway.dm3sk(volume_dm3, species=tree_species)