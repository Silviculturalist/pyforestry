"""Core simulation context, actions, and metric utilities."""

from __future__ import annotations

import copy
import warnings
from dataclasses import dataclass, field

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

from pyforestry.base.helpers import CircularPlot, Stand, TreeName
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
    """The context of one run: a stand, a clock, an audit trail.

    The stand is the state. This class used to own a second copy of it -- its own
    metric store, its own diameter-class inventory, its own plot-to-stand
    estimator -- and the two disagreed by a factor that grew with the number of
    species in the stand. Now :attr:`stand` holds every representation and every
    metric, and this class holds what is genuinely about the *run*: which
    inventory mode the model asked for, where time stands, the model itself, the
    RNG bundle, and the history.

    ``mode`` (∈ ``{"spatial", "tree_list", "diameter_class", "aggregate"}``) is
    the model's requirement, not the stand's storage: ``spatial`` and
    ``tree_list`` are the same representation, differing in whether the model
    needs tree positions.
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
        self.origin_ref = origin_ref  # provenance only
        self.model = model
        self.random_bundle = random_bundle
        self.stand: Stand = self._build_stand(mode, inventory, area_ha, site)

        self.state: Dict[str, Any] = dict(initial_state)
        self.attrs: Dict[str, Any] = dict(initial_attrs or {})
        #: The model's typed run inputs, resolved once by
        #: :meth:`GrowthModel.build_context`. ``None`` for a model that has not
        #: declared an ``Inputs`` type and still reads ``attrs`` directly.
        self.inputs: Any = None
        self.history: List[HistoryEntry] = []
        self.state.setdefault("t", 0.0)
        self.state.setdefault("last_dt", 0.0)

    def _build_stand(
        self,
        mode: str,
        inventory: Dict[str, Any],
        area_ha: Optional[float],
        site: Optional[Any],
    ) -> Stand:
        """Build the run's working stand from the inventory payload.

        The stand is a sandbox: plot containers are copied so a run cannot append
        to or thin the caller's inventory, while the ``Tree`` objects themselves
        are shared by reference, which is what lets a model mutate diameters in
        place and what :attr:`Tree.uid` exists to make traceable.
        """
        if mode in ("tree_list", "spatial"):
            stand = Stand(
                site=site,
                area_ha=area_ha,
                plots=self._copy_plots_with_tree_refs(inventory["plots"]),
            )
            stand.refresh_metrics()
            return stand
        if mode == "aggregate":
            return Stand.from_aggregate_metrics(inventory["metrics"], site=site, area_ha=area_ha)
        return Stand.from_diameter_classes(inventory["dclass"], site=site, area_ha=area_ha)

    # --------------------------- Stand delegation -----------------------------
    #
    # These forward to the one state object. They are kept because they read
    # better at a call site inside a model (``ctx.plots``, ``ctx.area_ha``) and
    # because removing them would touch every adapter for no gain -- but there is
    # no second store behind them.

    @property
    def area_ha(self) -> Optional[float]:
        """The stand's area in hectares, if known."""
        return self.stand.area_ha

    @property
    def site(self) -> Optional[Any]:
        """The stand's site reference, if any."""
        return self.stand.site

    @property
    def plots(self) -> List[CircularPlot]:
        """The working copy's plots.

        Raises:
            AttributeError: If the run is not in a tree-list representation.
        """
        if self.stand.representation not in ("tree_list", "angle_count"):
            raise AttributeError(
                f"This context is in {self.mode!r} mode, which holds no plots. "
                f"Read ctx.diameter_classes or ctx.metrics instead."
            )
        return self.stand.plots

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
        if self.stand.representation in ("tree_list", "angle_count"):
            plots = self.stand.plots
            tree_stats = {
                "n_plots": len(plots),
                "n_trees": sum(len(p.trees) for p in plots),
            }
        else:
            tree_stats = {"n_plots": 0, "n_trees": 0}

        metrics = self._metrics
        ba = float(metrics["BasalArea"]["TOTAL"]) if metrics["BasalArea"] else 0.0
        stems = float(metrics["Stems"]["TOTAL"]) if metrics["Stems"] else 0.0
        qmd = float(metrics["QMD"]["TOTAL"]) if metrics["QMD"] else 0.0

        return {
            "mode": self.mode,
            "t": self.state.get("t", 0.0),
            "metrics_total": {"BasalArea": ba, "Stems": stems, "QMD": qmd},
            "tree_stats": tree_stats,
            "state": copy.deepcopy(self.state),
        }

    @property
    def diameter_classes(self) -> Dict[Any, Dict[str, List[float]]]:
        """The stand's diameter-class inventory, keyed by species.

        Each entry holds ``bin_mids_cm`` and a matching ``n_per_ha``. This is a
        copy: mutate it freely and hand it back through
        :meth:`set_diameter_class`, which revalidates and refreshes the metrics.

        Raises:
            RuntimeError: If the context is not in diameter-class mode.
        """
        return self.stand.diameter_classes

    @property
    def _metrics(self) -> MetricMap:
        """The stand's metric estimates, in this module's three-key shape.

        Reads through to :attr:`Stand._metric_estimates`; there is no second
        store. ``Stand`` also computes BAWAD and Lorey's height, which this view
        drops because nothing in the runtime consumes them yet -- read them off
        ``ctx.stand`` when that changes.
        """
        estimates = self.stand._metric_estimates
        if "QMD" not in estimates:
            # Stand derives QMD lazily; force it here so every mode reports the
            # same three keys. An angle-count stand whose tallies carry no
            # diameters genuinely cannot produce one, and says so by raising.
            try:
                self.stand.QMD  # noqa: B018 -- accessed for its side effect
            except KeyError:
                pass
        return cast(
            MetricMap,
            {
                "Stems": estimates.get("Stems", {}),
                "BasalArea": estimates.get("BasalArea", {}),
                "QMD": estimates.get("QMD", {}),
            },
        )

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

    # ---------------------------- State mutation ------------------------------
    #
    # Every one of these forwards to the stand, which owns both the state and the
    # rule about which representation may be written directly.

    def set_aggregate_metrics(self, *, ba_total: float, stems_total: float) -> None:
        """Set aggregate basal area and stems, then recompute QMD.

        Raises:
            RuntimeError: If the context is not in aggregate mode.
        """
        self.stand.set_aggregate_metrics(ba_total=ba_total, stems_total=stems_total)

    def set_species_metrics(
        self,
        *,
        basal_area: Mapping[Any, Any],
        stems: Mapping[Any, Any],
    ) -> None:
        """Publish a per-species aggregate result, deriving totals and QMD.

        This is the public path for a model that steps species cohorts and knows
        the breakdown. Writing ``ctx._metrics`` directly used to be the only way,
        which put two modules' arithmetic in charge of the same invariants.

        Raises:
            RuntimeError: If the context is not in aggregate mode.
        """
        self.stand.set_species_metrics(basal_area=basal_area, stems=stems)

    def scale_stems(self, factor: float) -> None:
        """Scale aggregate stems and basal area by ``factor``.

        Raises:
            RuntimeError: If the context is not in aggregate mode.
        """
        self.stand.scale_stems(factor)

    def set_diameter_class(self, dclass: Dict[Any, Dict[str, List[float]]]) -> None:
        """Replace diameter-class inventory and recompute metrics.

        Raises:
            RuntimeError: If the context is not in diameter-class mode.
        """
        self.stand.set_diameter_classes(dclass)

    # ----------------------------- Internal utils -----------------------------

    def _refresh_metrics(self) -> None:
        """Rebuild the stand's metrics from whichever representation it holds."""
        self.stand.refresh_metrics()

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
            inventory = {"plots": copy.deepcopy(self.stand.plots)}
        elif self.mode == "diameter_class":
            inventory = {"dclass": copy.deepcopy(self.stand.diameter_classes)}
        else:
            inventory = {"metrics": copy.deepcopy(dict(self._metrics))}

        payload: Dict[str, Any] = {
            "mode": self.mode,
            "area_ha": self.stand.area_ha,
            "site": copy.deepcopy(self.stand.site),
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
