from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from pyforestry.base.helpers import Tree, TreeSpecies
from pyforestry.base.helpers.primitives import Age, SiteIndexValue
from pyforestry.sweden.blocks.elfving_2010 import (
    pine_ln_d2_growth as model_pine_ln_d2_growth,
)
from pyforestry.sweden.blocks.elfving_2010 import (
    stand_basal_area_growth_elfving_2009 as model_stand_basal_area_growth_elfving_2009,
)
from pyforestry.sweden.growth.elfving_2010.features import (
    collect_trees,
    distance_to_coast_km,
    fertilization_flag,
    field_estimated_basal_area_m2_ha,
    plot_expansion_factor,
    resolve_latitude_altitude,
    resolve_site_index_m,
    resolve_temperature_sum,
    species_group,
    split_edge_flags,
    thinning_flags,
    tree_age_bh_years,
    tree_age_total_years,
    vegetation_flags,
)
from pyforestry.sweden.growth.elfving_2010.kernels import (
    pine_ln_d2_growth as formula_pine_ln_d2_growth,
)
from pyforestry.sweden.growth.elfving_2010.kernels import (
    stand_basal_area_growth_elfving_2009 as formula_stand_basal_area_growth_elfving_2009,
)
from pyforestry.sweden.site.enums import Sweden
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970


@dataclass
class _Ctx:
    attrs: dict
    mode: str = "tree_list"
    plots: list | None = None

    def __post_init__(self) -> None:
        if self.plots is None:
            self.plots = []


def test_species_group_mapping_uses_extracted_feature_transform() -> None:
    assert species_group(TreeSpecies.Sweden.pinus_sylvestris) == "pine"
    assert species_group(TreeSpecies.Sweden.picea_abies) == "spruce"
    assert species_group(TreeSpecies.Sweden.betula_pubescens) == "birch"
    assert species_group(None) == "trivial"


def test_plot_expansion_factor_validation_in_features_kernel() -> None:
    assert plot_expansion_factor(0.02, 0.1) == pytest.approx(55.55555555555556)
    with pytest.raises(ValueError):
        plot_expansion_factor(0.02, 1.0)


def test_pine_wrapper_matches_extracted_formula_kernel() -> None:
    kwargs = {
        "diameter_cm": 22.0,
        "bal_over_dbh": 1.2,
        "age_bh_years": 45.0,
        "overstorey": 1,
        "mean_dgv_cm": 27.5,
        "basal_area_m2_ha": 30.0,
        "basal_area_pines_m2_ha": 18.0,
        "gotland": 0,
        "temperature_sum_dd": 1100.0,
        "site_index_m": 24.0,
        "rich": 1,
        "fertilized": 0,
        "thinned_0_10_years_flag": 1,
        "thinned_11_25_years_flag": 0,
        "split": 0,
        "edge": 1,
        "field_ba_m2_ha": 28.0,
    }
    assert model_pine_ln_d2_growth(**kwargs) == pytest.approx(formula_pine_ln_d2_growth(**kwargs))


def test_stand_growth_wrapper_matches_extracted_formula_kernel() -> None:
    kwargs = {
        "ln_mean_age": 4.0,
        "conifer_share_per_age": 0.02,
        "pine_share_times_veg": 1.5,
        "birch_share_sq": 0.01,
        "birch_share_cold": 0.005,
        "basal_area_survived_m2_ha": 20.0,
        "basal_area_all_m2_ha": 21.0,
        "stem_number_factor": 0.8,
        "veg": 2.0,
        "peat": 0,
        "moist": 1,
        "wet": 0,
        "site_index_m": 20.0,
        "ditch": 0,
        "fertilized": 0,
        "edge": 1,
        "split": 0,
        "thinned_0_10_years_flag": 1,
        "thinned_10_30_years_flag": 0,
        "ln_relative_basal_area": 0.0,
        "pine_share": 0.3,
        "spruce_share": 0.5,
        "use_edge_effects": True,
    }
    assert model_stand_basal_area_growth_elfving_2009(**kwargs) == pytest.approx(
        formula_stand_basal_area_growth_elfving_2009(**kwargs)
    )


def test_species_group_covers_remaining_species_groups() -> None:
    assert species_group(TreeSpecies.Sweden.populus_tremula) == "aspen"
    assert species_group(TreeSpecies.Sweden.fagus_sylvatica) == "beech"
    assert species_group(TreeSpecies.Sweden.quercus_robur) == "oak"
    assert species_group(TreeSpecies.Sweden.tilia_cordata) == "precious"


def test_vegetation_flags_and_distance_to_coast_resolution() -> None:
    assert vegetation_flags(None) == (0, 0)
    assert vegetation_flags(Sweden.FieldLayer.BILBERRY) == (0, 0)
    assert vegetation_flags(Sweden.FieldLayer.HIGH_HERB_WITHOUT_SHRUBS) == (1, 1)

    ctx = _Ctx(attrs={"distance_to_coast_km": 12.5})
    assert distance_to_coast_km(None, ctx) == pytest.approx(12.5)
    assert distance_to_coast_km(SimpleNamespace(distance_to_coast=2.0), ctx) == pytest.approx(2.0)
    assert distance_to_coast_km(None, _Ctx(attrs={})) == pytest.approx(50.0)


