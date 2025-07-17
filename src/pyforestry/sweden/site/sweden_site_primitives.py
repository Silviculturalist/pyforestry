from dataclasses import dataclass


@dataclass(frozen=True)
class Vegetation:
    code: int
    swedish_name: str
    english_name: str
    index: float


@dataclass(frozen=True)
class BottomLayerType:
    code: int
    english_name: str
    swedish_name: str


@dataclass(frozen=True)
class SoilWaterCat:
    code: int
    swedish_description: str
    english_description: str


@dataclass(frozen=True)
class SoilDepthCat:
    code: int
    swedish_description: str
    english_description: str


@dataclass(frozen=True)
class SoilTextureCategory:
    code: int
    swedish_name: str
    english_name: str
    short_name: str


@dataclass(frozen=True)
class SoilMoistureData:
    code: int
    swedish_description: str
    english_description: str


@dataclass(frozen=True)
class PeatHumificationCat:
    code: int
    swedish_description: str
    english_description: str


@dataclass(frozen=True)
class CountyData:
    code: int
    label: str  # Descriptive string label


@dataclass(frozen=True)
class ClimateZoneData:
    code: int
    label: str  # e.g., "M1", "K2"
    description: str  # Descriptive name
