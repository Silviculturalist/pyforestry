"""The growth-model interface every scientific model adapter implements.

A :class:`GrowthModel` binds a published model to the runtime: it declares what
inventory it needs (:class:`Requirements`), turns a :class:`Stand` into the
working copy it will step (:meth:`GrowthModel.build_context`), advances that copy
(:meth:`GrowthModel.update_step`), and optionally exposes management actions.

Implementers override ``requirements``, ``update_step``, ``component_id`` and
``source``; everything else has a usable default. :class:`ExampleStandGeneralModel`
at the bottom of this module is a minimal working reference, not a scientific
model.
"""

# pyforestry/base/simulation/growth_model.py
from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar, Dict, List, Literal, Optional, Tuple

from pyforestry.base.contracts import SourceReference
from pyforestry.base.helpers import Stand
from pyforestry.base.helpers.primitives import StandBasalArea, Stems

from .core import ActionSpec, SimulationContext

InventoryMode = Literal["spatial", "tree_list", "diameter_class", "aggregate", "either"]


def _has_tree_list(stand: Stand) -> bool:
    """Return True when ``stand`` holds measured trees rather than angle-count tallies."""
    return (not stand.use_angle_count) and any(p.trees for p in stand.plots)


def _has_positions(stand: Stand) -> bool:
    """Return True when every tree in ``stand`` carries a spatial position."""
    if not _has_tree_list(stand):
        return False
    return all(getattr(t, "position", None) is not None for p in stand.plots for t in p.trees)


def _has_aggregates(stand: Stand) -> bool:
    """Return True when ``stand`` can report a total basal area and stem count."""
    try:
        float(stand.BasalArea)
        float(stand.Stems)
        return True
    except Exception:
        return False


def _select_mode(req: "Requirements", stand: Stand, mode_hint: Optional[str]) -> str:
    """Decide which inventory mode a run of this model will use.

    One function, called by both :meth:`GrowthModel.can_build` and
    :meth:`GrowthModel.build_context`. They used to decide separately and did not
    agree: ``can_build`` tested ``mode_hint or req.inventory``, so for a model
    declaring ``"either"`` on an angle-count stand it checked the ``"either"``
    branch while ``build_context`` went on to choose ``"aggregate"`` -- two
    answers to "what will this run do" that had to be kept in step by hand.

    Args:
        req: The model's declared requirements.
        stand: The inventory to run on.
        mode_hint: The caller's override. Only meaningful when ``req.inventory``
            is ``"either"``; a model that declares a concrete mode gets it.

    Returns:
        One of ``"spatial"``, ``"tree_list"``, ``"diameter_class"``, ``"aggregate"``.
    """
    if req.inventory != "either":
        return req.inventory
    if mode_hint is not None:
        return mode_hint
    if stand.use_angle_count:
        # Angle-count tallies carry no stems unless diameters were recorded, so
        # aggregate is the safe default for a model that accepts either.
        return "aggregate"
    return "tree_list" if any(p.trees for p in stand.plots) else "aggregate"


#: What ``_acquire_inventory`` returns: the payload, the mode actually obtained
#: (which can differ from the one asked for when no adapter could supply it), how
#: it was obtained, and which adapter ran, if any.
AcquiredInventory = Tuple[Dict[str, Any], str, str, Optional[str]]


