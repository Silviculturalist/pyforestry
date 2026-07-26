"""Convert a stand into an inventory representation a model can step.

An angle-count stand carries tallies, not stems; a model that needs a tree list
or diameter classes cannot read it directly. These adapters bridge that gap, and
:meth:`GrowthModel.build_context` picks one automatically and records which ran
in ``ctx.attrs["inventory_adapter"]``, because a reconstructed inventory is not
the same evidence as a measured one.

The pseudo-tree adapters are the strongest claim here: they place every stem of a
species at the stand QMD, which reproduces the basal area and stem count exactly
and the diameter distribution not at all.
"""

# pyforestry/base/simulation/adapters.py
from __future__ import annotations

import math
from dataclasses import dataclass
from math import pi, sqrt
from typing import Any, Dict, List, Optional

from pyforestry.base.helpers import CircularPlot, Position, Tree
from pyforestry.base.helpers.primitives import Stems
from pyforestry.base.helpers.tree_species import TreeName


def _adapter_rng(kwargs: Dict[str, Any], *, default_seed: int) -> Any:
    """Return the caller's random stream, or open one from a seed.

    An adapter reconstructing pseudo-positions is not a stochastic *model* -- the
    coordinates support neighbourhood operations and claim nothing about where
    the trees stood -- but it still draws, so the run that owns it should be able
    to say from where. Pass ``rng=`` (``ctx.rng.child("adapters")``) to tie the
    draws to the run's seed. ``seed=`` remains for a standalone call and opens a
    stream through the same service, so an adapter's draws are checkpointable
    either way; its default keeps the historical coordinates reproducible.
    """
    rng = kwargs.get("rng")
    if rng is not None:
        return rng
    from pyforestry.simulation.services import RandomBundle

    return RandomBundle(int(kwargs.get("seed", default_seed))).rng_for()


class Adapter:
    """Protocol for inventory adapters that construct runnable inventories from a Stand."""

    name: str
    target_mode: str  # "spatial" | "tree_list" | "diameter_class" | "aggregate"

    def can_adapt(self, stand) -> bool:  # noqa: ANN001
        """Whether this adapter can produce its target mode from ``stand``."""
        raise NotImplementedError

    def adapt(self, stand, **kwargs) -> Dict[str, Any]:  # noqa: ANN001
        """Build the inventory payload for :class:`SimulationContext`.

        Returns:
            A single-key mapping -- ``{"plots": ...}``, ``{"dclass": ...}`` or
            ``{"metrics": ...}`` -- matching this adapter's ``target_mode``.
        """
        raise NotImplementedError


# ----------------------------- AC -> Tree-list -------------------------------


@dataclass
class AngleCountToPseudoTreesAdapter(Adapter):
    """Build a surrogate tree list from Angle-Count BA/N to enable tree-list actions."""

    name: str = "angle_count_pseudo_tree_list"
    target_mode: str = "tree_list"
    replicas_per_species: int = 32

    def can_adapt(self, stand) -> bool:  # noqa: ANN001
        """Whether the stand has the angle-count basal-area and stem estimates."""
        if not getattr(stand, "use_angle_count", False):
            return False
        metrics = getattr(stand, "_metric_estimates", {})
        return "BasalArea" in metrics and "Stems" in metrics and len(metrics["BasalArea"]) > 0

    def adapt(self, stand, **kwargs) -> Dict[str, Any]:  # noqa: ANN001
        """Replicate each species' stems as identical trees at the stand QMD.

        Reproduces basal area and stem count exactly and the diameter
        distribution not at all: every surrogate stem of a species carries the
        same diameter. Splitting the stems over ``replicas_per_species`` records
        exists so per-tree operations (thinning a fraction, removing the
        smallest) have something to bite on, not to represent variation.
        """
        reps = int(kwargs.get("replicas_per_species", self.replicas_per_species))
        if reps <= 0:
            reps = self.replicas_per_species
        _ = stand.QMD  # ensure QMD ready
        ba_dict = stand._metric_estimates["BasalArea"]
        n_dict = stand._metric_estimates["Stems"]

        plot = CircularPlot(id="ac_pseudo", area_m2=10_000.0, AngleCount=[], trees=[])
        species_keys = [k for k in ba_dict.keys() if isinstance(k, TreeName)]

        for sp in species_keys:
            n_sp: Stems = n_dict.get(sp, Stems(0.0))
            N = float(n_sp)
            if N <= 0.0:
                continue
            qmd_cm = float(stand.QMD(sp))
            weight_per = N / reps
            for i in range(reps):
                plot.trees.append(
                    Tree(
                        species=sp,
                        diameter_cm=qmd_cm,
                        height_m=None,
                        weight_n=weight_per,
                        uid=f"ac_{sp.code}_{i}",
                    )
                )

        if not plot.trees:
            Ntot = float(stand.Stems)
            BAtot = float(stand.BasalArea)
            if Ntot > 0 and BAtot > 0:
                qmd_tot_cm = float(stand.QMD)
                weight_per = Ntot / reps
                for i in range(reps):
                    plot.trees.append(
                        Tree(
                            species=None,
                            diameter_cm=qmd_tot_cm,
                            height_m=None,
                            weight_n=weight_per,
                            uid=f"ac_TOTAL_{i}",
                        )
                    )

        return {"plots": [plot]}


