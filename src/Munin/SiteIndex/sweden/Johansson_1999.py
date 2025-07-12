# Johansson_1999.py

import warnings
import math
from typing import Union
# Imports added
from Munin.helpers.primitives import Age, AgeMeasurement, SiteIndexValue
from Munin.helpers.tree_species import TreeSpecies

def johansson_1999_height_trajectory_sweden_alnus_glutinosa(
    dominant_height: float,
    age: Union[float, AgeMeasurement],
    age2: Union[float, AgeMeasurement]
) -> SiteIndexValue:
    """
    Height trajectory for Common Alder (Alnus glutinosa) in Sweden based on Johansson (1999).

    This function calculates the height trajectory for Common Alder stands in Sweden,
    suitable for stands under 100 years of age.

    Parameters:
        dominant_height (float): Dominant height of the stand (meters).
        age (Union[float, AgeMeasurement]): Total age of the stand (years). Must be float/int or Age.TOTAL.
        age2 (Union[float, AgeMeasurement]): Target age for output height (years). Must be float/int or Age.TOTAL.

    Returns:
        SiteIndexValue: Dominant height at age2 (meters) wrapped in a SiteIndexValue object.

    Raises:
        Warning: If the input ages exceed 100 years, as the model is suitable for stands under 100 years.
        TypeError: If age or age2 are not float/int or AgeMeasurement with Age.TOTAL code.

    References:
        Johansson, T. (1999). "Site Index Curves for Common Alder and Grey Alder Growing on
        Different Types of Forest Soil in Sweden." Scandinavian Journal of Forest Research,
        Vol. 14:5, pp. 441-453. DOI: https://doi.org/10.1080/02827589950154140

    Notes:
        - Suitable for Common Alder stands under 100 years of age.
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
    if age_val > 100 or age2_val > 100:
        warnings.warn("Suitable for stands of Common Alder under age of 100.")

    # Model parameters
    param_asi = 7
    param_beta = 381.5
    param_b2 = -1.3823

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
        species={TreeSpecies.Sweden.alnus_glutinosa},
        fn=johansson_1999_height_trajectory_sweden_alnus_glutinosa
    )


def johansson_1999_height_trajectory_sweden_alnus_incana(
    dominant_height: float,
    age: Union[float, AgeMeasurement],
    age2: Union[float, AgeMeasurement]
) -> SiteIndexValue:
    """
    Height trajectory for Grey Alder (Alnus incana) in Sweden based on Johansson (1999).

    This function calculates the height trajectory for Grey Alder stands in Sweden,
    suitable for stands under 70 years of age.

    Parameters:
        dominant_height (float): Dominant height of the stand (meters).
        age (Union[float, AgeMeasurement]): Total age of the stand (years). Must be float/int or Age.TOTAL.
        age2 (Union[float, AgeMeasurement]): Target age for output height (years). Must be float/int or Age.TOTAL.

    Returns:
        SiteIndexValue: Dominant height at age2 (meters) wrapped in a SiteIndexValue object.

    Raises:
        Warning: If the input ages exceed 70 years, as the model is suitable for stands under 70 years.
        TypeError: If age or age2 are not float/int or AgeMeasurement with Age.TOTAL code.

    References:
        Johansson, T. (1999). "Site Index Curves for Common Alder and Grey Alder Growing on
        Different Types of Forest Soil in Sweden." Scandinavian Journal of Forest Research,
        Vol. 14:5, pp. 441-453. DOI: https://doi.org/10.1080/02827589950154140

    Notes:
        - Suitable for Grey Alder stands under 70 years of age.
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
    if age_val > 70 or age2_val > 70:
        warnings.warn("Suitable for stands of Grey Alder under age of 70.")

    # Model parameters
    param_asi = 7
    param_beta = 278.9
    param_b2 = -1.3152

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
        species={TreeSpecies.Sweden.alnus_incana},
        fn=johansson_1999_height_trajectory_sweden_alnus_incana
    )