from Munin.Helpers.Base import TreeSpecies, TopHeightDefinition, SiteIndexValue, Age, AgeMeasurement
from Munin.Helpers.TreeSpecies import TreeSpecies
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
                        culture: bool = True) -> tuple[SiteIndexValue,float]:
    """
    Calculates the height trajectory of Norway Spruce in northern Sweden based on Hägglund (1972).

    Parameters:
        dominantHeight (float): Dominant height of the stand (meters).
        age (int): Stand age (years) at breast height (1.3 meters).
        age2 (int): Future age for which the height is to be computed.
        latitude (float): Latitude of the stand (degrees). Must be between 60° and 67° N.
        culture (bool): Indicates if the stand is cultured (True) or natural (False). Defaults to True.

    Returns:
        tuple: A tuple containing:
            - Height at age2 (float, meters).
            - Time to reach breast height (T13, float, years).

    Raises:
        Warning: If the input values are outside the material range.

    Reference:
        Hägglund, Björn (1972) Om övre höjdens utveckling för gran i norra
        Sverige: Site index curves for Norway Spruce in northern Sweden. Diss. Dept.
        of Forest Yield Research. Royal College of Forestry. Report 21. 298 pp. Stockholm.



    """
    #Age Validation
    # Check for age (should be a float/int or AgeMeasurement with DBH code)
    if isinstance(age, AgeMeasurement):
        # It's an AgeMeasurement, check the code
        if age.code != Age.DBH.value:
            raise TypeError("Parameter 'age' must be a float/int or an instance of Age.DBH.")
    elif not isinstance(age, (float, int)):
        # It's not an AgeMeasurement and not a float/int
        raise TypeError("Parameter 'age' must be a float/int or an instance of Age.DBH.")
    # If we reach here, it's either a valid Age.DBH or a float/int - proceed
    if isinstance(age2, AgeMeasurement):
        # It's an AgeMeasurement, check the code
        if age2.code != Age.TOTAL.value:
            raise TypeError("Parameter 'age2' must be a float/int or an instance of Age.TOTAL.")
    elif not isinstance(age2, (float, int)):
        # It's not an AgeMeasurement and not a float/int
        raise TypeError("Parameter 'age2' must be a float/int or an instance of Age.TOTAL.")
    # If we reach here, it's either a valid Age.TOTAL or a float/int - proceed



    P = 0.9175 if culture else 1.0

      # Adjust dominant height (convert meters to decimeters and subtract height at diameter measurement)
    top_height_dm = dominant_height * 10 - 13

    #Check material limits on age..
    if age > (407 - 1.167 * top_height_dm):
            warnings.warn("Too old stand, outside of the material.")

    if(latitude>=67 or latitude<=60):
        warnings.warn("Outside of latitudinal range, 60°<= L <= 67° N, using function 8.4 ")
        #function 8.4
        B =  3.4501
        C = 0.77518
        D = -0.42579
        E = 1.33935
    else:
        #function 8.7
        B = 3.3816
        C = 0.77896
        D = -1.24207 + 0.0014629*latitude*10
        E = 1.25998

    def subroutineBonitering(top_height=top_height_dm,
                             age=age,
                             B=B, 
                             C=C,
                             D=D,
                             E=E):
        
        AI1 = 10
        AI2 = 600
        
        while(abs(AI1-AI2)>1):
            AI3 = (AI1+AI2)/2
            RK = 0.001936+0.00004100*AI3**1.0105
            A2 = B*AI3**C
            RM2 = D+E/(0.56721+0.000008*AI3**1.8008)
            DIF = top_height-A2*(1-exp(-age*RK))**RM2
            if(DIF<=0):
                AI2 = AI3
            else:
                AI1 = AI3

        return A2, RK, RM2
    

    A2, RK, RM2 = subroutineBonitering()

    if(A2>336):
        warnings.warn('Too high productivity, outside of material.')
    if(A2<189):
        warnings.warn('Too low productivity, outside of material.')

    T26 = (-1/RK)*log(1-(13/A2)**(1/RM2))
    T13 = P*(7.0287+0.66118*T26)
        
    return SiteIndexValue(
       (13+A2*(1-exp(-age2*RK))**RM2)/10,
       reference_age=Age.TOTAL(age2),
       species={TreeSpecies.Sweden.picea_abies},
       fn=Hagglund_1970.height_trajectory.picea_abies.northern_sweden
    ), T13
   
   @staticmethod
   def southern_sweden(dominant_height: float,
                       age: Union[float,AgeMeasurement],
                       age2: Union[float,AgeMeasurement]) -> tuple[SiteIndexValue,float]:
        """
        Calculates the height trajectory of Norway Spruce in southern Sweden based on Hägglund (1973).

        Parameters:
            dominantHeight (float): Dominant height of the stand (meters).
            age (int): Stand age (years) at breast height (1.3 meters).
            age2 (int): Future age for which the height is to be computed.

        Returns:
            tuple: A tuple containing:
                - Height at age2 (float, meters).
                - Time to reach breast height (T13, float, years).

        Raises:
            Warning: If the input values are outside the material range.

        Reference:
            Hägglund, Björn (1973) Om övre höjdens utveckling för gran i södra
            Sverige: Site index curves for Norway Spruce in southern Sweden. Diss. Dept.
            of Forest Yield Research. Royal College of Forestry. Report 24. 49 pp. Stockholm.
        """

        #Age Validation
        # Check for age (should be a float/int or AgeMeasurement with DBH code)
        if isinstance(age, AgeMeasurement):
            # It's an AgeMeasurement, check the code
            if age.code != Age.DBH.value:
                raise TypeError("Parameter 'age' must be a float/int or an instance of Age.DBH.")
        elif not isinstance(age, (float, int)):
            # It's not an AgeMeasurement and not a float/int
            raise TypeError("Parameter 'age' must be a float/int or an instance of Age.DBH.")
        # If we reach here, it's either a valid Age.DBH or a float/int - proceed
        if isinstance(age2, AgeMeasurement):
            # It's an AgeMeasurement, check the code
            if age2.code != Age.TOTAL.value:
                raise TypeError("Parameter 'age2' must be a float/int or an instance of Age.TOTAL.")
        elif not isinstance(age2, (float, int)):
            # It's not an AgeMeasurement and not a float/int
            raise TypeError("Parameter 'age2' must be a float/int or an instance of Age.TOTAL.")
        # If we reach here, it's either a valid Age.TOTAL or a float/int - proceed


        top_height_dm = dominant_height*10 - 13


        def subroutine_bonitering(top_height=top_height_dm,age=age):
          AI1 = 10
          AI2 = 600

          while(abs(AI1-AI2)>1):
            AI3 = (AI1+AI2)/2
            RK = 0.042624-7.1145/AI3**1.0068
            A2 = 1.0017*AI3**0.99808
            RM = 0.15933+3.7*10**6/AI3**3.156

            if(RM>0.95):
              RM = 0.95

            RM2 = 0.98822/(1-RM)

            if(RK<0.0001):
              RK = 0.0001

            DIF = top_height-A2*(1-exp(-age*RK))**RM2

            if DIF<=0:
                AI2 = AI3
            else:
                AI1 = AI3

          T26 = (-1/RK)*log(1-(13/A2)**(1/RM2))
          T13 = 4.9546+0.63934*T26+0.031992*T26*T26

          return A2, RK, RM2, T26, T13

        A2, RK, RM2, T26, T13 = subroutine_bonitering()

        if(A2>400):
          warnings.warn("Too high productivity, outside of the material.")
        if(A2<250):
          warnings.warn("Too low productivity, outside of the material.")

        if(A2>375 and top_height_dm>267):
          warnings.warn("Too old stand, outside of the material.")

        if(age>90):
          warnings.warn("Too old stand, outside of the material.")

        return SiteIndexValue(
       (13+A2*(1-exp(-age2*RK))**RM2)/10,
       reference_age=Age.TOTAL(age2),
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
               regeneration: HagglundPineRegeneration) -> tuple[SiteIndexValue,float]: 
        """
        Hägglund 1974: Height growth of Scots Pine in Sweden.

        This function calculates the height of Scots Pine based on the Chapman-Richards 
        function and site-specific parameters. It is adapted from the Fortran IV script 
        in the original Hägglund 1974 source. The implementation accounts for warnings 
        when values are outside the material limits but does not halt execution.

        OBSERVE: Site index according to Hägglund is measured in total age.

        Parameters:
            dominant_height_m (float): Top height of the tree or stand in meters.
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
        #Age Validation
        # Check for age (should be a float/int or AgeMeasurement with DBH code)
        if isinstance(age, AgeMeasurement):
            # It's an AgeMeasurement, check the code
            if age.code != Age.DBH.value:
                raise TypeError("Parameter 'age' must be a float/int or an instance of Age.DBH.")
        elif not isinstance(age, (float, int)):
            # It's not an AgeMeasurement and not a float/int
            raise TypeError("Parameter 'age' must be a float/int or an instance of Age.DBH.")
        # If we reach here, it's either a valid Age.DBH or a float/int - proceed
        if isinstance(age2, AgeMeasurement):
            # It's an AgeMeasurement, check the code
            if age2.code != Age.TOTAL.value:
                raise TypeError("Parameter 'age2' must be a float/int or an instance of Age.TOTAL.")
        elif not isinstance(age2, (float, int)):
            # It's not an AgeMeasurement and not a float/int
            raise TypeError("Parameter 'age2' must be a float/int or an instance of Age.TOTAL.")
        # If we reach here, it's either a valid Age.TOTAL or a float/int - proceed

        if not isinstance(regeneration, HagglundPineRegeneration): 
            raise TypeError("Parameter 'regeneration' must be a Hagglund_1970.regeneration Enum.")

        top_height_dm = dominant_height_m * 10 - 13  # Convert to decimeters and adjust

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

            T26 = (-1 / RK) * math.log(1 - pow(13 / A2, 1 / RM2))
            T262 = T26**2

            if regeneration == Hagglund_1970.regeneration.NATURAL:
                T13 = 7.4624 + 0.11672 * T262
            elif regeneration == Hagglund_1970.regeneration.UNKNOWN:
                T13 = 6.8889 + 0.12405 * T262
            elif regeneration == Hagglund_1970.regeneration.CULTURE:
                T13 = 7.4624 + 0.11672 * T262 - 0.39276 * T26

            T13 = min(T13, 50)

            return A2, RK, RM2, T13

        A2, RK, RM2, T13 = subroutine_bonitering(top_height_dm, age, regeneration)

        if A2 > 311:
            print("Warning: Too high productivity, outside of the material.")
        if A2 < 180:
            print("Warning: Too low productivity, outside of the material.")
        if A2 > 250 and age > 100:
            print("Warning: Too old stand, outside of material.")

        # Return Height at age2
        return SiteIndexValue(
            (13 + A2 * (1 - math.exp(-age2 * RK))**RM2) / 10,
            reference_age=Age.TOTAL(age2),
            species={TreeSpecies.Sweden.pinus_sylvestris},
            fn=Hagglund_1970.height_trajectory.pinus_sylvestris.sweden), T13

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
        # Retrieve the attribute from the wrapped model, assuming it’s a callable.
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



#Container class to expose species-specific models

class Hagglund_1970:
    """
    Provides a class-based interface to Hägglund's site index functions.
    Callers can choose to return either the height trajectory (site index)
    or the time until breast height (T13).

    Examples:
        Hagglund1970.height_trajectory.PICEA_ABIES.northern_sweden(...)
        Hagglund1970.time_to_breast_height.PICEA_ABIES.northern_sweden(...)
    """
    # Expose species-specific models via wrappers.
    height_trajectory = type("HeightTrajectoryContainer", (), {
        "picea_abies": HeightTrajectoryWrapper(HagglundSpruceModel),
        "pinus_sylvestris": HeightTrajectoryWrapper(HagglundPineModel)
    })
    time_to_breast_height = type("TimeToBreastHeightContainer", (), {
        "picea_abies": TimeToBreastHeightWrapper(HagglundSpruceModel),
        "pinus_sylvestris": TimeToBreastHeightWrapper(HagglundPineModel)
    })
    regeneration = HagglundPineRegeneration
