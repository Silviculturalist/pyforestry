"""
WARNING WARNING WARNING
TODO: THIS FILE AUTOMATICALLY GENERATED. THIS FILE NOT CHECKED.
WARNING WARNING WARNING
""" 


import warnings
from Munin.Helpers.Primitives import SiteIndexValue, AgeMeasurement, TopHeightMeasurement, Age, Stems, StandBasalArea, StandVolume
from Munin.Helpers.TreeSpecies import TreeName, PINUS_SYLVESTRIS
from typing import Optional, Set, Tuple, Union, Literal
import math

# =============================================================================
# Kuehne Pine Model Implementation
# =============================================================================

class KuehnePineModel:
    """ Contains Kuehne et al. (2022) model implementations for Scots Pine. """
    SPECIES: Set[TreeName] = {PINUS_SYLVESTRIS}

    # --- Internal Methods (Direct R Translation) ---
    @staticmethod
    def _height_trajectory(age_total: float,
                           age2_total: float,
                           dominant_height_m: float) -> Tuple[float, float]:
        """ Internal: Calculates predicted height and SI H100. """
        b1 = 68.41819
        b2 = -24.04110
        b3 = 1.46991

        # Check for potential division by zero or invalid math ops
        if dominant_height_m <= 0 or age_total <= 0 or age2_total <= 0:
            warnings.warn("Height and ages must be positive.", stacklevel=3)
            return float('nan'), float('nan')
        if abs(1.0 - b2 * dominant_height_m * (age_total ** -b3)) < 1e-9:
            warnings.warn("Denominator near zero calculating X in height trajectory.", stacklevel=3)
            return float('nan'), float('nan')

        try:
            # Calculate intermediate X based on input height and age
            X = (dominant_height_m - b1) / (1.0 - b2 * dominant_height_m * (age_total ** -b3))

            # Calculate Height at age2
            denom_h2 = 1.0 + b2 * X * (age2_total ** -b3)
            if abs(denom_h2) < 1e-9:
                warnings.warn("Denominator near zero calculating height at age2.", stacklevel=3)
                height_at_age2 = float('nan')
            else:
                height_at_age2 = (b1 + X) / denom_h2

            # Calculate SI H100 (Height at age 100)
            denom_h100 = 1.0 + b2 * X * (100.0 ** -b3)
            if abs(denom_h100) < 1e-9:
                 warnings.warn("Denominator near zero calculating SI H100.", stacklevel=3)
                 si_h100 = float('nan')
            else:
                si_h100 = (b1 + X) / denom_h100

        except (ValueError, OverflowError) as e:
            warnings.warn(f"Calculation error in Kuehne height trajectory: {e}", stacklevel=3)
            return float('nan'), float('nan')

        return height_at_age2, si_h100

    @staticmethod
    def _basal_area_projection(
        age_total: float,
        age2_total: float,
        ba_m2_ha: float,
        dominant_height_m: float,
        dominant_height2_m: float,
        stems_ha: float,
        stems_ha2: float,
        # Thinning parameters (optional, assume 0 if not provided/relevant)
        ba_removed: float = 0.0,
        ba_before_thinning: Optional[float] = None,
        age_thin: Optional[float] = None
    ) -> float:
        """ Internal: Projects basal area. """
        b1 = 1.46553
        b2 = 0.52449
        b3 = 0.17701
        b4 = 16.53755
        b5 = -386.71670

        # Basic input checks
        if age_total <= 0 or age2_total <= 0 or ba_m2_ha <= 0 or dominant_height_m <= 0 or \
           dominant_height2_m <= 0 or stems_ha <= 0 or stems_ha2 <= 0:
            warnings.warn("Ages, BA, Heights, Stems must be positive for BA projection.", stacklevel=3)
            return float('nan')
        if age_total >= age2_total:
            warnings.warn("age2 must be greater than age for projection.", stacklevel=3)
            return float('nan') # Or return initial BA?

        # Handle thinning term safely
        thinning_term = 0.0
        if ba_removed > 0:
            if ba_before_thinning is None or ba_before_thinning <= 0:
                warnings.warn("BA before thinning must be positive if BA was removed.", stacklevel=3)
                return float('nan')
            if age_thin is None or age_thin <= 0:
                 warnings.warn("Age at thinning must be positive if BA was removed.", stacklevel=3)
                 return float('nan')
            if age_thin >= age_total: # Thinning must happen before or at start age for this formula structure
                 warnings.warn("Thinning age must be less than start age for this projection formula.", stacklevel=3)
                 # Or adjust formula logic if needed for thinnings between age and age2
                 return float('nan')

            thinning_term = b5 * (((ba_removed / ba_before_thinning) / age_thin) * ((1.0 / age2_total) - (1.0 / age_total)))

        try:
            log_ba2 = (
                (age_total / age2_total) * math.log(ba_m2_ha) +
                b1 * (1.0 - (age_total / age2_total)) +
                b2 * (math.log(dominant_height2_m) - (age_total / age2_total) * math.log(dominant_height_m)) +
                b3 * (math.log(stems_ha2) - (age_total / age2_total) * math.log(stems_ha)) +
                b4 * ((math.log(stems_ha2) - math.log(stems_ha)) / age2_total) + # Note: R code has /age2, seems odd? Check paper. Assuming /age2 for now.
                thinning_term
            )
            ba2 = math.exp(log_ba2)
        except (ValueError, OverflowError) as e:
            warnings.warn(f"Calculation error in Kuehne BA projection: {e}", stacklevel=3)
            return float('nan')

        return ba2

    @staticmethod
    def _stem_density_projection(
        age_total: float,
        age2_total: float,
        stems_ha: float,
        si40: float, # H at age 40 TOTAL
        # Thinning effect (optional)
        ba_after_thinning: Optional[float] = None,
        ba_before_thinning: Optional[float] = None
    ) -> float:
        """ Internal: Projects stem density. """
        b1 = -1.56856
        b2 = 0.00284
        b3 = 4.14779
        b4 = 4.87715

        if age_total <= 0 or age2_total <= 0 or stems_ha <= 0 or si40 <= 0:
             warnings.warn("Ages, stems, and SI40 must be positive for stem projection.", stacklevel=3)
             return float('nan')
        if age_total >= age2_total:
             warnings.warn("age2 must be greater than age for projection.", stacklevel=3)
             return float('nan')

        thinning_ratio = 1.0 # Default: no thinning effect
        if ba_after_thinning is not None and ba_before_thinning is not None:
            if ba_before_thinning <= 0:
                 warnings.warn("BA before thinning must be positive if thinning ratio is used.", stacklevel=3)
                 return float('nan')
            if ba_after_thinning < 0 or ba_after_thinning > ba_before_thinning:
                warnings.warn("BA after thinning is invalid.", stacklevel=3)
                return float('nan')
            thinning_ratio = ba_after_thinning / ba_before_thinning
        elif ba_after_thinning is not None or ba_before_thinning is not None:
            warnings.warn("Both BA before and after thinning required if one is provided.", stacklevel=3)
            return float('nan')

        try:
            term1 = stems_ha ** b1
            term2 = (b2 * thinning_ratio * ((si40 / 10000.0)**b3) * (age2_total**b4 - age_total**b4)) # Corrected age exponent based on typical integral form

            # Check if the base of the final power is positive
            base = term1 + term2
            if base <= 0:
                warnings.warn(f"Calculated base ({base:.2f}) for stem density power is non-positive. Likely mortality exceeds limits.", stacklevel=3)
                return 0.0 # Stem density becomes 0

            stems2 = base ** (1.0 / b1)

        except (ValueError, OverflowError) as e:
            warnings.warn(f"Calculation error in Kuehne stem projection: {e}", stacklevel=3)
            return float('nan')

        return stems2


    @staticmethod
    def _volume(ba_m2_ha: float,
                dominant_height_m: float,
                age_total: float,
                 # Thinning effect (optional)
                ba_after_thinning: Optional[float] = None,
                ba_before_thinning: Optional[float] = None,
                age_thin: Optional[float] = None
                ) -> float:
        """ Internal: Calculates stand volume. """
        b1 = 0.65394
        b2 = 0.96928
        b3 = 0.91504
        b4 = -2.05278
        b5 = -0.06848

        if ba_m2_ha <=0 or dominant_height_m <= 0 or age_total <= 0:
            warnings.warn("BA, height, and age must be positive for volume calculation.", stacklevel=3)
            return float('nan')

        thinning_term_exponent = 0.0 # Default: no thinning effect
        if ba_after_thinning is not None and ba_before_thinning is not None and age_thin is not None:
             if ba_before_thinning <= 0 or age_thin <= 0:
                 warnings.warn("BA before thinning and age thin must be positive if thinning ratio is used.", stacklevel=3)
                 return float('nan')
             if ba_after_thinning < 0 or ba_after_thinning > ba_before_thinning:
                 warnings.warn("BA after thinning is invalid.", stacklevel=3)
                 return float('nan')
             thinning_term_exponent = b5 * (age_thin / age_total)
             thinning_ratio = ba_after_thinning / ba_before_thinning
        elif ba_after_thinning is not None or ba_before_thinning is not None or age_thin is not None:
             warnings.warn("All BA before, BA after, and age thin required if one is provided.", stacklevel=3)
             return float('nan')
        else:
            thinning_ratio = 1.0 # No thinning effect if no params provided

        try:
            volume = (
                b1 *
                (ba_m2_ha ** b2) *
                (dominant_height_m ** b3) *
                math.exp(b4 / age_total) *
                (thinning_ratio ** thinning_term_exponent)
            )
        except (ValueError, OverflowError) as e:
             warnings.warn(f"Calculation error in Kuehne volume: {e}", stacklevel=3)
             return float('nan')

        return volume

    @staticmethod
    def _stems_quotient(ba_before_m2_ha: float, ba_after_m2_ha: float) -> float:
        """ Internal: Calculates stems ratio from BA ratio. """
        if ba_before_m2_ha <= 0 or ba_after_m2_ha < 0 or ba_after_m2_ha > ba_before_m2_ha:
            warnings.warn("Invalid BA values for stems quotient.", stacklevel=3)
            return float('nan')
        try:
            stems_quotient = math.exp(-1.91239 + 1.94414 * (ba_after_m2_ha / ba_before_m2_ha))
        except (ValueError, OverflowError) as e:
            warnings.warn(f"Calculation error in Kuehne stems quotient: {e}", stacklevel=3)
            return float('nan')
        return stems_quotient

    @staticmethod
    def _ba_quotient(stems_before_ha: float, stems_after_ha: float) -> float:
        """ Internal: Calculates BA ratio from stems ratio. """
        if stems_before_ha <= 0 or stems_after_ha < 0 or stems_after_ha > stems_before_ha:
            warnings.warn("Invalid stem values for BA quotient.", stacklevel=3)
            return float('nan')
        try:
            # Ensure log argument is positive
            stems_ratio = stems_after_ha / stems_before_ha
            if stems_ratio <= 0:
                 warnings.warn("Stem ratio must be positive for BA quotient.", stacklevel=3)
                 return float('nan')

            ba_quotient = (math.log(stems_ratio) + 1.91239) / 1.94414 # Fixed formula based on R code
        except (ValueError, OverflowError) as e:
             warnings.warn(f"Calculation error in Kuehne BA quotient: {e}", stacklevel=3)
             return float('nan')
        # BA quotient should be <= 1
        return min(ba_quotient, 1.0) if not math.isnan(ba_quotient) else float('nan')


    # --- Public Methods (Handling AgeMeasurement, Output Types etc.) ---
    @staticmethod
    def height_trajectory_and_si(
        age: AgeMeasurement,
        age2: AgeMeasurement,
        dominant_height: Union[TopHeightMeasurement, float],
        output: Literal["Height", "SIH100", "Both"] = "Height"
    ) -> Union[SiteIndexValue, float, Tuple[SiteIndexValue, float]]:
        """
        Calculates height trajectory and/or SI H100 for Scots Pine using Kuehne et al. (2022).
        Requires TOTAL age.

        Args:
            age: Stand total age (must be Age.TOTAL).
            age2: Target total age (must be Age.TOTAL).
            dominant_height: Dominant height (m) at 'age'.
            output: "Height" (returns SiteIndexValue with height at age2),
                    "SIH100" (returns float SI H100),
                    "Both" (returns tuple: SiteIndexValue(height@age2), float SIH100).

        Returns:
            Predicted height (as SiteIndexValue), SI H100 (float), or tuple based on 'output'.
        """
        if not isinstance(age, AgeMeasurement) or age.code != Age.TOTAL.value:
            raise TypeError("Input 'age' must be specified as Age.TOTAL.")
        if not isinstance(age2, AgeMeasurement) or age2.code != Age.TOTAL.value:
            raise TypeError("Input 'age2' must be specified as Age.TOTAL.")

        age_val = float(age)
        age2_val = float(age2)
        h_val = float(dominant_height)

        if age_val <= 0 or age2_val <= 0 or h_val <= 0:
             raise ValueError("Ages and height must be positive.")

        # Call internal function
        # Need to assign the correct caller function later based on where this is called from
        caller_fn = None # Placeholder, will be set by the wrapper context
        height_at_age2, si_h100 = KuehnePineModel._height_trajectory(age_val, age2_val, h_val)

        si_value_obj = SiteIndexValue(
            value=height_at_age2,
            reference_age=age2, # Total age
            species=KuehnePineModel.SPECIES,
            fn=caller_fn # Will be set by wrapper
        )

        if output == "Height":
            return si_value_obj
        elif output == "SIH100":
            return si_h100
        elif output == "Both":
            return si_value_obj, si_h100
        else:
            raise ValueError("output must be 'Height', 'SIH100', or 'Both'")

    @staticmethod
    def project_basal_area(
        age: AgeMeasurement,
        age2: AgeMeasurement,
        basal_area: Union[StandBasalArea, float],
        dominant_height: Union[TopHeightMeasurement, float],
        dominant_height2: Union[TopHeightMeasurement, float],
        stems: Union[Stems, float],
        stems2: Union[Stems, float],
        thinning_ba_removed: float = 0.0,
        thinning_ba_before: Optional[Union[StandBasalArea, float]] = None,
        thinning_age: Optional[AgeMeasurement] = None
    ) -> StandBasalArea:
        """ Projects basal area using Kuehne et al. (2022). Requires TOTAL age. """
        if not isinstance(age, AgeMeasurement) or age.code != Age.TOTAL.value: raise TypeError("'age' must be Age.TOTAL")
        if not isinstance(age2, AgeMeasurement) or age2.code != Age.TOTAL.value: raise TypeError("'age2' must be Age.TOTAL")
        if thinning_age and (not isinstance(thinning_age, AgeMeasurement) or thinning_age.code != Age.TOTAL.value): raise TypeError("'thinning_age' must be Age.TOTAL")

        ba2_val = KuehnePineModel._basal_area_projection(
            age_total=float(age),
            age2_total=float(age2),
            ba_m2_ha=float(basal_area),
            dominant_height_m=float(dominant_height),
            dominant_height2_m=float(dominant_height2),
            stems_ha=float(stems),
            stems_ha2=float(stems2),
            ba_removed=float(thinning_ba_removed),
            ba_before_thinning=float(thinning_ba_before) if thinning_ba_before is not None else None,
            age_thin=float(thinning_age) if thinning_age is not None else None
        )
        caller_fn = None # Placeholder, set by wrapper
        return StandBasalArea(value=ba2_val, species=KuehnePineModel.SPECIES, fn=caller_fn) # Precision not estimated here

    @staticmethod
    def project_stems(
        age: AgeMeasurement,
        age2: AgeMeasurement,
        stems: Union[Stems, float],
        site_index_40: float, # Assuming SI Ht(40, TOTAL)
        thinning_ba_after: Optional[Union[StandBasalArea, float]] = None,
        thinning_ba_before: Optional[Union[StandBasalArea, float]] = None,
    ) -> Stems:
        """ Projects stem density using Kuehne et al. (2022). Requires TOTAL age. """
        if not isinstance(age, AgeMeasurement) or age.code != Age.TOTAL.value: raise TypeError("'age' must be Age.TOTAL")
        if not isinstance(age2, AgeMeasurement) or age2.code != Age.TOTAL.value: raise TypeError("'age2' must be Age.TOTAL")

        stems2_val = KuehnePineModel._stem_density_projection(
             age_total=float(age),
             age2_total=float(age2),
             stems_ha=float(stems),
             si40=float(site_index_40),
             ba_after_thinning=float(thinning_ba_after) if thinning_ba_after is not None else None,
             ba_before_thinning=float(thinning_ba_before) if thinning_ba_before is not None else None
        )
        caller_fn = None # Placeholder, set by wrapper
        return Stems(value=stems2_val, species=KuehnePineModel.SPECIES, fn=caller_fn) # Precision not estimated

    @staticmethod
    def predict_volume(
        basal_area: Union[StandBasalArea, float],
        dominant_height: Union[TopHeightMeasurement, float],
        age: AgeMeasurement,
        thinning_ba_after: Optional[Union[StandBasalArea, float]] = None,
        thinning_ba_before: Optional[Union[StandBasalArea, float]] = None,
        thinning_age: Optional[AgeMeasurement] = None
    )-> StandVolume:
        """ Predicts stand volume using Kuehne et al. (2022). Requires TOTAL age. """
        if not isinstance(age, AgeMeasurement) or age.code != Age.TOTAL.value: raise TypeError("'age' must be Age.TOTAL")
        if thinning_age and (not isinstance(thinning_age, AgeMeasurement) or thinning_age.code != Age.TOTAL.value): raise TypeError("'thinning_age' must be Age.TOTAL")

        vol_val = KuehnePineModel._volume(
             ba_m2_ha=float(basal_area),
             dominant_height_m=float(dominant_height),
             age_total=float(age),
             ba_after_thinning=float(thinning_ba_after) if thinning_ba_after is not None else None,
             ba_before_thinning=float(thinning_ba_before) if thinning_ba_before is not None else None,
             age_thin=float(thinning_age) if thinning_age is not None else None
        )
        caller_fn = None # Placeholder, set by wrapper
        # Assuming volume is m3/ha over bark, adjust if needed based on paper
        return StandVolume(value=vol_val, species=KuehnePineModel.SPECIES, fn=caller_fn, over_bark=True)

    @staticmethod
    def predict_stems_quotient(
        ba_before: Union[StandBasalArea, float],
        ba_after: Union[StandBasalArea, float]
    ) -> float:
        """ Predicts stems remaining quotient from BA quotient. """
        return KuehnePineModel._stems_quotient(float(ba_before), float(ba_after))

    @staticmethod
    def predict_ba_quotient(
        stems_before: Union[Stems, float],
        stems_after: Union[Stems, float]
    ) -> float:
         """ Predicts BA remaining quotient from stems quotient. """
         return KuehnePineModel._ba_quotient(float(stems_before), float(stems_after))


