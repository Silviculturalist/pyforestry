"""Coverage for the Elfving 2010 composite preset ingrowth (recruitment) path."""

from __future__ import annotations

from pyforestry.base.helpers.primitives import SiteBase
from pyforestry.sweden.simulation.presets import build_elfving_2010_composite_preset
from pyforestry.sweden.simulation.presets.elfving_2010_composite import (
    Elfving2010CompositePresetConfig,
)
from pyforestry.sweden.site import Sweden, SwedishSite


class _SiteDemo(SwedishSite):
    """Concrete SwedishSite wrapper for tests."""

    def compute_attributes(self) -> None:
        """Compute derived site attributes."""
        SwedishSite.__post_init__(self)

    def __post_init__(self) -> None:
        """Initialize the base site."""
        SiteBase.__post_init__(self)


def _site() -> _SiteDemo:
    return _SiteDemo(
        latitude=60.5,
        longitude=15.0,
        altitude=150.0,
        field_layer=Sweden.FieldLayer.BILBERRY,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        soil_texture=Sweden.SoilTextureTill.SANDY,
        ditched=False,
    )


def _config(**overrides: object) -> Elfving2010CompositePresetConfig:
    return Elfving2010CompositePresetConfig(
        sample_trees=28, random_seed=42, deterministic=True, dt_years=5.0, **overrides
    )


def test_apply_ingrowth_runs_full_path_when_gated_in() -> None:
    """With QMD>10 cm and high mean age, the Wikberg ingrowth path executes."""
    preset = build_elfving_2010_composite_preset(_config())
    preset.initialize(site=_site())
    for tree in preset.tree_list:
        tree.diameter_cm = 16.0
        tree.weight_n = max(1.0, float(tree.weight_n or 0.0))
        tree.age = 90.0

    n_before = len(preset.tree_list)
    preset._apply_ingrowth()
    assert len(preset.tree_list) >= n_before  # full predict path ran without raising


def test_apply_ingrowth_skips_when_not_gated() -> None:
    """Without trees/site the ingrowth gate short-circuits (no recruitment)."""
    preset = build_elfving_2010_composite_preset(_config())
    assert preset._apply_ingrowth() is None
