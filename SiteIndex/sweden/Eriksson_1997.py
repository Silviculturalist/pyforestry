import warnings
import math

def eriksson_1997_height_trajectory_sweden_birch(dominant_height, age, age2):
    """
    Height trajectory for Birch in Sweden based on Eriksson et al. (1997).

    This function estimates the dominant height of Birch stands in Sweden at a given target age,
    based on the dominant height at the initial age. The model is derived from the Hossfeld IV 
    growth equation.

    Parameters:
        dominant_height (float): Dominant height of the stand (meters).
        age (float): Age of the stand at breast height (years).
        age2 (float): Target age at breast height (years).

    Returns:
        float: Estimated dominant height (meters) at age2.

    Raises:
        Warning: If the input ages are outside the range of suitability (10 to 90 years).

    References:
        Eriksson, H., Johansson, U., Kiviste, A. (1997). 
        "A site-index model for pure and mixed stands of Betula pendula and Betula pubescens in Sweden."
        Scandinavian Journal of Forest Research, 12:2, pp. 149-156.
        DOI: https://doi.org/10.1080/02827589709355396

    Notes:
        - Suitable for Birch stands of cultivated origin between ages 10 and 90 years.
    """

    # Check for suitability of input ages
    if age < 10 or age2 < 10:
        warnings.warn("Suitable for cultivated stands of Birch between total ages of 10 and 90.")
    if age > 90 or age2 > 90:
        warnings.warn("Suitable for cultivated stands of Birch between total ages of 10 and 90.")

    # Model parameters
    param_asi = 7
    param_beta = 394
    param_b2 = 1.387

    # Calculations
    d = param_beta / (param_asi**param_b2)
    r = math.sqrt(((dominant_height - 1.3 - d)**2) + (4 * param_beta * (dominant_height - 1.3) / (age**param_b2)))

    # Height at target age
    height_at_age2 = (
        ((dominant_height - 1.3 + d + r) /
         (2 + (4 * param_beta * (age2**-param_b2)) / (dominant_height - 1.3 - d + r)))
        + 1.3
    )

    return height_at_age2
