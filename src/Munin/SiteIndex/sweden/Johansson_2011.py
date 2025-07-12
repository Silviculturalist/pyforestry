# Johansson_2011.py

import math
import warnings
from typing import Union
# Imports added
from Munin.helpers.primitives import Age, AgeMeasurement, SiteIndexValue
from Munin.helpers.tree_species import TreeSpecies

def johansson_2011_height_trajectory_sweden_poplar(
    dominant_height: float,
    age: Union[float, AgeMeasurement],
    age2: Union[float, AgeMeasurement]
) -> SiteIndexValue:
    """
    Height trajectory for Poplar on former farmland in Sweden based on Johansson (2011).

    This function calculates the height trajectory for Poplar stands in Sweden using
    a generalized algebraic difference approach (ADA) model.

    Parameters:
        dominant_height (float): Dominant height of the stand (meters).
        age (Union[float, AgeMeasurement]): Total age of the stand (years). Must be float/int or Age.TOTAL.
        age2 (Union[float, AgeMeasurement]): Target age for output height (years). Must be float/int or Age.TOTAL.

    Returns:
        SiteIndexValue: Dominant height at age2 (meters) wrapped in a SiteIndexValue object.

    Raises:
        Warning: Indicates the model is suitable for stands under 50-60 years of age.
        TypeError: If age or age2 are not float/int or AgeMeasurement with Age.TOTAL code.

    References:
        Johansson, T. (2011). "Site index curves for Poplar growing on former farmland in Sweden."
        Scandinavian Journal of Forest Research, Vol. 26(2), pp. 161-170.
        DOI: https://doi.org/10.1080/02827581.2010.543428

    Notes:
        - Suitable for Poplar stands growing on former farmland in Sweden.
        - Model is most accurate for stands under 50 to 60 years of age.
        - Requires total age (Age.TOTAL).
        - Assumes Poplar refers to Populus tremula for species assignment.
    """
    # Argument Validation Added
    if isinstance(age, AgeMeasurement):
        if age.code != Age.TOTAL.value:
            raise TypeError("Parameter 'age' must be a float/int or an instance of Age.TOTAL.")
        age_val = float(age)
    elif isinstance(age, (float, int)):
        age_val = float(age)
    else:
        raise TypeError("Parameter 'age' must be a float/int or an instance of Age.TOTAL.")

    if isinstance(age2, AgeMeasurement):
        if age2.code != Age.TOTAL.value:
            raise TypeError("Parameter 'age2' must be a float/int or an instance of Age.TOTAL.")
        age2_val = float(age2)
    elif isinstance(age2, (float, int)):
        age2_val = float(age2)
    else:
        raise TypeError("Parameter 'age2' must be a float/int or an instance of Age.TOTAL.")

    # Warn if ages exceed suitability
    if age_val > 60 or age2_val > 60:
        warnings.warn("Suitable for stands of Poplar on former farmland in Sweden under age of 50-60 years.")

    # Model parameters
    b0 = 2.1405
    b1 = 6460.5
    b2 = 18.2238

    # Calculate intermediate values
    Z0 = dominant_height - b2
    P = Z0 + math.sqrt(Z0**2 + (2 * b1 * dominant_height) / (age_val**b0))

    # Height at target age
    height_at_age2 = dominant_height * (
        ((age2_val**b0) * ((age_val**b0) * P + b1)) /
        ((age_val**b0) * ((age2_val**b0) * P + b1))
    )

    # Return modified to SiteIndexValue (Assuming Populus tremula)
    return SiteIndexValue(
        value=height_at_age2,
        reference_age=Age.TOTAL(age2_val),
        species={TreeSpecies.Sweden.populus_tremula}, 
        fn=johansson_2011_height_trajectory_sweden_poplar
    )