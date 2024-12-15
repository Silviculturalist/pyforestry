def Odin_temperature_sum(latitude, altitude_m):
    '''
    Estimate annual temperature sum above 5°C.

    This function calculates the annual temperature sum (in degree-days) above 5 degrees Celsius 
    based on latitude and altitude. It uses an empirical model developed by Odin, Eriksson, 
    and Perttu (1983).

    Source:
        Odin, Eriksson & Perttu (1983). "Temperature Climate Maps for Swedish Forestry." 
        Reports in Forest Ecology and Forest Soils, 45, p.45.

    Parameters
    ----------
    latitude : float
        Decimal latitude (degrees north).
    altitude_m : float
        Altitude in meters above sea level.

    Returns
    -------
    float
        Estimated annual temperature sum > 5 degrees Celsius.
    '''
    return 4835 - (57.6 * latitude) - (0.9 * altitude_m)
