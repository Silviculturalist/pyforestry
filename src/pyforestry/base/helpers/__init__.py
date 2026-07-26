"""Convenience imports for common helper types."""

from importlib import import_module
from typing import TYPE_CHECKING

# Suggested pyforestry/Helpers/__init__.py
# ruff: noqa: F401, F403, F405
# isort: off

# From TreeSpecies.py
from .tree_species import (
    BETULA_PENDULA,  # noqa: F401
    BETULA_PUBESCENS,  # noqa: F401
    GLOBAL_TREE_SPECIES,  # noqa: F401
    # Constants for common species are also defined here, e.g.:
    PICEA_ABIES,  # noqa: F401
    PINUS_SYLVESTRIS,  # noqa: F401
    TreeGenus,  # noqa: F401
    TreeName,  # noqa: F401
    TreeSpecies,  # The regional container class
    parse_tree_species,
)

# From Primitives.py
from .primitives import *  # noqa: F401,F403
from .tree_metrics import basal_area_larger
from .height_models import (
    CurveHeightSource,
    MeasuredHeightSource,
    NaslundHeightCurve,
    resolve_height_source,
)
from .top_height import compute_top_height
from .tree import Tree
from .bitterlich_angle_count import AngleCount, AngleCountAggregator
from .plot import CircularPlot
from .stand import Stand, StandMetricAccessor
from .utils import enum_code
from .bucking import (
    BuckingConfig,
    BuckingResult,
    CrossCutSection,
    QualityType,
    _TreeCache,
)

# isort: on

_SIMULATION_EXPORTS = [
    "SimulationContext",
    "ActionSpec",
    "GrowthModel",
    "ExampleStandGeneralModel",
    "Requirements",
    "ContextEnsemble",
    "PythonEngine",
    "BatchEngine",
    "AdapterRegistry",
    "AngleCountToPseudoTreesAdapter",
    "AngleCountToSpatialPseudoTreesAdapter",
    "AngleCountToDiameterClassAdapter",
    "TreeListToDiameterClassAdapter",
    "TreeListToSpatialAdapter",
]
_SIMULATION_EXPORT_SET = set(_SIMULATION_EXPORTS)

if TYPE_CHECKING:  # pragma: no cover - for static checkers only
    from pyforestry.base.simulation import (  # noqa: F401
        ActionSpec,
        AdapterRegistry,
        AngleCountToDiameterClassAdapter,
        AngleCountToPseudoTreesAdapter,
        AngleCountToSpatialPseudoTreesAdapter,
        BatchEngine,
        ContextEnsemble,
        ExampleStandGeneralModel,
        GrowthModel,
        PythonEngine,
        Requirements,
        SimulationContext,
        TreeListToDiameterClassAdapter,
        TreeListToSpatialAdapter,
    )

__all__ = [
    # TreeSpecies components
    "TreeName",
    "TreeGenus",
    "tree_species",
    "parse_tree_species",
    "GLOBAL_TREE_SPECIES",
    "PICEA_ABIES",
    "PINUS_SYLVESTRIS",
    "BETULA_PENDULA",
    "BETULA_PUBESCENS",  # Example species constants
    # Primitives components
    "Age",
    "AgeMeasurement",
    "Diameter_cm",
    "diameter_to_basal_area_cm2",
    "basal_area_cm2_to_diameter_cm",
    "diameter_growth_to_basal_area_growth_cm2",
    "basal_area_growth_cm2_to_diameter_growth_cm",
    "Position",
    "SiteIndexValue",
    "StandBasalArea",
    "StandVolume",
    "Stems",
    "TopHeightDefinition",
    "TopHeightMeasurement",
    "QuadraticMeanDiameter",
    "LoreysMeanHeight",
    "AtomicVolume",
    "CompositeVolume",
    "AngleCount",
    "AngleCountAggregator",
    "Tree",
    "basal_area_larger",
    "NaslundHeightCurve",
    "MeasuredHeightSource",
    "CurveHeightSource",
    "resolve_height_source",
    "compute_top_height",
    # Base components
    "CircularPlot",
    "Stand",
    "StandMetricAccessor",
    "SiteBase",
    "enum_code",
    "CrossCutSection",
    "BuckingResult",
    "BuckingConfig",
    "_TreeCache",
    "QualityType",
] + _SIMULATION_EXPORTS


def __getattr__(name):
    """Lazily resolve simulation exports to avoid import cycles at module import time."""
    if name in _SIMULATION_EXPORT_SET:
        sim_mod = import_module("pyforestry.base.simulation")
        attr = getattr(sim_mod, name)
        globals()[name] = attr
        return attr
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