@dataclass
class AngleCountToSpatialPseudoTreesAdapter(AngleCountToPseudoTreesAdapter):
    """As above but assigns random XY within a 1-ha plot."""

    name: str = "angle_count_spatial_pseudo_tree_list"
    target_mode: str = "spatial"

    def adapt(self, stand, **kwargs) -> Dict[str, Any]:  # noqa: ANN001
        """Place the surrogate stems at uniform random positions in a 1 ha plot.

        The coordinates are drawn, not observed: they support neighbourhood
        operations that need *some* geometry, and say nothing about where the
        tallied trees actually stood.
        """
        out = super().adapt(stand, **kwargs)
        plot: CircularPlot = out["plots"][0]
        rng = _adapter_rng(kwargs, default_seed=1337)
        r = getattr(plot, "radius_m", sqrt(plot.area_m2 / pi))
        for t in plot.trees:
            rr = r * math.sqrt(rng.random())
            theta = 2 * math.pi * rng.random()
            x = rr * math.cos(theta)
            y = rr * math.sin(theta)
            t.position = Position(x, y)
        return out


# ------------------------- AC/Tree-list -> Diameter class ---------------------


@dataclass
class AngleCountToDiameterClassAdapter(Adapter):
    """Build a diameter-class inventory from Angle-Count BA/N (single bin at QMD by default)."""

    name: str = "angle_count_to_diameter_class"
    target_mode: str = "diameter_class"

    def can_adapt(self, stand) -> bool:  # noqa: ANN001
        """Whether the stand carries angle-count basal-area and stem estimates."""
        return (
            bool(getattr(stand, "use_angle_count", False))
            and "BasalArea" in stand._metric_estimates
            and "Stems" in stand._metric_estimates
        )

    def adapt(self, stand, **kwargs) -> Dict[str, Any]:  # noqa: ANN001
        """Bin each species into a single class at its own QMD.

        A relascope tally supports one class per species and no more; the width
        of the real distribution is not in the data.
        """
        stand._ensure_qmd_estimates()
        ba_dict = stand._metric_estimates["BasalArea"]
        n_dict = stand._metric_estimates["Stems"]
        dclass: Dict[Any, Dict[str, List[float]]] = {}
        for key, _ in ba_dict.items():
            if key == "TOTAL":
                continue
            N = float(n_dict.get(key, Stems(0.0)))
            if N <= 0:
                continue
            q = float(stand.QMD(key))
            dclass[key] = {"bin_mids_cm": [q], "n_per_ha": [N]}
        if not dclass:
            N = float(stand.Stems)
            q = float(stand.QMD)
            if q > 0 and N > 0:
                dclass["TOTAL"] = {"bin_mids_cm": [q], "n_per_ha": [N]}
        return {"dclass": dclass}


