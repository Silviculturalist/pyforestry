"""Scenario presets, harvest valuation, and shared run services.

What was here before -- ``StageRuntime``, ``Stage``, ``StandComposite``,
``StandPart``, ``StandAction`` and their dispatch types -- was a per-part
scheduling runtime. Every model in this package steps the whole stand, so its one
consumer had to make N-1 of every N stage invocations inert with a latch, and
bypassed the dispatch machinery entirely for thinning. The scheduler that
replaced it is :mod:`pyforestry.base.simulation.pipeline`, which schedules stands.

``CheckpointSerializer`` went with it: it serialised a composite, and
:meth:`SimulationContext.checkpoint` is the checkpoint mechanism that has a
consumer.
"""

from .contracts import (
    AssertionResult,
    ParityCase,
    SimulationPreset,
)
from .presets import ScenarioConfigBase
from .valuation import (
    CohortRemoval,
    EmptyVolumeDescriptor,
    PieceRecord,
    StandRemovalLedger,
    TreeRemoval,
    TreeVolumeDescriptor,
    ValuationSettings,
    ValuationStep,
    VolumeConnector,
    VolumeDescriptor,
    VolumeResult,
)

__all__ = [
    "SimulationPreset",
    "ScenarioConfigBase",
    "ParityCase",
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
    "ValuationSettings",
    "ValuationStep",
]
