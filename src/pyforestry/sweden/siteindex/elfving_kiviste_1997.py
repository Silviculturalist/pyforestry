import warnings
import math
from typing import Union

from pyforestry.base.helpers import (
    Age, AgeMeasurement, SiteIndexValue, TreeSpecies
)


def elfving_kiviste_1997_height_trajectory_sweden_pine(dominant_height : float,
                                                       age : Union[float,AgeMeasurement], 
                                                       age2 :Union[float, AgeMeasurement]) -> SiteIndexValue:
    """
    Height trajectory for Scots Pine in Sweden based on Elfving & Kiviste (1997).

    This function calculates the height of Scots Pine stands in Sweden for a given target age 
    based on the dominant height at the initial age, using site index equations.

    Parameters:
        dominant_height (float): Dominant height of the stand (meters).
        age (float): Total age of the stand (years).
        age2 (float): Total age at the target output age (years).

    Returns:
        float: Height (meters) a stand will reach at age2.

    Raises:
        Warning: If the input ages are outside the range of suitability (10 to 80 years).

    References:
        Elfving, B., Kiviste, A. (1997). "Construction of site index equations for Pinus sylvestris L. 
        using permanent plot data in Sweden." Forest Ecology and Management, Vol. 98, Issue 2, pp. 125-134.
        DOI: https://doi.org/10.1016/S0378-1127(97)00077-7

    Notes:
        - Suitable for Scots Pine stands of cultivated origin between ages 10 and 80 years.
        - RMSE: 0.401.
    """

    #Age Validation
    # Check for age (should be a float/int or AgeMeasurement with TOTAL code)
    if isinstance(age, AgeMeasurement):
        # It's an AgeMeasurement, check the code
        if age.code != Age.TOTAL.value:
            raise TypeError("Parameter 'age' must be a float/int or an instance of Age.TOTAL.")
    elif not isinstance(age, (float, int)):
        # It's not an AgeMeasurement and not a float/int
        raise TypeError("Parameter 'age' must be a float/int or an instance of Age.TOTAL.")
    # If we reach here, it's either a valid Age.TOTAL or a float/int - proceed
    if isinstance(age2, AgeMeasurement):
        # It's an AgeMeasurement, check the code
        if age2.code != Age.TOTAL.value:
            raise TypeError("Parameter 'age2' must be a float/int or an instance of Age.TOTAL.")
    elif not isinstance(age2, (float, int)):
        # It's not an AgeMeasurement and not a float/int
        raise TypeError("Parameter 'age2' must be a float/int or an instance of Age.TOTAL.")
    # If we reach here, it's either a valid Age.TOTAL or a float/int - proceed


    # Check for suitability of input ages
    if age < 10 or age2 < 10:
        warnings.warn("Suitable for cultivated stands of Scots Pine between total ages of 10 and 80.")
    if age > 80 or age2 > 80:
        warnings.warn("Suitable for cultivated stands of Scots Pine between total ages of 10 and 80.")

    # Parameters based on the model
    param_asi = 25
    param_beta = 7395.6
    param_b2 = -1.7829

    # Calculations
    d = param_beta * (param_asi**param_b2)
    r = math.sqrt(((dominant_height - d)**2) + (4 * param_beta * dominant_height * (age**param_b2)))

    # Height at target age
    height_at_age2 = ((dominant_height + d + r) /
                      (2 + (4 * param_beta * (age2**param_b2)) / (dominant_height - d + r)))

    return SiteIndexValue(
        value=height_at_age2,
        reference_age=Age.TOTAL(age2),
        species={TreeSpecies.Sweden.pinus_sylvestris},
        fn=elfving_kiviste_1997_height_trajectory_sweden_pine
    )
