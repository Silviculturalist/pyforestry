"""Volume conversion utilities for valuation workflows.

Pricing a removal needs three things the ledger does not carry: a price list, a
taper function and a bucking configuration. They arrive as one typed
:class:`ValuationSettings`.

That used to be a ``model_view: Any`` -- a name left over from a subsystem this
package no longer has -- resolved by ``getattr`` across four spellings
(``pricelist`` or ``price_list``, ``taper_class`` or ``get_taper_class()``, each
optionally callable). It is the defect :class:`~pyforestry.simulation.valuation.step.ValuationStep`
was written to fix one layer up, where a ledger had been looked for in six
places: several conventions for one value is no convention, and the failure mode
is an object that implements a seventh spelling being read as implementing
nothing.
"""

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
        """Normalize metadata and attach the stand identifier when available."""
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
        """Return an empty result tagged with the reason for emptiness."""
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
        """Run bucking and valuation over the recorded tree removals."""
        config = self.bucking_config
        if not isinstance(config, BuckingConfig):
            raise TypeError("Bucking configuration must be a BuckingConfig instance.")

        if not self.removals:
            return super().evaluate()
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


@dataclass(frozen=True)
class ValuationSettings:
    """What pricing a removal needs beyond the removal itself.

    One typed object, validated when it is built, so a misconfiguration is a
    named error at the call site rather than an ``AttributeError`` raised the
    first time a run happens to thin something.

    Args:
        pricelist: The price list to value the bucked assortments against.
        taper_class: The :class:`~pyforestry.base.taper.Taper` subclass the bucker
            takes stem dimensions from.
        bucking_config: Bucking options. ``save_sections`` is forced on, because
            the piece records this package reports are the sections.
        min_diam_dead_wood: Minimum top diameter, in cm, below which wood is
            treated as dead and not merchandised.

    Raises:
        TypeError: If any field is not of its declared type.
    """

    pricelist: Pricelist
    taper_class: Type[Taper]
    bucking_config: BuckingConfig = field(
        default_factory=lambda: BuckingConfig(save_sections=True)
    )
    min_diam_dead_wood: float = 0.0

    def __post_init__(self) -> None:
        """Validate the settings and force ``save_sections`` on."""
        if not isinstance(self.pricelist, Pricelist):
            raise TypeError(f"pricelist must be a Pricelist, got {type(self.pricelist).__name__}.")
        if not (isinstance(self.taper_class, type) and issubclass(self.taper_class, Taper)):
            raise TypeError("taper_class must be a Taper subclass.")
        if not isinstance(self.bucking_config, BuckingConfig):
            raise TypeError(
                f"bucking_config must be a BuckingConfig, got "
                f"{type(self.bucking_config).__name__}."
            )
        if not self.bucking_config.save_sections:
            object.__setattr__(
                self, "bucking_config", replace(self.bucking_config, save_sections=True)
            )
        object.__setattr__(self, "min_diam_dead_wood", float(self.min_diam_dead_wood))


class VolumeConnector:
    """Resolve removal ledgers into volume descriptors and valuation results."""

    def __init__(self, *, bucker_cls: Type[Nasberg_1985_BranchBound] | None = None) -> None:
        """Create a connector with an optional bucker override."""
        self._bucker_cls = bucker_cls or Nasberg_1985_BranchBound

    def describe(
        self, settings: ValuationSettings, ledger: StandRemovalLedger
    ) -> VolumeDescriptor:
        """Return the descriptor describing ``ledger`` priced under ``settings``.

        Raises:
            TypeError: If ``settings`` or ``ledger`` is not of its declared type.
        """
        if not isinstance(ledger, StandRemovalLedger):
            raise TypeError("ledger must be a StandRemovalLedger instance.")
        if ledger.is_empty:
            return EmptyVolumeDescriptor(ledger=ledger, metadata=dict(ledger.metadata))
        if not isinstance(settings, ValuationSettings):
            raise TypeError(
                f"settings must be a ValuationSettings, got {type(settings).__name__}. "
                "Build one with the price list, taper and bucking config to use."
            )

        return TreeVolumeDescriptor(
            ledger=ledger,
            removals=tuple(ledger.iter_tree_removals()),
            pricelist=settings.pricelist,
            taper_class=settings.taper_class,
            bucking_config=settings.bucking_config,
            bucker_cls=self._bucker_cls,
            min_diam_dead_wood=settings.min_diam_dead_wood,
            metadata=dict(ledger.metadata),
        )

    def connect(self, settings: ValuationSettings, ledger: StandRemovalLedger) -> VolumeResult:
        """Return the evaluated volume result for ``ledger`` under ``settings``."""
        return self.describe(settings, ledger).evaluate()


__all__ = [
    "PieceRecord",
    "ValuationSettings",
    "VolumeResult",
    "VolumeDescriptor",
    "EmptyVolumeDescriptor",
    "TreeVolumeDescriptor",
    "VolumeConnector",
]
