import math
import warnings
from typing import Union

from pyforestry.base.helpers.primitives import Diameter_cm

# --- Scots Pine Function ---


def Hannrup_2004_bark_pinus_sylvestris_sweden(
    diameter_breast_height_mm: Union[float, Diameter_cm], latitude: float, stem_height_cm: float
) -> float:
    """
    Calculates double bark thickness at a given stem height for Scots Pine in Sweden.

    Based on the "Sf_tall" function presented in Skogforsk Arbetsrapport 575-2004.

    Args:
        diameter_breast_height_mm (Union[float, Diameter_cm]): Diameter at breast
            height (1.3m) over bark, in millimeters. If Diameter_cm is passed,
            it will be converted to mm. Diameters over 590mm are capped at 590mm
            internally for the calculation.
        latitude (float): Latitude in decimal degrees (e.g., 63.82).
        stem_height_cm (float): The height along the stem (from ground level)
            where bark thickness is desired, in centimeters.

    Returns:
        float: Estimated double bark thickness at the specified `stem_height_cm`,
               in millimeters. Minimum value returned is 2 mm.

    Raises:
        ValueError: If inputs are outside reasonable ranges (e.g., negative diameter,
                    invalid latitude, negative stem height).
        TypeError: If diameter input type is invalid.

    References:
        Hannrup, Björn. (2004). Funktioner för skattning av barkens tjocklek hos
        tall och gran vid avverkning med skördare [Functions for estimating bark
        thickness of Scots pine and Norway spruce at harvester felling].
        Arbetsrapport 575. Skogforsk. Uppsala Science Park, Sweden. 34 pp.
        ISSN: 1404-305X.
        Available Online [2025-04-17]: https://www.skogforsk.se/contentassets/960ad964391d489785f97f9eaeeaf174/arbetsrapport-575-2004.pdf

    Notes:
        - This function calculates bark thickness at any point along the stem height,
          not just at breast height.
        - It requires latitude as an input.
        - The function returns DOUBLE bark thickness in MILLIMETERS.
        - Only applicable to Pinus sylvestris in Sweden.
    """
    # --- Input Validation ---
    if isinstance(diameter_breast_height_mm, Diameter_cm):
        if diameter_breast_height_mm.measurement_height_m != 1.3:
            warnings.warn(
                "Input 'diameter_breast_height_mm' (Diameter_cm) has measurement"
                f"height {diameter_breast_height_mm.measurement_height_m}m, model assumes 1.3m.",
                stacklevel=2,
            )
        if not diameter_breast_height_mm.over_bark:
            raise ValueError(
                "Input 'diameter_breast_height_mm' (Diameter_cm) must be measured over bark."
            )
        dbh_mm = float(diameter_breast_height_mm) * 10.0  # Convert cm to mm
    elif isinstance(diameter_breast_height_mm, (float, int)):
        dbh_mm = float(diameter_breast_height_mm)
    else:
        raise TypeError(
            "Input 'diameter_breast_height_mm' must be a float, int, or Diameter_cm object."
        )

    if dbh_mm < 0:
        raise ValueError("Input 'diameter_breast_height_mm' must be non-negative.")
    # Latitude check (approximate range for Sweden)
    if not (55.0 <= latitude <= 70.0):
        warnings.warn(
            f"Latitude {latitude} is outside the typical range for Sweden (55-70)."
            "Results may be extrapolated.",
            stacklevel=2,
        )
    if stem_height_cm < 0:
        raise ValueError("Input 'stem_height_cm' must be non-negative.")

    # --- Calculation Steps ---

    # Step 1: Cap DBH at 590 mm
    dbh_b = min(dbh_mm, 590.0)

    # Step 2: Calculate breakpoint height (htg in cm)
    term_lat = 72.1814 + 0.0789 * dbh_b - 0.9868 * latitude
    term_exp_coeff = 0.0078557 - 0.0000132 * dbh_b

    if term_lat <= 0:
        warnings.warn(
            f"Pine Bark: Term (72.1814 + 0.0789*dbh_b - 0.9868*lat) = {term_lat:.4f} <= 0. "
            "Cannot calculate htg. Returning minimum bark.",
            stacklevel=2,
        )
        return 2.0
    if abs(term_exp_coeff) < 1e-9:
        warnings.warn(
            f"Pine Bark: Term (0.0078557 - 0.0000132*dbh_b) = {term_exp_coeff:.7f} is close "
            "to zero. Cannot reliably calculate htg. Returning minimum bark.",
            stacklevel=2,
        )
        return 2.0

    try:
        htg = -math.log(0.12 / term_lat) / term_exp_coeff
    except (ValueError, ZeroDivisionError) as e:
        warnings.warn(
            "Pine Bark: Math error calculating htg (likely log of non-positive or division "
            f"by zero): {e}. Returning minimum bark.",
            stacklevel=2,
        )
        return 2.0

    # Step 3 & 4: Calculate double bark thickness (db in mm) based on h vs htg
    h = stem_height_cm
    db_mm = 0.0

    if h <= htg:
        try:
            exponent = -term_exp_coeff * h
            exponent = max(exponent, -700)  # Avoid exp() overflow
            db_mm = 3.5808 + 0.0109 * dbh_b + term_lat * math.exp(exponent)
        except OverflowError:
            warnings.warn(
                f"Pine Bark: Math OverflowError calculating exp term below htg. h={h}, htg={htg}. "
                "Returning minimum bark.",
                stacklevel=2,
            )
            db_mm = 2.0
        except ValueError as e:
            warnings.warn(
                f"Pine Bark: Math ValueError calculating bark below htg: {e}. Returning minimum "
                "bark.",
                stacklevel=2,
            )
            db_mm = 2.0
    else:  # h > htg
        db_mm = 3.5808 + 0.0109 * dbh_b + 0.12 - 0.005 * (h - htg)

    # Step 5: Apply minimum double bark thickness (2 mm)
    db_mm_final = max(db_mm, 2.0)

    return db_mm_final


