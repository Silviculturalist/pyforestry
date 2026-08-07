"""Volume conversion utilities for valuation workflows.

Pricing a removal needs three things the ledger does not carry: a price list, a
taper function and a bucking configuration. They arrive as one typed
:class:`ValuationSettings`.

Two routes, chosen by what the stand could report. A tree list is bucked stem by
stem and priced by grade (:class:`TreeVolumeDescriptor`). An aggregate model has
no individual stems, but it has a quadratic mean diameter and a mean height, so
its *representative* stem is bucked once and scaled up
(:class:`MeanTreeVolumeDescriptor`) -- which gets a stand-level model a real
assortment split rather than pulpwood for everything.

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
from typing import (
    Any,
    Callable,
    Dict,
    Mapping,
    MutableMapping,
    Protocol,
    Tuple,
    Type,
    runtime_checkable,
)

from pyforestry.base.helpers.bucking import BuckingConfig, QualityType
from pyforestry.base.pricelist import Pricelist
from pyforestry.base.taper import Taper
from pyforestry.base.timber import Timber
from pyforestry.base.timber_bucking.nasberg_1985 import Nasberg_1985_BranchBound

from .removals import MeanTreeRemoval, StandRemovalLedger, TreeRemoval


@runtime_checkable
class StemDimensions(Protocol):
    """What a timber factory needs from a removal, of either kind.

    :class:`~pyforestry.simulation.valuation.removals.TreeRemoval` and
    :class:`~pyforestry.simulation.valuation.removals.MeanTreeRemoval` both
    satisfy it, so one factory serves both routes -- a region whose taper needs
    its own ``Timber`` subclass writes it once.
    """

    @property
    def species_name(self) -> str:
        """The species' full scientific name."""
        ...

    @property
    def diameter_cm(self) -> float:
        """Breast-height diameter, in cm."""
        ...

    @property
    def height_m(self) -> float:
        """Total height, in m."""
        ...

    def to_timber(self) -> Timber:
        """Build the base timber for this stem."""
        ...


