"""Volume equation for hybrid aspen from Johnsson (1953)."""


def johnsson_1953_volume_hybrid_aspen(diameter_cm, height_m):
    """
    Calculate stem volume for Hybrid Aspen based on Johnsson (1953).

    This function estimates the stem volume over bark for Hybrid Aspen trees in cubic meters
    using diameter at breast height and tree height.

    Parameters:
        diameter_cm (float): Diameter at breast height (cm).
        height_m (float): Height of the tree (meters).

    Returns:
        float: Stem volume over bark (m³).

    References:
        Johnsson, H. (1953). "Hybridaspens ungdomsutveckling och ett försök till framtidsprognos."
        Svenska skogsvårdsföreningens tidsskrift. 51:73-96.

        Rytter, L., Stener, L.-G. (2014). "Growth and thinning effects during a rotation period of
        hybrid aspen in southern Sweden." Scandinavian Journal of Forest Research, Vol. 29,
        Issue 8, pp. 747-756. DOI: https://doi.org/10.1080/02827581.2014.968202
    """
    # Calculate volume in dm³
    volume_dm3 = (
        0.03186 * (diameter_cm**2) * height_m
        + 0.43 * height_m
        + 0.0551 * (diameter_cm**2)
        - 0.4148 * diameter_cm
    )

    # Convert volume to m³
    volume_m3 = volume_dm3 / 1000  # 1000 dm³ in 1 m³
    return volume_m3
