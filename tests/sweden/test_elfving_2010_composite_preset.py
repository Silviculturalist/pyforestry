from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

import pyforestry.sweden.simulation.presets.elfving_2010_composite as preset_module
from pyforestry.base.helpers import Tree
from pyforestry.base.helpers.primitives import SiteBase
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.simulation.mortality import MortalityConfig, MortalityResult
from pyforestry.sweden.simulation.presets import (
    Elfving2010CompositePresetConfig,
    build_elfving_2010_composite_preset,
)
from pyforestry.sweden.site import Sweden, SwedishSite


class _SiteDemo(SwedishSite):
    """Concrete wrapper for tests (implements SiteBase abstract method)."""

    def compute_attributes(self) -> None:
        SwedishSite.__post_init__(self)

    def __post_init__(self) -> None:
        SiteBase.__post_init__(self)


def _make_site() -> _SiteDemo:
    return _SiteDemo(
        latitude=60.5,
        longitude=15.0,
        altitude=150.0,
        field_layer=Sweden.FieldLayer.BILBERRY,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        soil_texture=Sweden.SoilTextureTill.SANDY,
        ditched=False,
    )


def _make_config(seed: int = 42, **overrides: object) -> Elfving2010CompositePresetConfig:
    return Elfving2010CompositePresetConfig(
        sample_trees=28,
        random_seed=seed,
        deterministic=True,
        dt_years=5.0,
        **overrides,
    )


def test_preset_initialization_returns_non_empty_tree_list() -> None:
    preset = build_elfving_2010_composite_preset(_make_config())
    trees = preset.initialize(site=_make_site())
    assert len(trees) > 0
    assert any((tree.diameter_cm or 0.0) > 0.0 for tree in trees)


def test_run_projection_is_deterministic_with_fixed_seed() -> None:
    site = _make_site()
    preset_one = build_elfving_2010_composite_preset(_make_config(seed=2026))
    preset_two = build_elfving_2010_composite_preset(_make_config(seed=2026))

    out_one = preset_one.run_projection(site=site, n_steps=2)
    out_two = preset_two.run_projection(site=site, n_steps=2)

    pd.testing.assert_frame_equal(out_one, out_two, check_exact=False, rtol=1e-10, atol=1e-10)


def test_projection_rows_include_qmd_and_hq_metrics() -> None:
    preset = build_elfving_2010_composite_preset(_make_config(seed=2026))
    out = preset.run_projection(site=_make_site(), n_steps=1)

    assert "qmd_cm" in out.columns
    assert "hq_m" in out.columns

    row = out.iloc[0]
    stems = float(row["stems_per_ha"])
    ba = float(row["basal_area_m2_ha"])
    expected_qmd = math.sqrt((40000.0 * ba) / (math.pi * stems)) if (stems > 0 and ba > 0) else 0.0

    assert float(row["qmd_cm"]) == pytest.approx(expected_qmd)
    assert float(row["hq_m"]) >= 0.0


def test_hq_helper_interpolates_height_at_qmd() -> None:
    trees = [
        Tree(
            species=TreeSpecies.Sweden.pinus_sylvestris,
            diameter_cm=10.0,
            height_m=12.0,
            weight_n=100.0,
        ),
        Tree(
            species=TreeSpecies.Sweden.pinus_sylvestris,
            diameter_cm=20.0,
            height_m=22.0,
            weight_n=100.0,
        ),
    ]

    preset = build_elfving_2010_composite_preset(_make_config())
    ba = sum(
        math.pi * ((float(tree.diameter_cm) / 200.0) ** 2) * float(tree.weight_n) for tree in trees
    )
    qmd_cm = preset._qmd_cm_from_basal_area_and_stems(basal_area_m2_ha=ba, stems_per_ha=200.0)
    hq_m = preset._hq_height_m_from_tree_list(trees, qmd_cm=qmd_cm)

    assert 10.0 < qmd_cm < 20.0
    assert 12.0 <= hq_m <= 22.0