def _default_timber_factory(removal: StemDimensions) -> Timber:
    """Build the base :class:`~pyforestry.base.timber.Timber` for a removal."""
    return removal.to_timber()


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
    timber_factory: Callable[[StemDimensions], Timber] = _default_timber_factory

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
            timber = self.timber_factory(removal)
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
        timber_factory: Builds the :class:`~pyforestry.base.timber.Timber` a
            removal is bucked as, for either kind of removal -- an individual stem
            or a stand's mean tree. Defaults to the base ``Timber``; a region
            whose taper needs its own subclass supplies one, which is what
            Sweden's ``EdgrenNylinder1949`` requires -- it rejects anything that
            is not a ``SweTimber``, so the default produced a ``ValueError`` from
            inside the bucker rather than at configuration time.

    Raises:
        TypeError: If any field is not of its declared type.
    """

    pricelist: Pricelist
    taper_class: Type[Taper]
    bucking_config: BuckingConfig = field(
        default_factory=lambda: BuckingConfig(save_sections=True)
    )
    min_diam_dead_wood: float = 0.0
    timber_factory: Callable[[StemDimensions], Timber] = _default_timber_factory

    def __post_init__(self) -> None:
        """Validate the settings and force ``save_sections`` on."""
        if not isinstance(self.pricelist, Pricelist):
            raise TypeError(f"pricelist must be a Pricelist, got {type(self.pricelist).__name__}.")
        if not (isinstance(self.taper_class, type) and issubclass(self.taper_class, Taper)):
            raise TypeError("taper_class must be a Taper subclass.")
        if not callable(self.timber_factory):
            raise TypeError("timber_factory must be callable.")
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


@dataclass(kw_only=True)
class MeanTreeVolumeDescriptor(VolumeDescriptor):
    """Buck the stand's representative stem, and scale it to the stems removed.

    An aggregate model reports a basal area and a stem count, so a thinning from
    it has no individual stems to cut. It does have a quadratic mean diameter and
    a mean height, and the stem those describe is a real stem: bucking it once
    gives the *proportions* of butt, middle, top and pulp a stand of that mean
    size yields.

    One stem's worth of logs, multiplied by how many came out -- the same
    arithmetic :class:`TreeVolumeDescriptor` does with an expansion factor, so the
    two routes report volume and value on the same basis.

    **This used to scale the grades so they summed to the model's own volume
    figure**, on the reasoning that how much came out is the model's business and
    only the split is the mean tree's. Those are not the same measure of volume.
    A stand volume function reports m3sk -- stem volume over bark, on the wider
    Nordic definition; the price list buys m3to, top-measured log volume, as
    :attr:`TimberPricelist.volume_type` declares. Scaling m3to grades up to an
    m3sk total pays m3to prices on m3sk cubic metres, about 21% more per removal
    than the stem yields. Nothing caught it because it made priced volume equal
    harvested volume by construction, and the tree-list route -- which prices
    around 78% of what its own reporter counts -- was the only place the
    difference showed.

    So the model's figure is no longer imposed on the logs. It still says how much
    left the stand, which is what the summary's ``harvested_m3`` reports in m3sk;
    the logs are what the mean stem yields in m3to.
    ``share_of_removed_volume_sold`` is the ratio between them, so the conversion
    is a number a reader can see instead of an assumption.

    Three things it assumes, all worth knowing before comparing the result with a
    bucked inventory:

    * The mean tree's grade split is the stand's. It is not: value is convex in
      diameter, so a stand with the same mean but a wider spread yields more
      sawtimber than its mean tree suggests. This understates a heterogeneous
      stand and is exact only for a uniform one.
    * Whatever height the run supplied for the mean stem is the mean stem's. A
      model that predicts only *dominant* height has none, and using that
      overstates the stem's taper -- which is why the height is the run's to
      supply rather than something guessed here. That overstatement now shows up
      where it can be seen, in the share of removed volume sold, rather than
      being absorbed into a scale factor.
    * The mean stem stands for every stem removed. A thinning from below takes
      stems smaller than the mean, so pricing them all at the mean overstates the
      grade split of a low thinning.

    Raises:
        ValueError: From :meth:`evaluate`, if a mean stem bucks to more log volume
            than the model says came out of the stand. m3to is a narrower measure
            than m3sk, so the logs cannot exceed the stem volume they came from;
            when they do, the representative stem is too large for the removal --
            most often a dominant height standing in for a mean one.
    """

    removals: Tuple[MeanTreeRemoval, ...]
    pricelist: Pricelist
    taper_class: Type[Taper]
    bucking_config: BuckingConfig = field(
        default_factory=lambda: BuckingConfig(save_sections=True)
    )
    bucker_cls: Type[Nasberg_1985_BranchBound] = Nasberg_1985_BranchBound
    min_diam_dead_wood: float = 0.0
    timber_factory: Callable[[StemDimensions], Timber] = _default_timber_factory

    def evaluate(self) -> VolumeResult:  # type: ignore[override]
        """Buck each mean stem and multiply its grades by the stems removed.

        Raises:
            ValueError: If a mean stem's logs exceed the volume the model says was
                removed, which no real stem can do.
        """
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
        removed_m3 = 0.0
        sold_m3 = 0.0

        for removal in self.removals:
            timber = self.timber_factory(removal)
            bucker = self.bucker_cls(timber, self.pricelist, self.taper_class)
            result = bucker.calculate_tree_value(
                min_diam_dead_wood=self.min_diam_dead_wood,
                config=config,
            )

            # The mean stem's own bucked volume, in the price list's measure.
            bucked = float(sum(result.volume_per_quality))
            removed_m3 += removal.volume_m3
            if bucked <= 0.0:
                # Too small to yield anything the price list buys. The volume is
                # still gone from the stand; it simply earns nothing.
                continue
            # One stem's worth of logs, times how many came out. The model's own
            # figure stays what it is: how much left the stand, in its own measure.
            scale = removal.stems
            sold = bucked * scale
            if sold > removal.volume_m3:
                raise ValueError(
                    f"The mean stem for cohort {removal.cohort_id!r} bucks to "
                    f"{sold:.4f} m3/ha of logs, but the model says only "
                    f"{removal.volume_m3:.4f} m3/ha came out of the stand. Log volume "
                    "is the narrower measure, so it cannot exceed the stem volume it "
                    f"came from. The stem given -- {removal.diameter_cm:.1f} cm by "
                    f"{removal.height_m:.1f} m -- is too big for this removal; the usual "
                    "cause is a dominant height standing in for a mean height."
                )
            sold_m3 += sold

            total_value += float(result.total_value) * scale
            for idx, volume in enumerate(result.volume_per_quality):
                try:
                    quality = QualityType(idx)
                except ValueError:
                    continue
                volume_by_quality[quality] += float(volume) * scale

            for section in result.sections or []:
                pieces.append(
                    PieceRecord(
                        cohort_id=removal.cohort_id,
                        species=removal.species_name,
                        quality=section.quality,
                        length_m=(section.end_point - section.start_point) / 10.0,
                        top_diameter_cm=float(section.top_diameter),
                        volume_m3=float(section.volume) * scale,
                        value=float(section.value) * scale,
                        weight=scale,
                    )
                )

        metadata = dict(self.metadata)
        metadata.setdefault("bucked", True)
        metadata.setdefault("method", "mean tree")
        metadata.setdefault(
            "pricing",
            "The stand's mean stem (QMD, mean height) bucked once and multiplied by the "
            "stems removed. Grade split is the mean tree's, which understates a stand "
            "whose diameters are widely spread.",
        )
        # What share of the volume that left the stand was sold as logs. The
        # remainder is the difference between the measures: the model reports the
        # wider stem volume, the price list buys top-measured logs. Reported rather
        # than assumed, because how far below 1.0 it sits depends on the species,
        # the taper and the height the run supplied for the mean stem.
        if removed_m3 > 0.0:
            metadata.setdefault("share_of_removed_volume_sold", sold_m3 / removed_m3)

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

        # An aggregate model's removals have no individual stems, but they do
        # have a mean tree, and that can be bucked. Taking this route rather than
        # dropping them is what gave Norway a valuation at all.
        mean_trees = tuple(ledger.iter_mean_tree_removals())
        stems = tuple(ledger.iter_tree_removals())
        if mean_trees and stems:
            # Nothing in the shipped runbooks produces both -- a removal is
            # recorded one way or the other, by what the stand could report -- but
            # both recorders are public, and this used to take the mean-tree route
            # and drop the stems without a word. A ledger holding one 30 cm stem
            # worth 22,821 and one small mean tree priced at 30.
            raise ValueError(
                f"This ledger holds {len(stems)} individual stem removal(s) and "
                f"{len(mean_trees)} mean-tree removal(s). They are two ways of "
                "describing what came out, and pricing both would count the same "
                "wood twice while pricing either alone would silently lose the "
                "other. Record a removal one way or the other."
            )
        if mean_trees:
            return MeanTreeVolumeDescriptor(
                ledger=ledger,
                removals=mean_trees,
                pricelist=settings.pricelist,
                taper_class=settings.taper_class,
                bucking_config=settings.bucking_config,
                bucker_cls=self._bucker_cls,
                min_diam_dead_wood=settings.min_diam_dead_wood,
                timber_factory=settings.timber_factory,
                metadata=dict(ledger.metadata),
            )

        return TreeVolumeDescriptor(
            ledger=ledger,
            removals=stems,
            pricelist=settings.pricelist,
            taper_class=settings.taper_class,
            bucking_config=settings.bucking_config,
            bucker_cls=self._bucker_cls,
            min_diam_dead_wood=settings.min_diam_dead_wood,
            timber_factory=settings.timber_factory,
            metadata=dict(ledger.metadata),
        )

    def connect(self, settings: ValuationSettings, ledger: StandRemovalLedger) -> VolumeResult:
        """Return the evaluated volume result for ``ledger`` under ``settings``."""
        return self.describe(settings, ledger).evaluate()


__all__ = [
    "MeanTreeVolumeDescriptor",
    "StemDimensions",
    "PieceRecord",
    "ValuationSettings",
    "VolumeResult",
    "VolumeDescriptor",
    "EmptyVolumeDescriptor",
    "TreeVolumeDescriptor",
    "VolumeConnector",
]
