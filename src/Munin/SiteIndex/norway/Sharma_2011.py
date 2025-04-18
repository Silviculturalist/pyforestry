# Sharma2011.py

import math
import warnings
from typing import Set

from Munin.Helpers.Primitives import SiteIndexValue, Age, AgeMeasurement
from Munin.Helpers.TreeSpecies import TreeName, PICEA_ABIES, PINUS_SYLVESTRIS


# =============================================================================
# Internal Model Implementations (Translating R code)
# =============================================================================

class SharmaSpruceModel:
    """
    Implements Sharma's (2011) model for Norway Spruce (Picea abies) in Norway.
    """
    SPECIES: Set[TreeName] = {PICEA_ABIES}
    B1 = 18.9206
    B2 = 5175.18
    B3 = 1.1576

    @staticmethod
    def _height_trajectory_spruce(dominant_height_m: float,
                                  age_dbh: float,
                                  age2_dbh: float) -> float:
        """
        Internal calculation based on Sharma et al. 2011 for Spruce.
        Assumes age and age2 are DBH and positive.

        Args:
            dominant_height_m: Dominant height (m) at age_dbh.
            age_dbh: Stand age at breast height (>0).
            age2_dbh: Target age at breast height (>0) for height prediction.

        Returns:
            Predicted dominant height (m) at age2_dbh. Returns NaN on calculation error.
        """
        if dominant_height_m <= 1.3:
             warnings.warn("Dominant height must be > 1.3m for Sharma 2011 model.", stacklevel=3)
             return 1.3 # Or NaN, or raise error

        try:
            theta = (dominant_height_m - 1.3) - SharmaSpruceModel.B1
            # Calculate term inside sqrt carefully
            age_pow_neg_b3 = age_dbh ** (-SharmaSpruceModel.B3)
            term_in_sqrt = 4 * SharmaSpruceModel.B2 * (dominant_height_m - 1.3) * age_pow_neg_b3
            
            sqrt_arg = theta**2 + term_in_sqrt
            if sqrt_arg < 0:
                 warnings.warn(f"Negative value encountered under square root ({sqrt_arg:.2f}) "
                               f"in Sharma Spruce model. Check inputs (H={dominant_height_m}, Age={age_dbh}).", stacklevel=3)
                 return float('nan')

            X = 0.5 * (theta + math.sqrt(sqrt_arg))

            # Avoid division by zero if X is very small
            if abs(X) < 1e-9:
                 warnings.warn("Intermediate value X is near zero in Sharma Spruce model. Result may be unstable.", stacklevel=3)
                 # Depending on context, might return NaN or estimate based on limits
                 return float('nan') # Return NaN as a safe default

            # Calculate the final height
            age2_pow_neg_b3 = age2_dbh ** (-SharmaSpruceModel.B3)
            denominator = (1 + SharmaSpruceModel.B2 / X * age2_pow_neg_b3)

            # Avoid division by zero in the final step
            if abs(denominator) < 1e-9:
                 warnings.warn("Denominator near zero in Sharma Spruce model final step. Result may be unstable.", stacklevel=3)
                 return float('nan')

            height2 = (SharmaSpruceModel.B1 + X) / denominator + 1.3

        except (ValueError, OverflowError) as e:
            warnings.warn(f"Calculation error in Sharma Spruce model: {e}. "
                          f"Inputs: H={dominant_height_m}, Age={age_dbh}, Age2={age2_dbh}", stacklevel=3)
            return float('nan')

        return height2

    # --- Public facing method ---
    @staticmethod
    def norway_ht(dominant_height_m: float,
                  age: AgeMeasurement,
                  age2: AgeMeasurement) -> SiteIndexValue:
        """
        Calculates the height trajectory of Norway Spruce in Norway based on Sharma et al. (2011).

        IMPORTANT: This function requires age and age2 to be specified as Age.DBH
                   (age at breast height), matching the original Sharma function.

        Args:
            dominant_height_m: Dominant height (m) at 'age'. Must be > 1.3m.
            age: Stand age at breast height (must be Age.DBH and > 0).
            age2: Target age at breast height (must be Age.DBH and > 0) for height prediction.

        Returns:
            SiteIndexValue: Contains the predicted dominant height (m) at age2.
                            The .reference_age attribute is age2 (DBH).
                            Returns NaN height if calculation fails.

        Raises:
            TypeError: If age or age2 are not Age.DBH.
            ValueError: If ages are non-positive.
        """
        if not isinstance(age, AgeMeasurement) or age.code != Age.DBH.value:
            raise TypeError("Input 'age' must be specified as Age.DBH for Sharma's height trajectory.")
        if not isinstance(age2, AgeMeasurement) or age2.code != Age.DBH.value:
            raise TypeError("Input 'age2' must be specified as Age.DBH for Sharma's height trajectory.")

        age_dbh_val = float(age)
        age2_dbh_val = float(age2)

        if age_dbh_val <= 0 or age2_dbh_val <= 0:
            raise ValueError("Ages must be positive for Sharma's height trajectory.")
        if dominant_height_m <= 1.3:
             raise ValueError("Dominant height must be > 1.3m for Sharma's height trajectory.")


        predicted_height = SharmaSpruceModel._height_trajectory_spruce(
            dominant_height_m, age_dbh_val, age2_dbh_val
        )

        return SiteIndexValue(
            value=predicted_height,
            reference_age=age2, # Keep the AgeMeasurement object (DBH)
            species=SharmaSpruceModel.SPECIES,
            fn=Sharma2011.height_trajectory.picea_abies
        )


