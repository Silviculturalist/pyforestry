def agestam_1985_si_translation_pine_to_birch(si_pine):
    """
    Translate SI H100 for Pine to Birch according to Hägglund (1974), from Agestam (1985).

    This function converts the site index (SI) H100 for Pine to Birch, based on
    empirical relationships presented by Agestam (1985).

    Parameters:
        si_pine (float): Site index (SI) H100 for Pine in meters.

    Returns:
        float: Site index (SI) H100 for Birch in meters.

    Reference:
        Agestam, E. (1985). "A growth simulator for mixed stands of pine, spruce, and birch in Sweden."
        Diss. Swedish University of Agricultural Sciences. Report no. 15. Dept. of Forest Yield Research.
        ISBN 91-576-2528-x. Garpenberg, Sweden; page 79.
    """
    return ((0.736 * (si_pine * 10)) - 21.1) / 10


def agestam_1985_si_translation_spruce_to_birch(si_spruce):
    """
    Translate SI H100 for Spruce to Birch according to Hägglund (1974), from Agestam (1985).

    This function converts the site index (SI) H100 for Spruce to Birch, based on
    empirical relationships presented by Agestam (1985).

    Parameters:
        si_spruce (float): Site index (SI) H100 for Spruce in meters.

    Returns:
        float: Site index (SI) H100 for Birch in meters.

    Reference:
        Agestam, E. (1985). "A growth simulator for mixed stands of pine, spruce, and birch in Sweden."
        Diss. Swedish University of Agricultural Sciences. Report no. 15. Dept. of Forest Yield Research.
        ISBN 91-576-2528-x. Garpenberg, Sweden; page 79.
    """
    return ((0.382 * (si_spruce * 10)) + 75.8) / 10
