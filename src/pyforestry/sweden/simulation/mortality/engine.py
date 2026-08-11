"""Simulation-layer mortality orchestration for Swedish mortality modules.

This module is pyforestry's own composition layer and carries no publication of
its own: it selects among, and applies, mortality models that each carry their
own provenance. The scientific sources are those of the composed modules --
:mod:`pyforestry.sweden.mortality.elfving_2013`,
:mod:`pyforestry.sweden.mortality.fridman_stahl_2001`,
:mod:`pyforestry.sweden.mortality.siipilehto_2020`,
:mod:`pyforestry.sweden.mortality.soderberg_1986`,
:mod:`pyforestry.sweden.mortality.bengtsson` and
:mod:`pyforestry.sweden.mortality.naslund_1986` -- reachable through
:attr:`MortalityEngine.components`.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Optional, Protocol

import numpy as np

from pyforestry.base.contracts import Describable, SourceReference
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.simulation.services import KeyedRNG
from pyforestry.sweden._model_input_normalization import (
    normalize_hagglund_h100_site_index_m as _normalize_hagglund_h100_site_index_m,
)
from pyforestry.sweden.mortality import (
    bengtsson,
    elfving_2013,
    fridman_stahl_2001,
    naslund_1986,
    retained_trees,
    siipilehto_2020,
    soderberg_1986,
)
from pyforestry.sweden.mortality._common import (
    calibration_group,
    clamp_probability,
    species_key,
    species_mortality_fraction_from_tree_probabilities,
    stems_per_tree,
)
from pyforestry.sweden.mortality.bengtsson import calibrate_bengtsson
from pyforestry.sweden.mortality.elfving_2013 import Elfving2013MortalityModel
from pyforestry.sweden.mortality.fridman_stahl_2001 import FridmanStahl2001Model
from pyforestry.sweden.mortality.retained_trees import retained_tree_mortality_by_species
from pyforestry.sweden.mortality.siipilehto_2020 import Siipilehto2020MortalityModel
from pyforestry.sweden.mortality.soderberg_1986 import calibrate_soderberg

from .context import (
    MortalityConfig,
    MortalityContext,
    MortalityHistoryConditions,
    MortalityRealizationMode,
    MortalityResult,
    MortalitySiteConditions,
    MortalityTreeModel,
    MortalityTreeRecord,
)
from .normalize import normalize_mortality_context


class MortalityModel(Protocol):
    """Structural interface shared by the interchangeable single-tree strategies.

    The three tree-model facades (Fridman & Ståhl 2001, Elfving 2013, Siipilehto
    et al. 2020) all expose this signature, so the engine treats the configured
    model as one strategy instead of branching on its concrete type.
    """

    def predict_probabilities(
        self,
        *,
        context: MortalityContext,
        period_years: float,
        default_stems_per_tree: float,
    ) -> tuple[list[float], dict[str, Any]]:
        """Return per-tree 5-year mortality probabilities and model diagnostics."""
        ...


# Maps the configured model family to a factory that builds the single selected
# strategy. Adding a model is a table entry, not another branch in the driver
# (cf. the enum->callable dispatch in sweden/ingrowth/wikberg_2004.py).
#: The second argument is the run's keyed stream, which a model that draws takes.
#: Given only ``stochastic_seed`` such a model opens a stream from that constant,
#: and because the engine is rebuilt every period it reopened the *same* one each
#: time -- so a stochastic tree model drew identical numbers in every period.
_TREE_MODEL_FACTORIES: dict[
    MortalityTreeModel, Callable[[MortalityConfig, "KeyedRNG"], MortalityModel]
] = {
    MortalityTreeModel.FRIDMAN_STAHL_2001: lambda config, rng: FridmanStahl2001Model(
        implementation_type=config.implementation_type,
        stochastic_seed=config.stochastic_seed,
        rng=rng,
    ),
    MortalityTreeModel.ELFVING_2013: lambda _config, _rng: Elfving2013MortalityModel(),
    MortalityTreeModel.SIIPILEHTO_2020: lambda _config, _rng: Siipilehto2020MortalityModel(),
}


@dataclass(frozen=True)
class _MortalitySource:
    """The resolved origin of per-tree probabilities for a single run.

    ``calibratable`` is True only for the model-predicted tree mortality. The
    retained-tree override supplies absolute mortality that is not re-scaled to a
    stand self-thinning target, so it is marked non-calibratable -- carrying that
    decision as data on the source keeps it out of the calibration step.
    """

    label: str
    predict: Callable[[], tuple[list[float], dict[str, Any]]]
    calibratable: bool


def _build_adjustment_lookup(
    factors: Mapping[str, float] | Mapping[Any, float] | None,
) -> dict[str, float]:
    """Normalize species adjustment factors lookup to lowercase keys."""
    lookup: dict[str, float] = {}
    if not factors:
        return lookup
    for key, value in factors.items():
        lookup[str(key).strip().lower()] = float(value)
    return lookup


def _retained_probability(
    tree: MortalityTreeRecord,
    retained_mortality_by_species: Mapping[str, float],
) -> float:
    """Resolve retained-tree mortality for a tree from species/group mapping."""
    return clamp_probability(
        retained_mortality_by_species.get(
            species_key(tree.species),
            retained_mortality_by_species.get(calibration_group(tree.species), 0.0),
        )
    )


def _apply_adjustment_factors(
    *,
    trees: Sequence[MortalityTreeRecord],
    probabilities: Sequence[float],
    global_adjustment_factor: float,
    species_adjustments: Mapping[Any, float] | None,
) -> list[float]:
    """Apply global and species-specific mortality adjustment factors."""
    if len(trees) != len(probabilities):
        raise ValueError("trees and probabilities must have equal length.")
    if global_adjustment_factor < 0.0:
        raise ValueError("global_adjustment_factor must be >= 0.")
    species_lookup = _build_adjustment_lookup(species_adjustments)
    adjusted: list[float] = []
    for tree, probability in zip(trees, probabilities, strict=True):
        factor = species_lookup.get(
            species_key(tree.species),
            species_lookup.get(calibration_group(tree.species), 1.0),
        )
        if factor < 0.0:
            raise ValueError("Species adjustment factors must be >= 0.")
        adjusted.append(clamp_probability(probability * global_adjustment_factor * factor))
    return adjusted


def _normalize_mortality_site_conditions(
    site_conditions: MortalitySiteConditions,
) -> MortalitySiteConditions:
    """Normalize site-state values that may be provided as rich primitives."""
    site_index_m = _normalize_hagglund_h100_site_index_m(
        site_conditions.site_index_m,
        parameter_name="site_index_m",
        allowed_species={
            TreeSpecies.Sweden.pinus_sylvestris,
            TreeSpecies.Sweden.picea_abies,
        },
    )
    return replace(site_conditions, site_index_m=site_index_m)


def _assign_stochastic_mortality(
    *,
    trees: Sequence[MortalityTreeRecord],
    probabilities: Sequence[float],
    rng: np.random.Generator,
    default_stems_per_tree: float,
) -> list[float]:
    """Realize per-tree mortality by binomial draws over represented stems.

    A record that represents ``n`` stems is a set of ``n`` independent trees,
    each dying with probability ``p``; the realized dead fraction is therefore a
    binomial draw ``Binomial(n, p) / n``. Records representing fewer than two
    stems are realized as a single all-or-nothing Bernoulli outcome.
    """
    realized: list[float] = []
    for tree, probability in zip(trees, probabilities, strict=True):
        p = clamp_probability(probability)
        stems = stems_per_tree(tree, default_stems_per_tree)
        stem_count = int(stems) if stems >= 2.0 else 1
        dead = int(rng.binomial(stem_count, p))
        realized.append(clamp_probability(dead / stem_count))
    return realized


def _species_fraction(
    trees: Sequence[MortalityTreeRecord],
    probabilities: Sequence[float],
    default_stems_per_tree: float,
) -> dict[str, float]:
    """Basal-area-weighted mortality fraction per species (no calibration grouping)."""
    return species_mortality_fraction_from_tree_probabilities(
        trees=trees,
        tree_probabilities=probabilities,
        default_stems_per_tree=default_stems_per_tree,
        use_calibration_groups=False,
    )


def _empty_result(config: MortalityConfig) -> MortalityResult:
    """Result for a stand with no trees."""
    return MortalityResult(
        tree_probabilities=[],
        tree_realized_mortality=[],
        species_mortality_fraction={},
        species_mortality_fraction_before_calibration={},
        diagnostics={"tree_model": config.tree_model.value},
    )


@dataclass(slots=True)
class MortalityEngine:
    """Simulation-layer mortality orchestration for Sweden.

    ``run`` is a single linear pipeline: resolve the probability source
    (retained override -> configured tree model), optionally calibrate
    (Bengtsson then Söderberg), apply adjustment factors, and realize the result
    (deterministic or stochastic).
    """

    config: MortalityConfig = field(default_factory=MortalityConfig)
    #: The random stream stochastic realisation draws from: the run's, as
    #: ``ctx.rng.child("mortality")``, so mortality follows the run's seed rather
    #: than a second seed carried on the config. Omitted, the engine falls back to
    #: ``config.stochastic_seed``, which keeps a directly-constructed engine
    #: reproducible on its own terms.
    #:
    #: A :class:`~pyforestry.simulation.services.KeyedRNG` and nothing else. This
    #: briefly accepted a bare ``numpy.random.Generator`` too, which is what
    #: callers passed before the tree models needed streams of their own -- but a
    #: NumPy generator cannot supply the scalar draws a tree model makes, so an
    #: engine given one had to leave its models on the config seed, and a caller
    #: doing the obvious thing got half the fix. One accepted type, or the
    #: distinction has to be documented at every call site instead.
    rng: Optional["KeyedRNG"] = None
    _rng: np.random.Generator = field(init=False, repr=False)
    _tree_model: MortalityModel = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Take the injected random stream, or seed one from the config.

        Raises:
            TypeError: If ``rng`` is not a :class:`KeyedRNG`. A bare generator is
                refused rather than half-used: it can seed this engine's own
                vectorised draws but not the scalar draws of the tree model it
                builds, so accepting one would silently leave the model on the
                config seed -- which is the fault this parameter exists to stop.
        """
        if self.rng is None:
            from pyforestry.simulation.services import RandomBundle

            self.rng = RandomBundle(int(self.config.stochastic_seed or 0)).rng_for()
        elif not isinstance(self.rng, KeyedRNG):
            raise TypeError(
                f"MortalityEngine.rng takes a KeyedRNG, not {type(self.rng).__name__}. "
                "Pass the run's stream -- ctx.rng.child('mortality') -- rather than one "
                "of its generators: the engine draws vectors, the tree model it builds "
                "draws scalars, and only the keyed stream carries both."
            )
        self._rng = self.rng.numpy
        self._tree_model = self._build_tree_model()

    # -- provenance --------------------------------------------------------

    @property
    def component_id(self) -> str:
        """Stable identifier for this composition."""
        return "sweden_mortality_engine"

    @property
    def source(self) -> SourceReference:
        """Provenance for the engine itself, which is a pyforestry composition.

        The engine has no publication of its own. The scientific content belongs
        to the composed mortality modules; see :attr:`components`.
        """
        return SourceReference(
            author="(none)",
            year=0,
            title="Swedish mortality orchestration (pyforestry composition)",
            note=(
                "No primary publication, and none is needed: this layer selects among "
                "and applies mortality models, and holds no coefficients of its own. "
                "year=0 is a sentinel for 'not applicable', not a citation date. The "
                "scientific provenance is that of the composed modules listed in "
                "`components`."
            ),
        )

    @property
    def components(self) -> tuple[Describable, ...]:
        """The mortality modules this engine can compose, each with its own citation.

        Returns the modules' descriptors, not their ids. ``components`` means
        ``Sequence[Describable]`` everywhere else in this package, and every
        consumer reads ``component_id`` and ``source`` off each entry -- so
        returning bare strings did not merely differ in type, it dropped the
        citations. ``pyforestry.projection._provenance`` reported a run through
        this engine as citing one thing, itself, and none of the seven papers
        that produced the numbers.
        """
        return (
            elfving_2013.DESCRIPTOR,
            fridman_stahl_2001.DESCRIPTOR,
            siipilehto_2020.DESCRIPTOR,
            soderberg_1986.DESCRIPTOR,
            bengtsson.DESCRIPTOR,
            naslund_1986.DESCRIPTOR,
            retained_trees.DESCRIPTOR,
        )

    # -- public API --------------------------------------------------------

    def run(self, context: MortalityContext) -> MortalityResult:
        """Predict and realize mortality for the stand described by ``context``."""
        context = self._prepare(context)
        if not context.trees:
            return _empty_result(self.config)

        source = self._resolve_source(context)
        probabilities, diagnostics = source.predict()
        diagnostics["tree_model"] = source.label
        before_calibration = _species_fraction(
            context.trees, probabilities, self.config.default_stems_per_tree
        )
        diagnostics["species_fraction_before_calibration"] = before_calibration

        if source.calibratable:
            probabilities = self._calibrate(context, probabilities, diagnostics)

        probabilities = _apply_adjustment_factors(
            trees=context.trees,
            probabilities=probabilities,
            global_adjustment_factor=self.config.global_adjustment_factor,
            species_adjustments=self.config.species_adjustment_factors,
        )
        realized = self._realize(context, probabilities)

        diagnostics["retained_override_applied"] = source.label == "retained_trees_override"
        return MortalityResult(
            tree_probabilities=list(probabilities),
            tree_realized_mortality=realized,
            species_mortality_fraction=_species_fraction(
                context.trees, realized, self.config.default_stems_per_tree
            ),
            species_mortality_fraction_before_calibration=before_calibration,
            diagnostics=diagnostics,
        )

    # -- pipeline stages ---------------------------------------------------

    def _prepare(self, context: MortalityContext) -> MortalityContext:
        """Copy mutable inputs, fill a default history, and normalize the site index."""
        context = normalize_mortality_context(context)
        return replace(
            context,
            site=_normalize_mortality_site_conditions(context.site),
            history=context.history or MortalityHistoryConditions(),
        )

    def _resolve_source(self, context: MortalityContext) -> _MortalitySource:
        """Select the probability source by precedence: retained override > tree model."""
        config = self.config
        history = context.history or MortalityHistoryConditions()

        retained = self._retained_override(history)
        if retained is not None:
            return _MortalitySource(
                label="retained_trees_override",
                predict=lambda: (
                    [_retained_probability(tree, retained) for tree in context.trees],
                    {},
                ),
                calibratable=False,
            )
        return _MortalitySource(
            label=config.tree_model.value,
            predict=lambda: self._tree_model.predict_probabilities(
                context=context,
                period_years=config.period_years,
                default_stems_per_tree=config.default_stems_per_tree,
            ),
            calibratable=True,
        )

    def _retained_override(
        self, history: MortalityHistoryConditions
    ) -> Mapping[str, float] | None:
        """Return retained-tree mortality-by-species, or None when not applicable."""
        config = self.config
        if not (
            config.use_retained_tree_override
            and config.retained_tree_mortality_years_1_to_5
            and config.retained_tree_mortality_years_6_to_10
        ):
            return None
        return retained_tree_mortality_by_species(
            years_since_final_felling=history.years_since_final_felling,
            mortality_year1_5=config.retained_tree_mortality_years_1_to_5,
            mortality_year6_10=config.retained_tree_mortality_years_6_to_10,
        )

    def _build_tree_model(self) -> MortalityModel:
        """Construct the single configured tree-model strategy from the dispatch table."""
        try:
            factory = _TREE_MODEL_FACTORIES[self.config.tree_model]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Unsupported tree model: {self.config.tree_model}") from exc
        return factory(self.config, self.rng)

    def _calibrate(
        self,
        context: MortalityContext,
        probabilities: list[float],
        diagnostics: dict[str, Any],
    ) -> list[float]:
        """Apply Bengtsson then Söderberg calibration, recording diagnostics in place."""
        config = self.config
        if config.calibrate_bengtsson:
            probabilities, targets, factors, diag = calibrate_bengtsson(
                context=context,
                tree_probabilities=probabilities,
                period_years=config.period_years,
                default_stems_per_tree=config.default_stems_per_tree,
            )
            diagnostics["bengtsson_target_fractions"] = targets
            diagnostics["bengtsson_correction_factors"] = factors
            diagnostics["bengtsson"] = diag
        if config.calibrate_soderberg:
            probabilities, adjusted, factors, diag = calibrate_soderberg(
                context=context,
                tree_probabilities=probabilities,
                site_index_adjustment_factor=config.site_index_adjustment_factor,
                period_years=config.period_years,
                default_stems_per_tree=config.default_stems_per_tree,
            )
            diagnostics["soderberg_adjusted_fractions"] = adjusted
            diagnostics["soderberg_correction_factors"] = factors
            diagnostics["soderberg"] = diag
        return probabilities

    def _realize(self, context: MortalityContext, probabilities: Sequence[float]) -> list[float]:
        """Turn probabilities into realized mortality (deterministic or stochastic)."""
        if self.config.implementation_type == MortalityRealizationMode.DETERMINISTIC:
            return list(probabilities)
        return _assign_stochastic_mortality(
            trees=context.trees,
            probabilities=probabilities,
            rng=self._rng,
            default_stems_per_tree=self.config.default_stems_per_tree,
        )


__all__ = [
    "MortalityEngine",
    "MortalityModel",
    "_apply_adjustment_factors",
    "_assign_stochastic_mortality",
    "_build_adjustment_lookup",
]
