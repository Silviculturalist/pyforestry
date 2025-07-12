import warnings
import math
from typing import Union
from pyforestry.helpers.primitives import Age, AgeMeasurement, SiteIndexValue
from pyforestry.helpers.tree_species import TreeSpecies

# Type hints added to signature, return type changed to SiteIndexValue
def eriksson_1997_height_trajectory_sweden_birch(
    dominant_height: float,
    age: Union[float, AgeMeasurement],
    age2: Union[float, AgeMeasurement]
) -> SiteIndexValue:
    """
    Height trajectory for Birch in Sweden based on Eriksson et al. (1997).

    This function estimates the dominant height of Birch stands in Sweden at a given target age,
    based on the dominant height at the initial age. The model is derived from the Hossfeld IV
    growth equation.

    Parameters:
        dominant_height (float): Dominant height of the stand (meters).
        age (Union[float, AgeMeasurement]): Age of the stand at breast height (years). Must be float/int or Age.DBH.
        age2 (Union[float, AgeMeasurement]): Target age at breast height (years). Must be float/int or Age.DBH.

    Returns:
        SiteIndexValue: Estimated dominant height (meters) at age2 wrapped in a SiteIndexValue object.

    Raises:
        Warning: If the input ages are outside the range of suitability (10 to 90 years).
        TypeError: If age or age2 are not float/int or AgeMeasurement with Age.DBH code.

    References:
        Eriksson, H., Johansson, U., Kiviste, A. (1997).
        "A site-index model for pure and mixed stands of Betula pendula and Betula pubescens in Sweden."
        Scandinavian Journal of Forest Research, 12:2, pp. 149-156.
        DOI: https://doi.org/10.1080/02827589709355396

    Notes:
        - Suitable for Birch stands of cultivated origin between ages 10 and 90 years (breast height age).
        - Requires breast height age (Age.DBH).
    """

    # Argument Validation (Existing validation is correct for Age.DBH)
    if isinstance(age, AgeMeasurement):
        if age.code != Age.DBH.value:
            raise TypeError("Parameter 'age' must be a float/int or an instance of Age.DBH.")
        # Added conversion to float for calculations
        age_val = float(age)
    elif isinstance(age, (float, int)):
        # Added conversion to float for calculations
        age_val = float(age)
    else:
        raise TypeError("Parameter 'age' must be a float/int or an instance of Age.DBH.")

    if isinstance(age2, AgeMeasurement):
        if age2.code != Age.DBH.value:
            raise TypeError("Parameter 'age2' must be a float/int or an instance of Age.DBH.")
        # Added conversion to float for calculations
        age2_val = float(age2)
    elif isinstance(age2, (float, int)):
        # Added conversion to float for calculations
        age2_val = float(age2)
    else:
        raise TypeError("Parameter 'age2' must be a float/int or an instance of Age.DBH.")

    # Check for suitability of input ages
    # Use age_val and age2_val
    if age_val < 10 or age2_val < 10:
        warnings.warn("Suitable for cultivated stands of Birch between breast height ages of 10 and 90.")
    if age_val > 90 or age2_val > 90:
        warnings.warn("Suitable for cultivated stands of Birch between breast height ages of 10 and 90.")


    # Model parameters
    param_asi = 7
    param_beta = 394
    param_b2 = 1.387

    # Calculations - use age_val and age2_val
    d = param_beta / (param_asi**param_b2)
    r = math.sqrt(((dominant_height - 1.3 - d)**2) + (4 * param_beta * (dominant_height - 1.3) / (age_val**param_b2)))

    # Height at target age - use age_val and age2_val
    height_at_age2 = (
        ((dominant_height - 1.3 + d + r) /
         (2 + (4 * param_beta * (age2_val**-param_b2)) / (dominant_height - 1.3 - d + r)))
        + 1.3
    )

    # Return statement (already correct, uses age2_val implicitly via height_at_age2 calculation)
    # Use age2_val explicitly for reference_age
    return SiteIndexValue(
        value=height_at_age2,
        reference_age=Age.DBH(age2_val),
        species={TreeSpecies.Sweden.betula_pendula, TreeSpecies.Sweden.betula_pubescens}, # This represents the genus group Betula
        fn=eriksson_1997_height_trajectory_sweden_birch
    )