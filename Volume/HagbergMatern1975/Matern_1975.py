def matern_1975_volume_sweden_oak(diameter_cm, height_m):
    """
    Calculate the volume of Oak trees based on Matérn (1975).

    This function estimates the volume of standing Oak trees in Sweden using 
    diameter at breast height and tree height.

    Parameters:
        diameter_cm (float): Diameter at breast height (cm).
        height_m (float): Height of the tree (meters).

    Returns:
        float: Volume of the tree (dm³).

    References:
        Matérn, B. (1975). "Volymfunktioner för stående träd av ek och bok." 
        Skogshögskolan, institutionen för skoglig matematisk statistik. Rapp. o. Upps. nr 15.
        PM for Heureka 2004-01-20 Björn Elfving. Available:
        https://www.heurekaslu.org/w/images/9/93/Heureka_prognossystem_(Elfving_rapportutkast).pdf
    """
    if height_m >= 10:
        # For trees with height >= 10 m
        volume = 0.03522 * (diameter_cm**2) * height_m + 0.08772 * diameter_cm * height_m - 0.04905 * (diameter_cm**2)
    else:
        # For trees with height < 10 m
        volume = (
            0.03522 * (diameter_cm**2) * height_m + 
            0.08772 * diameter_cm * height_m - 
            0.04905 * (diameter_cm**2) +
            ((1 - (height_m / 10))**2) * (
                0.01682 * (diameter_cm**2) * height_m + 
                0.01108 * diameter_cm * height_m - 
                0.02167 * diameter_cm * (height_m**2) + 
                0.04905 * (diameter_cm**2)
            )
        )
    return volume


def matern_1975_volume_sweden_beech(diameter_cm, height_m):
    """
    Calculate the volume of Beech trees based on Matérn (1975).

    This function estimates the volume of standing Beech trees in Sweden using 
    diameter at breast height and tree height.

    Parameters:
        diameter_cm (float): Diameter at breast height (cm).
        height_m (float): Height of the tree (meters).

    Returns:
        float: Volume of the tree (dm³).

    References:
        Matérn, B. (1975). "Volymfunktioner för stående träd av ek och bok." 
        Skogshögskolan, institutionen för skoglig matematisk statistik. Rapp. o. Upps. nr 15.
        PM for Heureka 2004-01-20 Björn Elfving. Available:
        https://www.heurekaslu.org/w/images/9/93/Heureka_prognossystem_(Elfving_rapportutkast).pdf
    """
    volume = (
        0.01275 * (diameter_cm**2) * height_m +
        0.12368 * (diameter_cm**2) +
        0.0004701 * (diameter_cm**2) * (height_m**2) +
        0.00622 * diameter_cm * (height_m**2)
    )
    return volume