def test_handover_rule_dbh_threshold_10cm() -> None:
    preset = build_elfving_2010_composite_preset(_make_config())
    trees = preset.initialize(site=_make_site())
    assert len(trees) >= 2

    trees[0].diameter_cm = 9.99
    trees[1].diameter_cm = 10.0
    young_ids = preset._young_tree_ids(trees)
    assert trees[0].uid in young_ids
    assert trees[1].uid not in young_ids


def test_standing_valuation_runs_with_mellanskog_2013() -> None:
    preset = build_elfving_2010_composite_preset(_make_config())
    preset.initialize(site=_make_site())
    valuation = preset.value_standing_forest()

    assert valuation["standing_value_sek_per_ha"] >= 0.0
    assert valuation["standing_volume_m3_per_ha"] >= 0.0
    assert valuation["value_per_m3_sek"] >= 0.0


def test_standing_valuation_uses_lookup_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    preset = build_elfving_2010_composite_preset(
        _make_config(
            valuation_use_solution_cube=True,
            valuation_solution_cube_path=None,
            valuation_cube_dbh_step_cm=5.0,
            valuation_cube_height_step_m=1.0,
            valuation_cube_bark_step_mm=2.0,
        )
    )
    preset.initialize(site=_make_site())

    base_species = preset.tree_list[0].species
    for tree in preset.tree_list:
        tree.species = base_species
        tree.diameter_cm = 25.1
        tree.height_m = 20.2
        tree.double_bark_mm = 12.3
        tree.weight_n = 1.0

    calls = {"count": 0}

    class _FakeBuckingResult:
        def __init__(self) -> None:
            self.total_value = 123.0
            self.vol_sk_ub = 0.9
            self.volume_per_quality = [0.0, 0.3, 0.2, 0.1, 0.2, 0.0, 0.0]

    def _fake_calculate_tree_value(self, *, min_diam_dead_wood, config=None):  # noqa: ANN001, ANN202
        calls["count"] += 1
        return _FakeBuckingResult()

    monkeypatch.setattr(
        preset_module.Nasberg_1985_BranchBound,
        "calculate_tree_value",
        _fake_calculate_tree_value,
    )

    first = preset.value_standing_forest()
    second = preset.value_standing_forest()

    assert calls["count"] == 1
    assert second["standing_value_sek_per_ha"] == pytest.approx(first["standing_value_sek_per_ha"])
    assert second["standing_volume_m3_per_ha"] == pytest.approx(first["standing_volume_m3_per_ha"])


def test_standing_valuation_cube_lookup_miss_falls_back_and_caches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preset = build_elfving_2010_composite_preset(
        _make_config(
            valuation_use_solution_cube=True,
            valuation_solution_cube_path=None,
            valuation_cube_dbh_step_cm=5.0,
            valuation_cube_height_step_m=1.0,
            valuation_cube_bark_step_mm=2.0,
        )
    )
    preset.initialize(site=_make_site())

    base_species = preset.tree_list[0].species
    for tree in preset.tree_list:
        tree.species = base_species
        tree.diameter_cm = 25.1
        tree.height_m = 20.2
        tree.double_bark_mm = 12.3
        tree.weight_n = 1.0

    class _MissingCube:
        def lookup(self, species: str, dbh: float, height: float) -> tuple[float, list]:  # noqa: ARG002
            return 0.0, []

    preset._valuation_solution_cube = _MissingCube()

    calls = {"count": 0}

    class _FakeBuckingResult:
        def __init__(self) -> None:
            self.total_value = 123.0
            self.vol_sk_ub = 0.9
            self.volume_per_quality = [0.0, 0.3, 0.2, 0.1, 0.2, 0.0, 0.0]

    def _fake_calculate_tree_value(self, *, min_diam_dead_wood, config=None):  # noqa: ANN001, ANN202
        calls["count"] += 1
        return _FakeBuckingResult()

    monkeypatch.setattr(
        preset_module.Nasberg_1985_BranchBound,
        "calculate_tree_value",
        _fake_calculate_tree_value,
    )

    first = preset.value_standing_forest()
    second = preset.value_standing_forest()

    assert calls["count"] == 1
    assert second["standing_value_sek_per_ha"] == pytest.approx(first["standing_value_sek_per_ha"])
    assert second["standing_volume_m3_per_ha"] == pytest.approx(first["standing_volume_m3_per_ha"])


