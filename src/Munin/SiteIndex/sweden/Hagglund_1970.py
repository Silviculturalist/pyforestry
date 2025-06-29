from Munin.Helpers.Primitives import SiteIndexValue, Age, AgeMeasurement
from Munin.Helpers import TreeSpecies
import math
import warnings
from numpy import exp, log
from enum import Enum
from typing import Union

class HagglundSpruceModel:
    @staticmethod
    def northern_sweden(dominant_height: float,
                        age: Union[float, AgeMeasurement],
                        age2: Union[float, AgeMeasurement],
                        latitude: float,
                        culture: bool = True) -> tuple[SiteIndexValue, float]:
        """
        Calculates the height trajectory of Norway Spruce in northern Sweden based on Hägglund (1972).

        In this version, we allow the input parameter 'age' to be provided either as Age.DBH
        (the effective DBH age for the stand) or as Age.TOTAL. In the latter case, we use Newton–Raphson
        to solve for the effective DBH age 'x' that satisfies: x + T13(x) = age_total.
        
        For the prediction age 'age2':
         - If provided as Age.DBH, we add the computed T13 to obtain the total age.
         - Otherwise (if Age.TOTAL) it is used directly.
        """
        # Extract numeric values from age and its code.
        if isinstance(age, AgeMeasurement):
            age_value = float(age)
            age_type = age.code
        else:
            age_value = float(age)
            age_type = Age.DBH.value  # default if plain number

        # For age2, extract numeric value and preserve type.
        if isinstance(age2, AgeMeasurement):
            age2_value = float(age2)
            age2_type = age2.code
        else:
            age2_value = float(age2)
            age2_type = Age.TOTAL.value  # default to total if no code provided

        P = 0.9175 if culture else 1.0
        # Convert dominant height (meters) to decimeters and subtract 13 (the base value)
        top_height_dm = dominant_height * 10 - 13

        if age_value > (407 - 1.167 * top_height_dm):
            warnings.warn("Too old stand, outside of the material.")

        if latitude >= 67 or latitude <= 60:
            warnings.warn("Outside of latitudinal range, 60°<= L <= 67° N, using function 8.4 ")
            # Parameters for function 8.4
            B = 3.4501
            C = 0.77518
            D = -0.42579
            E = 1.33935
        else:
            # Parameters for function 8.7
            B = 3.3816
            C = 0.77896
            D = -1.24207 + 0.0014629 * latitude * 10
            E = 1.25998

        # Define the bonitering subroutine that uses the effective DBH age (eff_age)
        def subroutineBonitering(eff_age: float):
            AI1 = 10.0
            AI2 = 600.0
            while abs(AI1 - AI2) > 1:
                AI3 = (AI1 + AI2) / 2.0
                RK = 0.001936 + 0.00004100 * AI3 ** 1.0105
                A2 = B * AI3 ** C
                RM2 = D + E / (0.56721 + 0.000008 * AI3 ** 1.8008)
                DIF = top_height_dm - A2 * (1 - exp(-eff_age * RK)) ** RM2
                if DIF <= 0:
                    AI2 = AI3
                else:
                    AI1 = AI3
            T26 = (-1 / RK) * log(1 - (13 / A2) ** (1 / RM2))
            T13_local = P * (7.0287 + 0.66118 * T26)
            return A2, RK, RM2, T26, T13_local

        # If age is provided as DBH, use it directly; if provided as TOTAL, solve for effective DBH age.
        if age_type == Age.DBH.value:
            eff_age = age_value
        else:
            # Use Newton–Raphson to solve: f(x) = x + T13(x) - age_value = 0
            def f(x):
                # Compute T13 from the bonitering subroutine for effective age x.
                _, _, _, _, T13_local = subroutineBonitering(x)
                return x + T13_local - age_value

            def fprime(x, h=0.001):
                return (f(x+h) - f(x-h)) / (2*h)

            # Choose an initial guess. (Empirically, effective DBH age is lower than total age.)
            x = age_value * 0.35
            for i in range(30):
                fx = f(x)
                fpx = fprime(x)
                if abs(fpx) < 1e-8:
                    break
                x_new = x - fx / fpx
                if abs(x_new - x) < 1e-6:
                    x = x_new
                    break
                x = x_new
            eff_age = x

        # Now compute productivity parameters at the effective DBH age.
        A2, RK, RM2, T26, T13 = subroutineBonitering(eff_age)
        if A2 > 336:
            warnings.warn('Too high productivity, outside of material.')
        if A2 < 189:
            warnings.warn('Too low productivity, outside of material.')

        # Determine the effective DBH age for the height prediction:
        if age2_type == Age.DBH.value:
        # If the target age 'age2' is already DBH, use its value directly for the formula.
            effective_age2_dbh = age2_value
        # The corresponding total age for output reference (if needed) would be:
            output_total_age = age2_value + T13
        else: # age2_type is TOTAL
            # If the target age 'age2' is TOTAL, calculate the corresponding effective DBH age.
            # We use the T13 calculated based on the input conditions (age, dominant_height).
            effective_age2_dbh = age2_value - T13
            # Check for potentially non-physical results (e.g., total age less than T13)
            if effective_age2_dbh <= 0:
                 warnings.warn(f"Calculated effective DBH age for prediction ({effective_age2_dbh:.2f}) is non-positive. "
                               f"This might happen if age2 (Total Age={age2_value}) is less than T13 ({T13:.2f}). "
                               f"Using a small positive value (e.g., 1.0) instead.", stacklevel=2)
                 effective_age2_dbh = 1.0 # Use a small positive fallback or handle as an error
            # The corresponding total age for output reference is the input total age itself:
            output_total_age = age2_value

        # Calculate height using the derived effective DBH age
        height = (13 + A2 * (1 - exp(-effective_age2_dbh * RK)) ** RM2) / 10


        return SiteIndexValue(
            height,
            reference_age=Age.TOTAL(output_total_age),
            species={TreeSpecies.Sweden.picea_abies},
            fn=Hagglund_1970.height_trajectory.picea_abies.northern_sweden
        ), T13

    @staticmethod
    def southern_sweden(dominant_height: float,
                        age: Union[float, AgeMeasurement],
                        age2: Union[float, AgeMeasurement]) -> tuple[SiteIndexValue, float]:
        """
        Calculates the height trajectory of Norway Spruce in southern Sweden based on Hägglund (1973).

        As in the northern function, the input 'age' can be provided either as DBH or TOTAL.
        If provided as TOTAL, we solve using Newton–Raphson for the effective DBH age.
        For the prediction age 'age2', if provided as DBH then T13 is added.
        """
        if isinstance(age, AgeMeasurement):
            age_value = float(age)
            age_type = age.code
        else:
            age_value = float(age)
            age_type = Age.DBH.value

        if isinstance(age2, AgeMeasurement):
            age2_value = float(age2)
            age2_type = age2.code
        else:
            age2_value = float(age2)
            age2_type = Age.TOTAL.value

        top_height_dm = dominant_height * 10 - 13

        def subroutineBonitering(eff_age: float):
            AI1 = 10.0
            AI2 = 600.0
            while abs(AI1 - AI2) > 1:
                AI3 = (AI1 + AI2) / 2.0
                RK = 0.042624 - 7.1145 / AI3 ** 1.0068
                A2 = 1.0017 * AI3 ** 0.99808
                RM = 0.15933 + 3.7e6 / AI3 ** 3.156
                if RM > 0.95:
                    RM = 0.95
                RM2 = 0.98822 / (1 - RM)
                if RK < 0.0001:
                    RK = 0.0001
                DIF = top_height_dm - A2 * (1 - exp(-eff_age * RK)) ** RM2
                if DIF <= 0:
                    AI2 = AI3
                else:
                    AI1 = AI3
            T26 = (-1 / RK) * log(1 - (13 / A2) ** (1 / RM2))
            T13_local = 4.9546 + 0.63934 * T26 + 0.031992 * T26 * T26
            return A2, RK, RM2, T26, T13_local

        if age_type == Age.DBH.value:
            eff_age = age_value
        else:
            def f(x):
                _, _, _, _, T13_local = subroutineBonitering(x)
                return x + T13_local - age_value

            def fprime(x, h=0.001):
                return (f(x+h) - f(x-h)) / (2*h)

            x = age_value * 0.35
            for i in range(30):
                fx = f(x)
                fpx = fprime(x)
                if abs(fpx) < 1e-8:
                    break
                x_new = x - fx / fpx
                if abs(x_new - x) < 1e-6:
                    x = x_new
                    break
                x = x_new
            eff_age = x

        A2, RK, RM2, T26, T13 = subroutineBonitering(eff_age)
        if A2 > 400:
            warnings.warn("Too high productivity, outside of the material.")
        if A2 < 250:
            warnings.warn("Too low productivity, outside of the material.")
        if A2 > 375 and top_height_dm > 267:
            warnings.warn("Too old stand, outside of the material.")
        if eff_age > 90:
            warnings.warn("Too old stand, outside of the material.")

            # Determine the effective DBH age for the height prediction:
        if age2_type == Age.DBH.value:
            # If the target age 'age2' is already DBH, use its value directly for the formula.
            effective_age2_dbh = age2_value
            # The corresponding total age for output reference (if needed) would be:
            output_total_age = age2_value + T13
        else: # age2_type is TOTAL
            # If the target age 'age2' is TOTAL, calculate the corresponding effective DBH age.
            # We use the T13 calculated based on the input conditions (age, dominant_height).
            effective_age2_dbh = age2_value - T13
            # Check for potentially non-physical results (e.g., total age less than T13)
            if effective_age2_dbh <= 0:
                 warnings.warn(f"Calculated effective DBH age for prediction ({effective_age2_dbh:.2f}) is non-positive. "
                               f"This might happen if age2 (Total Age={age2_value}) is less than T13 ({T13:.2f}). "
                               f"Using a small positive value (e.g., 1.0) instead.", stacklevel=2)
                 effective_age2_dbh = 1.0 # Use a small positive fallback or handle as an error
            # The corresponding total age for output reference is the input total age itself:
            output_total_age = age2_value

        # Calculate height using the derived effective DBH age
        height = (13 + A2 * (1 - exp(-effective_age2_dbh * RK)) ** RM2) / 10

        return SiteIndexValue(
            height,
            reference_age=Age.TOTAL(output_total_age),
            species={TreeSpecies.Sweden.picea_abies},
            fn=Hagglund_1970.height_trajectory.picea_abies.southern_sweden
        ), T13

