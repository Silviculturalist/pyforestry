import warnings
from typing import Union
from Munin.Helpers.Primitives import Diameter_cm 

def vestjordet_1967_norway_spruce_norway_bark_thickness(
    diameter_cm: Union[Diameter_cm, float],
    height_m: float
) -> float:
    """
    Calculates double bark thickness for Norway Spruce in Norway based on Vestjordet (1967).

    Args:
        diameter_cm (Union[Diameter_cm, float]): Diameter at breast height (1.3m)
            over bark, in centimeters. If Diameter_cm object is provided,
            it must be over_bark=True.
        height_m (float): Total tree height in meters.

    Returns:
        float: Estimated double bark thickness in centimeters.

    Raises:
        ValueError: If diameter_cm is negative, height_m <= 0, or if a
                    Diameter_cm object is provided with over_bark=False.
        TypeError: If diameter_cm is not a valid type.

    References:
        Vestjordet, E. (1967). Functions and tables for volume of standing trees. Norway spruce.
        Meddelelser fra Det norske Skogforsøksvesen, 22(84), pp. 539-574.
        Formula calculates double bark thickness in mm:
        d_bark_mm = -0.34 + 0.831648*d_cm - 0.002832*d_cm^2 - 0.010112*h^2 + 0.700203*d_cm^2/h^2

    Notes:
        - Aligns with C# BarkThicknessNorway.GetBarkThickness for Spruce.
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
    if height_m <= 0: # Check against 0 for division safety, C# uses this check.
        # raise ValueError("Input 'height_m' must be > 0 meters.")
         return 0.0 # Return 0 if height is non-positive, matching C#

    # Calculate double bark thickness in mm
    d2 = d_cm * d_cm
    h2 = height_m * height_m
    # Avoid division by zero already handled by height_m <= 0 check above
    double_bark_mm = (
        -0.34
        + 0.831648 * d_cm
        - 0.002832 * d2
        - 0.010112 * h2
        + 0.700203 * d2 / h2
    )

    # Apply safety check: ensure minimum 5% of DBH (as double bark thickness)
    min_double_bark_mm = d_cm * 0.05 * 10.0 # 5% of diameter in mm
    if double_bark_mm < min_double_bark_mm:
        double_bark_mm = min_double_bark_mm

    # Convert mm to cm for return value
    double_bark_cm = double_bark_mm / 10.0

    # Ensure non-negative return
    return max(0.0, double_bark_cm)