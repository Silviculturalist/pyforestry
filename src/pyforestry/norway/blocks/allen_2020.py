"""Simulation-facing facade for the Allen et al. (2020) Norway spruce model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers import Age, Stand, TreeSpecies
from pyforestry.base.helpers.primitives import (
    AgeMeasurement,
    SiteIndexValue,
    StandBasalArea,
    StandVolume,
    Stems,
)
from pyforestry.base.simulation import GrowthModel, Requirements, SimulationContext
from pyforestry.norway.growth.allen_2020 import (
    allen_2020_basal_area,
    allen_2020_dominant_height,
    allen_2020_quadratic_mean_diameter,
    allen_2020_site_index,
    allen_2020_stand_volume,
    allen_2020_stem_survival,
)


class Allen2020Model:
    """Callable facade over the Allen (2020) Norway spruce kernels."""

    @staticmethod
    def dominant_height(
        dominant_height_m: float, age1: AgeMeasurement, age2: AgeMeasurement
    ) -> float:
        """Project dominant height (`m`)."""
        return allen_2020_dominant_height(dominant_height_m, age1, age2)

    @staticmethod
    def site_index(dominant_height_m: float, age: AgeMeasurement) -> SiteIndexValue:
        """Return site index (dominant height at base age 40 yr)."""
        return allen_2020_site_index(dominant_height_m, age)

    @staticmethod
    def stem_survival(
        stems1: Stems | float,
        age1: AgeMeasurement,
        age2: AgeMeasurement,
        si_h40: SiteIndexValue | float,
        *,
        thinning_quotient: float = 1.0,
    ) -> Stems:
        """Project surviving stems per hectare."""
        return allen_2020_stem_survival(
            stems1, age1, age2, si_h40, thinning_quotient=thinning_quotient
        )

    @staticmethod
    def stand_volume(
        basal_area2: StandBasalArea | float,
        dominant_height2: float,
        age2: AgeMeasurement,
    ) -> StandVolume:
        """Return stand volume (`m3/ha`)."""
        return allen_2020_stand_volume(basal_area2, dominant_height2, age2)


@dataclass(frozen=True)
class Allen2020Config:
    """Configuration for the simulation-facing Allen (2020) growth adapter."""

    h40_m: float = 17.0
    dominant_height_m: float = 12.0
    start_total_age_years: float = 40.0


class Allen2020GrowthModel(GrowthModel):
    """Aggregate-inventory growth adapter using Allen et al. (2020).

    Projects an even-aged Norway spruce stand one step at a time (unthinned):
    dominant height, then surviving stems, then basal area, then volume.
    """

    def __init__(self, config: Optional[Allen2020Config] = None) -> None:
        """Store adapter configuration."""
        self.config = config or Allen2020Config()

    @property
    def component_id(self) -> str:
        """Stable identifier for the Allen 2020 model."""
        return "allen_2020"

    @property
    def source(self) -> SourceReference:
        """Bibliographic provenance."""
        return SourceReference(
            author="Allen, M.G. II, Antón-Fernández, C. & Astrup, R.",
            year=2020,
            title=(
                "A stand-level growth and yield model for thinned and unthinned "
                "managed Norway spruce forests in Norway"
            ),
            note=(
                "Scandinavian Journal of Forest Research 35(5-6):238-251. "
                "doi:10.1080/02827581.2020.1773525"
            ),
        )

    def requirements(self) -> Requirements:
        """Declare aggregate inventory requirement for the adapter."""
        return Requirements(inventory="aggregate")

    def build_context(
        self,
        stand: Stand,
        *,
        config: Optional[Allen2020Config] = None,
        **kwargs,
    ) -> SimulationContext:
        """Build and seed a simulation context for Allen projections."""
        cfg = config or self.config
        ctx = super().build_context(stand, mode_hint="aggregate", **kwargs)
        ctx.state["t"] = float(cfg.start_total_age_years)
        ctx.attrs["allen_h40_m"] = float(cfg.h40_m)
        ctx.attrs["dominant_height_m"] = float(cfg.dominant_height_m)
        return ctx

    def update_step(self, ctx: SimulationContext, dt: float) -> None:
        """Advance one step using Allen dominant-height, survival, BA and volume."""
        if dt <= 0.0:
            raise ValueError("dt must be positive.")

        age1 = Age.TOTAL(float(ctx.state.get("t", self.config.start_total_age_years)))
        age2 = Age.TOTAL(float(age1) + dt)
        h40_m = float(ctx.attrs.get("allen_h40_m", self.config.h40_m))
        si_h40 = SiteIndexValue(
            h40_m,
            reference_age=Age.TOTAL(40.0),
            species={TreeSpecies.Norway.picea_abies},
            fn=allen_2020_dominant_height,
        )

        stems1 = float(ctx.metrics["Stems"]["TOTAL"])
        ba1 = float(ctx.metrics["BasalArea"]["TOTAL"])
        h1 = float(ctx.attrs.get("dominant_height_m", self.config.dominant_height_m))

        h2 = allen_2020_dominant_height(h1, age1, age2)
        stems2 = allen_2020_stem_survival(stems1, age1, age2, si_h40)
        ba2 = allen_2020_basal_area(ba1, age1, age2, h1, h2, stems1, stems2)
        volume2 = allen_2020_stand_volume(ba2, h2, age2)
        qmd2 = allen_2020_quadratic_mean_diameter(ba2, float(stems2))

        ctx.set_aggregate_metrics(ba_total=float(ba2), stems_total=float(stems2))
        ctx.attrs["dominant_height_m"] = float(h2)
        ctx.attrs["stand_volume_m3_per_ha"] = float(volume2)
        ctx.attrs["quadratic_mean_diameter_cm"] = float(qmd2)
        ctx.state["t"] = float(age2)


__all__ = [
    "Allen2020Model",
    "Allen2020Config",
    "Allen2020GrowthModel",
]


DESCRIPTOR = FormulaDescriptor(
    component_id="allen_2020_model",
    source=SourceReference(
        author="Allen, M.G. II, Antón-Fernández, C. & Astrup, R.",
        year=2020,
        title=(
            "A stand-level growth and yield model for thinned and unthinned "
            "managed Norway spruce forests in Norway"
        ),
        note=(
            "Scandinavian Journal of Forest Research 35(5-6):238-251. "
            "doi:10.1080/02827581.2020.1773525"
        ),
    ),
    kind="model",
    domain="growth",
    composes=("allen_2020_growth",),
    kernel_names=("Allen2020GrowthModel",),
)
