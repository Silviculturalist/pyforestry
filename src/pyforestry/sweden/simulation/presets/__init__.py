"""Sweden's runnable pipelines and its scenario configuration.

This package holds two unrelated kinds of thing, and they used to share the word
"preset", which meant the name told you nothing:

* **Pipelines** -- :class:`Elfving2010Pipeline` and :class:`Soderberg1986Pipeline`
  are stateful simulators. You initialize one on a site, step it, and read a
  projection out of it.
* **Scenario configuration** -- :class:`ScenarioConfig` is a frozen dataclass of
  seeds, stage names, rulesets and required artifacts. It declares a run rather
  than being one; :func:`~pyforestry.simulation.scenario.run_scenario` executes
  it and writes the artifacts.

``get_scenario_config`` reaches the second, ``get_pipeline`` the first. There is
deliberately no single lookup that returns "a preset": the two have no common
interface, and the one that used to exist was typed as returning the
configuration, so it could not reach either simulator.
"""

from __future__ import annotations

from typing import Callable

from ._common import ScenarioConfig
from ._composite import CompositePipeline, CompositePipelineConfig
from .baseline import build_baseline_scenario_config
from .elfving_2010_pipeline import (
    Elfving2010Pipeline,
    Elfving2010PipelineConfig,
    build_elfving_2010_pipeline,
)
from .soderberg_1986_pipeline import (
    Soderberg1986Pipeline,
    Soderberg1986PipelineConfig,
    build_soderberg_1986_pipeline,
)

#: Every runnable pipeline, by the name a caller would type -- each pipeline's own
#: ``component_id``.
#:
#: The keys used to be ``"elfving_2010"`` and ``"soderberg_1986"``, which are also
#: the names ``pyforestry.project(model=...)`` accepts, where they mean the bare
#: single-tree growth adapters. One string named two very different things through
#: two entry points: ``project(model="elfving_2010")`` steps trees you supply with
#: Elfving (2010) alone, while ``get_pipeline("elfving_2010")`` reconstructed a
#: stand with NYSKOG and ran nine more models around it. Naming the composites
#: after themselves removes the collision.
PIPELINE_BUILDERS: dict[str, Callable[..., CompositePipeline]] = {
    "elfving_2010_composite": build_elfving_2010_pipeline,
    "soderberg_1986_composite": build_soderberg_1986_pipeline,
}

#: What the old, ambiguous pipeline keys mean now, for the error message.
_RENAMED_PIPELINES = {
    "elfving_2010": "elfving_2010_composite",
    "soderberg_1986": "soderberg_1986_composite",
}


def available_pipelines() -> list[str]:
    """Return every name :func:`get_pipeline` accepts, sorted.

    These are the *composite* pipelines, and they are not everything this package
    can run end to end. A composite is a composition pyforestry assembled: a
    dozen publications that were never fitted to each other, driven through one
    period. The whole published systems -- Eriksson (1976), Ekö (1985), Persson
    (1992), Petterson (1955) -- each project a stand just as completely, but the
    composition is their own author's, so they live in
    :mod:`pyforestry.sweden.systems` and ship their own runner. Ask
    :func:`~pyforestry.sweden.systems.available_systems` for those.

    The split is by whose composition it is, not by what can be run, and reading
    this list as the answer to "what can I project?" understates the package by
    four systems.
    """
    return sorted(PIPELINE_BUILDERS)


def get_scenario_config(scenario_id: str) -> ScenarioConfig:
    """Build the scenario configuration for a supported scenario id.

    Raises:
        ValueError: If ``scenario_id`` is not one this package defines.
    """
    if scenario_id == "baseline":
        return build_baseline_scenario_config()
    raise ValueError(f"Unsupported scenario_id: {scenario_id!r}. Known ids: 'baseline'.")


def get_pipeline(
    name: str,
    config: CompositePipelineConfig | None = None,
) -> CompositePipeline:
    """Build a runnable composite pipeline by name.

    Args:
        name: One of :func:`available_pipelines`.
        config: The pipeline's own config dataclass, or ``None`` for its defaults.

    Returns:
        A stateful simulator: ``initialize(site=...)``, then ``step()`` or
        ``run_projection(...)``. Unlike a
        :class:`~pyforestry.base.simulation.growth_model.GrowthModel` it builds its
        own stand from a site, which is why ``pyforestry.project(stand, ...)``
        cannot drive one.

    Raises:
        ValueError: If ``name`` is not a known pipeline.
    """
    try:
        builder = PIPELINE_BUILDERS[name]
    except KeyError:
        known = ", ".join(available_pipelines())
        renamed = _RENAMED_PIPELINES.get(name)
        hint = (
            f" Did you mean {renamed!r}? {name!r} now names only the single-tree "
            f"growth model of the same publication, which pyforestry.project() runs."
            if renamed
            else ""
        )
        raise ValueError(f"Unknown pipeline {name!r}. Known pipelines: {known}.{hint}") from None
    return builder(config) if config is not None else builder()


__all__ = [
    "PIPELINE_BUILDERS",
    "ScenarioConfig",
    "available_pipelines",
    "build_baseline_scenario_config",
    "Elfving2010PipelineConfig",
    "Elfving2010Pipeline",
    "build_elfving_2010_pipeline",
    "Soderberg1986PipelineConfig",
    "Soderberg1986Pipeline",
    "build_soderberg_1986_pipeline",
    "get_pipeline",
    "get_scenario_config",
]
