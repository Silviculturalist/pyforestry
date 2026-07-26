"""Sweden simulation presets and orchestration entrypoints."""

from .mortality import (
    MortalityConfig,
    MortalityContext,
    MortalityEngine,
    MortalityHistoryConditions,
    MortalityResult,
    MortalityRunConfig,
    MortalityRunResult,
    MortalitySiteConditions,
    MortalityStandConditions,
    MortalityTreeRecord,
)
from .orchestration import (
    PresetRunResult,
    emit_scenario_artifact_contract,
    load_scenario_summary,
    validate_artifact_contract,
)
from .presets import (
    Elfving2010Pipeline,
    Elfving2010PipelineConfig,
    Soderberg1986Pipeline,
    Soderberg1986PipelineConfig,
    build_baseline_scenario_config,
    build_elfving_2010_pipeline,
    build_soderberg_1986_pipeline,
    get_pipeline,
    get_scenario_config,
)

__all__ = [
    "MortalityConfig",
    "MortalityContext",
    "MortalityEngine",
    "MortalityHistoryConditions",
    "MortalityResult",
    "MortalityRunConfig",
    "MortalityRunResult",
    "MortalitySiteConditions",
    "MortalityStandConditions",
    "MortalityTreeRecord",
    "PresetRunResult",
    "Elfving2010PipelineConfig",
    "Elfving2010Pipeline",
    "Soderberg1986PipelineConfig",
    "Soderberg1986Pipeline",
    "build_baseline_scenario_config",
    "build_elfving_2010_pipeline",
    "build_soderberg_1986_pipeline",
    "get_pipeline",
    "get_scenario_config",
    "load_scenario_summary",
    "emit_scenario_artifact_contract",
    "validate_artifact_contract",
]
