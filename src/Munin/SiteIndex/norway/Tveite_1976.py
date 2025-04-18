import math
import warnings
from typing import Union, Tuple, Set
from Munin.Helpers.Base import (SiteIndexValue, Age, AgeMeasurement,
                      Stems, StandBasalArea, QuadraticMeanDiameter, Diameter_cm)
from Munin.Helpers.TreeSpecies import TreeName, PICEA_ABIES, PINUS_SYLVESTRIS

class TveiteSpruceModel:
    """
    Implements Tveite's models for Norway Spruce (Picea abies) in Norway.
    """
    SPECIES: Set[TreeName] = {PICEA_ABIES}

    @staticmethod
    def _height_trajectory_spruce(dominant_height_m: float,
                                  age_dbh: float,
                                  age2_dbh: float) -> float:
        """
        Internal calculation based on Tveite 1977.
        Assumes age and age2 are DBH.

        Args:
            dominant_height_m: Dominant height (m) at age_dbh.
            age_dbh: Stand age at breast height.
            age2_dbh: Target age at breast height for height prediction.

        Returns:
            Predicted dominant height (m) at age2_dbh.
        """
        if age_dbh < 15 or age2_dbh < 15:
             warnings.warn("Tveite (1977) Spruce height trajectory not recommended "
                           "for breast height ages below 15-20 years.", stacklevel=3)

        # Reference curve H17 calculation
        H17 = ((age_dbh + 5.5) / (4.30606 + 0.164818 * (age_dbh + 5.5)))**2.1

        # Difference function at age_dbh
        if age_dbh <= 100:
            diff_age = (3 + (0.040183 * (age_dbh - 40)) -
                        (0.104701 * (((age_dbh - 40)**2) / (10**2))) +
                        (0.679104 * (((age_dbh - 40)**3) / (10**5))) +
                        (0.184402 * (((age_dbh - 40)**4) / (10**6))) -
                        (0.224249 * (((age_dbh - 40)**5) / (10**8))))
        else:
            diff_age = 3.755

        diff_age = diff_age / 3.0

        # Avoid division by zero if diff_age is very small
        if abs(diff_age) < 1e-9:
             warnings.warn("Difference at age calculation resulted in near-zero value. "
                           "Projection might be unstable.", stacklevel=3)
             number_of_differences = 0.0 # Or handle as appropriate
        else:
            number_of_differences = (dominant_height_m - H17) / diff_age


        # Reference curve H17 calculation at age2_dbh
        H17_2 = ((age2_dbh + 5.5) / (4.30606 + 0.164818 * (age2_dbh + 5.5)))**2.1

        # Difference function at age2_dbh
        if age2_dbh <= 100:
            diff_age2 = (3 + (0.040183 * (age2_dbh - 40)) -
                         (0.104701 * (((age2_dbh - 40)**2) / (10**2))) +
                         (0.679104 * (((age2_dbh - 40)**3) / (10**5))) +
                         (0.184402 * (((age2_dbh - 40)**4) / (10**6))) -
                         (0.224249 * (((age2_dbh - 40)**5) / (10**8))))
        else:
            diff_age2 = 3.755

        diff_age2 = diff_age2 / 3.0

        # Predicted height at age2_dbh
        height2 = H17_2 + diff_age2 * number_of_differences

        return height2

    @staticmethod
    def _loreys_height_spruce(dominant_height_m: float,
                              stems_per_ha: float,
                              basal_area_m2_ha: float,
                              qmd_cm: float) -> float:
        """
        Internal calculation for Lorey's mean height based on Tveite 1967.

        Args:
            dominant_height_m: Dominant height (m).
            stems_per_ha: Number of stems per hectare.
            basal_area_m2_ha: Basal area (m²/ha).
            qmd_cm: Quadratic mean diameter (cm).

        Returns:
            Lorey's mean height (m).
        """
        loreys_h = dominant_height_m - (
            226.439 +
            14.37 * dominant_height_m -
            0.0329 * stems_per_ha +
            0.00468 * stems_per_ha * dominant_height_m -
            5.91 * basal_area_m2_ha +
            0.190 * basal_area_m2_ha * dominant_height_m -
            15.73 * qmd_cm
        ) / 100.0
        return loreys_h

    # --- Public facing methods ---
    @staticmethod
    def norway_ht(dominant_height_m: float,
                  age: AgeMeasurement,
                  age2: AgeMeasurement) -> SiteIndexValue:
        """
        Calculates the height trajectory of Norway Spruce in Norway based on Tveite (1977).

        IMPORTANT: This function requires age and age2 to be specified as Age.DBH
                   (age at breast height), matching the original Tveite function.

        Args:
            dominant_height_m: Dominant height (m) at 'age'.
            age: Stand age at breast height (must be Age.DBH).
            age2: Target age at breast height (must be Age.DBH) for height prediction.

        Returns:
            SiteIndexValue: Contains the predicted dominant height (m) at age2.
                            The .reference_age attribute is age2 (DBH).

        Raises:
            TypeError: If age or age2 are not Age.DBH.
            ValueError: If ages are non-positive.
        """
        if not isinstance(age, AgeMeasurement) or age.code != Age.DBH.value:
            raise TypeError("Input 'age' must be specified as Age.DBH for Tveite's height trajectory.")
        if not isinstance(age2, AgeMeasurement) or age2.code != Age.DBH.value:
            raise TypeError("Input 'age2' must be specified as Age.DBH for Tveite's height trajectory.")

        age_dbh_val = float(age)
        age2_dbh_val = float(age2)

        if age_dbh_val <= 0 or age2_dbh_val <= 0:
            raise ValueError("Ages must be positive.")

        predicted_height = TveiteSpruceModel._height_trajectory_spruce(
            dominant_height_m, age_dbh_val, age2_dbh_val
        )

        return SiteIndexValue(
            value=predicted_height,
            reference_age=age2, # Keep the AgeMeasurement object (DBH)
            species=TveiteSpruceModel.SPECIES,
            fn=Tveite1976.height_trajectory.picea_abies.norway_ht # Reference the public API endpoint
        )

    @staticmethod
    def norway_hl(dominant_height_m: float,
                  stems_per_ha: Union[Stems, float],
                  basal_area_m2_ha: Union[StandBasalArea, float],
                  qmd_cm: Union[QuadraticMeanDiameter, float]) -> float:
        """
        Calculates Lorey's mean height for Norway Spruce in Norway based on Tveite (1967).

        Args:
            dominant_height_m: Dominant height (m).
            stems_per_ha: Number of stems per hectare (Stems object or float).
            basal_area_m2_ha: Basal area (m²/ha) (StandBasalArea object or float).
            qmd_cm: Quadratic mean diameter (cm) (QuadraticMeanDiameter object or float).

        Returns:
            Lorey's mean height (m) as a float.
        """
        # Extract float values, handling potential custom types from Base.py
        stems_val = float(stems_per_ha)
        ba_val = float(basal_area_m2_ha)
        qmd_val = float(qmd_cm)

        return TveiteSpruceModel._loreys_height_spruce(
            dominant_height_m, stems_val, ba_val, qmd_val
        )


