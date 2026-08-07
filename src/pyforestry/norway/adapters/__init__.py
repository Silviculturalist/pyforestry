"""Runtime bindings for Norwegian equations — glue, not science.

Same contract as :mod:`pyforestry.sweden.adapters`: each module binds equation
kernels from a domain package to the simulation runtime and carries no
scientific coefficient literals of its own. Norway ships no whole growth-and-
yield system yet, so there is no ``norway/systems`` package beside this one;
when one arrives it goes there, not here.
"""

from .allen_2020 import Allen2020Config, Allen2020GrowthModel, Allen2020Model
from .bollandsas_2008 import (
    Bollandsas2008,
    Bollandsas2008AdapterConfig,
    Bollandsas2008GrowthModel,
)
from .kuehne_2022 import (
    KuehnePineAdapterConfig,
    KuehnePineGrowthModel,
    KuehnePineModel,
)
from .maleki_2022 import (
    Maleki2022Config,
    Maleki2022GrowthModel,
    Maleki2022ModelNorway,
)

__all__ = [
    "Allen2020Config",
    "Allen2020GrowthModel",
    "Allen2020Model",
    "Bollandsas2008",
    "Bollandsas2008AdapterConfig",
    "Bollandsas2008GrowthModel",
    "KuehnePineAdapterConfig",
    "KuehnePineGrowthModel",
    "KuehnePineModel",
    "Maleki2022Config",
    "Maleki2022GrowthModel",
    "Maleki2022ModelNorway",
]
