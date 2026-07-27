"""The composite Sweden pipeline driven by Elfving (2010) mature growth.

Everything around the mature-growth phase -- the NYSKOG reconstruction, Nyström
(2000) young-stand growth, Elfving (2013) mortality, Wikberg (2004) ingrowth,
Söderberg (1992) height and bark, and the valuation -- is
:class:`~pyforestry.sweden.simulation.presets._composite.CompositePipeline`.
What this module adds is the model that steps the mature trees, its typed
inputs, and its provenance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from pyforestry.base.contracts import Describable, SourceReference
from pyforestry.sweden.adapters.elfving_2010 import Elfving2010Inputs, Elfving2010Model

from ._composite import CompositePeriodRecord, CompositePipeline, CompositePipelineConfig

__all__ = [
    "Elfving2010PeriodRecord",
    "Elfving2010PipelineConfig",
    "Elfving2010Pipeline",
    "build_elfving_2010_pipeline",
]

#: The period record is the composite's, not this pipeline's. Kept as an alias
#: because a caller writing an extra :class:`Step` names the type it reports into.
Elfving2010PeriodRecord = CompositePeriodRecord


@dataclass(frozen=True)
class Elfving2010PipelineConfig(CompositePipelineConfig):
    """Configuration for the Elfving 2010 composite pipeline.

    Adds nothing to the composite's own knobs: Elfving (2010) needs no switch the
    shared workflow does not already have. It exists so that the two pipelines'
    configs are siblings rather than one being the other's base -- the Söderberg
    config used to inherit from this one and pick up Elfving-only fields with it.
    """


class Elfving2010Pipeline(CompositePipeline):
    """Composite Sweden stand simulation using Elfving (2010) mature growth."""

    def __init__(self, config: Elfving2010PipelineConfig | None = None) -> None:
        """Initialize the composite workflow with the Elfving 2010 growth model."""
        super().__init__(config=config or Elfving2010PipelineConfig())

    def _build_model(self) -> Elfving2010Model:
        """Elfving (2010) single-tree growth with the Elfving (2009) stand calibration."""
        return Elfving2010Model()

    # --- Introspection (Describable) ---

    @property
    def component_id(self) -> str:
        """Stable identifier for the Elfving 2010 composite pipeline."""
        return "elfving_2010_composite"

    @property
    def source(self) -> SourceReference:
        """Bibliographic provenance for the growth model this pipeline projects with."""
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
        """The growth model, plus everything the composite workflow composes."""
        return (self._model, *super().components)

    # --- Model inputs ---

    def _model_inputs(self) -> Elfving2010Inputs:
        """The typed site and stand facts Elfving (2010) steps with, as of now.

        These used to be twelve string keys written onto ``ctx.attrs`` after the
        context was built, where a mistyped name was indistinguishable from a site
        that had none of that value and only surfaced as a default -- or an
        exception -- once a growth kernel reached for it.

        Raises:
            RuntimeError: If no site has been set.
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


def build_elfving_2010_pipeline(
    config: Elfving2010PipelineConfig | None = None,
) -> Elfving2010Pipeline:
    """Build the Elfving 2010 composite Sweden pipeline for hybrid projection."""
    return Elfving2010Pipeline(config=config)
