"""Core simulation context, actions, and metric utilities."""

from __future__ import annotations

import copy
import warnings
from dataclasses import dataclass, field
from math import pi, sqrt

# ----------------------------- Actions & History ------------------------------
from typing import (
    Any,
    Callable,
    Concatenate,
    Dict,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    Optional,
    ParamSpec,
    Tuple,
    TypedDict,
    Union,
    cast,
)

import pandas as pd

from pyforestry.base.helpers import CircularPlot, Tree, TreeName, parse_tree_species
from pyforestry.base.helpers.primitives import QuadraticMeanDiameter, StandBasalArea, Stems

# ---- Type aliases for metric containers ----
MetricKey = Union[TreeName, str]
MetricValue = Union[StandBasalArea, Stems, QuadraticMeanDiameter]
MetricView = Mapping[str, Mapping[MetricKey, MetricValue]]  # read-only facade


# Mutable store
class MetricMap(TypedDict):
    """Mutable metrics mapping keyed by metric name and species."""

    Stems: Dict[MetricKey, Stems]
    BasalArea: Dict[MetricKey, StandBasalArea]
    QMD: Dict[MetricKey, QuadraticMeanDiameter]


P = ParamSpec("P")
ActionFn = Callable[Concatenate["SimulationContext", P], None]


@dataclass(frozen=True)
class ActionSpec:
    """Declarative action descriptor with mode gating."""

    name: str
    fn: Callable[..., None]
    description: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    # Legacy toggle (mapped to {"tree_list","spatial"}); prefer requires_modes.
    requires_tree_list: bool = False
    # New: explicit allowed modes, e.g. ["tree_list","spatial"] or []
    requires_modes: Optional[List[str]] = None
    # Optional: phases within update_step where this action is valid, e.g. ("pre","post")
    allowed_phases: Optional[Tuple[str, ...]] = None


@dataclass
class HistoryEntry:
    """History record capturing a single operation and its snapshots."""

    t: float
    op: str
    details: Dict[str, Any]
    model_state: Dict[str, Any]
    metrics: Mapping[
        str, Mapping[Union[TreeName, str], Union[StandBasalArea, Stems, QuadraticMeanDiameter]]
    ]
    pre_snapshot: Dict[str, Any]
    post_snapshot: Dict[str, Any]


# --------------------------------- Context -----------------------------------


