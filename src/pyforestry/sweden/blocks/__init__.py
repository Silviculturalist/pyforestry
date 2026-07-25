"""Swedish composable building blocks (GrowthModel adapters and model systems).

Symbols are imported from their canonical ``blocks/`` modules (not through
facade stubs) to keep a single source of truth and avoid circular import chains.
"""

from pyforestry.sweden.mortality.naslund_1986 import Naslund1986DamageModel

from .eko1985 import (
    DominantHeightObservation,
    Eko1985Cohort,
    Eko1985Model,
    Eko1985SiteContext,
    Eko1985Stand,
    RegionSE,
)
from .elfving_1982 import (
    HuginCropTreeProbability,
    HuginMeanHeightModel,
    NfiRegion,
    NyskogReconstruction,
    NyskogReconstructionSummary,
    RegenerationType,
)
from .elfving_2010 import Elfving2010Config, Elfving2010Model
from .elfving_hagglund_1975 import ElfvingHagglundInitialStand
from .eriksson_1976 import (
    Eriksson1976ManagementSchedule,
    Eriksson1976Model,
    Eriksson1976Stand,
    SimulationResult,
    StandInit,
    ThinningProgram,
    ThinningRequest,
    estimate_initial_stand,
    simulate,
)
from .nystrom_soderberg_1987 import NystromSoderberg1987
from .persson_1992 import (
    Persson1992Model,
    Persson1992Stand,
    PerssonSimulationResult,
    PerssonStandInit,
    PerssonThinningProgram,
    PerssonThinningRequest,
    persson_estimate_initial_stand,
    persson_simulate,
)
from .petterson_1955 import (
    PETTERSON_VARIANTS,
    Petterson1955Model,
    Petterson1955Stand,
    PettersonSimulationResult,
    PettersonStandInit,
    PettersonThinningProgram,
    PettersonVariant,
    PettersonYieldRow,
    petterson_simulate,
)
from .soderberg_1986_growth import Soderberg1986Config, Soderberg1986Model

__all__ = [
    "DominantHeightObservation",
    "Eko1985Cohort",
    "Eko1985Model",
    "Eko1985SiteContext",
    "Eko1985Stand",
    "RegionSE",
    "HuginCropTreeProbability",
    "HuginMeanHeightModel",
    "NfiRegion",
    "NyskogReconstruction",
    "NyskogReconstructionSummary",
    "RegenerationType",
    "Elfving2010Config",
    "Elfving2010Model",
    "ElfvingHagglundInitialStand",
    "Eriksson1976ManagementSchedule",
    "Eriksson1976Model",
    "Eriksson1976Stand",
    "SimulationResult",
    "StandInit",
    "ThinningProgram",
    "ThinningRequest",
    "estimate_initial_stand",
    "simulate",
    "Naslund1986DamageModel",
    "NystromSoderberg1987",
    "PETTERSON_VARIANTS",
    "Petterson1955Model",
    "Petterson1955Stand",
    "PettersonSimulationResult",
    "PettersonStandInit",
    "PettersonThinningProgram",
    "PettersonVariant",
    "PettersonYieldRow",
    "petterson_simulate",
    "Persson1992Model",
    "Persson1992Stand",
    "PerssonSimulationResult",
    "PerssonStandInit",
    "PerssonThinningProgram",
    "PerssonThinningRequest",
    "persson_estimate_initial_stand",
    "persson_simulate",
    "Soderberg1986Config",
    "Soderberg1986Model",
]
