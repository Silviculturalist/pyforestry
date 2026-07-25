"""Thin API facade for Kuehne (2022) Norway pine trajectories."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pyforestry.base.contracts import FormulaDescriptor
from pyforestry.base.helpers import Age, Stand
from pyforestry.base.simulation import GrowthModel, Requirements, SimulationContext
from pyforestry.norway.growth.kuehne_2022 import (
    kuehne_2022_basal_area,
    kuehne_2022_stand_volume,
    kuehne_2022_stem_density,
)
from pyforestry.norway.siteindex.kuehne_2022 import (
    KuehnePineModel,
    kuehne_2022_height_trajectory_and_si_scots_pine_norway,
    kuehne_2022_height_trajectory_scots_pine_norway,
)
from pyforestry.simulation.contracts import SourceReference


@dataclass(frozen=True)
class KuehnePineAdapterConfig:
    """Configuration for the Kuehne pine trajectory adapter."""

    dominant_height_m: float
    start_total_age_years: float


class KuehnePineGrowthModel(GrowthModel):
    """Aggregate-safe adapter that updates dominant height trajectories."""

    def __init__(self, config: KuehnePineAdapterConfig) -> None:
        """Store trajectory adapter configuration."""
        self.config = config

    @property
    def component_id(self) -> str:
        """Stable identifier for the Kuehne 2022 pine model."""
        return "kuehne_2022_pine"

    @property
    def source(self) -> SourceReference:
        """Bibliographic provenance."""
        return SourceReference(
            author="Kuehne, C., McLean, J.P., Maleki, K., Antón-Fernández, C. & Astrup, R.",
            year=2022,
            title=(
                "A stand-level growth and yield model for thinned and unthinned "
                "even-aged Scots pine forests in Norway"
            ),
            note="Silva Fennica 56(1), article 10627. doi:10.14214/sf.10627",
        )

    def requirements(self) -> Requirements:
        """Declare aggregate-mode compatibility."""
        return Requirements(inventory="aggregate")

    def build_context(
        self,
        stand: Stand,
        *,
        config: Optional[KuehnePineAdapterConfig] = None,
        **kwargs,
    ) -> SimulationContext:
        """Build context and seed Kuehne trajectory state."""
        cfg = config or self.config
        ctx = super().build_context(stand, mode_hint="aggregate", **kwargs)
        ctx.state["t"] = float(cfg.start_total_age_years)
        ctx.attrs["kuehne_dominant_height_m"] = float(cfg.dominant_height_m)
        return ctx

    def update_step(self, ctx: SimulationContext, dt: float) -> None:
        """Advance the stand: dominant height, then stem density, basal area and volume.

        Projects one unthinned period using the Kuehne (2022) component equations.
        Site index at base age 40 (SI40, required by the stem-density and volume
        equations) is derived from the dominant-height trajectory.
        """
        if dt <= 0.0:
            raise ValueError("dt must be positive.")

        age1 = Age.TOTAL(float(ctx.state.get("t", self.config.start_total_age_years)))
        age2 = Age.TOTAL(float(age1) + dt)
        h1 = float(ctx.attrs.get("kuehne_dominant_height_m", self.config.dominant_height_m))
        height2, h100 = kuehne_2022_height_trajectory_and_si_scots_pine_norway(
            dominant_height_m=h1,
            age=age1,
            age2=age2,
            output="both",
        )
        h2 = float(height2)
        si40 = float(kuehne_2022_height_trajectory_scots_pine_norway(h1, age1, Age.TOTAL(40.0)))

        stems1 = float(ctx.metrics["Stems"]["TOTAL"])
        ba1 = float(ctx.metrics["BasalArea"]["TOTAL"])
        stems2 = kuehne_2022_stem_density(stems1, age1, age2, si40)
        ba2 = kuehne_2022_basal_area(ba1, age1, age2, h1, h2, stems1, stems2)
        volume2 = kuehne_2022_stand_volume(ba2, h2, age2)

        ctx.set_aggregate_metrics(ba_total=float(ba2), stems_total=float(stems2))
        ctx.attrs["kuehne_dominant_height_m"] = h2
        ctx.attrs["kuehne_site_index_h100_m"] = float(h100)
        ctx.attrs["kuehne_site_index_si40_m"] = si40
        ctx.attrs["stand_volume_m3_per_ha"] = float(volume2)
        ctx.state["t"] = float(age2)


__all__ = [
    "KuehnePineModel",
    "KuehnePineAdapterConfig",
    "KuehnePineGrowthModel",
    "kuehne_2022_height_trajectory_and_si_scots_pine_norway",
]


DESCRIPTOR = FormulaDescriptor(
    component_id="kuehne_2022_model",
    source=SourceReference(
        author="Kuehne, C., McLean, J.P., Maleki, K., Antón-Fernández, C. & Astrup, R.",
        year=2022,
        title=(
            "A stand-level growth and yield model for thinned and unthinned "
            "even-aged Scots pine forests in Norway"
        ),
        note="Silva Fennica 56(1), article 10627. doi:10.14214/sf.10627",
    ),
    kind="model",
    domain="growth",
    composes=("kuehne_2022_siteindex",),
    kernel_names=("KuehnePineGrowthModel",),
)
