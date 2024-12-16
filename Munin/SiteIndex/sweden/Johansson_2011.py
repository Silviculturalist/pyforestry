import math
import warnings

def johansson_2011_height_trajectory_sweden_poplar(dominant_height, age, age2):
    """
    Height trajectory for Poplar on former farmland in Sweden based on Johansson (2011).

    This function calculates the height trajectory for Poplar stands in Sweden using 
    a generalized algebraic difference approach (ADA) model.

    Parameters:
        dominant_height (float): Dominant height of the stand (meters).
        age (float): Total age of the stand (years).
        age2 (float): Target age for output height (years).

    Returns:
        float: Dominant height at age2 (meters).

    Raises:
        Warning: Indicates the model is suitable for stands under 50-60 years of age.

    References:
        Johansson, T. (2011). "Site index curves for Poplar growing on former farmland in Sweden."
        Scandinavian Journal of Forest Research, Vol. 26(2), pp. 161-170.
        DOI: https://doi.org/10.1080/02827581.2010.543428

    Notes:
        - Suitable for Poplar stands growing on former farmland in Sweden.
        - Model is most accurate for stands under 50 to 60 years of age.
    """

    # Warn if ages exceed suitability
    if age > 60 or age2 > 60:
        warnings.warn("Suitable for stands of Poplar on former farmland in Sweden under age of 50-60 years.")

    # Model parameters
    b0 = 2.1405
    b1 = 6460.5
    b2 = 18.2238

    # Calculate intermediate values
    Z0 = dominant_height - b2
    P = Z0 + math.sqrt(Z0**2 + (2 * b1 * dominant_height) / (age**b0))

    # Height at target age
    height_at_age2 = dominant_height * (
        ((age2**b0) * ((age**b0) * P + b1)) /
        ((age**b0) * ((age2**b0) * P + b1))
    )

    return height_at_age2
