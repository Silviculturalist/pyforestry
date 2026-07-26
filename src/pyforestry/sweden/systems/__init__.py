"""Whole published growth-and-yield systems for Sweden.

Each module here is one publication reproduced end to end: its own coefficients,
its own state, its own stepping rules. Eriksson (1976), Persson (1992), Petterson
(1955), Ekö (1985) and Elfving & Hägglund (1975) are not assemblies of
interchangeable equations — the parts were fitted together and only agree with
the printed yield tables when used together. Keeping each one whole is what makes
it checkable against its source.

That is the difference from :mod:`pyforestry.sweden.adapters`, and it runs in one
direction only: a system may carry coefficients *and* ship the
:class:`~pyforestry.base.simulation.growth_model.GrowthModel` that drives it,
because a self-contained system owns its own interface. An adapter may not carry
coefficients at all.

Individual published equations that stand on their own — a volume function, a
site-index curve, a bark thickness model — belong in the domain packages
(``sweden/volume``, ``sweden/siteindex``, ``sweden/bark``, …) instead.
"""

from .eko1985 import (
    DominantHeightObservation,
    Eko1985Cohort,
    Eko1985Model,
    Eko1985SiteContext,
    Eko1985Stand,
    RegionSE,
)
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

__all__ = [
    "DominantHeightObservation",
    "Eko1985Cohort",
    "Eko1985Model",
    "Eko1985SiteContext",
    "Eko1985Stand",
    "ElfvingHagglundInitialStand",
    "Eriksson1976ManagementSchedule",
    "Eriksson1976Model",
    "Eriksson1976Stand",
    "NystromSoderberg1987",
    "PETTERSON_VARIANTS",
    "Persson1992Model",
    "Persson1992Stand",
    "PerssonSimulationResult",
    "PerssonStandInit",
    "PerssonThinningProgram",
    "PerssonThinningRequest",
    "Petterson1955Model",
    "Petterson1955Stand",
    "PettersonSimulationResult",
    "PettersonStandInit",
    "PettersonThinningProgram",
    "PettersonVariant",
    "PettersonYieldRow",
    "RegionSE",
    "SimulationResult",
    "StandInit",
    "ThinningProgram",
    "ThinningRequest",
    "estimate_initial_stand",
    "persson_estimate_initial_stand",
    "persson_simulate",
    "petterson_simulate",
    "simulate",
]