class TveitePineModel:
    """
    Implements Tveite's models for Scots Pine (Pinus sylvestris) in Norway.
    """
    SPECIES: Set[TreeName] = {PINUS_SYLVESTRIS}

    @staticmethod
    def _height_trajectory_pine(dominant_height_m: float,
                                age_dbh: float,
                                age2_dbh: float) -> float:
        """
        Internal calculation based on Tveite 1976.
        Assumes age and age2 are DBH.

        Args:
            dominant_height_m: Dominant height (m) at age_dbh.
            age_dbh: Stand age at breast height.
            age2_dbh: Target age at breast height for height prediction.

        Returns:
            Predicted dominant height (m) at age2_dbh.
        """
        # Reference curve H14 calculation
        try:
            H14 = 24.7 * (1 - math.exp(-0.02105 * age_dbh))**1.18029 + 1.3
        except ValueError: # Handle potential domain error if age_dbh is such that base is negative
            warnings.warn(f"Math domain error calculating H14 for Pine at age {age_dbh}. Check inputs.", stacklevel=3)
            # Decide on fallback behavior, e.g., return NaN or raise error
            return float('nan')


        # Difference function at age_dbh
        if age_dbh <= 119:
             diff_age = (3 + (0.0394624 * (age_dbh - 40)) -
                        (0.0649695 * (((age_dbh - 40)**2) / 100.0)) +
                        (0.487394 * (((age_dbh - 40)**3) / 100000.0)) -
                        (0.141827 * (((age_dbh - 40)**4) / 10000000.0)))
        else:
             diff_age = 3.913

        diff_age = diff_age / 3.0

        # Avoid division by zero
        if abs(diff_age) < 1e-9:
            warnings.warn("Difference at age calculation resulted in near-zero value for Pine. "
                          "Projection might be unstable.", stacklevel=3)
            number_of_differences = 0.0
        else:
            number_of_differences = (dominant_height_m - H14) / diff_age


        # Reference curve H14 calculation at age2_dbh
        try:
             H14_2 = 24.7 * (1 - math.exp(-0.02105 * age2_dbh))**1.18029 + 1.3
        except ValueError:
             warnings.warn(f"Math domain error calculating H14_2 for Pine at age {age2_dbh}. Check inputs.", stacklevel=3)
             return float('nan')

        # Difference function at age2_dbh
        if age2_dbh <= 119:
             diff_age2 = (3 + (0.0394624 * (age2_dbh - 40)) -
                         (0.0649695 * (((age2_dbh - 40)**2) / 100.0)) +
                         (0.487394 * (((age2_dbh - 40)**3) / 100000.0)) -
                         (0.141827 * (((age2_dbh - 40)**4) / 10000000.0)))
        else:
             diff_age2 = 3.913

        diff_age2 = diff_age2 / 3.0

        # Predicted height at age2_dbh
        height2 = H14_2 + diff_age2 * number_of_differences

        return height2

    @staticmethod
    def _loreys_height_pine(dominant_height_m: float,
                            stems_per_ha: float,
                            basal_area_m2_ha: float,
                            diameter_mean_ba_stem_cm: float) -> float:
        """
        Internal calculation for Lorey's mean height based on Tveite 1967.

        Args:
            dominant_height_m: Dominant height (m).
            stems_per_ha: Number of stems per hectare.
            basal_area_m2_ha: Basal area (m²/ha).
            diameter_mean_ba_stem_cm: Diameter (cm) corresponding to the mean basal area stem.

        Returns:
            Lorey's mean height (m).
        """
        loreys_h = dominant_height_m - (
            220.075 +
            7.698 * dominant_height_m -
            0.0300 * stems_per_ha +
            0.00344 * stems_per_ha * dominant_height_m -
            4.990 * basal_area_m2_ha +
            0.260 * basal_area_m2_ha * dominant_height_m -
            12.26 * diameter_mean_ba_stem_cm
        ) / 100.0
        return loreys_h

    # --- Public facing methods ---
    @staticmethod
    def norway_ht(dominant_height_m: float,
                  age: AgeMeasurement,
                  age2: AgeMeasurement) -> SiteIndexValue:
        """
        Calculates the height trajectory of Scots Pine in Norway based on Tveite (1976).

        IMPORTANT: This function requires age and age2 to be specified as Age.DBH
                   (age at breast height), matching the original Tveite function.

        Args:
            dominant_height_m: Dominant height (m) at 'age'.
            age: Stand age at breast height (must be Age.DBH).
            age2: Target age at breast height (must be Age.DBH) for height prediction.

        Returns:
            SiteIndexValue: Contains the predicted dominant height (m) at age2.
                            The .reference_age attribute is age2 (DBH).

        Raises:
            TypeError: If age or age2 are not Age.DBH.
            ValueError: If ages are non-positive.
        """
        if not isinstance(age, AgeMeasurement) or age.code != Age.DBH.value:
            raise TypeError("Input 'age' must be specified as Age.DBH for Tveite's height trajectory.")
        if not isinstance(age2, AgeMeasurement) or age2.code != Age.DBH.value:
            raise TypeError("Input 'age2' must be specified as Age.DBH for Tveite's height trajectory.")

        age_dbh_val = float(age)
        age2_dbh_val = float(age2)

        if age_dbh_val <= 0 or age2_dbh_val <= 0:
            raise ValueError("Ages must be positive.")

        predicted_height = TveitePineModel._height_trajectory_pine(
            dominant_height_m, age_dbh_val, age2_dbh_val
        )

        return SiteIndexValue(
            value=predicted_height,
            reference_age=age2, # Keep the AgeMeasurement object (DBH)
            species=TveitePineModel.SPECIES,
            fn=Tveite1976.height_trajectory.pinus_sylvestris.norway_ht # Reference the public API endpoint
        )

    @staticmethod
    def norway_hl(dominant_height_m: float,
                  stems_per_ha: Union[Stems, float],
                  basal_area_m2_ha: Union[StandBasalArea, float],
                  diameter_mean_ba_stem_cm: Union[Diameter_cm, float]) -> float:
        """
        Calculates Lorey's mean height for Scots Pine in Norway based on Tveite (1967).

        Args:
            dominant_height_m: Dominant height (m).
            stems_per_ha: Number of stems per hectare (Stems object or float).
            basal_area_m2_ha: Basal area (m²/ha) (StandBasalArea object or float).
            diameter_mean_ba_stem_cm: Diameter (cm) corresponding to the mean basal area stem
                                     (Diameter_cm object or float).

        Returns:
            Lorey's mean height (m) as a float.
        """
        # Extract float values
        stems_val = float(stems_per_ha)
        ba_val = float(basal_area_m2_ha)
        diam_val = float(diameter_mean_ba_stem_cm)

        return TveitePineModel._loreys_height_pine(
            dominant_height_m, stems_val, ba_val, diam_val
        )


