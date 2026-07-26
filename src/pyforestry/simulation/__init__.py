"""Simulation-facing views and orchestration helpers."""

from .contracts import (
    ActionEvent,
    AssertionResult,
    ParityCase,
    SimulationPreset,
    StageContract,
)
from .dp import (
    DeterministicAdapter,
    ModelViewStateKey,
    PartKey,
    SimulationProvenance,
    decode_model_views,
    encode_model_views,
    simulate_one_step_pure,
)
from .model_view import InventoryView, SpatialTreeView, StandMetricView
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
    "InventoryView",
    "SpatialTreeView",
    "StandMetricView",
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
    "DeterministicAdapter",
    "ModelViewStateKey",
    "PartKey",
    "SimulationProvenance",
    "decode_model_views",
    "encode_model_views",
    "simulate_one_step_pure",
]
