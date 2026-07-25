import math

import pytest

import pyforestry.sweden.blocks.soderberg_1986_growth as growth_module
from pyforestry.base.helpers import CircularPlot, Stand, Tree
from pyforestry.base.helpers.primitives import (
    Age,
    SiteBase,
    SiteIndexValue,
    diameter_growth_to_basal_area_growth_cm2,
    diameter_to_basal_area_cm2,
)
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.base.simulation import SimulationContext
from pyforestry.sweden.blocks.soderberg_1986_growth import (
    Soderberg1986Config,
    Soderberg1986Model,
    soderberg_1986_tree_diameter_growth_cm,
)
from pyforestry.sweden.site.enums import Sweden
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970


class _DummySite(SiteBase):
    def compute_attributes(self) -> None:  # pragma: no cover - simple stub
        return None


def _base_attrs(part_of_sweden: str = "north") -> dict[str, object]:
    return {
        "part_of_sweden": part_of_sweden,
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


def _run_single_tree(
    *,
    species,
    part_of_sweden: str = "north",
    age: object | None = None,
    diameter_cm: float = 20.0,
    dt: float = 5.0,
    mode: str = "tree_list",
    weight_n: float = 1.0,
    area_m2: float = 200.0,
    attrs_override: dict[str, object] | None = None,
    attrs_remove: set[str] | None = None,
    model: Soderberg1986Model | None = None,
):
    site = _DummySite(latitude=60.0, longitude=15.0)
    tree_kwargs = {}
    if mode == "spatial":
        tree_kwargs["position"] = (0.0, 0.0)
    tree = Tree(
        species=species,
        diameter_cm=diameter_cm,
        age=age if age is not None else Age.DBH(40.0),
        weight_n=weight_n,
        **tree_kwargs,
    )
    plot = CircularPlot(id=1, area_m2=area_m2, trees=[tree])
    stand = Stand(site=site, plots=[plot])

    growth_model = model or Soderberg1986Model()
    ctx = growth_model.build_context(stand, mode_hint=mode)
    attrs = _base_attrs(part_of_sweden)
    if attrs_override:
        attrs.update(attrs_override)
    if attrs_remove:
        for key in attrs_remove:
            attrs.pop(key, None)
    ctx.attrs.update(attrs)

    d0 = float(ctx.plots[0].trees[0].diameter_cm)
    growth_model.update_step(ctx, dt)
    d1 = float(ctx.plots[0].trees[0].diameter_cm)
    return (d1 - d0), ctx


@pytest.mark.parametrize(
    "case_name,species,part_of_sweden,attrs_override,expected_increment_cm",
    [
        (
            "pine_north",
            TreeSpecies.Sweden.pinus_sylvestris,
            "north",
            {"site_index_species": "pine"},
            2.168181754573478,
        ),
        (
            "spruce_middle",
            TreeSpecies.Sweden.picea_abies,
            "middle",
            {"site_index_species": "spruce"},
            2.257301811202236,
        ),
        (
            "birch_south",
            TreeSpecies.Sweden.betula_pendula,
            "south",
            {"site_index_species": "spruce"},
            2.1239928777484423,
        ),
        (
            "aspen_north",
            TreeSpecies.Sweden.populus_tremula,
            "north",
            {"site_index_species": "spruce"},
            2.4922178697629,
        ),
        (
            "beech_south",
            TreeSpecies.Sweden.fagus_sylvatica,
            "south",
            {"site_index_species": "spruce"},
            4.270644218131228,
        ),
        (
            "oak_middle",
            TreeSpecies.Sweden.quercus_robur,
            "middle",
            {"site_index_species": "spruce"},
            3.3549529257625252,
        ),
        (
            "other_decid_south",
            TreeSpecies.Sweden.alnus_glutinosa,
            "south",
            {"site_index_species": "spruce"},
            3.4253805473969052,
        ),
    ],
)
def test_soderberg_golden_parity_snapshots(
    case_name: str,
    species,
    part_of_sweden: str,
    attrs_override: dict[str, object],
    expected_increment_cm: float,
) -> None:
    increment_cm, _ctx = _run_single_tree(
        species=species,
        part_of_sweden=part_of_sweden,
        attrs_override=attrs_override,
    )
    assert increment_cm == pytest.approx(expected_increment_cm, rel=1e-10, abs=1e-12), case_name


def test_soderberg_age_group_boundaries() -> None:
    pine_below, _ = _run_single_tree(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        age=Age.DBH(54.9),
    )
    pine_above, _ = _run_single_tree(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        age=Age.DBH(55.0),
    )
    birch_below, _ = _run_single_tree(
        species=TreeSpecies.Sweden.betula_pendula,
        age=Age.DBH(44.9),
        attrs_override={"site_index_species": "spruce"},
    )
    birch_above, _ = _run_single_tree(
        species=TreeSpecies.Sweden.betula_pendula,
        age=Age.DBH(45.0),
        attrs_override={"site_index_species": "spruce"},
    )

    assert not math.isclose(pine_below, pine_above, rel_tol=1e-9, abs_tol=1e-12)
    assert not math.isclose(birch_below, birch_above, rel_tol=1e-9, abs_tol=1e-12)


def test_soderberg_thinning_states_and_include_thinning_effect_behavior() -> None:
    config_default = Soderberg1986Config(include_thinning_effect=True)
    model_default = Soderberg1986Model(config_default)

    inc_0, ctx_0 = _run_single_tree(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        model=model_default,
    )
    inc_1, ctx_1 = _run_single_tree(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        attrs_override={"thinned_0_5_years": True},
        model=model_default,
    )
    inc_2, ctx_2 = _run_single_tree(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        attrs_override={"thinned_6_25_years": True},
        model=model_default,
    )

    assert ctx_0.state["soderberg1986_thinning_state"] == 0
    assert ctx_1.state["soderberg1986_thinning_state"] == 1
    assert ctx_2.state["soderberg1986_thinning_state"] == 2
    assert not math.isclose(inc_0, inc_1, rel_tol=1e-9, abs_tol=1e-12)
    assert not math.isclose(inc_0, inc_2, rel_tol=1e-9, abs_tol=1e-12)

    inc_simulated, ctx_simulated = _run_single_tree(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        attrs_override={"thinned_0_5_years": True, "thinning_simulated": True},
        model=model_default,
    )
    assert ctx_simulated.state["soderberg1986_thinning_state"] == 0
    assert math.isclose(inc_0, inc_simulated, rel_tol=1e-9, abs_tol=1e-12)

    model_ignore = Soderberg1986Model(Soderberg1986Config(include_thinning_effect=False))
    _inc_ignore, ctx_ignore = _run_single_tree(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        attrs_override={"thinned_0_5_years": True, "thinning_simulated": True},
        model=model_ignore,
    )
    assert ctx_ignore.state["soderberg1986_thinning_state"] == 1


@pytest.mark.parametrize(
    "species,site_index_species,site_index_key",
    [
        (TreeSpecies.Sweden.pinus_sylvestris, "pine", "site_index_pine_m"),
        (TreeSpecies.Sweden.picea_abies, "spruce", "site_index_spruce_m"),
    ],
)
def test_soderberg_conifer_peat_site_index_zeroing(
    species,
    site_index_species: str,
    site_index_key: str,
) -> None:
    attrs_high = {
        "site_index_species": site_index_species,
        site_index_key: 35.0,
        "peat": True,
    }
    attrs_zero = {
        "site_index_species": site_index_species,
        site_index_key: 0.0,
        "peat": True,
    }

    inc_high, _ = _run_single_tree(species=species, attrs_override=attrs_high)
    inc_zero, _ = _run_single_tree(species=species, attrs_override=attrs_zero)
    assert inc_high == pytest.approx(inc_zero, rel=1e-12, abs=1e-12)


def test_soderberg_accepts_site_index_value_input() -> None:
    pine_site_index = SiteIndexValue(
        20.0,
        reference_age=Age.TOTAL(100.0),
        species={TreeSpecies.Sweden.pinus_sylvestris},
        fn=Hagglund_1970.height_trajectory.pinus_sylvestris.sweden,
    )
    increment_cm, _ = _run_single_tree(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        attrs_override={
            "site_index_species": "pine",
            "site_index_pine_m": pine_site_index,
            "site_index_spruce_m": 22.0,
        },
    )
    assert increment_cm > 0.0


def test_soderberg_rejects_site_index_species_mismatch() -> None:
    spruce_site_index = SiteIndexValue(
        22.0,
        reference_age=Age.TOTAL(100.0),
        species={TreeSpecies.Sweden.picea_abies},
        fn=Hagglund_1970.height_trajectory.picea_abies.northern_sweden,
    )
    with pytest.raises(ValueError, match="site_index_pine_m\\.species"):
        _run_single_tree(
            species=TreeSpecies.Sweden.pinus_sylvestris,
            attrs_override={
                "site_index_species": "pine",
                "site_index_pine_m": spruce_site_index,
                "site_index_spruce_m": 22.0,
            },
        )


def test_soderberg_contorta_site_index_offset() -> None:
    attrs = {"site_index_species": "pine", "site_index_pine_m": 20.0}
    inc_pine, _ = _run_single_tree(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        attrs_override=attrs,
    )
    inc_contorta, _ = _run_single_tree(
        species=TreeSpecies.Sweden.pinus_contorta,
        attrs_override=attrs,
    )
    assert inc_contorta > inc_pine


def _run_beech_ba_growth_with_target_stand_ba(target_stand_ba_m2_ha: float) -> float:
    diameter_cm = 30.0
    area_m2 = 100.0
    exp_factor = 1.0 / ((area_m2 / 10_000.0) * (1.0 - 0.0))
    ba_per_weight = diameter_to_basal_area_cm2(diameter_cm) * 1.0e-4 * exp_factor
    weight_n = target_stand_ba_m2_ha / ba_per_weight

    increment_cm, _ = _run_single_tree(
        species=TreeSpecies.Sweden.fagus_sylvatica,
        diameter_cm=diameter_cm,
        area_m2=area_m2,
        weight_n=weight_n,
        part_of_sweden="south",
        attrs_override={"site_index_species": "spruce", "site_index_spruce_m": 22.0},
    )
    return diameter_growth_to_basal_area_growth_cm2(diameter_cm, increment_cm)


def test_soderberg_beech_high_ba_adjustment() -> None:
    ba_growth_40 = _run_beech_ba_growth_with_target_stand_ba(40.0)
    ba_growth_60 = _run_beech_ba_growth_with_target_stand_ba(60.0)

    observed_ratio = ba_growth_60 / ba_growth_40
    expected_ratio = math.sqrt(20.0 / 60.0) / math.sqrt(20.0 / 40.0)
    assert observed_ratio == pytest.approx(expected_ratio, rel=1e-10, abs=1e-12)


def test_soderberg_aspen_age_cutoff() -> None:
    increment_young, _ = _run_single_tree(
        species=TreeSpecies.Sweden.populus_tremula,
        age=Age.DBH(119.0),
        attrs_override={"site_index_species": "spruce"},
    )
    increment_old, _ = _run_single_tree(
        species=TreeSpecies.Sweden.populus_tremula,
        age=Age.DBH(120.0),
        attrs_override={"site_index_species": "spruce"},
    )
    assert increment_young > 0.0
    assert increment_old == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("mode", ["tree_list", "spatial"])
def test_soderberg_model_updates_tree_list_and_spatial(mode: str) -> None:
    increment, _ctx = _run_single_tree(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        mode=mode,
    )
    assert increment > 0.0


def test_soderberg_model_dt_scaling_and_warning() -> None:
    inc_5, _ = _run_single_tree(species=TreeSpecies.Sweden.pinus_sylvestris, dt=5.0)
    with pytest.warns(UserWarning, match="scaled linearly from a 5-year period"):
        inc_10, _ = _run_single_tree(species=TreeSpecies.Sweden.pinus_sylvestris, dt=10.0)
    assert inc_10 == pytest.approx(inc_5 * 2.0, rel=1e-6)


def test_soderberg_model_rejects_unsupported_modes() -> None:
    site = _DummySite(latitude=60.0, longitude=15.0)
    plot = CircularPlot(
        id=1,
        area_m2=200.0,
        trees=[
            Tree(species=TreeSpecies.Sweden.pinus_sylvestris, diameter_cm=20.0, age=Age.DBH(40)),
            Tree(species=TreeSpecies.Sweden.picea_abies, diameter_cm=24.0, age=Age.DBH(40)),
        ],
    )
    stand = Stand(site=site, plots=[plot])
    model = Soderberg1986Model()

    ctx_aggregate = model.build_context(stand, mode_hint="aggregate")
    ctx_aggregate.attrs.update(_base_attrs())
    with pytest.raises(ValueError, match="supports only tree_list and spatial"):
        model.update_step(ctx_aggregate, 5.0)

    ctx_diam = SimulationContext(
        mode="diameter_class",
        area_ha=stand.area_ha,
        site=stand.site,
        origin_ref=stand,
        inventory={"dclass": {"TOTAL": {"bin_mids_cm": [20.0], "n_per_ha": [500.0]}}},
        initial_state=model.init_state_stub(),
        model=model,
        initial_attrs=model.default_attrs(),
    )
    ctx_diam.attrs.update(_base_attrs())
    with pytest.raises(ValueError, match="supports only tree_list and spatial"):
        model.update_step(ctx_diam, 5.0)


def _species_shares_for_single_tree(species) -> tuple[float, float, float]:
    group = growth_module._species_group(species)
    if group in {
        growth_module._SpeciesGroup.PINE,
        growth_module._SpeciesGroup.CONTORTA,
        growth_module._SpeciesGroup.LARCH,
    }:
        return 1.0, 0.0, 0.0
    if group == growth_module._SpeciesGroup.SPRUCE:
        return 0.0, 1.0, 0.0
    if group == growth_module._SpeciesGroup.BIRCH:
        return 0.0, 0.0, 1.0
    return 0.0, 0.0, 0.0


def _direct_increment_for_single_tree(
    *,
    species,
    part_of_sweden: str,
    age_bh_years: float,
    diameter_cm: float,
    site_index_species: str,
    thinned_0_5_years: bool,
    thinned_6_25_years: bool,
) -> float:
    exp_factor = 1.0 / ((200.0 / 10_000.0) * (1.0 - 0.0))
    stand_basal_area_m2_ha = diameter_to_basal_area_cm2(diameter_cm) * 1.0e-4 * exp_factor
    p_pine, p_spruce, p_birch = _species_shares_for_single_tree(species)
    return soderberg_1986_tree_diameter_growth_cm(
        species=species,
        diameter_cm=diameter_cm,
        age_bh_years=age_bh_years,
        part_of_sweden=part_of_sweden,
        stand_basal_area_m2_ha=stand_basal_area_m2_ha,
        tree_diameter_max_cm=diameter_cm,
        p_pine=p_pine,
        p_spruce=p_spruce,
        p_birch=p_birch,
        site_index_species=site_index_species,
        site_index_pine_m=20.0,
        site_index_spruce_m=22.0,
        latitude_deg=60.0,
        altitude_m=100.0,
        maritime=False,
        south_east=False,
        region5=False,
        rich=False,
        split=False,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        peat=False,
        fertilized_within_10_years=False,
        thinned_0_5_years=thinned_0_5_years,
        thinned_6_25_years=thinned_6_25_years,
        thinning_simulated=False,
        include_thinning_effect=True,
    )


def test_soderberg_public_function_matches_adapter_parity_matrix() -> None:
    species_cases = [
        (TreeSpecies.Sweden.pinus_sylvestris, "pine"),
        (TreeSpecies.Sweden.pinus_contorta, "pine"),
        (TreeSpecies.Sweden.larix_decidua, "pine"),
        (TreeSpecies.Sweden.picea_abies, "spruce"),
        (TreeSpecies.Sweden.betula_pendula, "spruce"),
        (TreeSpecies.Sweden.populus_tremula, "spruce"),
        (TreeSpecies.Sweden.quercus_robur, "spruce"),
        (TreeSpecies.Sweden.fagus_sylvatica, "spruce"),
        (TreeSpecies.Sweden.fraxinus_excelsior, "spruce"),
        (TreeSpecies.Sweden.alnus_glutinosa, "spruce"),
    ]
    parts = ("north", "middle", "south")
    ages = (35.0, 65.0)
    thinning_cases = (
        (False, False),
        (True, False),
        (False, True),
    )

    for species, site_index_species in species_cases:
        for part_of_sweden in parts:
            for age_bh_years in ages:
                for thinned_0_5_years, thinned_6_25_years in thinning_cases:
                    attrs_override = {
                        "site_index_species": site_index_species,
                        "thinned_0_5_years": thinned_0_5_years,
                        "thinned_6_25_years": thinned_6_25_years,
                    }
                    adapter_increment, _ = _run_single_tree(
                        species=species,
                        part_of_sweden=part_of_sweden,
                        age=Age.DBH(age_bh_years),
                        attrs_override=attrs_override,
                    )
                    direct_increment = _direct_increment_for_single_tree(
                        species=species,
                        part_of_sweden=part_of_sweden,
                        age_bh_years=age_bh_years,
                        diameter_cm=20.0,
                        site_index_species=site_index_species,
                        thinned_0_5_years=thinned_0_5_years,
                        thinned_6_25_years=thinned_6_25_years,
                    )
                    assert adapter_increment == pytest.approx(
                        direct_increment,
                        rel=1e-10,
                        abs=1e-12,
                    )


@pytest.mark.parametrize(
    "legacy_key,legacy_value",
    [
        ("county_code", 7),
        ("region_code_2009", "reg3"),
        ("region", "reg3"),
        ("climate_zone", "M2"),
        ("climate", "M2"),
        ("is_rich", 1),
        ("is_split_plot", 1),
        ("thinned_0_10_years", True),
        ("thinned_6_10_years", True),
        ("thinned_11_25_years", True),
        ("thinned_11_30_years", True),
        ("sis_pine_100", 20.0),
        ("sis_spruce_100", 22.0),
        ("site_index", 20.0),
        ("site_index_value", 20.0),
        ("site_index_m", 20.0),
        ("fertilized_remaining_years", 5.0),
        ("years_since_fertilization", 2.0),
    ],
)
def test_soderberg_rejects_legacy_alias_keys(legacy_key: str, legacy_value: object) -> None:
    with pytest.raises(ValueError, match="legacy attr keys"):
        _run_single_tree(
            species=TreeSpecies.Sweden.pinus_sylvestris,
            attrs_override={legacy_key: legacy_value},
        )


@pytest.mark.parametrize(
    "missing_key",
    [
        "part_of_sweden",
        "latitude_deg",
        "altitude_m",
        "site_index_species",
        "maritime",
        "south_east",
        "region5",
        "rich",
        "split",
        "soil_moisture",
        "peat",
    ],
)
def test_soderberg_requires_canonical_attr_keys(missing_key: str) -> None:
    with pytest.raises(ValueError, match="requires canonical attrs"):
        _run_single_tree(
            species=TreeSpecies.Sweden.pinus_sylvestris,
            attrs_remove={missing_key},
        )


def test_soderberg_requires_species_specific_site_index() -> None:
    with pytest.raises(ValueError, match="site_index_pine_m"):
        _run_single_tree(
            species=TreeSpecies.Sweden.pinus_sylvestris,
            attrs_override={"site_index_species": "pine"},
            attrs_remove={"site_index_pine_m"},
        )
    with pytest.raises(ValueError, match="site_index_spruce_m"):
        _run_single_tree(
            species=TreeSpecies.Sweden.picea_abies,
            attrs_override={"site_index_species": "spruce"},
            attrs_remove={"site_index_spruce_m"},
        )


def test_soderberg_rejects_invalid_site_index_species() -> None:
    with pytest.raises(ValueError, match="site_index_species must be either"):
        _run_single_tree(
            species=TreeSpecies.Sweden.pinus_sylvestris,
            attrs_override={"site_index_species": "birch"},
        )


def test_soderberg_total_age_and_missing_age_paths() -> None:
    tree_total = Tree(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        diameter_cm=20.0,
        age=Age.TOTAL(60.0),
    )
    age_bh = growth_module._tree_age_bh_years(tree_total, site_index_m=20.0, latitude_deg=60.0)
    assert 0.0 < age_bh < 60.0

    tree_missing = Tree(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        diameter_cm=20.0,
        age=None,
    )
    with pytest.warns(UserWarning, match="Tree age missing"):
        age_fallback = growth_module._tree_age_bh_years(
            tree_missing,
            site_index_m=20.0,
            latitude_deg=60.0,
        )
    assert age_fallback == pytest.approx(10.0)


def test_soderberg_unknown_species_no_growth() -> None:
    site = _DummySite(latitude=60.0, longitude=15.0)
    stand = Stand(
        site=site,
        plots=[
            CircularPlot(
                id=1,
                area_m2=200.0,
                trees=[Tree(species=None, diameter_cm=20.0, age=40.0)],
            )
        ],
    )
    model = Soderberg1986Model()
    ctx = model.build_context(stand, mode_hint="tree_list")
    ctx.attrs.update(_base_attrs())
    before = float(ctx.plots[0].trees[0].diameter_cm)
    model.update_step(ctx, 5.0)
    after = float(ctx.plots[0].trees[0].diameter_cm)
    assert after == pytest.approx(before, abs=1e-12)


def test_soderberg_public_function_argument_guards() -> None:
    with pytest.raises(ValueError, match="age_bh_years"):
        soderberg_1986_tree_diameter_growth_cm(
            species=TreeSpecies.Sweden.pinus_sylvestris,
            diameter_cm=20.0,
            age_bh_years=-1.0,
            part_of_sweden="north",
            stand_basal_area_m2_ha=10.0,
            tree_diameter_max_cm=30.0,
            p_pine=1.0,
            p_spruce=0.0,
            p_birch=0.0,
            site_index_species="pine",
            site_index_pine_m=20.0,
            site_index_spruce_m=22.0,
            latitude_deg=60.0,
            altitude_m=100.0,
            maritime=False,
            south_east=False,
            region5=False,
            rich=False,
            split=False,
            soil_moisture=Sweden.SoilMoistureEnum.MESIC,
            peat=False,
        )

    with pytest.raises(ValueError, match="part_of_sweden"):
        soderberg_1986_tree_diameter_growth_cm(
            species=TreeSpecies.Sweden.pinus_sylvestris,
            diameter_cm=20.0,
            age_bh_years=40.0,
            part_of_sweden="central",
            stand_basal_area_m2_ha=10.0,
            tree_diameter_max_cm=30.0,
            p_pine=1.0,
            p_spruce=0.0,
            p_birch=0.0,
            site_index_species="pine",
            site_index_pine_m=20.0,
            site_index_spruce_m=22.0,
            latitude_deg=60.0,
            altitude_m=100.0,
            maritime=False,
            south_east=False,
            region5=False,
            rich=False,
            split=False,
            soil_moisture=Sweden.SoilMoistureEnum.MESIC,
            peat=False,
        )

    zero_growth = soderberg_1986_tree_diameter_growth_cm(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        diameter_cm=0.0,
        age_bh_years=40.0,
        part_of_sweden="north",
        stand_basal_area_m2_ha=10.0,
        tree_diameter_max_cm=30.0,
        p_pine=1.0,
        p_spruce=0.0,
        p_birch=0.0,
        site_index_species="pine",
        site_index_pine_m=20.0,
        site_index_spruce_m=22.0,
        latitude_deg=60.0,
        altitude_m=100.0,
        maritime=False,
        south_east=False,
        region5=False,
        rich=False,
        split=False,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        peat=False,
    )
    assert zero_growth == pytest.approx(0.0, abs=1e-12)


def test_soderberg_private_helper_guard_branches() -> None:
    with pytest.raises(ValueError, match="No coefficients available"):
        growth_module._coefficients_for_formula_species(
            growth_module._SpeciesGroup.UNKNOWN,
            growth_module._PartOfSweden.NORTH,
        )
    with pytest.raises(ValueError, match="Plot area must be positive"):
        growth_module._plot_expansion_factor(0.0, 0.0)

    assert growth_module._soil_moisture_indicators(Sweden.SoilMoistureEnum.DRY) == (1, 0)
    assert growth_module._soil_moisture_indicators(5) == (0, 1)


def test_soderberg_collect_trees_returns_empty_for_non_tree_modes() -> None:
    site = _DummySite(latitude=60.0, longitude=15.0)
    stand = Stand(
        site=site,
        plots=[
            CircularPlot(
                id=1,
                area_m2=200.0,
                trees=[
                    Tree(
                        species=TreeSpecies.Sweden.pinus_sylvestris,
                        diameter_cm=20.0,
                        age=40.0,
                    )
                ],
            )
        ],
    )
    model = Soderberg1986Model()
    ctx = model.build_context(stand, mode_hint="aggregate")
    assert growth_module._collect_trees(ctx) == []