# =============================================================================
# MODIFIED Container wrappers to make them callable
# =============================================================================

class HeightTrajectoryWrapper:
    """
    Callable wrapper that calls the underlying model's height trajectory function (`norway_ht`)
    and returns the SiteIndexValue.
    """
    def __init__(self, model):
        self._model = model
        # Store the actual function to call
        self._target_func = getattr(model, "norway_ht")

    def __call__(self, *args, **kwargs):
        """ Makes the wrapper instance directly callable. """
        # Call the stored target function
        return self._target_func(*args, **kwargs)

    def __repr__(self):
        return f"<Callable HeightTrajectoryWrapper for {self._model.__name__}>"


class LoreysHeightWrapper:
    """
    Callable wrapper that calls the underlying model's Lorey's height function (`norway_hl`)
    and returns the float result.
    """
    def __init__(self, model):
        self._model = model
        # Store the actual function to call
        self._target_func = getattr(model, "norway_hl")

    def __call__(self, *args, **kwargs):
        """ Makes the wrapper instance directly callable. """
        # Call the stored target function
        return self._target_func(*args, **kwargs)

    def __repr__(self):
        return f"<Callable LoreysHeightWrapper for {self._model.__name__}>"


# =============================================================================
# Main Container class (Structure remains the same)
# =============================================================================

