from __future__ import annotations

import pandas as pd
import pytest

from pyforestry.base.helpers.primitives import SiteBase
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.adapters.elfving_2010 import Elfving2010Model
from pyforestry.sweden.adapters.soderberg_1986_growth import Soderberg1986Model
from pyforestry.sweden.simulation.presets import (
    Soderberg1986PipelineConfig,
    build_soderberg_1986_pipeline,
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


def _make_config(seed: int = 42, **overrides: object) -> Soderberg1986PipelineConfig:
    return Soderberg1986PipelineConfig(
        sample_trees=28,
        random_seed=seed,
        deterministic=True,
        dt_years=5.0,
        **overrides,
    )


def test_soderberg_preset_initialization_returns_non_empty_tree_list() -> None:
    preset = build_soderberg_1986_pipeline(_make_config())
    trees = preset.initialize(site=_make_site())
    assert len(trees) > 0
    assert any((tree.diameter_cm or 0.0) > 0.0 for tree in trees)


def test_soderberg_run_projection_is_deterministic_with_fixed_seed() -> None:
    site = _make_site()
    preset_one = build_soderberg_1986_pipeline(_make_config(seed=2026))
    preset_two = build_soderberg_1986_pipeline(_make_config(seed=2026))

    out_one = preset_one.run_projection(site=site, n_steps=2)
    out_two = preset_two.run_projection(site=site, n_steps=2)

    pd.testing.assert_frame_equal(out_one, out_two, check_exact=False, rtol=1e-10, atol=1e-10)


def test_soderberg_preset_uses_soderberg_model() -> None:
    preset = build_soderberg_1986_pipeline(_make_config())
    assert isinstance(preset._model, Soderberg1986Model)


def test_soderberg_refresh_model_context_sets_canonical_attrs_and_avoids_legacy_aliases() -> None:
    preset = build_soderberg_1986_pipeline(_make_config())
    preset.initialize(site=_make_site())
    preset._refresh_model_context()

    attrs = preset._ctx.attrs
    for key in {
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
    }:
        assert key in attrs

    for legacy_key in {
        "site_index_m",
        "thinned_0_10_years",
        "thinned_11_25_years",
        "thinned_11_30_years",
    }:
        assert legacy_key not in attrs

    assert attrs["site_index_species"] in {"pine", "spruce"}


def test_soderberg_refresh_model_context_uses_dynamic_conifer_site_index_selector() -> None:
    preset = build_soderberg_1986_pipeline(_make_config())
    preset.initialize(site=_make_site())

    for tree in preset.tree_list:
        tree.species = TreeSpecies.Sweden.picea_abies
        tree.diameter_cm = max(12.0, float(tree.diameter_cm or 0.0))

    preset._refresh_model_context()
    assert preset._ctx.attrs["site_index_species"] == "spruce"

    for tree in preset.tree_list:
        tree.species = TreeSpecies.Sweden.pinus_sylvestris

    preset._refresh_model_context()
    assert preset._ctx.attrs["site_index_species"] == "pine"


def test_soderberg_step_does_not_route_through_elfving_stand_calibration(
    monkeypatch,
) -> None:
    def _raise_if_called(*_args, **_kwargs) -> None:
        raise AssertionError(
            "Elfving stand calibration should not be called for Söderberg preset."
        )

    monkeypatch.setattr(Elfving2010Model, "_apply_stand_calibration", _raise_if_called)

    preset = build_soderberg_1986_pipeline(_make_config())
    preset.initialize(site=_make_site())
    for tree in preset.tree_list:
        tree.diameter_cm = max(12.0, float(tree.diameter_cm or 0.0))

    preset.step(dt_years=5.0)


def test_soderberg_preset_describable_metadata() -> None:
    preset = build_soderberg_1986_pipeline(_make_config())
    assert preset.component_id == "soderberg_1986_composite"
    # The preset cites the publication its growth model comes from, not itself:
    # "pyforestry contributors" with the model's year was not a citation anyone
    # could follow. What pyforestry composed is spelled out in the note.
    assert preset.source.author == "Söderberg, U."
    assert preset.source.year == 1986
    assert "pyforestry composition" in preset.source.note
    assert preset.components == (preset._model,)


_VALUATION_KEYS = {
    "standing_value_sek_per_ha",
    "standing_volume_m3_per_ha",
    "timber_volume_m3_per_ha",
    "pulp_volume_m3_per_ha",
    "value_per_m3_sek",
    "timber_valued_stems_per_ha",
    "volume_over_bark",
}


def test_soderberg_value_standing_forest_uses_form_height_volume() -> None:
    """The form-height route reports the same figures as the bucking route.

    It used to return four of the seven, and `_snapshot_row` filled two of the rest
    with `.get(key, 0.0)`.
    """
    preset = build_soderberg_1986_pipeline(_make_config(use_soderberg_form_height_volume=True))
    preset.initialize(site=_make_site())
    for tree in preset.tree_list:
        tree.diameter_cm = max(12.0, float(tree.diameter_cm or 0.0))
        tree.weight_n = max(1.0, float(tree.weight_n or 0.0))
        tree.age = max(20.0, float(tree.age or 0.0))

    result = preset.value_standing_forest()
    assert set(result) == _VALUATION_KEYS
    assert result["standing_volume_m3_per_ha"] > 0.0
    # This route bucks nothing, so there is no timber and no timber-valued stem, and
    # everything it does report is pulpwood.
    assert result["timber_volume_m3_per_ha"] == 0.0
    assert result["timber_valued_stems_per_ha"] == 0.0
    assert result["pulp_volume_m3_per_ha"] == pytest.approx(result["standing_volume_m3_per_ha"])
    assert result["standing_value_sek_per_ha"] > 0.0


def test_both_routes_report_volume_under_bark() -> None:
    """One basis, so a volume column is comparable and a price list applies to it."""
    bucking = build_soderberg_1986_pipeline(_make_config())
    bucking.initialize(site=_make_site())
    form_height = build_soderberg_1986_pipeline(
        _make_config(use_soderberg_form_height_volume=True)
    )
    form_height.initialize(site=_make_site())

    assert bucking.value_standing_forest()["volume_over_bark"] == 0.0
    assert form_height.value_standing_forest()["volume_over_bark"] == 0.0


def test_form_height_volume_is_converted_to_under_bark() -> None:
    """The conversion is the bark deduction it says it is, and it bites.

    Holding the form height and rescaling the cross-section by the Söderberg (1992)
    double bark: ``V_ub = V_ob * (d_ub / d_ob)^2``.
    """
    preset = build_soderberg_1986_pipeline(_make_config(use_soderberg_form_height_volume=True))
    preset.initialize(site=_make_site())

    tree = preset.tree_list[0]
    tree.diameter_cm = 25.0
    tree.double_bark_mm = 12.0
    structure = preset._stand_structure()

    converted = preset._form_height_volume_under_bark_m3(
        tree=tree,
        species=tree.species,
        volume_over_bark_m3=1.0,
        diameter_cm=25.0,
        structure=structure,
        mean_age_total_years=preset._mean_age_total_years(),
    )
    assert converted == pytest.approx((25.0 - 1.2) ** 2 / 25.0**2)
    assert 0.85 < converted < 1.0

    # A tree list from outside the pipeline may carry no bark; the conversion has to
    # find some rather than quietly return an over-bark volume.
    tree.double_bark_mm = 0.0
    from_stand = preset._form_height_volume_under_bark_m3(
        tree=tree,
        species=tree.species,
        volume_over_bark_m3=1.0,
        diameter_cm=25.0,
        structure=structure,
        mean_age_total_years=preset._mean_age_total_years(),
    )
    assert 0.0 < from_stand < 1.0


def test_soderberg_both_valuation_routes_report_the_same_figures() -> None:
    """One shape, so a projection column cannot mean two things by route."""
    bucking = build_soderberg_1986_pipeline(_make_config())
    bucking.initialize(site=_make_site())
    form_height = build_soderberg_1986_pipeline(
        _make_config(use_soderberg_form_height_volume=True)
    )
    form_height.initialize(site=_make_site())

    assert set(bucking.value_standing_forest()) == _VALUATION_KEYS
    assert set(form_height.value_standing_forest()) == _VALUATION_KEYS


def test_soderberg_value_standing_forest_form_height_empty_trees() -> None:
    preset = build_soderberg_1986_pipeline(_make_config(use_soderberg_form_height_volume=True))
    preset.initialize(site=_make_site())
    result = preset.value_standing_forest(tree_list=[])
    assert set(result) == _VALUATION_KEYS
    assert all(value == 0.0 for value in result.values())


def test_soderberg_site_index_selector_no_conifers_falls_back_to_species_to_plant() -> None:
    preset = build_soderberg_1986_pipeline(_make_config())
    no_conifer = preset._site_index_species_for_soderberg(
        dominant_species=TreeSpecies.Sweden.betula_pendula,
        stand_structure={"prop_pine": 0.0, "prop_spruce": 0.0},
    )
    assert no_conifer in {"pine", "spruce"}
    # equal conifer proportions -> decided by the dominant species
    tie_spruce = preset._site_index_species_for_soderberg(
        dominant_species=TreeSpecies.Sweden.picea_abies,
        stand_structure={"prop_pine": 0.3, "prop_spruce": 0.3},
    )
    assert tie_spruce == "spruce"


def test_soderberg_build_context_requires_site() -> None:
    preset = build_soderberg_1986_pipeline(_make_config())
    with pytest.raises(RuntimeError, match="site is not set"):
        preset._build_context()


def test_soderberg_refresh_model_context_requires_a_context() -> None:
    preset = build_soderberg_1986_pipeline(_make_config())
    with pytest.raises(RuntimeError, match="call initialize"):
        preset._refresh_model_context()
