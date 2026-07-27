"""The scenarios whose numbers are pinned in ``elfving_2010_pipeline_baseline.json``.

Shared by the regeneration script (``scripts/pin_elfving_2010_baseline.py``) and the
test that checks the pipeline still reproduces them, so the two cannot drift.
"""

from __future__ import annotations

from typing import Any, Dict

from pyforestry.base.helpers.primitives import SiteBase
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.site import Sweden, SwedishSite


class BaselineSite(SwedishSite):
    """Concrete site for the pinned scenarios (implements the abstract hook)."""

    def compute_attributes(self) -> None:
        """Populate the derived Swedish site attributes."""
        SwedishSite.__post_init__(self)

    def __post_init__(self) -> None:
        """Skip the Swedish derivation until :meth:`compute_attributes` asks for it."""
        SiteBase.__post_init__(self)


def make_site() -> BaselineSite:
    """Return the site every pinned scenario is projected on."""
    return BaselineSite(
        latitude=60.5,
        longitude=15.0,
        altitude=150.0,
        field_layer=Sweden.FieldLayer.BILBERRY,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        soil_texture=Sweden.SoilTextureTill.SANDY,
        ditched=False,
    )


#: Each scenario is ``(name, pipeline_kind, config_overrides, n_steps)``. Between them
#: they run every phase of ``step()``: the young-stand phase and the phase-over blend
#: (all scenarios start at age 12 and grow past the handover), mortality prediction
#: and realisation (``mortality``), the no-mortality branch (``no_mortality``),
#: Wikberg ingrowth (``ingrowth``, which needs the long horizon to pass the QMD and
#: mean-age gates), and the Söderberg mature-growth swap (``soderberg``).
SCENARIOS: tuple[tuple[str, str, Dict[str, Any], int], ...] = (
    (
        "mortality",
        "elfving",
        {"sample_trees": 28, "random_seed": 2026},
        12,
    ),
    (
        "no_mortality",
        "elfving",
        {"sample_trees": 24, "random_seed": 7, "apply_mortality": False},
        8,
    ),
    (
        "ingrowth",
        "elfving",
        {
            "sample_trees": 24,
            "random_seed": 11,
            "apply_ingrowth": True,
            "ingrowth_min_mean_age_years": 20.0,
            "species_to_plant": TreeSpecies.Sweden.picea_abies,
        },
        14,
    ),
    (
        "soderberg",
        "soderberg",
        {"sample_trees": 24, "random_seed": 99},
        10,
    ),
)


def build_pipeline(kind: str, overrides: Dict[str, Any]):
    """Build the pipeline a scenario names, with its config overrides applied."""
    from pyforestry.sweden.simulation.presets import (
        Elfving2010PipelineConfig,
        Soderberg1986PipelineConfig,
        build_elfving_2010_pipeline,
        build_soderberg_1986_pipeline,
    )

    if kind == "elfving":
        return build_elfving_2010_pipeline(
            Elfving2010PipelineConfig(deterministic=True, dt_years=5.0, **overrides)
        )
    if kind == "soderberg":
        return build_soderberg_1986_pipeline(
            Soderberg1986PipelineConfig(deterministic=True, dt_years=5.0, **overrides)
        )
    raise ValueError(f"Unknown pipeline kind {kind!r}.")


def run_scenario(kind: str, overrides: Dict[str, Any], n_steps: int) -> Dict[str, list]:
    """Project one scenario and return its table as plain column lists."""
    pipeline = build_pipeline(kind, overrides)
    table = pipeline.run_projection(site=make_site(), n_steps=n_steps)
    return {str(column): [float(v) for v in table[column]] for column in table.columns}
