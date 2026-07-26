"""Wikberg (2004) ingrowth model for established stands.

Implements the 4-step ingrowth model for trees recruited into the >=4 cm dbh
class over a 5-year period.

Source:
    Wikberg, P-E. (2004). "Occurrence, morphology and growth of understory
    saplings in Swedish forests", doctoral thesis, Acta Universitatis
    Agriculturae Sueciae, SLU, Umeå.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from math import exp, log, sqrt
from typing import Mapping, Sequence

from pyforestry.base.contracts import SourceReference
from pyforestry.base.helpers.primitives import QuadraticMeanDiameter, SiteIndexValue
from pyforestry.base.helpers.stand import Stand
from pyforestry.base.helpers.tree import Tree
from pyforestry.base.helpers.tree_species import TreeName, TreeSpecies, parse_tree_species
from pyforestry.sweden.site.enums import Sweden
from pyforestry.sweden.site.swedish_site import SwedishSite
from pyforestry.sweden.siteindex.validation import validate_hagglund_1970_h100_site_index


class IngrowthSpeciesGroup(Enum):
    """Species groups used in the Wikberg (2004) ingrowth model."""

    PINE = "pine"
    SPRUCE = "spruce"
    BIRCH = "birch"
    OTHER_BROADLEAF = "other_broadleaf"
    OAK = "oak"
    BEECH = "beech"
    SOUTHERN_BROADLEAF = "southern_broadleaf"


@dataclass(frozen=True)
class IngrowthResult:
    """Container for ingrowth outputs (per ha) and generated trees.

    Attributes:
        probability_small_trees (dict[IngrowthSpeciesGroup, float]): Probability of small trees
            per group.
        number_small_trees (dict[IngrowthSpeciesGroup, float]): Expected number of small trees
            per ha.
        number_ingrowth_trees (dict[IngrowthSpeciesGroup, float]): Expected number of ingrown
            trees per ha.
        mean_diameter_cm (dict[IngrowthSpeciesGroup, float]): Mean diameter (cm) of ingrown
            trees.
        ingrown_trees (list[Tree]): Representative ingrown trees with per-ha weights.
    """

    probability_small_trees: dict[IngrowthSpeciesGroup, float]
    number_small_trees: dict[IngrowthSpeciesGroup, float]
    number_ingrowth_trees: dict[IngrowthSpeciesGroup, float]
    mean_diameter_cm: dict[IngrowthSpeciesGroup, float]
    ingrown_trees: list[Tree]


@dataclass(frozen=True)
class CommonData:
    """Resolved and transformed stand/site variables for ingrowth calculations.

    Attributes:
        basal_area_capped_m2_ha (float): Basal area capped at 100 (m2/ha).
        basal_area_capped_sqrt (float): Square root of capped basal area.
        inv_basal_area_capped_plus5 (float): 1 / (5 + capped basal area).
        mean_age_excl_overstorey_capped_years (float): Mean age excluding overstorey capped
            at 160 (years).
        log_mean_age_excl_overstorey_capped_years (float): Natural log of capped mean age.
        inv_mean_age_excl_overstorey_capped_plus5 (float): 1 / (5 + capped mean age).
        temperature_sum_scaled (float): Temperature sum scaled by 0.01.
        temperature_sum_scaled_squared (float): Scaled temperature sum squared.
        inv_temperature_sum_scaled_minus3 (float): 1 / (temperature_sum_scaled - 3).
        altitude_scaled (float): Altitude scaled by 0.01.
        log_altitude_scaled (float): Natural log of altitude_scaled.
        altitude_scaled_squared (float): altitude_scaled squared.
        latitude_scaled (float): Latitude scaled by 10.
        latitude_scaled_squared (float): latitude_scaled squared scaled by 0.01.
        latitude_over_60 (bool): True if latitude > 60 degrees.
        spruce_small_tree_probability (float): Spruce small-tree probability (seed for pine
            and birch).
        pine_presence_10cm (int): Pine presence indicator for dbh >= 10 cm (0/1).
        spruce_presence_10cm (int): Spruce presence indicator for dbh >= 10 cm (0/1).
        birch_presence_10cm (int): Birch presence indicator for dbh >= 10 cm (0/1).
        other_broadleaf_presence_10cm (int): Other broadleaf indicator for dbh >= 10 cm (0/1).
        oak_presence_10cm (int): Oak presence indicator for dbh >= 10 cm (0/1).
        beech_presence_10cm (int): Beech presence indicator for dbh >= 10 cm (0/1).
        southern_broadleaf_presence_10cm (int): Southern broadleaf indicator for dbh >= 10 cm
            (0/1).
        thinning_0_5_years (int): Thinning indicator for years 0-5 (1 if thinned).
        thinning_6_10_years (int): Thinning indicator for years 6-10 (1 if thinned).
        visibility_cleaning (int): Visibility cleaning indicator (0/1).
        gotland (int): Gotland indicator (0/1).
        soil_moisture_code (int): Soil moisture code (1-4).
        ground_water_indicator (int): Ground-water indicator (0 if seldom/never, else 1).
        soil_texture_code_sqrt (float): Square root of soil texture code.
        poor_vegetation (int): Poor-vegetation indicator (poor shrub/low productivity).
        shrubs (int): Shrub indicator.
        poor_shrubs (int): Poor shrubs indicator.
        herb (int): Herb indicator.
        herb_without_shrubs (int): Herb without shrubs indicator.
        herb_with_shrubs (int): Herb with shrubs indicator.
        herb_without_shrubs_dry (int): Herb without shrubs (dry) indicator.
        no_vegetation (int): No vegetation indicator.
        broadleaved_grass (int): Broadleaved grass indicator.
        thinleaved_grass (int): Thinleaved grass indicator.
        sedge (int): Sedge indicator.
        lichen (int): Lichen indicator.
        peat (int): Peat indicator (0/1).
        bog_moss (int): Bog moss indicator (0/1).
        swamp_moss (int): Swamp moss indicator (0/1).
        field (int): Field position indicator (0/1).
        edge (int): Edge position indicator (0/1).
        road (int): Road position indicator (0/1).
        rich_vegetation (int): Rich vegetation indicator.
        site_index_m (float): Site index (m).
        spruce_basal_area_share (float): Spruce basal area share (0-1).
        mesic_indicator (int): Mesic soil indicator (0/1).
    """

    basal_area_capped_m2_ha: float
    basal_area_capped_sqrt: float
    inv_basal_area_capped_plus5: float
    mean_age_excl_overstorey_capped_years: float
    log_mean_age_excl_overstorey_capped_years: float
    inv_mean_age_excl_overstorey_capped_plus5: float
    temperature_sum_scaled: float
    temperature_sum_scaled_squared: float
    inv_temperature_sum_scaled_minus3: float
    altitude_scaled: float
    log_altitude_scaled: float
    altitude_scaled_squared: float
    latitude_scaled: float
    latitude_scaled_squared: float
    latitude_over_60: bool
    spruce_small_tree_probability: float
    pine_presence_10cm: int
    spruce_presence_10cm: int
    birch_presence_10cm: int
    other_broadleaf_presence_10cm: int
    oak_presence_10cm: int
    beech_presence_10cm: int
    southern_broadleaf_presence_10cm: int
    thinning_0_5_years: int
    thinning_6_10_years: int
    visibility_cleaning: int
    gotland: int
    soil_moisture_code: int
    ground_water_indicator: int
    soil_texture_code_sqrt: float
    poor_vegetation: int
    shrubs: int
    poor_shrubs: int
    herb: int
    herb_without_shrubs: int
    herb_with_shrubs: int
    herb_without_shrubs_dry: int
    no_vegetation: int
    broadleaved_grass: int
    thinleaved_grass: int
    sedge: int
    lichen: int
    peat: int
    bog_moss: int
    swamp_moss: int
    field: int
    edge: int
    road: int
    rich_vegetation: int
    site_index_m: float
    spruce_basal_area_share: float
    mesic_indicator: int


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
_OAK_SPECIES = {
    TreeSpecies.Sweden.quercus_robur,
    TreeSpecies.Sweden.quercus_petraea,
    TreeSpecies.Sweden.quercus_rubra,
}
_BEECH_SPECIES = {TreeSpecies.Sweden.fagus_sylvatica}
_OTHER_BROADLEAF_SPECIES = {
    TreeSpecies.Sweden.populus_tremula,
    TreeSpecies.Sweden.acer_platanoides,
    TreeSpecies.Sweden.alnus_glutinosa,
    TreeSpecies.Sweden.alnus_incana,
    TreeSpecies.Sweden.acer_pseudoplatanus,
    TreeSpecies.Sweden.salix_caprea,
    TreeSpecies.Sweden.sorbus_aucuparia,
}
_SOUTHERN_BROADLEAF_SPECIES = {
    TreeSpecies.Sweden.fraxinus_excelsior,
    TreeSpecies.Sweden.ulmus_glabra,
    TreeSpecies.Sweden.tilia_cordata,
}

_GROUP_SPECIES = {
    IngrowthSpeciesGroup.PINE: _PINE_SPECIES,
    IngrowthSpeciesGroup.SPRUCE: _SPRUCE_SPECIES,
    IngrowthSpeciesGroup.BIRCH: _BIRCH_SPECIES,
    IngrowthSpeciesGroup.OAK: _OAK_SPECIES,
    IngrowthSpeciesGroup.BEECH: _BEECH_SPECIES,
    IngrowthSpeciesGroup.OTHER_BROADLEAF: _OTHER_BROADLEAF_SPECIES,
    IngrowthSpeciesGroup.SOUTHERN_BROADLEAF: _SOUTHERN_BROADLEAF_SPECIES,
}

_REPRESENTATIVE_SPECIES: dict[IngrowthSpeciesGroup, TreeName] = {
    IngrowthSpeciesGroup.PINE: TreeSpecies.Sweden.pinus_sylvestris,
    IngrowthSpeciesGroup.SPRUCE: TreeSpecies.Sweden.picea_abies,
    IngrowthSpeciesGroup.BIRCH: TreeSpecies.Sweden.betula_pendula,
    IngrowthSpeciesGroup.OAK: TreeSpecies.Sweden.quercus_robur,
    IngrowthSpeciesGroup.BEECH: TreeSpecies.Sweden.fagus_sylvatica,
    IngrowthSpeciesGroup.OTHER_BROADLEAF: TreeSpecies.Sweden.populus_tremula,
    IngrowthSpeciesGroup.SOUTHERN_BROADLEAF: TreeSpecies.Sweden.fraxinus_excelsior,
}

_INGROWTH_ORDER = (
    IngrowthSpeciesGroup.SPRUCE,
    IngrowthSpeciesGroup.PINE,
    IngrowthSpeciesGroup.BIRCH,
    IngrowthSpeciesGroup.OTHER_BROADLEAF,
    IngrowthSpeciesGroup.OAK,
    IngrowthSpeciesGroup.BEECH,
    IngrowthSpeciesGroup.SOUTHERN_BROADLEAF,
)


class Wikberg2004Ingrowth:  # pragma: no cover - legacy parity implementation
    """Predict ingrowth for established stands using Wikberg (2004).

    Args:
        deterministic (bool): If True, return expected ingrowth (deterministic).
        use_initial_saplings (bool): Use sapling occurrence for period 0 step-1 probability.
        min_mean_age_invoke (float): Minimum mean age to invoke ingrowth (years).
        ingrowth_species (Sequence[IngrowthSpeciesGroup] | None): Species groups to include.
        rng (random.Random | None): RNG used when deterministic is False.

    Example:
        model = Wikberg2004Ingrowth(deterministic=True)
        result = model.predict(
            stand=stand,
            site_index_m=26.0,
            mean_age_excl_overstorey_years=60.0,
            qmd_cm=12.0,
            temperature_sum_dd=1400.0,
            latitude_deg=58.0,
            altitude_m=100.0,
            soil_moisture=Sweden.SoilMoistureEnum.MESIC,
            soil_texture=Sweden.SoilTextureSediment.MEDIUM_SAND,
            soil_water=Sweden.SoilWater.SELDOM_NEVER,
            bottom_layer=Sweden.BottomLayer.FRESH_MOSS,
            field_layer=Sweden.FieldLayer.BILBERRY,
        )
    """

    def __init__(
        self,
        *,
        deterministic: bool = True,
        use_initial_saplings: bool = False,
        min_mean_age_invoke: float = 50.0,
        ingrowth_species: Sequence[IngrowthSpeciesGroup] | None = None,
        rng: random.Random | None = None,
    ) -> None:
        """Initialize the ingrowth model configuration.

        Args:
            deterministic (bool): If True, return expected ingrowth (deterministic).
            use_initial_saplings (bool): Use sapling occurrence for period 0 step-1 probability.
            min_mean_age_invoke (float): Minimum mean age to invoke ingrowth (years).
            ingrowth_species (Sequence[IngrowthSpeciesGroup] | None): Species groups to include.
            rng (random.Random | None): RNG used when deterministic is False.

        Raises:
            ValueError: If ``min_mean_age_invoke`` is negative.
        """
        if min_mean_age_invoke < 0:
            raise ValueError("min_mean_age_invoke must be >= 0.")
        self.deterministic = deterministic
        self.use_initial_saplings = use_initial_saplings
        self.min_mean_age_invoke = min_mean_age_invoke
        self.ingrowth_species = (
            list(ingrowth_species) if ingrowth_species is not None else list(_INGROWTH_ORDER)
        )
        self.rng = rng

    def predict(
        self,
        *,
        stand: Stand | None = None,
        site: SwedishSite | None = None,
        site_index_m: float | SiteIndexValue | None = None,
        basal_area_m2_ha: float | None = None,
        qmd_cm: float | QuadraticMeanDiameter | None = None,
        mean_age_excl_overstorey_years: float | None = None,
        temperature_sum_dd: float | None = None,
        latitude_deg: float | None = None,
        altitude_m: float | None = None,
        soil_moisture: Sweden.SoilMoistureEnum | None = None,
        soil_texture: Sweden.SoilTextureTill | Sweden.SoilTextureSediment | None = None,
        soil_water: Sweden.SoilWater | None = None,
        bottom_layer: Sweden.BottomLayer | None = None,
        field_layer: Sweden.FieldLayer | None = None,
        peat: bool | None = None,
        gotland: int | None = None,
        species_ba_m2_ha: Mapping[IngrowthSpeciesGroup, float] | None = None,
        species_presence_10cm: Mapping[IngrowthSpeciesGroup, int] | None = None,
        sapling_occurrence: Mapping[IngrowthSpeciesGroup, float] | None = None,
        period_index: int = 0,
        ingrowth_species: Sequence[IngrowthSpeciesGroup] | None = None,
        thinning_0_5_years: int = 0,
        thinning_6_10_years: int = 0,
        visibility_cleaning: int = 0,
        field: int = 0,
        edge: int = 0,
        road: int = 0,
        plot_is_saplings: bool = False,
    ) -> IngrowthResult:
        """Compute per-ha ingrowth and return a generated tree list.

        Args:
            stand (Stand | None): Optional stand used for basal area, QMD, and tree list.
                Tree diameters are read from ``Tree.diameter_cm`` (usually ``Diameter_cm``).
            site (SwedishSite | None): Optional site used to populate missing site inputs.
            site_index_m (float | SiteIndexValue | None): Site index for the stand (m). Prefer
                ``SiteIndexValue`` (H100 from Hagglund 1970) for pine or spruce.
            basal_area_m2_ha (float | None): Basal area (m2/ha).
            qmd_cm (float | QuadraticMeanDiameter | None): Quadratic mean diameter (cm) used
                for gating.
            mean_age_excl_overstorey_years (float | None): Mean age excluding overstorey.
            temperature_sum_dd (float | None): Temperature sum (degree-days > 5C).
            latitude_deg (float | None): Latitude (degrees).
            altitude_m (float | None): Altitude (m).
            soil_moisture (Sweden.SoilMoistureEnum | None): Soil moisture class.
            soil_texture (Sweden.SoilTextureTill | Sweden.SoilTextureSediment | None):
                Soil texture.
            soil_water (Sweden.SoilWater | None): Soil water class.
            bottom_layer (Sweden.BottomLayer | None): Bottom layer class.
            field_layer (Sweden.FieldLayer | None): Field layer vegetation class.
            peat (bool | None): Peat indicator. If None, derived from soil_texture if possible.
            gotland (int | None): Gotland indicator (1 if county is Gotland, else 0).
            species_ba_m2_ha (Mapping | None): Basal area per ingrowth species group (m2/ha).
            species_presence_10cm (Mapping | None): Presence indicators for dbh >= 10 cm
                (pine_presence_10cm, spruce_presence_10cm, birch_presence_10cm,
                other_broadleaf_presence_10cm, oak_presence_10cm, beech_presence_10cm,
                southern_broadleaf_presence_10cm).
            sapling_occurrence (Mapping | None): Sapling occurrence indicators for dbh < 4 cm.
            period_index (int): Period index (0 for first period).
            ingrowth_species (Sequence[IngrowthSpeciesGroup] | None): Species groups to include.
            thinning_0_5_years (int): Thinning indicator for years 0-5 (1 if thinned).
            thinning_6_10_years (int): Thinning indicator for years 6-10 (1 if thinned).
            visibility_cleaning (int): Visibility cleaning indicator (0/1).
            field (int): Field position indicator (0/1).
            edge (int): Stand edge indicator (0/1).
            road (int): Road position indicator (0/1).
            plot_is_saplings (bool): Skip ingrowth if plot type is saplings.

        Returns:
            IngrowthResult: Per-ha metrics and a generated tree list.

        Raises:
            ValueError: If required inputs are missing or invalid.
        """
        deterministic = self.deterministic
        use_initial_saplings = self.use_initial_saplings
        min_mean_age_invoke = self.min_mean_age_invoke
        species_to_use = (
            list(ingrowth_species) if ingrowth_species is not None else list(self.ingrowth_species)
        )

        if site is None and stand is not None and isinstance(stand.site, SwedishSite):
            site = stand.site

        if site is not None:
            if latitude_deg is None:
                latitude_deg = site.latitude
            if altitude_m is None:
                altitude_m = site.altitude
            if temperature_sum_dd is None:
                temperature_sum_dd = site.temperature_sum_odin1983
            if soil_moisture is None:
                soil_moisture = site.soil_moisture
            if soil_texture is None:
                soil_texture = site.soil_texture
            if soil_water is None:
                soil_water = site.soil_water
            if bottom_layer is None:
                bottom_layer = site.bottom_layer
            if field_layer is None:
                field_layer = site.field_layer
            if gotland is None:
                gotland = int(site.county == Sweden.County.GOTLAND) if site.county else 0

        if gotland is None:
            gotland = 0

        if site_index_m is None:
            raise ValueError("site_index_m is required.")
        site_index_m = self._resolve_site_index_m(site_index_m)
        if mean_age_excl_overstorey_years is None:
            raise ValueError("mean_age_excl_overstorey_years is required.")
        if mean_age_excl_overstorey_years <= 0:
            raise ValueError("mean_age_excl_overstorey_years must be > 0.")

        if basal_area_m2_ha is None or qmd_cm is None:
            if stand is None:
                missing = []
                if basal_area_m2_ha is None:
                    missing.append("basal_area_m2_ha")
                if qmd_cm is None:
                    missing.append("qmd_cm")
                raise ValueError(f"Missing stand metrics: {', '.join(missing)}.")
            if basal_area_m2_ha is None:
                basal_area_m2_ha = float(stand.BasalArea)
            if qmd_cm is None:
                qmd_cm = float(stand.QMD)
        if qmd_cm is not None:
            qmd_cm = float(qmd_cm)
        if basal_area_m2_ha < 0:
            raise ValueError("basal_area_m2_ha must be non-negative.")

        if temperature_sum_dd is None or latitude_deg is None or altitude_m is None:
            raise ValueError("temperature_sum_dd, latitude_deg, and altitude_m are required.")
        if soil_moisture is None or soil_texture is None or soil_water is None:
            raise ValueError("soil_moisture, soil_texture, and soil_water are required.")
        if bottom_layer is None or field_layer is None:
            raise ValueError("bottom_layer and field_layer are required.")

        if peat is None:
            peat = soil_texture in {
                Sweden.SoilTextureSediment.PEAT,
                Sweden.SoilTextureTill.PEAT,
            }

        trees = self._trees_from_stand(stand)

        if species_ba_m2_ha is None:
            if stand is None:
                raise ValueError("species_ba_m2_ha is required when stand is not provided.")
            if stand.use_angle_count:
                raise ValueError("species_ba_m2_ha is required when stand uses angle-count data.")
            species_ba_m2_ha = {}
            for group, species_set in _GROUP_SPECIES.items():
                group_ba = 0.0
                for sp in species_set:
                    try:
                        group_ba += float(stand.BasalArea(sp))
                    except KeyError:
                        continue
                species_ba_m2_ha[group] = group_ba

        if species_presence_10cm is None:
            if not trees:
                raise ValueError(
                    "species_presence_10cm is required when no tree list is available."
                )
            species_presence_10cm = {group: 0 for group in _GROUP_SPECIES}
            for tree in trees:
                if tree.species is None or tree.diameter_cm is None:
                    continue
                species = parse_tree_species(tree.species)
                group = self._species_group_for_tree(species)
                if group is None:
                    continue
                if float(tree.diameter_cm) >= 10.0:
                    species_presence_10cm[group] = 1

        sapling_occ = {group: 0.0 for group in _GROUP_SPECIES}
        if use_initial_saplings and period_index == 0:
            if sapling_occurrence is not None:
                for group, value in sapling_occurrence.items():
                    sapling_occ[group] = float(value)
            if trees:
                for tree in trees:
                    if tree.species is None or tree.diameter_cm is None:
                        continue
                    species = parse_tree_species(tree.species)
                    group = self._species_group_for_tree(species)
                    if group is None:
                        continue
                    if float(tree.diameter_cm) < 4.0:
                        sapling_occ[group] = 1.0
            if sapling_occurrence is None and not trees:
                raise ValueError("sapling_occurrence required when use_initial_saplings is True.")

        if (
            qmd_cm <= 10.0
            or mean_age_excl_overstorey_years <= min_mean_age_invoke
            or plot_is_saplings
        ):
            return self._empty_result(species_to_use)

        rng = self.rng

        common = self.build_common_data(
            basal_area_m2_ha=basal_area_m2_ha,
            mean_age_excl_overstorey_years=mean_age_excl_overstorey_years,
            temperature_sum_dd=temperature_sum_dd,
            altitude_m=altitude_m,
            latitude_deg=latitude_deg,
            soil_moisture=soil_moisture,
            soil_texture=soil_texture,
            soil_water=soil_water,
            bottom_layer=bottom_layer,
            field_layer=field_layer,
            peat=peat,
            site_index_m=site_index_m,
            species_ba_m2_ha=species_ba_m2_ha,
            species_presence_10cm=species_presence_10cm,
            gotland=gotland,
            thinning_0_5_years=thinning_0_5_years,
            thinning_6_10_years=thinning_6_10_years,
            visibility_cleaning=visibility_cleaning,
            field=field,
            edge=edge,
            road=road,
        )

        use_initial_period0 = use_initial_saplings and period_index == 0
        (
            probability_small_trees,
            number_small_trees,
            number_ingrowth_trees,
            mean_diameter_cm,
        ) = self._run_ingrowth_dispatch(
            species_to_use=species_to_use,
            common=common,
            sapling_occ=sapling_occ,
            use_initial_period0=use_initial_period0,
            deterministic=deterministic,
            rng=rng,
        )

        ingrown_trees = self._build_ingrown_trees(
            species_to_use=species_to_use,
            mean_diameter_cm=mean_diameter_cm,
            number_ingrowth_trees=number_ingrowth_trees,
        )

        return IngrowthResult(
            probability_small_trees=probability_small_trees,
            number_small_trees=number_small_trees,
            number_ingrowth_trees=number_ingrowth_trees,
            mean_diameter_cm=mean_diameter_cm,
            ingrown_trees=ingrown_trees,
        )

    @staticmethod
    def _empty_result(species_to_use: Sequence[IngrowthSpeciesGroup]) -> IngrowthResult:
        """Return an empty ingrowth result with zeroed species payloads."""
        return IngrowthResult(
            probability_small_trees={group: 0.0 for group in species_to_use},
            number_small_trees={group: 0.0 for group in species_to_use},
            number_ingrowth_trees={group: 0.0 for group in species_to_use},
            mean_diameter_cm={group: 0.0 for group in species_to_use},
            ingrown_trees=[],
        )

    def _run_ingrowth_dispatch(
        self,
        *,
        species_to_use: Sequence[IngrowthSpeciesGroup],
        common: CommonData,
        sapling_occ: Mapping[IngrowthSpeciesGroup, float],
        use_initial_period0: bool,
        deterministic: bool,
        rng: random.Random,
    ) -> tuple[
        dict[IngrowthSpeciesGroup, float],
        dict[IngrowthSpeciesGroup, float],
        dict[IngrowthSpeciesGroup, float],
        dict[IngrowthSpeciesGroup, float],
    ]:
        """Dispatch per-species ingrowth equations for the configured region."""
        probability_small_trees = {group: 0.0 for group in species_to_use}
        number_small_trees = {group: 0.0 for group in species_to_use}
        number_ingrowth_trees = {group: 0.0 for group in species_to_use}
        mean_diameter_cm = {group: 0.0 for group in species_to_use}

        skip_southern = common.latitude_over_60
        spruce_small_tree_probability = 1.0
        dispatch = {
            IngrowthSpeciesGroup.SPRUCE: self._ingrowth_spruce,
            IngrowthSpeciesGroup.PINE: self._ingrowth_pine,
            IngrowthSpeciesGroup.BIRCH: self._ingrowth_birch,
            IngrowthSpeciesGroup.OTHER_BROADLEAF: self._ingrowth_other_broadleaf,
            IngrowthSpeciesGroup.OAK: self._ingrowth_oak,
            IngrowthSpeciesGroup.BEECH: self._ingrowth_beech,
            IngrowthSpeciesGroup.SOUTHERN_BROADLEAF: self._ingrowth_southern_broadleaf,
        }

        for group in _INGROWTH_ORDER:
            if group not in species_to_use:
                continue
            if skip_southern and group in {
                IngrowthSpeciesGroup.OAK,
                IngrowthSpeciesGroup.BEECH,
                IngrowthSpeciesGroup.SOUTHERN_BROADLEAF,
            }:
                continue
            prob, num_small, num_ingrowth, mean_dbh, spruce_small_tree_probability = dispatch[
                group
            ](
                common=common,
                sapling_occ=sapling_occ,
                use_initial_period0=use_initial_period0,
                deterministic=deterministic,
                rng=rng,
                spruce_small_tree_probability=spruce_small_tree_probability,
            )
            probability_small_trees[group] = prob
            number_small_trees[group] = num_small
            number_ingrowth_trees[group] = num_ingrowth
            mean_diameter_cm[group] = mean_dbh

        return (
            probability_small_trees,
            number_small_trees,
            number_ingrowth_trees,
            mean_diameter_cm,
        )

    @staticmethod
    def _build_ingrown_trees(
        *,
        species_to_use: Sequence[IngrowthSpeciesGroup],
        mean_diameter_cm: Mapping[IngrowthSpeciesGroup, float],
        number_ingrowth_trees: Mapping[IngrowthSpeciesGroup, float],
    ) -> list[Tree]:
        """Construct synthetic ingrowth trees from species-level ingrowth counts."""
        trees: list[Tree] = []
        for group in species_to_use:
            trees.append(
                Tree(
                    species=_REPRESENTATIVE_SPECIES[group],
                    diameter_cm=mean_diameter_cm.get(group, 0.0),
                    weight_n=number_ingrowth_trees.get(group, 0.0),
                )
            )
        return trees

    def _ingrowth_spruce(
        self,
        *,
        common: CommonData,
        sapling_occ: Mapping[IngrowthSpeciesGroup, float],
        use_initial_period0: bool,
        deterministic: bool,
        rng: random.Random | None,
        spruce_small_tree_probability: float,
    ) -> tuple[float, float, float, float, float]:
        """Compute spruce ingrowth steps.

        Args:
            common (CommonData): Precomputed stand/site variables (see CommonData for details).
            sapling_occ (Mapping[IngrowthSpeciesGroup, float]): Sapling occurrence indicators.
            use_initial_period0 (bool): Use sapling occurrence in step-1 for period 0.
            deterministic (bool): If True, use expected values instead of draws.
            rng (random.Random | None): RNG used when deterministic is False.
            spruce_small_tree_probability (float): Spruce small-tree probability passed
                forward.

        Returns:
            tuple[float, float, float, float, float]: (probability_small_trees,
            number_small_trees, number_ingrowth_trees, mean_diameter_cm,
            spruce_small_tree_probability_out).
        """
        rng = self._resolve_rng(rng)
        lp = (
            -7.0172
            - 0.032 * common.basal_area_capped_m2_ha
            + 0.3505 * common.basal_area_capped_sqrt
            + 0.0052 * common.mean_age_excl_overstorey_capped_years
            + 60.0307 * common.inv_mean_age_excl_overstorey_capped_plus5
            + 0.7613 * common.temperature_sum_scaled
            - 0.0393 * common.temperature_sum_scaled_squared
            + 1.4845 * common.spruce_presence_10cm
            + 0.3715 * common.birch_presence_10cm
            - 0.7303 * common.thinning_0_5_years
            - 0.4912 * common.thinning_6_10_years
            + 0.2927 * common.soil_moisture_code
            - 0.2371 * common.poor_shrubs
            + 0.411 * common.herb_with_shrubs
            - 0.3078 * common.herb_without_shrubs_dry
            + 0.3437 * common.bog_moss
            - 0.596 * common.field
        )
        p = self._prob_from_logit(lp)
        p_use = sapling_occ[IngrowthSpeciesGroup.SPRUCE] if use_initial_period0 else p
        if deterministic:
            prob_small = p_use
            calc_small = not (use_initial_period0 and p_use <= 0.0)
        else:
            prob_small = 1.0 if rng.random() <= p_use else 0.0
            calc_small = prob_small > 0.0
        if not calc_small:
            return prob_small, 0.0, 0.0, 0.0, p

        bx = (
            0.4947 * lp
            + 0.0127 * common.basal_area_capped_m2_ha
            - 1.3039 * common.inv_temperature_sum_scaled_minus3
        )
        linp = (
            -0.249
            - 0.4293 * common.basal_area_capped_sqrt
            - 0.00619 * common.mean_age_excl_overstorey_capped_years
            + 0.4782 * common.thinning_0_5_years
            + 0.0156 * common.site_index_m
            - 0.1713 * common.log_altitude_scaled
        )
        lnp = self._prob_from_logit(linp)
        num_small = self._number_of_small_trees(2.2215, bx, lnp)
        lndbh = (
            7.231
            + 5.0592 * common.inv_basal_area_capped_plus5
            + 0.01031 * common.site_index_m
            + 0.04
        )
        mean_dbh = sqrt(exp(lndbh)) / 10.0
        if deterministic:
            n_ingrowth = num_small * prob_small
        else:
            n_ingrowth = num_small if prob_small > 0.0 else 0.0
        return prob_small, num_small, n_ingrowth, mean_dbh, p

    def _ingrowth_pine(
        self,
        *,
        common: CommonData,
        sapling_occ: Mapping[IngrowthSpeciesGroup, float],
        use_initial_period0: bool,
        deterministic: bool,
        rng: random.Random | None,
        spruce_small_tree_probability: float,
    ) -> tuple[float, float, float, float, float]:
        """Compute pine ingrowth steps.

        Args:
            common (CommonData): Precomputed stand/site variables (see CommonData for details).
            sapling_occ (Mapping[IngrowthSpeciesGroup, float]): Sapling occurrence indicators.
            use_initial_period0 (bool): Use sapling occurrence in step-1 for period 0.
            deterministic (bool): If True, use expected values instead of draws.
            rng (random.Random | None): RNG used when deterministic is False.
            spruce_small_tree_probability (float): Spruce small-tree probability used in
                pine step-1.

        Returns:
            tuple[float, float, float, float, float]: (probability_small_trees,
            number_small_trees, number_ingrowth_trees, mean_diameter_cm,
            spruce_small_tree_probability_out).
        """
        rng = self._resolve_rng(rng)
        lp = (
            8.4197
            - 0.075 * common.basal_area_capped_m2_ha
            + 0.0129 * common.mean_age_excl_overstorey_capped_years
            - 1.732 * common.log_mean_age_excl_overstorey_capped_years
            - 0.2388 * common.temperature_sum_scaled
            - 0.339 * common.altitude_scaled
            + 0.4464 * spruce_small_tree_probability
            + 1.5613 * common.pine_presence_10cm
            - 0.5922 * common.spruce_presence_10cm
            - 0.7186 * common.thinning_0_5_years
            - 0.5074 * common.thinning_6_10_years
            + 1.2937 * common.gotland
            - 0.0984 * common.soil_moisture_code
            + 0.8961 * common.poor_vegetation
            - 0.923 * common.herb
            + 0.3013 * common.edge
        )
        p = self._prob_from_logit(lp)
        p_use = sapling_occ[IngrowthSpeciesGroup.PINE] if use_initial_period0 else p
        if deterministic:
            prob_small = p_use
            calc_small = not (use_initial_period0 and p_use <= 0.0)
        else:
            prob_small = 1.0 if rng.random() <= p_use else 0.0
            calc_small = prob_small > 0.0
        if not calc_small:
            return prob_small, 0.0, 0.0, 0.0, spruce_small_tree_probability

        bx = (
            0.5954 * lp
            + 0.0635 * common.basal_area_capped_m2_ha
            + 0.1424 * common.temperature_sum_scaled
        )
        linp = (
            -2.227
            - 0.07 * common.basal_area_capped_m2_ha
            - 0.00692 * common.mean_age_excl_overstorey_capped_years
            + 0.5333 * common.thinning_0_5_years
            - 1.4684 * common.spruce_basal_area_share
            + 0.0489 * common.site_index_m
            + 0.027 * common.altitude_scaled_squared
        )
        lnp = self._prob_from_logit(linp)
        num_small = self._number_of_small_trees(0.3224, bx, lnp)
        lndbh = (
            7.3132
            + 5.138 * common.inv_basal_area_capped_plus5
            + 0.00838 * common.site_index_m
            + 0.04
        )
        mean_dbh = sqrt(exp(lndbh)) / 10.0
        if deterministic:
            n_ingrowth = num_small * prob_small
        else:
            n_ingrowth = num_small if prob_small > 0.0 else 0.0
        return prob_small, num_small, n_ingrowth, mean_dbh, spruce_small_tree_probability

    def _ingrowth_birch(
        self,
        *,
        common: CommonData,
        sapling_occ: Mapping[IngrowthSpeciesGroup, float],
        use_initial_period0: bool,
        deterministic: bool,
        rng: random.Random | None,
        spruce_small_tree_probability: float,
    ) -> tuple[float, float, float, float, float]:
        """Compute birch ingrowth steps.

        Args:
            common (CommonData): Precomputed stand/site variables (see CommonData for details).
            sapling_occ (Mapping[IngrowthSpeciesGroup, float]): Sapling occurrence indicators.
            use_initial_period0 (bool): Use sapling occurrence in step-1 for period 0.
            deterministic (bool): If True, use expected values instead of draws.
            rng (random.Random | None): RNG used when deterministic is False.
            spruce_small_tree_probability (float): Spruce small-tree probability used in
                birch step-1.

        Returns:
            tuple[float, float, float, float, float]: (probability_small_trees,
            number_small_trees, number_ingrowth_trees, mean_diameter_cm,
            spruce_small_tree_probability_out).
        """
        rng = self._resolve_rng(rng)
        lp = (
            52.155
            - 0.1469 * common.basal_area_capped_m2_ha
            + 0.9159 * common.basal_area_capped_sqrt
            + 0.0024 * common.mean_age_excl_overstorey_capped_years
            + 47.101 * common.inv_mean_age_excl_overstorey_capped_plus5
            - 0.1945 * common.latitude_scaled
            + 0.0169 * common.latitude_scaled_squared
            + 0.4916 * spruce_small_tree_probability
            + 0.8687 * common.birch_presence_10cm
            - 0.6547 * common.visibility_cleaning
            - 0.6701 * common.gotland
            + 0.5942 * common.soil_moisture_code
            - 0.2136 * common.ground_water_indicator
            - 0.4979 * common.herb_without_shrubs_dry
            - 0.6733 * common.no_vegetation
            + 0.2284 * common.broadleaved_grass
            - 0.9416 * common.lichen
            + 0.1769 * common.peat
            + 0.5704 * common.road
        )
        p = self._prob_from_logit(lp)
        p_use = sapling_occ[IngrowthSpeciesGroup.BIRCH] if use_initial_period0 else p
        if deterministic:
            prob_small = p_use
            calc_small = not (use_initial_period0 and p_use <= 0.0)
        else:
            prob_small = 1.0 if rng.random() <= p_use else 0.0
            calc_small = prob_small > 0.0
        if not calc_small:
            return prob_small, 0.0, 0.0, 0.0, spruce_small_tree_probability

        bx = 0.4407 * lp - 0.0044 * common.mean_age_excl_overstorey_capped_years
        linp = (
            -3.5299
            - 0.0275 * common.basal_area_capped_m2_ha
            + 0.2405 * common.rich_vegetation
            + 0.3512 * common.mesic_indicator
        )
        lnp = self._prob_from_logit(linp)
        num_small = self._number_of_small_trees(7.7188, bx, lnp)
        lndbh = 7.4224 + 0.0179 * common.site_index_m + 0.05
        mean_dbh = sqrt(exp(lndbh)) / 10.0
        if deterministic:
            n_ingrowth = num_small * prob_small
        else:
            n_ingrowth = num_small if prob_small > 0.0 else 0.0
        return prob_small, num_small, n_ingrowth, mean_dbh, spruce_small_tree_probability

    def _ingrowth_other_broadleaf(
        self,
        *,
        common: CommonData,
        sapling_occ: Mapping[IngrowthSpeciesGroup, float],
        use_initial_period0: bool,
        deterministic: bool,
        rng: random.Random | None,
        spruce_small_tree_probability: float,
    ) -> tuple[float, float, float, float, float]:
        """Compute other broadleaf (Olov1) ingrowth steps.

        Args:
            common (CommonData): Precomputed stand/site variables (see CommonData for details).
            sapling_occ (Mapping[IngrowthSpeciesGroup, float]): Sapling occurrence indicators.
            use_initial_period0 (bool): Use sapling occurrence in step-1 for period 0.
            deterministic (bool): If True, use expected values instead of draws.
            rng (random.Random | None): RNG used when deterministic is False.
            spruce_small_tree_probability (float): Spruce small-tree probability passed
                forward.

        Returns:
            tuple[float, float, float, float, float]: (probability_small_trees,
            number_small_trees, number_ingrowth_trees, mean_diameter_cm,
            spruce_small_tree_probability_out).
        """
        rng = self._resolve_rng(rng)
        lp = (
            -1.0898
            - 0.027 * common.basal_area_capped_m2_ha
            - 0.3665 * common.altitude_scaled
            + 1.3327 * common.other_broadleaf_presence_10cm
            - 0.5057 * common.gotland
            + 0.2112 * common.soil_moisture_code
            + 0.1523 * common.ground_water_indicator
            - 0.5936 * common.shrubs
            + 0.6112 * common.herb_without_shrubs
            - 1.4621 * common.sedge
            - 1.4304 * common.lichen
            - 0.1545 * common.peat
            - 0.2185 * common.swamp_moss
        )
        p = self._prob_from_logit(lp)
        p_use = sapling_occ[IngrowthSpeciesGroup.OTHER_BROADLEAF] if use_initial_period0 else p
        if deterministic:
            prob_small = p_use
            calc_small = not (use_initial_period0 and p_use <= 0.0)
        else:
            prob_small = 1.0 if rng.random() <= p_use else 0.0
            calc_small = prob_small > 0.0
        if not calc_small:
            return prob_small, 0.0, 0.0, 0.0, spruce_small_tree_probability

        bx = (
            0.4989 * lp
            - 0.0383 * common.basal_area_capped_m2_ha
            + 0.7363 * common.temperature_sum_scaled
            - 0.0352 * common.temperature_sum_scaled_squared
        )
        lnp = 0.0452
        num_small = self._number_of_small_trees(0.6155, bx, lnp)
        mean_dbh = 48.9 / 10.0
        if deterministic:
            n_ingrowth = num_small * prob_small
        else:
            n_ingrowth = num_small if prob_small > 0.0 else 0.0
        return prob_small, num_small, n_ingrowth, mean_dbh, spruce_small_tree_probability

    def _ingrowth_oak(
        self,
        *,
        common: CommonData,
        sapling_occ: Mapping[IngrowthSpeciesGroup, float],
        use_initial_period0: bool,
        deterministic: bool,
        rng: random.Random | None,
        spruce_small_tree_probability: float,
    ) -> tuple[float, float, float, float, float]:
        """Compute oak ingrowth steps.

        Args:
            common (CommonData): Precomputed stand/site variables (see CommonData for details).
            sapling_occ (Mapping[IngrowthSpeciesGroup, float]): Sapling occurrence indicators.
            use_initial_period0 (bool): Use sapling occurrence in step-1 for period 0.
            deterministic (bool): If True, use expected values instead of draws.
            rng (random.Random | None): RNG used when deterministic is False.
            spruce_small_tree_probability (float): Spruce small-tree probability passed
                forward.

        Returns:
            tuple[float, float, float, float, float]: (probability_small_trees,
            number_small_trees, number_ingrowth_trees, mean_diameter_cm,
            spruce_small_tree_probability_out).
        """
        rng = self._resolve_rng(rng)
        lp = (
            33.976
            - 0.021 * common.basal_area_capped_m2_ha
            - 0.0073 * common.mean_age_excl_overstorey_capped_years
            - 0.8561 * common.altitude_scaled
            - 0.059 * common.latitude_scaled
            + 1.1611 * common.oak_presence_10cm
            - 0.6769 * common.thinning_0_5_years
            - 0.4802 * common.soil_moisture_code
            + 0.4357 * common.soil_texture_code_sqrt
        )
        p = self._prob_from_logit(lp)
        p_use = sapling_occ[IngrowthSpeciesGroup.OAK] if use_initial_period0 else p
        if deterministic:
            prob_small = p_use
            calc_small = not (use_initial_period0 and p_use <= 0.0)
        else:
            prob_small = 1.0 if rng.random() <= p_use else 0.0
            calc_small = prob_small > 0.0
        if not calc_small:
            return prob_small, 0.0, 0.0, 0.0, spruce_small_tree_probability

        bx = 0.3272 * lp - 0.0121 * common.mean_age_excl_overstorey_capped_years
        lnp = 0.0406
        num_small = self._number_of_small_trees(8.3071, bx, lnp)
        mean_dbh = 47.3 / 10.0
        if deterministic:
            n_ingrowth = num_small * prob_small
        else:
            n_ingrowth = num_small if prob_small > 0.0 else 0.0
        return prob_small, num_small, n_ingrowth, mean_dbh, spruce_small_tree_probability

    def _ingrowth_beech(
        self,
        *,
        common: CommonData,
        sapling_occ: Mapping[IngrowthSpeciesGroup, float],
        use_initial_period0: bool,
        deterministic: bool,
        rng: random.Random | None,
        spruce_small_tree_probability: float,
    ) -> tuple[float, float, float, float, float]:
        """Compute beech ingrowth steps.

        Args:
            common (CommonData): Precomputed stand/site variables (see CommonData for details).
            sapling_occ (Mapping[IngrowthSpeciesGroup, float]): Sapling occurrence indicators.
            use_initial_period0 (bool): Use sapling occurrence in step-1 for period 0.
            deterministic (bool): If True, use expected values instead of draws.
            rng (random.Random | None): RNG used when deterministic is False.
            spruce_small_tree_probability (float): Spruce small-tree probability passed
                forward.

        Returns:
            tuple[float, float, float, float, float]: (probability_small_trees,
            number_small_trees, number_ingrowth_trees, mean_diameter_cm,
            spruce_small_tree_probability_out).
        """
        rng = self._resolve_rng(rng)
        lp = (
            -9.3382
            - 0.0231 * common.basal_area_capped_m2_ha
            - 0.0118 * common.mean_age_excl_overstorey_capped_years
            + 0.0285 * common.temperature_sum_scaled_squared
            # pyforestry applies the beech-presence coefficient per Wikberg (2004),
            # so beech presence enters the ingrowth prediction.
            + 4.0056 * common.beech_presence_10cm
            + 0.9387 * common.no_vegetation
            + 0.6695 * common.thinleaved_grass
        )
        p = self._prob_from_logit(lp)
        p_use = sapling_occ[IngrowthSpeciesGroup.BEECH] if use_initial_period0 else p
        if deterministic:
            prob_small = p_use
            calc_small = not (use_initial_period0 and p_use <= 0.0)
        else:
            prob_small = 1.0 if rng.random() <= p_use else 0.0
            calc_small = prob_small > 0.0
        if not calc_small:
            return prob_small, 0.0, 0.0, 0.0, spruce_small_tree_probability

        bx = 0.0324 * lp - 0.0141 * common.mean_age_excl_overstorey_capped_years
        lnp = 0.0594
        num_small = self._number_of_small_trees(6.6233, bx, lnp)
        mean_dbh = 43.6 / 10.0
        if deterministic:
            n_ingrowth = num_small * prob_small
        else:
            n_ingrowth = num_small if prob_small > 0.0 else 0.0
        return prob_small, num_small, n_ingrowth, mean_dbh, spruce_small_tree_probability

    def _ingrowth_southern_broadleaf(
        self,
        *,
        common: CommonData,
        sapling_occ: Mapping[IngrowthSpeciesGroup, float],
        use_initial_period0: bool,
        deterministic: bool,
        rng: random.Random | None,
        spruce_small_tree_probability: float,
    ) -> tuple[float, float, float, float, float]:
        """Compute southern broadleaf (Olov2) ingrowth steps.

        Args:
            common (CommonData): Precomputed stand/site variables (see CommonData for details).
            sapling_occ (Mapping[IngrowthSpeciesGroup, float]): Sapling occurrence indicators.
            use_initial_period0 (bool): Use sapling occurrence in step-1 for period 0.
            deterministic (bool): If True, use expected values instead of draws.
            rng (random.Random | None): RNG used when deterministic is False.
            spruce_small_tree_probability (float): Spruce small-tree probability passed
                forward.

        Returns:
            tuple[float, float, float, float, float]: (probability_small_trees,
            number_small_trees, number_ingrowth_trees, mean_diameter_cm,
            spruce_small_tree_probability_out).
        """
        rng = self._resolve_rng(rng)
        lp = (
            -12.506
            + 0.472 * common.temperature_sum_scaled
            + 3.3092 * common.southern_broadleaf_presence_10cm
            + 2.3856 * common.herb
        )
        p = self._prob_from_logit(lp)
        p_use = sapling_occ[IngrowthSpeciesGroup.SOUTHERN_BROADLEAF] if use_initial_period0 else p
        if deterministic:
            prob_small = p_use
            calc_small = not (use_initial_period0 and p_use <= 0.0)
        else:
            prob_small = 1.0 if rng.random() <= p_use else 0.0
            calc_small = prob_small > 0.0
        if not calc_small:
            return prob_small, 0.0, 0.0, 0.0, spruce_small_tree_probability

        bx = 0.1551 * lp
        lnp = 0.0442
        num_small = self._number_of_small_trees(8.4818, bx, lnp)
        mean_dbh = 45.1 / 10.0
        if deterministic:
            n_ingrowth = num_small * prob_small
        else:
            n_ingrowth = num_small if prob_small > 0.0 else 0.0
        return prob_small, num_small, n_ingrowth, mean_dbh, spruce_small_tree_probability

    @classmethod
    def build_common_data(
        cls,
        *,
        basal_area_m2_ha: float,
        mean_age_excl_overstorey_years: float,
        temperature_sum_dd: float,
        altitude_m: float,
        latitude_deg: float,
        soil_moisture: Sweden.SoilMoistureEnum,
        soil_texture: Sweden.SoilTextureTill | Sweden.SoilTextureSediment,
        soil_water: Sweden.SoilWater,
        bottom_layer: Sweden.BottomLayer,
        field_layer: Sweden.FieldLayer,
        peat: bool,
        site_index_m: float,
        species_ba_m2_ha: Mapping[IngrowthSpeciesGroup, float],
        species_presence_10cm: Mapping[IngrowthSpeciesGroup, int],
        gotland: int = 0,
        thinning_0_5_years: int = 0,
        thinning_6_10_years: int = 0,
        visibility_cleaning: int = 0,
        field: int = 0,
        edge: int = 0,
        road: int = 0,
    ) -> CommonData:
        """Build common ingrowth variables from resolved inputs.

        Args:
            basal_area_m2_ha (float): Basal area (m2/ha).
            mean_age_excl_overstorey_years (float): Mean age excluding overstorey.
            temperature_sum_dd (float): Temperature sum (degree-days > 5C).
            altitude_m (float): Altitude (m).
            latitude_deg (float): Latitude (degrees).
            soil_moisture (Sweden.SoilMoistureEnum): Soil moisture class.
            soil_texture (Sweden.SoilTextureTill | Sweden.SoilTextureSediment): Soil texture.
            soil_water (Sweden.SoilWater): Soil water class.
            bottom_layer (Sweden.BottomLayer): Bottom layer class.
            field_layer (Sweden.FieldLayer): Field layer vegetation class.
            peat (bool): Peat indicator.
            site_index_m (float): Site index (m). This should be the H100 site index for the
                stand's main conifer species; use ``SiteIndexValue`` with ``predict`` if you
                want validation.
            species_ba_m2_ha (Mapping[IngrowthSpeciesGroup, float]): Basal area per group.
            species_presence_10cm (Mapping[IngrowthSpeciesGroup, int]): Presence indicators for
                dbh >= 10 cm (pine_presence_10cm, spruce_presence_10cm, birch_presence_10cm,
                other_broadleaf_presence_10cm, oak_presence_10cm, beech_presence_10cm,
                southern_broadleaf_presence_10cm).
            gotland (int): Gotland indicator (1 if county is Gotland, else 0).
            thinning_0_5_years (int): Thinning indicator for years 0-5 (1 if thinned).
            thinning_6_10_years (int): Thinning indicator for years 6-10 (1 if thinned).
            visibility_cleaning (int): Visibility cleaning indicator (0/1).
            field (int): Field position indicator (0/1).
            edge (int): Stand edge indicator (0/1).
            road (int): Road position indicator (0/1).

        Returns:
            CommonData: Transformed variables used in the ingrowth model.

        Raises:
            ValueError: If transformed variables are undefined (e.g. Ts == 3 or alt <= 0).
        """
        basal_area_capped_m2_ha = min(100.0, basal_area_m2_ha)
        basal_area_capped_sqrt = sqrt(basal_area_capped_m2_ha)
        inv_basal_area_capped_plus5 = 1.0 / (5.0 + basal_area_capped_m2_ha)

        mean_age_excl_overstorey_capped_years = min(160.0, mean_age_excl_overstorey_years)
        log_mean_age_excl_overstorey_capped_years = log(mean_age_excl_overstorey_capped_years)
        inv_mean_age_excl_overstorey_capped_plus5 = 1.0 / (
            5.0 + mean_age_excl_overstorey_capped_years
        )

        temperature_sum_scaled = temperature_sum_dd * 0.01
        if abs(temperature_sum_scaled - 3.0) < 1e-9:
            raise ValueError(
                "temperature_sum_dd yields temperature_sum_scaled == 3, inv(Ts-3) undefined."
            )
        temperature_sum_scaled_squared = temperature_sum_scaled**2
        inv_temperature_sum_scaled_minus3 = 1.0 / (temperature_sum_scaled - 3.0)

        altitude_scaled = altitude_m * 0.01
        if altitude_scaled <= 0:
            raise ValueError("altitude_m must be > 0 to compute log(altitude_scaled).")
        log_altitude_scaled = log(altitude_scaled)
        altitude_scaled_squared = altitude_scaled**2

        latitude_scaled = latitude_deg * 10.0
        latitude_scaled_squared = (latitude_scaled**2) * 0.01
        latitude_over_60 = latitude_deg > 60.0

        soil_moisture_code = 2
        mesic_indicator = 0
        if soil_moisture == Sweden.SoilMoistureEnum.DRY:
            soil_moisture_code = 1
        elif soil_moisture in {
            Sweden.SoilMoistureEnum.MESIC,
            Sweden.SoilMoistureEnum.MESIC_MOIST,
        }:
            soil_moisture_code = 2
            mesic_indicator = 1
        elif soil_moisture == Sweden.SoilMoistureEnum.MOIST:
            soil_moisture_code = 3
        elif soil_moisture == Sweden.SoilMoistureEnum.WET:
            soil_moisture_code = 4

        ground_water_indicator = 0 if soil_water == Sweden.SoilWater.SELDOM_NEVER else 1
        soil_texture_code_sqrt = sqrt(soil_texture.value.code)

        veg = cls._vegetation_indicators(field_layer)

        peat_indicator = 1 if peat else 0
        bog_moss = 1 if bottom_layer == Sweden.BottomLayer.BOGMOSS_TYPE else 0
        swamp_moss = 1 if bottom_layer == Sweden.BottomLayer.SWAMP_MOSS else 0

        spruce_basal_area_share = (
            species_ba_m2_ha.get(IngrowthSpeciesGroup.SPRUCE, 0.0) / basal_area_capped_m2_ha
            if basal_area_capped_m2_ha > 0
            else 0.0
        )

        return CommonData(
            basal_area_capped_m2_ha=basal_area_capped_m2_ha,
            basal_area_capped_sqrt=basal_area_capped_sqrt,
            inv_basal_area_capped_plus5=inv_basal_area_capped_plus5,
            mean_age_excl_overstorey_capped_years=mean_age_excl_overstorey_capped_years,
            log_mean_age_excl_overstorey_capped_years=log_mean_age_excl_overstorey_capped_years,
            inv_mean_age_excl_overstorey_capped_plus5=inv_mean_age_excl_overstorey_capped_plus5,
            temperature_sum_scaled=temperature_sum_scaled,
            temperature_sum_scaled_squared=temperature_sum_scaled_squared,
            inv_temperature_sum_scaled_minus3=inv_temperature_sum_scaled_minus3,
            altitude_scaled=altitude_scaled,
            log_altitude_scaled=log_altitude_scaled,
            altitude_scaled_squared=altitude_scaled_squared,
            latitude_scaled=latitude_scaled,
            latitude_scaled_squared=latitude_scaled_squared,
            latitude_over_60=latitude_over_60,
            spruce_small_tree_probability=1.0,
            pine_presence_10cm=species_presence_10cm.get(IngrowthSpeciesGroup.PINE, 0),
            spruce_presence_10cm=species_presence_10cm.get(IngrowthSpeciesGroup.SPRUCE, 0),
            birch_presence_10cm=species_presence_10cm.get(IngrowthSpeciesGroup.BIRCH, 0),
            other_broadleaf_presence_10cm=species_presence_10cm.get(
                IngrowthSpeciesGroup.OTHER_BROADLEAF, 0
            ),
            oak_presence_10cm=species_presence_10cm.get(IngrowthSpeciesGroup.OAK, 0),
            beech_presence_10cm=species_presence_10cm.get(IngrowthSpeciesGroup.BEECH, 0),
            southern_broadleaf_presence_10cm=species_presence_10cm.get(
                IngrowthSpeciesGroup.SOUTHERN_BROADLEAF, 0
            ),
            thinning_0_5_years=thinning_0_5_years,
            thinning_6_10_years=thinning_6_10_years,
            visibility_cleaning=visibility_cleaning,
            gotland=gotland,
            soil_moisture_code=soil_moisture_code,
            ground_water_indicator=ground_water_indicator,
            soil_texture_code_sqrt=soil_texture_code_sqrt,
            poor_vegetation=veg["poor_vegetation"],
            shrubs=veg["shrubs"],
            poor_shrubs=veg["poor_shrubs"],
            herb=veg["herb"],
            herb_without_shrubs=veg["herb_without_shrubs"],
            herb_with_shrubs=veg["herb_with_shrubs"],
            herb_without_shrubs_dry=veg["herb_without_shrubs_dry"],
            no_vegetation=veg["no_vegetation"],
            broadleaved_grass=veg["broadleaved_grass"],
            thinleaved_grass=veg["thinleaved_grass"],
            sedge=veg["sedge"],
            lichen=veg["lichen"],
            peat=peat_indicator,
            bog_moss=bog_moss,
            swamp_moss=swamp_moss,
            field=field,
            edge=edge,
            road=road,
            rich_vegetation=veg["rich_vegetation"],
            site_index_m=site_index_m,
            spruce_basal_area_share=spruce_basal_area_share,
            mesic_indicator=mesic_indicator,
        )

    @staticmethod
    def to_plot_trees(result: IngrowthResult, plot_area_ha: float) -> list[Tree]:
        """Scale per-ha ingrowth trees to a plot area.

        Args:
            result (IngrowthResult): Per-ha ingrowth result.
            plot_area_ha (float): Plot area in hectares.

        Returns:
            list[Tree]: Trees scaled to plot area.
        """
        trees: list[Tree] = []
        for group, dbh in result.mean_diameter_cm.items():
            trees.append(
                Tree(
                    species=_REPRESENTATIVE_SPECIES[group],
                    diameter_cm=dbh,
                    weight_n=result.number_ingrowth_trees.get(group, 0.0) * plot_area_ha,
                )
            )
        return trees

    @staticmethod
    def _resolve_rng(rng: random.Random | None) -> random.Random:
        """Ensure a usable RNG when stochastic paths are requested."""
        return rng if rng is not None else random.Random()

    @staticmethod
    def _prob_from_logit(lp: float) -> float:
        """Convert a linear predictor to a probability.

        Args:
            lp (float): Linear predictor.

        Returns:
            float: Probability in [0, 1].
        """
        return 1.0 / (1.0 + exp(-lp))

    @staticmethod
    def _number_of_small_trees(b0: float, bx: float, lnp: float) -> float:
        """Compute number of small trees (per ha) passing the ingrowth limit.

        Args:
            b0 (float): Intercept coefficient in step-2 model.
            bx (float): Linear predictor in step-2 model.
            lnp (float): Probability that small trees pass the 4 cm limit.

        Returns:
            float: Expected number of ingrowth candidates per ha.
        """
        to_ha_weight = 10000.0 / (3.141592653589793 * 5 * 5)
        number_of_small_trees = 1.0 + b0 * exp(bx)
        return number_of_small_trees * lnp * to_ha_weight

    @staticmethod
    def _resolve_site_index_m(site_index_m: float | SiteIndexValue) -> float:
        """Normalize site index input and validate SiteIndexValue metadata.

        Args:
            site_index_m (float | SiteIndexValue): Site index in meters. If a SiteIndexValue
                is provided, it must be H100 from Hagglund 1970 for pine or spruce.

        Returns:
            float: Site index in meters.

        Raises:
            TypeError: If site_index_m is not a float or SiteIndexValue.
            ValueError: If SiteIndexValue metadata is incompatible with Wikberg (2004).
        """
        if isinstance(site_index_m, SiteIndexValue):
            validate_hagglund_1970_h100_site_index(
                site_index_m,
                param_name="site_index_m",
                allowed_species={
                    TreeSpecies.Sweden.pinus_sylvestris,
                    TreeSpecies.Sweden.picea_abies,
                },
            )
            return float(site_index_m)
        if isinstance(site_index_m, (float, int)):
            return float(site_index_m)
        raise TypeError("site_index_m must be a float or SiteIndexValue.")

    @staticmethod
    def _species_group_for_tree(species: TreeName) -> IngrowthSpeciesGroup | None:
        """Map a tree species to an ingrowth species group.

        Args:
            species (TreeName): Tree species identifier.

        Returns:
            IngrowthSpeciesGroup | None: Matching ingrowth group, or None if not mapped.
        """
        if species in _PINE_SPECIES:
            return IngrowthSpeciesGroup.PINE
        if species in _SPRUCE_SPECIES:
            return IngrowthSpeciesGroup.SPRUCE
        if species in _BIRCH_SPECIES:
            return IngrowthSpeciesGroup.BIRCH
        if species in _OAK_SPECIES:
            return IngrowthSpeciesGroup.OAK
        if species in _BEECH_SPECIES:
            return IngrowthSpeciesGroup.BEECH
        if species in _SOUTHERN_BROADLEAF_SPECIES:
            return IngrowthSpeciesGroup.SOUTHERN_BROADLEAF
        if species in _OTHER_BROADLEAF_SPECIES:
            return IngrowthSpeciesGroup.OTHER_BROADLEAF
        return None

    @staticmethod
    def _trees_from_stand(stand: Stand | None) -> list[Tree]:
        """Extract tree list from a stand when available.

        Args:
            stand (Stand | None): Stand with plots and trees.

        Returns:
            list[Tree]: Flattened tree list or empty when unavailable.
        """
        if stand is None or stand.use_angle_count:
            return []
        return [t for plot in stand.plots for t in plot.trees]

    @staticmethod
    def _vegetation_indicators(field_layer: Sweden.FieldLayer | None) -> dict[str, int]:
        """Map field layer to vegetation indicator flags.

        Args:
            field_layer (Sweden.FieldLayer | None): Field layer vegetation class.

        Returns:
            dict[str, int]: Vegetation indicator flags used by the model. Keys include:
            poor_vegetation, poor_shrubs, shrubs, herb, herb_without_shrubs, herb_with_shrubs,
            herb_without_shrubs_dry, no_vegetation, broadleaved_grass, thinleaved_grass, sedge,
            lichen, rich_vegetation.
        """
        poor_vegetation = poor_shrubs = shrubs = herb = herb_without_shrubs = 0
        herb_with_shrubs = herb_without_shrubs_dry = 0
        no_vegetation = broadleaved_grass = thinleaved_grass = sedge = lichen = 0
        rich_vegetation = 0

        if field_layer is None:
            return {
                "poor_vegetation": poor_vegetation,
                "poor_shrubs": poor_shrubs,
                "shrubs": shrubs,
                "herb": herb,
                "herb_without_shrubs": herb_without_shrubs,
                "herb_with_shrubs": herb_with_shrubs,
                "herb_without_shrubs_dry": herb_without_shrubs_dry,
                "no_vegetation": no_vegetation,
                "broadleaved_grass": broadleaved_grass,
                "thinleaved_grass": thinleaved_grass,
                "sedge": sedge,
                "lichen": lichen,
                "rich_vegetation": rich_vegetation,
            }

        if field_layer in {
            Sweden.FieldLayer.HIGH_HERB_WITHOUT_SHRUBS,
            Sweden.FieldLayer.LOW_HERB_WITHOUT_SHRUBS,
        }:
            herb = 1
            herb_without_shrubs = 1
            herb_without_shrubs_dry = 1
            rich_vegetation = 1
        elif field_layer in {
            Sweden.FieldLayer.HIGH_HERB_WITH_SHRUBS_BLUEBERRY,
            Sweden.FieldLayer.HIGH_HERB_WITH_SHRUBS_LINGON,
        }:
            herb = 1
            herb_without_shrubs = 1
            herb_with_shrubs = 1
            rich_vegetation = 1
        elif field_layer in {
            Sweden.FieldLayer.LOW_HERB_WITH_SHRUBS_BLUEBERRY,
            Sweden.FieldLayer.LOW_HERB_WITH_SHRUBS_LINGON,
        }:
            herb = 1
            herb_with_shrubs = 1
            rich_vegetation = 1
        elif field_layer == Sweden.FieldLayer.NO_FIELD_LAYER:
            no_vegetation = 1
            rich_vegetation = 1
        elif field_layer == Sweden.FieldLayer.BROADLEAVED_GRASS:
            broadleaved_grass = 1
            rich_vegetation = 1
        elif field_layer == Sweden.FieldLayer.THINLEAVED_GRASS:
            thinleaved_grass = 1
            rich_vegetation = 1
        elif field_layer == Sweden.FieldLayer.HORSETAIL:
            rich_vegetation = 1
        elif field_layer == Sweden.FieldLayer.SEDGE_HIGH:
            sedge = 1
        elif field_layer == Sweden.FieldLayer.SEDGE_LOW:
            sedge = 1
            poor_vegetation = 1
        elif field_layer in {
            Sweden.FieldLayer.LINGONBERRY,
            Sweden.FieldLayer.CROWBERRY,
            Sweden.FieldLayer.POOR_SHRUB,
        }:
            poor_vegetation = 1
            poor_shrubs = 1
            shrubs = 1
        elif field_layer in {Sweden.FieldLayer.LICHEN_FREQUENT, Sweden.FieldLayer.LICHEN_DOMINANT}:
            poor_vegetation = 1
            poor_shrubs = 1
            lichen = 1
            shrubs = 1
        elif field_layer == Sweden.FieldLayer.BILBERRY:
            shrubs = 1

        return {
            "poor_vegetation": poor_vegetation,
            "poor_shrubs": poor_shrubs,
            "shrubs": shrubs,
            "herb": herb,
            "herb_without_shrubs": herb_without_shrubs,
            "herb_with_shrubs": herb_with_shrubs,
            "herb_without_shrubs_dry": herb_without_shrubs_dry,
            "no_vegetation": no_vegetation,
            "broadleaved_grass": broadleaved_grass,
            "thinleaved_grass": thinleaved_grass,
            "sedge": sedge,
            "lichen": lichen,
            "rich_vegetation": rich_vegetation,
        }


def build_common_data(
    *,
    basal_area_m2_ha: float,
    mean_age_excl_overstorey_years: float,
    temperature_sum_dd: float,
    altitude_m: float,
    latitude_deg: float,
    soil_moisture: Sweden.SoilMoistureEnum,
    soil_texture: Sweden.SoilTextureTill | Sweden.SoilTextureSediment,
    soil_water: Sweden.SoilWater,
    bottom_layer: Sweden.BottomLayer,
    field_layer: Sweden.FieldLayer,
    peat: bool,
    site_index_m: float,
    species_ba_m2_ha: Mapping[IngrowthSpeciesGroup, float],
    species_presence_10cm: Mapping[IngrowthSpeciesGroup, int],
    gotland: int = 0,
    thinning_0_5_years: int = 0,
    thinning_6_10_years: int = 0,
    visibility_cleaning: int = 0,
    field: int = 0,
    edge: int = 0,
    road: int = 0,
) -> CommonData:
    """Build common ingrowth variables from resolved inputs.

    Args:
        basal_area_m2_ha (float): Basal area (m2/ha).
        mean_age_excl_overstorey_years (float): Mean age excluding overstorey.
        temperature_sum_dd (float): Temperature sum (degree-days > 5C).
        altitude_m (float): Altitude (m).
        latitude_deg (float): Latitude (degrees).
        soil_moisture (Sweden.SoilMoistureEnum): Soil moisture class.
        soil_texture (Sweden.SoilTextureTill | Sweden.SoilTextureSediment): Soil texture.
        soil_water (Sweden.SoilWater): Soil water class.
        bottom_layer (Sweden.BottomLayer): Bottom layer class.
        field_layer (Sweden.FieldLayer): Field layer vegetation class.
        peat (bool): Peat indicator.
        site_index_m (float): Site index (m). This should be the H100 site index for the
            stand's main conifer species; use ``SiteIndexValue`` with ``predict`` if you want
            validation.
        species_ba_m2_ha (Mapping[IngrowthSpeciesGroup, float]): Basal area per group.
        species_presence_10cm (Mapping[IngrowthSpeciesGroup, int]): Presence indicators for
            dbh >= 10 cm (pine_presence_10cm, spruce_presence_10cm, birch_presence_10cm,
            other_broadleaf_presence_10cm, oak_presence_10cm, beech_presence_10cm,
            southern_broadleaf_presence_10cm).
        gotland (int): Gotland indicator (1 if county is Gotland, else 0).
        thinning_0_5_years (int): Thinning indicator for years 0-5 (1 if thinned).
        thinning_6_10_years (int): Thinning indicator for years 6-10 (1 if thinned).
        visibility_cleaning (int): Visibility cleaning indicator (0/1).
        field (int): Field position indicator (0/1).
        edge (int): Stand edge indicator (0/1).
        road (int): Road position indicator (0/1).

    Returns:
        CommonData: Transformed variables used in the ingrowth model.

    Raises:
        ValueError: If transformed variables are undefined (e.g. Ts == 3 or alt <= 0).
    """
    return Wikberg2004Ingrowth.build_common_data(
        basal_area_m2_ha=basal_area_m2_ha,
        mean_age_excl_overstorey_years=mean_age_excl_overstorey_years,
        temperature_sum_dd=temperature_sum_dd,
        altitude_m=altitude_m,
        latitude_deg=latitude_deg,
        soil_moisture=soil_moisture,
        soil_texture=soil_texture,
        soil_water=soil_water,
        bottom_layer=bottom_layer,
        field_layer=field_layer,
        peat=peat,
        site_index_m=site_index_m,
        species_ba_m2_ha=species_ba_m2_ha,
        species_presence_10cm=species_presence_10cm,
        gotland=gotland,
        thinning_0_5_years=thinning_0_5_years,
        thinning_6_10_years=thinning_6_10_years,
        visibility_cleaning=visibility_cleaning,
        field=field,
        edge=edge,
        road=road,
    )


def ingrowth_predict(
    *,
    stand: Stand | None = None,
    site: SwedishSite | None = None,
    site_index_m: float | SiteIndexValue | None = None,
    basal_area_m2_ha: float | None = None,
    qmd_cm: float | QuadraticMeanDiameter | None = None,
    mean_age_excl_overstorey_years: float | None = None,
    temperature_sum_dd: float | None = None,
    latitude_deg: float | None = None,
    altitude_m: float | None = None,
    soil_moisture: Sweden.SoilMoistureEnum | None = None,
    soil_texture: Sweden.SoilTextureTill | Sweden.SoilTextureSediment | None = None,
    soil_water: Sweden.SoilWater | None = None,
    bottom_layer: Sweden.BottomLayer | None = None,
    field_layer: Sweden.FieldLayer | None = None,
    peat: bool | None = None,
    gotland: int | None = None,
    species_ba_m2_ha: Mapping[IngrowthSpeciesGroup, float] | None = None,
    species_presence_10cm: Mapping[IngrowthSpeciesGroup, int] | None = None,
    sapling_occurrence: Mapping[IngrowthSpeciesGroup, float] | None = None,
    deterministic: bool = True,
    rng: random.Random | None = None,
    use_initial_saplings: bool = False,
    period_index: int = 0,
    min_mean_age_invoke: float = 50.0,
    ingrowth_species: Sequence[IngrowthSpeciesGroup] | None = None,
    thinning_0_5_years: int = 0,
    thinning_6_10_years: int = 0,
    visibility_cleaning: int = 0,
    field: int = 0,
    edge: int = 0,
    road: int = 0,
    plot_is_saplings: bool = False,
) -> IngrowthResult:
    """Convenience wrapper around :class:`Wikberg2004Ingrowth`.

    Args:
        stand (Stand | None): Optional stand used for basal area, QMD, and tree list.
            Tree diameters are read from ``Tree.diameter_cm`` (usually ``Diameter_cm``).
        site (SwedishSite | None): Optional site used to populate missing site inputs.
        site_index_m (float | SiteIndexValue | None): Site index for the stand (m). Prefer
            ``SiteIndexValue`` (H100 from Hagglund 1970) for pine or spruce.
        basal_area_m2_ha (float | None): Basal area (m2/ha).
        qmd_cm (float | QuadraticMeanDiameter | None): Quadratic mean diameter (cm) used
            for gating.
        mean_age_excl_overstorey_years (float | None): Mean age excluding overstorey.
        temperature_sum_dd (float | None): Temperature sum (degree-days > 5C).
        latitude_deg (float | None): Latitude (degrees).
        altitude_m (float | None): Altitude (m).
        soil_moisture (Sweden.SoilMoistureEnum | None): Soil moisture class.
        soil_texture (Sweden.SoilTextureTill | Sweden.SoilTextureSediment | None): Soil texture.
        soil_water (Sweden.SoilWater | None): Soil water class.
        bottom_layer (Sweden.BottomLayer | None): Bottom layer class.
        field_layer (Sweden.FieldLayer | None): Field layer vegetation class.
        peat (bool | None): Peat indicator. If None, derived from soil_texture if possible.
        gotland (int | None): Gotland indicator (1 if county is Gotland, else 0).
        species_ba_m2_ha (Mapping | None): Basal area per ingrowth species group (m2/ha).
        species_presence_10cm (Mapping | None): Presence indicators for dbh >= 10 cm
            (pine_presence_10cm, spruce_presence_10cm, birch_presence_10cm,
            other_broadleaf_presence_10cm, oak_presence_10cm, beech_presence_10cm,
            southern_broadleaf_presence_10cm).
        sapling_occurrence (Mapping | None): Sapling occurrence indicators for dbh < 4 cm.
        deterministic (bool): If True, apply deterministic ingrowth.
        rng (random.Random | None): RNG used when deterministic is False.
        use_initial_saplings (bool): If True, use sapling occurrence in period 0.
        period_index (int): Period index (0 for first period).
        min_mean_age_invoke (float): Minimum mean age to invoke ingrowth.
        ingrowth_species (Sequence[IngrowthSpeciesGroup] | None): Species groups to include.
        thinning_0_5_years (int): Thinning indicator for years 0-5 (1 if thinned).
        thinning_6_10_years (int): Thinning indicator for years 6-10 (1 if thinned).
        visibility_cleaning (int): Visibility cleaning indicator (0/1).
        field (int): Field position indicator (0/1).
        edge (int): Stand edge indicator (0/1).
        road (int): Road position indicator (0/1).
        plot_is_saplings (bool): Skip ingrowth if plot type is saplings.

    Returns:
        IngrowthResult: Per-ha metrics and a generated tree list.
    """
    model = Wikberg2004Ingrowth(
        deterministic=deterministic,
        use_initial_saplings=use_initial_saplings,
        min_mean_age_invoke=min_mean_age_invoke,
        ingrowth_species=ingrowth_species,
        rng=rng,
    )
    return model.predict(
        stand=stand,
        site=site,
        site_index_m=site_index_m,
        basal_area_m2_ha=basal_area_m2_ha,
        qmd_cm=qmd_cm,
        mean_age_excl_overstorey_years=mean_age_excl_overstorey_years,
        temperature_sum_dd=temperature_sum_dd,
        latitude_deg=latitude_deg,
        altitude_m=altitude_m,
        soil_moisture=soil_moisture,
        soil_texture=soil_texture,
        soil_water=soil_water,
        bottom_layer=bottom_layer,
        field_layer=field_layer,
        peat=peat,
        gotland=gotland,
        species_ba_m2_ha=species_ba_m2_ha,
        species_presence_10cm=species_presence_10cm,
        sapling_occurrence=sapling_occurrence,
        period_index=period_index,
        thinning_0_5_years=thinning_0_5_years,
        thinning_6_10_years=thinning_6_10_years,
        visibility_cleaning=visibility_cleaning,
        field=field,
        edge=edge,
        road=road,
        plot_is_saplings=plot_is_saplings,
    )


def ingrowth_to_plot_trees(result: IngrowthResult, plot_area_ha: float) -> list[Tree]:
    """Scale per-ha ingrowth trees to a plot area.

    Args:
        result (IngrowthResult): Per-ha ingrowth result.
        plot_area_ha (float): Plot area in hectares.

    Returns:
        list[Tree]: Trees scaled to plot area.
    """
    return Wikberg2004Ingrowth.to_plot_trees(result, plot_area_ha)


__all__ = [
    "IngrowthSpeciesGroup",
    "IngrowthResult",
    "CommonData",
    "Wikberg2004Ingrowth",
    "build_common_data",
    "ingrowth_predict",
    "ingrowth_to_plot_trees",
]


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------


class _Descriptor:
    """FormulaModuleDescriptor for Wikberg (2004) ingrowth model."""

    @property
    def component_id(self):
        return "wikberg_2004_ingrowth"

    @property
    def source(self):
        return SourceReference(
            author="Wikberg, P-E.",
            year=2004,
            title=("Occurrence, morphology and growth of understory saplings in Swedish forests"),
            note=(
                "Doctoral thesis. Acta Universitatis Agriculturae Sueciae, Silvestria 322, "
                "Sveriges lantbruksuniversitet, Umeå. ISBN 91-576-6706-3."
            ),
        )

    @property
    def species_groups(self):
        return {
            "pine": frozenset({"Pinus sylvestris"}),
            "spruce": frozenset({"Picea abies"}),
            "birch": frozenset({"Betula pubescens", "Betula pendula"}),
            "aspen": frozenset({"Populus tremula"}),
            "beech": frozenset({"Fagus sylvatica"}),
            "oak": frozenset({"Quercus robur"}),
        }

    @property
    def units(self):
        return {"basal_area_m2_ha": "m²/ha", "stems_ha": "stems/ha", "diameter_cm": "cm"}

    @property
    def kernel_names(self):
        return ["ingrowth_predict", "build_common_data", "ingrowth_to_plot_trees"]


DESCRIPTOR = _Descriptor()
