import warnings
from math import exp
from typing import Union

from pyforestry.base.helpers import (
    Age, AgeMeasurement, SiteIndexValue, TreeSpecies
)

def hagglund_remrod_1977_height_trajectories_lodgepole_pine(
        dominant_height_m : float,
        age : Union[float, AgeMeasurement],
        age2 : Union[float, AgeMeasurement]) -> SiteIndexValue:
    """
    Hägglund and Remröd (1977): Height growth of Lodgepole Pine (Pinus contorta) in Northern Sweden.
    
    This function computes the height of Lodgepole Pine at a specific age based on dominant height 
    and initial age. The calculations are adapted from the original Chapman-Richards function.

    Parameters:
        dominant_height_m (float): Dominant height of the stand or tree (meters).
        age (float): Age of the stand or tree at breast height (1.3 m).
        age2 (float): Age (DBH) for which the height is to be computed.

    Returns:
        float: Height at age2 in meters.

    Raises:
        Warning: If the input values are outside the material range.

    References:
        Hägglund, B., & Remröd, J. (1977). Övre höjdens utveckling i bestånd med Pinus contorta.
        HUGIN rapport nr. 4.
    """

    if age > 60:
        warnings.warn("Too old stand, outside of the material.")
    if age < 15:
        warnings.warn("Too young stand, outside of the material.")

    #Age Validation
    # Check for age (should be a float/int or AgeMeasurement with DBH code)
    if isinstance(age, AgeMeasurement):
        # It's an AgeMeasurement, check the code
        if age.code != Age.DBH.value:
            raise TypeError("Parameter 'age' must be a float/int or an instance of Age.DBH.")
    elif not isinstance(age, (float, int)):
        # It's not an AgeMeasurement and not a float/int
        raise TypeError("Parameter 'age' must be a float/int or an instance of Age.DBH.")
    # If we reach here, it's either a valid Age.DBH or a float/int - proceed
    if isinstance(age2, AgeMeasurement):
        # It's an AgeMeasurement, check the code
        if age2.code != Age.DBH.value:
            raise TypeError("Parameter 'age2' must be a float/int or an instance of Age.DBH.")
    elif not isinstance(age2, (float, int)):
        # It's not an AgeMeasurement and not a float/int
        raise TypeError("Parameter 'age2' must be a float/int or an instance of Age.DBH.")
    # If we reach here, it's either a valid Age.TOTAL or a float/int - proceed


    # Convert dominant height to decimeters and adjust
    dominant_height_dm = dominant_height_m * 10 - 13

    def subroutine_bonitering(dominant_height, age):
        """
        Subroutine to determine parameters A, RK, and RM2.

        Parameters:
            dominant_height (float): Dominant height in decimeters.
            age (int): Age of the stand or tree at breast height.

        Returns:
            dict: Parameters A, RK, and RM2.
        """
        AI1 = 10
        AI2 = 800
        A, RK, RM2 = 0, 0, 0 #placeholders

        while abs(AI1 - AI2) > 1:
            AI3 = (AI1 + AI2) / 2
            RK = -0.0039105 + 4.7562 * AI3**1.0286 / 10**5
            RK = max(RK, 0.00001)  # Ensure RK is not below the minimum threshold

            RM = 0.076089 - 6.5492 * AI3**1.5627 / 10**6
            RM = min(RM, 0.95)  # Ensure RM does not exceed the maximum threshold

            A = 1.02931 * AI3**0.9958
            RM2 = 1.00414 / (1 - RM)

            # Calculate difference
            DIF = dominant_height - A * (1 - exp(-RK * age))**RM2

            if DIF <= 0:
                AI2 = AI3
            else:
                AI1 = AI3

        return A, RK, RM2

    # Compute parameters using subroutine
    A, RK, RM2 = subroutine_bonitering(dominant_height_dm, age)

    # Compute H50 (height at age 50)
    H50 = A * (1 - exp(-50 * RK))**RM2 + 13

    if H50 > 270:
        warnings.warn("Too high productivity, outside of the material.")
    elif H50 < 140:
        warnings.warn("Too low productivity, outside of the material.")

    # Compute height at age2
    height_at_age2 = (13 + A * (1 - exp(-age2 * RK))**RM2) / 10

    return SiteIndexValue(
        value=height_at_age2,
        reference_age=Age.DBH(age2),
        species={TreeSpecies.Sweden.pinus_contorta},
        fn=hagglund_remrod_1977_height_trajectories_lodgepole_pine
    )