def test_generate_recommended_cube_uses_expected_species(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}
    fake_cube = object()

    def _fake_generate(
        *,
        pricelist_data,
        taper_model,
        timber_class,
        species_list,
        dbh_range,
        height_range,
        dbh_step,
        height_step,
        workers,
    ):  # noqa: ANN001, ANN202
        calls["pricelist_data"] = pricelist_data
        calls["taper_model"] = taper_model
        calls["timber_class"] = timber_class
        calls["species_list"] = species_list
        calls["dbh_range"] = dbh_range
        calls["height_range"] = height_range
        calls["dbh_step"] = dbh_step
        calls["height_step"] = height_step
        calls["workers"] = workers
        return fake_cube

    monkeypatch.setattr(
        preset_module.SolutionCube,
        "generate",
        staticmethod(_fake_generate),
    )

    out = preset_module.Elfving2010CompositePreset.generate_recommended_valuation_solution_cube(
        workers=3,
        dbh_range_cm=(12.0, 32.0),
        height_range_m=(9.0, 25.0),
        dbh_step_cm=4,
        height_step_m=1.5,
    )

    assert out is fake_cube
    assert calls["timber_class"] is preset_module.SweTimber
    assert calls["species_list"] == ["pinus sylvestris", "picea abies"]
    assert calls["dbh_range"] == (12.0, 32.0)
    assert calls["height_range"] == (9.0, 25.0)
    assert calls["dbh_step"] == 4
    assert calls["height_step"] == 1.5
    assert calls["workers"] == 3


def test_recommended_cube_file_helper_builds_and_saves(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: dict[str, object] = {}

    class _FakeCube:
        def save(self, path: str) -> None:
            calls["save_path"] = path
            Path(path).write_text("fake cube")

    def _fake_generate(
        cls,  # noqa: ANN001
        *,
        workers,
        dbh_range_cm,
        height_range_m,
        dbh_step_cm,
        height_step_m,
    ):  # noqa: ANN001, ANN202
        calls["workers"] = workers
        calls["dbh_range_cm"] = dbh_range_cm
        calls["height_range_m"] = height_range_m
        calls["dbh_step_cm"] = dbh_step_cm
        calls["height_step_m"] = height_step_m
        return _FakeCube()

    monkeypatch.setattr(
        preset_module.Elfving2010CompositePreset,
        "generate_recommended_valuation_solution_cube",
        classmethod(_fake_generate),
    )

    cube_path = tmp_path / "test_composite_cube_helper.nc"
    out = preset_module.Elfving2010CompositePreset.ensure_recommended_valuation_solution_cube_file(
        path=str(cube_path),
        overwrite=True,
        workers=3,
        dbh_range_cm=(12.0, 32.0),
        height_range_m=(9.0, 25.0),
        dbh_step_cm=4,
        height_step_m=1.5,
    )

    assert Path(out) == cube_path
    assert Path(calls["save_path"]) == cube_path
    assert calls["workers"] == 3
    assert calls["dbh_range_cm"] == (12.0, 32.0)
    assert calls["height_range_m"] == (9.0, 25.0)
    assert calls["dbh_step_cm"] == 4
    assert calls["height_step_m"] == 1.5


def test_load_solution_cube_autogenerates_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    preset = build_elfving_2010_composite_preset(
        _make_config(
            valuation_solution_cube_path="/tmp/missing_composite_cube.nc",
            valuation_solution_cube_autogenerate_if_missing=True,
        )
    )
    calls: dict[str, object] = {}
    fake_cube = object()

    def _fake_ensure(self, *, path=None, overwrite=False, workers=None):  # noqa: ANN001, ANN202
        calls["path"] = path
        calls["overwrite"] = overwrite
        calls["workers"] = workers
        self._valuation_solution_cube = fake_cube
        return fake_cube

    monkeypatch.setattr(
        preset_module.Elfving2010CompositePreset,
        "ensure_valuation_solution_cube",
        _fake_ensure,
    )

    loaded = preset._load_solution_cube()

    assert loaded is fake_cube
    assert calls["path"] == "/tmp/missing_composite_cube.nc"
    assert calls["overwrite"] is False


def test_step_uses_5_year_default_period() -> None:
    preset = build_elfving_2010_composite_preset(_make_config())
    preset.initialize(site=_make_site())
    age_before = preset.current_age_years
    elapsed_before = preset.years_elapsed

    preset.step()

    assert preset.current_age_years == pytest.approx(age_before + 5.0)
    assert preset.years_elapsed == pytest.approx(elapsed_before + 5.0)


def test_mature_only_step_updates_live_tree_diameter() -> None:
    preset = build_elfving_2010_composite_preset(_make_config())
    preset.initialize(site=_make_site())

    for tree in preset.tree_list:
        tree.diameter_cm = max(12.0, float(tree.diameter_cm or 0.0))

    assert preset._young_tree_ids(preset.tree_list) == set()
    before = [float(tree.diameter_cm or 0.0) for tree in preset.tree_list]

    preset.step(dt_years=5.0)

    after = [float(tree.diameter_cm or 0.0) for tree in preset.tree_list]
    assert any(a > b for a, b in zip(after, before, strict=False))


def test_step_routes_mature_growth_via_elfving_stand_calibration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"count": 0}
    original = preset_module.Elfving2010Model._apply_stand_calibration

    def _wrapped(self, *args, **kwargs):  # noqa: ANN001, ANN202
        calls["count"] += 1
        return original(self, *args, **kwargs)

    monkeypatch.setattr(
        preset_module.Elfving2010Model,
        "_apply_stand_calibration",
        _wrapped,
    )

    preset = build_elfving_2010_composite_preset(_make_config())
    preset.initialize(site=_make_site())
    for tree in preset.tree_list:
        tree.diameter_cm = max(12.0, float(tree.diameter_cm or 0.0))

    preset.step(dt_years=5.0)

    assert calls["count"] >= 1


