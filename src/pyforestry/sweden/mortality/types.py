"""Type definitions for Swedish mortality models.

This module contains explicit, unit-bearing context containers and
configuration objects used by mortality equations and orchestration engines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from pyforestry.base.helpers.primitives import SiteIndexValue
from pyforestry.base.helpers.tree_species import TreeName
from pyforestry.sweden.site.enums import Sweden


class MortalityRealizationMode(Enum):
    """Implementation mode for mortality assignment."""

    DETERMINISTIC = "deterministic"
    STOCHASTIC = "stochastic"


class MortalityTreeModel(Enum):
    """Supported single-tree mortality model families."""

    FRIDMAN_STAHL_2001 = "fridman_stahl_2001"
    ELFVING_2013 = "elfving_2013"
    SIIPILEHTO_2020 = "siipilehto_2020"


@dataclass(slots=True)
class MortalityTreeRecord:
    """Tree-level mortality input record.

    Attributes:
        species: Tree species.
        diameter_cm: Diameter at breast height in centimeters.
        bal: Basal area larger trees (BAL) for the tree, unitless.
        stems_per_tree: Number of represented stems. Used for stochastic
            assignment and basal-area weighting.
        basal_area_cm2: Optional tree basal area in square centimeters. When
            omitted, it is derived from `diameter_cm`.
        age_total_years: Optional total age in years for tree-level equations.
        is_overstorey: Whether the tree is classified as overstorey.
        volume_m3: Optional per-tree volume in cubic meters.
        metadata: Optional extra attributes used by adapters.
    """

    species: TreeName | str
    diameter_cm: float
    bal: float = 0.0
    stems_per_tree: float | None = None
    basal_area_cm2: float | None = None
    age_total_years: float | None = None
    is_overstorey: bool = False
    volume_m3: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MortalityStandConditions:
    """Stand-level mortality input conditions.

    Attributes:
        plot_area_m2: Plot area in square meters.
        total_basal_area_m2_ha: Total stand basal area in m2/ha.
        total_stems_per_ha: Total stems in stems/ha.
        mean_diameter_arithmetic_cm: Arithmetic mean diameter in centimeters.
        mean_diameter_dg_cm: Basal-area weighted mean diameter in centimeters.
        mean_age_total_years: Mean total age in years.
        mean_age_excl_overstorey_years: Mean total age excluding overstorey.
        mean_age_overstorey_years: Mean total age overstorey trees.
        species_basal_area_m2_ha: Optional species-level basal area mapping.
        slope_percent: Terrain slope in percent.
        aspect_degrees: Terrain aspect in degrees.
    """

    plot_area_m2: float
    total_basal_area_m2_ha: float | None = None
    total_stems_per_ha: float | None = None
    mean_diameter_arithmetic_cm: float | None = None
    mean_diameter_dg_cm: float | None = None
    mean_age_total_years: float | None = None
    mean_age_excl_overstorey_years: float | None = None
    mean_age_overstorey_years: float = 0.0
    species_basal_area_m2_ha: Mapping[TreeName | str, float] | None = None
    slope_percent: float = 0.0
    aspect_degrees: float | None = None


@dataclass(slots=True)
class MortalitySiteConditions:
    """Site-level mortality input conditions.

    Attributes:
        latitude_deg: Latitude in decimal degrees.
        altitude_m: Altitude in meters above sea level.
        site_index_m: Site index in meters (H100 scale where applicable).
            Can be provided as a numeric value or as ``SiteIndexValue``.
        soil_moisture: Soil moisture class (`Sweden.SoilMoistureEnum` or code).
        peat: Whether peat soil is present.
        temperature_sum: Temperature sum in degree-days.
        part_of_sweden: Region label (`north`, `middle`, `south`).
        field_layer: Optional field-layer enum used for vegetation coding.
        vegetation_type_code: Optional direct vegetation type code.
        texture_is_sand_medium: True for sandy-silty till indicator.
        is_rich: Optional rich-site indicator for Nystrom-based routing.
        is_poor: Optional poor-site indicator for Nystrom-based routing.
    """

    latitude_deg: float
    altitude_m: float
    site_index_m: float | SiteIndexValue
    soil_moisture: Sweden.SoilMoistureEnum | int
    peat: bool = False
    temperature_sum: float = 0.0
    part_of_sweden: str = "middle"
    field_layer: Sweden.FieldLayer | None = None
    vegetation_type_code: int | None = None
    texture_is_sand_medium: bool = False
    is_rich: bool | None = None
    is_poor: bool | None = None


@dataclass(slots=True)
class MortalityHistoryConditions:
    """Historical disturbance/treatment conditions for mortality routing."""

    thinned_within_0_2_years: bool = False
    thinned_within_0_5_years: bool = False
    thinned_within_2_20_years: bool = False
    thinning_intensity_fraction: float = 0.0
    thinning_form_q: float = 0.0
    years_since_final_felling: float | None = None


@dataclass(slots=True)
class MortalityContext:
    """Canonical unified mortality context (pure inputs; the engine owns config)."""

    trees: list[MortalityTreeRecord]
    stand: MortalityStandConditions
    site: MortalitySiteConditions
    history: MortalityHistoryConditions | None = None


@dataclass(slots=True)
class MortalityConfig:
    """Configuration for mortality orchestration engines."""

    implementation_type: MortalityRealizationMode = MortalityRealizationMode.DETERMINISTIC
    tree_model: MortalityTreeModel = MortalityTreeModel.FRIDMAN_STAHL_2001
    calibrate_bengtsson: bool = True
    calibrate_soderberg: bool = True
    site_index_adjustment_factor: float = 1.0
    global_adjustment_factor: float = 1.0
    species_adjustment_factors: Mapping[TreeName | str, float] | None = None
    use_retained_tree_override: bool = True
    retained_tree_mortality_years_1_to_5: Mapping[TreeName | str, float] | None = None
    retained_tree_mortality_years_6_to_10: Mapping[TreeName | str, float] | None = None
    period_years: float = 5.0
    stochastic_seed: int | None = None
    default_stems_per_tree: float = 1.0


@dataclass(slots=True)
class MortalityResult:
    """Result container for mortality orchestration runs."""

    tree_probabilities: list[float]
    tree_realized_mortality: list[float]
    species_mortality_fraction: dict[str, float]
    species_mortality_fraction_before_calibration: dict[str, float]
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RootRotRiskResult:
    """Root-rot risk outputs for the Thor-Stahl-Stenlid (2005) model."""

    tree_risk_probabilities: list[float]
    stems_with_root_rot: float
    basal_area_with_root_rot_m2_ha: float
    volume_with_root_rot_m3_ha: float


__all__ = [
    "MortalityRealizationMode",
    "MortalityTreeModel",
    "MortalityTreeRecord",
    "MortalityStandConditions",
    "MortalitySiteConditions",
    "MortalityHistoryConditions",
    "MortalityContext",
    "MortalityConfig",
    "MortalityResult",
    "RootRotRiskResult",
]
