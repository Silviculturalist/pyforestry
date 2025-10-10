"""Immutable snapshot models used by the simulation framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence, Tuple


@dataclass(frozen=True, slots=True)
class TreeState:
    """An immutable representation of the state of a :class:`Tree` instance.

    The dataclass deliberately mirrors the attributes exposed by
    :class:`pyforestry.base.helpers.tree.Tree` while remaining serialisable.
    Only plain Python types are stored so that ``TreeState`` objects can be
    included in checkpoint payloads or JSON documents without custom
    encoders.
    """

    uid: str | int | None
    """Unique identifier assigned to the originating tree (if provided)."""

    species: str | None
    """Species name captured using ``TreeName.full_name`` where available."""

    age: float | None
    """Tree age in years."""

    diameter_cm: float | None
    """Diameter at breast height in centimetres."""

    height_m: float | None
    """Total height in metres."""

    weight_n: float
    """Number of represented stems."""

    position: Tuple[float, ...] | None
    """Cartesian coordinates of the tree, stored as an ``(x, y[, z])`` tuple."""

    plot_id: str | int | None
    """Identifier of the :class:`~pyforestry.base.helpers.plot.CircularPlot`."""

    deltas: Mapping[str, float] = field(default_factory=dict)
    """Optional growth deltas recorded by models for diagnostics."""

    extras: Mapping[str, Any] = field(default_factory=dict)
    """Additional per-model variables preserved for later analysis."""


@dataclass(frozen=True, slots=True)
class PlotState:
    """Snapshot of a plot used to derive tree contexts when restoring."""

    id: str | int
    area_m2: float | None
    radius_m: float | None
    occlusion: float
    position: Tuple[float, ...] | None
    site: Any
    tree_uids: Tuple[str | int | None, ...]
    angle_counts: Tuple[Any, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class StandState:
    """Aggregated representation of a :class:`Stand` and its plots."""

    site: Any
    area_ha: float | None
    top_height_definition: Any
    attrs: Mapping[str, Any]
    metric_estimates: Mapping[str, Mapping[str, float]]
    use_angle_count: bool
    plots: Tuple[PlotState, ...] = field(default_factory=tuple)

    def require_metric(self, metric: str) -> Mapping[str, float]:
        """Retrieve a metric from the cached estimates.

        Parameters
        ----------
        metric:
            Name of the metric to extract.

        Returns
        -------
        Mapping[str, float]
            Mapping of species (or ``"TOTAL"``) to numeric values.
        """

        if metric not in self.metric_estimates:
            raise KeyError(f"Metric '{metric}' missing from stand snapshot")
        return self.metric_estimates[metric]


TreeStateSequence = Sequence[TreeState]
"""Convenience alias used by other simulation components."""
