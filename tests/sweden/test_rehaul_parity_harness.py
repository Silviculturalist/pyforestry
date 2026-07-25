import inspect
import math

import pytest

from pyforestry.base.helpers import CircularPlot, Stand, Tree
from pyforestry.base.helpers.primitives import Age, SiteBase
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.bark.soderberg_1992 import soderberg_1992_bark_thickness_bh_mm
from pyforestry.sweden.blocks.elfving_1982 import NyskogReconstruction, RegenerationType
from pyforestry.sweden.blocks.elfving_2010 import (
    Elfving2010Model,
    stand_basal_area_growth_elfving_2009,
)
from pyforestry.sweden.blocks.soderberg_1986_growth import Soderberg1986Model
from pyforestry.sweden.height.nystrom_2000 import sapling_height_growth_m
from pyforestry.sweden.height.soderberg_1992 import (
    soderberg_1992_height_stand_age_m,
    soderberg_1992_height_tree_age_m,
)
from pyforestry.sweden.ingrowth.wikberg_2004 import (
    IngrowthSpeciesGroup,
    Wikberg2004Ingrowth,
    build_common_data,
    ingrowth_predict,
    ingrowth_to_plot_trees,
)
from pyforestry.sweden.mortality.naslund_1986 import Naslund1986DamageModel, SaplingSpeciesGroup
from pyforestry.sweden.regeneration.elfving_1992 import Elfving1992Regeneration
from pyforestry.sweden.site.enums import Sweden
from pyforestry.sweden.volume.soderberg_1986_form_height import (
    soderberg_1986_form_height_m,
    soderberg_1986_volume_m3,
)


class _DummySite(SiteBase):
    def compute_attributes(self) -> None:  # pragma: no cover - simple stub
        return None


def _signature_schema(fn) -> list[tuple[str, str, bool]]:
    """Return signature shape as (name, kind, required)."""
    return [
        (
            parameter.name,
            parameter.kind.name,
            parameter.default is inspect.Signature.empty,
        )
        for parameter in inspect.signature(fn).parameters.values()
    ]