def test_temperature_and_latitude_altitude_resolution_paths() -> None:
    site = SimpleNamespace(temperature_sum_odin1983=1100.0, latitude=62.0, altitude=140.0)
    assert resolve_temperature_sum(site, _Ctx(attrs={})) == pytest.approx(1100.0)
    assert resolve_temperature_sum(None, _Ctx(attrs={"temperature_sum": 980.0})) == pytest.approx(
        980.0
    )
    assert resolve_latitude_altitude(site, _Ctx(attrs={})) == (62.0, 140.0)
    assert resolve_latitude_altitude(
        None, _Ctx(attrs={"latitude_deg": 60.0, "altitude_m": 100.0})
    ) == (
        60.0,
        100.0,
    )

    with pytest.raises(ValueError, match="Temperature sum is required"):
        resolve_temperature_sum(None, _Ctx(attrs={}))
    with pytest.raises(ValueError, match="latitude_deg and altitude_m are required"):
        resolve_latitude_altitude(None, _Ctx(attrs={}))


def test_resolve_site_index_m_paths_and_type_errors() -> None:
    site = SimpleNamespace(sis_spruce_100=24.0, sis_pine_100=22.0)
    assert resolve_site_index_m(
        site=None, ctx=_Ctx(attrs={"site_index_m": 23.5})
    ) == pytest.approx(23.5)

    wrapped = SimpleNamespace(
        value=SiteIndexValue(
            20.0,
            reference_age=Age.TOTAL(100),
            species={TreeSpecies.Sweden.pinus_sylvestris},
            fn=Hagglund_1970.height_trajectory.pinus_sylvestris.sweden,
        )
    )
    assert resolve_site_index_m(
        site=None, ctx=_Ctx(attrs={"site_index_value": wrapped})
    ) == pytest.approx(20.0)

    assert resolve_site_index_m(
        site=site,
        ctx=_Ctx(attrs={"dominant_species": TreeSpecies.Sweden.picea_abies}),
    ) == pytest.approx(24.0)
    assert resolve_site_index_m(
        site=site, ctx=_Ctx(attrs={}), pine_ba=10.0, spruce_ba=5.0
    ) == pytest.approx(22.0)

    with pytest.raises(ValueError, match="Site index is required"):
        resolve_site_index_m(site=None, ctx=_Ctx(attrs={}))
    with pytest.raises(TypeError, match="site_index_value.value must be numeric"):
        resolve_site_index_m(
            site=None, ctx=_Ctx(attrs={"site_index_value": SimpleNamespace(value="bad")})
        )
    with pytest.raises(ValueError, match="Unable to resolve site index"):
        resolve_site_index_m(
            site=SimpleNamespace(sis_spruce_100=None, sis_pine_100=None),
            ctx=_Ctx(attrs={}),
        )


def test_misc_flags_collect_trees_and_age_helpers() -> None:
    ctx = _Ctx(
        attrs={
            "fertilized_within_10_years": False,
            "fertilized_remaining_years": 2.0,
            "thinning_simulated": False,
            "thinned_0_10_years": True,
            "thinned_11_25_years": True,
            "split": True,
            "edge": False,
            "field_estimated_basal_area_m2_ha": 33.0,
        },
        mode="tree_list",
        plots=[
            SimpleNamespace(
                trees=[Tree(species=TreeSpecies.Sweden.pinus_sylvestris, diameter_cm=20.0)]
            )
        ],
    )
    assert fertilization_flag(ctx) == 1
    assert thinning_flags(ctx, include_thinning_effect=False) == (1, 1)
    ctx.attrs["thinning_simulated"] = True
    assert thinning_flags(ctx, include_thinning_effect=True) == (0, 0)
    assert split_edge_flags(ctx) == (1, 0)
    assert field_estimated_basal_area_m2_ha(ctx) == pytest.approx(33.0)
    assert len(collect_trees(ctx)) == 1
    assert collect_trees(_Ctx(attrs={}, mode="aggregate", plots=ctx.plots)) == []

    tree_dbh = Tree(species=TreeSpecies.Sweden.pinus_sylvestris, age=Age.DBH(30), diameter_cm=20.0)
    tree_total = Tree(
        species=TreeSpecies.Sweden.pinus_sylvestris, age=Age.TOTAL(35), diameter_cm=20.0
    )
    assert tree_age_bh_years(
        tree=tree_dbh,
        site_index_m=22.0,
        latitude_deg=60.0,
        default_species=TreeSpecies.Sweden.pinus_sylvestris,
    ) == pytest.approx(30.0)
    assert tree_age_total_years(
        tree=tree_total,
        site_index_m=22.0,
        latitude_deg=60.0,
        default_species=TreeSpecies.Sweden.pinus_sylvestris,
    ) == pytest.approx(35.0)
    assert (
        tree_age_bh_years(
            tree=tree_total,
            site_index_m=22.0,
            latitude_deg=60.0,
            default_species=TreeSpecies.Sweden.pinus_sylvestris,
        )
        >= 1.0
    )
    assert (
        tree_age_total_years(
            tree=tree_dbh,
            site_index_m=22.0,
            latitude_deg=60.0,
            default_species=TreeSpecies.Sweden.pinus_sylvestris,
        )
        >= 30.0
    )

    missing_age_tree = Tree(
        species=TreeSpecies.Sweden.pinus_sylvestris, age=None, diameter_cm=20.0
    )
    with pytest.warns(UserWarning, match="Tree age missing"):
        assert tree_age_bh_years(
            tree=missing_age_tree,
            site_index_m=22.0,
            latitude_deg=60.0,
            default_species=TreeSpecies.Sweden.pinus_sylvestris,
        ) == pytest.approx(10.0)
    with pytest.warns(UserWarning, match="Tree age missing"):
        assert tree_age_total_years(
            tree=missing_age_tree,
            site_index_m=22.0,
            latitude_deg=60.0,
            default_species=TreeSpecies.Sweden.pinus_sylvestris,
        ) == pytest.approx(10.0)
