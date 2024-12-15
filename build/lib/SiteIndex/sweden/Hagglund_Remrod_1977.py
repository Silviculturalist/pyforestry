import warnings
from math import exp

def hagglund_remrod_1977_height_trajectories_lodgepole_pine(dominant_height_m, age, age2):
    """
    Hägglund and Remröd (1977): Height growth of Lodgepole Pine (Pinus contorta) in Northern Sweden.
    
    This function computes the height of Lodgepole Pine at a specific age based on dominant height 
    and initial age. The calculations are adapted from the original Chapman-Richards function.

    Parameters:
        dominant_height_m (float): Dominant height of the stand or tree (meters).
        age (float): Age of the stand or tree at breast height (1.3 m).
        age2 (float): Age for which the height is to be computed.

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

        return {"A": A, "RK": RK, "RM2": RM2}

    # Compute parameters using subroutine
    params = subroutine_bonitering(dominant_height_dm, age)

    # Compute H50 (height at age 50)
    H50 = params["A"] * (1 - exp(-50 * params["RK"]))**params["RM2"] + 13

    if H50 > 270:
        warnings.warn("Too high productivity, outside of the material.")
    elif H50 < 140:
        warnings.warn("Too low productivity, outside of the material.")

    # Compute height at age2
    height_at_age2 = (13 + params["A"] * (1 - exp(-age2 * params["RK"]))**params["RM2"]) / 10

    return height_at_age2
