"""Composite Sweden stand-simulation preset for Elfving/Nyström workflows.

This preset composes published models into a deterministic, 5-year stepping
pipeline (parameterized to reproduce the Heureka system's published behaviour):

1. Regeneration quality from the published Elfving regeneration functions
   (Elfving 1992 stocking SLH + Elfving 1982 young-stand quality W/ASINW).
2. NYSKOG stand creation from regeneration outputs.
3. Young-stand growth with Nyström (2000) + Nyström/Söderberg (1987).
4. Mature-tree forecasting with Elfving (2010), including stand-level correction.
5. Standing valuation using Söderberg (1992) bark/height and Mellanskog (2013) prices.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from pyforestry.base.contracts import Describable, SourceReference
from pyforestry.base.helpers import CircularPlot, Stand, Tree
from pyforestry.base.helpers.primitives import Age, SiteIndexValue
from pyforestry.base.helpers.tree import TreeUid
from pyforestry.base.helpers.tree_species import TreeName, TreeSpecies
from pyforestry.base.pricelist import Pricelist, SolutionCube, create_pricelist_from_data
from pyforestry.base.simulation.core import SimulationContext
from pyforestry.base.simulation.pipeline import Step
from pyforestry.base.timber_bucking.nasberg_1985 import BuckingConfig, Nasberg_1985_BranchBound
from pyforestry.simulation.services import RandomBundle
from pyforestry.sweden.adapters.elfving_1982 import (
    HuginMeanHeightModel,
    NfiRegion,
    NyskogReconstruction,
    RegenerationType,
)
from pyforestry.sweden.adapters.elfving_2010 import Elfving2010Inputs, Elfving2010Model
from pyforestry.sweden.bark.soderberg_1992 import soderberg_1992_bark_thickness_bh_mm
from pyforestry.sweden.height.nystrom_2000 import sapling_height_growth_m
from pyforestry.sweden.height.soderberg_1992 import soderberg_1992_height_tree_age_m
from pyforestry.sweden.ingrowth.wikberg_2004 import (
    IngrowthSpeciesGroup,
    ingrowth_predict,
    ingrowth_to_plot_trees,
)
from pyforestry.sweden.mortality.naslund_1986 import (
    Naslund1986DamageModel,
    SaplingSpeciesGroup,
)
from pyforestry.sweden.mortality.types import MortalityRealizationMode, MortalityTreeModel
from pyforestry.sweden.pricelist.data.mellanskog_2013 import MELLANSKOG_2013_PRICE_DATA
from pyforestry.sweden.regeneration.elfving_1992 import Elfving1992Regeneration
from pyforestry.sweden.simulation.mortality import (
    MortalityConfig,
    MortalityContext,
    MortalityEngine,
    MortalityHistoryConditions,
    MortalitySiteConditions,
    MortalityStandConditions,
    MortalityTreeRecord,
)
from pyforestry.sweden.simulation.presets import valuation_cube
from pyforestry.sweden.site import Sweden, SwedishSite
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970
from pyforestry.sweden.systems.nystrom_soderberg_1987 import NystromSoderberg1987
from pyforestry.sweden.taper import EdgrenNylinder1949
from pyforestry.sweden.timber import SweTimber

# Two of these three deliberately do not match the package-wide groups in
# ``pyforestry.sweden._model_input_normalization``, so do not "unify" them without
# checking: ``PINE_GROUP`` there also contains *Pinus mugo*, and ``BIRCH_GROUP``
# does not contain the ``betula`` genus group that the NYSKOG species map produces.
# ``_SPRUCE_SET`` does match, and the Söderberg pipeline imports it from here rather
# than keeping a copy -- the two have to agree, because one picks the site-index
# curve for growth and the other for reporting.
_PINE_SET = {
    TreeSpecies.Sweden.pinus_sylvestris,
    TreeSpecies.Sweden.pinus_contorta,
    TreeSpecies.Sweden.larix_sibirica,
    TreeSpecies.Sweden.larix_decidua,
    TreeSpecies.Sweden.larix_europaea_x_leptolepis,
    TreeSpecies.Sweden.larix_sukaczewii,
}
_LARCH_SET = {
    TreeSpecies.Sweden.larix_sibirica,
    TreeSpecies.Sweden.larix_decidua,
    TreeSpecies.Sweden.larix_europaea_x_leptolepis,
    TreeSpecies.Sweden.larix_sukaczewii,
}
_CONTORTA_SET = {TreeSpecies.Sweden.pinus_contorta}
_SPRUCE_SET = {
    TreeSpecies.Sweden.picea_abies,
    TreeSpecies.Sweden.picea_sitchensis,
    TreeSpecies.Sweden.picea_mariana,
}
_BIRCH_SET = {
    TreeSpecies.Sweden.betula_pendula,
    TreeSpecies.Sweden.betula_pubescens,
    TreeSpecies.Sweden.betula,
}
_ASPEN_SET = {
    TreeSpecies.Sweden.populus_tremula,
    TreeSpecies.Sweden.populus_tremula_x_tremuloides,
}
_BROADLEAF_SET = {
    TreeSpecies.Sweden.betula_pendula,
    TreeSpecies.Sweden.betula_pubescens,
    TreeSpecies.Sweden.betula,
    TreeSpecies.Sweden.populus_tremula,
    TreeSpecies.Sweden.populus_tremula_x_tremuloides,
}
_NYSKOG_SPECIES_MAP = {
    "pine": TreeSpecies.Sweden.pinus_sylvestris,
    "spruce": TreeSpecies.Sweden.picea_abies,
    "contorta": TreeSpecies.Sweden.pinus_contorta,
    "larch": TreeSpecies.Sweden.larix_sibirica,
    "birch": TreeSpecies.Sweden.betula_pendula,
    # Keep broadleaf valuation/bucking compatible with available price/timber support.
    "other_broadleaf": TreeSpecies.Sweden.betula_pubescens,
}


def _to_ingrowth_species(species: TreeName | None) -> IngrowthSpeciesGroup:
    """Map a tree species to the Wikberg 2004 ingrowth species group."""
    if species in _PINE_SET:
        return IngrowthSpeciesGroup.PINE
    if species in _SPRUCE_SET:
        return IngrowthSpeciesGroup.SPRUCE
    if species in _BIRCH_SET:
        return IngrowthSpeciesGroup.BIRCH
    if species in _ASPEN_SET:
        return IngrowthSpeciesGroup.OTHER_BROADLEAF
    return IngrowthSpeciesGroup.OTHER_BROADLEAF


@dataclass(frozen=True)
class Elfving2010PipelineConfig:
    """Configuration for the Elfving 2010 composite preset."""

    regeneration_type: RegenerationType = RegenerationType.NATURAL
    species_to_plant: TreeName = TreeSpecies.Sweden.pinus_sylvestris
    nfi_region: NfiRegion = NfiRegion.REG3
    site_index_pine_m: float = 20.0
    site_index_spruce_m: float = 22.0
    initial_age_years: float = 12.0
    sample_trees: int = 120
    random_seed: int = 42
    deterministic: bool = True
    handover_dbh_cm: float = 10.0
    handover_mean_height_m: float = 7.0
    handover_smoothing_width_m: float = 1.0
    dt_years: float = 5.0
    regeneration_seed_trees_per_ha: float = 150.0
    regeneration_plant_count_per_ha: float | None = None
    regeneration_ground_prepared: bool = True
    regeneration_burnt: bool = False
    regeneration_area_ha: float = 1.0
    use_naslund_damage_index: bool = True
    use_naslund_damage_mortality: bool = True
    naslund_damage_mortality_scale: float = 1.0
    naslund_moose_factor: float = 1.0
    naslund_vole_factor: float = 1.0
    naslund_snow_break_factor: float = 1.0
    naslund_whip_factor: float = 1.0
    naslund_frost_factor: float = 1.0
    naslund_snow_blight_factor: float = 1.0
    naslund_other_factor: float = 1.0
    apply_ingrowth: bool = False
    ingrowth_deterministic: bool = True
    ingrowth_min_mean_age_years: float = 50.0
    apply_mortality: bool = True
    mortality_tree_model: MortalityTreeModel = MortalityTreeModel.ELFVING_2013
    mortality_config: MortalityConfig | None = None
    temperature_sum_dd: float | None = None
    valuation_region: str | None = None
    valuation_use_solution_cube: bool = True
    valuation_solution_cube_path: str | None = None
    valuation_solution_cube_autogenerate_if_missing: bool = False
    valuation_solution_cube_generate_workers: int = -1
    valuation_solution_cube_generate_dbh_range_cm: tuple[float, float] = (10.0, 40.0)
    valuation_solution_cube_generate_height_range_m: tuple[float, float] = (8.0, 30.0)
    valuation_solution_cube_generate_dbh_step_cm: int = 5
    valuation_solution_cube_generate_height_step_m: float = 2.0
    valuation_cube_dbh_step_cm: float = 1.0
    valuation_cube_height_step_m: float = 0.5
    valuation_cube_bark_step_mm: float = 1.0


@dataclass
class _ValuationTotals:
    """What a standing-forest valuation adds up to, in one shape.

    There are two valuation routes: bucked assortments priced through Näsberg
    (1985), and whole-stem volume priced as pulpwood. They used to return two
    different dicts -- six keys and four -- and :meth:`Elfving2010Pipeline._snapshot_row`
    covered the difference with ``.get(key, 0.0)``, so a run that priced every cubic
    metre as pulpwood reported nought pulp volume in its own report. Both routes
    fill this now, and a route that cannot produce a figure says so by leaving it
    zero rather than by omitting it.
    """

    value_sek_per_ha: float = 0.0
    volume_m3_per_ha: float = 0.0
    timber_volume_m3_per_ha: float = 0.0
    pulp_volume_m3_per_ha: float = 0.0
    #: Stems whose value came from a *bucking* solution. Zero for a route that does
    #: not buck, which is a fact about the route rather than a missing number.
    timber_valued_stems_per_ha: float = 0.0

    def as_row(self) -> dict[str, float]:
        """Return the reporting keys, with the unit value derived once.

        Returns:
            The six figures a projection row carries, whichever route produced them.
        """
        return {
            "standing_value_sek_per_ha": self.value_sek_per_ha,
            "standing_volume_m3_per_ha": self.volume_m3_per_ha,
            "timber_volume_m3_per_ha": self.timber_volume_m3_per_ha,
            "pulp_volume_m3_per_ha": self.pulp_volume_m3_per_ha,
            "value_per_m3_sek": (
                self.value_sek_per_ha / self.volume_m3_per_ha if self.volume_m3_per_ha > 0 else 0.0
            ),
            "timber_valued_stems_per_ha": self.timber_valued_stems_per_ha,
        }


@dataclass
class Elfving2010PeriodRecord:
    """What one period produced, written by the phases that produced it.

    These are results, not state. They used to be five ``_last_*`` attributes on the
    pipeline, assigned from thirty-eight places -- a return value turned into an
    instance variable. Nothing said when one was valid, so a phase that did not run
    left the previous period's figures standing and :meth:`Elfving2010Pipeline._snapshot_row`
    reported them as this period's. A record is built fresh each period, so a phase
    that does nothing reports its zero rather than last time's number.

    Two of the fields are not reported but carried: the young-tree set and their
    post-Nyström diameters are what the phase-over blend needs from the young phase,
    and the mature growth step runs between the two.
    """

    #: Trees below the handover DBH when the period started. The height/bark phase
    #: recomputes its own set from the end-of-period stand, so this one is only the
    #: young phase's own view.
    young_uids: frozenset[TreeUid] = field(default_factory=frozenset)
    #: Each young tree's DBH after the Nyström phase grew it and before the Elfving
    #: step overwrote it. The blend needs both trajectories to interpolate between.
    young_dbh_after_nystrom: dict[TreeUid, float] = field(default_factory=dict)
    #: Weight given to the mature (Elfving) DBH trajectory this period, from the
    #: stand's mean height. Measured after the young phase grew the heights.
    phase_over_weight: float = 0.0
    #: Mean Näslund (1986) damage index over the young trees, or zero with none.
    damage_index_mean: float = 0.0
    #: Stems/ha the Näslund damage pathway removed from the young trees.
    damage_mortality_stems_per_ha: float = 0.0
    #: Mean predicted per-tree mortality fraction for the period.
    mortality_fraction_mean: float = 0.0
    #: Stems/ha the realisation phase actually removed.
    mortality_stems_removed_per_ha: float = 0.0


# ---------------------------------------------------------------------------
# The phases of one period
#
# Each is a :class:`~pyforestry.base.simulation.pipeline.Step`: it takes the run's
# context and a period length, and advances the whole stand. They are bound to the
# pipeline because the state they work on -- the config, the site, the composed
# submodels -- is the pipeline's; what the *runtime* sees is an ordered tuple it can
# read, which is what `step()` hand-coded in one 65-line method before.
#
# The order is part of the model, not an implementation detail, so each step below
# says what it must come after and why. Reordering them changes the numbers.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _PipelineStep:
    """Base for the phases: a step bound to the pipeline whose stand it advances."""

    pipeline: "Elfving2010Pipeline"


@dataclass(frozen=True)
class _BeginPeriodStep(_PipelineStep):
    """Open a fresh :class:`Elfving2010PeriodRecord` for the period.

    First, so that every figure the snapshot row reports is this period's. It is a
    step rather than something ``step()`` does around the loop so that the tuple is
    self-contained: driven through
    :func:`~pyforestry.base.simulation.pipeline.run_pipeline`, it resets per period
    just the same.
    """

    name: str = "begin_period"

    def run(self, ctx: SimulationContext, dt: float) -> None:
        """Discard the previous period's results."""
        self.pipeline._record = Elfving2010PeriodRecord()