def test_naslund_damage_index_is_applied_in_young_growth() -> None:
    preset = build_elfving_2010_composite_preset(_make_config())
    preset.initialize(site=_make_site())
    for tree in preset.tree_list:
        tree.diameter_cm = min(8.0, float(tree.diameter_cm or 8.0))

    young_ids = preset._young_tree_ids(preset.tree_list)
    assert young_ids
    preset._apply_nystrom_young_growth(young_ids=young_ids, dt_years=5.0)

    assert 0.0 <= preset._last_damage_index_mean <= 1.0


def test_phase_over_smoothing_blend_function() -> None:
    preset = build_elfving_2010_composite_preset(_make_config())
    assert (
        preset._blend_phase_over_dbh(young_dbh_cm=8.0, mature_dbh_cm=12.0, mature_weight=0.0)
        == 8.0
    )
    assert (
        preset._blend_phase_over_dbh(young_dbh_cm=8.0, mature_dbh_cm=12.0, mature_weight=1.0)
        == 12.0
    )
    assert (
        preset._blend_phase_over_dbh(young_dbh_cm=8.0, mature_dbh_cm=12.0, mature_weight=0.5)
        == 10.0
    )
    assert preset._phase_over_weight(7.0) == pytest.approx(0.5)


def test_apply_soderberg_height_preserves_nystrom_height_for_young_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preset = build_elfving_2010_composite_preset(_make_config())
    preset.initialize(site=_make_site())
    assert len(preset.tree_list) >= 2

    young_tree = preset.tree_list[0]
    mature_tree = preset.tree_list[1]
    young_tree.diameter_cm = 8.0
    mature_tree.diameter_cm = 14.0
    young_tree.height_m = 9.0
    mature_tree.height_m = 12.0

    monkeypatch.setattr(
        preset_module,
        "soderberg_1992_height_tree_age_m",
        lambda **_kwargs: 1.25,
    )
    monkeypatch.setattr(
        preset_module,
        "soderberg_1992_bark_thickness_bh_mm",
        lambda **_kwargs: 4.0,
    )

    preset._apply_soderberg_height_and_bark(
        fallback_age_years=20.0,
        preserve_height_tree_ids={young_tree.uid},
    )

    assert young_tree.height_m == pytest.approx(9.0)
    assert mature_tree.height_m == pytest.approx(1.25)
    assert young_tree.double_bark_mm == pytest.approx(4.0)
    assert mature_tree.double_bark_mm == pytest.approx(4.0)


