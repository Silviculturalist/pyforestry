# This code should watch : https://github.com/SmartForest-no/taperNOR/blob/b7a826f3eb9856f7201705e832b385484161ff9f/R/barkNOR.R [PERMALINK]
# for changes.
# MODIFIED  FROM ABOVE LINK TO INCLUDE SAFETY CHECKS AND TRANSLATE TO PYTHON.

# MIT LICENSE
#Copyright (c) 2022 taperNOR authors
#Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.




import warnings
from typing import Union
# Assuming Munin paths are correctly configured for import
from Munin.Helpers.Base import Diameter_cm

# --- Norway Spruce Function ---

def hansen_2023_norway_spruce_norway_bark_thickness(
    diameter_cm: Union[float, Diameter_cm],
    diameter_desired_cm: float
) -> float:
    """
    Calculates double bark thickness for Norway Spruce in Norway (Hansen et al., 2023).

    Estimates bark thickness based on diameter at breast height (DBH) and the
    diameter at the point where bark thickness is desired.

    Args:
        diameter_cm (Union[float, Diameter_cm]): Diameter at breast height (1.3m)
            over bark, in centimeters. If Diameter_cm object is passed, it must
            be over_bark=True.
        diameter_desired_cm (float): Diameter over bark at the point of interest
            along the stem, in centimeters.

    Returns:
        float: Estimated double bark thickness in centimeters at the point
               corresponding to `diameter_desired_cm`. Returns 0 if inputs are
               non-positive.

    Raises:
        ValueError: If inputs are negative.
        TypeError: If input types are invalid.

    References:
        Hansen, E., Rahlf, J., Astrup, R., & Gobakken, T. (2023). Taper, volume,
        and bark thickness models for spruce, pine, and birch in Norway.
        Scandinavian Journal of Forest Research, 38(6), 413–428.
        https://doi.org/10.1080/02827581.2023.2243821
        Formula: db_cm = 0.2324 + 0.0068 * dbh_cm + 0.0399 * dia_desired_cm

    Notes:
        - The function returns DOUBLE bark thickness in CENTIMETERS.
        - Applicable to Picea abies in Norway.
    """
    # --- Input Validation ---
    if isinstance(diameter_cm, Diameter_cm):
        if diameter_cm.measurement_height_m != 1.3:
             warnings.warn(f"Input 'diameter_cm' (Diameter_cm) has measurement height {diameter_cm.measurement_height_m}m, model assumes 1.3m.")
        if not diameter_cm.over_bark:
             raise ValueError("Input 'diameter_cm' (Diameter_cm) must be measured over bark.")
        dbh_cm_val = float(diameter_cm)
    elif isinstance(diameter_cm, (float, int)):
        dbh_cm_val = float(diameter_cm)
    else:
        raise TypeError("Input 'diameter_cm' must be a float, int, or Diameter_cm object.")

    if not isinstance(diameter_desired_cm, (float, int)):
        raise TypeError("Input 'diameter_desired_cm' must be a number (float or int).")
    dia_desired_cm_val = float(diameter_desired_cm)

    if dbh_cm_val < 0:
        raise ValueError("Input 'diameter_cm' must be non-negative.")
    if dia_desired_cm_val < 0:
         raise ValueError("Input 'diameter_desired_cm' must be non-negative.")

    # Handle cases where diameters are zero
    if dbh_cm_val <= 0 or dia_desired_cm_val <= 0:
        return 0.0

    # --- Calculation ---
    # Formula: db_cm = 0.2324 + 0.0068 * dbh_cm + 0.0399 * dia_desired_cm
    double_bark_cm = 0.2324 + 0.0068 * dbh_cm_val + 0.0399 * dia_desired_cm_val

    # Ensure non-negative return
    return max(0.0, double_bark_cm)


# --- Scots Pine Function ---