class Tveite1976:
    """
    Provides a class-based interface to Tveite's height trajectory (1976, 1977)
    and Lorey's mean height (1967) functions for Norway.

    Usage:
        # Height trajectory (requires Age.DBH for age and age2)
        predicted_h_spruce = Tveite1970.height_trajectory.picea_abies(
            dominant_height_m=17.0,
            age=Age.DBH(40),
            age2=Age.DBH(20)
        )
        predicted_h_pine = Tveite1970.height_trajectory.pinus_sylvestris(...)

        # Lorey's Height (HL)
        hl_spruce = Tveite1970.HL.picea_abies(
             dominant_height_m=20.0,
             stems_per_ha=1000.0,
             basal_area_m2_ha=25.0,
             qmd_cm=18.0
        )
         hl_pine = Tveite1970.HL.pinus_sylvestris(...)

    Note:
        - Height trajectory functions require `Age.DBH` for age inputs.
        - Lorey's height functions return a float value (meters).
        - Height trajectory functions return a `SiteIndexValue` object where the value
          is the predicted height and `reference_age` is the target `age2` (DBH).
    """
    height_trajectory = type("HeightTrajectoryContainer", (), {
        "picea_abies": HeightTrajectoryWrapper(TveiteSpruceModel),
        "pinus_sylvestris": HeightTrajectoryWrapper(TveitePineModel)
    })()

    HL = type("LoreysHeightContainer", (), {
        "picea_abies": LoreysHeightWrapper(TveiteSpruceModel),
        "pinus_sylvestris": LoreysHeightWrapper(TveitePineModel)
    })()
