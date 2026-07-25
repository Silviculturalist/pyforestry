"""Soderberg (1986) single-tree diameter growth model for Sweden.

This module implements Söderberg's single-tree diameter growth functions at
tree level for 5-year growth periods.

Primary reference:
  - Söderberg, U. (1986). Report 14, SLU, Umeå (Appendix 4 and related growth
    notes).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

from pyforestry.base.contracts import FormulaDescriptor
from pyforestry.base.helpers import TreeSpecies
from pyforestry.base.helpers.primitives import diameter_to_basal_area_cm2
from pyforestry.base.simulation import GrowthModel, Requirements, SimulationContext
from pyforestry.simulation.contracts import SourceReference
from pyforestry.sweden.growth.soderberg_1986.equations import (
    _active_site_index_m,
    _coefficients_for_formula_species,  # noqa: F401 -- re-exported for tests
    _collect_trees,
    _EquationCoefficients,  # noqa: F401 -- re-exported for tests
    _PartOfSweden,  # noqa: F401 -- re-exported for tests
    _plot_expansion_factor,
    _PredictorInputs,  # noqa: F401 -- re-exported for tests
    _resolve_thinning_state,
    _soil_moisture_indicators,  # noqa: F401 -- re-exported for tests
    _species_group,
    _SpeciesGroup,
    _tree_age_bh_years,
    _validate_canonical_attrs,
    soderberg_1986_tree_diameter_growth_cm,
)


@dataclass(frozen=True)
class Soderberg1986Config:
    """Configuration options for :class:`Soderberg1986Model`.

    Attributes:
        include_thinning_effect (bool): If ``True``, apply Söderberg's thinning-response
            terms (the thinned 0-5 yr / 6-25 yr state indicators in the published
            diameter-growth functions). When thinning is simulated in this period, the
            thinning-history indicators are ignored for this step.
    """

    include_thinning_effect: bool = True


class Soderberg1986Model(GrowthModel):
    """Simulation-engine adapter for the Söderberg (1986) diameter-growth equations."""

    def __init__(self, config: Soderberg1986Config | None = None) -> None:
        """Initialize the model with optional configuration."""
        self.config = config or Soderberg1986Config()

    @property
    def component_id(self) -> str:
        """Stable identifier for the Soderberg 1986 growth model."""
        return "soderberg_1986"

    @property
    def source(self) -> SourceReference:
        """Bibliographic provenance for the Soderberg 1986 growth model."""
        return SourceReference(
            author="Söderberg, U.",
            year=1986,
            title="Funktioner för skogliga produktionsprognoser",
        )

    def requirements(self) -> Requirements:
        """Return model inventory/site requirements."""
        return Requirements(inventory="either", require_site=False)

    def update_step(self, ctx: SimulationContext, dt: float) -> None:
        """Update one simulation step for tree-list or spatial contexts."""
        if dt <= 0:
            raise ValueError("dt must be positive.")
        if ctx.mode not in {"tree_list", "spatial"}:
            raise ValueError(
                f"Soderberg1986Model supports only tree_list and spatial modes; got '{ctx.mode}'."
            )

        scale = dt / 5.0
        if dt != 5.0:
            warnings.warn(
                "Soderberg growth scaled linearly from a 5-year period.",
                stacklevel=2,
            )

        self._update_tree_list(ctx, scale)
        ctx.state["years_since_thin"] = float(ctx.state.get("years_since_thin", 0.0)) + dt

    def _update_tree_list(self, ctx: SimulationContext, scale: float) -> None:
        """Apply growth update for trees using canonical context attributes."""
        _validate_canonical_attrs(ctx.attrs)
        trees = _collect_trees(ctx)
        if not trees:
            return

        expansions: list[float] = []
        for plot in ctx.plots:
            expansion_factor = _plot_expansion_factor(plot.area_ha, plot.occlusion)
            expansions.extend([expansion_factor] * len(plot.trees))

        stand_basal_area_m2_ha = float(ctx.metrics["BasalArea"].get("TOTAL", 0.0))
        if stand_basal_area_m2_ha <= 0:
            return

        tree_diameter_max_cm = max(
            (float(getattr(tree, "diameter_cm", 0.0) or 0.0) for tree in trees),
            default=0.0,
        )
        if tree_diameter_max_cm <= 0:
            return

        pine_basal_area_m2_ha = 0.0
        spruce_basal_area_m2_ha = 0.0
        birch_basal_area_m2_ha = 0.0
        for tree, expansion_factor in zip(trees, expansions, strict=False):
            diameter_cm = float(getattr(tree, "diameter_cm", 0.0) or 0.0)
            if diameter_cm <= 0:
                continue
            group = _species_group(tree.species)
            basal_area_m2_ha = (
                diameter_to_basal_area_cm2(diameter_cm)
                * 1.0e-4
                * float(getattr(tree, "weight_n", 1.0) or 1.0)
                * expansion_factor
            )
            if group in {
                _SpeciesGroup.PINE,
                _SpeciesGroup.CONTORTA,
                _SpeciesGroup.LARCH,
            }:
                pine_basal_area_m2_ha += basal_area_m2_ha
            elif group is _SpeciesGroup.SPRUCE:
                spruce_basal_area_m2_ha += basal_area_m2_ha
            elif group is _SpeciesGroup.BIRCH:
                birch_basal_area_m2_ha += basal_area_m2_ha

        p_pine = pine_basal_area_m2_ha / stand_basal_area_m2_ha
        p_spruce = spruce_basal_area_m2_ha / stand_basal_area_m2_ha
        p_birch = birch_basal_area_m2_ha / stand_basal_area_m2_ha

        part_of_sweden = str(ctx.attrs["part_of_sweden"])
        latitude_deg = float(ctx.attrs["latitude_deg"])
        altitude_m = float(ctx.attrs["altitude_m"])
        site_index_species = str(ctx.attrs["site_index_species"])
        site_index_pine_m = (
            ctx.attrs["site_index_pine_m"] if "site_index_pine_m" in ctx.attrs else None
        )
        site_index_spruce_m = (
            ctx.attrs["site_index_spruce_m"] if "site_index_spruce_m" in ctx.attrs else None
        )
        maritime = bool(ctx.attrs["maritime"])
        south_east = bool(ctx.attrs["south_east"])
        region5 = bool(ctx.attrs["region5"])
        rich = bool(ctx.attrs["rich"])
        split = bool(ctx.attrs["split"])
        soil_moisture = ctx.attrs["soil_moisture"]
        peat = bool(ctx.attrs["peat"])
        fertilized_within_10_years = bool(ctx.attrs.get("fertilized_within_10_years", False))
        thinned_0_5_years = bool(ctx.attrs.get("thinned_0_5_years", False))
        thinned_6_25_years = bool(ctx.attrs.get("thinned_6_25_years", False))
        thinning_simulated = bool(ctx.attrs.get("thinning_simulated", False))

        thinning_state = _resolve_thinning_state(
            thinned_0_5_years=thinned_0_5_years,
            thinned_6_25_years=thinned_6_25_years,
            thinning_simulated=thinning_simulated,
            include_thinning_effect=self.config.include_thinning_effect,
        )
        ctx.state["soderberg1986_thinning_state"] = thinning_state

        active_site_index_m = _active_site_index_m(
            site_index_species=site_index_species,
            site_index_pine_m=site_index_pine_m,
            site_index_spruce_m=site_index_spruce_m,
        )

        for tree in trees:
            diameter_cm = float(getattr(tree, "diameter_cm", 0.0) or 0.0)
            if diameter_cm <= 0:
                continue
            age_bh_years = _tree_age_bh_years(tree, active_site_index_m, latitude_deg)
            diameter_growth_cm = soderberg_1986_tree_diameter_growth_cm(
                species=tree.species or TreeSpecies.Sweden.pinus_sylvestris,
                diameter_cm=diameter_cm,
                age_bh_years=age_bh_years,
                part_of_sweden=part_of_sweden,
                stand_basal_area_m2_ha=stand_basal_area_m2_ha,
                tree_diameter_max_cm=tree_diameter_max_cm,
                p_pine=p_pine,
                p_spruce=p_spruce,
                p_birch=p_birch,
                site_index_species=site_index_species,
                site_index_pine_m=site_index_pine_m,
                site_index_spruce_m=site_index_spruce_m,
                latitude_deg=latitude_deg,
                altitude_m=altitude_m,
                maritime=maritime,
                south_east=south_east,
                region5=region5,
                rich=rich,
                split=split,
                soil_moisture=soil_moisture,  # type: ignore[arg-type]
                peat=peat,
                fertilized_within_10_years=fertilized_within_10_years,
                thinned_0_5_years=thinned_0_5_years,
                thinned_6_25_years=thinned_6_25_years,
                thinning_simulated=thinning_simulated,
                include_thinning_effect=self.config.include_thinning_effect,
            )
            tree.diameter_cm = diameter_cm + diameter_growth_cm * scale


__all__ = ["Soderberg1986Config", "Soderberg1986Model", "soderberg_1986_tree_diameter_growth_cm"]


DESCRIPTOR = FormulaDescriptor(
    component_id="soderberg_1986_model",
    source=SourceReference(
        author="Söderberg, U.",
        year=1986,
        title="Funktioner för skogliga produktionsprognoser",
    ),
    kind="model",
    domain="growth",
    composes=("soderberg_1986_growth",),
    kernel_names=("Soderberg1986Model",),
)
