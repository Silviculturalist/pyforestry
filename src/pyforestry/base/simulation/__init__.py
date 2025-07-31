"""Interfaces for stand growth simulation modules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Sequence

from pyforestry.base.helpers import Stand, TreeName


@dataclass
class GrowthModule(ABC):
    """Update existing trees to account for growth during a time step."""

    supported_species: Sequence[TreeName] = field(default_factory=list)

    def supports(self, species: TreeName) -> bool:
        """Return ``True`` if ``species`` is handled by this module."""
        return species in self.supported_species

    @abstractmethod
    def apply(self, stand: Stand) -> None:
        """Modify ``stand`` in-place to reflect tree growth."""


@dataclass
class IngrowthModule(ABC):
    """Add newly established trees to the stand."""

    supported_species: Sequence[TreeName] = field(default_factory=list)

    def supports(self, species: TreeName) -> bool:
        """Return ``True`` if ``species`` is handled by this module."""
        return species in self.supported_species

    @abstractmethod
    def apply(self, stand: Stand) -> None:
        """Insert new trees into ``stand``."""


@dataclass
class MortalityModule(ABC):
    """Remove trees that die between time steps."""

    supported_species: Sequence[TreeName] = field(default_factory=list)

    def supports(self, species: TreeName) -> bool:
        """Return ``True`` if ``species`` is handled by this module."""
        return species in self.supported_species

    @abstractmethod
    def apply(self, stand: Stand) -> None:
        """Delete dead trees from ``stand``."""


@dataclass
class CalamityModule(ABC):
    """Optional module simulating stochastic disturbances such as storms."""

    supported_species: Sequence[TreeName] = field(default_factory=list)

    def supports(self, species: TreeName) -> bool:
        """Return ``True`` if ``species`` is handled by this module."""
        return species in self.supported_species

    @abstractmethod
    def apply(self, stand: Stand) -> None:
        """Apply calamity effects to ``stand``."""


@dataclass
class SimulationRuleset(ABC):
    """Collection of modules defining a growth simulation."""

    growth: GrowthModule
    ingrowth: IngrowthModule
    mortality: MortalityModule
    calamity: CalamityModule | None = None

    @abstractmethod
    def grow(self, stand: Stand) -> None:
        """Advance ``stand`` one step using the configured modules.

        Implementations should execute the modules in the following order:

        1. ``GrowthModule`` to update existing trees.
        2. ``IngrowthModule`` to add new recruits.
        3. ``MortalityModule`` to remove trees that died.
        4. ``CalamityModule`` (if present) for disturbances.
        """
