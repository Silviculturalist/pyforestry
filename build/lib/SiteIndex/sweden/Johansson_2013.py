import warnings
import math

def johansson_2013_height_trajectory_sweden_beech(dominant_height, age, age2):
    """
    Height trajectory for Beech in Sweden based on Johansson et al. (2013).

    Parameters:
        dominant_height (float): Dominant height of the stand (meters).
        age (float): Total age of the stand (years).
        age2 (float): Target age for output height (years).

    Returns:
        float: Dominant height at age2 (meters).

    Raises:
        Warning: If age or age2 is outside the range of 20 to 150 years.

    References:
        Johansson, U., Ekö, P.-M., Elfving, B., Johansson, T., Nilsson, U. (2013).
        "Nya höjdutvecklingskurvor för bonitering." FAKTA SKOG nr. 14.
        https://www.slu.se/globalassets/ew/ew-centrala/forskn/popvet-dok/faktaskog/faktaskog13/faktaskog_14_2013.pdf
    """

    if age < 20 or age2 < 20:
        warnings.warn("Suitable for cultivated stands of Beech between total ages of 20 and 150.")
    if age > 150 or age2 > 150:
        warnings.warn("Suitable for cultivated stands of Beech between total ages of 20 and 150.")

    param_asi = 15
    param_beta = 4239.3
    param_b2 = -1.7753

    d = param_beta * (param_asi ** param_b2)
    r = math.sqrt(((dominant_height - d) ** 2) + (4 * param_beta * dominant_height * (age ** param_b2)))

    return ((dominant_height + d + r) / (2 + (4 * param_beta * (age2 ** param_b2)) / (dominant_height - d + r)))


def johansson_2013_height_trajectory_sweden_hybrid_aspen(dominant_height, age, age2):
    """
    Height trajectory for Hybrid Aspen in Sweden based on Johansson (2013).

    Parameters:
        dominant_height (float): Dominant height of the stand (meters).
        age (float): Total age of the stand (years).
        age2 (float): Target age for output height (years).

    Returns:
        float: Dominant height at age2 (meters).

    Raises:
        Warning: If age or age2 is above 50 years.

    References:
        Johansson, T. (2013). "A site dependent top height growth model for hybrid aspen."
        Journal of Forestry Research, Vol. 24, pp. 691-698.
        https://doi.org/10.1007/s11676-013-0365-6
    """

    if age > 50 or age2 > 50:
        warnings.warn("Suitable for stands of Hybrid Aspen under age of 50.")

    b0 = 2.0381
    b1 = 4692.5
    b2 = 23.1758

    Z0 = dominant_height - b2
    P = Z0 + math.sqrt(Z0 ** 2 + (2 * b1 * dominant_height) / (age ** b0))

    return dominant_height * (((age2 ** b0) * ((age ** b0) * P + b1)) / ((age ** b0) * ((age2 ** b0) * P + b1)))


def johansson_2013_height_trajectory_sweden_larch(dominant_height, age, age2):
    """
    Height trajectory for Larch in Sweden based on Johansson et al. (2013).

    Parameters:
        dominant_height (float): Dominant height of the stand (meters).
        age (float): Total age of the stand (years).
        age2 (float): Target age for output height (years).

    Returns:
        float: Dominant height at age2 (meters).

    Raises:
        Warning: If age or age2 is outside the range of 10 to 100 years.

    References:
        Johansson, U., Ekö, P.-M., Elfving, B., Johansson, T., Nilsson, U. (2013).
        "Nya höjdutvecklingskurvor för bonitering." FAKTA SKOG nr. 14.
        https://www.slu.se/globalassets/ew/ew-centrala/forskn/popvet-dok/faktaskog/faktaskog13/faktaskog_14_2013.pdf
    """

    if age < 10 or age2 < 10:
        warnings.warn("Suitable for cultivated stands of Larch between total ages of 10 and 100.")
    if age > 100 or age2 > 100:
        warnings.warn("Suitable for cultivated stands of Larch between total ages of 10 and 100.")

    param_asi = 17.97
    param_beta = 1529
    param_b2 = -1.3451

    d = param_beta * (param_asi ** param_b2)
    r = math.sqrt(((dominant_height - d) ** 2) + (4 * param_beta * dominant_height * (age ** param_b2)))

    return ((dominant_height + d + r) / (2 + (4 * param_beta * (age2 ** param_b2)) / (dominant_height - d + r)))


def johansson_2013_height_trajectory_sweden_oak(dominant_height, age, age2):
    """
    Height trajectory for Oak in Sweden based on Johansson et al. (2013).

    Parameters:
        dominant_height (float): Dominant height of the stand (meters).
        age (float): Total age of the stand (years).
        age2 (float): Target age for output height (years).

    Returns:
        float: Dominant height at age2 (meters).

    Raises:
        Warning: If age or age2 is outside the range of 20 to 150 years.

    References:
        Johansson, U., Ekö, P.-M., Elfving, B., Johansson, T., Nilsson, U. (2013).
        "Nya höjdutvecklingskurvor för bonitering." FAKTA SKOG nr. 14.
        https://www.slu.se/globalassets/ew/ew-centrala/forskn/popvet-dok/faktaskog/faktaskog13/faktaskog_14_2013.pdf
    """

    if age < 20 or age2 < 20:
        warnings.warn("Suitable for cultivated stands of Oak between total ages of 20 and 150.")
    if age > 150 or age2 > 150:
        warnings.warn("Suitable for cultivated stands of Oak between total ages of 20 and 150.")

    param_asi = 1000
    param_beta = 8841.4
    param_b2 = -1.4317

    d = param_beta * (param_asi ** param_b2)
    r = math.sqrt(((dominant_height - d) ** 2) + (4 * param_beta * dominant_height * (age ** param_b2)))

    return ((dominant_height + d + r) / (2 + (4 * param_beta * (age2 ** param_b2)) / (dominant_height - d + r)))