# =============================================================================
# Callable Wrappers (Defined once in the core implementation module)
# =============================================================================

class HeightTrajectoryWrapper:
    """ Callable wrapper for height_trajectory_and_si """
    def __init__(self, model):
        self._model = model
        self._target_func = model.height_trajectory_and_si
        self._caller_ref = None # Will be set when container is built

    def __call__(self, *args, **kwargs):
        result = self._target_func(*args, **kwargs)
        # Inject the correct caller reference into SiteIndexValue if returned
        if isinstance(result, SiteIndexValue):
            result.fn = self._caller_ref
        elif isinstance(result, tuple) and isinstance(result[0], SiteIndexValue):
             result[0].fn = self._caller_ref
        return result

    def __repr__(self): return f"<Callable HeightTrajectoryWrapper for {self._model.__name__}>"

class BasalAreaProjectionWrapper:
    """ Callable wrapper for project_basal_area """
    def __init__(self, model):
        self._model = model
        self._target_func = model.project_basal_area
        self._caller_ref = None

    def __call__(self, *args, **kwargs):
        result = self._target_func(*args, **kwargs)
        if isinstance(result, StandBasalArea): result.fn = self._caller_ref # Inject caller ref
        return result

    def __repr__(self): return f"<Callable BasalAreaProjectionWrapper for {self._model.__name__}>"

