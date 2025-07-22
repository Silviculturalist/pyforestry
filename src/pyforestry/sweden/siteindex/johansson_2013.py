# Johansson_2013.py

import math
import warnings
from typing import Union

# Imports added
from pyforestry.base.helpers import Age, AgeMeasurement, SiteIndexValue, TreeSpecies


def johansson_2013_height_trajectory_sweden_beech(
    dominant_height: float, age: Union[float, AgeMeasurement], age2: Union[float, AgeMeasurement]
) -> SiteIndexValue:
    """
    Height trajectory for Beech in Sweden based on Johansson et al. (2013).

    Parameters:
        dominant_height (float): Dominant height of the stand (meters).
        age (Union[float, AgeMeasurement]): Total age of the stand (years).
            Must be float/int or Age.TOTAL.
        age2 (Union[float, AgeMeasurement]): Target age for output height (years).
            Must be float/int or Age.TOTAL.

    Returns:
        SiteIndexValue: Dominant height at age2 (meters) wrapped in a SiteIndexValue object.

    Raises:
        Warning: If age or age2 is outside the range of 20 to 150 years.
        TypeError: If age or age2 are not float/int or AgeMeasurement with Age.TOTAL code.

    References:
        Johansson, U., Ekö, P.-M., Elfving, B., Johansson, T., Nilsson, U. (2013).
        "Nya höjdutvecklingskurvor för bonitering." FAKTA SKOG nr. 14.
        https://www.slu.se/globalassets/ew/ew-centrala/forskn/popvet-dok/faktaskog/faktaskog13/faktaskog_14_2013.pdf

    Notes:
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

    # Age range warning
    if age_val < 20 or age2_val < 20:
        warnings.warn(
            "Suitable for cultivated stands of Beech between total ages of 20 and 150.",
            stacklevel=2,
        )
    if age_val > 150 or age2_val > 150:
        warnings.warn(
            "Suitable for cultivated stands of Beech between total ages of 20 and 150.",
            stacklevel=2,
        )

    # Model parameters
    param_asi = 15
    param_beta = 4239.3
    param_b2 = -1.7753

    d = param_beta * (param_asi**param_b2)
    r = math.sqrt(
        ((dominant_height - d) ** 2) + (4 * param_beta * dominant_height * (age_val**param_b2))
    )

    height_at_age2 = (dominant_height + d + r) / (
        2 + (4 * param_beta * (age2_val**param_b2)) / (dominant_height - d + r)
    )

    # Return modified to SiteIndexValue
    return SiteIndexValue(
        value=height_at_age2,
        reference_age=Age.TOTAL(age2_val),
        species={TreeSpecies.Sweden.fagus_sylvatica},
        fn=johansson_2013_height_trajectory_sweden_beech,
    )


def johansson_2013_height_trajectory_sweden_hybrid_aspen(
    dominant_height: float, age: Union[float, AgeMeasurement], age2: Union[float, AgeMeasurement]
) -> SiteIndexValue:
    """
    Height trajectory for Hybrid Aspen in Sweden based on Johansson (2013).

    Parameters:
        dominant_height (float): Dominant height of the stand (meters).
        age (Union[float, AgeMeasurement]): Total age of the stand (years).
            Must be float/int or Age.TOTAL.
        age2 (Union[float, AgeMeasurement]): Target age for output height (years).
            Must be float/int or Age.TOTAL.

    Returns:
        SiteIndexValue: Dominant height at age2 (meters) wrapped in a SiteIndexValue object.

    Raises:
        Warning: If age or age2 is above 50 years.
        TypeError: If age or age2 are not float/int or AgeMeasurement with Age.TOTAL code.

    References:
        Johansson, T. (2013). "A site dependent top height growth model for hybrid aspen."
        Journal of Forestry Research, Vol. 24, pp. 691-698.
        https://doi.org/10.1007/s11676-013-0365-6

    Notes:
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

    # Age range warning
    if age_val > 50 or age2_val > 50:
        warnings.warn("Suitable for stands of Hybrid Aspen under age of 50.", stacklevel=2)

    # Model parameters
    b0 = 2.0381
    b1 = 4692.5
    b2 = 23.1758

    Z0 = dominant_height - b2
    P = Z0 + math.sqrt(Z0**2 + (2 * b1 * dominant_height) / (age_val**b0))

    height_at_age2 = dominant_height * (
        ((age2_val**b0) * ((age_val**b0) * P + b1)) / ((age_val**b0) * ((age2_val**b0) * P + b1))
    )

    # Return modified to SiteIndexValue
    return SiteIndexValue(
        value=height_at_age2,
        reference_age=Age.TOTAL(age2_val),
        species={TreeSpecies.Sweden.populus_tremula_x_tremuloides},  # TODO : Check if valid.
        fn=johansson_2013_height_trajectory_sweden_hybrid_aspen,
    )