class SharmaPineModel:
    """
    Implements Sharma's (2011) model for Scots Pine (Pinus sylvestris) in Norway.
    """
    SPECIES: Set[TreeName] = {PINUS_SYLVESTRIS}
    B1 = 12.8361
    B2 = 3263.99
    B3 = 1.1758

    @staticmethod
    def _height_trajectory_pine(dominant_height_m: float,
                                age_dbh: float,
                                age2_dbh: float) -> float:
        """
        Internal calculation based on Sharma et al. 2011 for Pine.
        Assumes age and age2 are DBH and positive.

        Args:
            dominant_height_m: Dominant height (m) at age_dbh.
            age_dbh: Stand age at breast height (>0).
            age2_dbh: Target age at breast height (>0) for height prediction.

        Returns:
            Predicted dominant height (m) at age2_dbh. Returns NaN on calculation error.
        """
        if dominant_height_m <= 1.3:
             warnings.warn("Dominant height must be > 1.3m for Sharma 2011 model.", stacklevel=3)
             return 1.3 # Or NaN

        try:
            theta = (dominant_height_m - 1.3) - SharmaPineModel.B1
            # Calculate term inside sqrt carefully
            age_pow_neg_b3 = age_dbh ** (-SharmaPineModel.B3)
            term_in_sqrt = 4 * SharmaPineModel.B2 * (dominant_height_m - 1.3) * age_pow_neg_b3

            sqrt_arg = theta**2 + term_in_sqrt
            if sqrt_arg < 0:
                 warnings.warn(f"Negative value encountered under square root ({sqrt_arg:.2f}) "
                               f"in Sharma Pine model. Check inputs (H={dominant_height_m}, Age={age_dbh}).", stacklevel=3)
                 return float('nan')

            X = 0.5 * (theta + math.sqrt(sqrt_arg))

             # Avoid division by zero if X is very small
            if abs(X) < 1e-9:
                 warnings.warn("Intermediate value X is near zero in Sharma Pine model. Result may be unstable.", stacklevel=3)
                 return float('nan')

            # Calculate the final height
            age2_pow_neg_b3 = age2_dbh ** (-SharmaPineModel.B3)
            denominator = (1 + SharmaPineModel.B2 / X * age2_pow_neg_b3)

             # Avoid division by zero in the final step
            if abs(denominator) < 1e-9:
                 warnings.warn("Denominator near zero in Sharma Pine model final step. Result may be unstable.", stacklevel=3)
                 return float('nan')

            height2 = (SharmaPineModel.B1 + X) / denominator + 1.3

        except (ValueError, OverflowError) as e:
            warnings.warn(f"Calculation error in Sharma Pine model: {e}. "
                          f"Inputs: H={dominant_height_m}, Age={age_dbh}, Age2={age2_dbh}", stacklevel=3)
            return float('nan')

        return height2

    # --- Public facing method ---
    @staticmethod
    def norway_ht(dominant_height_m: float,
                  age: AgeMeasurement,
                  age2: AgeMeasurement) -> SiteIndexValue:
        """
        Calculates the height trajectory of Scots Pine in Norway based on Sharma et al. (2011).

        IMPORTANT: This function requires age and age2 to be specified as Age.DBH
                   (age at breast height), matching the original Sharma function.

        Args:
            dominant_height_m: Dominant height (m) at 'age'. Must be > 1.3m.
            age: Stand age at breast height (must be Age.DBH and > 0).
            age2: Target age at breast height (must be Age.DBH and > 0) for height prediction.

        Returns:
            SiteIndexValue: Contains the predicted dominant height (m) at age2.
                            The .reference_age attribute is age2 (DBH).
                            Returns NaN height if calculation fails.

        Raises:
            TypeError: If age or age2 are not Age.DBH.
            ValueError: If ages are non-positive or dominant_height <= 1.3.
        """
        if not isinstance(age, AgeMeasurement) or age.code != Age.DBH.value:
            raise TypeError("Input 'age' must be specified as Age.DBH for Sharma's height trajectory.")
        if not isinstance(age2, AgeMeasurement) or age2.code != Age.DBH.value:
            raise TypeError("Input 'age2' must be specified as Age.DBH for Sharma's height trajectory.")

        age_dbh_val = float(age)
        age2_dbh_val = float(age2)

        if age_dbh_val <= 0 or age2_dbh_val <= 0:
            raise ValueError("Ages must be positive for Sharma's height trajectory.")
        if dominant_height_m <= 1.3:
             raise ValueError("Dominant height must be > 1.3m for Sharma's height trajectory.")

        predicted_height = SharmaPineModel._height_trajectory_pine(
            dominant_height_m, age_dbh_val, age2_dbh_val
        )

        return SiteIndexValue(
            value=predicted_height,
            reference_age=age2, # Keep the AgeMeasurement object (DBH)
            species=SharmaPineModel.SPECIES,
            fn=Sharma2011.height_trajectory.pinus_sylvestris
        )


