"""Nyström & Söderberg (1987) young-stand functions for age and diameter."""

from __future__ import annotations

from math import exp, log, sin, sqrt
from typing import Optional

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers.tree_species import TreeName, TreeSpecies

_PINE_SPECIES = {
    TreeSpecies.Sweden.pinus_sylvestris,
    TreeSpecies.Sweden.pinus_contorta,
    TreeSpecies.Sweden.larix_sibirica,
    TreeSpecies.Sweden.larix_decidua,
    TreeSpecies.Sweden.larix_europaea_x_leptolepis,
    TreeSpecies.Sweden.larix_sukaczewii,
}
_SPRUCE_SPECIES = {
    TreeSpecies.Sweden.picea_abies,
    TreeSpecies.Sweden.picea_sitchensis,
    TreeSpecies.Sweden.picea_mariana,
}
_BIRCH_SPECIES = {TreeSpecies.Sweden.betula_pendula, TreeSpecies.Sweden.betula_pubescens}


class NystromSoderberg1987:
    """Age at breast height and dbh-from-height functions."""

    @staticmethod
    def age_at_breast_height(
        *,
        height_dm: float,
        mean_height_dm: float,
        site_index_dm: float,
        species: TreeName,
        stub_indicator: float = 0.0,
        european_birch_indicator: Optional[float] = None,
    ) -> float:
        """Compute sapling age at breast height (years).

        Args:
            height_dm (float): Tree height in decimetres.
            mean_height_dm (float): Mean height (dm) for saplings on the plot.
            site_index_dm (float): Site index in decimetres.
            species (TreeName): Tree species.
            stub_indicator (float): Indicator for vegetatively propagated birch (0/1).
            european_birch_indicator (float | None): Indicator for Betula pendula (0/1).

        Returns:
            float: Age at breast height (years). For height < 12 dm, returns -1.
        """
        if height_dm < 12.0:
            return -1.0

        if species in _PINE_SPECIES or species in _SPRUCE_SPECIES:
            if species in _SPRUCE_SPECIES:
                b0 = 2.643
                b1 = 78.635
                b2 = -2.107e-03
                b3 = 28.862
                b4 = 0.510
                b5 = -1.000
            else:
                b0 = 2.548
                b1 = 68.228
                b2 = -2.609e-03
                b3 = 24.540
                b4 = 0.572
                b5 = -1.000

            age = (
                b0 * log(height_dm - 12.0)
                + b1 * (height_dm / site_index_dm) ** 2
                + b2 * height_dm * site_index_dm / 10.0
                + b3 * (mean_height_dm / site_index_dm) ** 2
                + b4 * (height_dm - mean_height_dm) / mean_height_dm
                + b5
            )
            return max(age, 0.5)

        if european_birch_indicator is None:
            european_birch_indicator = 1.0 if species is TreeSpecies.Sweden.betula_pendula else 0.0

        age = (
            1.988 * log(height_dm - 12.0)
            + 61.889 * (height_dm / site_index_dm) ** 2
            + -1.490 * mean_height_dm / site_index_dm
            + -15.724 * european_birch_indicator * (height_dm / site_index_dm) ** 2
            + 0.0142 * stub_indicator * (height_dm - 50.0)
        )
        return max(age, 0.5)

    @staticmethod
    def dbh_from_height(
        *,
        height_dm: float,
        species: TreeName,
        total_height_sqr_m2_per_100m2: float,
        broadleaf_height_sqr_share: float,
        natural_regeneration: int,
        cleaning_indicator: int,
        years_since_cleaning: int,
        altitude_m: float,
        latitude_deg: float,
        shrubs: int,
        herb_grass: int,
        near_coast: int,
        site_index_pine_m: float,
        h_max_m: float,
        veg: int = 0,
    ) -> float:
        """Estimate dbh (cm) from height and stand context.

        Args:
            height_dm (float): Tree height in decimetres.
            species (TreeName): Tree species.
            total_height_sqr_m2_per_100m2 (float): Sum of height^2 (m2/100m2).
            broadleaf_height_sqr_share (float): Broadleaf share of height^2 (0..1).
            natural_regeneration (int): Indicator for natural regeneration.
            cleaning_indicator (int): Indicator for cleaning in last 10 years.
            years_since_cleaning (int): Years since cleaning (0/5/10).
            altitude_m (float): Altitude (m).
            latitude_deg (float): Latitude (degrees).
            shrubs (int): Shrub indicator.
            herb_grass (int): Herb/grass indicator.
            near_coast (int): Indicator for distance-to-coast < 5 km.
            site_index_pine_m (float): Pine site index (m).
            h_max_m (float): Mean height of three tallest trees (m).
            veg (int): Indicator for vegetatively propagated birch (0/1).

        Returns:
            float: Diameter at breast height (cm).
        """
        if height_dm < 13.0:
            return 0.0

        height_diff_dm = max(1.0, h_max_m * 10.0 - height_dm)

        if species in _PINE_SPECIES:
            sqr_diam = (
                exp(
                    1.251
                    + 2.098 * log(height_dm - 10.0)
                    + -1.473e-04 * total_height_sqr_m2_per_100m2
                    + -0.176 * log(total_height_sqr_m2_per_100m2 + 100.0)
                    + -0.098
                    * log(1.0 + height_diff_dm * (total_height_sqr_m2_per_100m2 + 100.0) * 0.001)
                    + 0.136 * sin(broadleaf_height_sqr_share * 1.5708)
                    + -0.312 * natural_regeneration
                    + 0.0244 * natural_regeneration * sqrt(height_dm)
                    + -0.171 * cleaning_indicator * (1.0 / (1.0 + years_since_cleaning))
                    + 0.022 * cleaning_indicator * log(10.0 + years_since_cleaning)
                    + 0.014 * latitude_deg
                    + -4.660e-04 * altitude_m
                    + 1.260e-04 * (altitude_m / 10.0) ** 2
                    + 0.088 * herb_grass
                    + 0.096 * near_coast
                )
                * 1.070
            )
            return sqrt(sqr_diam) * 0.1

        if species in _SPRUCE_SPECIES:
            sqr_diam = (
                exp(
                    1.243
                    + 1.868 * log(height_dm - 10.0)
                    + 1.471e-05 * (height_dm - 10.0) ** 2
                    + -5.248e-05 * total_height_sqr_m2_per_100m2
                    + -0.109 * log(total_height_sqr_m2_per_100m2 + 100.0)
                    + -0.058
                    * log(1.0 + height_diff_dm * (total_height_sqr_m2_per_100m2 + 100.0) * 0.001)
                    + 0.081 * sin(broadleaf_height_sqr_share * 1.5708)
                    + -0.052 * natural_regeneration
                    + -0.093 * cleaning_indicator * (1.0 / (1.0 + years_since_cleaning))
                    + 0.013 * cleaning_indicator * log(10.0 + years_since_cleaning)
                    + 0.014 * latitude_deg
                    + 4.483e-05 * (altitude_m / 10.0) ** 2
                    + -0.053 * shrubs
                    + 0.103 * near_coast
                )
                * 1.063
            )
            return sqrt(sqr_diam) * 0.1

        sqr_diam = (
            exp(
                0.311
                + 2.250 * log(height_dm - 11.0)
                + 1.190e-03 * height_dm
                + -1.656e-04 * total_height_sqr_m2_per_100m2
                + -0.119
                * log(1.0 + height_diff_dm * (total_height_sqr_m2_per_100m2 + 100.0) * 0.001)
                + -0.071 * cleaning_indicator * (1.0 / (1.0 + years_since_cleaning))
                + 0.033 * cleaning_indicator * log(10.0 + years_since_cleaning)
                + 6.800e-04 * altitude_m
                + -9.595e-04 * site_index_pine_m * 10.0
                + -2.928e-06 * veg * (height_dm**2)
                + 0.120 * near_coast
            )
            * 1.094
        )
        return sqrt(sqr_diam) * 0.1


__all__ = ["NystromSoderberg1987"]


DESCRIPTOR = FormulaDescriptor(
    component_id="nystrom_1987_model",
    source=SourceReference(
        author="Nyström, K. & Söderberg, U.",
        year=1987,
        title="Tillväxtberäkningen för ungskog i Hugin-systemet",
        note=(
            "Sveriges lantbruksuniversitet, institutionen för skogsskötsel, "
            "Arbetsrapport nr 18, Umeå, 81 s. Full title: 'Tillväxtberäkningen för "
            "ungskog i HUGIN-systemet: en kontroll med data från återinventerade "
            "ungskogsytor'."
        ),
    ),
    kind="model",
    domain="growth",
    composes=(),
    kernel_names=("NystromSoderberg1987",),
)
