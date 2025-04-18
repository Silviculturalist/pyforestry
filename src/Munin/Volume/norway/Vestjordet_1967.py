import math
import warnings
from typing import Union, Optional
from Munin.Helpers.Base import Volume, Diameter_cm #
from Munin.Helpers.TreeSpecies import TreeName, TreeSpecies, parse_tree_species 

def vestjordet_1967_volume_norway_spruce_norway(
    height_m: float,
    diameter_cm: Union[Diameter_cm, float],
    bark_thickness_cm: Optional[float] = None, # Double bark thickness in cm (required if with_bark=False)
    with_bark: bool = True
) -> Volume:
    """
    Calculates tree volume for Norway Spruce in Norway based on Vestjordet (1967).

    Can calculate volume over bark (default) or under bark if double bark
    thickness is provided.

    Args:
        height_m (float): Total tree height in meters.
        diameter_cm (Union[Diameter_cm, float]): Diameter at breast height (1.3m)
            over bark, in centimeters.
        bark_thickness_cm (Optional[float]): Double bark thickness at breast
            height in cm. Required if `with_bark` is False. Ignored if
            `with_bark` is True.
        with_bark (bool): If True (default), calculates volume over bark.
                          If False, calculates volume under bark using the
                          provided `bark_thickness_cm` to reduce the diameter.

    Returns:
        Volume: Estimated tree volume ('m3sk' type) in cubic decimeters (liters),
                tagged with region 'Norway' and species 'Picea abies'.
                Returns 0 volume if inputs are below thresholds or invalid.

    Raises:
        ValueError: If inputs are invalid (e.g., negative diameter/height,
                    missing bark thickness when `with_bark=False`).
        TypeError: If input types are incorrect.

    References:
        Vestjordet, E. (1967). Functions and tables for volume of standing trees. Norway spruce.
        Meddelelser fra Det norske Skogforsøksvesen, 22(84), pp. 539-574.
        Formulas (V in dm³, d_eff in cm, h in m):
        If d_ob <= 10: V = 0.52 + 0.02403*d_eff^2*h + 0.01463*d_eff*h^2 - 0.10983*h^2 + 0.15195*d_eff*h
        If 10 < d_ob < 13: V = -31.57 + 0.0016*d_eff*h^2 + 0.0186*h^2 + 0.63*d_eff*h - 2.34*h + 3.20*d_eff
        If d_ob >= 13: V = 10.14 + 0.01240*d_eff^2*h + 0.03117*d_eff*h^2 - 0.36381*h^2 + 0.28578*d_eff*h
        Where d_eff = d_ob (if with_bark=True) or d_ob - bark (if with_bark=False).
        d_ob is original over-bark diameter.

    Notes:
        - Aligns with C# TreeVolumeNorway.CalcTreeVol for Spruce.
        - Assumes the volume type is 'm3sk'. Needs verification.
        - Returns volume in dm³ (liters).
        - Only applicable to Picea abies.
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
    if height_m < 1.3:
        raise ValueError("Input 'height_m' must be >= 1.3 meters.")

    # Bark and Diameter Under Bark Validation/Calculation
    diam_eff_cm = diam_ob_cm # Effective diameter used in the formula
    if not with_bark:
        if bark_thickness_cm is None:
            raise ValueError("`bark_thickness_cm` (double bark thickness) must be provided when `with_bark` is False.")
        if not isinstance(bark_thickness_cm, (float, int)):
             raise TypeError("`bark_thickness_cm` must be a number.")
        if bark_thickness_cm < 0:
             raise ValueError("`bark_thickness_cm` cannot be negative.")

        diam_eff_cm = diam_ob_cm - float(bark_thickness_cm)
        # Check if diameter under bark became negative
        if diam_eff_cm < 0:
            return Volume.Norway.dm3sk(0.0, species=TreeName.picea_abies) #

    # Handle edge case: zero original diameter or effective diameter <= 0
    if diam_ob_cm <= 0 or diam_eff_cm <= 0:
        return Volume.Norway.dm3sk(0.0, species=TreeName.picea_abies) #

    # --- Calculation ---
    d2 = diam_eff_cm * diam_eff_cm
    h2 = height_m * height_m
    volume_dm3 = 0.0

    # Threshold checks use original Over Bark diameter (diam_ob_cm, like diamGr in C#)
    if diam_ob_cm <= 10.0:
        volume_dm3 = (
            0.52
            + 0.02403 * d2 * height_m
            + 0.01463 * diam_eff_cm * h2
            - 0.10983 * h2
            + 0.15195 * diam_eff_cm * height_m
        )
    elif diam_ob_cm < 13.0: # 10 < diam_ob_cm < 13
        volume_dm3 = (
            -31.57
            + 0.0016 * diam_eff_cm * h2
            + 0.0186 * h2
            + 0.63 * diam_eff_cm * height_m
            - 2.34 * height_m
            + 3.20 * diam_eff_cm
        )
    else: # diam_ob_cm >= 13.0
        volume_dm3 = (
            10.14
            + 0.01240 * d2 * height_m
            + 0.03117 * diam_eff_cm * h2
            - 0.36381 * h2
            + 0.28578 * diam_eff_cm * height_m
        )

    # Ensure non-negative volume
    volume_dm3 = max(0.0, volume_dm3)

    # Return using Volume class factory
    return Volume.Norway.dm3sk(volume_dm3, species=TreeName.picea_abies)



def vestjordet_1967_volume_tree_top(
    species: Union[TreeName, str],
    diameter_cm: Union[Diameter_cm, float],
    height_m: float,
    over_bark: bool = True
) -> Volume:
    """
    Calculates the volume of the treetop section based on Vestjordet (1967).

    This volume typically represents the part of the stem above a certain
    merchantable limit, often used in calculating total vs. merchantable volume.

    Args:
        species (Union[TreeName, str]): The tree species (e.g., 'Picea abies',
            'Pinus sylvestris', or a broadleaf type).
        diameter_cm (Union[Diameter_cm, float]): Diameter at breast height (1.3m)
            in centimeters. If Diameter_cm object is provided, its over_bark
            attribute should match the `over_bark` argument.
        height_m (float): Total tree height in meters.
        over_bark (bool): Whether the diameter and the resulting top volume
                          refer to measurements over bark (True) or under
                          bark (False). Defaults to True.

    Returns:
        Volume: Estimated treetop volume ('m3sk' type - needs verification)
                in cubic decimeters (liters), tagged with region 'Norway'
                and the input species.

    Raises:
        ValueError: If inputs are invalid (e.g., negative diameter/height,
                    unrecognized species, mismatch between Diameter_cm.over_bark
                    and the over_bark argument).
        TypeError: If input types are incorrect.

    References:
        Vestjordet, E. (1967). Functions and tables for volume of standing trees. Norway spruce.
        Meddelelser fra Det norske Skogforsøksvesen, 22(84), pp. 539-574.
        Formulas (ftop is volume in dm³):
        Spruce (Picea abies):
          Over bark: ftop = 9.50 - 0.41*d + 0.0049*d^2 + 0.11*h
          Under bark: ftop = 8.04 - 0.39*d + 0.0048*d^2 + 0.11*h
        Other Species (Pine, Broadleaves):
          Over bark: ftop = 11.55 - 0.64*d + 0.0088*d^2 + 0.14*h
          Under bark: ftop = 9.6 - 0.55*d + 0.0075*d^2 + 0.13*h
        Units: Assumes volume (V) is in dm³, d in cm, h in m.

    Notes:
        - The interpretation of "Other Species" including Pine and Broadleaves
          should be verified against the source.
        - Assumes the volume type is 'm3sk'. Needs verification.
        - The function returns volume in dm³ (liters).
    """
    # Input validation & Species parsing
    try:
        tree_species = parse_tree_species(species) #
    except ValueError as e:
        raise ValueError(f"Invalid species input: {e}") from e

    # Diameter validation
    if isinstance(diameter_cm, Diameter_cm): #
        if diameter_cm.over_bark != over_bark:
            raise ValueError(f"Mismatch: over_bark argument is {over_bark}, but Diameter_cm.over_bark is {diameter_cm.over_bark}.")
        if diameter_cm.measurement_height_m != 1.3:
             warnings.warn(f"Input 'diameter_cm' (Diameter_cm) has measurement height {diameter_cm.measurement_height_m}m, but the model assumes 1.3m.")
        d_cm = float(diameter_cm)
    elif isinstance(diameter_cm, (float, int)):
        d_cm = float(diameter_cm)
    else:
        raise TypeError("Input 'diameter_cm' must be a float, int, or Diameter_cm object.")

    if d_cm < 0:
        raise ValueError("Input 'diameter_cm' must be non-negative.")
    if height_m < 0: # Allow height < 1.3m here? Check paper context. Assume >= 0 for now.
        raise ValueError("Input 'height_m' must be non-negative.")


    # Calculation
    d2 = d_cm * d_cm
    ftop_dm3 = 0.0

    # Check if Spruce
    is_spruce = (tree_species == TreeSpecies.Sweden.picea_abies) # Use defined constant

    if is_spruce:
        if over_bark:
            ftop_dm3 = 9.50 - 0.41 * d_cm + 0.0049 * d2 + 0.11 * height_m
        else: # under bark
            ftop_dm3 = 8.04 - 0.39 * d_cm + 0.0048 * d2 + 0.11 * height_m
    else: # Other species (Pine, Broadleaves according to original comment)
        if over_bark:
            ftop_dm3 = 11.55 - 0.64 * d_cm + 0.0088 * d2 + 0.14 * height_m
        else: # under bark
            ftop_dm3 = 9.60 - 0.55 * d_cm + 0.0075 * d2 + 0.13 * height_m

    # Ensure non-negative volume
    ftop_dm3 = max(0.0, ftop_dm3)

    # Return using Volume class factory
    # Assuming dm³ and type 'm3sk' 
    return Volume.Norway.dm3sk(ftop_dm3, species=tree_species)