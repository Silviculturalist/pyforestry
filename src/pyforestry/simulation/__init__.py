"""Staged simulation runtime: stages, composites, valuation and shared services."""

from .contracts import (
    ActionEvent,
    AssertionResult,
    ParityCase,
    SimulationPreset,
    StageContract,
)
from .presets import ScenarioPresetBase
from .stage_runtime import (
    DisturbanceStage,
    GrowthStage,
    ManagementStage,
    Stage,
    StageAction,
    StageRuntime,
    ValuationStage,
)
from .stand_composite import (
    DispatchRecord,
    DispatchResult,
    StandAction,
    StandComposite,
    StandPart,
)
from .valuation import (
    CohortRemoval,
    EmptyVolumeDescriptor,
    PieceRecord,
    StandRemovalLedger,
    TreeRemoval,
    TreeVolumeDescriptor,
    VolumeConnector,
    VolumeDescriptor,
    VolumeResult,
)

# ``GrowthModule`` was renamed to ``StageRuntime``; keep the old name as a
# deprecated alias for backward compatibility.
GrowthModule = StageRuntime

__all__ = [
    "DispatchRecord",
    "DispatchResult",
    "StandAction",
    "StandComposite",
    "StandPart",
    "StageRuntime",
    "GrowthModule",
    "GrowthStage",
    "ManagementStage",
    "DisturbanceStage",
    "ValuationStage",
    "Stage",
    "StageAction",
    "StageContract",
    "SimulationPreset",
    "ScenarioPresetBase",
    "ParityCase",
    "ActionEvent",
    "AssertionResult",
    "StandRemovalLedger",
    "CohortRemoval",
    "TreeRemoval",
    "VolumeDescriptor",
    "EmptyVolumeDescriptor",
    "TreeVolumeDescriptor",
    "VolumeResult",
    "VolumeConnector",
    "PieceRecord",
]
