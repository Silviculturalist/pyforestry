"""Serialization utilities for checkpointing tree- and stand-level state.

The helpers in this module translate :class:`~pyforestry.base.helpers.tree.Tree`
objects into plain dictionaries that can be stored using common persistence
formats such as JSON, CSV, Parquet, or database rows.  Every value emitted by
:func:`serialize_tree` is JSON serialisable which means snapshots can be
written directly to object storage, parquet writers, or column stores without
custom encoders.  The inverse operation, :func:`restore_tree`, rebuilds
:class:`Tree` instances from those dictionaries.

Batch helpers (``snapshot_*``/``restore_*``) provide convenient utilities for
entire collections.  ``snapshot_plot`` and ``snapshot_stand`` return lists of
:class:`TreeCheckpoint` objects that can be fed to arrow/parquet writers or
further transformed before storage, while ``restore_plot`` and
``restore_stand`` hydrate :class:`Tree` objects from either ``TreeCheckpoint``
instances or raw dictionaries as loaded from JSON files.

The emitted dictionaries use the following field structure:

``position``
    ``{"x": float, "y": float, "z": float | None, "crs": str | None}``.
    ``crs`` uses :func:`pyproj.CRS.to_string` so it is readily reversible.
``species``
    ``{"code": str | None, "full_name": str | None}``.  ``code`` corresponds
    to entries in :data:`pyforestry.base.helpers.tree_species.GLOBAL_TREE_SPECIES`
    and is preferred for lookups, while ``full_name`` is used as a fallback via
    :func:`pyforestry.base.helpers.tree_species.parse_tree_species`.
``age``
    ``{"kind": "measurement"|"enum"|"numeric", "value": float | None, "code": int | None}``.
``diameter_cm``
    ``{"kind": "diameter_cm"|"numeric", "value": float, "over_bark": bool | None,
    "measurement_height_m": float | None}``.
``height_m``
    Raw numeric height (metres) or ``None``.
``weight_n``
    Stem expansion factor (number of stems represented) or ``None``.
``uid``
    Optional identifier preserved without interpretation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Optional, Sequence, Union

from pyproj import CRS

from pyforestry.base.helpers.plot import CircularPlot
from pyforestry.base.helpers.primitives.age import Age, AgeMeasurement
from pyforestry.base.helpers.primitives.cartesian_position import Position
from pyforestry.base.helpers.primitives.diameter_cm import Diameter_cm
from pyforestry.base.helpers.stand import Stand
from pyforestry.base.helpers.tree import Tree
from pyforestry.base.helpers.tree_species import (
    GLOBAL_TREE_SPECIES,
    TreeName,
    parse_tree_species,
)


@dataclass(slots=True)
class TreeCheckpoint:
    """Lightweight, serialisable representation of a :class:`Tree`.

    Instances of this dataclass carry only JSON-compatible values so they can
    be stored directly or converted to Python dictionaries via
    :func:`dataclasses.asdict`.  Use :func:`serialize_tree` and
    :func:`restore_tree` for the high-level conversion functions.
    """

    position: Optional[Mapping[str, Any]] = None
    species: Optional[Mapping[str, Optional[str]]] = None
    age: Optional[Mapping[str, Optional[Union[int, float, str]]]] = None
    diameter_cm: Optional[Mapping[str, Optional[Union[bool, float, str]]]] = None
    height_m: Optional[float] = None
    weight_n: Optional[float] = 1.0
    uid: Optional[Union[int, str]] = None

    def to_dict(self) -> dict[str, Any]:
        """Return a deep copy of the checkpoint suitable for serialisation."""

        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TreeCheckpoint":
        """Hydrate a checkpoint from a mapping of primitive values."""

        return cls(
            position=data.get("position"),
            species=data.get("species"),
            age=data.get("age"),
            diameter_cm=data.get("diameter_cm"),
            height_m=data.get("height_m"),
            weight_n=data.get("weight_n"),
            uid=data.get("uid"),
        )


def serialize_tree(tree: Tree) -> dict[str, Any]:
    """Convert a :class:`Tree` instance into a serialisable dictionary."""

    checkpoint = TreeCheckpoint(
        position=_serialize_position(tree.position),
        species=_serialize_species(tree.species),
        age=_serialize_age(tree.age),
        diameter_cm=_serialize_diameter(tree.diameter_cm),
        height_m=tree.height_m,
        weight_n=tree.weight_n,
        uid=tree.uid,
    )
    return checkpoint.to_dict()


def restore_tree(data: Mapping[str, Any] | TreeCheckpoint) -> Tree:
    """Rebuild a :class:`Tree` from a checkpoint dictionary or dataclass."""

    checkpoint = data if isinstance(data, TreeCheckpoint) else TreeCheckpoint.from_dict(data)

    position = _restore_position(checkpoint.position)
    species = _restore_species(checkpoint.species)
    age = _restore_age(checkpoint.age)
    diameter = _restore_diameter(checkpoint.diameter_cm)

    return Tree(
        position=position,
        species=species,
        age=age,
        diameter_cm=diameter,
        height_m=checkpoint.height_m,
        weight_n=checkpoint.weight_n,
        uid=checkpoint.uid,
    )


def snapshot_trees(trees: Iterable[Tree]) -> list[TreeCheckpoint]:
    """Snapshot an iterable of :class:`Tree` instances."""

    return [
        TreeCheckpoint(
            position=_serialize_position(tree.position),
            species=_serialize_species(tree.species),
            age=_serialize_age(tree.age),
            diameter_cm=_serialize_diameter(tree.diameter_cm),
            height_m=tree.height_m,
            weight_n=tree.weight_n,
            uid=tree.uid,
        )
        for tree in trees
    ]


def snapshot_plot(plot: CircularPlot) -> list[TreeCheckpoint]:
    """Return checkpoints for every tree stored on ``plot``."""

    return snapshot_trees(plot.trees)


def snapshot_stand(stand: Stand) -> list[TreeCheckpoint]:
    """Return checkpoints for all trees across every plot in ``stand``."""

    plots: Sequence[CircularPlot]
    iterator = getattr(stand, "__iter__", None)
    if callable(iterator):
        plots = list(iterator())  # type: ignore[arg-type]
    else:
        plots = stand.plots

    snapshots: list[TreeCheckpoint] = []
    for plot in plots:
        snapshots.extend(snapshot_plot(plot))
    return snapshots


def restore_trees(
    checkpoints: Iterable[Mapping[str, Any] | TreeCheckpoint],
) -> list[Tree]:
    """Restore a list of :class:`Tree` objects from ``checkpoints``."""

    return [restore_tree(checkpoint) for checkpoint in checkpoints]


def restore_plot(
    checkpoints: Iterable[Mapping[str, Any] | TreeCheckpoint],
) -> list[Tree]:
    """Restore the tree list for a plot from ``checkpoints``."""

    return restore_trees(checkpoints)


def restore_stand(
    checkpoints: Iterable[Mapping[str, Any] | TreeCheckpoint],
) -> list[Tree]:
    """Restore a flattened list of trees for an entire stand."""

    return restore_trees(checkpoints)


def _serialize_position(position: Optional[Position]) -> Optional[dict[str, Any]]:
    if position is None:
        return None

    crs = position.crs.to_string() if getattr(position, "crs", None) else None
    return {
        "x": position.X,
        "y": position.Y,
        "z": position.Z,
        "crs": crs,
    }


def _restore_position(data: Optional[Mapping[str, Any]]) -> Optional[Position]:
    if not data:
        return None

    crs_value = data.get("crs")
    crs = CRS.from_user_input(crs_value) if crs_value else None
    return Position(
        X=data.get("x", 0.0),
        Y=data.get("y", 0.0),
        Z=data.get("z"),
        crs=crs,
    )


def _serialize_species(species: Optional[Union[TreeName, str]]) -> Optional[dict[str, Any]]:
    if species is None:
        return None

    if isinstance(species, TreeName):
        return {"code": species.code, "full_name": species.full_name}
    return {"code": None, "full_name": str(species)}


def _restore_species(data: Optional[Mapping[str, Any]]) -> Optional[TreeName]:
    if not data:
        return None

    code = data.get("code")
    if code:
        for candidate in GLOBAL_TREE_SPECIES:
            if candidate.code == code:
                return candidate

    full_name = data.get("full_name")
    if full_name:
        try:
            return parse_tree_species(full_name)
        except ValueError:
            return None
    return None


def _serialize_age(age: Optional[Any]) -> Optional[dict[str, Any]]:
    if age is None:
        return None

    if isinstance(age, AgeMeasurement):
        return {"kind": "measurement", "value": float(age), "code": age.code}
    if isinstance(age, Age):
        return {"kind": "enum", "value": None, "code": age.value}
    return {"kind": "numeric", "value": float(age), "code": None}


def _restore_age(data: Optional[Mapping[str, Any]]) -> Optional[Any]:
    if not data:
        return None

    kind = data.get("kind")
    code = data.get("code")
    value = data.get("value")

    if kind == "measurement":
        if value is None or code is None:
            return None
        return AgeMeasurement(float(value), int(code))
    if kind == "enum":
        if code is None:
            return None
        try:
            return Age(int(code))
        except ValueError:
            return None
    if kind == "numeric":
        if value is None:
            return None
        return float(value)

    # Fallback for legacy/unknown structures
    if value is not None and code is not None:
        try:
            return AgeMeasurement(float(value), int(code))
        except (TypeError, ValueError):
            pass
    if value is not None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return None


def _serialize_diameter(diameter: Optional[Union[Diameter_cm, float]]) -> Optional[dict[str, Any]]:
    if diameter is None:
        return None

    if isinstance(diameter, Diameter_cm):
        return {
            "kind": "diameter_cm",
            "value": float(diameter),
            "over_bark": getattr(diameter, "over_bark", True),
            "measurement_height_m": getattr(diameter, "measurement_height_m", 1.3),
        }
    return {"kind": "numeric", "value": float(diameter)}


def _restore_diameter(data: Optional[Mapping[str, Any]]) -> Optional[Union[Diameter_cm, float]]:
    if not data:
        return None

    kind = data.get("kind")
    value = data.get("value")

    if value is None:
        return None

    if kind == "diameter_cm" or "over_bark" in data or "measurement_height_m" in data:
        over_bark = data.get("over_bark", True)
        measurement_height_m = data.get("measurement_height_m", 1.3)
        measurement_height = measurement_height_m if measurement_height_m is not None else 1.3
        return Diameter_cm(
            float(value),
            over_bark=bool(over_bark),
            measurement_height_m=float(measurement_height),
        )
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