def test_parity_soderberg_models_snapshot() -> None:
    bark_mm = soderberg_1992_bark_thickness_bh_mm(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        diameter_cm=25.0,
        max_diameter_cm=40.0,
        mean_age_total_years=80.0,
        site_index_pine_m=20.0,
        latitude_deg=60.0,
        altitude_m=100.0,
        prop_pine=0.6,
        prop_spruce=0.3,
        prop_birch=0.1,
        part_of_sweden="north",
    )
    # Paper-faithful 1/(10*d_cm + 50) diameter term (Söderberg 1992); the previous
    # value 29.221847707621034 used a rounded 11.2838*sqrt(area) encoding (~6e-7 rel).
    assert bark_mm == pytest.approx(29.221829612699917, rel=1e-10, abs=1e-12)

    stand_age_m = soderberg_1992_height_stand_age_m(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        diameter_cm=25.0,
        max_diameter_cm=40.0,
        mean_age_total_years=80.0,
        site_index_pine_m=20.0,
        latitude_deg=60.0,
        altitude_m=100.0,
        prop_pine=0.6,
        prop_spruce=0.3,
        prop_birch=0.1,
        part_of_sweden="north",
    )
    assert stand_age_m == pytest.approx(21.12210818718463, rel=1e-10, abs=1e-12)

    tree_age_m = soderberg_1992_height_tree_age_m(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        diameter_cm=22.0,
        tree_age_bh_years=30.0,
        max_diameter_cm=40.0,
        stand_basal_area_m2_ha=25.0,
        dominant_species=TreeSpecies.Sweden.pinus_sylvestris,
        site_index_dominant_m=20.0,
        latitude_deg=60.0,
        altitude_m=100.0,
        prop_pine=0.6,
        prop_spruce=0.3,
        prop_birch=0.1,
        prop_beech=0.0,
        part_of_sweden="north",
    )
    assert tree_age_m == pytest.approx(13.05522367022596, rel=1e-10, abs=1e-12)

    form_kwargs = dict(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        diameter_cm=30.0,
        age_bh_years=40.0,
        max_diameter_cm=45.0,
        stand_basal_area_m2_ha=25.0,
        dominant_species=TreeSpecies.Sweden.pinus_sylvestris,
        site_index_dominant_m=20.0,
        latitude_deg=60.0,
        altitude_m=100.0,
        part_of_sweden="north",
        distance_to_coast_lt_50km=True,
        split_plot=False,
        crowberry=True,
        south_slope=False,
        wet_soil=False,
        fertilized=False,
        herbs=False,
        maritime=False,
        region5=False,
        continental=False,
        north_slope=False,
        dry_soil=False,
        south_east=False,
        groundwater_never=False,
        prop_pine=0.6,
        prop_spruce=0.3,
        prop_birch=0.1,
        prop_beech=0.0,
        prop_oak=0.0,
        gotland=False,
    )
    form_height_m = soderberg_1986_form_height_m(**form_kwargs)
    volume_m3 = soderberg_1986_volume_m3(**form_kwargs)
    assert form_height_m == pytest.approx(6.881162794364282, rel=1e-10, abs=1e-12)
    assert volume_m3 == pytest.approx(0.48640073586593036, rel=1e-10, abs=1e-12)

    model = Soderberg1986Model()
    stand = Stand(
        site=_DummySite(latitude=60.0, longitude=15.0),
        plots=[
            CircularPlot(
                id=1,
                area_m2=200.0,
                trees=[
                    Tree(
                        species=TreeSpecies.Sweden.pinus_sylvestris,
                        diameter_cm=20.0,
                        age=Age.DBH(40),
                    )
                ],
            )
        ],
    )
    ctx = model.build_context(stand, mode_hint="tree_list")
    ctx.attrs.update(
        {
            "part_of_sweden": "north",
            "latitude_deg": 60.0,
            "altitude_m": 100.0,
            "site_index_species": "pine",
            "site_index_pine_m": 20.0,
            "site_index_spruce_m": 22.0,
            "maritime": 0,
            "south_east": 0,
            "region5": 0,
            "rich": 0,
            "split": False,
            "peat": False,
            "soil_moisture": Sweden.SoilMoistureEnum.MESIC,
        }
    )
    model.update_step(ctx, 5.0)
    assert ctx.plots[0].trees[0].diameter_cm == pytest.approx(
        22.168181754573478,
        rel=1e-10,
        abs=1e-12,
    )


def test_parity_elfving_models_snapshot() -> None:
    # Regeneration stocking (SLH): Elfving 1992, Appendix 1 Table 1 (natural).
    # ground_prepared -> scarified (markberedning); Jonson index fixed at 4.
    asinslh, _slh_est, slh_corr = Elfving1992Regeneration.slh_natural(
        latitude_deg=61.0,
        altitude_m=120.0,
        county=Sweden.County.VARMLAND,
        soil_moisture=Sweden.SoilMoistureEnum.DRY,
        jonson_index=4.0,
        seed_trees_per_ha=150.0,
        regen_area_ha=2.0,
        scarified=True,
        burnt=False,
    )
    # Young-stand quality (ASINW = arcsin(sqrt(W))): Elfving 1982, Hugin Rapport 27.
    asinw = NyskogReconstruction.young_stand_quality_asinw(
        stocking_arcsine_radians=asinslh,
        regeneration_type=RegenerationType.NATURAL,
    )
    assert asinslh == pytest.approx(2.5318215866163936, rel=1e-10, abs=1e-12)
    assert slh_corr == pytest.approx(0.8630720506508575, rel=1e-10, abs=1e-12)
    assert asinw == pytest.approx(1.0710618659719255, rel=1e-10, abs=1e-12)

    stand_growth = stand_basal_area_growth_elfving_2009(
        ln_mean_age=math.log(53.42),
        conifer_share_per_age=1.0 / 53.42,
        pine_share_times_veg=0.0,
        birch_share_sq=0.0,
        birch_share_cold=0.0,
        basal_area_survived_m2_ha=10.68,
        basal_area_all_m2_ha=10.67,
        stem_number_factor=604.79 / (604.79 + 80.0),
        veg=0.0,
        peat=0,
        moist=0,
        wet=0,
        site_index_m=15.0,
        ditch=0,
        fertilized=0,
        edge=0,
        split=0,
        thinned_0_10_years_flag=1,
        thinned_10_30_years_flag=0,
        ln_relative_basal_area=0.0,
        pine_share=0.496,
        spruce_share=0.504,
        use_edge_effects=False,
    )
    assert stand_growth == pytest.approx(2.2020696115571856, rel=1e-10, abs=1e-12)


