# This file implements the Site index functions created by Björn Hägglund during the 1970's for Norway Spruce and Scots Pine in Sweden 
# version 0.1 Carl Vigren 2024-12-14

import warnings 
from numpy import exp, log

def Hagglund1972SpruceHeightTrajectoryNorthernSweden(dominantHeight,age,age2,latitude,culture=True):
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
    
    P = 0.9175**culture
    top_height_dm = dominantHeight*10
    top_height_dm = top_height_dm - 13
    
    if(age>(407-1.167*top_height_dm)):
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
        
    return (13+A2*(1-exp(-age2*RK))**RM2)/10, T13


def getSIH100_Hagglund1972SpruceNorthernSweden(dominantHeight,age,latitude,culture=True):
    """
    Computes the site index at age 100 for Norway Spruce in northern Sweden.

    Parameters:
        dominantHeight (float): Dominant height of the stand (meters).
        age (int): Stand age (years) at breast height (1.3 meters).
        latitude (float): Latitude of the stand (degrees). Must be between 60° and 67° N.
        culture (bool): Indicates if the stand is cultured (True) or natural (False). Defaults to True.

    Returns:
        float: Site index (SIH100) based on total age at 100 years.

    Raises:
        Warning: If the input values are outside the material range.

    Reference:
        Hägglund, Björn (1972) Om övre höjdens utveckling för gran i norra
        Sverige: Site index curves for Norway Spruce in northern Sweden. Diss. Dept.
        of Forest Yield Research. Royal College of Forestry. Report 21. 298 pp. Stockholm.
    """
    
    P = 0.9175**culture
    top_height_dm = dominantHeight*10
    top_height_dm = top_height_dm - 13
    
    if(age>(407-1.167*top_height_dm)):
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
    return((13+A2*(1-exp((T13-100)*RK))**RM2)/10)



def Hagglund_1973_southern_Sweden_Height_trajectories_Spruce(dominantHeight,age,age2):
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

  top_height_dm = dominantHeight*10
  top_height_dm = top_height_dm - 13


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

  if(A2>375 & top_height_dm>267):
    warnings.warn("Too old stand, outside of the material.")

  if(age>90):
    warnings.warn("Too old stand, outside of the material.")

  return (13+A2*(1-exp(-age2*RK))**RM2)/10, T13


def getSIH100_Hagglund1973SpruceSouthernSweden(dominantHeight, age):
  """
    Computes the site index at age 100 for Norway Spruce in southern Sweden.

    Parameters:
        dominantHeight (float): Dominant height of the stand (meters).
        age (int): Stand age (years) at breast height (1.3 meters).

    Returns:
        float: Site index (SIH100) based on total age at 100 years.

    Raises:
        Warning: If the input values are outside the material range.

    Reference:
        Hägglund, Björn (1973) Om övre höjdens utveckling för gran i södra
        Sverige: Site index curves for Norway Spruce in southern Sweden. Diss. Dept.
        of Forest Yield Research. Royal College of Forestry. Report 24. 49 pp. Stockholm.
  """
    
  top_height_dm = dominantHeight*10
  top_height_dm = top_height_dm - 13


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

  if(A2>375 & top_height_dm>267):
    warnings.warn("Too old stand, outside of the material.")

  if(age>90):
    warnings.warn("Too old stand, outside of the material.")

  return (13+A2*(1-exp((T13-100)*RK))**RM2)/10