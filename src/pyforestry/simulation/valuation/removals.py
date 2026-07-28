"""What a run removed, in whatever detail the stand it came from could give.

Two kinds, because two kinds of model produce removals:

* :class:`TreeRemoval` -- a stem, with a diameter and a height, which can be
  bucked into assortments and priced by grade. What a tree-list model gives.
* :class:`VolumeRemoval` -- a volume of a species, and nothing more. What an
  *aggregate* model gives: Kuehne (2022) and its siblings step a basal area and
  a stem count, so a thinning there is m³ of pine, with no stem to cut into logs.

The second existed nowhere, which is the whole reason Norway had no valuation
stage: its models are aggregate, the ledger could only hold stems, so there was
nothing for a valuation to price. A stand-level model cannot be bucked, but it
can certainly be sold.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, Mapping, MutableMapping, Optional

from pyforestry.base.helpers import Tree
from pyforestry.base.helpers.tree_species import TreeName, parse_tree_species
from pyforestry.base.timber import Timber


def _normalise_species(species: TreeName | str) -> TreeName:
    """Return a :class:`TreeName` instance for ``species``."""

    if isinstance(species, TreeName):
        return species
    if isinstance(species, str):
        return parse_tree_species(species)
    raise TypeError("Species must be a TreeName or parsable string.")


def _merge_metadata(*sources: Mapping[str, Any] | None) -> Dict[str, Any]:
    """Merge mapping objects from left to right into a new dictionary."""

    merged: Dict[str, Any] = {}
    for source in sources:
        if not source:
            continue
        merged.update(source)
    return merged


@dataclass
class TreeRemoval:
    """Record the removal of an individual (possibly weighted) tree."""

    cohort_id: str
    species: TreeName | str
    tree: Tree
    weight: float | None = None
    metadata: MutableMapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate the record and resolve the stem weight it stands for."""
        if not self.cohort_id:
            raise ValueError("Tree removals require a cohort identifier.")
        if not isinstance(self.tree, Tree):
            raise TypeError("TreeRemoval expects a Tree instance.")
        self.species = _normalise_species(self.species)
        resolved_weight = self.weight
        if resolved_weight is None:
            tree_weight = getattr(self.tree, "weight_n", None)
            if tree_weight is None:
                resolved_weight = 1.0
            else:
                resolved_weight = tree_weight
        if resolved_weight <= 0:
            raise ValueError("Removal weights must be positive.")
        self.weight = float(resolved_weight)
        self.metadata = dict(self.metadata)
        self.metadata.setdefault("cohort_id", self.cohort_id)
        self.metadata.setdefault("species", self.species.full_name)

    @property
    def species_name(self) -> str:
        """Return the lower-case ``"genus species"`` representation."""

        return self.species.full_name

    @property
    def diameter_cm(self) -> float:
        """Return the tree diameter in centimetres."""

        diameter = self.tree.diameter_cm
        if diameter is None:
            raise ValueError("Tree removals require diameter measurements.")
        return float(diameter)

    @property
    def height_m(self) -> float:
        """Return the tree height in metres."""

        height = self.tree.height_m
        if height is None:
            raise ValueError("Tree removals require height measurements.")
        return float(height)

    @property
    def stump_height_m(self) -> float:
        """Return the stump height in metres for the removal."""

        stump = self.metadata.get("stump_height_m")
        if stump is not None:
            return float(stump)
        stump_from_tree = getattr(self.tree, "stump_height_m", None)
        if stump_from_tree is not None:
            return float(stump_from_tree)
        return 0.3

    def to_timber(self) -> Timber:
        """Convert the removal into a :class:`~pyforestry.base.timber.Timber`."""

        kwargs: Dict[str, Any] = {}
        for key in ("double_bark_mm", "crown_base_height_m", "over_bark"):
            if key in self.metadata:
                kwargs[key] = self.metadata[key]
        return Timber(
            species=self.species_name,
            diameter_cm=self.diameter_cm,
            height_m=self.height_m,
            stump_height_m=self.stump_height_m,
            **kwargs,
        )


@dataclass
class VolumeRemoval:
    """Record the removal of a bulk volume, with no stems to cut it from.

    What an aggregate model can say: this many cubic metres of this species came
    out. There is no diameter and no height, so there is nothing to buck, and a
    valuation prices the volume as a whole -- see
    :class:`~pyforestry.simulation.valuation.volume.BulkVolumeDescriptor`, which
    is explicit that no assortments are involved.

    Attributes:
        cohort_id: Which removal event this belongs to.
        species: The species removed.
        volume_m3: The volume, in the same unit the run reports.
        metadata: Anything the caller wants carried through to the piece record.
    """

    cohort_id: str
    species: TreeName | str
    volume_m3: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Normalise the species and reject a non-positive volume."""
        self.species = _normalise_species(self.species)
        self.volume_m3 = float(self.volume_m3)
        if self.volume_m3 <= 0.0:
            raise ValueError(
                f"A volume removal must be positive, got {self.volume_m3!r} m3 for "
                f"cohort {self.cohort_id!r}."
            )
        self.metadata = dict(self.metadata)

    @property
    def species_name(self) -> str:
        """The species' full scientific name."""
        return str(self.species.full_name)