def test_parity_naslund_wikberg_nystrom_snapshot() -> None:
    stems = {
        SaplingSpeciesGroup.PINE: 1000.0,
        SaplingSpeciesGroup.SPRUCE: 0.0,
        SaplingSpeciesGroup.CONTORTA: 0.0,
        SaplingSpeciesGroup.BIRCH: 0.0,
        SaplingSpeciesGroup.ASPEN: 0.0,
        SaplingSpeciesGroup.OTHER_BROADLEAF: 0.0,
        SaplingSpeciesGroup.LARCH: 0.0,
    }
    mean_heights = {group: (2.0 if group == SaplingSpeciesGroup.PINE else 0.0) for group in stems}
    naslund = Naslund1986DamageModel.damage_proportions(
        stems=stems,
        mean_heights=mean_heights,
        site_index_pine_m=20.0,
        site_index_spruce_m=22.0,
        latitude_deg=60.0,
        altitude_m=100.0,
    )
    assert naslund[SaplingSpeciesGroup.PINE] == pytest.approx(
        0.28788427351773743, rel=1e-10, abs=1e-12
    )

    species_ba = {group: 0.0 for group in IngrowthSpeciesGroup}
    species_ba[IngrowthSpeciesGroup.SPRUCE] = 15.0
    species_presence = {group: 0 for group in IngrowthSpeciesGroup}
    species_presence[IngrowthSpeciesGroup.SPRUCE] = 1
    wikberg = ingrowth_predict(
        site_index_m=20.0,
        basal_area_m2_ha=20.0,
        qmd_cm=14.0,
        mean_age_excl_overstorey_years=80.0,
        temperature_sum_dd=900.0,
        latitude_deg=60.0,
        altitude_m=100.0,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        soil_texture=Sweden.SoilTextureTill.SANDY,
        soil_water=Sweden.SoilWater.SELDOM_NEVER,
        bottom_layer=Sweden.BottomLayer.FRESH_MOSS,
        field_layer=Sweden.FieldLayer.BILBERRY,
        gotland=0,
        species_ba_m2_ha=species_ba,
        species_presence_10cm=species_presence,
        ingrowth_species=[IngrowthSpeciesGroup.SPRUCE],
        deterministic=True,
    )
    assert wikberg.probability_small_trees[IngrowthSpeciesGroup.SPRUCE] == pytest.approx(
        0.6836998025664799, rel=1e-10, abs=1e-12
    )
    assert wikberg.number_small_trees[IngrowthSpeciesGroup.SPRUCE] == pytest.approx(
        48.39943933329723, rel=1e-10, abs=1e-12
    )
    assert wikberg.number_ingrowth_trees[IngrowthSpeciesGroup.SPRUCE] == pytest.approx(
        33.09068711650364, rel=1e-10, abs=1e-12
    )
    assert wikberg.mean_diameter_cm[IngrowthSpeciesGroup.SPRUCE] == pytest.approx(
        4.651542602257833, rel=1e-10, abs=1e-12
    )

    nystrom_growth = sapling_height_growth_m(
        height_m=3.2,
        age_bh_years=Age.DBH(8),
        mean_height_m=3.8,
        total_height_sqr_m2_per_ha=14500.0,
        total_height_sqr_std_m2_per_ha=2200.0,
        temperature_sum=1100.0,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        field_layer=Sweden.FieldLayer.BILBERRY,
        damage_index=0.2,
        edge_effect=0.0,
        edge_effect_alt=0.0,
        species=TreeSpecies.Sweden.pinus_sylvestris,
        period_years=5.0,
    )
    assert nystrom_growth == pytest.approx(1.916399983223728, rel=1e-10, abs=1e-12)