# --- Norway Spruce Function ---


def Hannrup_2004_bark_picea_abies_sweden(
    diameter_at_height_mm: float, diameter_breast_height_mm: Union[float, Diameter_cm]
) -> float:
    """
    Calculates double bark thickness for Norway Spruce in Sweden based on diameter.

    Based on the function presented in Skogforsk Arbetsrapport 575-2004.

    Args:
        diameter_at_height_mm (float): Diameter over bark at the point of interest
            along the stem, in millimeters.
        diameter_breast_height_mm (Union[float, Diameter_cm]): Diameter at breast
            height (1.3m) over bark, in millimeters. Must be in the same units
            as diameter_at_height_mm. If Diameter_cm is passed, it's converted to mm.

    Returns:
        float: Estimated double bark thickness at the point corresponding to
               `diameter_at_height_mm`, in millimeters. Minimum value is 2 mm.

    Raises:
        ValueError: If inputs are non-positive or dbh is zero.
        TypeError: If diameter input types are invalid.

    References:
        Hannrup, Björn. (2004). Funktioner för skattning av barkens tjocklek hos
        tall och gran vid avverkning med skördare [Functions for estimating bark
        thickness of Scots pine and Norway spruce at harvester felling].
        Arbetsrapport 575. Skogforsk. Uppsala Science Park, Sweden. 34 pp.
        ISSN: 1404-305X.
        Available Online [2025-04-17]: https://www.skogforsk.se/contentassets/960ad964391d489785f97f9eaeeaf174/arbetsrapport-575-2004.pdf

    Notes:
        - This function calculates bark thickness based on the diameter at a given
          point relative to the breast height diameter. It does not directly use
          stem height or latitude.
        - The function returns DOUBLE bark thickness in MILLIMETERS.
        - Only applicable to Picea abies in Sweden.
    """
    # --- Input Validation ---
    if not isinstance(diameter_at_height_mm, (float, int)):
        raise TypeError("Input 'diameter_at_height_mm' must be a number (float or int).")
    if diameter_at_height_mm < 0:
        raise ValueError("Input 'diameter_at_height_mm' must be non-negative.")

    if isinstance(diameter_breast_height_mm, Diameter_cm):
        if diameter_breast_height_mm.measurement_height_m != 1.3:
            warnings.warn(
                "Input 'diameter_breast_height_mm' (Diameter_cm) has "
                f"measurement height {diameter_breast_height_mm.measurement_height_m}m, "
                "model assumes 1.3m.",
                stacklevel=2,
            )
        if not diameter_breast_height_mm.over_bark:
            raise ValueError(
                "Input 'diameter_breast_height_mm' (Diameter_cm) must be measured over bark."
            )
        dbh_mm = float(diameter_breast_height_mm) * 10.0  # Convert cm to mm
    elif isinstance(diameter_breast_height_mm, (float, int)):
        dbh_mm = float(diameter_breast_height_mm)
    else:
        raise TypeError(
            "Input 'diameter_breast_height_mm' must be a float, int, or Diameter_cm object."
        )

    if dbh_mm <= 0:
        raise ValueError(
            "Input 'diameter_breast_height_mm' must be positive for relative diameter calculation."
        )

    # --- Calculation Steps ---
    dia_mm = float(diameter_at_height_mm)  # Ensure float

    # Step 1: Calculate relative diameter
    # Avoid division by zero (already checked dbh_mm > 0)
    reldia = dia_mm / dbh_mm

    # Step 2: Calculate double bark thickness (db in mm)
    db_mm = 0.46146 + 0.01386 * dbh_mm + 0.03571 * dbh_mm * reldia

    # Step 3: Apply minimum double bark thickness (2 mm)
    db_mm_final = max(db_mm, 2.0)

    return db_mm_final