@dataclass(frozen=True)
class _YoungStandGrowthStep(_PipelineStep):
    """Grow the trees still below the handover DBH with Nyström (2000).

    First of the growth phases, because it decides which trees are young *before*
    the Elfving step moves any diameters, and because the phase-over blend later in
    the period interpolates between the diameter this phase produced and the one the
    Elfving step produces from the same starting point. Both are recorded here for
    it.

    The mature-phase weight is also measured here rather than at the blend, because
    it comes from the stand's mean height and this is the phase that changes heights.
    """

    name: str = "young_stand_growth"

    def run(self, ctx: SimulationContext, dt: float) -> None:
        """Apply Nyström height and DBH growth, then record what the blend needs."""
        pipeline = self.pipeline
        record = pipeline._record
        record.young_uids = frozenset(pipeline._young_tree_ids(pipeline._trees))
        pipeline._apply_nystrom_young_growth(
            young_ids=set(record.young_uids),
            dt_years=dt,
        )
        record.young_dbh_after_nystrom = {
            tree.uid: float(tree.diameter_cm or 0.0)
            for tree in pipeline._trees
            if tree.uid in record.young_uids
        }
        record.phase_over_weight = pipeline._phase_over_weight(
            pipeline._weighted_mean_height_m(pipeline._trees),
        )


@dataclass(frozen=True)
class _MortalityPredictionStep(_PipelineStep):
    """Predict the period's mortality onto ``tree.mortality``, removing nothing.

    Before growth, and that is load-bearing. The Elfving stand calibration inside
    the mature step multiplies each tree's growth by ``1 - tree.mortality``, so it
    calibrates on survived rather than gross basal area. Predicting after growth
    would calibrate the stand against stems that do not survive the period.
    The stems themselves come out in :class:`_MortalityRealizationStep`, after
    growth.
    """

    name: str = "mortality_prediction"

    def run(self, ctx: SimulationContext, dt: float) -> None:
        """Store per-tree mortality fractions for this period."""
        pipeline = self.pipeline
        if pipeline.config.apply_mortality:
            pipeline._predict_mortality(dt_years=dt)
            return
        for tree in pipeline._trees:
            tree.mortality = 0.0


@dataclass(frozen=True)
class _SyncModelViewStep(_PipelineStep):
    """Re-read the stand into the context the growth model steps.

    Placed twice: once before the mature step, because by then the young phase has
    grown diameters and dropped damaged stems and the model's basal area and
    dominant species have to be the current ones; and once at the end of the period,
    so the context a caller inspects afterwards agrees with the stand.
    """

    name: str = "sync_model_view"

    def run(self, ctx: SimulationContext, dt: float) -> None:
        """Refresh the stand's metrics and the model's resolved inputs."""
        self.pipeline._refresh_model_view()


@dataclass(frozen=True)
class _MatureGrowthStep(_PipelineStep):
    """Advance every tree with the mature growth model for the period.

    Elfving (2010) single-tree diameter increment plus the Elfving (2009)
    whole-stand basal-area calibration; the Söderberg pipeline swaps the model and
    keeps everything around it.
    """

    name: str = "mature_growth"

    def run(self, ctx: SimulationContext, dt: float) -> None:
        """Run the context's growth model over the whole stand."""
        ctx.update_step(dt)


@dataclass(frozen=True)
class _PhaseOverBlendStep(_PipelineStep):
    """Blend each young tree's two diameters into one.

    Immediately after the mature step, which is the only moment both trajectories
    exist: the young diameter is in the record, the mature one is on the tree, and
    the next phase to touch diameters would see only the blend.
    """

    name: str = "phase_over_blend"

    def run(self, ctx: SimulationContext, dt: float) -> None:
        """Interpolate young and mature DBH at this period's phase-over weight."""
        pipeline = self.pipeline
        record = pipeline._record
        for tree in pipeline._trees:
            young_dbh_cm = record.young_dbh_after_nystrom.get(tree.uid)
            if young_dbh_cm is None:
                continue
            tree.diameter_cm = pipeline._blend_phase_over_dbh(
                young_dbh_cm=float(young_dbh_cm),
                mature_dbh_cm=float(tree.diameter_cm or 0.0),
                mature_weight=float(record.phase_over_weight),
            )


@dataclass(frozen=True)
class _MortalityRealizationStep(_PipelineStep):
    """Take out the stems :class:`_MortalityPredictionStep` marked.

    After growth, because the growth the stand calibration produced was already
    calibrated on the survivors; removing them earlier would take the same stems out
    twice.
    """

    name: str = "mortality_realization"

    def run(self, ctx: SimulationContext, dt: float) -> None:
        """Scale weights by the survived fraction and drop emptied trees."""
        if self.pipeline.config.apply_mortality:
            self.pipeline._realize_mortality()


@dataclass(frozen=True)
class _AgeAdvanceStep(_PipelineStep):
    """Advance the trees' breast-height ages and the pipeline's clock.

    After mortality so the trees that died do not age first, and before ingrowth so
    the recruits this period produces start at their own age rather than being aged
    for a period they were not alive for.
    """

    name: str = "age_advance"

    def run(self, ctx: SimulationContext, dt: float) -> None:
        """Add ``dt`` years to every tree age and to the stand's own two counters."""
        pipeline = self.pipeline
        pipeline._increment_tree_ages(dt)
        pipeline._years_elapsed += dt
        pipeline._current_age_years += dt


@dataclass(frozen=True)
class _IngrowthStep(_PipelineStep):
    """Recruit new trees with Wikberg (2004), if the config asks for it.

    After mortality and the age advance, because the model is gated on the stand's
    QMD and mean age and those are the end-of-period ones; before height and bark,
    which is what gives the recruits theirs.
    """

    name: str = "ingrowth"

    def run(self, ctx: SimulationContext, dt: float) -> None:
        """Add the period's recruits to the stand."""
        if self.pipeline.config.apply_ingrowth:
            self.pipeline._apply_ingrowth()


@dataclass(frozen=True)
class _HeightAndBarkStep(_PipelineStep):
    """Refresh heights and double bark thickness with Söderberg (1992).

    Last, because it is a function of the end-of-period diameter, age and stand
    structure -- so it has to see the diameters growth and the blend produced, the
    ages the age step advanced, and the trees ingrowth added. Trees still in the
    young phase keep the height Nyström gave them, or the blend would be damped by
    a mature height function evaluated on a sapling.
    """

    name: str = "height_and_bark"

    def run(self, ctx: SimulationContext, dt: float) -> None:
        """Impute mature heights and bark, preserving young-phase heights."""
        pipeline = self.pipeline
        pipeline._apply_soderberg_height_and_bark(
            fallback_age_years=pipeline._current_age_years,
            preserve_height_tree_ids=pipeline._young_tree_ids(pipeline._trees),
        )


