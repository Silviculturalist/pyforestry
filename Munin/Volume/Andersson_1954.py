import math

def andersson_1954_volume_small_trees_birch_height_above_4_m(diameter_cm, height_m):
    """
    Andersson 1954 volume for small trees, Birch.
    
    Description:
        Suitable for trees taller than 4 m.
    
    Source:
        Andersson, S.-O. 1954. Funktioner och tabeller för kubering av småträd. 
        Meddelanden från Statens Skogsforskningsinstitut 44:12, 29 s.
        Available: https://www.skogskunskap.se/rakna-med-verktyg/mata-skogen/volymberakning/volymfunktioner/
    
    Parameters:
        diameter_cm (float): Diameter in cm.
        height_m (float): Height in m.
    
    Returns:
        float: Volume in dm³.
    """
    return math.exp(
        -4.49213 
        + 2.10253 * math.log(diameter_cm) 
        + 3.98519 * math.log(height_m) 
        - 2.65900 * math.log(height_m - 1.3) 
        - 0.0140970 * diameter_cm
    )

def andersson_1954_volume_small_trees_birch_under_diameter_5_cm(diameter_cm, height_m):
    """
    Andersson 1954 volume for small trees, Birch.
    
    Description:
        Suitable for diameters < 5 cm.
    
    Source:
        Andersson, S.-O. 1954. Funktioner och tabeller för kubering av småträd. 
        Meddelanden från Statens Skogsforskningsinstitut 44:12, 29 s.
        Available: https://www.skogskunskap.se/rakna-med-verktyg/mata-skogen/volymberakning/volymfunktioner/
    
    Parameters:
        diameter_cm (float): Diameter in cm.
        height_m (float): Height in m.
    
    Returns:
        float: Volume in dm³.
    """
    return (
        0.11 
        + 0.1302 * (diameter_cm ** 2) 
        + 0.01063 * (diameter_cm ** 2) * height_m 
        + 0.007981 * diameter_cm * (height_m ** 2)
    )

def andersson_1954_volume_small_trees_pine(diameter_cm, height_m):
    """
    Andersson 1954 volume for small trees, Pine.
    
    Description:
        Suitable for diameters < 5 cm.
    
    Source:
        Andersson, S.-O. 1954. Funktioner och tabeller för kubering av småträd. 
        Meddelanden från Statens Skogsforskningsinstitut 44:12, 29 s.
        Available: https://www.skogskunskap.se/rakna-med-verktyg/mata-skogen/volymberakning/volymfunktioner/
    
    Parameters:
        diameter_cm (float): Diameter in cm.
        height_m (float): Height in m.
    
    Returns:
        float: Volume in dm³.
    """
    return (
        0.22 
        + 0.1066 * (diameter_cm ** 2) 
        + 0.02085 * (diameter_cm ** 2) * height_m 
        + 0.008427 * diameter_cm * (height_m ** 2)
    )

def andersson_1954_volume_small_trees_spruce(diameter_cm, height_m):
    """
    Andersson 1954 volume for small trees, Spruce.
    
    Description:
        Suitable for diameters < 5 cm.
    
    Source:
        Andersson, S.-O. 1954. Funktioner och tabeller för kubering av småträd. 
        Meddelanden från Statens Skogsforskningsinstitut 44:12, 29 s.
        Available: https://www.skogskunskap.se/rakna-med-verktyg/mata-skogen/volymberakning/volymfunktioner/
    
    Parameters:
        diameter_cm (float): Diameter in cm.
        height_m (float): Height in m.
    
    Returns:
        float: Volume in dm³.
    """
    return (
        0.22 
        + 0.1086 * (diameter_cm ** 2) 
        + 0.01712 * (diameter_cm ** 2) * height_m 
        + 0.008905 * diameter_cm * (height_m ** 2)
    )
