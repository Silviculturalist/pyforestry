"""Checkpointing utilities for simulation runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Mapping, Sequence

from pyforestry.base.helpers import CircularPlot, Stand, Tree
from pyforestry.base.helpers.primitives.cartesian_position import Position

from .state import PlotState, StandState, TreeState

__all__ = ["SimulationCheckpoint", "TreeCheckpointer"]


def _to_tuple(position: Position | tuple[float, ...] | None) -> tuple[float, ...] | None:
    """Convert a :class:`Position` object to a plain tuple."""

    if position is None:
        return None
    if isinstance(position, tuple):
        return position
    coords = [position.X, position.Y]
    if position.Z not in (None, 0, 0.0):
        coords.append(position.Z)
    return tuple(coords)


def _normalise_scalar(value: Any) -> float | Any | None:
    """Attempt to coerce metric values into floats for serialisation."""

    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    for attr in ("value", "values"):
        maybe = getattr(value, attr, None)
        if isinstance(maybe, (int, float)):
            return float(maybe)
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


@dataclass(slots=True)
class SimulationCheckpoint:
    """Bundle of stand and tree snapshots captured at a point in time."""

    timestamp: datetime
    seed_state: Mapping[str, Any]
    tree_states: Sequence[TreeState]
    stand_state: StandState
    active_modules: Sequence[str] = field(default_factory=tuple)
    pending_events: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the checkpoint into a serialisable dictionary."""

        return {
            "timestamp": self.timestamp.isoformat(),
            "seed_state": dict(self.seed_state),
            "tree_states": [asdict(ts) for ts in self.tree_states],
            "stand_state": asdict(self.stand_state),
            "active_modules": list(self.active_modules),
            "pending_events": [dict(ev) for ev in self.pending_events],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SimulationCheckpoint":
        """Recreate a checkpoint from a serialised dictionary."""

        tree_states = [TreeState(**ts) for ts in payload["tree_states"]]
        plots = tuple(PlotState(**plot) for plot in payload["stand_state"].get("plots", ()))
        stand_state = StandState(
            site=payload["stand_state"].get("site"),
            area_ha=payload["stand_state"].get("area_ha"),
            top_height_definition=payload["stand_state"].get("top_height_definition"),
            attrs=payload["stand_state"].get("attrs", {}),
            metric_estimates=payload["stand_state"].get("metric_estimates", {}),
            use_angle_count=payload["stand_state"].get("use_angle_count", False),
            plots=plots,
        )
        return cls(
            timestamp=datetime.fromisoformat(payload["timestamp"]),
            seed_state=payload.get("seed_state", {}),
            tree_states=tree_states,
            stand_state=stand_state,
            active_modules=payload.get("active_modules", ()),
            pending_events=payload.get("pending_events", ()),
            metadata=payload.get("metadata", {}),
        )


class TreeCheckpointer:
    """Helper responsible for converting live objects to snapshot dataclasses."""

    def __init__(self, tree_factory: type[Tree] | None = None):
        self._tree_factory = tree_factory or Tree

    def capture_tree_states(self, stand: Stand) -> List[TreeState]:
        """Extract :class:`TreeState` objects from every plot in ``stand``."""

        tree_states: List[TreeState] = []
        for plot in stand.plots:
            for tree in plot.trees:
                position = _to_tuple(tree.position)
                species = getattr(tree.species, "full_name", None)
                tree_states.append(
                    TreeState(
                        uid=tree.uid,
                        species=species,
                        age=_normalise_scalar(tree.age),
                        diameter_cm=_normalise_scalar(tree.diameter_cm),
                        height_m=_normalise_scalar(tree.height_m),
                        weight_n=float(tree.weight_n) if tree.weight_n is not None else 0.0,
                        position=position,
                        plot_id=plot.id,
                    )
                )
        return tree_states

    def capture_stand_state(self, stand: Stand) -> StandState:
        """Create a :class:`StandState` snapshot for ``stand``."""

        if not stand.use_angle_count:
            stand._compute_ht_estimates()

        metric_estimates: Dict[str, Dict[str, float]] = {}
        for metric, values in stand._metric_estimates.items():
            metric_estimates[metric] = {}
            for species, measurement in values.items():
                if species == "TOTAL":
                    species_key = "TOTAL"
                else:
                    species_key = getattr(species, "full_name", str(species))
                metric_estimates[metric][species_key] = _normalise_scalar(measurement)

        plots: List[PlotState] = []
        for plot in stand.plots:
            position = _to_tuple(plot.position)
            plots.append(
                PlotState(
                    id=plot.id,
                    area_m2=getattr(plot, "area_m2", None),
                    radius_m=getattr(plot, "radius_m", None),
                    occlusion=plot.occlusion,
                    position=position,
                    site=plot.site,
                    tree_uids=tuple(tree.uid for tree in plot.trees),
                    angle_counts=tuple(plot.AngleCount),
                )
            )

        return StandState(
            site=stand.site,
            area_ha=stand.area_ha,
            top_height_definition=stand.top_height_definition,
            attrs=dict(stand.attrs),
            metric_estimates=metric_estimates,
            use_angle_count=stand.use_angle_count,
            plots=tuple(plots),
        )

    def create_checkpoint(
        self,
        stand: Stand,
        *,
        seed_state: Mapping[str, Any] | None = None,
        active_modules: Sequence[str] | None = None,
        pending_events: Sequence[Mapping[str, Any]] | None = None,
        metadata: Mapping[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> SimulationCheckpoint:
        """Capture a :class:`SimulationCheckpoint` for ``stand``."""

        tree_states = self.capture_tree_states(stand)
        stand_state = self.capture_stand_state(stand)
        return SimulationCheckpoint(
            timestamp=timestamp or datetime.utcnow(),
            seed_state=seed_state or {},
            tree_states=tuple(tree_states),
            stand_state=stand_state,
            active_modules=tuple(active_modules or ()),
            pending_events=tuple(pending_events or ()),
            metadata=metadata or {},
        )

    def restore(self, stand: Stand, checkpoint: SimulationCheckpoint) -> None:
        """Restore ``stand`` to the state described by ``checkpoint``."""

        stand.site = checkpoint.stand_state.site
        stand.area_ha = checkpoint.stand_state.area_ha
        stand.top_height_definition = checkpoint.stand_state.top_height_definition
        stand.attrs = dict(checkpoint.stand_state.attrs)
        stand.use_angle_count = checkpoint.stand_state.use_angle_count

        tree_by_plot: Dict[Any, List[TreeState]] = {}
        for tree_state in checkpoint.tree_states:
            tree_by_plot.setdefault(tree_state.plot_id, []).append(tree_state)

        new_plots: List[CircularPlot] = []
        for plot_state in checkpoint.stand_state.plots:
            position = None
            if plot_state.position is not None:
                position = Position(*plot_state.position)
            trees: List[Tree] = []
            for tree_state in tree_by_plot.get(plot_state.id, []):
                tree = self._tree_factory(
                    position=Position(*tree_state.position) if tree_state.position else None,
                    species=tree_state.species,
                    age=tree_state.age,
                    diameter_cm=tree_state.diameter_cm,
                    height_m=tree_state.height_m,
                    weight_n=tree_state.weight_n,
                    uid=tree_state.uid,
                )
                trees.append(tree)
            plot = CircularPlot(
                id=plot_state.id,
                occlusion=plot_state.occlusion,
                position=position,
                radius_m=plot_state.radius_m,
                area_m2=plot_state.area_m2,
                site=plot_state.site,
                trees=trees,
            )
            plot.AngleCount = list(plot_state.angle_counts)
            new_plots.append(plot)

        stand.plots = new_plots
        stand._metric_estimates.clear()
        if stand.plots and not stand.use_angle_count:
            stand._compute_ht_estimates()

    def diff_tree_uids(
        self, checkpoint: SimulationCheckpoint, stand: Stand
    ) -> Dict[str, set[str | int | None]]:
        """Return additions and removals when comparing a checkpoint to ``stand``."""

        live_uids = {tree.uid for plot in stand.plots for tree in plot.trees}
        snapshot_uids = {state.uid for state in checkpoint.tree_states}
        return {
            "added": {uid for uid in live_uids if uid not in snapshot_uids},
            "removed": {uid for uid in snapshot_uids if uid not in live_uids},
        }
