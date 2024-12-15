import warnings
import math

def johansson_1999_height_trajectory_sweden_alnus_glutinosa(dominant_height, age, age2):
    """
    Height trajectory for Common Alder (Alnus glutinosa) in Sweden based on Johansson (1999).

    This function calculates the height trajectory for Common Alder stands in Sweden, 
    suitable for stands under 100 years of age.

    Parameters:
        dominant_height (float): Dominant height of the stand (meters).
        age (float): Total age of the stand (years).
        age2 (float): Target age for output height (years).

    Returns:
        float: Dominant height at age2 (meters).

    Raises:
        Warning: If the input ages exceed 100 years, as the model is suitable for stands under 100 years.

    References:
        Johansson, T. (1999). "Site Index Curves for Common Alder and Grey Alder Growing on 
        Different Types of Forest Soil in Sweden." Scandinavian Journal of Forest Research, 
        Vol. 14:5, pp. 441-453. DOI: https://doi.org/10.1080/02827589950154140

    Notes:
        - Suitable for Common Alder stands under 100 years of age.
    """

    # Warn if ages exceed suitability
    if age > 100 or age2 > 100:
        warnings.warn("Suitable for stands of Common Alder under age of 100.")

    # Model parameters
    param_asi = 7
    param_beta = 381.5
    param_b2 = -1.3823

    # Calculate parameters
    d = param_beta * (param_asi**param_b2)
    r = math.sqrt(((dominant_height - d)**2) + (4 * param_beta * dominant_height * (age**param_b2)))

    # Calculate height at target age
    height_at_age2 = ((dominant_height + d + r) /
                      (2 + (4 * param_beta * (age2**param_b2)) / (dominant_height - d + r)))

    return height_at_age2

def johansson_1999_height_trajectory_sweden_alnus_incana(dominant_height, age, age2):
    """
    Height trajectory for Grey Alder (Alnus incana) in Sweden based on Johansson (1999).

    This function calculates the height trajectory for Grey Alder stands in Sweden, 
    suitable for stands under 70 years of age.

    Parameters:
        dominant_height (float): Dominant height of the stand (meters).
        age (float): Total age of the stand (years).
        age2 (float): Target age for output height (years).

    Returns:
        float: Dominant height at age2 (meters).

    Raises:
        Warning: If the input ages exceed 70 years, as the model is suitable for stands under 70 years.

    References:
        Johansson, T. (1999). "Site Index Curves for Common Alder and Grey Alder Growing on 
        Different Types of Forest Soil in Sweden." Scandinavian Journal of Forest Research, 
        Vol. 14:5, pp. 441-453. DOI: https://doi.org/10.1080/02827589950154140

    Notes:
        - Suitable for Grey Alder stands under 70 years of age.
    """

    # Warn if ages exceed suitability
    if age > 70 or age2 > 70:
        warnings.warn("Suitable for stands of Grey Alder under age of 70.")

    # Model parameters
    param_asi = 7
    param_beta = 278.9
    param_b2 = -1.3152

    # Calculate parameters
    d = param_beta * (param_asi**param_b2)
    r = math.sqrt(((dominant_height - d)**2) + (4 * param_beta * dominant_height * (age**param_b2)))

    # Calculate height at target age
    height_at_age2 = ((dominant_height + d + r) /
                      (2 + (4 * param_beta * (age2**param_b2)) / (dominant_height - d + r)))

    return height_at_age2

