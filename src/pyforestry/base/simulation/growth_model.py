"""Growth Model utilities and interfaces.

Source: Internal pyforestry simulation architecture and runtime contracts.
"""

# pyforestry/base/simulation/growth_model.py
from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple

from pyforestry.base.contracts import SourceReference
from pyforestry.base.helpers import Stand
from pyforestry.base.helpers.primitives import StandBasalArea, Stems

from .core import ActionSpec, SimulationContext

InventoryMode = Literal["spatial", "tree_list", "diameter_class", "aggregate", "either"]


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
    estimates = getattr(stand, "_metric_estimates", {})
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
    """Declares model prerequisites and preferred/required inventory mode."""

    inventory: InventoryMode = "either"
    require_site: bool = False
    require_top_height: bool = False


class GrowthModel:
    """Abstract base for growth models with a factory interface.

    Subclasses should override ``component_id`` and ``source`` to satisfy
    the ``Describable`` protocol for provenance and catalog support.
    """

    # ----------------------------- Introspection ------------------------------

    @property
    def component_id(self) -> str:
        """Stable identifier for this model. Override in subclasses."""
        return type(self).__name__

    @property
    def source(self) -> SourceReference:
        """Bibliographic provenance. Override in subclasses."""
        return SourceReference(author="unknown", year=0, title="unknown")

    # ----------------------------- Factory ------------------------------------

    def requirements(self) -> Requirements:
        """Requirements.

        Returns:
            Result produced by this callable.

        Source:
            Internal pyforestry simulation architecture and runtime contracts.
        """
        raise NotImplementedError

    def can_build(
        self,
        stand: Stand,
        *,
        allow_adapters: bool = True,
        mode_hint: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """Can build.

        Args:
            stand: Parameter for `GrowthModel.can_build`.
            allow_adapters: Parameter for `GrowthModel.can_build`.
            mode_hint: Parameter for `GrowthModel.can_build`.

        Returns:
            Result produced by this callable.

        Source:
            Internal pyforestry simulation architecture and runtime contracts.
        """
        req = self.requirements()
        missing: List[str] = []

        if req.require_site and stand.site is None:
            missing.append("site")
        if req.require_top_height and stand.get_dominant_height() is None:
            missing.append("top_height")

        def _has_tree_list() -> bool:
            """Check whether the stand has explicit tree-list inventory.

            Returns:
                ``True`` when plots contain trees and the stand is not angle-count based.

            Source:
                Internal pyforestry simulation architecture and runtime contracts.
            """
            return (not stand.use_angle_count) and any(p.trees for p in stand.plots)

        def _has_positions() -> bool:
            """Check whether all trees in the stand have spatial positions.

            Returns:
                ``True`` when every tree has a non-null ``position`` value.

            Source:
                Internal pyforestry simulation architecture and runtime contracts.
            """
            if not _has_tree_list():
                return False
            for p in stand.plots:
                for t in p.trees:
                    if getattr(t, "position", None) is None:
                        return False
            return True

        def _has_aggregates() -> bool:
            """Check whether aggregate metrics can be read from the stand.

            Returns:
                ``True`` when basal area and stem count can be converted to floats.

            Source:
                Internal pyforestry simulation architecture and runtime contracts.
            """
            try:
                _ = float(stand.BasalArea)
                _ = float(stand.Stems)
                return True
            except Exception:
                return False

        desired = mode_hint or req.inventory
        if desired == "spatial":
            if _has_positions():
                pass
            elif allow_adapters and (_has_tree_list() or stand.use_angle_count):
                pass
            else:
                missing.append("spatial (positions required or adapter)")
        elif desired == "tree_list":
            if _has_tree_list():
                pass
            elif allow_adapters and stand.use_angle_count:
                pass
            else:
                missing.append("tree_list")
        elif desired == "diameter_class":
            if _has_tree_list() or _has_aggregates() or (allow_adapters and stand.use_angle_count):
                pass
            else:
                missing.append("diameter_class (needs tree list or aggregates)")
        elif desired == "aggregate":
            if not _has_aggregates():
                missing.append("aggregates (BasalArea/Stems)")
        else:  # 'either'
            if not (
                _has_tree_list() or _has_aggregates() or (allow_adapters and stand.use_angle_count)
            ):
                missing.append("tree_list or aggregates (or adapter)")

        return (len(missing) == 0, missing)

    def build_context(
        self,
        stand: Stand,
        *,
        mode_hint: Optional[str] = None,
        use_adapter: Optional[str] = None,
        adapter_kwargs: Optional[Dict[str, Any]] = None,
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

        Returns:
            A :class:`SimulationContext` holding a working copy of the inventory,
            the model's initial state, and an ``inventory_origin`` attribute
            recording how the representation was obtained.

        Raises:
            ValueError: If ``use_adapter`` names an adapter that cannot adapt
                ``stand``.
        """
        req = self.requirements()
        adapter_kwargs = adapter_kwargs or {}
        inventory: Dict[str, Any] = {}
        # Mode selection. A model that declares a concrete inventory mode gets it:
        # silently downgrading an angle-count stand to "aggregate" would hand a
        # tree-list model a representation it cannot step. ``mode_hint`` overrides,
        # and is the only knob for a model that accepts "either".
        if req.inventory in ("spatial", "tree_list", "diameter_class", "aggregate"):
            mode = req.inventory
            if mode_hint is not None and mode_hint != mode:
                warnings.warn(
                    f"{type(self).__name__} requires inventory mode {mode!r}; "
                    f"ignoring mode_hint={mode_hint!r}.",
                    stacklevel=2,
                )
        elif mode_hint is not None:
            mode = mode_hint
        elif stand.use_angle_count:
            # Angle-count tallies carry no stems unless diameters were recorded,
            # so aggregate is the safe default for a model that accepts either.
            mode = "aggregate"
        else:
            has_trees = any(p.trees for p in stand.plots)
            mode = "tree_list" if has_trees else "aggregate"

        # How the inventory was actually obtained, recorded as it is built rather
        # than reconstructed afterwards.
        origin = mode
        adapter_used: Optional[str] = None

        # Build inventory by mode
        if mode in ("tree_list", "spatial"):
            plots_payload = None
            if stand.use_angle_count:
                # AC → pseudo tree list or spatial pseudo tree list
                from .adapters import AdapterRegistry

                reg = AdapterRegistry.default()
                if use_adapter:
                    adp = reg.get(use_adapter)
                    if adp is None or not adp.can_adapt(stand):
                        raise ValueError(f"Adapter '{use_adapter}' cannot adapt this stand.")
                    plots_payload = adp.adapt(stand, **adapter_kwargs)["plots"]
                    adapter_used = use_adapter
                else:
                    if mode == "spatial":
                        preferred = [
                            "angle_count_spatial_pseudo_tree_list",
                            "angle_count_pseudo_tree_list",
                        ]
                    else:
                        preferred = [
                            "angle_count_pseudo_tree_list",
                            "angle_count_spatial_pseudo_tree_list",
                        ]
                    for name in preferred:
                        adp = reg.get(name)
                        if adp and adp.can_adapt(stand):
                            plots_payload = adp.adapt(stand, **adapter_kwargs)["plots"]
                            adapter_used = name
                            break
                origin = adapter_used or origin
                if plots_payload is None:
                    # No adapter could turn the tallies into stems, so fall back to
                    # the aggregate metrics the tallies do support.
                    inventory = {"metrics": _aggregate_metrics(stand)}
                    mode = "aggregate"
                    origin = "angle_count_aggregate"
            elif mode == "spatial":
                # Ensure positions or use adapter to fill
                have_all_pos = all(
                    getattr(t, "position", None) is not None for p in stand.plots for t in p.trees
                )
                if not have_all_pos:
                    from .adapters import AdapterRegistry

                    adp = AdapterRegistry.default().get("tree_list_to_spatial")
                    if adp and adp.can_adapt(stand):
                        plots_payload = adp.adapt(stand, **adapter_kwargs)["plots"]
                        adapter_used = "tree_list_to_spatial"
                        origin = adapter_used
                    else:
                        mode = "tree_list"
                        origin = "tree_list"

            if mode in ("tree_list", "spatial"):
                inventory = {"plots": plots_payload if plots_payload is not None else stand.plots}

        elif mode == "diameter_class":
            from .adapters import AdapterRegistry

            reg = AdapterRegistry.default()
            dclass_payload = None
            if not stand.use_angle_count and any(p.trees for p in stand.plots):
                adp = reg.get("tree_list_to_diameter_class")
                if adp:
                    dclass_payload = adp.adapt(stand, **adapter_kwargs)["dclass"]
                    adapter_used = "tree_list_to_diameter_class"
            else:
                adp = reg.get("angle_count_to_diameter_class")
                if adp and adp.can_adapt(stand):
                    dclass_payload = adp.adapt(stand, **adapter_kwargs)["dclass"]
                    adapter_used = "angle_count_to_diameter_class"
            if dclass_payload is None:
                # Nothing to bin, so stand in a single class at the stand's own QMD.
                ba = float(stand.BasalArea)
                n = float(stand.Stems)
                qmd = float(stand.QMD) if n > 0 and ba > 0 else 0.0
                dclass_payload = {
                    "TOTAL": {
                        "bin_mids_cm": [qmd] if qmd > 0 else [],
                        "n_per_ha": [n] if qmd > 0 else [],
                    }
                }
                origin = "diameter_class_from_qmd"
            else:
                origin = adapter_used or origin
            inventory = {"dclass": dclass_payload}

        else:  # aggregate
            inventory = {"metrics": _aggregate_metrics(stand)}
            origin = "angle_count_aggregate" if stand.use_angle_count else "aggregate"

        state = self.init_state_stub()
        attrs = self.default_attrs()

        # Provenance: what the inventory in this context actually came from. Only
        # record an adapter when one really ran -- claiming a measured tree list was
        # reconstructed from angle-count tallies is worse than saying nothing.
        attrs["inventory_origin"] = origin
        if adapter_used is not None:
            attrs["inventory_adapter"] = adapter_used

        ctx = SimulationContext(
            mode=mode,
            area_ha=stand.area_ha,
            site=stand.site,
            origin_ref=stand,
            inventory=inventory,
            initial_state=state,
            model=self,
            initial_attrs=attrs,
        )
        return ctx

    # ------------------------------ Behavior ----------------------------------

    def default_attrs(self) -> Dict[str, Any]:
        """Default attrs.

        Returns:
            Result produced by this callable.

        Source:
            Internal pyforestry simulation architecture and runtime contracts.
        """
        return {}

    def init_state_stub(self) -> Dict[str, Any]:
        """Init state stub.

        Returns:
            Result produced by this callable.

        Source:
            Internal pyforestry simulation architecture and runtime contracts.
        """
        return {"t": 0.0, "years_since_thin": 0.0}

    def update_step(self, ctx: SimulationContext, dt: float) -> None:
        """Update step.

        Args:
            ctx: Parameter for `GrowthModel.update_step`.
            dt: Parameter for `GrowthModel.update_step`.

        Returns:
            Result produced by this callable.

        Source:
            Internal pyforestry simulation architecture and runtime contracts.
        """
        raise NotImplementedError

    def grow(self, ctx: SimulationContext, dt: float) -> None:  # pragma: no cover - compatibility
        """Grow.

        Args:
            ctx: Parameter for `GrowthModel.grow`.
            dt: Parameter for `GrowthModel.grow`.

        Returns:
            Result produced by this callable.

        Source:
            Internal pyforestry simulation architecture and runtime contracts.
        """
        warnings.warn(
            "GrowthModel.grow is deprecated; implement/update_step instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.update_step(ctx, dt)

    def available_actions(self) -> Dict[str, ActionSpec]:
        """Available actions.

        Returns:
            Result produced by this callable.

        Source:
            Internal pyforestry simulation architecture and runtime contracts.
        """
        return {}


# ------------------------ Example reference model -----------------------------


class ExampleStandGeneralModel(GrowthModel):
    """Example stand general model container and behavior.

    Source:
        Internal pyforestry simulation architecture and runtime contracts.
    """

    def __init__(
        self,
        ba_rel_per_year: float = 0.03,
        mortality_rate_per_year: float = 0.005,
        diam_cm_inc_per_year: float = 0.20,
        fertilization_boost: float = 0.01,
        fertilization_years: float = 5.0,
    ) -> None:
        """Init.

        Args:
            ba_rel_per_year: Parameter for `ExampleStandGeneralModel.__init__`.
            mortality_rate_per_year: Parameter for `ExampleStandGeneralModel.__init__`.
            diam_cm_inc_per_year: Parameter for `ExampleStandGeneralModel.__init__`.
            fertilization_boost: Parameter for `ExampleStandGeneralModel.__init__`.
            fertilization_years: Parameter for `ExampleStandGeneralModel.__init__`.

        Source:
            Internal pyforestry simulation architecture and runtime contracts.
        """
        self.ba_rel = ba_rel_per_year
        self.mort = mortality_rate_per_year
        self.diam_inc = diam_cm_inc_per_year
        self.fert_boost = fertilization_boost
        self.fert_years = fertilization_years

    def requirements(self) -> Requirements:
        """Requirements.

        Returns:
            Result produced by this callable.

        Source:
            Internal pyforestry simulation architecture and runtime contracts.
        """
        return Requirements(inventory="either")

    def default_attrs(self) -> Dict[str, Any]:
        """Default attrs.

        Returns:
            Result produced by this callable.

        Source:
            Internal pyforestry simulation architecture and runtime contracts.
        """
        return {"fertilized_remaining_years": 0.0}

    def update_step(self, ctx: SimulationContext, dt: float) -> None:
        """Update step.

        Args:
            ctx: Parameter for `ExampleStandGeneralModel.update_step`.
            dt: Parameter for `ExampleStandGeneralModel.update_step`.

        Returns:
            Result produced by this callable.

        Source:
            Internal pyforestry simulation architecture and runtime contracts.
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
            dclass = ctx._dclass
            for _, rec in dclass.items():
                rec["bin_mids_cm"] = [float(m) + self.diam_inc * dt for m in rec["bin_mids_cm"]]
                rec["n_per_ha"] = [float(n_i) * (1.0 - self.mort * dt) for n_i in rec["n_per_ha"]]
            ctx.set_diameter_class(dclass)

    def grow(self, ctx: SimulationContext, dt: float) -> None:  # pragma: no cover - compatibility
        """Grow.

        Args:
            ctx: Parameter for `ExampleStandGeneralModel.grow`.
            dt: Parameter for `ExampleStandGeneralModel.grow`.

        Returns:
            Result produced by this callable.

        Source:
            Internal pyforestry simulation architecture and runtime contracts.
        """
        warnings.warn(
            "ExampleStandGeneralModel.grow is deprecated; use update_step instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.update_step(ctx, dt)

    def available_actions(self) -> Dict[str, ActionSpec]:
        """Available actions.

        Returns:
            Result produced by this callable.

        Source:
            Internal pyforestry simulation architecture and runtime contracts.
        """
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
        """Act fertilize.

        Args:
            ctx: Parameter for `ExampleStandGeneralModel._act_fertilize`.
            years: Parameter for `ExampleStandGeneralModel._act_fertilize`.

        Returns:
            Result produced by this callable.

        Source:
            Internal pyforestry simulation architecture and runtime contracts.
        """
        ctx.attrs["fertilized_remaining_years"] = float(
            years if years is not None else self.fert_years
        )

    def _act_apply_mortality_rate(self, ctx: SimulationContext, rate: float) -> None:
        """Act apply mortality rate.

        Args:
            ctx: Parameter for `ExampleStandGeneralModel._act_apply_mortality_rate`.
            rate: Parameter for `ExampleStandGeneralModel._act_apply_mortality_rate`.

        Returns:
            Result produced by this callable.

        Source:
            Internal pyforestry simulation architecture and runtime contracts.
        """
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
            dclass = ctx._dclass
            for _, rec in dclass.items():
                rec["n_per_ha"] = [float(n_i) * (1.0 - rate) for n_i in rec["n_per_ha"]]
            ctx.set_diameter_class(dclass)
        ctx.state["years_since_thin"] = 0.0

    def _act_thin_fraction(self, ctx: SimulationContext, fraction: float) -> None:
        """Act thin fraction.

        Args:
            ctx: Parameter for `ExampleStandGeneralModel._act_thin_fraction`.
            fraction: Parameter for `ExampleStandGeneralModel._act_thin_fraction`.

        Returns:
            Result produced by this callable.

        Source:
            Internal pyforestry simulation architecture and runtime contracts.
        """
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
        """Act thin smallest classes.

        Args:
            ctx: Parameter for `ExampleStandGeneralModel._act_thin_smallest_classes`.
            fraction: Parameter for `ExampleStandGeneralModel._act_thin_smallest_classes`.

        Returns:
            Result produced by this callable.

        Source:
            Internal pyforestry simulation architecture and runtime contracts.
        """
        if ctx.mode != "diameter_class":
            raise RuntimeError("thin_smallest_classes requires diameter_class")
        if not (0.0 < fraction < 1.0):
            raise ValueError("fraction must be in (0,1)")
        dclass = ctx._dclass
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
