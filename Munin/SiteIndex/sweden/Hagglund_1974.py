from math import log, exp

def hagglund_1974_sweden_height_trajectories_pine(dominant_height, age, age2, regeneration="culture"):
    """
    Hägglund 1974: Height growth of Scots Pine in Sweden.

    This function calculates the height of Scots Pine based on the Chapman-Richards 
    function and site-specific parameters. It is adapted from the Fortran IV script 
    in the original Hägglund 1974 source. The implementation accounts for warnings 
    when values are outside the material limits but does not halt execution.

    OBSERVE: Site index according to Hägglund is measured in total age.

    Parameters:
        dominant_height (float): Top height of the tree or stand in meters.
        age (int): Age of the stand or tree at breast height (1.3 m).
        age2 (int): The age for which the height along the same curve is to be computed.
        regeneration (str): Method of stand establishment, one of "culture", "natural", or "unknown".

    Returns:
        float: Height at age2 in meters,
        float: Time estimate to reach breast height.

    Raises:
        ValueError: If the `regeneration` argument is not one of "culture", "natural", or "unknown".
        Warning: If the stand age, productivity, or height are outside the material limits.

    References:
        Hägglund, Björn (1974) Övre höjdens utveckling i tallbestånd:
        Site index curves for Scots Pine in Sweden. Dept.
        of Forest Yield Research. Royal College of Forestry. Report 31. 54 pp. Stockholm.
    """

    if regeneration not in ["culture", "natural", "unknown"]:
        raise ValueError("Argument 'regeneration' must be one of 'culture', 'natural', or 'unknown'.")

    top_height_dm = dominant_height * 10 - 13  # Convert to decimeters and adjust

    if age > 120:
        print("Warning: Too old stand, outside of the material.")

    def subroutine_bonitering(top_height, age, regeneration):
        AI1, AI2 = 10, 600

        while abs(AI1 - AI2) > 1:
            AI3 = (AI1 + AI2) / 2
            RM = 0.066074 + 4.4189e5 / AI3**2.9134
            RM = min(RM, 0.95)

            RM2 = 1.0 / (1 - RM)
            RK = 1.0002e-4 + 9.5953 * AI3**1.3755 / 1e6
            RK = max(RK, 0.0001)

            A2 = 1.0075 * AI3
            DIF = top_height-A2*(1-exp(-age*RK))**RM2

            if DIF <= 0:
                AI2 = AI3
            else:
                AI1 = AI3

        T26 = (-1 / RK) * log(1 - pow(13 / A2, 1 / RM2))
        T262 = T26**2

        if regeneration == "natural":
            T13 = 7.4624 + 0.11672 * T262
        elif regeneration == "unknown":
            T13 = 6.8889 + 0.12405 * T262
        elif regeneration == "culture":
            T13 = 7.4624 + 0.11672 * T262 - 0.39276 * T26

        T13 = min(T13, 50)

        return {"A2": A2, "RK": RK, "RM2": RM2, "T13": T13}

    params = subroutine_bonitering(top_height_dm, age, regeneration)

    if params["A2"] > 311:
        print("Warning: Too high productivity, outside of the material.")
    if params["A2"] < 180:
        print("Warning: Too low productivity, outside of the material.")
    if params["A2"] > 250 and age > 100:
        print("Warning: Too old stand, outside of material.")

    # Return Height at age2
    return (13 + params["A2"] * (1 - exp(-age2 * params["RK"]))**params["RM2"]) / 10, params['T13']
