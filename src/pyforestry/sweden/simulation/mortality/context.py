"""Unified mortality context models for Sweden simulation orchestration."""

from pyforestry.sweden.mortality.types import (
    MortalityConfig,
    MortalityContext,
    MortalityHistoryConditions,
    MortalityRealizationMode,
    MortalityResult,
    MortalitySiteConditions,
    MortalityStandConditions,
    MortalityTreeModel,
    MortalityTreeRecord,
)

# Deprecated aliases retained for backward compatibility; prefer the canonical
# ``MortalityConfig`` / ``MortalityResult``.
MortalityRunConfig = MortalityConfig
MortalityRunResult = MortalityResult


__all__ = [
    "MortalityConfig",
    "MortalityContext",
    "MortalityHistoryConditions",
    "MortalityRealizationMode",
    "MortalityResult",
    "MortalityRunConfig",
    "MortalityRunResult",
    "MortalitySiteConditions",
    "MortalityStandConditions",
    "MortalityTreeModel",
    "MortalityTreeRecord",
]
