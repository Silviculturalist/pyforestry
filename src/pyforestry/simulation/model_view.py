"""View classes that bridge helper-layer objects into the simulation API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Tuple, Union

from pyforestry.base.helpers import CircularPlot, Stand, StandMetricAccessor, Tree
from pyforestry.base.helpers.primitives import Position
from pyforestry.base.helpers.tree_species import TreeName, parse_tree_species


class StandMetricView:
    """Expose stand-level aggregations via :class:`StandMetricAccessor` objects."""

    _SUPPORTED = ("BasalArea", "Stems", "QMD", "BAWAD")

    def __init__(self, stand: Stand):
        if not isinstance(stand, Stand):  # pragma: no cover - defensive
            raise TypeError("StandMetricView requires a Stand instance.")
        if not stand.plots:
            raise ValueError("StandMetricView requires a stand with at least one plot.")
        for plot in stand.plots:
            if not isinstance(plot, CircularPlot):
                raise TypeError("StandMetricView expects plots to be CircularPlot instances.")
        self._stand = stand

    @property
    def requires_stand_metrics(self) -> bool:
        """Flag indicating that stand-level metric estimates are required."""

        return True

    @property
    def requires_plots(self) -> bool:
        """Stand metrics ultimately derive from the stand's plots."""

        return True

    @property
    def requires_trees(self) -> bool:
        """Whether tree-level observations are needed to source the metrics."""

        return not self._stand.use_angle_count

    @property
    def supported_metrics(self) -> Tuple[str, ...]:
        """Return the list of metric accessors this view can expose."""

        available = []
        for name in self._SUPPORTED:
            if hasattr(self._stand.__class__, name):
                available.append(name)
        return tuple(available)

    def metric(self, metric_name: str) -> StandMetricAccessor:
        """Return the :class:`StandMetricAccessor` for ``metric_name``."""

        if metric_name not in self.supported_metrics:
            raise KeyError(f"Stand does not expose a {metric_name} accessor.")
        accessor = getattr(self._stand, metric_name)
        if not isinstance(accessor, StandMetricAccessor):  # pragma: no cover - defensive
            raise TypeError(f"Stand attribute {metric_name} is not a StandMetricAccessor.")
        return accessor

    def total(self, metric_name: str) -> float:
        """Return the total value for the supplied metric."""

        return float(self.metric(metric_name))

    def by_species(self, metric_name: str, species: Union[TreeName, str]):
        """Delegate species-level lookups to the matching accessor."""

        return self.metric(metric_name)(species)


@dataclass
class InventoryView:
    """Iterate over the plots and trees that compose a stand inventory."""

    stand: Stand

    def __post_init__(self) -> None:
        if not isinstance(self.stand, Stand):  # pragma: no cover - defensive
            raise TypeError("InventoryView requires a Stand instance.")
        if not self.stand.plots:
            raise ValueError("InventoryView requires at least one CircularPlot.")
        for plot in self.stand.plots:
            if not isinstance(plot, CircularPlot):
                raise TypeError("InventoryView expects CircularPlot instances.")
            if plot.trees is None:
                raise ValueError("InventoryView requires plots to expose tree collections.")
        self._plots = tuple(self.stand.plots)

    @property
    def requires_stand_metrics(self) -> bool:
        """Inventory iteration does not demand pre-computed stand metrics."""

        return False

    @property
    def requires_plots(self) -> bool:
        """The view iterates plots directly."""

        return True

    @property
    def requires_trees(self) -> bool:
        """Determine whether any plots expose tree measurements."""

        return any(plot.trees for plot in self._plots)

    @property
    def plot_count(self) -> int:
        """Number of plots available in the inventory."""

        return len(self._plots)

    def iter_plots(self) -> Iterator[CircularPlot]:
        """Yield plots exactly as stored on the underlying :class:`Stand`."""

        for plot in self._plots:
            yield plot

    def iter_trees(self) -> Iterator[Tree]:
        """Yield trees from every plot in inventory order."""

        for plot in self._plots:
            for tree in plot.trees:
                yield tree


@dataclass
class SpatialTreeView:
    """Expose the spatial context of an individual :class:`Tree`."""

    tree: Tree

    def __post_init__(self) -> None:
        if not isinstance(self.tree, Tree):  # pragma: no cover - defensive
            raise TypeError("SpatialTreeView requires a Tree instance.")
        if not isinstance(self.tree.position, Position):
            raise ValueError("SpatialTreeView requires trees to carry a Position.")
        if self.tree.weight_n is None or self.tree.weight_n <= 0:
            raise ValueError("SpatialTreeView requires tree weights to be positive.")

    @property
    def requires_stand_metrics(self) -> bool:
        """Spatial views operate solely on tree-level inputs."""

        return False

    @property
    def requires_plots(self) -> bool:
        """No plot context is necessary to expose tree coordinates."""

        return False

    @property
    def requires_trees(self) -> bool:
        """The view is defined for tree measurements."""

        return True

    @property
    def requires_spatial_coordinates(self) -> bool:
        """Spatial outputs mandate positional data."""

        return True

    @property
    def coordinates(self) -> Tuple[float, float, float]:
        """Return the tree coordinates as an ``(x, y, z)`` tuple."""

        pos = self.tree.position
        assert isinstance(pos, Position)  # mypy/runtime guard
        return (pos.X, pos.Y, pos.Z or 0.0)

    @property
    def species(self) -> Union[TreeName, None]:
        """Return the tree's species identifier if available."""

        raw_species = self.tree.species
        if raw_species is None:
            return None
        if isinstance(raw_species, str):
            return parse_tree_species(raw_species)
        return raw_species

    @property
    def weight(self) -> float:
        """Return the expansion factor associated with the tree."""

        return float(self.tree.weight_n)