class HagglundPineRegeneration(Enum):
    CULTURE = "culture"
    NATURAL = "natural"
    UNKNOWN = "unknown"

    def __str__(self):
        return self.value

class HagglundPineModel:
    @staticmethod
    def sweden(dominant_height_m: float,
               age: Union[float, AgeMeasurement],
               age2: Union[float, AgeMeasurement],
               regeneration: HagglundPineRegeneration) -> tuple[SiteIndexValue, float]:
        """
        Hägglund 1974: Height growth of Scots Pine in Sweden.
        The forward-only solver is used.
          - For 'age': if provided as Age.TOTAL, we solve using Newton–Raphson for the effective DBH age.
          - For 'age2': if Age.DBH is provided, T13 is added.
        """
        if not isinstance(regeneration, HagglundPineRegeneration):
            raise TypeError('regeneration argument must be of type HagglundPineRegeneration')
        if isinstance(age, AgeMeasurement):
            age_value = float(age)
            age_type = age.code
        else:
            age_value = float(age)
            age_type = Age.DBH.value

        if isinstance(age2, AgeMeasurement):
            age2_value = float(age2)
            age2_type = age2.code
        else:
            age2_value = float(age2)
            age2_type = Age.TOTAL.value

        top_height_dm = dominant_height_m * 10 - 13

        if age_value > 120:
            print("Warning: Too old stand, outside of the material.")

        def subroutineBonitering(eff_age: float):
            AI1 = 10.0
            AI2 = 600.0
            while abs(AI1 - AI2) > 1:
                AI3 = (AI1 + AI2) / 2.0
                RM = 0.066074 + 4.4189e5 / AI3 ** 2.9134
                RM = min(RM, 0.95)
                RM2 = 1.0 / (1 - RM)
                RK = 1.0002e-4 + 9.5953 * AI3 ** 1.3755 / 1e6
                RK = max(RK, 0.0001)
                A2 = 1.0075 * AI3
                DIF = top_height_dm - A2 * (1 - math.exp(-eff_age * RK)) ** RM2
                if DIF <= 0:
                    AI2 = AI3
                else:
                    AI1 = AI3
            T26 = (-1 / RK) * math.log(1 - (13 / A2) ** (1 / RM2))
            T262 = T26 ** 2
            if regeneration == HagglundPineRegeneration.NATURAL:
                T13_local = 7.4624 + 0.11672 * T262
            elif regeneration == HagglundPineRegeneration.UNKNOWN:
                T13_local = 6.8889 + 0.12405 * T262
            elif regeneration == HagglundPineRegeneration.CULTURE:
                T13_local = 7.4624 + 0.11672 * T262 - 0.39276 * T26
            T13_local = min(T13_local, 50)
            return A2, RK, RM2, T13_local

        if age_type == Age.DBH.value:
            eff_age = age_value
        else:
            def f(x):
                _, _, _, T13_local = subroutineBonitering(x)
                return x + T13_local - age_value

            def fprime(x, h=0.001):
                return (f(x+h) - f(x-h)) / (2*h)

            x = age_value * 0.35
            for i in range(30):
                fx = f(x)
                fpx = fprime(x)
                if abs(fpx) < 1e-8:
                    break
                x_new = x - fx / fpx
                if abs(x_new - x) < 1e-6:
                    x = x_new
                    break
                x = x_new
            eff_age = x

        A2, RK, RM2, T13 = subroutineBonitering(eff_age)
        if A2 > 311:
            print("Warning: Too high productivity, outside of the material.")
        if A2 < 180:
            print("Warning: Too low productivity, outside of the material.")
        if A2 > 250 and eff_age > 100:
            print("Warning: Too old stand, outside of material.")

            # Determine the effective DBH age for the height prediction:
        if age2_type == Age.DBH.value:
            # If the target age 'age2' is already DBH, use its value directly for the formula.
            effective_age2_dbh = age2_value
            # The corresponding total age for output reference (if needed) would be:
            output_total_age = age2_value + T13
        else: # age2_type is TOTAL
            # If the target age 'age2' is TOTAL, calculate the corresponding effective DBH age.
            # We use the T13 calculated based on the input conditions (age, dominant_height).
            effective_age2_dbh = age2_value - T13
            # Check for potentially non-physical results (e.g., total age less than T13)
            if effective_age2_dbh <= 0:
                 warnings.warn(f"Calculated effective DBH age for prediction ({effective_age2_dbh:.2f}) is non-positive. "
                               f"This might happen if age2 (Total Age={age2_value}) is less than T13 ({T13:.2f}). "
                               f"Using a small positive value (e.g., 1.0) instead.", stacklevel=2)
                 effective_age2_dbh = 1.0 # Use a small positive fallback or handle as an error
            # The corresponding total age for output reference is the input total age itself:
            output_total_age = age2_value

        # Calculate height using the derived effective DBH age
        height = (13 + A2 * (1 - exp(-effective_age2_dbh * RK)) ** RM2) / 10

        # Return the SiteIndexValue, referencing the corresponding TOTAL age.
        # This standardizes the output reference age type.
        return SiteIndexValue(
            height,
            reference_age=Age.TOTAL(output_total_age), # Always reference total age
            species={TreeSpecies.Sweden.pinus_sylvestris},
            fn=Hagglund_1970.height_trajectory.pinus_sylvestris.sweden
        ), T13
        
