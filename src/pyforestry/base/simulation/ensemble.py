"""Batch execution utilities for running ensembles of contexts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Union

import numpy as np

from .core import SimulationContext


class BatchEngine:
    """Protocol for batch engines."""

    def grow(
        self,
        model: Any,
        vec: Dict[str, np.ndarray],
        dt: float,
        extra: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, np.ndarray]:
        """Advance a batch of aggregate metrics by ``dt``."""
        raise NotImplementedError


class PythonEngine(BatchEngine):
    """NumPy baseline."""

    def grow(
        self,
        model: Any,
        vec: Dict[str, np.ndarray],
        dt: float,
        extra: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, np.ndarray]:
        """Run the Python batch growth routine for aggregate metrics."""
        ba = vec["ba"]
        n = vec["n"]
        fert_mask = (extra or {}).get("fert_mask", np.zeros_like(ba))
        if hasattr(model, "batch_grow_step"):
            new_ba, new_n = model.batch_grow_step(ba, n, dt, fert_mask)
        else:
            new_ba, new_n = ba, n
        return {"ba": new_ba, "n": new_n}


def _optional_numba_engine() -> Optional[BatchEngine]:
    """Return a numba-capable engine if numba is available."""
    try:
        import numba  # noqa: F401
    except Exception:
        return None
    return PythonEngine()


def _optional_jax_engine() -> Optional[BatchEngine]:
    """Return a jax-capable engine if jax is available."""
    try:
        import jax  # noqa: F401
    except Exception:
        return None
    return PythonEngine()


def _engine_from_hint(hint: Optional[Union[str, BatchEngine]]) -> Optional[BatchEngine]:
    """Resolve an engine hint into a concrete batch engine."""
    if hint is None:
        return None
    if isinstance(hint, BatchEngine):
        return hint
    if isinstance(hint, str):
        key = hint.strip().lower()
        if key in ("numpy", "python"):
            return PythonEngine()
        if key == "numba":
            eng = _optional_numba_engine()
            return eng or PythonEngine()
        if key == "jax":
            eng = _optional_jax_engine()
            return eng or PythonEngine()
        raise ValueError(f"Unknown engine hint: {hint}")
    raise TypeError("engine must be None, a BatchEngine, or a backend string.")


@dataclass
class ContextEnsemble:
    """Bundle multiple contexts and advance them in batches when possible."""

    contexts: List[SimulationContext]
    model: Any
    engine: Optional[Union[BatchEngine, str]] = None

    def __post_init__(self) -> None:
        """Select a batch engine based on the hint or available backends."""
        chosen = _engine_from_hint(self.engine)
        if chosen is None:
            chosen = _optional_jax_engine() or _optional_numba_engine() or PythonEngine()
        self.engine = chosen

    def update_step(self, dt: float) -> None:
        """Advance all contexts by one step, batching aggregate contexts.

        Management is not threaded through here. An ensemble steps many contexts
        together for speed; deciding *what to do* to each is a per-context policy,
        so run a
        :func:`~pyforestry.base.simulation.pipeline.run_pipeline` per context when
        the runs need managing, and use the ensemble when they only need growing.
        """
        if self.engine is None:
            raise RuntimeError("No batch engine configured for this ensemble.")

        engine = self.engine
        if engine is None:
            raise RuntimeError("Batch engine not configured.")
        if isinstance(engine, str):  # pragma: no cover - should be resolved in __post_init__
            raise TypeError("Engine hint was not resolved to a BatchEngine.")

        agg_ctxs = [
            c
            for c in self.contexts
            if c.mode == "aggregate" and getattr(self.model, "has_batch_engine", lambda: False)()
        ]
        other_ctxs = [c for c in self.contexts if c not in agg_ctxs]
        for c in other_ctxs:
            c.update_step(dt)
        if agg_ctxs:
            ba = np.array(
                [float(c.metrics["BasalArea"]["TOTAL"]) for c in agg_ctxs],
                dtype=float,
            )
            n = np.array(
                [float(c.metrics["Stems"]["TOTAL"]) for c in agg_ctxs],
                dtype=float,
            )
            fert_mask = np.array(
                [
                    1.0 if c.attrs.get("fertilized_remaining_years", 0.0) > 0.0 else 0.0
                    for c in agg_ctxs
                ],
                dtype=float,
            )
            out = engine.grow(
                self.model,
                {"ba": ba, "n": n},
                dt,
                extra={"fert_mask": fert_mask},
            )
            for i, c in enumerate(agg_ctxs):
                c.set_aggregate_metrics(
                    ba_total=float(out["ba"][i]), stems_total=float(out["n"][i])
                )
                c.state["t"] = c.state.get("t", 0.0) + dt
                c.state["last_dt"] = dt
                c._log_external_update("update_step", {"dt": dt})

    def do(self, name: str, **kwargs: Any) -> None:
        """Execute an action on each context."""
        for c in self.contexts:
            c.do(name, **kwargs)

    def to_pandas(self):
        """Concatenate history tables from all contexts."""
        import pandas as pd

        return pd.concat(
            [c.to_pandas().assign(context_id=i) for i, c in enumerate(self.contexts)],
            ignore_index=True,
        )