def _acquire_tree_list(
    stand: Stand,
    mode: str,
    use_adapter: Optional[str],
    adapter_kwargs: Dict[str, Any],
) -> AcquiredInventory:
    """Obtain a tree list or a spatial tree list, adapting angle-count tallies if needed.

    Raises:
        ValueError: If ``use_adapter`` names an adapter that cannot adapt ``stand``.
    """
    from .adapters import AdapterRegistry

    registry = AdapterRegistry.default()
    plots_payload = None
    adapter_used: Optional[str] = None

    if stand.use_angle_count:
        if use_adapter:
            adapter = registry.get(use_adapter)
            if adapter is None or not adapter.can_adapt(stand):
                raise ValueError(f"Adapter '{use_adapter}' cannot adapt this stand.")
            plots_payload = adapter.adapt(stand, **adapter_kwargs)["plots"]
            adapter_used = use_adapter
        else:
            preferred = (
                ["angle_count_spatial_pseudo_tree_list", "angle_count_pseudo_tree_list"]
                if mode == "spatial"
                else ["angle_count_pseudo_tree_list", "angle_count_spatial_pseudo_tree_list"]
            )
            for name in preferred:
                adapter = registry.get(name)
                if adapter and adapter.can_adapt(stand):
                    plots_payload = adapter.adapt(stand, **adapter_kwargs)["plots"]
                    adapter_used = name
                    break
        if plots_payload is None:
            # No adapter could turn the tallies into stems, so fall back to the
            # aggregate metrics the tallies do support.
            return (
                {"metrics": _aggregate_metrics(stand)},
                "aggregate",
                "angle_count_aggregate",
                None,
            )

    elif mode == "spatial" and not _has_positions(stand):
        adapter = registry.get("tree_list_to_spatial")
        if adapter and adapter.can_adapt(stand):
            plots_payload = adapter.adapt(stand, **adapter_kwargs)["plots"]
            adapter_used = "tree_list_to_spatial"
        else:
            mode = "tree_list"

    inventory = {"plots": plots_payload if plots_payload is not None else stand.plots}
    return inventory, mode, adapter_used or mode, adapter_used


def _acquire_diameter_classes(
    stand: Stand,
    adapter_kwargs: Dict[str, Any],
) -> AcquiredInventory:
    """Obtain a diameter-class inventory, binning a tree list or tallies if possible."""
    from .adapters import AdapterRegistry

    registry = AdapterRegistry.default()
    payload = None
    adapter_used: Optional[str] = None

    if _has_tree_list(stand):
        adapter = registry.get("tree_list_to_diameter_class")
        if adapter:
            payload = adapter.adapt(stand, **adapter_kwargs)["dclass"]
            adapter_used = "tree_list_to_diameter_class"
    else:
        adapter = registry.get("angle_count_to_diameter_class")
        if adapter and adapter.can_adapt(stand):
            payload = adapter.adapt(stand, **adapter_kwargs)["dclass"]
            adapter_used = "angle_count_to_diameter_class"

    if payload is not None:
        return (
            {"dclass": payload},
            "diameter_class",
            adapter_used or "diameter_class",
            adapter_used,
        )

    # Nothing to bin, so stand in a single class at the stand's own QMD.
    ba = float(stand.BasalArea)
    n = float(stand.Stems)
    qmd = float(stand.QMD) if n > 0 and ba > 0 else 0.0
    payload = {
        "TOTAL": {
            "bin_mids_cm": [qmd] if qmd > 0 else [],
            "n_per_ha": [n] if qmd > 0 else [],
        }
    }
    return {"dclass": payload}, "diameter_class", "diameter_class_from_qmd", None


def _acquire_inventory(
    stand: Stand,
    mode: str,
    use_adapter: Optional[str],
    adapter_kwargs: Dict[str, Any],
) -> AcquiredInventory:
    """Obtain the representation ``mode`` names, and record how it was obtained.

    Split out of :meth:`GrowthModel.build_context`, which carried mode selection,
    representation acquisition and provenance recording in one 120-line body with
    ``mode`` reassigned in two of its branches -- so reading it meant tracking
    which of the four modes was live at each point.

    Returns:
        ``(inventory, mode, origin, adapter_used)``. ``mode`` is the mode actually
        obtained: asking for a tree list from angle-count tallies no adapter can
        expand yields ``"aggregate"``, and asking for positions no adapter can
        supply yields ``"tree_list"``.
    """
    if mode in ("tree_list", "spatial"):
        return _acquire_tree_list(stand, mode, use_adapter, adapter_kwargs)
    if mode == "diameter_class":
        return _acquire_diameter_classes(stand, adapter_kwargs)
    origin = "angle_count_aggregate" if stand.use_angle_count else "aggregate"
    return {"metrics": _aggregate_metrics(stand)}, "aggregate", origin, None


