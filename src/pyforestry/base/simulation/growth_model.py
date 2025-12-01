# pyforestry/base/simulation/growth_model.py
from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple

from pyforestry.base.helpers import Stand
from pyforestry.base.helpers.primitives import StandBasalArea, Stems

from .core import ActionSpec, SimulationContext

InventoryMode = Literal["spatial", "tree_list", "diameter_class", "aggregate", "either"]


@dataclass(frozen=True)
class Requirements:
    """Declares model prerequisites and preferred/required inventory mode."""

    inventory: InventoryMode = "either"
    require_site: bool = False
    require_top_height: bool = False


class GrowthModel:
    """Abstract base for growth models with a factory interface."""

    # ----------------------------- Factory ------------------------------------

    def requirements(self) -> Requirements:
        raise NotImplementedError

    def can_build(
        self,
        stand: Stand,
        *,
        allow_adapters: bool = True,
        mode_hint: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        req = self.requirements()
        missing: List[str] = []

        if req.require_site and stand.site is None:
            missing.append("site")
        if req.require_top_height and stand.get_dominant_height() is None:
            missing.append("top_height")

        def _has_tree_list() -> bool:
            return (not stand.use_angle_count) and any(p.trees for p in stand.plots)

        def _has_positions() -> bool:
            if not _has_tree_list():
                return False
            for p in stand.plots:
                for t in p.trees:
                    if getattr(t, "position", None) is None:
                        return False
            return True

        def _has_aggregates() -> bool:
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
        req = self.requirements()
        adapter_kwargs = adapter_kwargs or {}
        inventory: Dict[str, Any] = {}
        # Choose mode
        if mode_hint is not None:
            mode = mode_hint
        elif stand.use_angle_count:
            # Default safety for Angle-Count: aggregate unless caller opts in.
            mode = "aggregate"
        else:
            if req.inventory in ("spatial", "tree_list", "diameter_class", "aggregate"):
                mode = req.inventory
            else:
                has_trees = any(p.trees for p in stand.plots)
                mode = "tree_list" if has_trees else "aggregate"

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
                            break
                if plots_payload is None:
                    # Fallback to aggregate metrics when adapter cannot produce plots
                    metrics = {
                        "BasalArea": getattr(stand, "_metric_estimates", {}).get(
                            "BasalArea",
                            {"TOTAL": StandBasalArea(float(stand.BasalArea), species=None)},
                        ),
                        "Stems": getattr(stand, "_metric_estimates", {}).get(
                            "Stems",
                            {"TOTAL": Stems(float(stand.Stems), species=None)},
                        ),
                    }
                    inventory = {"metrics": metrics}
                    mode = "aggregate"
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
                    else:
                        mode = "tree_list"

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
            else:
                adp = reg.get("angle_count_to_diameter_class")
                if adp and adp.can_adapt(stand):
                    dclass_payload = adp.adapt(stand, **adapter_kwargs)["dclass"]
            if dclass_payload is None:
                ba = float(stand.BasalArea)
                n = float(stand.Stems)
                qmd = float(stand.QMD) if n > 0 and ba > 0 else 0.0
                dclass_payload = {
                    "TOTAL": {
                        "bin_mids_cm": [qmd] if qmd > 0 else [],
                        "n_per_ha": [n] if qmd > 0 else [],
                    }
                }
            inventory = {"dclass": dclass_payload}

        else:  # aggregate
            metrics = {
                "BasalArea": getattr(stand, "_metric_estimates", {}).get(
                    "BasalArea", {"TOTAL": StandBasalArea(float(stand.BasalArea), species=None)}
                ),
                "Stems": getattr(stand, "_metric_estimates", {}).get(
                    "Stems", {"TOTAL": Stems(float(stand.Stems), species=None)}
                ),
            }
            inventory = {"metrics": metrics}

        state = self.init_state_stub()
        attrs = self.default_attrs()

        # Provenance
        if stand.use_angle_count and mode in ("tree_list", "spatial"):
            attrs["inventory_origin"] = (
                "angle_count_pseudo_tree_list"
                if mode == "tree_list"
                else "angle_count_spatial_pseudo_tree_list"
            )
            if mode == "tree_list":
                attrs["inventory_origin"] = "angle_count_pseudo_tree_list"
        else:
            attrs["inventory_origin"] = "angle_count_spatial_pseudo_tree_list"
            attrs["angle_count_adapter"] = use_adapter or "auto"
        if mode == "diameter_class":
            attrs.setdefault("inventory_origin", "diameter_class_built")

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
        return {}

    def init_state_stub(self) -> Dict[str, Any]:
        return {"t": 0.0, "years_since_thin": 0.0}

    def update_step(self, ctx: SimulationContext, dt: float) -> None:
        raise NotImplementedError

    def grow(self, ctx: SimulationContext, dt: float) -> None:  # pragma: no cover - compatibility
        warnings.warn(
            "GrowthModel.grow is deprecated; implement/update_step instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.update_step(ctx, dt)

    def available_actions(self) -> Dict[str, ActionSpec]:
        return {}


# ------------------------ Example reference model -----------------------------


class ExampleStandGeneralModel(GrowthModel):
    def __init__(
        self,
        ba_rel_per_year: float = 0.03,
        mortality_rate_per_year: float = 0.005,
        diam_cm_inc_per_year: float = 0.20,
        fertilization_boost: float = 0.01,
        fertilization_years: float = 5.0,
    ) -> None:
        self.ba_rel = ba_rel_per_year
        self.mort = mortality_rate_per_year
        self.diam_inc = diam_cm_inc_per_year
        self.fert_boost = fertilization_boost
        self.fert_years = fertilization_years

    def requirements(self) -> Requirements:
        return Requirements(inventory="either")

    def default_attrs(self) -> Dict[str, Any]:
        return {"fertilized_remaining_years": 0.0}

    def update_step(self, ctx: SimulationContext, dt: float) -> None:
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
        warnings.warn(
            "ExampleStandGeneralModel.grow is deprecated; use update_step instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.update_step(ctx, dt)

    def available_actions(self) -> Dict[str, ActionSpec]:
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
        ctx.attrs["fertilized_remaining_years"] = float(
            years if years is not None else self.fert_years
        )

    def _act_apply_mortality_rate(self, ctx: SimulationContext, rate: float) -> None:
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
