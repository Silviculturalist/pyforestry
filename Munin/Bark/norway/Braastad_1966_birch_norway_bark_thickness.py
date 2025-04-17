import warnings
from typing import Union
from Munin.Helpers.Base import Diameter_cm 

def braastad_1966_birch_norway_bark_thickness(
    diameter_cm: Union[Diameter_cm, float],
    height_m: float # Height is not used in formula but kept for signature consistency
) -> float:
    """
    Calculates double bark thickness for Birch (and Aspen) in Norway based on Braastad (1966).

    Args:
        diameter_cm (Union[Diameter_cm, float]): Diameter at breast height (1.3m)
            over bark, in centimeters. If Diameter_cm object is provided,
            it must be over_bark=True.
        height_m (float): Total tree height in meters (parameter kept for consistency,
             but not used in this specific formula).

    Returns:
        float: Estimated double bark thickness in centimeters.

    Raises:
        ValueError: If diameter_cm is negative, height_m < 1.3 (if checked), or if a
                    Diameter_cm object is provided with over_bark=False.
        TypeError: If diameter_cm is not a valid type.

    References:
        Braastad, H. (1966). Volumtabeller for bjørk [Volume tables for birch].
        Meddelelser fra Det norske Skogforsøksvesen, 21(77?), 23-? pp.
        Formula calculates double bark thickness in mm: d_bark_mm = 1.046 * dbh_cm
        Also used for Aspen according to C# code.

    Notes:
        - Aligns with C# BarkThicknessNorway.GetBarkThickness for Birch/Aspen.
        - Returns *double* bark thickness in cm.
        - A minimum double bark thickness of 5% of DBH is applied.
    """
    # Input validation
    if isinstance(diameter_cm, Diameter_cm): #
        if not diameter_cm.over_bark:
            raise ValueError("Input 'diameter_cm' (Diameter_cm) must be measured over bark.")
        if diameter_cm.measurement_height_m != 1.3:
             warnings.warn(f"Input 'diameter_cm' (Diameter_cm) has measurement height {diameter_cm.measurement_height_m}m, but the model assumes 1.3m.")
        d_cm = float(diameter_cm)
    elif isinstance(diameter_cm, (float, int)):
        d_cm = float(diameter_cm)
    else:
        raise TypeError("Input 'diameter_cm' must be a float, int, or Diameter_cm object.")

    if d_cm < 0:
        raise ValueError("Input 'diameter_cm' must be non-negative.")
    # Optional: Check height_m if strict consistency is needed, even if unused.
    # if height_m < 1.3:
    #     raise ValueError("Input 'height_m' must be >= 1.3 meters.")

    # Calculate double bark thickness in mm
    double_bark_mm = 1.046 * d_cm

    # Apply safety check: ensure minimum 5% of DBH (as double bark thickness)
    min_double_bark_mm = d_cm * 0.05 * 10.0 # 5% of diameter in mm
    if double_bark_mm < min_double_bark_mm:
        double_bark_mm = min_double_bark_mm

    # Convert mm to cm for return value
    double_bark_cm = double_bark_mm / 10.0

    # Ensure non-negative return
    return max(0.0, double_bark_cm)