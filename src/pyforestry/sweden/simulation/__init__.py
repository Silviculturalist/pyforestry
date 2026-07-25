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
    load_scenario_summary,
    run_sweden_preset,
    validate_artifact_contract,
)
from .presets import (
    Elfving2010CompositePreset,
    Elfving2010CompositePresetConfig,
    Soderberg1986CompositePreset,
    Soderberg1986CompositePresetConfig,
    build_baseline_preset,
    build_elfving_2010_composite_preset,
    build_soderberg_1986_composite_preset,
    get_preset,
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
    "Elfving2010CompositePresetConfig",
    "Elfving2010CompositePreset",
    "Soderberg1986CompositePresetConfig",
    "Soderberg1986CompositePreset",
    "build_baseline_preset",
    "build_elfving_2010_composite_preset",
    "build_soderberg_1986_composite_preset",
    "get_preset",
    "load_scenario_summary",
    "run_sweden_preset",
    "validate_artifact_contract",
]