def _aggregate_metrics(stand: Stand) -> Dict[str, Any]:
    """Read a stand's aggregate basal area and stem density.

    Prefers the stand's own plot-mean estimates and only derives a total from the
    metric accessors when no estimate is stored. Reading them eagerly is what a
    ``dict.get(name, {"TOTAL": Stems(float(stand.Stems))})`` default used to do,
    which turned "this stand has no stem estimate" into a bare ``KeyError`` raised
    from inside a default argument -- an angle-count stand whose tallies carry no
    diameters cannot report stems/ha at all, and deserves to be told so.

    Args:
        stand: The stand to read.

    Returns:
        A metrics mapping suitable for :class:`SimulationContext` in aggregate mode.

    Raises:
        ValueError: If the stand cannot supply one of the required metrics.
    """
    estimates = stand.metric_estimates()
    out: Dict[str, Any] = {}
    for name, wrapper in (("BasalArea", StandBasalArea), ("Stems", Stems)):
        stored = estimates.get(name)
        if stored:
            out[name] = stored
            continue
        try:
            total = float(getattr(stand, name))
        except Exception as exc:
            raise ValueError(
                f"Cannot build an aggregate simulation context: this stand does not "
                f"supply {name}. Angle-count tallies yield stems/ha only when the "
                f"tallied trees' diameters were recorded (AngleCount(diameters_cm=...)); "
                f"without them only BasalArea is available. Use GrowthModel.can_build() "
                f"to check before building."
            ) from exc
        out[name] = {"TOTAL": wrapper(total, species=None)}
    return out


@dataclass(frozen=True)
class Requirements:
    """Declares model prerequisites and preferred/required inventory mode.

    ``native_step_years`` is the period the model's functions were fitted for.
    Declaring it is how a caller learns a model's step length without triggering
    its exception: Bollandsås raises unless ``dt`` is a whole multiple of 5, Ekö
    steps 5, Elfving scales linearly from 5 with a warning. ``None`` means the
    model is genuinely step-agnostic, not that nobody filled it in -- a model
    with a native period should say so.
    """

    inventory: InventoryMode = "either"
    require_site: bool = False
    require_top_height: bool = False
    native_step_years: Optional[float] = None


