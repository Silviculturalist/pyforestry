"""Thin API facade and runtime adapter for Bollandsas et al. (2008)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

from pyforestry.base.contracts import FormulaDescriptor
from pyforestry.base.helpers import Stand
from pyforestry.base.simulation import GrowthModel, Requirements, SimulationContext
from pyforestry.norway.growth.bollandsas_2008 import Bollandsas2008
from pyforestry.simulation.contracts import SourceReference


@dataclass(frozen=True)
class Bollandsas2008AdapterConfig:
    """Configuration for the Bollandsas simulation adapter."""

    site_index_by_species: Mapping[str, float]
    latitude_deg: float
    n_classes: int = 15
    class_width_mm: float = 50.0


class Bollandsas2008GrowthModel(GrowthModel):
    """Tree-list adapter around the Bollandsas diameter-class model."""

    def __init__(self, config: Bollandsas2008AdapterConfig) -> None:
        """Store adapter configuration."""
        self.config = config

    @property
    def component_id(self) -> str:
        """Stable identifier for the Bollandsas 2008 model."""
        return "bollandsas_2008"

    @property
    def source(self) -> SourceReference:
        """Bibliographic provenance."""
        return SourceReference(
            author="Bollandsås, O.M., Buongiorno, J. & Gobakken, T.",
            year=2008,
            title=(
                "Predicting the growth of stands of trees of mixed species and size: "
                "a matrix model for Norway"
            ),
            note=(
                "Scandinavian Journal of Forest Research 23(2):167-178. "
                "doi:10.1080/02827580801995315. Submodels from Bollandsås (2007)."
            ),
        )

    def requirements(self) -> Requirements:
        """Require tree-list style stand input for class construction."""
        return Requirements(inventory="tree_list")

    @staticmethod
    def _stems_total(state: Mapping[str, object]) -> float:
        """Return total stems/ha from species class vectors."""
        return float(sum(float(arr.sum()) for arr in state.values()))

    @staticmethod
    def _ba_total(core: Bollandsas2008, state: Mapping[str, object]) -> float:
        """Return total basal area (`m2/ha`) across all species groups."""
        ba_by_species = core.compute_stand_basal_area_by_species(state)
        return float(sum(float(v) for v in ba_by_species.values()))

    def build_context(
        self,
        stand: Stand,
        *,
        config: Optional[Bollandsas2008AdapterConfig] = None,
        **kwargs,
    ) -> SimulationContext:
        """Build context and seed class-state payload for simulation updates."""
        cfg = config or self.config
        ctx = super().build_context(stand, mode_hint="tree_list", **kwargs)
        core = Bollandsas2008(
            site_index_by_species=cfg.site_index_by_species,
            latitude_deg=float(cfg.latitude_deg),
            n_classes=int(cfg.n_classes),
            class_width_mm=float(cfg.class_width_mm),
        )
        state = core.stand_to_state(stand)
        ctx.attrs["bollandsas_model"] = core
        ctx.attrs["bollandsas_state"] = state
        ctx.set_aggregate_metrics(
            ba_total=self._ba_total(core, state),
            stems_total=self._stems_total(state),
        )
        return ctx

    def update_step(self, ctx: SimulationContext, dt: float) -> None:
        """Advance one or more 5-year Bollandsas transitions."""
        if dt <= 0.0:
            raise ValueError("dt must be positive.")
        n_steps = dt / 5.0
        rounded = int(round(n_steps))
        if abs(n_steps - rounded) > 1e-9:
            raise ValueError("Bollandsas2008GrowthModel requires dt in whole 5-year increments.")

        core = ctx.attrs.get("bollandsas_model")
        state = ctx.attrs.get("bollandsas_state")
        if not isinstance(core, Bollandsas2008) or not isinstance(state, Mapping):
            raise ValueError("Bollandsas context is missing initialized state.")

        next_state = state
        for _ in range(rounded):
            next_state = core.step_5y(next_state)

        ctx.attrs["bollandsas_state"] = next_state
        ctx.attrs["bollandsas_basal_area_by_species"] = {
            k: float(v) for k, v in core.compute_stand_basal_area_by_species(next_state).items()
        }
        ctx.set_aggregate_metrics(
            ba_total=self._ba_total(core, next_state),
            stems_total=self._stems_total(next_state),
        )
        ctx.state["t"] = float(ctx.state.get("t", 0.0)) + dt


__all__ = ["Bollandsas2008", "Bollandsas2008AdapterConfig", "Bollandsas2008GrowthModel"]


DESCRIPTOR = FormulaDescriptor(
    component_id="bollandsas_2008_model",
    source=SourceReference(
        author="Bollandsås, O.M., Buongiorno, J. & Gobakken, T.",
        year=2008,
        title=(
            "Predicting the growth of stands of trees of mixed species and size: "
            "a matrix model for Norway"
        ),
        note=(
            "Scandinavian Journal of Forest Research 23(2):167-178. "
            "doi:10.1080/02827580801995315. Submodels from Bollandsås (2007)."
        ),
    ),
    kind="model",
    domain="growth",
    composes=("bollandsas_2008_growth",),
    kernel_names=("Bollandsas2008GrowthModel",),
)