# =============================================================================
# MODIFIED Container wrapper (only height trajectory is available)
# =============================================================================

class HeightTrajectoryWrapper:
    """
    Callable wrapper that calls the underlying model's height trajectory function (`norway_ht`)
    and returns the SiteIndexValue.
    """
    def __init__(self, model):
        self._model = model
        self._target_func = getattr(model, "norway_ht") # Store the function

    def __call__(self, *args, **kwargs):
        """ Makes the wrapper instance directly callable. """
        return self._target_func(*args, **kwargs)

    def __repr__(self):
        return f"<Callable HeightTrajectoryWrapper for {self._model.__name__}>"


# =============================================================================
# Main Container class (Structure remains the same)
# =============================================================================

class Sharma2011:
    """
    Provides a class-based interface to Sharma et al.'s (2011) height trajectory
    functions for Norway Spruce and Scots Pine in Norway.

    Usage:
        # Height trajectory (requires Age.DBH for age and age2)
        predicted_h_spruce = Sharma2011.height_trajectory.picea_abies(
            dominant_height_m=17.0,
            age=Age.DBH(40),
            age2=Age.DBH(20)
        )
        predicted_h_pine = Sharma2011.height_trajectory.pinus_sylvestris(...)

    Note:
        - Requires `Age.DBH` for age inputs. Ages must be > 0.
        - Requires dominant_height > 1.3m.
        - Returns a `SiteIndexValue` object where the value is the predicted height
          and `reference_age` is the target `age2` (DBH).
        - May return NaN in SiteIndexValue if calculation errors occur.
    """
    height_trajectory = type("HeightTrajectoryContainer", (), {
        "picea_abies": HeightTrajectoryWrapper(SharmaSpruceModel),
        "pinus_sylvestris": HeightTrajectoryWrapper(SharmaPineModel)
    })() # Instantiate the container