class GrowthModel(ABC):
    """Abstract base for growth models with a factory interface.

    :meth:`requirements` and :meth:`update_step` are abstract, so a model that
    forgets one fails at instantiation rather than partway through a projection.

    :attr:`source` is *not* given a default. It used to return
    ``SourceReference(author="unknown", year=0, title="unknown")``, which meant a
    model that forgot its provenance produced a citation-shaped object that read
    like a real one in a catalog listing and a provenance report -- in a package
    whose stated value is traceability. Not overriding it now raises, and says
    what to write.
    """

    # ----------------------------- Introspection ------------------------------

    @property
    def component_id(self) -> str:
        """Stable identifier for this model. Override in subclasses."""
        return type(self).__name__

    @property
    def source(self) -> SourceReference:
        """Bibliographic provenance for the published model this implements.

        Raises:
            NotImplementedError: Always; every model must cite its own source.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not declare a source. Every model must "
            f"cite the publication it implements:\n\n"
            f"    @property\n"
            f"    def source(self) -> SourceReference:\n"
            f"        return SourceReference(author=..., year=..., title=...)\n\n"
            f"This used to default to a placeholder that read like a real "
            f"citation wherever provenance was reported."
        )

    # ----------------------------- Factory ------------------------------------

    @abstractmethod
    def requirements(self) -> Requirements:
        """Declare the inventory and site data this model needs.

        Returns:
            The model's prerequisites. The declared ``inventory`` is authoritative:
            :meth:`build_context` builds that representation rather than guessing
            from what the stand happens to carry.
        """
        raise NotImplementedError

    def can_build(
        self,
        stand: Stand,
        *,
        allow_adapters: bool = True,
        mode_hint: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """Check whether ``stand`` can supply what this model needs.

        Args:
            stand: The inventory to test.
            allow_adapters: Whether angle-count tallies may be converted to the
                required representation. ``False`` tests the stand as it stands.
            mode_hint: Test against this mode instead of the declared requirement.

        Returns:
            ``(ok, missing)``, where ``missing`` names each prerequisite the stand
            cannot meet -- ``"site"``, ``"top_height"``, or a description of the
            inventory representation it lacks. Call this before
            :meth:`build_context` to get a list rather than an exception. The mode
            it tests is the one :meth:`build_context` would choose, because both
            ask :func:`_select_mode`.
        """
        req = self.requirements()
        missing: List[str] = []

        if req.require_site and stand.site is None:
            missing.append("site")
        if req.require_top_height and stand.get_dominant_height() is None:
            missing.append("top_height")

        mode = _select_mode(req, stand, mode_hint)
        adaptable = allow_adapters and stand.use_angle_count

        if mode == "spatial":
            if not (
                _has_positions(stand) or adaptable or (allow_adapters and _has_tree_list(stand))
            ):
                missing.append("spatial (positions required or adapter)")
        elif mode == "tree_list":
            if not (_has_tree_list(stand) or adaptable):
                missing.append("tree_list")
        elif mode == "diameter_class":
            if not (_has_tree_list(stand) or _has_aggregates(stand) or adaptable):
                missing.append("diameter_class (needs tree list or aggregates)")
        elif not _has_aggregates(stand):  # aggregate
            missing.append("aggregates (BasalArea/Stems)")

        return (len(missing) == 0, missing)

    def build_context(
        self,
        stand: Stand,
        *,
        mode_hint: Optional[str] = None,
        use_adapter: Optional[str] = None,
        adapter_kwargs: Optional[Dict[str, Any]] = None,
        attrs: Optional[Dict[str, Any]] = None,
        inputs: Optional[Any] = None,
        seed: Optional[int] = None,
        random_bundle: Optional[Any] = None,
    ) -> SimulationContext:
        """Build the working context this model will step.

        The inventory mode comes from :meth:`requirements`: a model that declares
        a concrete ``inventory`` gets that mode, because running it on a
        representation it was not written for is a silent error rather than a
        graceful degradation. ``mode_hint`` is the caller's override for the
        ``"either"`` case, and subclasses should *not* pass it from an overridden
        ``build_context`` -- declare the mode in ``requirements()`` instead.

        Args:
            stand: The inventory to build from. Not mutated; the context works on
                its own plot containers.
            mode_hint: Override the inventory mode. Only meaningful for models
                whose requirements say ``"either"``.
            use_adapter: Name of a specific registered adapter to convert
                angle-count tallies with, instead of the preferred-order default.
            adapter_kwargs: Extra keyword arguments forwarded to the adapter.
            attrs: Site and history values the stand does not carry typed, merged
                over :meth:`default_attrs`. Pass them here rather than writing them
                onto ``ctx.attrs`` afterwards: :meth:`resolve_inputs` runs during
                this call, so anything set later is too late to be resolved or
                checked.
            inputs: An already-built :attr:`Inputs` instance. Supplying it skips
                resolution entirely, which is what a caller that constructed the
                stand and knows its site should do -- the values are then typed at
                the call site instead of round-tripping through a string-keyed
                dict.
            seed: Root seed for the run's random streams. Every stochastic kernel
                draws from a stream keyed off this one, so the whole run is
                reproducible from this single number. A run that draws without a
                seed raises rather than quietly using an unseeded generator.
            random_bundle: An existing bundle to use instead of building one from
                ``seed``. Mutually exclusive with it.

        Returns:
            A :class:`SimulationContext` holding a working copy of the inventory,
            the model's initial state, the model's resolved ``inputs``, and an
            ``inventory_origin`` attribute recording how the representation was
            obtained.

        Raises:
            ValueError: If ``use_adapter`` names an adapter that cannot adapt
                ``stand``, or if a required model input cannot be resolved.
        """
        req = self.requirements()
        adapter_kwargs = adapter_kwargs or {}

        # A model that declares a concrete inventory mode gets it: silently
        # downgrading an angle-count stand to "aggregate" would hand a tree-list
        # model a representation it cannot step. ``mode_hint`` is the only knob
        # for a model that accepts "either", so warn when it is ignored.
        if req.inventory != "either" and mode_hint is not None and mode_hint != req.inventory:
            warnings.warn(
                f"{type(self).__name__} requires inventory mode {req.inventory!r}; "
                f"ignoring mode_hint={mode_hint!r}.",
                stacklevel=2,
            )
        mode = _select_mode(req, stand, mode_hint)

        acquired = _acquire_inventory(stand, mode, use_adapter, adapter_kwargs)
        inventory, mode, origin, adapter_used = acquired

        state = self.init_state_stub()
        context_attrs = self.default_attrs()
        if attrs:
            context_attrs.update(attrs)

        # Provenance: what the inventory in this context actually came from. Only
        # record an adapter when one really ran -- claiming a measured tree list was
        # reconstructed from angle-count tallies is worse than saying nothing.
        context_attrs["inventory_origin"] = origin
        if adapter_used is not None:
            context_attrs["inventory_adapter"] = adapter_used

        if seed is not None and random_bundle is not None:
            raise ValueError(
                "Pass either seed= or random_bundle=, not both: a bundle already "
                "carries its root seed, so supplying a second one has no defined "
                "meaning."
            )
        if random_bundle is None and seed is not None:
            from pyforestry.simulation.services import RandomBundle

            random_bundle = RandomBundle(int(seed))

        ctx = SimulationContext(
            mode=mode,
            area_ha=stand.area_ha,
            site=stand.site,
            origin_ref=stand,
            inventory=inventory,
            initial_state=state,
            model=self,
            initial_attrs=context_attrs,
            random_bundle=random_bundle,
        )
        ctx.inputs = inputs if inputs is not None else self._resolve_inputs_or_explain(ctx)
        return ctx

    # ------------------------------- Inputs -----------------------------------

    #: The frozen dataclass this model resolves its run inputs into, or ``None``
    #: for a model that reads ``ctx.attrs`` directly. Declaring it is what lets a
    #: caller ask "which models can I run on the data I have?" without running one.
    Inputs: ClassVar[Optional[type]] = None

    def resolve_inputs(self, ctx: SimulationContext) -> Optional[Any]:
        """Resolve this model's run inputs, once, while the context is being built.

        Return an instance of :attr:`Inputs` -- the site and plot facts that hold
        for the whole run, read out of the stand's typed :class:`Site` where it
        has them and out of ``ctx.attrs`` where it does not. Raise for anything
        required and absent.

        The point is *where* it raises. Reading inputs with ``attrs.get(key,
        default)`` at the moment a kernel needs them means a missing input either
        surfaces twenty frames into a step or, worse, silently becomes its
        default; and a mistyped key is indistinguishable from an absent one. Doing
        it here turns both into a named error at ``build_context``, before any
        time has been simulated.

        Values that a step can *change* -- whether a thinning has been simulated,
        how many fertilised years remain -- are run state and do not belong here.
        Freeze those and the model stops responding to its own management.

        Returns:
            The resolved inputs, or ``None`` if this model declares none.
        """
        return None

    def _resolve_inputs_or_explain(self, ctx: SimulationContext) -> Optional[Any]:
        """Call :meth:`resolve_inputs`, naming the model if it cannot."""
        try:
            return self.resolve_inputs(ctx)
        except (KeyError, TypeError, ValueError) as exc:
            raise type(exc)(
                f"{type(self).__name__} cannot resolve its inputs from this stand: {exc}"
            ) from exc

    # ------------------------------ Behavior ----------------------------------

    def default_attrs(self) -> Dict[str, Any]:
        """Model-specific values seeded into ``ctx.attrs`` when a context is built.

        Returns:
            Initial attributes. Empty by default; override to declare the site and
            history inputs your ``update_step`` reads.
        """
        return {}

    def init_state_stub(self) -> Dict[str, Any]:
        """Initial run state seeded into ``ctx.state``.

        Returns:
            ``t`` (elapsed years) and ``years_since_thin``, which the runtime and
            the thinning-response terms of several models both read.
        """
        return {"t": 0.0, "years_since_thin": 0.0}

    @abstractmethod
    def update_step(self, ctx: SimulationContext, dt: float) -> None:
        """Advance ``ctx`` by ``dt`` years. This is the model.

        Write results into the representation ``ctx`` holds -- its plots, its
        diameter classes, or its aggregate metrics -- because the context rebuilds
        its metrics from that representation after every step.

        Args:
            ctx: The working copy to advance, in the mode this model requires.
            dt: Length of the step in years.
        """
        raise NotImplementedError

    def available_actions(self) -> Dict[str, ActionSpec]:
        """Management actions this model exposes to :meth:`SimulationContext.do`.

        Returns:
            Action specs by name. Empty by default; a model that supports thinning
            or fertilisation declares it here, along with the inventory modes each
            action needs.
        """
        return {}


# ------------------------ Example reference model -----------------------------


class ExampleStandGeneralModel(GrowthModel):
    """A minimal working :class:`GrowthModel`, for tests and as a template.

    Not a scientific model: growth is a fixed relative rate and mortality a fixed
    annual fraction. It exists to show the shape of an implementation -- declaring
    requirements, stepping each inventory mode, exposing actions with mode gates --
    and to give the runtime something to exercise.
    """

    def __init__(
        self,
        ba_rel_per_year: float = 0.03,
        mortality_rate_per_year: float = 0.005,
        diam_cm_inc_per_year: float = 0.20,
        fertilization_boost: float = 0.01,
        fertilization_years: float = 5.0,
    ) -> None:
        """Configure the illustrative growth and mortality rates.

        Args:
            ba_rel_per_year: Relative basal-area increment per year, aggregate mode.
            mortality_rate_per_year: Fraction of stems lost per year.
            diam_cm_inc_per_year: Diameter increment per year, per-tree and
                diameter-class modes.
            fertilization_boost: Extra relative BA growth while fertilised.
            fertilization_years: Default duration of the fertilisation effect.
        """
        self.ba_rel = ba_rel_per_year
        self.mort = mortality_rate_per_year
        self.diam_inc = diam_cm_inc_per_year
        self.fert_boost = fertilization_boost
        self.fert_years = fertilization_years

    def requirements(self) -> Requirements:
        """Accept any representation; this model can step all four."""
        return Requirements(inventory="either")

    def default_attrs(self) -> Dict[str, Any]:
        """Seed the fertilisation countdown that :meth:`update_step` decrements."""
        return {"fertilized_remaining_years": 0.0}

    def update_step(self, ctx: SimulationContext, dt: float) -> None:
        """Grow, and kill, at fixed rates in whichever mode ``ctx`` holds.

        Args:
            ctx: The working copy to advance.
            dt: Length of the step in years.
        """
        ctx.state["years_since_thin"] = ctx.state.get("years_since_thin", 0.0) + dt
        fert_extra = (
            self.fert_boost if ctx.attrs.get("fertilized_remaining_years", 0.0) > 0.0 else 0.0
        )
        if ctx.attrs.get("fertilized_remaining_years", 0.0) > 0.0:
            ctx.attrs["fertilized_remaining_years"] = max(
                0.0, ctx.attrs["fertilized_remaining_years"] - dt
            )

        if ctx.mode == "aggregate":
            ba = float(ctx.metrics["BasalArea"]["TOTAL"])
            n = float(ctx.metrics["Stems"]["TOTAL"])
            new_ba = ba * (1.0 + (self.ba_rel + fert_extra) * dt)
            new_n = n * (1.0 - self.mort * dt)
            ctx.set_aggregate_metrics(ba_total=new_ba, stems_total=new_n)
        elif ctx.mode in ("tree_list", "spatial"):
            for p in ctx.plots:
                for t in p.trees:
                    if t.diameter_cm is not None:
                        t.diameter_cm = float(t.diameter_cm) + self.diam_inc * dt
                    if t.weight_n is not None:
                        t.weight_n = float(t.weight_n) * (1.0 - self.mort * dt)
        else:  # diameter_class
            dclass = ctx.diameter_classes
            for _, rec in dclass.items():
                rec["bin_mids_cm"] = [float(m) + self.diam_inc * dt for m in rec["bin_mids_cm"]]
                rec["n_per_ha"] = [float(n_i) * (1.0 - self.mort * dt) for n_i in rec["n_per_ha"]]
            ctx.set_diameter_class(dclass)

    def available_actions(self) -> Dict[str, ActionSpec]:
        """Fertilisation, mortality and two thinnings, each gated on the modes it needs."""
        return {
            "fertilize": ActionSpec(
                name="fertilize",
                description="Apply fertilization; boosts BA relative growth temporarily.",
                fn=self._act_fertilize,
                params={"years": "float"},
                requires_modes=[],
            ),
            "apply_mortality_rate": ActionSpec(
                name="apply_mortality_rate",
                description="Aggregate-safe downscale of stems (and BA).",
                fn=self._act_apply_mortality_rate,
                params={"rate": "float in [0,1]"},
                requires_modes=[],
            ),
            "thin_fraction": ActionSpec(
                name="thin_fraction",
                description="Remove the smallest-diameter fraction of stems (per-tree).",
                fn=self._act_thin_fraction,
                params={"fraction": "float in (0,1)"},
                requires_modes=["tree_list", "spatial"],
            ),
            "thin_smallest_classes": ActionSpec(
                name="thin_smallest_classes",
                description="Remove a fraction of stems starting from smallest diameter classes.",
                fn=self._act_thin_smallest_classes,
                params={"fraction": "float in (0,1)"},
                requires_modes=["diameter_class"],
            ),
        }

    def _act_fertilize(self, ctx: SimulationContext, years: Optional[float] = None) -> None:
        """Start (or restart) the fertilisation effect for ``years``."""
        ctx.attrs["fertilized_remaining_years"] = float(
            years if years is not None else self.fert_years
        )

    def _act_apply_mortality_rate(self, ctx: SimulationContext, rate: float) -> None:
        """Remove ``rate`` of the stems, in whichever mode ``ctx`` holds."""
        if rate < 0 or rate > 1:
            raise ValueError("rate must be in [0,1]")
        if ctx.mode == "aggregate":
            ctx.scale_stems(1.0 - rate)
        elif ctx.mode in ("tree_list", "spatial"):
            for p in ctx.plots:
                for t in p.trees:
                    w_raw = t.weight_n  # type: float | None
                    if w_raw is None:
                        base_w = 1.0
                    else:
                        base_w = float(w_raw)
                    t.weight_n = base_w * (1.0 - rate)
        elif ctx.mode == "diameter_class":
            dclass = ctx.diameter_classes
            for _, rec in dclass.items():
                rec["n_per_ha"] = [float(n_i) * (1.0 - rate) for n_i in rec["n_per_ha"]]
            ctx.set_diameter_class(dclass)
        ctx.state["years_since_thin"] = 0.0

    def _act_thin_fraction(self, ctx: SimulationContext, fraction: float) -> None:
        """Thin from below: remove ``fraction`` of stems, smallest diameters first."""
        if not (0.0 < fraction < 1.0):
            raise ValueError("fraction must be in (0,1)")
        records = []
        for p in ctx.plots:
            for t in p.trees:
                d = float(getattr(t, "diameter_cm", 0.0) or 0.0)
                w = float(getattr(t, "weight_n", 1.0) or 1.0)
                records.append((t, d, w))
        if not records:
            return
        total_stems = sum(w for (_, _, w) in records)
        target_remove = total_stems * fraction
        records.sort(key=lambda r: r[1])
        removed = 0.0
        for t, _d, w in records:
            if removed >= target_remove:
                break
            take = min(w, target_remove - removed)
            t.weight_n = w - take
            removed += take
        for p in ctx.plots:
            p.trees = [t for t in p.trees if float(getattr(t, "weight_n", 0.0) or 0.0) > 1e-9]
        ctx.state["years_since_thin"] = 0.0

    def _act_thin_smallest_classes(self, ctx: SimulationContext, fraction: float) -> None:
        """Thin from below in diameter-class mode, emptying the smallest classes first."""
        if ctx.mode != "diameter_class":
            raise RuntimeError("thin_smallest_classes requires diameter_class")
        if not (0.0 < fraction < 1.0):
            raise ValueError("fraction must be in (0,1)")
        dclass = ctx.diameter_classes
        total_n = float(ctx.metrics["Stems"]["TOTAL"])
        target = total_n * fraction
        removed = 0.0
        for _, rec in dclass.items():
            pairs = sorted(
                zip(rec["bin_mids_cm"], rec["n_per_ha"], strict=False), key=lambda x: x[0]
            )
            new_n = []
            for _, n_i in pairs:
                if removed >= target:
                    new_n.append(n_i)
                    continue
                take = min(n_i, target - removed)
                new_n.append(n_i - take)
                removed += take
            # new_n already aligned to sorted mids
            rec["n_per_ha"] = [n for n in new_n]
        ctx.set_diameter_class(dclass)
        ctx.state["years_since_thin"] = 0.0
