"""Utility functions translating site index between species."""

from pyforestry.base.contracts import FormulaDescriptor, SourceReference


def agestam_1985_si_translation_pine_to_birch(si_pine: float) -> float:
    """
    Translate SI H100 for Pine to Birch according to Hägglund (1974), from Agestam (1985).

    This function converts the site index (SI) H100 for Pine to Birch, based on
    empirical relationships presented by Agestam (1985).

    Parameters:
        si_pine (float): Site index (SI) H100 for Pine in meters.

    Returns:
        float: Site index (SI) H100 for Birch in meters.

    Reference:
        Agestam, E. (1985). "A growth simulator for mixed stands of pine, spruce, and birch in
        Sweden." Diss. Swedish University of Agricultural Sciences.
        Report no. 15. Dept. of Forest Yield Research.
        ISBN 91-576-2528-x. Garpenberg, Sweden; page 79.
    """
    pine_site_index_h100_dm = si_pine * 10.0
    birch_site_index_h100_dm = 0.736 * pine_site_index_h100_dm - 21.1
    return birch_site_index_h100_dm / 10.0


def agestam_1985_si_translation_spruce_to_birch(si_spruce: float) -> float:
    """
    Translate SI H100 for Spruce to Birch according to Hägglund (1974), from Agestam (1985).

    This function converts the site index (SI) H100 for Spruce to Birch, based on
    empirical relationships presented by Agestam (1985).

    Parameters:
        si_spruce (float): Site index (SI) H100 for Spruce in meters.

    Returns:
        float: Site index (SI) H100 for Birch in meters.

    Reference:
        Agestam, E. (1985). "A growth simulator for mixed stands of pine, spruce, and birch in
        Sweden." Diss. Swedish University of Agricultural Sciences.
        Report no. 15. Dept. of Forest Yield Research.
        ISBN 91-576-2528-x. Garpenberg, Sweden; page 79.
    """
    spruce_site_index_h100_dm = si_spruce * 10.0
    birch_site_index_h100_dm = 0.382 * spruce_site_index_h100_dm + 75.8
    return birch_site_index_h100_dm / 10.0


DESCRIPTOR = FormulaDescriptor(
    component_id="agestam_1985_siteindex",
    source=SourceReference(
        author="Agestam, E.",
        year=1985,
        title="A growth simulator for mixed stands of pine, spruce and birch in Sweden",
    ),
    species_groups={},
    units={},
    kernel_names=(
        "agestam_1985_si_translation_pine_to_birch",
        "agestam_1985_si_translation_spruce_to_birch",
    ),
)
