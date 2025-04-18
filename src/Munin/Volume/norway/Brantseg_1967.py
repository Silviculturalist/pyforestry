import warnings
from typing import Union, Optional
from Munin.Helpers.Base import Volume, Diameter_cm #
from Munin.Helpers.TreeSpecies import TreeName

def brantseg_1967_volume_scots_pine_norway(
    height_m: float,
    diameter_cm: Union[Diameter_cm, float],
    bark_thickness_cm: Optional[float] = None, # Double bark thickness in cm (required if with_bark=False)
    with_bark: bool = True
) -> Volume:
    """
    Calculates tree volume for Scots Pine in South Norway based on Brantseg (1967).

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
                tagged with region 'Norway' and species 'Pinus sylvestris'.
                Returns 0 volume if inputs are below thresholds or invalid.

    Raises:
        ValueError: If inputs are invalid (e.g., negative diameter/height,
                    missing bark thickness when `with_bark=False`).
        TypeError: If input types are incorrect.

    References:
        Brantseg, A. (1967). Volume functions and tables for Scots pine. South Norway.
        Meddelelser fra Det norske Skogforsøksvesen, 22(84), pp. 689-739.
        Formulas (V in dm³, d_eff in cm, h in m):
        If d_ob <= 12: V = 2.912 + 0.039994*d_eff^2*h - 0.001091*d_eff*h^2
        If d_ob > 12:  V = 8.6524 + 0.076844*d_eff^2 + 0.031573*d_eff^2*h
        Where d_eff = d_ob (if with_bark=True) or d_ob - bark (if with_bark=False).
        d_ob is original over-bark diameter.

    Notes:
        - Aligns with C# TreeVolumeNorway.CalcTreeVol for Pine.
        - Assumes the volume type is 'm3sk'. Needs verification.
        - Returns volume in dm³ (liters).
        - Only applicable to Pinus sylvestris.
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
            return Volume.Norway.dm3sk(0.0, species=TreeName.pinus_sylvestris) #

    # Handle edge case: zero original diameter or effective diameter <= 0
    if diam_ob_cm <= 0 or diam_eff_cm <= 0:
        return Volume.Norway.dm3sk(0.0, species=TreeName.pinus_sylvestris) #

    # --- Calculation ---
    d2 = diam_eff_cm * diam_eff_cm
    h2 = height_m * height_m
    volume_dm3 = 0.0

    # Threshold check uses original Over Bark diameter (diam_ob_cm, like diamGr in C#)
    if diam_ob_cm <= 12.0:
        volume_dm3 = (2.912
                      + 0.039994 * d2 * height_m
                      - 0.001091 * diam_eff_cm * h2)
    else: # diam_ob_cm > 12.0
        volume_dm3 = (8.6524
                      + 0.076844 * d2
                      + 0.031573 * d2 * height_m)

    # Ensure non-negative volume
    volume_dm3 = max(0.0, volume_dm3)

    # Return using Volume class factory
    return Volume.Norway.dm3sk(volume_dm3, species=TreeName.pinus_sylvestris)