class Elfving2010Pipeline:
    """Stateful simulation preset combining NYSKOG, Nyström and Elfving 2010."""

    def __init__(self, config: Elfving2010PipelineConfig | None = None) -> None:
        """Initialize with optional config overrides."""
        self.config = config or Elfving2010PipelineConfig()
        self._pricelist: Pricelist = create_pricelist_from_data(MELLANSKOG_2013_PRICE_DATA)
        self._model = Elfving2010Model()
        self._mortality_engine = MortalityEngine(config=self._build_mortality_config())
        self._site: SwedishSite | None = None
        self._ctx: SimulationContext | None = None
        self._trees = []
        self._current_age_years: float = self.config.initial_age_years
        self._years_elapsed: float = 0.0
        self._rng = RandomBundle(int(self.config.random_seed)).rng_for()
        self._regen_asinw: float = 0.0
        self._regen_q: float = 0.0
        self._record = Elfving2010PeriodRecord()
        self._steps: tuple[Step, ...] = self._build_steps()
        self._valuation_solution_cube: SolutionCube | None = None
        self._valuation_lookup_cache: dict[
            tuple[str, int, int, int, str], tuple[float, float, bool]
        ] = {}

    def _build_steps(self) -> tuple[Step, ...]:
        """Return the phases of one period, in the order they run.

        This is the whole schedule, as data. It used to be sixty-five lines of
        ``step()`` with the ordering carried by statement order and one comment;
        each phase now states in its own docstring what it must follow and why,
        because the order is part of the model rather than an implementation
        detail.
        """
        return (
            _BeginPeriodStep(self),
            _YoungStandGrowthStep(self),
            _MortalityPredictionStep(self),
            _SyncModelViewStep(self),
            _MatureGrowthStep(self),
            _PhaseOverBlendStep(self),
            _MortalityRealizationStep(self),
            _AgeAdvanceStep(self),
            _IngrowthStep(self),
            _HeightAndBarkStep(self),
            _SyncModelViewStep(self),
        )

    @property
    def steps(self) -> tuple[Step, ...]:
        """The phases of one period, in order.

        Each is a :class:`~pyforestry.base.simulation.pipeline.Step`, so the tuple
        can be handed to :func:`~pyforestry.base.simulation.pipeline.run_pipeline`
        as well as run by :meth:`step` -- the composite and the generic runtime
        schedule the same objects rather than two look-alike orderings.
        """
        return self._steps

    @property
    def _trees(self) -> list[Tree]:
        """The stand's trees.

        Once :meth:`initialize` has built the run's context this *is* the context's
        plot list, not a copy of it: ``build_context`` copies the plot container but
        shares the ``Tree`` objects, so a phase that only grows a tree stays in sync
        either way, and a phase that adds or removes one (ingrowth, mortality) would
        not. Before there is a context it is a staging list, which is what
        ``initialize`` fills before it has anywhere to put it.

        The setter writes *through* to that list rather than replacing it, so
        ``pipeline._trees = [...]`` -- which is how a caller thins a stand -- cannot
        leave the context describing a stand that no longer exists. Keeping the two
        in step is what removed two of the three context rebuilds per period.
        """
        if self._ctx is not None:
            return self._ctx.stand.plots[0].trees
        return self._staged_trees

    @_trees.setter
    def _trees(self, trees: list[Tree]) -> None:
        """Replace the tree list, in place where the context owns it."""
        if self._ctx is not None:
            self._ctx.stand.plots[0].trees[:] = trees
            return
        self._staged_trees: list[Tree] = list(trees)

    # --- Introspection (Describable) ---

    @property
    def component_id(self) -> str:
        """Stable identifier for the Elfving 2010 composite preset."""
        return "elfving_2010_composite"

    @property
    def source(self) -> SourceReference:
        """Bibliographic provenance for this composite preset."""
        return SourceReference(
            author="Elfving, B.",
            year=2010,
            title="Growth modelling in the Heureka system",
            note="Provenance of the growth model this preset projects with. The "
            "preset itself is a pyforestry composition and carries no separate "
            "publication: alongside Elfving (2010) it draws on Elfving (1982)/NYSKOG "
            "reconstruction, Nyström (2000) & Nyström-Söderberg (1987) young-stand, "
            "Elfving (2013) mortality, Söderberg (1992) bark/height, Elfving "
            "(1992/1982) regeneration and Mellanskog (2013) prices. See `components` "
            "for each model's own provenance.",
        )

    @property
    def components(self) -> Sequence[Describable]:
        """Describable components composed by this preset."""
        return (
            self._model,  # Elfving2010Model (Describable)
            self._mortality_engine,  # MortalityEngine -- not yet Describable, skipped at runtime
        )

    # --- State access ---

    @property
    def tree_list(self) -> list[Tree]:
        """Return the current in-memory tree list."""
        return self._trees

    @property
    def current_age_years(self) -> float:
        """Return current stand age at breast height in years."""
        return self._current_age_years

    @property
    def years_elapsed(self) -> float:
        """Return years elapsed since preset initialization."""
        return self._years_elapsed

    def _build_mortality_config(self) -> MortalityConfig:
        """Build mortality run configuration with deterministic defaults."""
        base = self.config.mortality_config
        if base is not None:
            return replace(
                base,
                period_years=float(self.config.dt_years),
                stochastic_seed=self.config.random_seed,
            )
        return MortalityConfig(
            implementation_type=(
                MortalityRealizationMode.DETERMINISTIC
                if self.config.deterministic
                else MortalityRealizationMode.STOCHASTIC
            ),
            tree_model=self.config.mortality_tree_model,
            period_years=float(self.config.dt_years),
            stochastic_seed=self.config.random_seed,
        )

    def initialize(self, *, site: SwedishSite) -> list[Tree]:
        """Build an initial stand from regeneration quality + NYSKOG reconstruction."""
        self._site = site
        self._current_age_years = self.config.initial_age_years
        self._years_elapsed = 0.0
        self._rng = RandomBundle(int(self.config.random_seed)).rng_for()
        self._mortality_engine = MortalityEngine(
            config=self._build_mortality_config(),
            rng=self._rng.child("mortality").numpy,
        )
        self._record = Elfving2010PeriodRecord()
        self._valuation_lookup_cache = {}
        self._valuation_solution_cube = self._load_solution_cube()

        # Regeneration stocking (SLH): Elfving (1992), Appendix 1 Tables 1-2. The
        # Jonson productivity index is derived from the pine site index. Ground
        # preparation (markberedning) drives the report's scarification term.
        regen_h100 = SiteIndexValue(
            float(self.config.site_index_pine_m),
            reference_age=Age.TOTAL(100),
            species={TreeSpecies.Sweden.pinus_sylvestris},
            fn=Hagglund_1970.height_trajectory.pinus_sylvestris.sweden,
        )
        regeneration_type = self.config.regeneration_type
        if regeneration_type in {RegenerationType.NATURAL, RegenerationType.EXTENSIVE}:
            stocking_arcsine_radians, _slh_est, _slh_corr = Elfving1992Regeneration.slh_natural(
                latitude_deg=float(site.latitude),
                altitude_m=float(site.altitude or 0.0),
                county=site.county,
                soil_moisture=site.soil_moisture,
                h100_input=regen_h100,
                main_species=TreeSpecies.Sweden.pinus_sylvestris,
                vegetation=site.field_layer,
                seed_trees_per_ha=self.config.regeneration_seed_trees_per_ha,
                regen_area_ha=self.config.regeneration_area_ha,
                scarified=self.config.regeneration_ground_prepared,
                burnt=self.config.regeneration_burnt,
            )
        else:
            stocking_arcsine_radians, _slh_est, _slh_corr = Elfving1992Regeneration.slh_cultivated(
                latitude_deg=float(site.latitude),
                altitude_m=float(site.altitude or 0.0),
                county=site.county,
                h100_input=regen_h100,
                main_species=TreeSpecies.Sweden.pinus_sylvestris,
                vegetation=site.field_layer,
                plant_count_per_ha=self.config.regeneration_plant_count_per_ha,
                scarified=self.config.regeneration_ground_prepared,
                burnt=self.config.regeneration_burnt,
                sown=regeneration_type == RegenerationType.SOWN,
                spruce=regeneration_type == RegenerationType.SPRUCE_PLANTATION,
            )
        # Young-stand quality (ASINW / W): Elfving (1982), Hugin Rapport 27.
        self._regen_asinw = float(
            NyskogReconstruction.young_stand_quality_asinw(
                stocking_arcsine_radians=stocking_arcsine_radians,
                regeneration_type=regeneration_type,
                latitude_deg=float(site.latitude),
            )
        )
        self._regen_q = float(NyskogReconstruction.production_potential_q(self._regen_asinw))

        mean_height_main_m = HuginMeanHeightModel.mean_height(
            age_years=self.config.initial_age_years,
            species=self.config.species_to_plant,
            site_index_pine_m=self.config.site_index_pine_m,
            site_index_spruce_m=self.config.site_index_spruce_m,
        )
        nyskog = NyskogReconstruction.reconstruct_summary(
            asinw=self._regen_asinw,
            mean_height_main_m=mean_height_main_m,
            site_index_m=self._site_index_for_species(self.config.species_to_plant),
            regeneration_type=self.config.regeneration_type,
            species_to_plant=self.config.species_to_plant,
            nfi_region=self.config.nfi_region,
            field_layer=site.field_layer,
            soil_moisture=site.soil_moisture,
            deterministic=self.config.deterministic,
        )
        self._trees = self._sample_tree_list(nyskog.stems_per_species, nyskog.weibull_params)
        self._apply_initial_dbh_and_age()
        self._apply_soderberg_height_and_bark(fallback_age_years=self.config.initial_age_years)
        self._record.phase_over_weight = self._phase_over_weight(
            self._weighted_mean_height_m(self._trees)
        )
        self._build_context()
        return self._trees

    def step(self, *, dt_years: float | None = None) -> list[Tree]:
        """Advance one hybrid step with Nyström (< handover dbh) and Elfving (>= handover).

        Runs :attr:`steps` in order over the run's one context. What each phase is
        and what it must follow is on the phase; this method is the clock check and
        the loop.
        """
        if self._site is None or not self._trees:
            raise RuntimeError("Preset must be initialized before calling step().")
        dt = self.config.dt_years if dt_years is None else float(dt_years)
        if dt <= 0.0:
            raise ValueError("dt_years must be > 0.")

        for phase in self._steps:
            phase.run(self._ctx, dt)
        return self._trees

    def run_projection(
        self,
        *,
        site: SwedishSite | None = None,
        n_steps: int = 20,
        dt_years: float | None = None,
    ) -> pd.DataFrame:
        """Run a full projection and return one summary row per 5-year step."""
        if n_steps <= 0:
            raise ValueError("n_steps must be > 0.")
        if site is not None:
            self.initialize(site=site)
        elif self._site is None or not self._trees:
            raise RuntimeError("Provide site or call initialize(...) before run_projection(...).")

        dt = self.config.dt_years if dt_years is None else float(dt_years)
        if dt <= 0.0:
            raise ValueError("dt_years must be > 0.")

        rows = [self._snapshot_row(step_index=0)]
        for step_index in range(1, n_steps + 1):
            self.step(dt_years=dt)
            rows.append(self._snapshot_row(step_index=step_index))
        return pd.DataFrame.from_records(rows)

    def value_standing_forest(self, tree_list: list[Tree] | None = None) -> dict[str, float]:
        """Estimate standing value/volume for all living trees at current step.

        Volumes are under-bark throughout. For bucked trees the Nasberg 1985
        result provides per-quality volumes. For non-timber trees the Brandel/
        Andersson fallback uses ``over_bark=False`` to keep the same bark basis.
        """
        if self._site is None:
            raise RuntimeError("Preset must be initialized before valuation.")
        trees = self._trees if tree_list is None else tree_list
        totals = _ValuationTotals()
        valuation_region = self._valuation_region()

        for tree in trees:
            species = tree.species
            if species is None:
                continue
            diameter_cm = float(tree.diameter_cm or 0.0)
            height_m = float(tree.height_m or 0.0)
            weight = float(tree.weight_n or 0.0)
            if diameter_cm <= 0.0 or height_m <= 0.0 or weight <= 0.0:
                continue

            valuation_species = self._valuation_species_name(species)
            bark_mm = float(getattr(tree, "double_bark_mm", 0.0) or 0.0)
            timber = SweTimber(
                species=valuation_species,
                diameter_cm=diameter_cm,
                height_m=height_m,
                double_bark_mm=bark_mm if bark_mm > 0 else None,
                region=valuation_region,
                over_bark=False,  # Under-bark to match bucking result basis
            )

            timber_price_table = self._pricelist.Timber.get(valuation_species)
            min_timber_diameter = (
                float(timber_price_table.min_diameter)
                if timber_price_table is not None
                else float("inf")
            )
            if timber_price_table is not None and diameter_cm >= min_timber_diameter:
                cached = self._lookup_or_compute_timber_value_volume(
                    species=valuation_species,
                    diameter_cm=diameter_cm,
                    height_m=height_m,
                    bark_mm=bark_mm,
                    region=valuation_region,
                )
                if cached is not None:
                    cached_value, cached_volume, has_timber_solution = cached
                    if has_timber_solution:
                        totals.value_sek_per_ha += float(cached_value) * weight
                        totals.volume_m3_per_ha += float(cached_volume) * weight
                        totals.timber_volume_m3_per_ha += float(cached_volume) * weight
                        if cached_value > 0.0:
                            totals.timber_valued_stems_per_ha += weight
                        continue
                try:
                    bucker = Nasberg_1985_BranchBound(timber, self._pricelist, EdgrenNylinder1949)
                    result = bucker.calculate_tree_value(
                        min_diam_dead_wood=99.0,
                        config=BuckingConfig(save_sections=False),
                    )
                    vol_ub = float(result.vol_sk_ub)
                    # Extract assortment volumes from quality array
                    vq = result.volume_per_quality
                    tree_timber_vol = sum(vq[1:4])  # ButtLog + MiddleLog + TopLog
                    tree_pulp_vol = vq[4] if len(vq) > 4 else 0.0
                    totals.value_sek_per_ha += float(result.total_value) * weight
                    totals.volume_m3_per_ha += vol_ub * weight
                    totals.timber_volume_m3_per_ha += tree_timber_vol * weight
                    totals.pulp_volume_m3_per_ha += tree_pulp_vol * weight
                    totals.timber_valued_stems_per_ha += weight
                    continue
                except ValueError:
                    # Keep valuation stable for edge trees outside taper/bucking validity.
                    pass

            pulp_price = float(self._pricelist.Pulp.get_pulpwood_price(valuation_species))
            try:
                volume_m3 = float(timber.getvolume())
            except ValueError:
                continue  # Skip trees too small for volume calculation
            totals.value_sek_per_ha += volume_m3 * pulp_price * weight
            totals.volume_m3_per_ha += volume_m3 * weight
            totals.pulp_volume_m3_per_ha += volume_m3 * weight

        return totals.as_row()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sample_tree_list(
        self,
        stems_per_species: dict[str, float],
        weibull_params: dict[str, tuple[float, float]],
    ) -> list[Tree]:
        """Sample an explicit tree list from NYSKOG species-level reconstructions."""
        trees: list[Tree] = []
        total_stems = sum(float(v) for v in stems_per_species.values())
        if total_stems <= 0.0:
            return trees

        for species_key, stems_ha in stems_per_species.items():
            stems_ha = float(stems_ha)
            if stems_ha <= 0.0:
                continue
            species = _NYSKOG_SPECIES_MAP.get(species_key)
            if species is None:
                continue
            beta, shape = weibull_params.get(species_key, (0.0, 0.0))
            if beta <= 0.0 or shape <= 0.0:
                continue
            n_trees = max(1, int(round(self.config.sample_trees * stems_ha / total_stems)))
            heights = beta * self._rng.child("regeneration").numpy.weibull(shape, size=n_trees)
            weight = stems_ha / n_trees
            for height in heights:
                trees.append(
                    Tree(
                        species=species,
                        height_m=float(max(0.3, height)),
                        weight_n=float(weight),
                    )
                )
        return trees

    def _site_index_for_species(self, species: TreeName) -> float:
        """Return a species-appropriate site index from config defaults."""
        if species in _SPRUCE_SET:
            return float(self.config.site_index_spruce_m)
        return float(self.config.site_index_pine_m)

    def _temperature_sum(self) -> float:
        """Resolve temperature sum from config override or site attributes."""
        if self.config.temperature_sum_dd is not None:
            return float(self.config.temperature_sum_dd)
        if (
            self._site is not None
            and getattr(self._site, "temperature_sum_odin1983", None) is not None
        ):
            return float(self._site.temperature_sum_odin1983)
        return 1200.0

    def _valuation_region(self) -> str:
        """Resolve valuation region for SweTimber and taper model paths."""
        if self.config.valuation_region is not None:
            return self.config.valuation_region
        if self._site is not None and self._site.latitude >= 60.0:
            return "northern"
        return "southern"

    def ensure_valuation_solution_cube(
        self,
        *,
        path: str | None = None,
        overwrite: bool = False,
        workers: int | None = None,
    ) -> SolutionCube:
        """Ensure the configured cube file exists, then load it into this pipeline.

        The building and the loading live in
        :mod:`~pyforestry.sweden.simulation.presets.valuation_cube`; this method
        supplies the grid from the pipeline's config and keeps the result. It is
        the only place the pipeline touches the filesystem.
        """
        cube_path = path or self.config.valuation_solution_cube_path
        if not cube_path:
            raise ValueError("Pass `path` or set `valuation_solution_cube_path` in config.")

        resolved_path = valuation_cube.ensure_cube_file(
            path=cube_path,
            overwrite=overwrite,
            workers=(
                int(self.config.valuation_solution_cube_generate_workers)
                if workers is None
                else int(workers)
            ),
            dbh_range_cm=self.config.valuation_solution_cube_generate_dbh_range_cm,
            height_range_m=self.config.valuation_solution_cube_generate_height_range_m,
            dbh_step_cm=int(self.config.valuation_solution_cube_generate_dbh_step_cm),
            height_step_m=float(self.config.valuation_solution_cube_generate_height_step_m),
        )
        self._valuation_solution_cube = valuation_cube.load_cube(resolved_path)
        return self._valuation_solution_cube

    def _load_solution_cube(self) -> SolutionCube | None:
        """Load a precomputed solution cube when configured."""
        path = self.config.valuation_solution_cube_path
        if not path:
            return None
        if Path(path).exists():
            return valuation_cube.load_cube(path)
        if self.config.valuation_solution_cube_autogenerate_if_missing:
            return self.ensure_valuation_solution_cube(path=path, overwrite=False)
        return None

    def _valuation_lookup_key(
        self,
        *,
        species: str,
        diameter_cm: float,
        height_m: float,
        bark_mm: float,
        region: str,
    ) -> tuple[str, int, int, int, str]:
        """Build a stable cache key from rounded valuation dimensions."""
        dbh_step = max(0.1, float(self.config.valuation_cube_dbh_step_cm))
        height_step = max(0.1, float(self.config.valuation_cube_height_step_m))
        bark_step = max(0.1, float(self.config.valuation_cube_bark_step_mm))
        return (
            species,
            int(round(float(diameter_cm) / dbh_step)),
            int(round(float(height_m) / height_step)),
            int(round(max(0.0, float(bark_mm)) / bark_step)),
            region,
        )

    def _valuation_lookup_quantized_inputs(
        self,
        *,
        dbh_bin: int,
        height_bin: int,
        bark_bin: int,
    ) -> tuple[float, float, float]:
        """Return quantized DBH/height/bark values from integer bins."""
        dbh_step = max(0.1, float(self.config.valuation_cube_dbh_step_cm))
        height_step = max(0.1, float(self.config.valuation_cube_height_step_m))
        bark_step = max(0.1, float(self.config.valuation_cube_bark_step_mm))
        return (
            float(dbh_bin) * dbh_step,
            float(height_bin) * height_step,
            float(bark_bin) * bark_step,
        )

    def _lookup_or_compute_timber_value_volume(
        self,
        *,
        species: str,
        diameter_cm: float,
        height_m: float,
        bark_mm: float,
        region: str,
    ) -> tuple[float, float, bool] | None:
        """Return cached timber value/volume per tree, or ``None`` when lookup mode is off."""
        if not self.config.valuation_use_solution_cube:
            return None

        key = self._valuation_lookup_key(
            species=species,
            diameter_cm=diameter_cm,
            height_m=height_m,
            bark_mm=bark_mm,
            region=region,
        )
        cached = self._valuation_lookup_cache.get(key)
        if cached is not None:
            return cached

        _species, dbh_bin, height_bin, bark_bin, _region = key
        dbh_q, height_q, bark_q = self._valuation_lookup_quantized_inputs(
            dbh_bin=dbh_bin,
            height_bin=height_bin,
            bark_bin=bark_bin,
        )
        bark_arg = bark_q if bark_q > 0 else None

        if self._valuation_solution_cube is not None:
            value_q, sections_q = self._valuation_solution_cube.lookup(species, dbh_q, height_q)
            if float(value_q) > 0.0 or sections_q:
                volume_q = float(
                    sum(
                        float(section.get("volume", 0.0))
                        for section in sections_q
                        if isinstance(section, dict)
                    )
                )
                if volume_q <= 0.0:
                    timber_q = SweTimber(
                        species=species,
                        diameter_cm=dbh_q,
                        height_m=height_q,
                        double_bark_mm=bark_arg,
                        region=region,
                        over_bark=False,
                    )
                    volume_q = float(timber_q.getvolume())
                result = (float(value_q), float(volume_q), True)
                self._valuation_lookup_cache[key] = result
                return result

        try:
            timber_q = SweTimber(
                species=species,
                diameter_cm=dbh_q,
                height_m=height_q,
                double_bark_mm=bark_arg,
                region=region,
                over_bark=False,
            )
            bucker_q = Nasberg_1985_BranchBound(timber_q, self._pricelist, EdgrenNylinder1949)
            buck_result_q = bucker_q.calculate_tree_value(
                min_diam_dead_wood=99.0,
                config=BuckingConfig(save_sections=False),
            )
            result = (float(buck_result_q.total_value), float(buck_result_q.vol_sk_ub), True)
        except ValueError:
            # Remember failed bins to avoid repeated expensive retries.
            result = (0.0, 0.0, False)

        self._valuation_lookup_cache[key] = result
        return result

    def _build_context(self) -> None:
        """Create the run's one context around the current tree list.

        Called once, at the end of :meth:`initialize`. The pipeline used to build a
        fresh ``CircularPlot``, ``Stand`` and ``SimulationContext`` three times per
        period and throw each away -- so the context's history, the thing it exists
        to keep, never survived a step, and the stand it described had to be
        reassembled before anything could read it.

        Raises:
            RuntimeError: If no site has been set.
        """
        if self._site is None:
            raise RuntimeError("site is not set")
        plot = CircularPlot(id=1, area_m2=10000.0, trees=self._trees)
        stand = Stand(site=self._site, plots=[plot])
        self._ctx = self._model.build_context(
            stand,
            mode_hint="tree_list",
            inputs=self._model_inputs(),
        )
        self._refresh_model_view()

    def _refresh_model_view(self) -> None:
        """Re-read the stand into the context the growth model steps.

        Two things in the context go stale when a phase changes the stand: the
        stand's metric estimates, which the growth models read as their whole-stand
        basal area, and the model's resolved inputs, two of which -- the dominant
        species and the field-estimated basal area -- are facts about the crop
        rather than about the site.

        Raises:
            RuntimeError: If called before :meth:`initialize` built a context.
        """
        ctx = self._ctx
        if ctx is None:
            raise RuntimeError("Pipeline has no context; call initialize(site=...) first.")
        ctx.stand.refresh_metrics()
        inputs = self._model_inputs()
        if inputs is not None:
            ctx.inputs = inputs
        ctx.attrs.update(self._model_attrs())
        # Elfving's growth kernels read ctx.state["t"] to decide between the
        # field-estimated basal area (first period only) and the stand's own, so the
        # context's clock has to agree with the pipeline's before the model steps.
        ctx.state["t"] = float(self._years_elapsed)

    def _model_inputs(self) -> Any | None:
        """The typed site and stand facts the growth model steps with, as of now.

        These used to be twelve string keys written onto ``ctx.attrs`` after the
        context was built, where a mistyped name was indistinguishable from a site
        that had none of that value and only surfaced as a default -- or an
        exception -- once a growth kernel reached for it.

        Returns ``None`` for a model that declares no ``Inputs`` type and reads
        ``ctx.attrs`` instead; see :meth:`_model_attrs`.
        """
        if self._site is None:
            raise RuntimeError("site is not set")
        dominant_species = (
            self._stand_structure()["dominant_species"]
            if self._trees
            else self.config.species_to_plant
        )
        return Elfving2010Inputs(
            site_index_m=float(self._site_index_for_species(dominant_species)),
            temperature_sum_dd=self._temperature_sum(),
            latitude_deg=float(self._site.latitude),
            altitude_m=float(self._site.altitude or 0.0),
            distance_to_coast_km=float(getattr(self._site, "distance_to_coast", 50.0) or 50.0),
            dominant_species=dominant_species,
            field_estimated_basal_area_m2_ha=self._basal_area_m2_ha(self._trees),
            # This pipeline starts from a bare regeneration, so there is no pre-run
            # thinning history to declare; thinnings it performs itself are carried
            # by ctx.attrs["thinning_simulated"] and the Elfving (2009) continuous
            # response instead.
            thinned_0_10_years=False,
            thinned_11_25_years=False,
            thinned_11_30_years=False,
        )

    def _model_attrs(self) -> Mapping[str, Any]:
        """The untyped run values the growth model reads from ``ctx.attrs``.

        Empty here: Elfving 2010 declares an ``Inputs`` type, so everything it needs
        is typed. A model that does not -- Söderberg 1986 -- overrides this, and the
        dict is the honest record of which of the two contracts it is on.
        """
        return {}

    def _young_tree_ids(self, trees: list[Tree]) -> set[TreeUid]:
        """Return object ids for trees below the configured phase-over DBH threshold."""
        if self._phase_over_weight(self._weighted_mean_height_m(trees)) >= 0.999:
            return set()
        handover = float(self.config.handover_dbh_cm)
        return {tree.uid for tree in trees if float(tree.diameter_cm or 0.0) < handover}

    def _weighted_mean_height_m(self, trees: list[Tree]) -> float:
        """Return weighted arithmetic mean tree height for phase-over classification."""
        numerator = 0.0
        denominator = 0.0
        for tree in trees:
            height = float(tree.height_m or 0.0)
            weight = float(tree.weight_n or 0.0)
            if height <= 0.0 or weight <= 0.0:
                continue
            numerator += height * weight
            denominator += weight
        if denominator <= 0.0:
            return 0.0
        return numerator / denominator

    def _phase_over_weight(self, mean_height_m: float) -> float:
        """Return smooth mature-phase weight from stand mean height."""
        width = max(0.2, float(self.config.handover_smoothing_width_m))
        z = (float(mean_height_m) - float(self.config.handover_mean_height_m)) / width
        return 1.0 / (1.0 + math.exp(-z))

    @staticmethod
    def _blend_phase_over_dbh(
        *,
        young_dbh_cm: float,
        mature_dbh_cm: float,
        mature_weight: float,
    ) -> float:
        """Blend young and mature DBH trajectories using a clamped smooth weight."""
        w = max(0.0, min(1.0, float(mature_weight)))
        return (1.0 - w) * float(young_dbh_cm) + w * float(mature_dbh_cm)

    def _stand_metrics_for_nystrom(self, trees: list[Tree]) -> dict[str, float]:
        """Compute stand metrics needed by Nyström height and DBH functions."""
        heights = np.array([float(tree.height_m or 0.0) for tree in trees], dtype=float)
        weights = np.array([float(tree.weight_n or 0.0) for tree in trees], dtype=float)
        diameters = np.array([float(tree.diameter_cm or 0.0) for tree in trees], dtype=float)
        if heights.size == 0 or weights.sum() <= 0.0:
            return {
                "mean_height_m": 0.0,
                "total_height_sqr_m2_per_ha": 0.0,
                "total_height_sqr_std_m2_per_ha": 0.0,
                "total_height_sqr_m2_per_100m2": 0.0,
                "broadleaf_height_sqr_share": 0.0,
                "h_max_m": 0.0,
            }

        total_weight = float(weights.sum())
        mean_height_m = float((heights * weights).sum() / total_weight)
        total_height_sqr_m2_per_ha = float(((heights**2) * weights).sum())
        overstorey_mask = diameters >= float(self.config.handover_dbh_cm)
        total_height_sqr_std_m2_per_ha = float(((heights**2) * weights * overstorey_mask).sum())

        broadleaf_mask = np.array([tree.species in _BROADLEAF_SET for tree in trees], dtype=float)
        broadleaf_height_sqr = float(((heights**2) * weights * broadleaf_mask).sum())
        broadleaf_share = (
            broadleaf_height_sqr / total_height_sqr_m2_per_ha
            if total_height_sqr_m2_per_ha > 0
            else 0.0
        )
        top_heights = sorted((float(tree.height_m or 0.0) for tree in trees), reverse=True)[:3]
        h_max_m = float(np.mean(top_heights)) if top_heights else 0.0
        return {
            "mean_height_m": mean_height_m,
            "total_height_sqr_m2_per_ha": total_height_sqr_m2_per_ha,
            "total_height_sqr_std_m2_per_ha": total_height_sqr_std_m2_per_ha,
            "total_height_sqr_m2_per_100m2": total_height_sqr_m2_per_ha / 100.0,
            "broadleaf_height_sqr_share": broadleaf_share,
            "h_max_m": h_max_m,
        }

    def _apply_initial_dbh_and_age(self) -> None:
        """Initialize DBH with Nyström/Söderberg (1987) and assign age at breast height."""
        if self._site is None:
            raise RuntimeError("site is not set")
        metrics = self._stand_metrics_for_nystrom(self._trees)
        if metrics["mean_height_m"] <= 0.0:
            return
        near_coast = int(float(getattr(self._site, "distance_to_coast", 999.0) or 999.0) < 5.0)
        shrubs = int(self._site.field_layer == Sweden.FieldLayer.HIGH_HERB_WITH_SHRUBS_BLUEBERRY)
        herb_grass = int(self._site.field_layer == Sweden.FieldLayer.BROADLEAVED_GRASS)

        for tree in self._trees:
            if tree.species is None or tree.height_m is None:
                continue
            tree.diameter_cm = NystromSoderberg1987.dbh_from_height(
                height_dm=float(tree.height_m) * 10.0,
                species=tree.species,
                total_height_sqr_m2_per_100m2=metrics["total_height_sqr_m2_per_100m2"],
                broadleaf_height_sqr_share=metrics["broadleaf_height_sqr_share"],
                natural_regeneration=int(
                    self.config.regeneration_type == RegenerationType.NATURAL
                ),
                cleaning_indicator=0,
                years_since_cleaning=0,
                altitude_m=float(self._site.altitude or 0.0),
                latitude_deg=float(self._site.latitude),
                shrubs=shrubs,
                herb_grass=herb_grass,
                near_coast=near_coast,
                site_index_pine_m=float(self.config.site_index_pine_m),
                h_max_m=max(metrics["h_max_m"], float(tree.height_m)),
                veg=0,
            )
            age_bh = NystromSoderberg1987.age_at_breast_height(
                height_dm=float(tree.height_m) * 10.0,
                mean_height_dm=max(12.0, metrics["mean_height_m"] * 10.0),
                site_index_dm=self._site_index_for_species(tree.species) * 10.0,
                species=tree.species,
            )
            if age_bh < 0:
                age_bh = max(1.0, self.config.initial_age_years - 1.0)
            tree.age = Age.DBH(age_bh)

    def _apply_nystrom_young_growth(self, *, young_ids: set[TreeUid], dt_years: float) -> None:
        """Advance height and DBH for trees still in the young-stand phase.

        Reports the period's mean damage index and damage mortality onto
        :attr:`_record`, including the two cases where there is nothing to do: a
        stand with no young trees left has a damage index of zero, not last
        period's.

        Raises:
            RuntimeError: If no site has been set.
        """
        if self._site is None:
            raise RuntimeError("site is not set")
        if not young_ids:
            self._record.damage_index_mean = 0.0
            self._record.damage_mortality_stems_per_ha = 0.0
            return

        metrics = self._stand_metrics_for_nystrom(self._trees)
        if metrics["mean_height_m"] <= 0.0:
            self._record.damage_index_mean = 0.0
            self._record.damage_mortality_stems_per_ha = 0.0
            return

        young_trees = [tree for tree in self._trees if tree.uid in young_ids]
        damage_by_group = self._naslund_damage_by_group(young_trees)
        damage_index_sum = 0.0
        damage_index_count = 0.0

        for tree in self._trees:
            if tree.uid not in young_ids or tree.species is None or tree.height_m is None:
                continue
            species_group = self._naslund_species_group(tree.species)
            damage_index = float(damage_by_group.get(species_group, 0.0))
            damage_index_sum += damage_index
            damage_index_count += 1.0
            age_bh_years = (
                float(tree.age) if tree.age is not None else self.config.initial_age_years
            )
            current_height = max(0.3, float(tree.height_m or 0.3))
            growth_m = sapling_height_growth_m(
                height_m=current_height,
                age_bh_years=Age.DBH(max(0.0, age_bh_years)),
                mean_height_m=max(0.3, metrics["mean_height_m"]),
                total_height_sqr_m2_per_ha=metrics["total_height_sqr_m2_per_ha"],
                total_height_sqr_std_m2_per_ha=metrics["total_height_sqr_std_m2_per_ha"],
                temperature_sum=self._temperature_sum(),
                soil_moisture=self._site.soil_moisture,
                field_layer=self._site.field_layer,
                damage_index=damage_index,
                species=tree.species,
                period_years=dt_years,
            )
            tree.height_m = max(0.3, current_height + float(growth_m))

        self._record.damage_index_mean = (
            damage_index_sum / damage_index_count if damage_index_count > 0 else 0.0
        )

        metrics = self._stand_metrics_for_nystrom(self._trees)
        near_coast = int(float(getattr(self._site, "distance_to_coast", 999.0) or 999.0) < 5.0)
        shrubs = int(self._site.field_layer == Sweden.FieldLayer.HIGH_HERB_WITH_SHRUBS_BLUEBERRY)
        herb_grass = int(self._site.field_layer == Sweden.FieldLayer.BROADLEAVED_GRASS)
        for tree in self._trees:
            if tree.uid not in young_ids or tree.species is None or tree.height_m is None:
                continue
            tree.diameter_cm = NystromSoderberg1987.dbh_from_height(
                height_dm=float(tree.height_m) * 10.0,
                species=tree.species,
                total_height_sqr_m2_per_100m2=metrics["total_height_sqr_m2_per_100m2"],
                broadleaf_height_sqr_share=metrics["broadleaf_height_sqr_share"],
                natural_regeneration=int(
                    self.config.regeneration_type == RegenerationType.NATURAL
                ),
                cleaning_indicator=0,
                years_since_cleaning=0,
                altitude_m=float(self._site.altitude or 0.0),
                latitude_deg=float(self._site.latitude),
                shrubs=shrubs,
                herb_grass=herb_grass,
                near_coast=near_coast,
                site_index_pine_m=float(self.config.site_index_pine_m),
                h_max_m=max(metrics["h_max_m"], float(tree.height_m)),
                veg=0,
            )

        removed_stems = 0.0
        if self.config.use_naslund_damage_mortality:
            for tree in self._trees:
                if tree.uid not in young_ids or tree.species is None or tree.height_m is None:
                    continue
                species_group = self._naslund_species_group(tree.species)
                damage_index = float(damage_by_group.get(species_group, 0.0))
                expected_dead_fraction = self._naslund_expected_dead_fraction(
                    species_group=species_group,
                    tree_height_m=float(tree.height_m),
                    damage_index=damage_index,
                )
                expected_dead_fraction *= float(self.config.naslund_damage_mortality_scale)
                expected_dead_fraction *= dt_years / 5.0
                expected_dead_fraction = max(0.0, min(1.0, expected_dead_fraction))
                if expected_dead_fraction <= 0.0:
                    continue
                old_weight = float(tree.weight_n or 0.0)
                if old_weight <= 0.0:
                    continue
                new_weight = old_weight * (1.0 - expected_dead_fraction)
                tree.weight_n = new_weight
                removed_stems += old_weight - new_weight

        self._record.damage_mortality_stems_per_ha = removed_stems
        self._trees = [tree for tree in self._trees if float(tree.weight_n or 0.0) > 1.0e-9]

    @staticmethod
    def _naslund_species_group(species: TreeName) -> SaplingSpeciesGroup:
        """Map a species to Näslund (1986) sapling-group coding."""
        if species in _CONTORTA_SET:
            return SaplingSpeciesGroup.CONTORTA
        if species in _LARCH_SET:
            return SaplingSpeciesGroup.LARCH
        if species in _SPRUCE_SET:
            return SaplingSpeciesGroup.SPRUCE
        if species in _BIRCH_SET:
            return SaplingSpeciesGroup.BIRCH
        if species in _ASPEN_SET:
            return SaplingSpeciesGroup.ASPEN
        if species in _PINE_SET:
            return SaplingSpeciesGroup.PINE
        return SaplingSpeciesGroup.OTHER_BROADLEAF

    def _naslund_damage_by_group(self, trees: list[Tree]) -> dict[SaplingSpeciesGroup, float]:
        """Return Näslund (1986) group-wise damage proportions for current young trees."""
        if not self.config.use_naslund_damage_index or self._site is None or not trees:
            return {}
        return Naslund1986DamageModel.damage_proportions_from_trees(
            trees=trees,
            site_index_pine_m=float(self.config.site_index_pine_m),
            site_index_spruce_m=float(self.config.site_index_spruce_m),
            latitude_deg=float(self._site.latitude),
            altitude_m=float(self._site.altitude or 0.0),
            expansion_factor=1.0,
            moose_factor=float(self.config.naslund_moose_factor),
            vole_factor=float(self.config.naslund_vole_factor),
            snow_break_factor=float(self.config.naslund_snow_break_factor),
            whip_factor=float(self.config.naslund_whip_factor),
            frost_factor=float(self.config.naslund_frost_factor),
            snow_blight_factor=float(self.config.naslund_snow_blight_factor),
            other_factor=float(self.config.naslund_other_factor),
        )

    def _naslund_expected_dead_fraction(
        self,
        *,
        species_group: SaplingSpeciesGroup,
        tree_height_m: float,
        damage_index: float,
    ) -> float:
        """Estimate expected dead fraction from Näslund damage risk and severity pathways."""
        risks = Naslund1986DamageModel.risk_of_damage(
            species_group=species_group,
            height_m=max(0.3, float(tree_height_m)),
            moose_factor=float(self.config.naslund_moose_factor),
            vole_factor=float(self.config.naslund_vole_factor),
            snow_break_factor=float(self.config.naslund_snow_break_factor),
            whip_factor=float(self.config.naslund_whip_factor),
            frost_factor=float(self.config.naslund_frost_factor),
            snow_blight_factor=float(self.config.naslund_snow_blight_factor),
            other_factor=float(self.config.naslund_other_factor),
        )
        if not risks:
            return 0.0
        risk_weights = [max(0.0, float(risk)) for risk in risks]
        total_weight = float(sum(risk_weights))
        if total_weight <= 0.0:
            return 0.0

        dead_given_damage = 0.0
        for agent_idx, weight in enumerate(risk_weights):
            if weight <= 0.0:
                continue
            needs_moose_prop = (
                species_group
                in {
                    SaplingSpeciesGroup.PINE,
                    SaplingSpeciesGroup.LARCH,
                    SaplingSpeciesGroup.BIRCH,
                }
                and agent_idx == 0
            )
            degree = Naslund1986DamageModel.damage_degree(
                species_group=species_group,
                causal_agent=agent_idx,
                height_m=max(0.3, float(tree_height_m)),
                moose_damage_prop=float(damage_index) if needs_moose_prop else None,
            )
            dead_given_damage += (weight / total_weight) * max(0.0, min(1.0, float(degree[2])))
        return max(0.0, min(1.0, float(damage_index))) * max(0.0, min(1.0, dead_given_damage))

    @staticmethod
    def _bal_m2_ha_for_tree(tree: Tree) -> float:
        """Return represented tree basal area in m2/ha."""
        diameter_cm = float(tree.diameter_cm or 0.0)
        weight = float(tree.weight_n or 0.0)
        if diameter_cm <= 0.0 or weight <= 0.0:
            return 0.0
        return math.pi * (diameter_cm / 200.0) ** 2 * weight

    def _predict_mortality(self, *, dt_years: float) -> None:
        """Predict period mortality and store it as per-tree ``mortality`` fractions.

        This runs BEFORE the growth step so the Elfving stand calibration (which
        multiplies by ``1 - tree.mortality``) calibrates on survived basal area.
        No stems are removed here; :meth:`_realize_mortality` removes them after
        growth.
        """
        for tree in self._trees:
            tree.mortality = 0.0
        if self._site is None or not self._trees:
            self._record.mortality_fraction_mean = 0.0
            return

        mortality_trees = [
            tree
            for tree in self._trees
            if tree.species is not None
            and float(tree.diameter_cm or 0.0) > 0.0
            and float(tree.weight_n or 0.0) > 0.0
        ]
        if not mortality_trees:
            self._record.mortality_fraction_mean = 0.0
            return

        sorted_by_dbh = sorted(
            mortality_trees,
            key=lambda tree: float(tree.diameter_cm or 0.0),
            reverse=True,
        )
        bal_map_m2_ha: dict[int, float] = {}
        cumulative_bal = 0.0
        for tree in sorted_by_dbh:
            bal_map_m2_ha[tree.uid] = cumulative_bal
            cumulative_bal += self._bal_m2_ha_for_tree(tree)

        species_ba_m2_ha: dict[TreeName, float] = {}
        for tree in mortality_trees:
            species = tree.species
            if species is None:
                continue
            species_ba_m2_ha[species] = species_ba_m2_ha.get(
                species, 0.0
            ) + self._bal_m2_ha_for_tree(tree)

        total_stems_per_ha = sum(float(tree.weight_n or 0.0) for tree in mortality_trees)
        if total_stems_per_ha <= 0.0:
            self._record.mortality_fraction_mean = 0.0
            return
        total_basal_area_m2_ha = sum(self._bal_m2_ha_for_tree(tree) for tree in mortality_trees)
        if total_basal_area_m2_ha <= 0.0:
            self._record.mortality_fraction_mean = 0.0
            return
        mean_diameter_arithmetic_cm = (
            sum(
                float(tree.diameter_cm or 0.0) * float(tree.weight_n or 0.0)
                for tree in mortality_trees
            )
            / total_stems_per_ha
        )
        mean_diameter_dg_cm = math.sqrt(
            (40000.0 * total_basal_area_m2_ha) / (math.pi * total_stems_per_ha)
        )
        mean_age_total_years = self._mean_age_total_years()

        records = [
            MortalityTreeRecord(
                species=tree.species,
                diameter_cm=float(tree.diameter_cm or 0.0),
                bal=float(bal_map_m2_ha.get(tree.uid, 0.0)),
                stems_per_tree=float(tree.weight_n or 0.0),
                age_total_years=float(tree.age)
                if tree.age is not None
                else float(self._current_age_years),
                is_overstorey=bool(tree.is_overstorey or False),
            )
            for tree in mortality_trees
            if tree.species is not None
        ]
        if not records:
            self._record.mortality_fraction_mean = 0.0
            return

        structure = self._stand_structure()
        soil_texture = getattr(self._site, "soil_texture", None)
        peat = bool(soil_texture in {Sweden.SoilTextureSediment.PEAT, Sweden.SoilTextureTill.PEAT})
        run_config = replace(
            self._mortality_engine.config,
            period_years=float(dt_years),
            stochastic_seed=self.config.random_seed,
        )
        self._mortality_engine = MortalityEngine(config=run_config)
        result = self._mortality_engine.run(
            MortalityContext(
                trees=records,
                stand=MortalityStandConditions(
                    plot_area_m2=10000.0,
                    total_basal_area_m2_ha=total_basal_area_m2_ha,
                    total_stems_per_ha=total_stems_per_ha,
                    mean_diameter_arithmetic_cm=mean_diameter_arithmetic_cm,
                    mean_diameter_dg_cm=mean_diameter_dg_cm,
                    mean_age_total_years=mean_age_total_years,
                    mean_age_excl_overstorey_years=mean_age_total_years,
                    species_basal_area_m2_ha=species_ba_m2_ha,
                ),
                site=MortalitySiteConditions(
                    latitude_deg=float(self._site.latitude),
                    altitude_m=float(self._site.altitude or 0.0),
                    site_index_m=float(structure["site_index_dominant_m"]),
                    soil_moisture=self._site.soil_moisture,
                    peat=peat,
                    temperature_sum=float(self._temperature_sum()),
                    part_of_sweden=self._infer_part_of_sweden(),
                    field_layer=self._site.field_layer,
                ),
                history=MortalityHistoryConditions(),
            )
        )

        mortality_sum = 0.0
        count = 0
        for tree, mortality_fraction in zip(
            mortality_trees,
            result.tree_realized_mortality,
            strict=True,
        ):
            mortality = max(0.0, min(1.0, float(mortality_fraction)))
            tree.mortality = mortality
            mortality_sum += mortality
            count += 1

        self._record.mortality_fraction_mean = (mortality_sum / count) if count > 0 else 0.0

    def _realize_mortality(self) -> None:
        """Remove the stems marked dead by :meth:`_predict_mortality`.

        Runs after growth: scales each tree's ``weight_n`` by ``1 - mortality``
        (the same fraction the stand calibration already accounted for) and drops
        emptied trees.
        """
        removed_stems_per_ha = 0.0
        for tree in self._trees:
            mortality = max(0.0, min(1.0, float(getattr(tree, "mortality", 0.0) or 0.0)))
            old_weight = float(tree.weight_n or 0.0)
            tree.mortality = 0.0
            if old_weight <= 0.0 or mortality <= 0.0:
                continue
            tree.weight_n = old_weight * (1.0 - mortality)
            removed_stems_per_ha += old_weight - float(tree.weight_n or 0.0)
        self._trees = [tree for tree in self._trees if float(tree.weight_n or 0.0) > 1.0e-9]
        self._record.mortality_stems_removed_per_ha = removed_stems_per_ha

    def _apply_ingrowth(self) -> None:
        """Add recruited trees via Wikberg 2004 ingrowth model.

        Called after mortality and age increment, before height/bark update.
        Ingrowth is gated to the model's applicability range: QMD > 10 cm and
        mean age > threshold.
        """
        if not self._trees or self._site is None:
            return

        # Compute stand metrics for gating
        ba = self._basal_area_m2_ha(self._trees)
        stems = sum(float(t.weight_n or 0.0) for t in self._trees)
        if stems <= 0.0 or ba <= 0.0:
            return
        qmd = math.sqrt((40000.0 * ba) / (math.pi * stems))
        if qmd <= 10.0:
            return

        # Mean age excluding overstorey (BA-weighted)
        age_sum = 0.0
        ba_sum = 0.0
        for t in self._trees:
            if getattr(t, "is_overstorey", False):
                continue
            d = float(t.diameter_cm or 0.0)
            w = float(t.weight_n or 0.0)
            a = float(t.age or 0.0)
            if d > 0.0 and w > 0.0:
                tree_ba = math.pi * (d / 200.0) ** 2 * w
                age_sum += a * tree_ba
                ba_sum += tree_ba
        mean_age_excl = (age_sum / ba_sum) if ba_sum > 0.0 else 0.0
        if mean_age_excl < self.config.ingrowth_min_mean_age_years:
            return

        # Build species-level basal area and presence maps
        species_ba: dict[IngrowthSpeciesGroup, float] = {}
        species_presence: dict[IngrowthSpeciesGroup, int] = {}
        for t in self._trees:
            d = float(t.diameter_cm or 0.0)
            w = float(t.weight_n or 0.0)
            if d <= 0.0 or w <= 0.0:
                continue
            grp = _to_ingrowth_species(t.species)
            species_ba[grp] = species_ba.get(grp, 0.0) + math.pi * (d / 200.0) ** 2 * w
            if d >= 10.0:
                species_presence[grp] = 1

        # Site inputs
        site = self._site
        si_m = max(self.config.site_index_pine_m, self.config.site_index_spruce_m)
        temp_sum = self._temperature_sum()

        # Provide sensible defaults for site attributes the ingrowth model requires
        soil_texture = getattr(site, "soil_texture", None) or Sweden.SoilTextureTill.SANDY
        soil_water = getattr(site, "soil_water", None) or Sweden.SoilWater.SELDOM_NEVER
        bottom_layer = getattr(site, "bottom_layer", None) or Sweden.BottomLayer.LICHEN_TYPE

        result = ingrowth_predict(
            site_index_m=si_m,
            basal_area_m2_ha=ba,
            qmd_cm=qmd,
            mean_age_excl_overstorey_years=mean_age_excl,
            temperature_sum_dd=temp_sum,
            latitude_deg=float(site.latitude),
            altitude_m=float(site.altitude or 0.0),
            soil_moisture=site.soil_moisture,
            soil_texture=soil_texture,
            soil_water=soil_water,
            bottom_layer=bottom_layer,
            field_layer=site.field_layer,
            species_ba_m2_ha=species_ba,
            species_presence_10cm=species_presence,
            deterministic=self.config.ingrowth_deterministic,
            rng=self._rng.child("ingrowth"),
        )

        new_trees = ingrowth_to_plot_trees(result, plot_area_ha=1.0)
        if new_trees:
            self._trees.extend(new_trees)

    def _mean_age_total_years(self) -> float:
        """Return basal-area-weighted stand age (years), with a safe fallback."""
        weighted_age_sum = 0.0
        ba_sum = 0.0
        for tree in self._trees:
            diameter_cm = float(tree.diameter_cm or 0.0)
            if diameter_cm <= 0.0:
                continue
            weight = float(tree.weight_n or 0.0)
            if weight <= 0.0:
                continue
            ba = math.pi * (diameter_cm / 200.0) ** 2 * weight
            age = float(tree.age) if tree.age is not None else self._current_age_years
            weighted_age_sum += ba * max(1.0, age)
            ba_sum += ba
        if ba_sum <= 0.0:
            return max(1.0, self._current_age_years)
        return weighted_age_sum / ba_sum

    def _infer_part_of_sweden(self) -> str:
        """Map latitude to the coarse Söderberg region."""
        if self._site is None:
            raise RuntimeError("site is not set")
        latitude = float(self._site.latitude)
        if latitude < 57.0:
            return "south"
        if latitude < 59.0:
            return "middle"
        return "north"

    def _climate_flags(self) -> tuple[bool, bool]:
        """Return (maritime, continental) flags from site climate-zone label."""
        if self._site is None:
            return False, False
        climate_zone = getattr(self._site, "climate_zone", None)
        if climate_zone is None:
            return False, False
        label = climate_zone.value.label
        return label.startswith("M"), label.startswith("K")

    def _stand_structure(self) -> dict[str, Any]:
        """Return stand-level context needed by Söderberg height and bark functions."""
        ba_total = self._basal_area_m2_ha(self._trees)
        max_diameter_cm = max(
            (float(tree.diameter_cm or 0.0) for tree in self._trees), default=0.0
        )
        if ba_total <= 0.0 or max_diameter_cm <= 0.0:
            return {
                "ba_total": 0.0,
                "max_diameter_cm": 0.0,
                "dominant_species": TreeSpecies.Sweden.pinus_sylvestris,
                "site_index_dominant_m": float(self.config.site_index_pine_m),
                "prop_pine": 0.0,
                "prop_spruce": 0.0,
                "prop_birch": 0.0,
                "prop_beech": 0.0,
            }

        species_ba: dict[TreeName, float] = {}
        group_ba = {"pine": 0.0, "spruce": 0.0, "birch": 0.0, "beech": 0.0}
        for tree in self._trees:
            if tree.species is None:
                continue
            diameter_cm = float(tree.diameter_cm or 0.0)
            weight = float(tree.weight_n or 0.0)
            if diameter_cm <= 0.0 or weight <= 0.0:
                continue
            ba = math.pi * (diameter_cm / 200.0) ** 2 * weight
            species_ba[tree.species] = species_ba.get(tree.species, 0.0) + ba
            if tree.species in _PINE_SET:
                group_ba["pine"] += ba
            elif tree.species in _SPRUCE_SET:
                group_ba["spruce"] += ba
            elif tree.species in _BIRCH_SET:
                group_ba["birch"] += ba
            elif tree.species is TreeSpecies.Sweden.fagus_sylvatica:
                group_ba["beech"] += ba

        dominant_species = (
            max(species_ba.items(), key=lambda item: item[1])[0]
            if species_ba
            else TreeSpecies.Sweden.pinus_sylvestris
        )
        site_index_dominant_m = (
            self.config.site_index_spruce_m
            if dominant_species in _SPRUCE_SET
            else self.config.site_index_pine_m
        )
        return {
            "ba_total": ba_total,
            "max_diameter_cm": max_diameter_cm,
            "dominant_species": dominant_species,
            "site_index_dominant_m": float(site_index_dominant_m),
            "prop_pine": group_ba["pine"] / ba_total,
            "prop_spruce": group_ba["spruce"] / ba_total,
            "prop_birch": group_ba["birch"] / ba_total,
            "prop_beech": group_ba["beech"] / ba_total,
        }

    def _apply_soderberg_height_and_bark(
        self,
        *,
        fallback_age_years: float,
        preserve_height_tree_ids: set[TreeUid] | None = None,
    ) -> None:
        """Refresh tree bark and mature-tree heights using Söderberg (1992) functions."""
        if self._site is None:
            raise RuntimeError("site is not set")
        preserve_ids = preserve_height_tree_ids or set()
        structure = self._stand_structure()
        max_diameter_cm = float(structure["max_diameter_cm"])
        if max_diameter_cm <= 0.0:
            for tree in self._trees:
                tree.height_m = 0.0
                tree.double_bark_mm = 0.0
            return

        part_of_sweden = self._infer_part_of_sweden()
        maritime, continental = self._climate_flags()
        near_coast = bool(float(getattr(self._site, "distance_to_coast", 999.0) or 999.0) < 50.0)
        mean_age_total = self._mean_age_total_years()

        for tree in self._trees:
            if tree.species is None:
                continue
            diameter_cm = float(tree.diameter_cm or 0.0)
            if diameter_cm <= 0.0:
                tree.height_m = 0.0
                tree.double_bark_mm = 0.0
                continue
            age_bh_years = float(tree.age) if tree.age is not None else float(fallback_age_years)
            age_bh_years = max(2.0, age_bh_years)
            if tree.uid not in preserve_ids:
                tree.height_m = soderberg_1992_height_tree_age_m(
                    species=tree.species,
                    diameter_cm=diameter_cm,
                    tree_age_bh_years=age_bh_years,
                    max_diameter_cm=max_diameter_cm,
                    stand_basal_area_m2_ha=float(structure["ba_total"]),
                    dominant_species=structure["dominant_species"],
                    site_index_dominant_m=float(structure["site_index_dominant_m"]),
                    latitude_deg=float(self._site.latitude),
                    altitude_m=float(self._site.altitude or 0.0),
                    prop_pine=float(structure["prop_pine"]),
                    prop_spruce=float(structure["prop_spruce"]),
                    prop_birch=float(structure["prop_birch"]),
                    prop_beech=float(structure["prop_beech"]),
                    part_of_sweden=part_of_sweden,
                    maritime=maritime,
                    continental=continental,
                    near_coast=near_coast,
                )
            else:
                # Keep Nyström young-tree height so the DBH phase-over is not damped.
                tree.height_m = max(0.3, float(tree.height_m or 0.3))
            tree.double_bark_mm = soderberg_1992_bark_thickness_bh_mm(
                species=tree.species,
                diameter_cm=diameter_cm,
                max_diameter_cm=max_diameter_cm,
                mean_age_total_years=mean_age_total,
                site_index_pine_m=float(self.config.site_index_pine_m),
                latitude_deg=float(self._site.latitude),
                altitude_m=float(self._site.altitude or 0.0),
                prop_pine=float(structure["prop_pine"]),
                prop_spruce=float(structure["prop_spruce"]),
                prop_birch=float(structure["prop_birch"]),
                part_of_sweden=part_of_sweden,
            )

    def _increment_tree_ages(self, years: float) -> None:
        """Increase breast-height age for all trees with age information."""
        for tree in self._trees:
            if tree.age is None:
                continue
            tree.age = Age.DBH(float(tree.age) + years)

    def _basal_area_m2_ha(self, trees: list[Tree]) -> float:
        """Return total stand basal area (m2/ha) from tree list records."""
        total = 0.0
        for tree in trees:
            diameter_cm = float(tree.diameter_cm or 0.0)
            weight = float(tree.weight_n or 0.0)
            if diameter_cm <= 0.0 or weight <= 0.0:
                continue
            total += math.pi * (diameter_cm / 200.0) ** 2 * weight
        return total

    @staticmethod
    def _qmd_cm_from_basal_area_and_stems(
        *,
        basal_area_m2_ha: float,
        stems_per_ha: float,
    ) -> float:
        """Return stand QMD (cm) from basal area and stems."""
        ba = float(basal_area_m2_ha)
        stems = float(stems_per_ha)
        if ba <= 0.0 or stems <= 0.0:
            return 0.0
        return math.sqrt((40000.0 * ba) / (math.pi * stems))

    @staticmethod
    def _hq_height_m_from_tree_list(
        trees: list[Tree],
        *,
        qmd_cm: float,
    ) -> float:
        """Return Hq (m): height corresponding to stand QMD from the tree list."""
        if qmd_cm <= 0.0:
            return 0.0

        diameters = np.array([float(tree.diameter_cm or 0.0) for tree in trees], dtype=float)
        heights = np.array([float(tree.height_m or 0.0) for tree in trees], dtype=float)
        weights = np.array([float(tree.weight_n or 0.0) for tree in trees], dtype=float)

        valid = (diameters > 0.0) & (heights > 0.0) & (weights > 0.0)
        if not np.any(valid):
            return 0.0

        diameters = diameters[valid]
        heights = heights[valid]
        weights = weights[valid]

        diameter_bins_cm = np.round(diameters, 1)
        unique_bins_cm, inverse = np.unique(diameter_bins_cm, return_inverse=True)

        height_weighted_sum = np.zeros(unique_bins_cm.shape, dtype=float)
        bin_weight_sum = np.zeros(unique_bins_cm.shape, dtype=float)
        np.add.at(height_weighted_sum, inverse, heights * weights)
        np.add.at(bin_weight_sum, inverse, weights)

        mean_height_by_bin = np.divide(
            height_weighted_sum,
            bin_weight_sum,
            out=np.zeros_like(height_weighted_sum),
            where=bin_weight_sum > 0.0,
        )

        if unique_bins_cm.size == 1:
            return float(mean_height_by_bin[0])

        d_eval_cm = float(np.clip(qmd_cm, unique_bins_cm[0], unique_bins_cm[-1]))
        return float(np.interp(d_eval_cm, unique_bins_cm, mean_height_by_bin))

    def _valuation_species_name(self, species: TreeName) -> str:
        """Map species to a valuation species accepted by SweTimber/pricelist paths."""
        if species in _SPRUCE_SET:
            return TreeSpecies.Sweden.picea_abies.full_name
        if species in _PINE_SET:
            return TreeSpecies.Sweden.pinus_sylvestris.full_name
        return TreeSpecies.Sweden.betula.full_name

    def _snapshot_row(self, *, step_index: int) -> dict[str, float]:
        """Build one projection row with stand and valuation metrics."""
        weights = np.array([float(tree.weight_n or 0.0) for tree in self._trees], dtype=float)
        diameters = np.array([float(tree.diameter_cm or 0.0) for tree in self._trees], dtype=float)
        heights = np.array([float(tree.height_m or 0.0) for tree in self._trees], dtype=float)
        total_weight = float(weights.sum())
        mean_dbh_cm = (
            float((diameters * weights).sum() / total_weight) if total_weight > 0 else 0.0
        )
        mean_height_m = (
            float((heights * weights).sum() / total_weight) if total_weight > 0 else 0.0
        )
        basal_area_m2_ha = self._basal_area_m2_ha(self._trees)
        qmd_cm = self._qmd_cm_from_basal_area_and_stems(
            basal_area_m2_ha=basal_area_m2_ha,
            stems_per_ha=total_weight,
        )
        hq_m = self._hq_height_m_from_tree_list(
            self._trees,
            qmd_cm=qmd_cm,
        )
        valuation = self.value_standing_forest(self._trees)

        group_ba = {"pine": 0.0, "spruce": 0.0, "birch": 0.0}
        for tree in self._trees:
            if tree.species is None:
                continue
            diameter_cm = float(tree.diameter_cm or 0.0)
            weight = float(tree.weight_n or 0.0)
            if diameter_cm <= 0.0 or weight <= 0.0:
                continue
            ba = math.pi * (diameter_cm / 200.0) ** 2 * weight
            if tree.species in _PINE_SET:
                group_ba["pine"] += ba
            elif tree.species in _SPRUCE_SET:
                group_ba["spruce"] += ba
            elif tree.species in _BIRCH_SET:
                group_ba["birch"] += ba

        return {
            "step_index": float(step_index),
            "age_years": float(self._current_age_years),
            "years_elapsed": float(self._years_elapsed),
            "stems_per_ha": float(total_weight),
            "mean_dbh_cm": mean_dbh_cm,
            "mean_height_m": mean_height_m,
            "qmd_cm": float(qmd_cm),
            "hq_m": float(hq_m),
            "basal_area_m2_ha": float(basal_area_m2_ha),
            "standing_volume_m3_per_ha": float(valuation["standing_volume_m3_per_ha"]),
            # Indexed, not `.get(key, 0.0)`: every valuation route returns the same
            # six keys now, so a missing one is a bug to raise on rather than a zero
            # to print.
            "timber_volume_m3_per_ha": float(valuation["timber_volume_m3_per_ha"]),
            "pulp_volume_m3_per_ha": float(valuation["pulp_volume_m3_per_ha"]),
            "standing_value_sek_per_ha": float(valuation["standing_value_sek_per_ha"]),
            "value_per_m3_sek": float(valuation["value_per_m3_sek"]),
            "timber_valued_stems_per_ha": float(valuation["timber_valued_stems_per_ha"]),
            "pine_ba_share": (
                float(group_ba["pine"] / basal_area_m2_ha) if basal_area_m2_ha > 0 else 0.0
            ),
            "spruce_ba_share": float(group_ba["spruce"] / basal_area_m2_ha)
            if basal_area_m2_ha > 0
            else 0.0,
            "birch_ba_share": (
                float(group_ba["birch"] / basal_area_m2_ha) if basal_area_m2_ha > 0 else 0.0
            ),
            "handover_dbh_cm": float(self.config.handover_dbh_cm),
            "handover_mean_height_m": float(self.config.handover_mean_height_m),
            "handover_smoothing_width_m": float(self.config.handover_smoothing_width_m),
            "phase_over_weight": float(self._record.phase_over_weight),
            "young_damage_index_mean": float(self._record.damage_index_mean),
            "young_damage_mortality_stems_removed_per_ha": float(
                self._record.damage_mortality_stems_per_ha
            ),
            "mortality_fraction_mean": float(self._record.mortality_fraction_mean),
            "mortality_stems_removed_per_ha": float(self._record.mortality_stems_removed_per_ha),
            "young_stand_potential_q": float(self._regen_q),
        }


def build_elfving_2010_pipeline(
    config: Elfving2010PipelineConfig | None = None,
) -> Elfving2010Pipeline:
    """Build the Elfving 2010 composite Sweden preset for hybrid projection."""
    return Elfving2010Pipeline(config=config)


__all__ = [
    # Declared because ``Elfving2010Pipeline.steps`` is now data a caller can add to,
    # and a step they write has to name the type it reports into.
    "Elfving2010PeriodRecord",
    "Elfving2010PipelineConfig",
    "Elfving2010Pipeline",
    "build_elfving_2010_pipeline",
]
