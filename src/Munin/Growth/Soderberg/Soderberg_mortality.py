import math

def soderberg_1986_ba_percentual_mortality_per_annum(
    SI_species,
    SIH100,
    total_age_stand,
    Basal_area_plot_m2_ha,
    Basal_area_Spruce_m2_ha,
    Basal_area_Deciduous_m2_ha
):
    """
    Mortality in self-thinned stands.

    Source:
        Söderberg, U. (1986). Funktioner för skogliga produktionsprognoser - 
        Tillväxt och formhöjd för enskilda träd av inhemska trädslag i Sverige.
        Section of Forest Mensuration and Management. Swedish University of Agricultural Sciences.

    Description:
        Material from unthinned permanent plots.
        Note: This function is intended for plots with very high basal area.

    Details:
        - Multiple correlation coefficient R = 0.40
        - Spread about the function sf = 0.0059
        - sf / Spread about the mean = 92.7
        - Number of observations = 532

    Parameters:
        SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
        SIH100 (float): Site Index H100, metres.
        total_age_stand (int): Total age of the stand.
        Basal_area_plot_m2_ha (float): Basal area of all tree species on the plot, m²/ha.
        Basal_area_Spruce_m2_ha (float): Basal area of spruce on the plot, m²/ha.
        Basal_area_Deciduous_m2_ha (float): Basal area of deciduous trees on the plot, m²/ha.

    Returns:
        float: Mortality as annual proportion of basal area.
    """
    BA_quotient_Spruce = Basal_area_Spruce_m2_ha / Basal_area_plot_m2_ha
    BA_quotient_Deciduous = Basal_area_Deciduous_m2_ha / Basal_area_plot_m2_ha
    spruce = 1 if SI_species == "Picea abies" else 0
    pine = 1 if SI_species == "Pinus sylvestris" else 0

    return (
        +0.60949 * (1 / (total_age_stand + 10)) +
        -12.5903 * ((1 / (total_age_stand + 10)) ** 2) +
        +0.0003317 * Basal_area_plot_m2_ha +
        -0.01006 * math.log(Basal_area_plot_m2_ha) +
        +0.000173 * spruce * SIH100 +
        +0.000156 * pine * SIH100 +
        -0.0130 * BA_quotient_Spruce +
        +0.0119 * (BA_quotient_Spruce ** 2) +
        +0.0189 * BA_quotient_Deciduous +
        -0.0174 * (BA_quotient_Deciduous ** 2) +
        +0.0232
    )


def soderberg_1986_ba_self_thinned_stands(
    SI_species,
    SIH100,
    total_age_stand,
    BA_quotient_Spruce,
    BA_quotient_Deciduous,
    stems_per_ha
):
    """
    Basal area in self-thinned stands.

    Source:
        Söderberg, U. (1986). Funktioner för skogliga produktionsprognoser - 
        Tillväxt och formhöjd för enskilda träd av inhemska trädslag i Sverige.
        Section of Forest Mensuration and Management. Swedish University of Agricultural Sciences.

    Description:
        Material from unthinned permanent plots.

    Details:
        - Multiple correlation coefficient R = 0.87
        - Spread about the function sf = 0.15
        - sf / Spread about the mean = 50.2
        - Number of observations = 532

    Parameters:
        SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
        SIH100 (float): Site Index H100, metres.
        total_age_stand (int): Total age of the stand.
        BA_quotient_Spruce (float): Basal area Spruce / Basal area.
        BA_quotient_Deciduous (float): Basal area Deciduous trees / Basal area.
        stems_per_ha (int): Number of stems per hectare.

    Returns:
        float: Basal area in m²/ha.
    """
    spruce = 1 if SI_species == "Picea abies" else 0
    pine = 1 if SI_species == "Pinus sylvestris" else 0

    return math.exp(
        -18.612 * (1 / (total_age_stand + 10)) +
        -765.295 * ((1 / (total_age_stand + 10)) ** 2) +
        +0.04798 * SIH100 * spruce +
        +0.05589 * SIH100 * pine +
        +0.00006717 * stems_per_ha +
        -0.00000002864 * (stems_per_ha ** 2) +
        +0.7204 * BA_quotient_Spruce +
        -0.4879 * (BA_quotient_Spruce ** 2) +
        +0.1062 * BA_quotient_Deciduous +
        -0.2073 * (BA_quotient_Deciduous ** 2) +
        +2.5225
    )
