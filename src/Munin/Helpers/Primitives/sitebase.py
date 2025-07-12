from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True)
class SiteBase(ABC):
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        self.compute_attributes()

    @abstractmethod
    def compute_attributes(self) -> None:
        """
        Compute site-specific derived attributes.
        Subclasses must implement this method.
        """
        pass