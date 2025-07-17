"""Dataclasses defining Swedish site classification codes."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Vegetation:
    """Vegetation type with a productivity index."""

    code: int
    swedish_name: str
    english_name: str
    index: float


@dataclass(frozen=True)
class BottomLayerType:
    """Main ground vegetation category."""

    code: int
    english_name: str
    swedish_name: str


@dataclass(frozen=True)
class SoilWaterCat:
    """Qualitative class describing soil water availability."""

    code: int
    swedish_description: str
    english_description: str


@dataclass(frozen=True)
class SoilDepthCat:
    """Categorical depth to parent material."""

    code: int
    swedish_description: str
    english_description: str


@dataclass(frozen=True)
class SoilTextureCategory:
    """Soil texture group such as clay or sand."""

    code: int
    swedish_name: str
    english_name: str
    short_name: str


@dataclass(frozen=True)
class SoilMoistureData:
    """Relative soil moisture description."""

    code: int
    swedish_description: str
    english_description: str


@dataclass(frozen=True)
class PeatHumificationCat:
    """Degree of humification for peat soils."""

    code: int
    swedish_description: str
    english_description: str


@dataclass(frozen=True)
class CountyData:
    """Swedish county identifier."""

    code: int
    label: str  # Descriptive string label


@dataclass(frozen=True)
class ClimateZoneData:
    """Zonal climate classification."""

    code: int
    label: str  # e.g., "M1", "K2"
    description: str  # Descriptive name