def test_rebuild_context_sets_site_index_from_dominant_species() -> None:
    preset = build_elfving_2010_composite_preset(
        _make_config(
            species_to_plant=preset_module.TreeSpecies.Sweden.picea_abies,
            site_index_pine_m=18.0,
            site_index_spruce_m=32.0,
        )
    )
    preset.initialize(site=_make_site())

    for tree in preset.tree_list:
        tree.species = preset_module.TreeSpecies.Sweden.picea_abies
        tree.diameter_cm = max(12.0, float(tree.diameter_cm or 0.0))

    preset._rebuild_context()

    assert preset._ctx is not None
    assert preset._ctx.attrs["site_index_m"] == pytest.approx(32.0)
    assert preset._ctx.attrs["dominant_species"] is preset_module.TreeSpecies.Sweden.picea_abies


def test_mortality_engine_application_reduces_tree_weights(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preset = build_elfving_2010_composite_preset(_make_config())
    preset.initialize(site=_make_site())

    def _fake_run(self, context):  # noqa: ANN001, ANN202
        n = len(context.trees)
        return MortalityResult(
            tree_probabilities=[0.2] * n,
            tree_realized_mortality=[0.2] * n,
            species_mortality_fraction={},
            species_mortality_fraction_before_calibration={},
            diagnostics={},
        )

    monkeypatch.setattr(preset_module.MortalityEngine, "run", _fake_run)

    stems_before = sum(float(tree.weight_n or 0.0) for tree in preset.tree_list)
    # Mortality is now two-phase: predict fractions (used by growth calibration),
    # then realize the stem removal.
    preset._predict_mortality(dt_years=5.0)
    preset._realize_mortality()
    stems_after = sum(float(tree.weight_n or 0.0) for tree in preset.tree_list)

    assert stems_after < stems_before
    assert preset._last_mortality_fraction_mean == pytest.approx(0.2)


def test_step_validation_and_no_mortality_branch() -> None:
    preset = build_elfving_2010_composite_preset(_make_config(apply_mortality=False))
    with pytest.raises(RuntimeError, match="initialized before calling step"):
        preset.step()

    preset.initialize(site=_make_site())
    with pytest.raises(ValueError, match="dt_years must be > 0"):
        preset.step(dt_years=0.0)

    preset.step(dt_years=5.0)
    assert preset._last_mortality_fraction_mean == pytest.approx(0.0)
    assert preset._last_mortality_stems_removed_per_ha == pytest.approx(0.0)


def test_run_projection_validation_errors() -> None:
    preset = build_elfving_2010_composite_preset(_make_config())
    with pytest.raises(ValueError, match="n_steps must be > 0"):
        preset.run_projection(site=_make_site(), n_steps=0)
    with pytest.raises(RuntimeError, match="Provide site or call initialize"):
        preset.run_projection(n_steps=1)


def test_build_mortality_config_uses_base_config_with_overrides() -> None:
    base = MortalityConfig(period_years=2.0, stochastic_seed=7)
    config = Elfving2010CompositePresetConfig(
        sample_trees=28,
        deterministic=True,
        random_seed=123,
        dt_years=7.0,
        mortality_config=base,
    )
    preset = build_elfving_2010_composite_preset(config)

    cfg = preset._build_mortality_config()
    assert cfg.period_years == pytest.approx(7.0)
    assert cfg.stochastic_seed == 123


def test_value_standing_forest_cached_and_direct_bucking_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preset_cached = build_elfving_2010_composite_preset(_make_config())
    preset_cached.initialize(site=_make_site())
    for tree in preset_cached.tree_list:
        tree.species = TreeSpecies.Sweden.pinus_sylvestris
        tree.diameter_cm = 25.0
        tree.height_m = 20.0
        tree.double_bark_mm = 10.0
        tree.weight_n = 1.0

    monkeypatch.setattr(
        preset_cached,
        "_lookup_or_compute_timber_value_volume",
        lambda **_kwargs: (10.0, 0.5, True),
    )
    valuation_cached = preset_cached.value_standing_forest()
    assert valuation_cached["timber_valued_stems_per_ha"] > 0.0

    preset_direct = build_elfving_2010_composite_preset(
        _make_config(valuation_use_solution_cube=False)
    )
    preset_direct.initialize(site=_make_site())
    for tree in preset_direct.tree_list:
        tree.species = TreeSpecies.Sweden.pinus_sylvestris
        tree.diameter_cm = 25.0
        tree.height_m = 20.0
        tree.double_bark_mm = 10.0
        tree.weight_n = 1.0

    class _FakeBuckingResult:
        total_value = 250.0
        vol_sk_ub = 1.2
        volume_per_quality = [0.0, 0.4, 0.3, 0.2, 0.2, 0.0, 0.0]

    monkeypatch.setattr(
        preset_module.Nasberg_1985_BranchBound,
        "calculate_tree_value",
        lambda self, *, min_diam_dead_wood, config=None: _FakeBuckingResult(),  # noqa: ARG005, ANN001
    )
    valuation_direct = preset_direct.value_standing_forest()
    assert valuation_direct["timber_valued_stems_per_ha"] > 0.0


def test_solution_cube_management_and_lookup_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}
    fake_cube = object()
    cube_path = "/tmp/test_elfving_composite_cube.nc"

    preset = build_elfving_2010_composite_preset(
        _make_config(valuation_solution_cube_path=cube_path)
    )

    monkeypatch.setattr(
        preset_module.Elfving2010CompositePreset,
        "ensure_recommended_valuation_solution_cube_file",
        classmethod(lambda cls, **kwargs: kwargs["path"]),  # noqa: ARG005
    )
    monkeypatch.setattr(
        preset_module.SolutionCube,
        "load",
        staticmethod(
            lambda path, pricelist_to_verify=None: (
                calls.__setitem__("load_path", path),
                fake_cube,
            )[1]  # noqa: ARG005
        ),
    )

    out = preset.ensure_valuation_solution_cube(path=cube_path, overwrite=True)
    assert out is fake_cube
    assert calls["load_path"] == cube_path

    Path(cube_path).write_text("cube")
    loaded = preset._load_solution_cube()
    assert loaded is fake_cube

    class _CubeHit:
        def lookup(self, species: str, dbh: float, height: float) -> tuple[float, list]:  # noqa: ARG002
            return 42.0, [{"volume": 0.7}]

    preset._valuation_solution_cube = _CubeHit()
    looked_up = preset._lookup_or_compute_timber_value_volume(
        species=TreeSpecies.Sweden.pinus_sylvestris.full_name,
        diameter_cm=25.0,
        height_m=20.0,
        bark_mm=10.0,
        region="southern",
    )
    assert looked_up == pytest.approx((42.0, 0.7, True))

    class _CubeMiss:
        def lookup(self, species: str, dbh: float, height: float) -> tuple[float, list]:  # noqa: ARG002
            return 0.0, []

    class _FakeBuckingResult:
        total_value = 123.0
        vol_sk_ub = 0.9
        volume_per_quality = [0.0, 0.3, 0.2, 0.1, 0.2, 0.0, 0.0]

    monkeypatch.setattr(
        preset_module.Nasberg_1985_BranchBound,
        "calculate_tree_value",
        lambda self, *, min_diam_dead_wood, config=None: _FakeBuckingResult(),  # noqa: ARG005, ANN001
    )
    preset._valuation_solution_cube = _CubeMiss()
    preset._valuation_lookup_cache = {}
    looked_up_miss = preset._lookup_or_compute_timber_value_volume(
        species=TreeSpecies.Sweden.pinus_sylvestris.full_name,
        diameter_cm=25.0,
        height_m=20.0,
        bark_mm=10.0,
        region="southern",
    )
    assert looked_up_miss == pytest.approx((123.0, 0.9, True))


