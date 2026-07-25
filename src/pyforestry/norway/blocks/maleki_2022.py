"""Thin model facade for Maleki et al. (2022) Norway stand equations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pyforestry.base.contracts import FormulaDescriptor
from pyforestry.base.helpers import Age, Stand, TreeSpecies
from pyforestry.base.helpers.primitives import (
    AgeMeasurement,
    QuadraticMeanDiameter,
    SiteIndexValue,
    StandBasalArea,
    StandVolume,
    Stems,
)
from pyforestry.base.simulation import GrowthModel, Requirements, SimulationContext
from pyforestry.norway.growth.maleki_2022 import (
    Maleki2022Species,
    maleki_2022_basal_area_projection,
    maleki_2022_height_trajectory,
    maleki_2022_ingrowth_count,
    maleki_2022_ingrowth_probability,
    maleki_2022_stand_volume,
    maleki_2022_stem_density,
    maleki_2022_stem_survival,
)
from pyforestry.simulation.contracts import SourceReference


@dataclass(frozen=True)
class _MalekiSpeciesFacade:
    """Species-scoped callable facade for Maleki equations."""

    species: Maleki2022Species

    def get_stand_volume(
        self,
        dominant_height_m: float,
        basal_area: StandBasalArea | float,
        age: AgeMeasurement,
    ) -> StandVolume:
        """Return stand volume (`m3/ha`) for this species group."""
        return maleki_2022_stand_volume(self.species, dominant_height_m, basal_area, age)

    def get_stem_survival(
        self,
        age1: AgeMeasurement,
        age2: AgeMeasurement,
        stems1: Stems | float,
        si_h40: SiteIndexValue,
    ) -> Stems:
        """Return projected surviving stems for this species group."""
        return maleki_2022_stem_survival(self.species, age1, age2, stems1, si_h40)

    def get_stem_density(
        self,
        age1: AgeMeasurement,
        age2: AgeMeasurement,
        stems1: Stems | float,
        si_h40: SiteIndexValue,
    ) -> Stems:
        """Return projected stem density for this species group."""
        return maleki_2022_stem_density(self.species, age1, age2, stems1, si_h40)

    def get_ingrowth_count(
        self,
        *,
        basal_area: StandBasalArea | float | None = None,
        qmd: QuadraticMeanDiameter | float | None = None,
    ) -> float:
        """Return expected ingrowth count per 5-year period."""
        return maleki_2022_ingrowth_count(self.species, basal_area=basal_area, qmd=qmd)

    def get_ingrowth_probability(
        self,
        qmd: QuadraticMeanDiameter | float,
        stems: Stems | float,
    ) -> float:
        """Return probability of ingrowth occurrence for this species group."""
        return maleki_2022_ingrowth_probability(self.species, qmd, stems)

    def get_height_trajectory(
        self,
        dominant_height_m: float,
        age1: AgeMeasurement,
        age2: AgeMeasurement,
    ) -> float:
        """Return projected dominant height (`m`) for this species group."""
        return maleki_2022_height_trajectory(self.species, dominant_height_m, age1, age2)

    def get_basal_area_projection(
        self,
        basal_area1: StandBasalArea | float,
        age1: AgeMeasurement,
        age2: AgeMeasurement,
        si_h40: SiteIndexValue,
        stems1: Stems | float,
        stems2: Stems | float,
    ) -> StandBasalArea:
        """Return projected basal area (`m2/ha`) for this species group."""
        return maleki_2022_basal_area_projection(
            self.species,
            basal_area1,
            age1,
            age2,
            si_h40,
            stems1,
            stems2,
        )


class Maleki2022ModelNorway:
    """Compatibility model facade matching the Norway asset shape."""

    norway_spruce = _MalekiSpeciesFacade(Maleki2022Species.NORWAY_SPRUCE)
    scots_pine = _MalekiSpeciesFacade(Maleki2022Species.SCOTS_PINE)
    broadleaves = _MalekiSpeciesFacade(Maleki2022Species.BROADLEAVES)

    # Asset-compatibility aliases.
    picea_abies = norway_spruce
    pinus_sylvestris = scots_pine


@dataclass(frozen=True)
class Maleki2022Config:
    """Configuration for the simulation-facing Maleki growth adapter."""

    species: Maleki2022Species = Maleki2022Species.NORWAY_SPRUCE
    h40_m: float = 14.0
    dominant_height_m: float = 14.0
    start_total_age_years: float = 40.0


class Maleki2022GrowthModel(GrowthModel):
    """Aggregate-inventory growth adapter using Maleki et al. (2022)."""

    def __init__(self, config: Optional[Maleki2022Config] = None) -> None:
        """Store adapter configuration."""
        self.config = config or Maleki2022Config()

    @property
    def component_id(self) -> str:
        """Stable identifier for the Maleki 2022 model."""
        return "maleki_2022"

    @property
    def source(self) -> SourceReference:
        """Bibliographic provenance."""
        return SourceReference(
            author="Maleki, K., Astrup, R., Kuehne, C., McLean, J.P. & Antón-Fernández, C.",
            year=2022,
            title=(
                "Stand-level growth models for long-term projections of the main "
                "species groups in Norway"
            ),
            note=(
                "Scandinavian Journal of Forest Research 37(2):130-143. "
                "doi:10.1080/02827581.2022.2056632"
            ),
        )

    def requirements(self) -> Requirements:
        """Declare aggregate inventory requirement for the adapter."""
        return Requirements(inventory="aggregate")

    @staticmethod
    def _species_ref(species: Maleki2022Species):
        """Return representative species metadata for H40 site-index values."""
        if species is Maleki2022Species.NORWAY_SPRUCE:
            return TreeSpecies.Norway.picea_abies
        if species is Maleki2022Species.SCOTS_PINE:
            return TreeSpecies.Norway.pinus_sylvestris
        return TreeSpecies.Norway.betula_pubescens

    def build_context(
        self,
        stand: Stand,
        *,
        config: Optional[Maleki2022Config] = None,
        **kwargs,
    ) -> SimulationContext:
        """Build and seed simulation context for Maleki projections."""
        cfg = config or self.config
        ctx = super().build_context(stand, mode_hint="aggregate", **kwargs)
        ctx.state["t"] = float(cfg.start_total_age_years)
        ctx.attrs["maleki_species"] = cfg.species.value
        ctx.attrs["maleki_h40_m"] = float(cfg.h40_m)
        ctx.attrs["dominant_height_m"] = float(cfg.dominant_height_m)
        return ctx

    def update_step(self, ctx: SimulationContext, dt: float) -> None:
        """Advance one step using Maleki stem, basal-area, and height equations."""
        if dt <= 0.0:
            raise ValueError("dt must be positive.")

        age1 = Age.TOTAL(float(ctx.state.get("t", self.config.start_total_age_years)))
        age2 = Age.TOTAL(float(age1) + dt)
        species_raw = str(ctx.attrs.get("maleki_species", self.config.species.value))
        species = Maleki2022Species(species_raw)
        h40_m = float(ctx.attrs.get("maleki_h40_m", self.config.h40_m))
        si_h40 = SiteIndexValue(
            h40_m,
            reference_age=Age.TOTAL(40.0),
            species={self._species_ref(species)},
            fn=maleki_2022_height_trajectory,
        )

        stems1 = float(ctx.metrics["Stems"]["TOTAL"])
        ba1 = float(ctx.metrics["BasalArea"]["TOTAL"])
        h1 = float(ctx.attrs.get("dominant_height_m", self.config.dominant_height_m))

        stems2 = maleki_2022_stem_density(species, age1, age2, stems1, si_h40)
        ba2 = maleki_2022_basal_area_projection(species, ba1, age1, age2, si_h40, stems1, stems2)
        h2 = maleki_2022_height_trajectory(species, h1, age1, age2)
        volume2 = maleki_2022_stand_volume(species, h2, ba2, age2)

        ctx.set_aggregate_metrics(ba_total=float(ba2), stems_total=float(stems2))
        ctx.attrs["dominant_height_m"] = float(h2)
        ctx.attrs["stand_volume_m3_per_ha"] = float(volume2)
        ctx.state["t"] = float(age2)


__all__ = [
    "Maleki2022ModelNorway",
    "Maleki2022Species",
    "Maleki2022Config",
    "Maleki2022GrowthModel",
]


DESCRIPTOR = FormulaDescriptor(
    component_id="maleki_2022_model",
    source=SourceReference(
        author="Maleki, K., Astrup, R., Kuehne, C., McLean, J.P. & Antón-Fernández, C.",
        year=2022,
        title=(
            "Stand-level growth models for long-term projections of the main "
            "species groups in Norway"
        ),
        note=(
            "Scandinavian Journal of Forest Research 37(2):130-143. "
            "doi:10.1080/02827581.2022.2056632"
        ),
    ),
    kind="model",
    domain="growth",
    composes=("maleki_2022_growth",),
    kernel_names=("Maleki2022GrowthModel",),
)
