"""Core simulation context, actions, and metric utilities."""

from __future__ import annotations

import copy
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
    Optional,
    ParamSpec,
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
    """Declarative action descriptor with mode gating.

    ``requires_modes`` is the gate: the inventory modes this action can run in,
    or an empty list for one that works in all of them. A second field,
    ``requires_tree_list``, used to mean ``["tree_list", "spatial"]`` and was
    unioned with this one -- two spellings of the same gate, with nothing in the
    package setting the older.
    """

    name: str
    fn: Callable[..., None]
    description: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    #: Inventory modes this action may run in, e.g. ``["tree_list", "spatial"]``.
    #: ``None`` or ``[]`` means every mode.
    requires_modes: Optional[List[str]] = None


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

        ``random_bundle`` is any object exposing ``rng_for(*keys)``,
        ``snapshot()`` and ``restore(state)`` (a
        :class:`~pyforestry.simulation.services.RandomBundle`, in practice). It is
        kept duck-typed so the base simulation layer does not depend on the
        services package. Supplying one is what makes :meth:`checkpoint` and
        :meth:`from_checkpoint` reproduce a stochastic run, and what lets a model
        reach a keyed stream through :attr:`rng` instead of building its own.
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
    def rng(self) -> Any:
        """The run's root random stream. Derive sub-streams with ``.child(...)``.

        Every stochastic kernel in this package takes its generator as a
        parameter and none constructs one, because a generator built where it is
        used cannot be seeded by the run, cannot be checkpointed, and -- when two
        of them are seeded from the same scalar, as the Elfving composite once did
        -- makes the interleaving of draws across them an unwritten part of the
        result. Ask for a keyed stream instead::

            rng = ctx.rng.child("mortality").child(str(species))

        Raises:
            RuntimeError: If the context was built without a random bundle. A run
                that draws random numbers needs a seed, and defaulting to an
                unseeded generator would make it silently irreproducible.
        """
        bundle = self.random_bundle
        if bundle is None:
            raise RuntimeError(
                "This context has no random bundle, so it cannot supply a random "
                "stream. Build it with a seed -- model.build_context(stand, "
                "seed=42) -- or pass random_bundle= explicitly. Defaulting to an "
                "unseeded generator would make the run irreproducible without "
                "saying so."
            )
        return bundle.rng_for()

    def holds_tree_list(self) -> bool:
        """Whether this run's stand stores individual trees.

        ``True`` for ``mode`` ``"tree_list"`` and ``"spatial"``, which are the
        same storage and differ only in whether the model needs tree positions.

        This is the one place the two vocabularies are reconciled. ``mode`` is the
        *model's* requirement and ``stand.representation`` is the *stand's*
        storage; they answer different questions but overlap in their values, and
        methods here keyed off whichever came to hand -- :meth:`snapshot` branched
        on the representation while :meth:`checkpoint` branched on the mode, so
        the two would have described different stands the first time they
        disagreed.
        """
        return self.stand.representation in ("tree_list", "angle_count")

    @property
    def plots(self) -> List[CircularPlot]:
        """The working copy's plots.

        Raises:
            AttributeError: If the run's stand holds no individual trees.
        """
        if not self.holds_tree_list():
            raise AttributeError(
                f"This context is in {self.mode!r} mode, which holds no plots. "
                f"Read ctx.diameter_classes or ctx.metrics instead."
            )
        return self.stand.plots

    # ------------------------------ Public API --------------------------------

    def update_step(self, years: float) -> None:
        """Advance the model by ``years``, refresh the metrics, record the step.

        This is the atom, not the schedule. Management used to be threaded through
        here as a dict of ``{"pre": [...], "mid": [...], "post": [...]}`` action
        names -- one of the three schedulers this package carried. It is now a
        :class:`~pyforestry.base.simulation.pipeline.ManagementStep` placed where
        you want it in a pipeline, which is the same capability with an ordering
        you can read.
        """
        pre = self.snapshot()
        t1 = self.state.get("t", 0.0) + years

        self.model.update_step(self, years)
        self.state["t"] = t1
        self.state["last_dt"] = years

        self._refresh_metrics()
        post = self.snapshot()
        self._append_history("update_step", {"dt": years}, pre, post)

    def do(self, action: str, **kwargs: Any) -> None:
        """Execute a capability the model declares, gated on the inventory mode."""
        actions = self.model.available_actions()
        if action not in actions:
            raise KeyError(f"Action '{action}' not available for this model.")
        spec: ActionSpec = actions[action]

        requires_modes = set(spec.requires_modes or [])
        if requires_modes and self.mode not in requires_modes:
            req_str = ", ".join(sorted(requires_modes))
            raise RuntimeError(
                f"Action '{action}' requires mode in {{{req_str}}}, got '{self.mode}'."
            )

        pre = self.snapshot()
        spec.fn(self, **kwargs)
        self._refresh_metrics()
        post = self.snapshot()
        self._append_history(f"action:{action}", {"params": kwargs}, pre, post)

    def snapshot(self) -> Dict[str, Any]:
        """Return a lightweight snapshot of state and aggregate totals."""
        if self.holds_tree_list():
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

        Reads through to :meth:`Stand.metric_estimates`; there is no second
        store. ``Stand`` also computes BAWAD and Lorey's height, which this view
        drops because nothing in the runtime consumes them yet -- read them off
        ``ctx.stand`` when that changes.
        """
        estimates = self.stand.metric_estimates()
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

        if self.holds_tree_list():
            inventory = {"plots": copy.deepcopy(self.stand.plots)}
        elif self.stand.representation == "diameter_class":
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
            # The root seed too, not only the per-stream states: a stream reached
            # for the first time after a restore derives its seed from the root,
            # and without it that stream would be a different one. It is also what
            # lets :meth:`from_checkpoint` rebuild a bundle when the caller has no
            # way to hand one over -- a worker process, say.
            root_seed = getattr(rng_bundle, "seed", None)
            if root_seed is not None:
                payload["rng_seed"] = int(root_seed)
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
        ``random_bundle`` receives any RNG state the checkpoint carries. Pass one
        to restore into a bundle you already hold; otherwise a checkpoint that
        records its root seed rebuilds an equivalent bundle here, which is what
        lets a checkpoint cross a process boundary -- :func:`run_parallel` hands
        one to a worker that has no bundle to give.

        A checkpoint carrying RNG state but *no* seed still raises: resuming that
        one without a bundle would silently continue on a fresh stream.

        Raises:
            ValueError: If the checkpoint carries RNG state that cannot be
                restored -- no bundle given, and no root seed recorded.
        """

        payload = dict(checkpoint)
        mode = payload["mode"]
        inventory = payload["inventory"]
        if random_bundle is None and "rng_state" in payload and "rng_seed" in payload:
            from pyforestry.simulation.services import RandomBundle

            random_bundle = RandomBundle(int(payload["rng_seed"]))
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