@dataclass
class TreeListToDiameterClassAdapter(Adapter):
    """Histogram from a real tree list."""

    name: str = "tree_list_to_diameter_class"
    target_mode: str = "diameter_class"
    bin_width_cm: float = 2.0

    def can_adapt(self, stand) -> bool:  # noqa: ANN001
        """Whether the stand holds measured trees rather than angle-count tallies."""
        return (not getattr(stand, "use_angle_count", False)) and any(p.trees for p in stand.plots)

    def adapt(self, stand, **kwargs) -> Dict[str, Any]:  # noqa: ANN001
        """Histogram the measured stems into fixed-width diameter classes.

        Each tree contributes ``weight_n`` stems per hectare of its plot's
        effective (post-occlusion) area to the class its diameter falls in.
        """
        bin_w = float(kwargs.get("bin_width_cm", self.bin_width_cm))
        per_sp: Dict[Any, List[tuple[float, float, float]]] = {}
        for p in stand.plots:
            eff_area = p.area_ha * (1 - p.occlusion) if (1 - p.occlusion) > 0 else p.area_ha
            for t in p.trees:
                sp = getattr(t, "species", None)
                if t.diameter_cm is None or sp is None:
                    continue
                per_sp.setdefault(sp, []).append(
                    (float(t.diameter_cm), float(t.weight_n or 1.0), eff_area)
                )
        dclass: Dict[Any, Dict[str, List[float]]] = {}
        for sp, items in per_sp.items():
            if not items:
                continue
            d_vals = [d for (d, _, _) in items]
            d_min, d_max = min(d_vals), max(d_vals)
            lo = bin_w * math.floor(d_min / bin_w)
            # At least one bin, always. When every tree of a species shares a
            # diameter that sits exactly on a bin boundary -- 20.0 cm at a 2 cm
            # width -- the span rounds to zero, and the empty ``mids`` that
            # produced made the ``counts[idx]`` below index an empty list.
            n_bins = max(1, math.ceil((d_max - lo) / bin_w))
            mids = [lo + bin_w * i + bin_w / 2.0 for i in range(n_bins)]
            counts = [0.0 for _ in mids]
            for d, w, eff_area in items:
                idx = int((d - lo) // bin_w)
                idx = max(0, min(idx, len(mids) - 1))
                counts[idx] += w / eff_area
            dclass[sp] = {"bin_mids_cm": mids, "n_per_ha": counts}
        if not dclass:
            return AngleCountToDiameterClassAdapter().adapt(stand)
        return {"dclass": dclass}


# ------------------------------ Tree-list -> Spatial --------------------------


@dataclass
class TreeListToSpatialAdapter(Adapter):
    """Ensure every tree has a position; fill missing uniformly within its plot."""

    name: str = "tree_list_to_spatial"
    target_mode: str = "spatial"

    def can_adapt(self, stand) -> bool:  # noqa: ANN001
        """Whether the stand holds measured trees rather than angle-count tallies."""
        return (not getattr(stand, "use_angle_count", False)) and any(p.trees for p in stand.plots)

    def adapt(self, stand, **kwargs) -> Dict[str, Any]:  # noqa: ANN001
        """Fill in a position for every tree that lacks one.

        Missing coordinates are drawn uniformly within the tree's own plot.
        Trees that already carry a position keep it.
        """
        rng = _adapter_rng(kwargs, default_seed=2027)
        plots = []
        for p in stand.plots:
            plots.append(p)
            r = getattr(p, "radius_m", sqrt(p.area_m2 / pi))
            for t in p.trees:
                if getattr(t, "position", None) is None:
                    rr = r * math.sqrt(rng.random())
                    theta = 2 * math.pi * rng.random()
                    t.position = Position(rr * math.cos(theta), rr * math.sin(theta))
        return {"plots": plots}


# -------------------------------- Registry -----------------------------------


class AdapterRegistry:
    """Named lookup for the inventory adapters ``build_context`` chooses from."""

    def __init__(self):
        """Register the built-in adapters."""
        self._by_name: Dict[str, Adapter] = {}
        self.register(AngleCountToPseudoTreesAdapter())
        self.register(AngleCountToSpatialPseudoTreesAdapter())
        self.register(AngleCountToDiameterClassAdapter())
        self.register(TreeListToDiameterClassAdapter())
        self.register(TreeListToSpatialAdapter())

    def register(self, adapter: Adapter) -> None:
        """Add ``adapter`` under its own ``name``, replacing any previous one."""
        self._by_name[adapter.name] = adapter

    def get(self, name: str) -> Optional[Adapter]:
        """Get."""
        return self._by_name.get(name)

    def find_for(self, target_mode: str) -> List[Adapter]:
        """Find for."""
        return [a for a in self._by_name.values() if a.target_mode == target_mode]

    @staticmethod
    def default() -> "AdapterRegistry":
        """Default."""
        if not hasattr(AdapterRegistry, "_DEFAULT"):
            AdapterRegistry._DEFAULT = AdapterRegistry()  # type: ignore[attr-defined]
        return AdapterRegistry._DEFAULT  # type: ignore[attr-defined]
