def si_to_bonitet(H100, main_species, vegetation, altitude, county):
    """
    Calculate smoothed productivity estimates in m3sk (cu.m.) from Hägglund 1981.
    
    Parameters:
        H100 (float): Estimated stand top height at 100 years age.
        main_species (str): Main species, one of: 'Picea abies' or 'Pinus sylvestris'.
        vegetation (int): Vegetation class.
        altitude (float): Altitude in meters above sea level.
        county (str): Swedish county.
    
    Returns:
        float: Mean volume growth in m3sk / ha yr-1 at the time of culmination (or at 150 years for late culmination).
    """
    # Validate inputs
    if not isinstance(H100, (int, float)) or H100 <= 0:
        raise ValueError("H100 must be a positive numeric value.")
    
    F1 = 0.72 + (H100 / 130)
    F2 = 0.70 + (H100 / 100)
    fun = None
    
    # Updated county mappings for Northern Sweden
    northern_counties = [
        "Norrbottens lappmark (BD lappm)", "Norrbottens kustland (BD kust)", 
        "Västerbottens lappmark (AC lappm)", "Västerbottens kustland (AC kust)", 
        "Västernorrland - Ångermanlands landskap (Y Ångerm)", "Västernorrland - Medelpads landskap (Y Medelp)", 
        "Jämtland - Jämtlands landskap (Z)", "Jämtland - Härjedalens landskap (Z Härjed)", 
        "Kopparberg (Dalarna), Sälen - Idre (W)"
    ]
    
    # Updated county mappings for Middle Sweden
    middle_counties = [
        "Kopparberg (Dalarna), övriga (W övr)", "Gävleborg - Hälsinglands landskap (X Hälsingl)", 
        "Gävleborg, övriga (X övr)", "Kopparberg (Dalarna), övriga (W övr)", "Värmland (S)"
    ]
    
    # Determine function based on species, county, vegetation, and altitude
    if main_species == "Picea abies":
        if county in northern_counties:
            fun = "d" if vegetation <= 9 else "e"
        elif county in middle_counties:
            fun = "b" if vegetation <= 9 else "c"
        else:
            fun = "a"
    elif main_species == "Pinus sylvestris":
        # For Pine: Northern Sweden with altitude >= 200 meters
        fun = "g" if county in northern_counties and altitude >= 200 else "f"
    
    if fun is None:
        raise ValueError(f"Unrecognized combination of inputs for main_species: {main_species}")
    
    # Calculate bonitet based on the function
    if fun == "a":
        bon = (0.57207 + 0.22166 * H100 + 0.0050164 * H100 ** 2) * F1
    elif fun == "b":
        bon = (1.28417 + 0.31060 * H100 + 0.0020048 * H100 ** 2) * F1
    elif fun == "c":
        bon = (-0.42289 + 0.17735 * H100 + 0.0050580 * H100 ** 2) * F1
    elif fun == "d":
        bon = (-0.75761 + 0.24393 * H100 + 0.0014564 * H100 ** 2) * F2
    elif fun == "e":
        bon = (-0.59224 + 0.21765 * H100 + 0.0011391 * H100 ** 2) * F2
    elif fun == "f":
        bon = (-0.39456 + 0.16469 * H100 + 0.0047191 * H100 ** 2) * F2
    elif fun == "g":
        bon = (0.099227 + 0.067873 * H100 + 0.0066316 * H100 ** 2) * F2
    else:
        raise ValueError(f"{fun} is an unrecognized function. Please use one between 'a' and 'g'.")
    
    return bon
