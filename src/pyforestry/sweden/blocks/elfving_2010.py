"""Elfving tree and stand growth models for Sweden.

This module implements two published functions:
  - Single-tree diameter increment (Elfving 2010, tracing to Elfving 2003).
  - Stand-level basal-area growth and calibration (Elfving 2009).

Notes:
  - Diameter inputs/outputs are in centimeters. Basal area is in m²/ha at stand scale.
  - Growth functions are calibrated for 5-year periods. We scale linearly when ``dt != 5``.
  - The published pine equation applies the rich-vegetation term additively, and we
    follow the published form. An inconsistency in one downstream implementation would
    instead fold that term into the fertilisation term, which we do not reproduce.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from math import exp, log, sqrt
from typing import Sequence

from pyforestry.base.contracts import FormulaDescriptor
from pyforestry.base.helpers import Tree, TreeName, TreeSpecies
from pyforestry.base.helpers.primitives import (
    QuadraticMeanDiameter,
    StandBasalArea,
    Stems,
    basal_area_growth_cm2_to_diameter_growth_cm,
    diameter_growth_to_basal_area_growth_cm2,
    diameter_to_basal_area_cm2,
)
from pyforestry.base.simulation import GrowthModel, Requirements, SimulationContext
from pyforestry.simulation.contracts import SourceReference
from pyforestry.sweden.growth.elfving_2010.features import (
    BIRCH_SPECIES as _BIRCH_SPECIES,
)
from pyforestry.sweden.growth.elfving_2010.features import (
    PINE_SPECIES as _PINE_SPECIES,
)
from pyforestry.sweden.growth.elfving_2010.features import (
    SPRUCE_SPECIES as _SPRUCE_SPECIES,
)
from pyforestry.sweden.growth.elfving_2010.features import (
    collect_trees as _collect_trees,
)
from pyforestry.sweden.growth.elfving_2010.features import (
    compute_bal_by_tree as _compute_bal_by_tree,
)
from pyforestry.sweden.growth.elfving_2010.features import (
    compute_bawad_cm as _compute_bawad_cm,
)
from pyforestry.sweden.growth.elfving_2010.features import (
    distance_to_coast_km as _distance_to_coast_km,
)
from pyforestry.sweden.growth.elfving_2010.features import (
    fertilization_flag as _fertilization_flag,
)
from pyforestry.sweden.growth.elfving_2010.features import (
    field_estimated_basal_area_m2_ha as _field_estimated_basal_area_m2_ha,
)
from pyforestry.sweden.growth.elfving_2010.features import (
    mean_age_total as _mean_age_total,
)
from pyforestry.sweden.growth.elfving_2010.features import (
    plot_expansion_factor as _plot_expansion_factor,
)
from pyforestry.sweden.growth.elfving_2010.features import (
    resolve_latitude_altitude as _resolve_latitude_altitude,
)
from pyforestry.sweden.growth.elfving_2010.features import (
    resolve_site_index_m as _resolve_site_index_m,
)
from pyforestry.sweden.growth.elfving_2010.features import (
    resolve_temperature_sum as _resolve_temperature_sum,
)
from pyforestry.sweden.growth.elfving_2010.features import (
    species_group as _species_group,
)
from pyforestry.sweden.growth.elfving_2010.features import (
    split_edge_flags as _split_edge_flags,
)
from pyforestry.sweden.growth.elfving_2010.features import (
    thinning_flags as _thinning_flags,
)
from pyforestry.sweden.growth.elfving_2010.features import (
    tree_age_bh_years as _tree_age_bh_years,
)
from pyforestry.sweden.growth.elfving_2010.features import (
    tree_age_total_years as _tree_age_total_years,
)
from pyforestry.sweden.growth.elfving_2010.features import (
    vegetation_flags as _vegetation_flags,
)
from pyforestry.sweden.growth.elfving_2010.kernels import (
    aspen_ln_d2_growth,
    beech_ln_d2_growth,
    birch_ln_d2_growth,
    oak_ln_d2_growth,
    pine_ln_d2_growth,
    precious_ln_d2_growth,
    spruce_ln_d2_growth,
    stand_basal_area_growth_elfving_2009,
    trivial_ln_d2_growth,
)
from pyforestry.sweden.growth.elfving_2010.thinning_response import (
    elfving_2009_thinning_response_factor,
)
from pyforestry.sweden.misc import dominant_mean_diameter_cm
from pyforestry.sweden.site import Sweden, SwedishSite

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Elfving2010Config:
    """Configuration for Elfving 2010 growth model."""

    include_thinning_effect: bool = True
    stand_growth_min_diameter_cm: float = 10.0
    site_index_adjustment_factor: float = 1.0
    use_edge_effects: bool = False
    max_mean_dgv_cm: float = 70.0
    max_bal_over_dbh: float = 3.0


# ---------------------------------------------------------------------------
# Growth model adapter
# ---------------------------------------------------------------------------


class Elfving2010Model(GrowthModel):
    """Simulation adapter for the Elfving 2010 tree + stand growth model."""

    def __init__(self, config: Elfving2010Config | None = None) -> None:
        """Initialize model adapter with optional configuration overrides."""
        self.config = config or Elfving2010Config()

    @property
    def component_id(self) -> str:
        """Stable identifier for the Elfving 2010 growth model."""
        return "elfving_2010"

    @property
    def source(self) -> SourceReference:
        """Bibliographic provenance for the Elfving growth model."""
        return SourceReference(
            author="Elfving, B.",
            year=2010,
            title="Growth modelling in the Heureka system",
            note=(
                "The single-tree diameter functions are from Elfving (2010), "
                "'Growth modelling in the Heureka system' (tracing to Elfving 2003). "
                "The stand-level basal-area growth function is Elfving (2009)."
            ),
        )

    def requirements(self) -> Requirements:
        """Declare that this model accepts either inventory mode and needs site data."""
        return Requirements(inventory="either", require_site=True)

    def update_step(self, ctx: SimulationContext, dt: float) -> None:
        """Advance one simulation step and route to tree-list or aggregate update."""
        if dt <= 0:
            raise ValueError("dt must be positive.")

        site = ctx.site if isinstance(ctx.site, SwedishSite) else None
        scale = dt / 5.0
        if dt != 5.0:
            warnings.warn("Elfving growth scaled linearly from 5-year period.", stacklevel=2)

        if ctx.mode in ("tree_list", "spatial"):
            self._update_tree_list(ctx, site, scale)
        else:
            self._update_aggregate(ctx, site, scale)

        ctx.state["years_since_thin"] = ctx.state.get("years_since_thin", 0.0) + dt

    def _ln_d2_growth_for_group(
        self,
        *,
        group: str,
        diameter_cm: float,
        bal_over_dbh: float,
        age_bh_years: float,
        overstorey: int,
        bawad_total: float,
        qmd_total: float,
        basal_area_total: float,
        group_ba: dict[str, float],
        gotland: int,
        temperature_sum_dd: float,
        site_index_m: float,
        rich: int,
        herb: int,
        fertilized: int,
        thinned_0_10_years_flag: int,
        thinned_11_25_years_flag: int,
        split: int,
        edge: int,
        field_ba: float,
        distance_to_coast_km: float,
        latitude_deg: float,
        altitude_m: float,
    ) -> float:
        """Dispatch tree-level log-growth equation by Elfving species group."""
        if group == "pine":
            return pine_ln_d2_growth(
                diameter_cm=diameter_cm,
                bal_over_dbh=bal_over_dbh,
                age_bh_years=age_bh_years,
                overstorey=overstorey,
                mean_dgv_cm=bawad_total,
                basal_area_m2_ha=basal_area_total,
                basal_area_pines_m2_ha=group_ba["pine"],
                gotland=gotland,
                temperature_sum_dd=temperature_sum_dd,
                site_index_m=site_index_m,
                rich=rich,
                fertilized=fertilized,
                thinned_0_10_years_flag=thinned_0_10_years_flag,
                thinned_11_25_years_flag=thinned_11_25_years_flag,
                split=split,
                edge=edge,
                field_ba_m2_ha=field_ba,
            )
        if group == "spruce":
            return spruce_ln_d2_growth(
                diameter_cm=diameter_cm,
                bal_over_dbh=bal_over_dbh,
                age_bh_years=age_bh_years,
                overstorey=overstorey,
                mean_dgv_cm=bawad_total,
                mean_dg_cm=qmd_total,
                basal_area_m2_ha=basal_area_total,
                basal_area_spruce_m2_ha=group_ba["spruce"],
                gotland=gotland,
                temperature_sum_dd=temperature_sum_dd,
                site_index_m=site_index_m,
                rich=rich,
                fertilized=fertilized,
                thinned_0_10_years_flag=thinned_0_10_years_flag,
                split=split,
                edge=edge,
                field_ba_m2_ha=field_ba,
            )
        if group == "birch":
            return birch_ln_d2_growth(
                diameter_cm=diameter_cm,
                bal_over_dbh=bal_over_dbh,
                age_bh_years=age_bh_years,
                overstorey=overstorey,
                basal_area_m2_ha=basal_area_total,
                basal_area_birch_m2_ha=group_ba["birch"],
                temperature_sum_dd=temperature_sum_dd,
                distance_to_coast_km=distance_to_coast_km,
                rich=rich,
                fertilized=fertilized,
                thinned_0_10_years_flag=thinned_0_10_years_flag,
                edge=edge,
                field_ba_m2_ha=field_ba,
            )
        if group == "aspen":
            return aspen_ln_d2_growth(
                diameter_cm=diameter_cm,
                bal_over_dbh=bal_over_dbh,
                age_bh_years=age_bh_years,
                basal_area_m2_ha=basal_area_total,
                basal_area_aspen_m2_ha=group_ba["aspen"],
                temperature_sum_dd=temperature_sum_dd,
                rich=rich,
                thinned_0_10_years_flag=thinned_0_10_years_flag,
                field_ba_m2_ha=field_ba,
            )
        if group == "beech":
            return beech_ln_d2_growth(
                diameter_cm=diameter_cm,
                bal_over_dbh=bal_over_dbh,
                age_bh_years=age_bh_years,
                basal_area_m2_ha=basal_area_total,
                basal_area_beech_m2_ha=group_ba["beech"],
                latitude_deg=latitude_deg,
                site_index_m=site_index_m,
                thinned_0_10_years_flag=thinned_0_10_years_flag,
                split=split,
                field_ba_m2_ha=field_ba,
            )
        if group == "oak":
            return oak_ln_d2_growth(
                diameter_cm=diameter_cm,
                bal_over_dbh=bal_over_dbh,
                basal_area_m2_ha=basal_area_total,
                basal_area_oak_m2_ha=group_ba["oak"],
                gotland=gotland,
                altitude_m=altitude_m,
                rich=rich,
                thinned_0_10_years_flag=thinned_0_10_years_flag,
                edge=edge,
                field_ba_m2_ha=field_ba,
            )
        if group == "precious":
            return precious_ln_d2_growth(
                diameter_cm=diameter_cm,
                bal_over_dbh=bal_over_dbh,
                basal_area_m2_ha=basal_area_total,
                gotland=gotland,
                herb=herb,
                thinned_0_10_years_flag=thinned_0_10_years_flag,
                field_ba_m2_ha=field_ba,
            )
        return trivial_ln_d2_growth(
            diameter_cm=diameter_cm,
            bal_over_dbh=bal_over_dbh,
            age_bh_years=age_bh_years,
            basal_area_m2_ha=basal_area_total,
            site_index_m=site_index_m,
            herb=herb,
            thinned_0_10_years_flag=thinned_0_10_years_flag,
        )

    # ------------------------------------------------------------------
    # Tree-list / spatial mode
    # ------------------------------------------------------------------

    def _update_tree_list(
        self,
        ctx: SimulationContext,
        site: SwedishSite | None,
        scale: float,
    ) -> None:
        """Update tree-list/spatial inventories using tree kernels and stand calibration."""
        trees = _collect_trees(ctx)
        if not trees:
            return

        # expansion factors per tree (aligned to trees)
        expansions = []
        for plot in ctx.plots:
            exp_factor = _plot_expansion_factor(plot.area_ha, plot.occlusion)
            expansions.extend([exp_factor] * len(plot.trees))

        bal_map = _compute_bal_by_tree(trees, expansions)

        # Stand-level aggregates
        basal_area_total = float(ctx.metrics["BasalArea"]["TOTAL"])
        if basal_area_total <= 0:
            return
        qmd_total = float(ctx.metrics["QMD"]["TOTAL"]) if ctx.metrics["QMD"] else 0.0
        bawad_total = _compute_bawad_cm(trees, expansions)
        bawad_total = min(bawad_total, self.config.max_mean_dgv_cm)

        # Species basal areas by group (m2/ha)
        group_ba = {
            k: 0.0
            for k in (
                "pine",
                "spruce",
                "birch",
                "aspen",
                "beech",
                "oak",
                "precious",
                "trivial",
            )
        }
        for tree, exp_factor in zip(trees, expansions, strict=False):
            d = float(getattr(tree, "diameter_cm", 0.0) or 0.0)
            if d <= 0:
                continue
            ba_m2_ha = (
                diameter_to_basal_area_cm2(d)
                * 1.0e-4
                * float(getattr(tree, "weight_n", 1.0) or 1.0)
                * exp_factor
            )
            group_ba[_species_group(tree.species)] += ba_m2_ha

        pine_ba = group_ba["pine"]
        spruce_ba = group_ba["spruce"]

        ts = _resolve_temperature_sum(site, ctx)
        lat, alt = _resolve_latitude_altitude(site, ctx)
        rich, herb = _vegetation_flags(site.field_layer if site is not None else None)
        gotland = int(site is not None and site.county == Sweden.County.GOTLAND)
        split, edge = _split_edge_flags(ctx)
        field_ba = _field_estimated_basal_area_m2_ha(ctx)
        if field_ba is None or field_ba <= 0:
            field_ba = basal_area_total
        thinned_0_10_years_flag, thinned_10_30_years_flag = _thinning_flags(
            ctx, self.config.include_thinning_effect
        )
        thinned_11_25_years_flag = int(bool(ctx.attrs.get("thinned_11_25_years", False)))
        fertilized = _fertilization_flag(ctx)
        distance_to_coast_km = _distance_to_coast_km(site, ctx)

        site_index_m = _resolve_site_index_m(
            site=site,
            ctx=ctx,
            pine_ba=pine_ba,
            spruce_ba=spruce_ba,
        )

        # Overstorey classification (if needed)
        mean_age_total = _mean_age_total(trees, expansions, site_index_m, lat)
        dominant_mean = dominant_mean_diameter_cm(
            mean_age_total_years=mean_age_total,
            field_estimated_basal_area_m2_ha=field_ba,
            site_index_m=site_index_m,
        )
        diameter_limit_overstorey = 1.8 * (dominant_mean + 8.0) if dominant_mean > 0 else 1.0e6

        # First-pass tree increments (5-year)
        base_increments = []
        for idx, tree in enumerate(trees):
            d = float(getattr(tree, "diameter_cm", 0.0) or 0.0)
            if d <= 0:
                base_increments.append(0.0)
                continue
            bal = bal_map.get(idx, 0.0)
            bal_over_dbh = min(self.config.max_bal_over_dbh, bal / (d + 1.0))
            overstorey = (
                int(bool(tree.is_overstorey))
                if tree.is_overstorey is not None
                else int(d > diameter_limit_overstorey)
            )
            age_bh = _tree_age_bh_years(
                tree=tree,
                site_index_m=site_index_m,
                latitude_deg=lat,
                default_species=TreeSpecies.Sweden.pinus_sylvestris,
            )
            group = _species_group(tree.species)
            ln_d2 = self._ln_d2_growth_for_group(
                group=group,
                diameter_cm=d,
                bal_over_dbh=bal_over_dbh,
                age_bh_years=age_bh,
                overstorey=overstorey,
                bawad_total=bawad_total,
                qmd_total=qmd_total,
                basal_area_total=basal_area_total,
                group_ba=group_ba,
                gotland=gotland,
                temperature_sum_dd=ts,
                site_index_m=site_index_m,
                rich=rich,
                herb=herb,
                fertilized=fertilized,
                thinned_0_10_years_flag=thinned_0_10_years_flag,
                thinned_11_25_years_flag=thinned_11_25_years_flag,
                split=split,
                edge=edge,
                field_ba=field_ba,
                distance_to_coast_km=distance_to_coast_km,
                latitude_deg=lat,
                altitude_m=alt,
            )

            d2_growth = exp(ln_d2)
            diam_growth = sqrt(d2_growth + d**2) - d
            if diam_growth < 0.0:
                raise ValueError("Diameter growth must be non-negative.")
            if diam_growth > 1000.0:
                raise ValueError("Diameter growth > 1000 mm; check inputs.")
            base_increments.append(diam_growth)

        # Stand-level calibration
        self._apply_stand_calibration(
            ctx=ctx,
            trees=trees,
            expansions=expansions,
            base_increments=base_increments,
            site=site,
            site_index_m=site_index_m,
            mean_age_total=mean_age_total,
            field_ba=field_ba,
            scale=scale,
        )

    def _thinning_response_factor(
        self, ctx: SimulationContext, spruce_basal_area_share: float
    ) -> float:
        """Return the Elfving (2009) continuous thinning-response multiplier.

        Active only when ``include_thinning_effect`` is set and a thinning has been
        simulated (``ctx.attrs['thinning_simulated']``), in which case the discrete
        ``thinned_0_10``/``thinned_10_30`` dummies are already suppressed. Reads the
        thinning history from ``ctx.attrs['thinning_history']`` -- a sequence of
        ``ThinningEvent`` ordered most-recent first. Returns 1.0 otherwise, leaving
        the unmanaged stand growth unchanged.
        """
        if not self.config.include_thinning_effect:
            return 1.0
        if ctx.attrs.get("thinning_simulated") is not True:
            return 1.0
        history = tuple(ctx.attrs.get("thinning_history") or ())
        if not history:
            return 1.0
        return elfving_2009_thinning_response_factor(
            last_thinning=history[0],
            earlier_thinnings=history[1:],
            spruce_basal_area_share=float(spruce_basal_area_share),
        )

    def _apply_stand_calibration(
        self,
        *,
        ctx: SimulationContext,
        trees: Sequence[Tree],
        expansions: Sequence[float],
        base_increments: Sequence[float],
        site: SwedishSite | None,
        site_index_m: float,
        mean_age_total: float,
        field_ba: float,
        scale: float,
    ) -> None:
        """Apply stand calibration and update tree diameters."""
        lat, _alt = _resolve_latitude_altitude(site, ctx)

        basal_area_all = 0.0
        contorta_ba = 0.0
        for tree, exp_factor in zip(trees, expansions, strict=False):
            d = float(getattr(tree, "diameter_cm", 0.0) or 0.0)
            if d <= 0:
                continue
            ba = (
                diameter_to_basal_area_cm2(d)
                * 1.0e-4
                * float(getattr(tree, "weight_n", 1.0) or 1.0)
                * exp_factor
            )
            basal_area_all += ba
            if tree.species is TreeSpecies.Sweden.pinus_contorta:
                contorta_ba += ba

        if basal_area_all <= 0:
            return

        # Site index adjustment for contorta
        site_index_adj = site_index_m
        if contorta_ba > 0:
            site_index_adj += 3.0 * contorta_ba / basal_area_all
        site_index_adj *= self.config.site_index_adjustment_factor

        dominant_mean = dominant_mean_diameter_cm(
            mean_age_total_years=mean_age_total,
            field_estimated_basal_area_m2_ha=field_ba,
            site_index_m=site_index_m,
        )
        diameter_limit_overstorey = 1.8 * (dominant_mean + 8.0) if dominant_mean > 0 else 1.0e6

        ts = _resolve_temperature_sum(site, ctx)
        veg = (
            float(site.field_layer.value.index)
            if site is not None and site.field_layer is not None
            else float(ctx.attrs.get("vegetation_index", 0.0))
        )
        moist = int(site is not None and site.soil_moisture == Sweden.SoilMoistureEnum.MOIST)
        wet = int(site is not None and site.soil_moisture == Sweden.SoilMoistureEnum.WET)
        peat = int(
            site is not None
            and site.soil_texture in {Sweden.SoilTextureSediment.PEAT, Sweden.SoilTextureTill.PEAT}
        )
        ditch = int(site is not None and bool(site.ditched))
        split, edge = _split_edge_flags(ctx)
        fert = _fertilization_flag(ctx)
        thinned_0_10_years_flag, thinned_10_30_years_flag = _thinning_flags(
            ctx, self.config.include_thinning_effect
        )

        surrounding_basal_area = field_ba if ctx.state.get("t", 0.0) <= 0.0 else basal_area_all
        ln_relative_basal_area = (
            log(basal_area_all / surrounding_basal_area) if surrounding_basal_area > 0 else 0.0
        )

        # Pre-compute group proportions for stand growth (all trees)
        group_ba = {"pine": 0.0, "spruce": 0.0, "birch": 0.0}
        for tree, exp_factor in zip(trees, expansions, strict=False):
            d = float(getattr(tree, "diameter_cm", 0.0) or 0.0)
            if d <= 0:
                continue
            ba_m2_ha = (
                diameter_to_basal_area_cm2(d)
                * 1.0e-4
                * float(getattr(tree, "weight_n", 1.0) or 1.0)
                * exp_factor
            )
            group = _species_group(tree.species)
            if group == "pine":
                group_ba["pine"] += ba_m2_ha
            elif group == "spruce":
                group_ba["spruce"] += ba_m2_ha
            elif group == "birch":
                group_ba["birch"] += ba_m2_ha

        pine_share = group_ba["pine"] / basal_area_all if basal_area_all > 0 else 0.0
        spruce_share = group_ba["spruce"] / basal_area_all if basal_area_all > 0 else 0.0
        birch_share = group_ba["birch"] / basal_area_all if basal_area_all > 0 else 0.0
        birch_share_sq = birch_share**2
        birch_share_cold = birch_share * exp(-0.01 * (ts - 300.0))

        # Tree growth sum (5-year) by layer
        tree_growth_by_layer = {True: 0.0, False: 0.0}
        for tree, inc, exp_factor in zip(trees, base_increments, expansions, strict=False):
            d = float(getattr(tree, "diameter_cm", 0.0) or 0.0)
            if d <= 0 or inc <= 0 or d < self.config.stand_growth_min_diameter_cm:
                continue
            overstorey = (
                bool(tree.is_overstorey)
                if tree.is_overstorey is not None
                else d > diameter_limit_overstorey
            )
            if tree.is_overstorey is None:
                tree.is_overstorey = overstorey
            ba_growth_cm2 = diameter_growth_to_basal_area_growth_cm2(d, inc)
            mortality = float(getattr(tree, "mortality", 0.0) or 0.0)
            w = float(getattr(tree, "weight_n", 1.0) or 1.0)
            tree_growth_by_layer[overstorey] += (
                ba_growth_cm2 * w * exp_factor * (1.0 - mortality) * 1.0e-4
            )

        # Stand growth and adjustment per layer
        stand_growth_by_layer = {True: 0.0, False: 0.0}
        for overstorey in (True, False):
            ba_sum = 0.0
            age_sum = 0.0
            basal_area_measured = 0.0
            stems_measured = 0.0
            for tree, exp_factor in zip(trees, expansions, strict=False):
                d = float(getattr(tree, "diameter_cm", 0.0) or 0.0)
                if d <= 0 or d <= self.config.stand_growth_min_diameter_cm:
                    continue
                tree_overstorey = (
                    bool(tree.is_overstorey)
                    if tree.is_overstorey is not None
                    else d > diameter_limit_overstorey
                )
                if tree_overstorey != overstorey:
                    continue
                w = float(getattr(tree, "weight_n", 1.0) or 1.0)
                ba = diameter_to_basal_area_cm2(d) * 1.0e-4 * w * exp_factor
                ba_sum += ba
                age_total = _tree_age_total_years(
                    tree=tree,
                    site_index_m=site_index_m,
                    latitude_deg=lat,
                    default_species=TreeSpecies.Sweden.pinus_sylvestris,
                )
                age_sum += ba * age_total
                mortality = float(getattr(tree, "mortality", 0.0) or 0.0)
                basal_area_measured += ba * (1.0 - mortality)
                if d >= 4.0:
                    stems_measured += w * exp_factor * (1.0 - mortality)

            mean_age_layer = age_sum / ba_sum if ba_sum > 0 else 0.0
            ln_mean_age = log(max(10.0, mean_age_layer)) if mean_age_layer > 0 else log(10.0)
            conifer_share_per_age = (
                (pine_share + spruce_share) / mean_age_layer if mean_age_layer > 0 else 0.0
            )
            stem_number_factor = (
                stems_measured / (stems_measured + 80.0) if stems_measured > 0 else 0.0
            )

            stand_growth_by_layer[overstorey] = stand_basal_area_growth_elfving_2009(
                ln_mean_age=ln_mean_age,
                conifer_share_per_age=conifer_share_per_age,
                pine_share_times_veg=pine_share * veg,
                birch_share_sq=birch_share_sq,
                birch_share_cold=birch_share_cold,
                basal_area_survived_m2_ha=basal_area_measured,
                basal_area_all_m2_ha=basal_area_all,
                stem_number_factor=stem_number_factor,
                veg=veg,
                peat=peat,
                moist=moist,
                wet=wet,
                site_index_m=site_index_adj,
                ditch=ditch,
                fertilized=fert,
                edge=edge,
                split=split,
                thinned_0_10_years_flag=thinned_0_10_years_flag,
                thinned_10_30_years_flag=thinned_10_30_years_flag,
                ln_relative_basal_area=ln_relative_basal_area,
                pine_share=pine_share,
                spruce_share=spruce_share,
                use_edge_effects=self.config.use_edge_effects,
            )

        # Elfving (2009) continuous thinning-response multiplier on basal-area growth
        # (1.0 unless a thinning has been simulated with include_thinning_effect).
        thinning_factor = self._thinning_response_factor(ctx, spruce_share)

        # Apply calibration and update diameters
        for tree, inc in zip(trees, base_increments, strict=False):
            d = float(getattr(tree, "diameter_cm", 0.0) or 0.0)
            if d <= 0:
                continue
            overstorey = (
                bool(tree.is_overstorey)
                if tree.is_overstorey is not None
                else d > diameter_limit_overstorey
            )
            layer_tree_growth = tree_growth_by_layer[overstorey]
            stand_growth = stand_growth_by_layer[overstorey]
            if layer_tree_growth <= 0:
                adj_inc = inc
            else:
                ratio = min(2.0, stand_growth / layer_tree_growth)
                ba_growth_cm2 = diameter_growth_to_basal_area_growth_cm2(d, inc)
                if d >= self.config.stand_growth_min_diameter_cm:
                    ba_growth_cm2 *= ratio
                adj_inc = basal_area_growth_cm2_to_diameter_growth_cm(d, ba_growth_cm2)

            if thinning_factor != 1.0 and adj_inc > 0.0:
                ba_growth_cm2 = (
                    diameter_growth_to_basal_area_growth_cm2(d, adj_inc) * thinning_factor
                )
                adj_inc = basal_area_growth_cm2_to_diameter_growth_cm(d, ba_growth_cm2)

            tree.diameter_cm = float(d) + adj_inc * scale

    # ------------------------------------------------------------------
    # Aggregate mode
    # ------------------------------------------------------------------

    def _update_aggregate(
        self,
        ctx: SimulationContext,
        site: SwedishSite | None,
        scale: float,
    ) -> None:
        """Update aggregate inventory metrics using stand-level Elfving 2009 growth."""
        metrics = ctx.metrics
        ba_total = float(metrics["BasalArea"].get("TOTAL", 0.0))
        stems_total = float(metrics["Stems"].get("TOTAL", 0.0))
        if ba_total <= 0 or stems_total <= 0:
            return

        # Require species-level BA metrics
        species_ba = {k: v for k, v in metrics["BasalArea"].items() if k != "TOTAL"}
        if not species_ba:
            raise ValueError("Aggregate Elfving requires species-level basal area metrics.")

        # Mean age is required for stand growth
        mean_age_total = ctx.attrs.get("mean_age_total_years")
        if mean_age_total is None:
            raise ValueError("mean_age_total_years is required for aggregate Elfving.")
        mean_age_total = float(mean_age_total)

        # Compute proportions by group (approx. using basal area)
        pine_ba = spruce_ba = birch_ba = contorta_ba = 0.0
        for sp, ba in species_ba.items():
            sp_name = sp if isinstance(sp, TreeName) else None
            if sp_name in _PINE_SPECIES:
                pine_ba += float(ba)
                if sp_name is TreeSpecies.Sweden.pinus_contorta:
                    contorta_ba += float(ba)
            elif sp_name in _SPRUCE_SPECIES:
                spruce_ba += float(ba)
            elif sp_name in _BIRCH_SPECIES:
                birch_ba += float(ba)

        pine_share = pine_ba / ba_total if ba_total > 0 else 0.0
        spruce_share = spruce_ba / ba_total if ba_total > 0 else 0.0
        birch_share = birch_ba / ba_total if ba_total > 0 else 0.0

        ts = _resolve_temperature_sum(site, ctx)
        veg = (
            float(site.field_layer.value.index)
            if site is not None and site.field_layer is not None
            else float(ctx.attrs.get("vegetation_index", 0.0))
        )
        moist = int(site is not None and site.soil_moisture == Sweden.SoilMoistureEnum.MOIST)
        wet = int(site is not None and site.soil_moisture == Sweden.SoilMoistureEnum.WET)
        peat = int(
            site is not None
            and site.soil_texture in {Sweden.SoilTextureSediment.PEAT, Sweden.SoilTextureTill.PEAT}
        )
        ditch = int(site is not None and bool(site.ditched))
        split, edge = _split_edge_flags(ctx)
        fert = _fertilization_flag(ctx)
        thinned_0_10_years_flag, thinned_10_30_years_flag = _thinning_flags(
            ctx, self.config.include_thinning_effect
        )

        site_index_m = _resolve_site_index_m(
            site=site,
            ctx=ctx,
            pine_ba=pine_ba,
            spruce_ba=spruce_ba,
        )
        site_index_adj = site_index_m
        if contorta_ba > 0 and ba_total > 0:
            site_index_adj += 3.0 * contorta_ba / ba_total
        site_index_adj *= self.config.site_index_adjustment_factor

        field_ba = _field_estimated_basal_area_m2_ha(ctx)
        if field_ba is None or field_ba <= 0:
            field_ba = ba_total

        surrounding_basal_area = field_ba if ctx.state.get("t", 0.0) <= 0.0 else ba_total
        ln_relative_basal_area = (
            log(ba_total / surrounding_basal_area) if surrounding_basal_area > 0 else 0.0
        )

        stand_growth = stand_basal_area_growth_elfving_2009(
            ln_mean_age=log(max(10.0, mean_age_total)),
            conifer_share_per_age=(pine_share + spruce_share) / mean_age_total
            if mean_age_total > 0
            else 0.0,
            pine_share_times_veg=pine_share * veg,
            birch_share_sq=birch_share**2,
            birch_share_cold=birch_share * exp(-0.01 * (ts - 300.0)),
            basal_area_survived_m2_ha=ba_total,
            basal_area_all_m2_ha=ba_total,
            stem_number_factor=stems_total / (stems_total + 80.0) if stems_total > 0 else 0.0,
            veg=veg,
            peat=peat,
            moist=moist,
            wet=wet,
            site_index_m=site_index_adj,
            ditch=ditch,
            fertilized=fert,
            edge=edge,
            split=split,
            thinned_0_10_years_flag=thinned_0_10_years_flag,
            thinned_10_30_years_flag=thinned_10_30_years_flag,
            ln_relative_basal_area=ln_relative_basal_area,
            pine_share=pine_share,
            spruce_share=spruce_share,
            use_edge_effects=self.config.use_edge_effects,
        )

        # Elfving (2009) continuous thinning-response multiplier (1.0 if not thinned).
        stand_growth *= self._thinning_response_factor(ctx, spruce_share)

        ba_new = ba_total + stand_growth * scale
        if ba_new < 0:
            ba_new = 0.0

        # Scale species-level basal areas to preserve proportions.
        scale_ba = ba_new / ba_total

        new_ba_dict: dict[TreeName | str, StandBasalArea] = {}
        for key, ba in ctx._metrics["BasalArea"].items():
            if key == "TOTAL":
                continue
            new_val = float(ba) * scale_ba
            new_ba_dict[key] = StandBasalArea(
                new_val,
                species=getattr(ba, "species", None),
                precision=getattr(ba, "precision", 0.0),
                over_bark=getattr(ba, "over_bark", True),
                direct_estimate=getattr(ba, "direct_estimate", True),
            )

        new_ba_dict["TOTAL"] = StandBasalArea(
            ba_new, species=None, precision=0.0, over_bark=True, direct_estimate=True
        )

        # Preserve stems
        new_stems_dict = dict(ctx._metrics["Stems"])
        new_stems_dict["TOTAL"] = Stems(stems_total, species=None, precision=0.0)

        # Recompute QMD
        new_qmd_dict: dict[TreeName | str, QuadraticMeanDiameter] = {}
        for key, ba in new_ba_dict.items():
            stems = new_stems_dict.get(key)
            if stems is None or float(stems) <= 0 or float(ba) <= 0:
                continue
            qmd_val = sqrt((40000.0 * float(ba)) / (3.141592653589793 * float(stems)))
            new_qmd_dict[key] = QuadraticMeanDiameter(qmd_val)

        ctx._metrics = {
            "BasalArea": new_ba_dict,
            "Stems": new_stems_dict,
            "QMD": {k: v for k, v in new_qmd_dict.items()},
        }


__all__ = [
    "Elfving2010Config",
    "Elfving2010Model",
    "stand_basal_area_growth_elfving_2009",
    "pine_ln_d2_growth",
    "spruce_ln_d2_growth",
    "birch_ln_d2_growth",
    "aspen_ln_d2_growth",
    "beech_ln_d2_growth",
    "oak_ln_d2_growth",
    "precious_ln_d2_growth",
    "trivial_ln_d2_growth",
]


DESCRIPTOR = FormulaDescriptor(
    component_id="elfving_2010_model",
    source=SourceReference(
        author="Elfving, B.",
        year=2010,
        title="Growth modelling in the Heureka system",
        note=(
            "The single-tree diameter functions are from Elfving (2010), "
            "'Growth modelling in the Heureka system' (tracing to Elfving 2003). "
            "The stand-level basal-area growth function is Elfving (2009)."
        ),
    ),
    kind="model",
    domain="growth",
    composes=("elfving_2010_growth",),
    kernel_names=("Elfving2010Model",),
)