class SimulationContext:
    """
    Sandboxed, auditable working copy for a single run.

    mode ∈ {"spatial","tree_list","diameter_class","aggregate"}
    """

    def __init__(
        self,
        *,
        mode: str,
        area_ha: Optional[float],
        site: Optional[Any],
        origin_ref: Any,
        inventory: Dict[str, Any],
        initial_state: Dict[str, Any],
        model: Any,
        initial_attrs: Optional[Dict[str, Any]] = None,
        random_bundle: Optional[Any] = None,
    ) -> None:
        """Initialize a simulation context with inventory and initial state.

        ``random_bundle`` is any object exposing ``snapshot()``/``restore(state)``
        (a :class:`~pyforestry.simulation.services.RandomBundle`, in practice). It
        is kept duck-typed so the base simulation layer does not depend on the
        staged runtime. Supplying one is what makes :meth:`checkpoint` and
        :meth:`from_checkpoint` reproduce a stochastic run.
        """
        if mode not in ("spatial", "tree_list", "diameter_class", "aggregate"):
            raise ValueError("mode must be 'spatial','tree_list','diameter_class', or 'aggregate'")
        self.mode = mode
        self.area_ha = area_ha
        self.site = site
        self.origin_ref = origin_ref  # provenance only
        self.model = model
        self.random_bundle = random_bundle
        # Internal inventory & metrics containers (dicts for mutability)
        self._metrics: MetricMap = {"Stems": {}, "BasalArea": {}, "QMD": {}}
        self._dclass: Dict[Any, Dict[str, List[float]]] = {}

        if self.mode in ("tree_list", "spatial"):
            self.plots: List[CircularPlot] = self._copy_plots_with_tree_refs(inventory["plots"])
            self._metrics = self._recompute_metrics_tree_list(self.plots)
        elif self.mode == "aggregate":
            self._metrics = self._normalize_aggregate_metrics(inventory["metrics"])
        else:  # "diameter_class"
            self._dclass = self._normalize_dclass_inventory(inventory["dclass"])
            self._metrics = self._recompute_metrics_dclass(self._dclass)

        self.state: Dict[str, Any] = dict(initial_state)
        self.attrs: Dict[str, Any] = dict(initial_attrs or {})
        self.history: List[HistoryEntry] = []
        self.state.setdefault("t", 0.0)
        self.state.setdefault("last_dt", 0.0)

    # ------------------------------ Public API --------------------------------

    def update_step(
        self,
        years: float,
        *,
        management: Optional[
            Mapping[str, Iterable[Union[str, tuple[str, Mapping[str, Any]]]]]
        ] = None,
    ) -> None:
        """
        Advance the simulation by ``years`` while allowing management hooks.

        ``management`` can map phase names ("pre", "mid", "post") to an iterable of
        action specifications. Each action specification may be a string (action name)
        or a tuple of ``(name, kwargs_mapping)`` to pass parameters. Phases execute
        in order: pre -> model update -> mid -> metrics refresh -> post. Actions are
        dispatched through ``self.do`` so model-provided capabilities still gate them.
        """

        def _phase_actions(
            phase: str, actions: Iterable[Union[str, tuple[str, Mapping[str, Any]]]]
        ):
            """Dispatch phase-specific actions by name and parameters."""
            for item in actions:
                if isinstance(item, tuple):
                    name, params = item
                    params = dict(params)
                else:
                    name, params = str(item), {}
                self.do(name, phase=phase, **params)

        mgmt: MutableMapping[str, Iterable[Union[str, tuple[str, Mapping[str, Any]]]]] = (
            dict(management) if management else {}
        )

        pre = self.snapshot()
        t0 = self.state.get("t", 0.0)
        t1 = t0 + years
        self.state["t"] = t1

        # Pre-update management
        _phase_actions("pre", mgmt.get("pre", ()))

        # Core model update
        if hasattr(self.model, "update_step"):
            self.model.update_step(self, years)  # type: ignore[call-arg]
        else:  # pragma: no cover - compatibility shim
            self.model.grow(self, years)  # type: ignore[call-arg]
        self.state["t"] = t1
        self.state["last_dt"] = years

        # Optional mid-phase hooks (after model update, before metric recompute)
        _phase_actions("mid", mgmt.get("mid", ()))

        self._refresh_metrics()
        post = self.snapshot()

        # Post-metric hooks (e.g. logging/valuation that depends on refreshed totals)
        _phase_actions("post", mgmt.get("post", ()))

        self._append_history(
            "update_step",
            {
                "dt": years,
                "management": {
                    k: [str(a[0] if isinstance(a, tuple) else a) for a in v]
                    for k, v in mgmt.items()
                },
            },
            pre,
            post,
        )

    def grow(self, years: float, **kwargs: Any) -> None:  # pragma: no cover - compatibility alias
        """Compatibility alias for :meth:`update_step`."""
        warnings.warn(
            "SimulationContext.grow is deprecated; use update_step instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.update_step(years, **kwargs)

    def do(self, action: str, *, phase: Optional[str] = None, **kwargs: Any) -> None:
        """Execute a named action with optional phase gating."""
        actions = self.model.available_actions()
        if action not in actions:
            raise KeyError(f"Action '{action}' not available for this model.")
        spec: ActionSpec = actions[action]

        # New gating
        requires_modes = set(spec.requires_modes or [])
        if spec.requires_tree_list:
            requires_modes.update({"tree_list", "spatial"})
        if requires_modes and self.mode not in requires_modes:
            req_str = ", ".join(sorted(requires_modes))
            raise RuntimeError(
                f"Action '{action}' requires mode in {{{req_str}}}, got '{self.mode}'."
            )
        if phase is not None and spec.allowed_phases:
            if phase not in spec.allowed_phases:
                allowed = ", ".join(spec.allowed_phases)
                raise RuntimeError(
                    f"Action '{action}' not permitted during '{phase}' phase (allowed: {allowed})."
                )

        pre = self.snapshot()
        spec.fn(self, **kwargs)
        self._refresh_metrics()
        post = self.snapshot()
        self._append_history(f"action:{action}", {"params": kwargs, "phase": phase}, pre, post)

    def snapshot(self) -> Dict[str, Any]:
        """Return a lightweight snapshot of state and aggregate totals."""
        if self.mode in ("tree_list", "spatial"):
            n_plots = len(self.plots)
            n_trees = sum(len(p.trees) for p in self.plots)
            tree_stats = {"n_plots": n_plots, "n_trees": n_trees}
        else:
            tree_stats = {"n_plots": 0, "n_trees": 0}

        ba = float(self._metrics["BasalArea"]["TOTAL"]) if "BasalArea" in self._metrics else 0.0
        stems = float(self._metrics["Stems"]["TOTAL"]) if "Stems" in self._metrics else 0.0
        qmd = float(self._metrics["QMD"]["TOTAL"]) if "QMD" in self._metrics else 0.0

        return {
            "mode": self.mode,
            "t": self.state.get("t", 0.0),
            "metrics_total": {"BasalArea": ba, "Stems": stems, "QMD": qmd},
            "tree_stats": tree_stats,
            "state": copy.deepcopy(self.state),
        }

    @property
    def metrics(self) -> MetricView:
        """Return a read-only copy of the current metrics."""
        m = self._metrics
        return cast(
            MetricView,
            {
                "Stems": dict(m["Stems"]),
                "BasalArea": dict(m["BasalArea"]),
                "QMD": dict(m["QMD"]),
            },
        )

    def to_pandas(self) -> pd.DataFrame:
        """Return the history log as a pandas DataFrame."""
        rows = []
        for h in self.history:
            rows.append(
                {
                    "t": h.t,
                    "op": h.op,
                    "details": h.details,
                    "ba_total": float(h.metrics.get("BasalArea", {}).get("TOTAL", 0.0)),
                    "n_total": float(h.metrics.get("Stems", {}).get("TOTAL", 0.0)),
                    "qmd_total_cm": float(h.metrics.get("QMD", {}).get("TOTAL", 0.0)),
                    "model_state": h.model_state,
                }
            )
        return pd.DataFrame(rows)

    # Aggregate helpers
    def set_aggregate_metrics(self, *, ba_total: float, stems_total: float) -> None:
        """Set aggregate basal area and stems, then recompute QMD."""
        self._metrics.setdefault("BasalArea", {})
        self._metrics.setdefault("Stems", {})
        self._metrics.setdefault("QMD", {})
        self._metrics["BasalArea"]["TOTAL"] = StandBasalArea(ba_total, species=None, precision=0.0)
        self._metrics["Stems"]["TOTAL"] = Stems(stems_total, species=None, precision=0.0)
        self._recompute_qmd()

    def scale_stems(self, factor: float) -> None:
        """Scale aggregate stems and basal area by ``factor``."""
        total_n = float(self._metrics["Stems"]["TOTAL"])
        total_ba = float(self._metrics["BasalArea"]["TOTAL"])
        new_n = max(0.0, total_n * factor)
        new_ba = max(0.0, total_ba * factor)
        self.set_aggregate_metrics(ba_total=new_ba, stems_total=new_n)

    # Diameter-class helper
    def set_diameter_class(self, dclass: Dict[Any, Dict[str, List[float]]]) -> None:
        """Replace diameter-class inventory and recompute metrics."""
        self._dclass = self._normalize_dclass_inventory(dclass)
        self._metrics = self._recompute_metrics_dclass(self._dclass)

    # ----------------------------- Internal utils -----------------------------

    def _refresh_metrics(self) -> None:
        """Refresh metrics based on the active inventory representation."""
        if self.mode in ("tree_list", "spatial"):
            computed = self._recompute_metrics_tree_list(self.plots)
            self._metrics = cast(
                MetricMap,
                {
                    "Stems": dict(computed.get("Stems", {})),
                    "BasalArea": dict(computed.get("BasalArea", {})),
                    "QMD": dict(computed.get("QMD", {})),
                },
            )

        elif self.mode == "aggregate":
            self._recompute_qmd()
        else:
            computed = self._recompute_metrics_dclass(self._dclass)
            self._metrics = cast(
                MetricMap,
                {
                    "Stems": dict(computed.get("Stems", {})),
                    "BasalArea": dict(computed.get("BasalArea", {})),
                    "QMD": dict(computed.get("QMD", {})),
                },
            )

    def _recompute_qmd(self) -> None:
        """Recompute quadratic mean diameter from aggregate totals."""
        try:
            ba = float(self._metrics["BasalArea"]["TOTAL"])
            n = float(self._metrics["Stems"]["TOTAL"])
            qmd_val = sqrt((40000.0 * ba) / (pi * n)) if (ba > 0 and n > 0) else 0.0
        except KeyError:
            qmd_val = 0.0
        self._metrics.setdefault("QMD", {})
        self._metrics["QMD"]["TOTAL"] = QuadraticMeanDiameter(qmd_val, precision=0.0)

    def _append_history(
        self, op: str, details: Dict[str, Any], pre: Dict[str, Any], post: Dict[str, Any]
    ) -> None:
        """Append a history entry capturing operation metadata and snapshots."""
        model_state = {k: v for k, v in self.state.items()}
        entry = HistoryEntry(
            t=self.state.get("t", 0.0),
            op=op,
            details=copy.deepcopy(details),
            model_state=model_state,
            metrics=self.metrics,
            pre_snapshot=pre,
            post_snapshot=post,
        )
        self.history.append(entry)

    def _copy_plots_with_tree_refs(self, plots: Iterable[CircularPlot]) -> List[CircularPlot]:
        """Copy plot containers while preserving references to the original tree objects."""
        out: List[CircularPlot] = []
        for p in plots:
            new_trees = list(p.trees)
            out.append(
                CircularPlot(
                    id=p.id,
                    occlusion=p.occlusion,
                    position=p.position,
                    area_m2=p.area_m2,
                    site=p.site,
                    AngleCount=[],  # never copy AngleCount tallies into sim inventory
                    trees=new_trees,
                )
            )
        return out

    def _normalize_aggregate_metrics(self, metrics_in: Dict[str, Dict[Any, Any]]) -> MetricMap:
        """Normalize aggregate metric inputs and compute derived values."""
        stems_dict = cast(Dict[MetricKey, Stems], dict(metrics_in.get("Stems", {})))
        ba_dict = cast(Dict[MetricKey, StandBasalArea], dict(metrics_in.get("BasalArea", {})))
        qmd_dict: Dict[MetricKey, QuadraticMeanDiameter] = {}
        stems_dict.setdefault("TOTAL", Stems(0.0))
        ba_dict.setdefault("TOTAL", StandBasalArea(0.0))
        out_map = cast(
            MetricMap,
            {"Stems": stems_dict, "BasalArea": ba_dict, "QMD": qmd_dict},
        )
        self._metrics = out_map
        self._recompute_qmd()
        return out_map

    def _recompute_metrics_tree_list(self, plots: Iterable[CircularPlot]) -> MetricMap:
        """Compute metric aggregates from tree-list plots."""
        species_data: Dict[TreeName, Dict[str, List[float]]] = {}

        def _eff_area_ha(p: CircularPlot) -> float:
            """Return effective plot area in hectares after occlusion."""
            area_ha = p.area_ha or 1.0
            return area_ha * (1 - p.occlusion) if (1 - p.occlusion) > 0 else area_ha

        for plot in plots:
            eff = _eff_area_ha(plot)
            by_sp: Dict[TreeName, List[Tree]] = {}
            for t in plot.trees:
                sp = getattr(t, "species", None)
                if sp is None:
                    continue
                if isinstance(sp, str):
                    sp = parse_tree_species(sp)
                by_sp.setdefault(sp, []).append(t)

            for sp, trs in by_sp.items():
                stems = 0.0
                for t in trs:
                    weight = getattr(t, "weight_n", 1.0)
                    stems += 1.0 if weight is None else float(weight)
                stems_ha = stems / eff
                ba_sum = 0.0
                for t in trs:
                    d_cm = float(getattr(t, "diameter_cm", 0.0) or 0.0)
                    r_m = (d_cm / 100.0) / 2.0
                    weight = getattr(t, "weight_n", 1.0)
                    ba_sum += pi * (r_m**2) * (1.0 if weight is None else float(weight))
                ba_ha = ba_sum / eff
                species_data.setdefault(sp, {"stems_per_ha": [], "basal_area_per_ha": []})
                species_data[sp]["stems_per_ha"].append(stems_ha)
                species_data[sp]["basal_area_per_ha"].append(ba_ha)

        stems_dict: Dict[Union[TreeName, str], Stems] = {}
        ba_dict: Dict[Union[TreeName, str], StandBasalArea] = {}
        total_stems_val = 0.0
        total_ba_val = 0.0
        for sp, vals in species_data.items():
            s_vals = vals["stems_per_ha"]
            b_vals = vals["basal_area_per_ha"]
            stems_mean = sum(s_vals) / len(s_vals) if s_vals else 0.0
            ba_mean = sum(b_vals) / len(b_vals) if b_vals else 0.0
            stems_dict[sp] = Stems(stems_mean, species=sp, precision=0.0)
            ba_dict[sp] = StandBasalArea(ba_mean, species=sp, precision=0.0)
            total_stems_val += stems_mean
            total_ba_val += ba_mean

        stems_dict["TOTAL"] = Stems(total_stems_val, species=None, precision=0.0)
        ba_dict["TOTAL"] = StandBasalArea(total_ba_val, species=None, precision=0.0)
        qmd_dict: Dict[Union[TreeName, str], QuadraticMeanDiameter] = {}
        if total_stems_val > 0 and total_ba_val > 0:
            total_qmd = sqrt((40000.0 * total_ba_val) / (pi * total_stems_val))
        else:
            total_qmd = 0.0
        qmd_dict["TOTAL"] = QuadraticMeanDiameter(total_qmd, precision=0.0)
        return cast(
            MetricMap,
            {"Stems": stems_dict, "BasalArea": ba_dict, "QMD": qmd_dict},
        )

    def _normalize_dclass_inventory(
        self, dclass_in: Dict[Any, Dict[str, List[float]]]
    ) -> Dict[Any, Dict[str, List[float]]]:
        """Validate and normalize diameter-class inventory arrays."""
        out: Dict[Any, Dict[str, List[float]]] = {}
        for key, rec in dclass_in.items():
            mids = list(rec.get("bin_mids_cm", []))
            nph = list(rec.get("n_per_ha", []))
            if len(mids) != len(nph):
                raise ValueError(f"Diameter-class arrays length mismatch for {key}.")
            out[key] = {"bin_mids_cm": mids, "n_per_ha": nph}
        return out

    def _recompute_metrics_dclass(self, dclass: Dict[Any, Dict[str, List[float]]]) -> MetricMap:
        """Compute metric aggregates from diameter-class inventory."""
        stems_dict: Dict[Union[TreeName, str], Stems] = {}
        ba_dict: Dict[Union[TreeName, str], StandBasalArea] = {}
        total_n = 0.0
        total_ba = 0.0
        for key, rec in dclass.items():
            mids = rec["bin_mids_cm"]
            nph = rec["n_per_ha"]
            n_sp = sum(nph)
            ba_sp = 0.0
            for D_cm, n_i in zip(mids, nph, strict=False):
                r_m = (float(D_cm) / 100.0) / 2.0
                ba_sp += float(n_i) * (pi * r_m * r_m)
            stems_dict[key] = Stems(n_sp, species=key if key != "TOTAL" else None, precision=0.0)
            ba_dict[key] = StandBasalArea(
                ba_sp, species=key if key != "TOTAL" else None, precision=0.0
            )
            if key != "TOTAL":
                total_n += n_sp
                total_ba += ba_sp
        stems_dict["TOTAL"] = Stems(total_n, species=None, precision=0.0)
        ba_dict["TOTAL"] = StandBasalArea(total_ba, species=None, precision=0.0)
        qmd_dict: Dict[Union[TreeName, str], QuadraticMeanDiameter] = {}
        if total_ba > 0.0 and total_n > 0.0:
            qmd_dict["TOTAL"] = QuadraticMeanDiameter(
                sqrt((40000.0 * total_ba) / (pi * total_n)), precision=0.0
            )
        else:
            qmd_dict["TOTAL"] = QuadraticMeanDiameter(0.0, precision=0.0)
        return cast(
            MetricMap,
            {"Stems": stems_dict, "BasalArea": ba_dict, "QMD": qmd_dict},
        )

    # Used by ensemble to log vector updates
    def _log_external_update(self, op: str, details: Dict[str, Any]) -> None:
        """Log an external update while refreshing metrics."""
        pre = self.snapshot()
        self._refresh_metrics()
        post = self.snapshot()
        self._append_history(op, details, pre, post)

    # --------------------------- Checkpointing -------------------------------

    def checkpoint(
        self,
        *,
        include_history: bool = False,
        history_tail: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Return a serialisable snapshot of the context state and inventory.

        The checkpoint includes mode, area/site provenance, state/attrs, and the
        current inventory representation (plots for tree_list/spatial, diameter
        classes for diameter_class, aggregate metrics otherwise). History is not
        captured unless explicitly requested.
        """

        if self.mode in ("tree_list", "spatial"):
            inventory = {"plots": copy.deepcopy(self.plots)}
        elif self.mode == "diameter_class":
            inventory = {"dclass": copy.deepcopy(self._dclass)}
        else:
            inventory = {"metrics": copy.deepcopy(self._metrics)}

        payload: Dict[str, Any] = {
            "mode": self.mode,
            "area_ha": self.area_ha,
            "site": copy.deepcopy(self.site),
            "state": copy.deepcopy(self.state),
            "attrs": copy.deepcopy(self.attrs),
            "inventory": inventory,
        }
        rng_bundle = getattr(self, "random_bundle", None)
        if rng_bundle is not None and hasattr(rng_bundle, "snapshot"):
            payload["rng_state"] = rng_bundle.snapshot()
        if include_history:
            if history_tail is not None:
                history_slice = self.history[-int(history_tail) :]
            else:
                history_slice = self.history
            payload["history"] = copy.deepcopy(history_slice)
        return payload

    @classmethod
    def from_checkpoint(
        cls,
        model: Any,
        checkpoint: Mapping[str, Any],
        *,
        random_bundle: Optional[Any] = None,
    ) -> "SimulationContext":
        """
        Restore a context from ``checkpoint`` produced by :meth:`checkpoint`.

        ``model`` must be the growth model instance that will drive the context.
        ``random_bundle`` receives any RNG state the checkpoint carries. Without it
        a checkpoint's ``rng_state`` cannot be restored, and a stochastic run
        resumed from it would silently diverge -- so that combination raises rather
        than continuing with a fresh stream.

        Raises:
            ValueError: If the checkpoint carries RNG state but no bundle was given
                to restore it into.
        """

        payload = dict(checkpoint)
        mode = payload["mode"]
        inventory = payload["inventory"]
        ctx = cls(
            mode=mode,
            area_ha=payload.get("area_ha"),
            site=payload.get("site"),
            origin_ref=None,
            inventory=inventory,
            initial_state=payload.get("state", {}),
            model=model,
            initial_attrs=payload.get("attrs", {}),
            random_bundle=random_bundle,
        )
        if "history" in payload:
            ctx.history = list(payload["history"])
        if "rng_state" in payload:
            bundle = ctx.random_bundle
            if bundle is None or not hasattr(bundle, "restore"):
                raise ValueError(
                    "This checkpoint carries RNG state but no random_bundle was supplied "
                    "to restore it into; resuming without it would silently diverge from "
                    "the checkpointed run. Pass "
                    "SimulationContext.from_checkpoint(..., random_bundle=...)."
                )
            bundle.restore(payload["rng_state"])
        return ctx
