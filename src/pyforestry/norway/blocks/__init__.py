"""Simulation-facing thin model facades for Norway equations."""

from .allen_2020 import Allen2020Config, Allen2020GrowthModel, Allen2020Model
from .bollandsas import Bollandsas2008, Bollandsas2008AdapterConfig, Bollandsas2008GrowthModel
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
    "Allen2020Model",
    "Allen2020Config",
    "Allen2020GrowthModel",
    "KuehnePineModel",
    "KuehnePineAdapterConfig",
    "KuehnePineGrowthModel",
    "Bollandsas2008",
    "Bollandsas2008AdapterConfig",
    "Bollandsas2008GrowthModel",
    "Maleki2022ModelNorway",
    "Maleki2022Config",
    "Maleki2022GrowthModel",
]