def test_signature_compat_public_entrypoints() -> None:
    expected = {
        "soderberg_1992_bark_thickness_bh_mm": [
            ("species", "KEYWORD_ONLY", True),
            ("diameter_cm", "KEYWORD_ONLY", True),
            ("max_diameter_cm", "KEYWORD_ONLY", True),
            ("mean_age_total_years", "KEYWORD_ONLY", True),
            ("site_index_pine_m", "KEYWORD_ONLY", True),
            ("latitude_deg", "KEYWORD_ONLY", True),
            ("altitude_m", "KEYWORD_ONLY", True),
            ("prop_pine", "KEYWORD_ONLY", True),
            ("prop_spruce", "KEYWORD_ONLY", True),
            ("prop_birch", "KEYWORD_ONLY", True),
            ("part_of_sweden", "KEYWORD_ONLY", True),
            ("south_east", "KEYWORD_ONLY", False),
            ("region5", "KEYWORD_ONLY", False),
            ("split_plot", "KEYWORD_ONLY", False),
        ],
        "soderberg_1992_height_stand_age_m": [
            ("species", "KEYWORD_ONLY", True),
            ("diameter_cm", "KEYWORD_ONLY", True),
            ("max_diameter_cm", "KEYWORD_ONLY", True),
            ("mean_age_total_years", "KEYWORD_ONLY", True),
            ("site_index_pine_m", "KEYWORD_ONLY", True),
            ("latitude_deg", "KEYWORD_ONLY", True),
            ("altitude_m", "KEYWORD_ONLY", True),
            ("prop_pine", "KEYWORD_ONLY", True),
            ("prop_spruce", "KEYWORD_ONLY", True),
            ("prop_birch", "KEYWORD_ONLY", True),
            ("part_of_sweden", "KEYWORD_ONLY", True),
            ("near_coast", "KEYWORD_ONLY", False),
            ("south_east", "KEYWORD_ONLY", False),
            ("region5", "KEYWORD_ONLY", False),
            ("split_plot", "KEYWORD_ONLY", False),
        ],
        "soderberg_1992_height_tree_age_m": [
            ("species", "KEYWORD_ONLY", True),
            ("diameter_cm", "KEYWORD_ONLY", True),
            ("tree_age_bh_years", "KEYWORD_ONLY", True),
            ("max_diameter_cm", "KEYWORD_ONLY", True),
            ("stand_basal_area_m2_ha", "KEYWORD_ONLY", True),
            ("dominant_species", "KEYWORD_ONLY", True),
            ("site_index_dominant_m", "KEYWORD_ONLY", True),
            ("latitude_deg", "KEYWORD_ONLY", True),
            ("altitude_m", "KEYWORD_ONLY", True),
            ("prop_pine", "KEYWORD_ONLY", True),
            ("prop_spruce", "KEYWORD_ONLY", True),
            ("prop_birch", "KEYWORD_ONLY", True),
            ("prop_beech", "KEYWORD_ONLY", False),
            ("part_of_sweden", "KEYWORD_ONLY", False),
            ("maritime", "KEYWORD_ONLY", False),
            ("continental", "KEYWORD_ONLY", False),
            ("near_coast", "KEYWORD_ONLY", False),
            ("south_east", "KEYWORD_ONLY", False),
            ("region5", "KEYWORD_ONLY", False),
            ("split_plot", "KEYWORD_ONLY", False),
        ],
        "soderberg_1986_form_height_m": [
            ("species", "KEYWORD_ONLY", True),
            ("diameter_cm", "KEYWORD_ONLY", True),
            ("age_bh_years", "KEYWORD_ONLY", True),
            ("max_diameter_cm", "KEYWORD_ONLY", True),
            ("stand_basal_area_m2_ha", "KEYWORD_ONLY", True),
            ("dominant_species", "KEYWORD_ONLY", True),
            ("site_index_dominant_m", "KEYWORD_ONLY", True),
            ("latitude_deg", "KEYWORD_ONLY", True),
            ("altitude_m", "KEYWORD_ONLY", True),
            ("part_of_sweden", "KEYWORD_ONLY", True),
            ("distance_to_coast_lt_50km", "KEYWORD_ONLY", False),
            ("split_plot", "KEYWORD_ONLY", False),
            ("crowberry", "KEYWORD_ONLY", False),
            ("south_slope", "KEYWORD_ONLY", False),
            ("wet_soil", "KEYWORD_ONLY", False),
            ("fertilized", "KEYWORD_ONLY", False),
            ("herbs", "KEYWORD_ONLY", False),
            ("maritime", "KEYWORD_ONLY", False),
            ("region5", "KEYWORD_ONLY", False),
            ("continental", "KEYWORD_ONLY", False),
            ("north_slope", "KEYWORD_ONLY", False),
            ("dry_soil", "KEYWORD_ONLY", False),
            ("south_east", "KEYWORD_ONLY", False),
            ("groundwater_never", "KEYWORD_ONLY", False),
            ("prop_pine", "KEYWORD_ONLY", False),
            ("prop_spruce", "KEYWORD_ONLY", False),
            ("prop_birch", "KEYWORD_ONLY", False),
            ("prop_beech", "KEYWORD_ONLY", False),
            ("prop_oak", "KEYWORD_ONLY", False),
            ("gotland", "KEYWORD_ONLY", False),
        ],
        "soderberg_1986_volume_m3": [("kwargs", "VAR_KEYWORD", True)],
        "NyskogReconstruction.young_stand_quality_asinw": [
            ("stocking_arcsine_radians", "KEYWORD_ONLY", True),
            ("regeneration_type", "KEYWORD_ONLY", True),
            ("latitude_deg", "KEYWORD_ONLY", False),
        ],
        "Elfving2010Model.update_step": [
            ("self", "POSITIONAL_OR_KEYWORD", True),
            ("ctx", "POSITIONAL_OR_KEYWORD", True),
            ("dt", "POSITIONAL_OR_KEYWORD", True),
        ],
        "Soderberg1986Model.update_step": [
            ("self", "POSITIONAL_OR_KEYWORD", True),
            ("ctx", "POSITIONAL_OR_KEYWORD", True),
            ("dt", "POSITIONAL_OR_KEYWORD", True),
        ],
        "Naslund1986DamageModel.damage_proportions": [
            ("stems", "KEYWORD_ONLY", True),
            ("mean_heights", "KEYWORD_ONLY", True),
            ("site_index_pine_m", "KEYWORD_ONLY", True),
            ("site_index_spruce_m", "KEYWORD_ONLY", True),
            ("latitude_deg", "KEYWORD_ONLY", True),
            ("altitude_m", "KEYWORD_ONLY", True),
            ("moose_factor", "KEYWORD_ONLY", False),
            ("vole_factor", "KEYWORD_ONLY", False),
            ("snow_break_factor", "KEYWORD_ONLY", False),
            ("whip_factor", "KEYWORD_ONLY", False),
            ("frost_factor", "KEYWORD_ONLY", False),
            ("snow_blight_factor", "KEYWORD_ONLY", False),
            ("other_factor", "KEYWORD_ONLY", False),
        ],
        "Wikberg2004Ingrowth.predict": [
            ("self", "POSITIONAL_OR_KEYWORD", True),
            ("stand", "KEYWORD_ONLY", False),
            ("site", "KEYWORD_ONLY", False),
            ("site_index_m", "KEYWORD_ONLY", False),
            ("basal_area_m2_ha", "KEYWORD_ONLY", False),
            ("qmd_cm", "KEYWORD_ONLY", False),
            ("mean_age_excl_overstorey_years", "KEYWORD_ONLY", False),
            ("temperature_sum_dd", "KEYWORD_ONLY", False),
            ("latitude_deg", "KEYWORD_ONLY", False),
            ("altitude_m", "KEYWORD_ONLY", False),
            ("soil_moisture", "KEYWORD_ONLY", False),
            ("soil_texture", "KEYWORD_ONLY", False),
            ("soil_water", "KEYWORD_ONLY", False),
            ("bottom_layer", "KEYWORD_ONLY", False),
            ("field_layer", "KEYWORD_ONLY", False),
            ("peat", "KEYWORD_ONLY", False),
            ("gotland", "KEYWORD_ONLY", False),
            ("species_ba_m2_ha", "KEYWORD_ONLY", False),
            ("species_presence_10cm", "KEYWORD_ONLY", False),
            ("sapling_occurrence", "KEYWORD_ONLY", False),
            ("period_index", "KEYWORD_ONLY", False),
            ("ingrowth_species", "KEYWORD_ONLY", False),
            ("thinning_0_5_years", "KEYWORD_ONLY", False),
            ("thinning_6_10_years", "KEYWORD_ONLY", False),
            ("visibility_cleaning", "KEYWORD_ONLY", False),
            ("field", "KEYWORD_ONLY", False),
            ("edge", "KEYWORD_ONLY", False),
            ("road", "KEYWORD_ONLY", False),
            ("plot_is_saplings", "KEYWORD_ONLY", False),
        ],
        "build_common_data": [
            ("basal_area_m2_ha", "KEYWORD_ONLY", True),
            ("mean_age_excl_overstorey_years", "KEYWORD_ONLY", True),
            ("temperature_sum_dd", "KEYWORD_ONLY", True),
            ("altitude_m", "KEYWORD_ONLY", True),
            ("latitude_deg", "KEYWORD_ONLY", True),
            ("soil_moisture", "KEYWORD_ONLY", True),
            ("soil_texture", "KEYWORD_ONLY", True),
            ("soil_water", "KEYWORD_ONLY", True),
            ("bottom_layer", "KEYWORD_ONLY", True),
            ("field_layer", "KEYWORD_ONLY", True),
            ("peat", "KEYWORD_ONLY", True),
            ("site_index_m", "KEYWORD_ONLY", True),
            ("species_ba_m2_ha", "KEYWORD_ONLY", True),
            ("species_presence_10cm", "KEYWORD_ONLY", True),
            ("gotland", "KEYWORD_ONLY", False),
            ("thinning_0_5_years", "KEYWORD_ONLY", False),
            ("thinning_6_10_years", "KEYWORD_ONLY", False),
            ("visibility_cleaning", "KEYWORD_ONLY", False),
            ("field", "KEYWORD_ONLY", False),
            ("edge", "KEYWORD_ONLY", False),
            ("road", "KEYWORD_ONLY", False),
        ],
        "ingrowth_predict": [
            ("stand", "KEYWORD_ONLY", False),
            ("site", "KEYWORD_ONLY", False),
            ("site_index_m", "KEYWORD_ONLY", False),
            ("basal_area_m2_ha", "KEYWORD_ONLY", False),
            ("qmd_cm", "KEYWORD_ONLY", False),
            ("mean_age_excl_overstorey_years", "KEYWORD_ONLY", False),
            ("temperature_sum_dd", "KEYWORD_ONLY", False),
            ("latitude_deg", "KEYWORD_ONLY", False),
            ("altitude_m", "KEYWORD_ONLY", False),
            ("soil_moisture", "KEYWORD_ONLY", False),
            ("soil_texture", "KEYWORD_ONLY", False),
            ("soil_water", "KEYWORD_ONLY", False),
            ("bottom_layer", "KEYWORD_ONLY", False),
            ("field_layer", "KEYWORD_ONLY", False),
            ("peat", "KEYWORD_ONLY", False),
            ("gotland", "KEYWORD_ONLY", False),
            ("species_ba_m2_ha", "KEYWORD_ONLY", False),
            ("species_presence_10cm", "KEYWORD_ONLY", False),
            ("sapling_occurrence", "KEYWORD_ONLY", False),
            ("deterministic", "KEYWORD_ONLY", False),
            ("rng", "KEYWORD_ONLY", False),
            ("use_initial_saplings", "KEYWORD_ONLY", False),
            ("period_index", "KEYWORD_ONLY", False),
            ("min_mean_age_invoke", "KEYWORD_ONLY", False),
            ("ingrowth_species", "KEYWORD_ONLY", False),
            ("thinning_0_5_years", "KEYWORD_ONLY", False),
            ("thinning_6_10_years", "KEYWORD_ONLY", False),
            ("visibility_cleaning", "KEYWORD_ONLY", False),
            ("field", "KEYWORD_ONLY", False),
            ("edge", "KEYWORD_ONLY", False),
            ("road", "KEYWORD_ONLY", False),
            ("plot_is_saplings", "KEYWORD_ONLY", False),
        ],
        "ingrowth_to_plot_trees": [
            ("result", "POSITIONAL_OR_KEYWORD", True),
            ("plot_area_ha", "POSITIONAL_OR_KEYWORD", True),
        ],
        "sapling_height_growth_m": [
            ("height_m", "KEYWORD_ONLY", True),
            ("age_bh_years", "KEYWORD_ONLY", True),
            ("mean_height_m", "KEYWORD_ONLY", True),
            ("total_height_sqr_m2_per_ha", "KEYWORD_ONLY", True),
            ("total_height_sqr_std_m2_per_ha", "KEYWORD_ONLY", True),
            ("temperature_sum", "KEYWORD_ONLY", True),
            ("soil_moisture", "KEYWORD_ONLY", True),
            ("field_layer", "KEYWORD_ONLY", True),
            ("damage_index", "KEYWORD_ONLY", False),
            ("edge_effect", "KEYWORD_ONLY", False),
            ("edge_effect_alt", "KEYWORD_ONLY", False),
            ("species", "KEYWORD_ONLY", True),
            ("period_years", "KEYWORD_ONLY", False),
        ],
    }

    observed = {
        "soderberg_1992_bark_thickness_bh_mm": _signature_schema(
            soderberg_1992_bark_thickness_bh_mm
        ),
        "soderberg_1992_height_stand_age_m": _signature_schema(soderberg_1992_height_stand_age_m),
        "soderberg_1992_height_tree_age_m": _signature_schema(soderberg_1992_height_tree_age_m),
        "soderberg_1986_form_height_m": _signature_schema(soderberg_1986_form_height_m),
        "soderberg_1986_volume_m3": _signature_schema(soderberg_1986_volume_m3),
        "NyskogReconstruction.young_stand_quality_asinw": _signature_schema(
            NyskogReconstruction.young_stand_quality_asinw
        ),
        "Elfving2010Model.update_step": _signature_schema(Elfving2010Model.update_step),
        "Soderberg1986Model.update_step": _signature_schema(Soderberg1986Model.update_step),
        "Naslund1986DamageModel.damage_proportions": _signature_schema(
            Naslund1986DamageModel.damage_proportions
        ),
        "Wikberg2004Ingrowth.predict": _signature_schema(Wikberg2004Ingrowth.predict),
        "build_common_data": _signature_schema(build_common_data),
        "ingrowth_predict": _signature_schema(ingrowth_predict),
        "ingrowth_to_plot_trees": _signature_schema(ingrowth_to_plot_trees),
        "sapling_height_growth_m": _signature_schema(sapling_height_growth_m),
    }

    assert observed == expected