@dataclass
class CohortRemoval:
    """Group a collection of removed trees for a cohort."""

    identifier: str
    species: TreeName | str
    metadata: MutableMapping[str, Any] = field(default_factory=dict)
    trees: list[TreeRemoval] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate the cohort and stamp its species into the metadata."""
        if not self.identifier:
            raise ValueError("Cohort removals require an identifier.")
        self.species = _normalise_species(self.species)
        self.metadata = dict(self.metadata)
        self.metadata.setdefault("species", self.species.full_name)

    def record_tree(
        self,
        tree: Tree,
        *,
        weight: float | None = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> TreeRemoval:
        """Append a tree removal to the cohort."""

        combined = _merge_metadata(self.metadata, metadata)
        removal = TreeRemoval(
            cohort_id=self.identifier,
            species=self.species,
            tree=tree,
            weight=weight,
            metadata=combined,
        )
        self.trees.append(removal)
        return removal

    def iter_trees(self) -> Iterator[TreeRemoval]:
        """Yield the recorded tree removals."""

        yield from self.trees

    @property
    def tree_count(self) -> int:
        """Return the number of recorded tree removals."""

        return len(self.trees)

    @property
    def total_weight(self) -> float:
        """Return the sum of removal weights in the cohort."""

        return float(sum(tree.weight for tree in self.trees))


@dataclass
class StandRemovalLedger:
    """Top-level container aggregating removal cohorts for a stand."""

    stand_id: Optional[str] = None
    metadata: MutableMapping[str, Any] = field(default_factory=dict)
    cohorts: MutableMapping[str, CohortRemoval] = field(default_factory=dict)
    #: Bulk volume removals, from stands that hold no stems to buck.
    volumes: list[VolumeRemoval] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Copy the mappings in so the ledger owns its own state."""
        self.metadata = dict(self.metadata)
        self.cohorts = dict(self.cohorts)
        self.volumes = list(self.volumes)
        if self.stand_id:
            self.metadata.setdefault("stand_id", self.stand_id)

    def add_cohort(
        self,
        identifier: str,
        *,
        species: TreeName | str,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> CohortRemoval:
        """Register a cohort and return it (existing cohorts are updated)."""

        if identifier in self.cohorts:
            cohort = self.cohorts[identifier]
            cohort.metadata.update(metadata or {})
            return cohort
        cohort = CohortRemoval(
            identifier=identifier,
            species=species,
            metadata=dict(metadata or {}),
        )
        self.cohorts[identifier] = cohort
        return cohort

    def record_tree(
        self,
        identifier: str,
        tree: Tree,
        *,
        species: TreeName | str | None = None,
        weight: float | None = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> TreeRemoval:
        """Record a tree removal under ``identifier`` and return the entry."""

        cohort = self.cohorts.get(identifier)
        if cohort is None:
            if species is None:
                if tree.species is None:
                    raise ValueError("Species must be provided when creating a new cohort.")
                species = tree.species
            cohort = self.add_cohort(identifier, species=species, metadata=metadata)
        else:
            if species is not None and _normalise_species(species) != cohort.species:
                raise ValueError("Species for tree removal does not match cohort species.")
        return cohort.record_tree(tree, weight=weight, metadata=metadata)

    def iter_cohorts(self) -> Iterator[CohortRemoval]:
        """Yield the registered cohorts."""

        yield from self.cohorts.values()

    def record_volume(
        self,
        identifier: str,
        *,
        species: TreeName | str,
        volume_m3: float,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> VolumeRemoval:
        """Record a bulk volume removal, for a stand that holds no stems.

        Args:
            identifier: The removal event, e.g. ``"management@2035"``.
            species: What was removed.
            volume_m3: How much.
            metadata: Carried through to the piece record.

        Returns:
            The recorded removal.
        """
        removal = VolumeRemoval(
            cohort_id=identifier,
            species=species,
            volume_m3=volume_m3,
            metadata=dict(metadata or {}),
        )
        self.volumes.append(removal)
        return removal

    def iter_tree_removals(self) -> Iterator[TreeRemoval]:
        """Yield tree removals across all cohorts."""

        for cohort in self.iter_cohorts():
            yield from cohort.iter_trees()

    def iter_volume_removals(self) -> Iterator[VolumeRemoval]:
        """Yield bulk volume removals, in the order they were recorded."""

        yield from self.volumes

    @property
    def is_empty(self) -> bool:
        """Return ``True`` when nothing at all was recorded.

        Both kinds count: a ledger holding only bulk volume is not empty, which
        is what lets an aggregate model's thinning be priced.
        """
        return not self.volumes and all(cohort.tree_count == 0 for cohort in self.cohorts.values())

    @property
    def total_volume_m3(self) -> float:
        """Return the bulk volume recorded, across every removal."""
        return float(sum(removal.volume_m3 for removal in self.volumes))

    @property
    def tree_count(self) -> int:
        """Return the total number of tree removals."""

        return sum(cohort.tree_count for cohort in self.cohorts.values())

    @property
    def total_weight(self) -> float:
        """Return the total removal weight across cohorts."""

        return float(sum(cohort.total_weight for cohort in self.cohorts.values()))

    def extend(self, cohorts: Iterable[CohortRemoval]) -> None:
        """Merge ``cohorts`` into the ledger."""

        for cohort in cohorts:
            existing = self.cohorts.get(cohort.identifier)
            if existing is None:
                self.cohorts[cohort.identifier] = cohort
                continue
            for tree in cohort.iter_trees():
                existing.record_tree(tree.tree, weight=tree.weight, metadata=tree.metadata)


__all__ = ["TreeRemoval", "CohortRemoval", "StandRemovalLedger"]
