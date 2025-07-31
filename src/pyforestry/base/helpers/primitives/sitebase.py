"""Abstract base class for geographic site definitions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SiteBase(ABC):
    """Base dataclass for location information used across site models.

    Attributes
    ----------
    latitude : float
        Geographic latitude in decimal degrees.
    longitude : float
        Geographic longitude in decimal degrees.
    """

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        """Trigger computation of derived site attributes after initialization."""
        self.compute_attributes()

    @abstractmethod
    def compute_attributes(self) -> None:
        """
        Compute site-specific derived attributes.
        Subclasses must implement this method.
        """
        pass