def johansson_2013_height_trajectory_sweden_larch(
    dominant_height: float, age: Union[float, AgeMeasurement], age2: Union[float, AgeMeasurement]
) -> SiteIndexValue:
    """
    Height trajectory for Larch in Sweden based on Johansson et al. (2013).

    Parameters:
        dominant_height (float): Dominant height of the stand (meters).
        age (Union[float, AgeMeasurement]): Total age of the stand (years).
            Must be float/int or Age.TOTAL.
        age2 (Union[float, AgeMeasurement]): Target age for output height (years).
            Must be float/int or Age.TOTAL.

    Returns:
        SiteIndexValue: Dominant height at age2 (meters) wrapped in a SiteIndexValue object.

    Raises:
        Warning: If age or age2 is outside the range of 10 to 100 years.
        TypeError: If age or age2 are not float/int or AgeMeasurement with Age.TOTAL code.

    References:
        Johansson, U., Ekö, P.-M., Elfving, B., Johansson, T., Nilsson, U. (2013).
        "Nya höjdutvecklingskurvor för bonitering." FAKTA SKOG nr. 14.
        https://www.slu.se/globalassets/ew/ew-centrala/forskn/popvet-dok/faktaskog/faktaskog13/faktaskog_14_2013.pdf

    Notes:
        - Requires total age (Age.TOTAL).
        - Assigns TreeSpecies.Sweden.larix_sibirica as the species.
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

    # Age range warning
    if age_val < 10 or age2_val < 10:
        warnings.warn(
            "Suitable for cultivated stands of Larch between total ages of 10 and 100.",
            stacklevel=2,
        )
    if age_val > 100 or age2_val > 100:
        warnings.warn(
            "Suitable for cultivated stands of Larch between total ages of 10 and 100.",
            stacklevel=2,
        )

    # Model parameters
    param_asi = 17.97
    param_beta = 1529
    param_b2 = -1.3451

    d = param_beta * (param_asi**param_b2)
    r = math.sqrt(
        ((dominant_height - d) ** 2) + (4 * param_beta * dominant_height * (age_val**param_b2))
    )

    height_at_age2 = (dominant_height + d + r) / (
        2 + (4 * param_beta * (age2_val**param_b2)) / (dominant_height - d + r)
    )

    # Return modified to SiteIndexValue (Using Larix sibirica as representative)
    return SiteIndexValue(
        value=height_at_age2,
        reference_age=Age.TOTAL(age2_val),
        species={TreeSpecies.Sweden.larix_sibirica},
        fn=johansson_2013_height_trajectory_sweden_larch,
    )


def johansson_2013_height_trajectory_sweden_oak(
    dominant_height: float, age: Union[float, AgeMeasurement], age2: Union[float, AgeMeasurement]
) -> SiteIndexValue:
    """
    Height trajectory for Oak in Sweden based on Johansson et al. (2013).

    Parameters:
        dominant_height (float): Dominant height of the stand (meters).
        age (Union[float, AgeMeasurement]): Total age of the stand (years).
            Must be float/int or Age.TOTAL.
        age2 (Union[float, AgeMeasurement]): Target age for output height (years).
            Must be float/int or Age.TOTAL.

    Returns:
        SiteIndexValue: Dominant height at age2 (meters) wrapped in a SiteIndexValue object.

    Raises:
        Warning: If age or age2 is outside the range of 20 to 150 years.
        TypeError: If age or age2 are not float/int or AgeMeasurement with Age.TOTAL code.

    References:
        Johansson, U., Ekö, P.-M., Elfving, B., Johansson, T., Nilsson, U. (2013).
        "Nya höjdutvecklingskurvor för bonitering." FAKTA SKOG nr. 14.
        https://www.slu.se/globalassets/ew/ew-centrala/forskn/popvet-dok/faktaskog/faktaskog13/faktaskog_14_2013.pdf

    Notes:
        - Requires total age (Age.TOTAL).
        - Assigns TreeSpecies.Sweden.quercus_robur as the species.
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

    # Age range warning
    if age_val < 20 or age2_val < 20:
        warnings.warn(
            "Suitable for cultivated stands of Oak between total ages of 20 and 150.", stacklevel=2
        )
    if age_val > 150 or age2_val > 150:
        warnings.warn(
            "Suitable for cultivated stands of Oak between total ages of 20 and 150.", stacklevel=2
        )

    # Model parameters
    param_asi = 1000
    param_beta = 8841.4
    param_b2 = -1.4317

    d = param_beta * (param_asi**param_b2)
    r = math.sqrt(
        ((dominant_height - d) ** 2) + (4 * param_beta * dominant_height * (age_val**param_b2))
    )

    height_at_age2 = (dominant_height + d + r) / (
        2 + (4 * param_beta * (age2_val**param_b2)) / (dominant_height - d + r)
    )

    # Return modified to SiteIndexValue (Using Quercus robur as representative)
    return SiteIndexValue(
        value=height_at_age2,
        reference_age=Age.TOTAL(age2_val),
        species={TreeSpecies.Sweden.quercus_robur},
        fn=johansson_2013_height_trajectory_sweden_oak,
    )
