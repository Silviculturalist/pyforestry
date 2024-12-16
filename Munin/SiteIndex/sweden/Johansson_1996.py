import warnings
import math

def johansson_1996_height_trajectory_sweden_aspen(dominant_height, age, age2, model1=False):
    """
    Height trajectory for European Aspen in Sweden based on Johansson (1996).

    This function calculates the height trajectory of European Aspen (Populus tremula L.) 
    stands in Sweden, either based on the recommended site index model or an alternative model (Model 1).

    Parameters:
        dominant_height (float): Dominant height of the stand (meters).
        age (float): Total age of the stand (years).
        age2 (float): Target age for output height (years).
        model1 (bool): If True, uses Model 1 from Johansson (1996); otherwise, uses the default model. Defaults to False.

    Returns:
        float: Dominant height at age2 (meters).

    Raises:
        Warning: If `age` or `age2` exceed 60 years, as the model is suitable for stands under 60 years.

    References:
        Johansson, T. (1996). "Site Index Curves for European Aspen (Populus tremula L.) Growing on Forest Land 
        of Different Soils in Sweden." Silva Fennica 30(4): 437-458. DOI: https://doi.org/10.14214/sf.a8503

    Notes:
        - The function is suitable for stands of Aspen under 60 years of age.
        - If Model 1 is selected, the formula uses a simpler exponential model.

    """
    # Warn if ages exceed suitability
    if age > 60 or age2 > 60:
        warnings.warn("Suitable for stands of Aspen under age of 60.")

    # If Model 1 is selected
    if model1:
        return dominant_height * (((1 - math.exp(-0.0235 * age2)) / (1 - math.exp(-0.0235 * age))) ** 1.1568)

    # Default model parameters
    param_asi = 7
    param_beta = 693.2
    param_b2 = -0.9771

    # Calculate parameters
    d = param_beta * (param_asi**param_b2)
    r = math.sqrt(((dominant_height - d)**2) + (4 * param_beta * dominant_height * (age**param_b2)))

    # Calculate height at target age
    height_at_age2 = ((dominant_height + d + r) / 
                      (2 + (4 * param_beta * (age2**param_b2)) / (dominant_height - d + r)))

    return height_at_age2
