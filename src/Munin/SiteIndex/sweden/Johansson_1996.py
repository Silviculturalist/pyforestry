# Johansson_1996.py

import warnings
import math
from typing import Union
# Imports added
from Munin.Helpers.Primitives import Age, AgeMeasurement, SiteIndexValue
from Munin.Helpers.TreeSpecies import TreeSpecies

def johansson_1996_height_trajectory_sweden_aspen(
    dominant_height: float,
    age: Union[float, AgeMeasurement],
    age2: Union[float, AgeMeasurement],
    model1: bool = False
) -> SiteIndexValue:
    """
    Height trajectory for European Aspen in Sweden based on Johansson (1996).

    This function calculates the height trajectory of European Aspen (Populus tremula L.)
    stands in Sweden, either based on the recommended site index model or an alternative model (Model 1).

    Parameters:
        dominant_height (float): Dominant height of the stand (meters).
        age (Union[float, AgeMeasurement]): Total age of the stand (years). Must be float/int or Age.TOTAL.
        age2 (Union[float, AgeMeasurement]): Target age for output height (years). Must be float/int or Age.TOTAL.
        model1 (bool): If True, uses Model 1 from Johansson (1996); otherwise, uses the default model. Defaults to False.

    Returns:
        SiteIndexValue: Dominant height at age2 (meters) wrapped in a SiteIndexValue object.

    Raises:
        Warning: If `age` or `age2` exceed 60 years, as the model is suitable for stands under 60 years.
        TypeError: If age or age2 are not float/int or AgeMeasurement with Age.TOTAL code.

    References:
        Johansson, T. (1996). "Site Index Curves for European Aspen (Populus tremula L.) Growing on Forest Land
        of Different Soils in Sweden." Silva Fennica 30(4): 437-458. DOI: https://doi.org/10.14214/sf.a8503

    Notes:
        - The function is suitable for stands of Aspen under 60 years of age.
        - If Model 1 is selected, the formula uses a simpler exponential model.
        - Requires total age (Age.TOTAL).

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
        warnings.warn("Suitable for stands of Aspen under age of 60.")

    # If Model 1 is selected
    if model1:
        height_at_age2 = dominant_height * (((1 - math.exp(-0.0235 * age2_val)) / (1 - math.exp(-0.0235 * age_val))) ** 1.1568)
        return SiteIndexValue(
            value=height_at_age2,
            reference_age=Age.TOTAL(age2_val),
            species={TreeSpecies.Sweden.populus_tremula},
            fn=johansson_1996_height_trajectory_sweden_aspen
        )


    # Default model parameters
    param_asi = 7
    param_beta = 693.2
    param_b2 = -0.9771

    # Calculate parameters
    d = param_beta * (param_asi**param_b2)
    r = math.sqrt(((dominant_height - d)**2) + (4 * param_beta * dominant_height * (age_val**param_b2)))

    # Calculate height at target age
    height_at_age2 = ((dominant_height + d + r) /
                      (2 + (4 * param_beta * (age2_val**param_b2)) / (dominant_height - d + r)))

    # Return modified to SiteIndexValue
    return SiteIndexValue(
        value=height_at_age2,
        reference_age=Age.TOTAL(age2_val),
        species={TreeSpecies.Sweden.populus_tremula},
        fn=johansson_1996_height_trajectory_sweden_aspen
    )