# =============================================================================
# Container wrappers to select return value
# =============================================================================

class HeightTrajectoryWrapper:
    """
    Wrapper that calls the underlying model function and returns only the SiteIndexValue.
    """
    def __init__(self, model):
        self._model = model

    def __getattr__(self, name):
        attr = getattr(self._model, name)
        if callable(attr):
            def wrapper(*args, **kwargs):
                si_value, _ = attr(*args, **kwargs)
                return si_value
            return wrapper
        return attr

class TimeToBreastHeightWrapper:
    """
    Wrapper that calls the underlying model function and returns only the T13 value.
    """
    def __init__(self, model):
        self._model = model

    def __getattr__(self, name):
        attr = getattr(self._model, name)
        if callable(attr):
            def wrapper(*args, **kwargs):
                _, T13 = attr(*args, **kwargs)
                return T13
            return wrapper
        return attr

# =============================================================================
# Container class to expose species-specific models
# =============================================================================

class Hagglund_1970:
    """
    Provides a class-based interface to Hägglund's site index functions.
    Callers can choose to obtain either the height trajectory (site index)
    or the time to breast height (T13).
    """
    height_trajectory = type("HeightTrajectoryContainer", (), {
        "picea_abies": HeightTrajectoryWrapper(HagglundSpruceModel),
        "pinus_sylvestris": HeightTrajectoryWrapper(HagglundPineModel)
    })
    time_to_breast_height = type("TimeToBreastHeightContainer", (), {
        "picea_abies": TimeToBreastHeightWrapper(HagglundSpruceModel),
        "pinus_sylvestris": TimeToBreastHeightWrapper(HagglundPineModel)
    })
    regeneration = HagglundPineRegeneration
