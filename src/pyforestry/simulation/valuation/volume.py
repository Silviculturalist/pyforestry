"""Volume conversion utilities for valuation workflows."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Dict, Mapping, MutableMapping, Tuple, Type

from pyforestry.base.helpers.bucking import BuckingConfig, QualityType
from pyforestry.base.pricelist import Pricelist
from pyforestry.base.taper import Taper
from pyforestry.base.timber_bucking.nasberg_1985 import Nasberg_1985_BranchBound

from .removals import StandRemovalLedger, TreeRemoval


@dataclass(frozen=True)
class PieceRecord:
    """Representation of one bucked piece aggregated across identical trees."""

    cohort_id: str
    species: str
    quality: QualityType
    length_m: float
    top_diameter_cm: float
    volume_m3: float
    value: float
    weight: float

    def as_mapping(self) -> Dict[str, Any]:
        """Return a plain mapping useful for serialisation."""

        return {
            "cohort_id": self.cohort_id,
            "species": self.species,
            "quality": self.quality.name,
            "length_m": self.length_m,
            "top_diameter_cm": self.top_diameter_cm,
            "volume_m3": self.volume_m3,
            "value": self.value,
            "weight": self.weight,
        }


@dataclass(frozen=True)
class VolumeResult:
    """Container describing the outcome of a valuation conversion."""

    descriptor: "VolumeDescriptor"
    pieces: Tuple[PieceRecord, ...]
    total_value: float
    volume_by_quality: Mapping[QualityType, float]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def total_volume(self) -> float:
        """Return the total merchantable volume (m³)."""

        return float(sum(piece.volume_m3 for piece in self.pieces))


@dataclass(kw_only=True)
class VolumeDescriptor:
    """Base descriptor for conversion inputs."""

    ledger: StandRemovalLedger
    metadata: MutableMapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.metadata = dict(self.metadata)
        if self.ledger.stand_id:
            self.metadata.setdefault("stand_id", self.ledger.stand_id)

    def evaluate(self) -> VolumeResult:
        """Return an empty result for descriptors that cannot produce volume."""

        return VolumeResult(
            descriptor=self,
            pieces=(),
            total_value=0.0,
            volume_by_quality={quality: 0.0 for quality in QualityType},
            metadata=dict(self.metadata),
        )


@dataclass(kw_only=True)
class EmptyVolumeDescriptor(VolumeDescriptor):
    """Descriptor used when no removals are present."""

    reason: str = "empty"

    def evaluate(self) -> VolumeResult:  # type: ignore[override]
        base = super().evaluate()
        metadata = dict(base.metadata)
        metadata.setdefault("reason", self.reason)
        return VolumeResult(
            descriptor=base.descriptor,
            pieces=base.pieces,
            total_value=base.total_value,
            volume_by_quality=base.volume_by_quality,
            metadata=metadata,
        )


@dataclass(kw_only=True)
class TreeVolumeDescriptor(VolumeDescriptor):
    """Descriptor based on individual tree removals."""

    removals: Tuple[TreeRemoval, ...]
    pricelist: Pricelist
    taper_class: Type[Taper]
    bucking_config: BuckingConfig = field(
        default_factory=lambda: BuckingConfig(save_sections=True)
    )
    bucker_cls: Type[Nasberg_1985_BranchBound] = Nasberg_1985_BranchBound
    min_diam_dead_wood: float = 0.0

    def evaluate(self) -> VolumeResult:  # type: ignore[override]
        if not self.removals:
            return super().evaluate()

        config = self.bucking_config
        if not isinstance(config, BuckingConfig):
            raise TypeError("Bucking configuration must be a BuckingConfig instance.")
        if not config.save_sections:
            config = replace(config, save_sections=True)

        pieces: list[PieceRecord] = []
        total_value = 0.0
        volume_by_quality: Dict[QualityType, float] = {quality: 0.0 for quality in QualityType}

        for removal in self.removals:
            timber = removal.to_timber()
            bucker = self.bucker_cls(timber, self.pricelist, self.taper_class)
            result = bucker.calculate_tree_value(
                min_diam_dead_wood=self.min_diam_dead_wood,
                config=config,
            )
            weight = removal.weight
            total_value += float(result.total_value) * weight
            for idx, volume in enumerate(result.volume_per_quality):
                try:
                    quality = QualityType(idx)
                except ValueError:
                    continue
                volume_by_quality[quality] += float(volume) * weight

            sections = result.sections or []
            if sections:
                for section in sections:
                    length_m = (section.end_point - section.start_point) / 10.0
                    pieces.append(
                        PieceRecord(
                            cohort_id=removal.cohort_id,
                            species=removal.species_name,
                            quality=section.quality,
                            length_m=length_m,
                            top_diameter_cm=float(section.top_diameter),
                            volume_m3=float(section.volume) * weight,
                            value=float(section.value) * weight,
                            weight=weight,
                        )
                    )
            else:
                # Fall back to aggregating the total sk volume when sections are absent.
                pieces.append(
                    PieceRecord(
                        cohort_id=removal.cohort_id,
                        species=removal.species_name,
                        quality=QualityType.Undefined,
                        length_m=removal.height_m,
                        top_diameter_cm=removal.diameter_cm,
                        volume_m3=float(result.vol_sk_ub) * weight,
                        value=float(result.total_value) * weight,
                        weight=weight,
                    )
                )

        metadata = dict(self.metadata)
        metadata.setdefault("cohort_count", len(self.ledger.cohorts))
        metadata.setdefault("tree_count", self.ledger.tree_count)

        return VolumeResult(
            descriptor=self,
            pieces=tuple(pieces),
            total_value=float(total_value),
            volume_by_quality=volume_by_quality,
            metadata=metadata,
        )


class VolumeConnector:
    """Resolve removal ledgers into volume descriptors and valuation results."""

    def __init__(self, *, bucker_cls: Type[Nasberg_1985_BranchBound] | None = None) -> None:
        self._bucker_cls = bucker_cls or Nasberg_1985_BranchBound

    def describe(self, model_view: Any, ledger: StandRemovalLedger) -> VolumeDescriptor:
        """Return the descriptor describing ``ledger`` for ``model_view``."""

        if not isinstance(ledger, StandRemovalLedger):
            raise TypeError("ledger must be a StandRemovalLedger instance.")
        if ledger.is_empty:
            return EmptyVolumeDescriptor(ledger=ledger, metadata=dict(ledger.metadata))

        removals = tuple(ledger.iter_tree_removals())
        pricelist = self._resolve_pricelist(model_view)
        taper_class = self._resolve_taper_class(model_view)
        config = self._resolve_bucking_config(model_view)
        min_dead = float(getattr(model_view, "min_diam_dead_wood", 0.0))

        return TreeVolumeDescriptor(
            ledger=ledger,
            removals=removals,
            pricelist=pricelist,
            taper_class=taper_class,
            bucking_config=config,
            bucker_cls=self._bucker_cls,
            min_diam_dead_wood=min_dead,
            metadata=dict(ledger.metadata),
        )

    def connect(self, model_view: Any, ledger: StandRemovalLedger) -> VolumeResult:
        """Return the evaluated volume result for ``ledger`` and ``model_view``."""

        descriptor = self.describe(model_view, ledger)
        return descriptor.evaluate()

    @staticmethod
    def _resolve_pricelist(model_view: Any) -> Pricelist:
        candidates = (
            getattr(model_view, "pricelist", None),
            getattr(model_view, "price_list", None),
        )
        for candidate in candidates:
            resolved = candidate() if callable(candidate) else candidate
            if isinstance(resolved, Pricelist):
                return resolved
        raise AttributeError("Model view must provide a Pricelist via 'pricelist'.")

    @staticmethod
    def _resolve_taper_class(model_view: Any) -> Type[Taper]:
        candidate = getattr(model_view, "taper_class", None)
        if callable(candidate) and not isinstance(candidate, type):
            candidate = candidate()
        if candidate is None:
            getter = getattr(model_view, "get_taper_class", None)
            candidate = getter() if callable(getter) else None
        if not isinstance(candidate, type) or not issubclass(candidate, Taper):
            raise AttributeError("Model view must supply a taper_class derived from Taper.")
        return candidate

    @staticmethod
    def _resolve_bucking_config(model_view: Any) -> BuckingConfig:
        candidate = getattr(model_view, "bucking_config", None)
        if callable(candidate):
            candidate = candidate()
        if candidate is None:
            return BuckingConfig(save_sections=True)
        if not isinstance(candidate, BuckingConfig):
            raise TypeError("bucking_config must be a BuckingConfig instance.")
        if not candidate.save_sections:
            candidate = replace(candidate, save_sections=True)
        return candidate


__all__ = [
    "PieceRecord",
    "VolumeResult",
    "VolumeDescriptor",
    "EmptyVolumeDescriptor",
    "TreeVolumeDescriptor",
    "VolumeConnector",
]
