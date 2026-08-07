"""Convenience imports for common helper types."""

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
from .utils import enum_code, warn_proportion
from .bucking import (
    BuckingConfig,
    BuckingResult,
    CrossCutSection,
    QualityType,
    _TreeCache,
)

# isort: on

# The names this module used to re-export from the simulation runtime. Kept only
# so ``__getattr__`` can point at their real home rather than saying "no such
# attribute" to code written against the old spelling.
_SIMULATION_NAMES = frozenset(
    {
        "ActionSpec",
        "AdapterRegistry",
        "AngleCountToDiameterClassAdapter",
        "AngleCountToPseudoTreesAdapter",
        "AngleCountToSpatialPseudoTreesAdapter",
        "BatchEngine",
        "ContextEnsemble",
        "ExampleStandGeneralModel",
        "GrowthModel",
        "PythonEngine",
        "Requirements",
        "SimulationContext",
        "TreeListToDiameterClassAdapter",
        "TreeListToSpatialAdapter",
    }
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
    "warn_proportion",
    "CrossCutSection",
    "BuckingResult",
    "BuckingConfig",
    "QualityType",
]


def __getattr__(name):
    """Reject an unknown attribute, and say where the simulation runtime lives.

    This module used to lazily re-export seventeen names from
    ``pyforestry.base.simulation`` -- ``GrowthModel``, ``SimulationContext``,
    every adapter -- so the data-contract layer advertised the simulation runtime
    as its own API and each of those classes had two supported spellings. The
    docstring said the re-export existed to avoid an import cycle, but the cycle
    only ever ran one way: ``base.simulation`` imports ``base.helpers`` and never
    the reverse, so there was nothing to break.
    """
    if name in _SIMULATION_NAMES:
        raise AttributeError(
            f"{name!r} is part of the simulation runtime, not the data contract. "
            f"Import it from pyforestry.base.simulation instead; "
            f"pyforestry.base.helpers no longer re-exports it."
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