class StemDensityWrapper:
    """ Callable wrapper for project_stems """
    def __init__(self, model):
        self._model = model
        self._target_func = model.project_stems
        self._caller_ref = None

    def __call__(self, *args, **kwargs):
        result = self._target_func(*args, **kwargs)
        if isinstance(result, Stems): result.fn = self._caller_ref
        return result

    def __repr__(self): return f"<Callable StemDensityWrapper for {self._model.__name__}>"

class VolumeWrapper:
    """ Callable wrapper for predict_volume """
    def __init__(self, model):
        self._model = model
        self._target_func = model.predict_volume
        self._caller_ref = None

    def __call__(self, *args, **kwargs):
        result = self._target_func(*args, **kwargs)
        if isinstance(result, StandVolume): result.fn = self._caller_ref
        return result

    def __repr__(self): return f"<Callable VolumeWrapper for {self._model.__name__}>"

class StemsQuotientWrapper:
    """ Callable wrapper for predict_stems_quotient """
    def __init__(self, model):
        self._model = model
        self._target_func = model.predict_stems_quotient

    def __call__(self, *args, **kwargs): return self._target_func(*args, **kwargs)
    def __repr__(self): return f"<Callable StemsQuotientWrapper for {self._model.__name__}>"

class BAQuotientWrapper:
    """ Callable wrapper for predict_ba_quotient """
    def __init__(self, model):
        self._model = model
        self._target_func = model.predict_ba_quotient

    def __call__(self, *args, **kwargs): return self._target_func(*args, **kwargs)
    def __repr__(self): return f"<Callable BAQuotientWrapper for {self._model.__name__}>"