def test_initial_dbh_age_fallback_and_naslund_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    preset = build_elfving_2010_composite_preset(_make_config())
    preset.initialize(site=_make_site())

    monkeypatch.setattr(
        preset_module.NystromSoderberg1987,
        "dbh_from_height",
        staticmethod(lambda **_kwargs: 5.0),
    )
    monkeypatch.setattr(
        preset_module.NystromSoderberg1987,
        "age_at_breast_height",
        staticmethod(lambda **_kwargs: -1.0),
    )
    preset._apply_initial_dbh_and_age()
    assert all(
        float(tree.age or 0.0) >= preset.config.initial_age_years - 1.0
        for tree in preset.tree_list
    )

    with pytest.raises(RuntimeError, match="site is not set"):
        object.__setattr__(preset, "_site", None)
        preset._apply_nystrom_young_growth(young_ids={id(preset.tree_list[0])}, dt_years=5.0)

    preset.initialize(site=_make_site())
    preset._apply_nystrom_young_growth(young_ids=set(), dt_years=5.0)
    assert preset._last_damage_index_mean == pytest.approx(0.0)
    assert preset._last_damage_mortality_stems_per_ha == pytest.approx(0.0)

    monkeypatch.setattr(
        preset,
        "_stand_metrics_for_nystrom",
        lambda trees: {"mean_height_m": 0.0},
    )
    preset._apply_nystrom_young_growth(young_ids={id(preset.tree_list[0])}, dt_years=5.0)
    assert preset._last_damage_index_mean == pytest.approx(0.0)

    assert (
        preset._naslund_species_group(TreeSpecies.Sweden.pinus_contorta)
        is preset_module.SaplingSpeciesGroup.CONTORTA
    )
    assert (
        preset._naslund_species_group(TreeSpecies.Sweden.larix_sibirica)
        is preset_module.SaplingSpeciesGroup.LARCH
    )
    assert (
        preset._naslund_species_group(TreeSpecies.Sweden.populus_tremula)
        is preset_module.SaplingSpeciesGroup.ASPEN
    )

    monkeypatch.setattr(
        preset_module.Naslund1986DamageModel,
        "risk_of_damage",
        staticmethod(lambda **_kwargs: []),
    )
    assert (
        preset._naslund_expected_dead_fraction(
            species_group=preset_module.SaplingSpeciesGroup.PINE,
            tree_height_m=2.0,
            damage_index=0.4,
        )
        == 0.0
    )

    monkeypatch.setattr(
        preset_module.Naslund1986DamageModel,
        "risk_of_damage",
        staticmethod(lambda **_kwargs: [0.6, 0.4]),
    )
    monkeypatch.setattr(
        preset_module.Naslund1986DamageModel,
        "damage_degree",
        staticmethod(lambda **_kwargs: (0.1, 0.2, 0.5)),
    )
    dead_fraction = preset._naslund_expected_dead_fraction(
        species_group=preset_module.SaplingSpeciesGroup.PINE,
        tree_height_m=2.0,
        damage_index=0.4,
    )
    assert dead_fraction == pytest.approx(0.2)


def test_misc_internal_helpers_cover_region_and_structure_branches() -> None:
    preset = build_elfving_2010_composite_preset(_make_config())
    preset.initialize(site=_make_site())

    assert preset._bal_m2_ha_for_tree(Tree(diameter_cm=0.0, weight_n=1.0)) == pytest.approx(0.0)

    object.__setattr__(preset._site, "latitude", 56.0)
    assert preset._infer_part_of_sweden() == "south"
    object.__setattr__(preset._site, "latitude", 58.0)
    assert preset._infer_part_of_sweden() == "middle"

    object.__setattr__(preset, "_trees", [])
    structure = preset._stand_structure()
    assert structure["ba_total"] == pytest.approx(0.0)
    assert preset._mean_age_total_years() == pytest.approx(max(1.0, preset.current_age_years))