def hansen_2023_scots_pine_norway_bark_thickness(
    diameter_cm: Union[float, Diameter_cm],
    diameter_desired_cm: float
) -> float:
    """
    Calculates double bark thickness for Scots Pine in Norway (Hansen et al., 2023).

    Estimates bark thickness based on diameter at breast height (DBH) and the
    diameter at the point where bark thickness is desired.

    Args:
        diameter_cm (Union[float, Diameter_cm]): Diameter at breast height (1.3m)
            over bark, in centimeters. If Diameter_cm object is passed, it must
            be over_bark=True.
        diameter_desired_cm (float): Diameter over bark at the point of interest
            along the stem, in centimeters.

    Returns:
        float: Estimated double bark thickness in centimeters at the point
               corresponding to `diameter_desired_cm`. Returns 0 if inputs are
               non-positive.

    Raises:
        ValueError: If inputs are negative.
        TypeError: If input types are invalid.

    References:
        Hansen, E., Rahlf, J., Astrup, R., & Gobakken, T. (2023). Taper, volume,
        and bark thickness models for spruce, pine, and birch in Norway.
        Scandinavian Journal of Forest Research, 38(6), 413–428.
        https://doi.org/10.1080/02827581.2023.2243821
        Formula: db_cm = 0.2931 - 0.0405 * dbh_cm + 0.1213 * dia_desired_cm

    Notes:
        - The function returns DOUBLE bark thickness in CENTIMETERS.
        - Applicable to Pinus sylvestris in Norway.
    """
    # --- Input Validation ---
    if isinstance(diameter_cm, Diameter_cm):
        if diameter_cm.measurement_height_m != 1.3:
             warnings.warn(f"Input 'diameter_cm' (Diameter_cm) has measurement height {diameter_cm.measurement_height_m}m, model assumes 1.3m.")
        if not diameter_cm.over_bark:
             raise ValueError("Input 'diameter_cm' (Diameter_cm) must be measured over bark.")
        dbh_cm_val = float(diameter_cm)
    elif isinstance(diameter_cm, (float, int)):
        dbh_cm_val = float(diameter_cm)
    else:
        raise TypeError("Input 'diameter_cm' must be a float, int, or Diameter_cm object.")

    if not isinstance(diameter_desired_cm, (float, int)):
        raise TypeError("Input 'diameter_desired_cm' must be a number (float or int).")
    dia_desired_cm_val = float(diameter_desired_cm)

    if dbh_cm_val < 0:
        raise ValueError("Input 'diameter_cm' must be non-negative.")
    if dia_desired_cm_val < 0:
         raise ValueError("Input 'diameter_desired_cm' must be non-negative.")

    # Handle cases where diameters are zero
    if dbh_cm_val <= 0 or dia_desired_cm_val <= 0:
        return 0.0

    # --- Calculation ---
    # Formula: db_cm = 0.2931 - 0.0405 * dbh_cm + 0.1213 * dia_desired_cm
    double_bark_cm = 0.2931 - 0.0405 * dbh_cm_val + 0.1213 * dia_desired_cm_val

    # Ensure non-negative return
    return max(0.0, double_bark_cm)


# --- Birch Function ---

def hansen_2023_birch_norway_bark_thickness(
    diameter_cm: Union[float, Diameter_cm],
    diameter_desired_cm: float
) -> float:
    """
    Calculates double bark thickness for Birch (Betula spp.) in Norway (Hansen et al., 2023).

    Estimates bark thickness based on diameter at breast height (DBH) and the
    diameter at the point where bark thickness is desired.

    Args:
        diameter_cm (Union[float, Diameter_cm]): Diameter at breast height (1.3m)
            over bark, in centimeters. If Diameter_cm object is passed, it must
            be over_bark=True.
        diameter_desired_cm (float): Diameter over bark at the point of interest
            along the stem, in centimeters.

    Returns:
        float: Estimated double bark thickness in centimeters at the point
               corresponding to `diameter_desired_cm`. Returns 0 if inputs are
               non-positive.

    Raises:
        ValueError: If inputs are negative.
        TypeError: If input types are invalid.

    References:
        Hansen, E., Rahlf, J., Astrup, R., & Gobakken, T. (2023). Taper, volume,
        and bark thickness models for spruce, pine, and birch in Norway.
        Scandinavian Journal of Forest Research, 38(6), 413–428.
        https://doi.org/10.1080/02827581.2023.2243821
        Formula: db_cm = -0.0483 + 0.0050 * dbh_cm + 0.0846 * dia_desired_cm

    Notes:
        - The function returns DOUBLE bark thickness in CENTIMETERS.
        - Applicable to Betula spp. (e.g., B. pendula, B. pubescens) in Norway.
    """
    # --- Input Validation ---
    if isinstance(diameter_cm, Diameter_cm):
        if diameter_cm.measurement_height_m != 1.3:
             warnings.warn(f"Input 'diameter_cm' (Diameter_cm) has measurement height {diameter_cm.measurement_height_m}m, model assumes 1.3m.")
        if not diameter_cm.over_bark:
             raise ValueError("Input 'diameter_cm' (Diameter_cm) must be measured over bark.")
        dbh_cm_val = float(diameter_cm)
    elif isinstance(diameter_cm, (float, int)):
        dbh_cm_val = float(diameter_cm)
    else:
        raise TypeError("Input 'diameter_cm' must be a float, int, or Diameter_cm object.")

    if not isinstance(diameter_desired_cm, (float, int)):
        raise TypeError("Input 'diameter_desired_cm' must be a number (float or int).")
    dia_desired_cm_val = float(diameter_desired_cm)

    if dbh_cm_val < 0:
        raise ValueError("Input 'diameter_cm' must be non-negative.")
    if dia_desired_cm_val < 0:
         raise ValueError("Input 'diameter_desired_cm' must be non-negative.")

    # Handle cases where diameters are zero
    if dbh_cm_val <= 0 or dia_desired_cm_val <= 0:
        return 0.0

    # --- Calculation ---
    # Formula: db_cm = -0.0483 + 0.0050 * dbh_cm + 0.0846 * dia_desired_cm
    double_bark_cm = -0.0483 + 0.0050 * dbh_cm_val + 0.0846 * dia_desired_cm_val

    # Ensure non-negative return
    return max(0.0, double_bark_cm)
