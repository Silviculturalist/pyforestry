"""Sweden's runnable pipelines and its scenario configuration.

This package holds two unrelated kinds of thing, and they used to share the word
"preset", which meant the name told you nothing:

* **Pipelines** -- :class:`Elfving2010Pipeline` and :class:`Soderberg1986Pipeline`
  are stateful simulators. You initialize one on a site, step it, and read a
  projection out of it.
* **Scenario configuration** -- :class:`ScenarioConfig` is a frozen dataclass of
  seeds, stage names, rulesets and required artifacts. It runs nothing.

``get_scenario_config`` reaches the second. There is deliberately no single
lookup that returns "a preset": the two have no common interface, and the one
that used to exist was typed as returning the configuration, so it could not
reach either simulator.
"""

from ._common import ScenarioConfig
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

#: Every runnable pipeline, by the name a caller would type. This is what
#: ``get_preset`` could not offer: it was typed to return a ``ScenarioConfig``,
#: so the two real simulators were unreachable through the one discovery
#: entrypoint the package had.
PIPELINE_BUILDERS = {
    "elfving_2010": build_elfving_2010_pipeline,
    "soderberg_1986": build_soderberg_1986_pipeline,
}


def get_scenario_config(scenario_id: str) -> ScenarioConfig:
    """Build the scenario configuration for a supported scenario id.

    Raises:
        ValueError: If ``scenario_id`` is not one this package defines.
    """
    if scenario_id == "baseline":
        return build_baseline_scenario_config()
    raise ValueError(f"Unsupported scenario_id: {scenario_id!r}. Known ids: 'baseline'.")


def get_pipeline(name: str, config=None):
    """Build a runnable pipeline by name.

    Args:
        name: One of :data:`PIPELINE_BUILDERS`.
        config: The pipeline's own config dataclass, or ``None`` for its defaults.

    Raises:
        ValueError: If ``name`` is not a known pipeline.
    """
    try:
        builder = PIPELINE_BUILDERS[name]
    except KeyError:
        known = ", ".join(sorted(PIPELINE_BUILDERS))
        raise ValueError(f"Unknown pipeline {name!r}. Known pipelines: {known}.") from None
    return builder(config) if config is not None else builder()


__all__ = [
    "PIPELINE_BUILDERS",
    "ScenarioConfig",
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
