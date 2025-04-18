import numpy as np

def Eriksson_1973_volume_aspen_Sweden(diameter_cm:float,height_m:float)->float:
    """
    Calculates the volume of a Ash, Aspen, Alnus glutinosa tree in m³ according to Eriksson (1973).

    Parameters:
        height (float): Tree height in dm.
        diameter (float): Tree diameter in cm.

    Returns:
        float: Calculated volume in m³.
    
    Reference:
        Eriksson, H. (1973). Volymfunktioner för stående träd av ask, asp, klibbal och contortatall.
        Skogshögskolan, institutionen för skogsproduktion. Rapp. o. Upps. nr 26.
    """
    # Calculate diameter squared (cm²)
    diameter_power_two = diameter_cm ** 2
    
    # Convert height from dm to m
    height_power_two = height_m ** 2
    
    volume = (diameter_power_two * 0.01548 +
              diameter_power_two * height_m * 0.03255 -
              diameter_power_two * height_power_two * 0.000047 -
              diameter_cm * height_m * 0.01333 +
              diameter_cm * height_power_two * 0.004859)
    return volume/1000 #Original in dm3

def Eriksson_1973_volume_lodgepole_pine_Sweden(diameter_cm:float,height_m:float)->float:
    """
    Calculates the volume of a Lodgepole Pine tree in m³ according to Eriksson (1973).

    Parameters:
        height (float): Tree height in dm.
        diameter (float): Tree diameter in cm.

    Returns:
        float: Calculated volume in m³.
    
    Reference:
        Eriksson, H. (1973). Volymfunktioner för stående träd av ask, asp, klibbal och contortatall.
        Skogshögskolan, institutionen för skogsproduktion. Rapp. o. Upps. nr 26.
    """

    # Calculate powers of diameter and height
    d2 = diameter_cm * diameter_cm
    h2 = height_m * height_m

    # Compute the volume using the given coefficients
    volume = (0.1121 * d2 +
              0.02870 * d2 * height_m +
              -0.000061 * d2 * h2 +
              -0.09176 * diameter_cm * height_m +
              0.01249 * diameter_cm * h2)
    return volume/1000
