"""Jonson site index mapping helpers.

Provides:
    - A mapping from m3sk productivity to Jonson index class (1-8).
    - A wrapper that validates H100 SiteIndexValue inputs and derives m3sk via
      Hagglund (1981) before mapping to Jonson index.
"""

from __future__ import annotations

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers.primitives import SiteIndexValue
from pyforestry.base.helpers.tree_species import TreeName, TreeSpecies
from pyforestry.sweden.site.enums import Sweden
from pyforestry.sweden.siteindex.translate.hagglund_1981_si_to_productivity import (
    hagglund_1981_si_to_productivity,
)
from pyforestry.sweden.siteindex.validation import validate_hagglund_1970_h100_site_index


def jonson_index_from_m3sk(site_index_m3sk: float) -> int:
    """Map site index (m3sk/ha) to Jonson index class (1..8).

    Args:
        site_index_m3sk (float): Productivity in m3sk/ha at MAI culmination.

    Returns:
        int: Jonson index class (1..8), where 1 is highest productivity.
    """

    if site_index_m3sk > 0 and site_index_m3sk <= 1.57:
        return 8
    if site_index_m3sk <= 2.18:
        return 7
    if site_index_m3sk <= 2.97:
        return 6
    if site_index_m3sk <= 3.93:
        return 5
    if site_index_m3sk <= 5.24:
        return 4
    if site_index_m3sk <= 6.99:
        return 3
    if site_index_m3sk <= 9.24:
        return 2
    return 1


def _validate_h100_site_index_input(h100_input: SiteIndexValue, main_species: TreeName) -> None:
    """Validate that the H100 input matches required species and function.

    Args:
        h100_input (SiteIndexValue): H100 site index value.
        main_species (TreeName): Species for H100 (pine or spruce).

    Raises:
        TypeError: If input types are invalid.
        ValueError: If reference age, species, or function provenance is invalid.
    """
    allowed = {TreeSpecies.Sweden.picea_abies, TreeSpecies.Sweden.pinus_sylvestris}
    validate_hagglund_1970_h100_site_index(
        h100_input,
        param_name="h100_input",
        expected_species=main_species,
        allowed_species=allowed,
    )


def jonson_index_from_site_index(
    h100_input: SiteIndexValue,
    *,
    main_species: TreeName,
    vegetation: Sweden.FieldLayer,
    altitude: float,
    county: Sweden.County,
) -> int:
    """Translate H100 to Jonson index using Hagglund 1981 productivity.

    Args:
        h100_input (SiteIndexValue): H100 site index value.
        main_species (TreeName): Main species (pine or spruce).
        vegetation (Sweden.FieldLayer): Field layer vegetation enum.
        altitude (float): Altitude in meters above sea level.
        county (Sweden.County): Swedish county enum.

    Returns:
        int: Jonson index class (1..8).

    Raises:
        TypeError: If any input type is invalid.
        ValueError: If H100 is not valid or not from a supported function.
    """

    _validate_h100_site_index_input(h100_input, main_species)
    site_index_m3sk = hagglund_1981_si_to_productivity(
        h100_input=h100_input,
        main_species=main_species,
        vegetation=vegetation,
        altitude=altitude,
        county=county,
    )
    return jonson_index_from_m3sk(site_index_m3sk)


__all__ = ["jonson_index_from_m3sk", "jonson_index_from_site_index"]


DESCRIPTOR = FormulaDescriptor(
    component_id="jonson_1914_siteindex",
    source=SourceReference(
        author="Jonson, T.",
        year=1914,
        title="Jonson site index (bonitet) classification from productivity",
    ),
    species_groups={},
    units={},
    kernel_names=("jonson_index_from_m3sk", "jonson_index_from_site_index"),
)
