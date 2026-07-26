"""Multiprocessing runner for stand simulations with checkpoint hand-off."""

from __future__ import annotations

import multiprocessing as mp
import traceback
from typing import Any, Callable, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Union

from pyforestry.base.simulation import ContextEnsemble, SimulationContext

Task = Tuple[int, Mapping[str, Any]]
Result = Tuple[int, Mapping[str, Any], Optional[MutableMapping[str, Any]], Optional[List[Any]]]


def _worker_run(
    tasks: Sequence[Task],
    model: Any,
    dt: float,
    steps: int,
    include_history: bool,
    history_tail: Optional[int],
) -> List[Result]:
    """Restore contexts, run update steps, and return checkpoints with telemetry."""
    out: List[Result] = []
    for idx, cp in tasks:
        telemetry_payload: Optional[List[Any]] = None
        try:
            ctx = SimulationContext.from_checkpoint(model, cp)
            for _i in range(steps):
                ctx.update_step(dt)
            tp = getattr(ctx, "telemetry", None)
            if tp is not None and hasattr(tp, "events"):
                telemetry_payload = list(tp.events)
            out.append(
                (
                    idx,
                    ctx.checkpoint(include_history=include_history, history_tail=history_tail),
                    None,
                    telemetry_payload,
                )
            )
        except Exception as exc:  # pragma: no cover - defensive
            out.append(
                (
                    idx,
                    {},
                    {
                        "error": exc.__class__.__name__,
                        "message": str(exc),
                        "traceback": traceback.format_exc(),
                    },
                    telemetry_payload,
                )
            )
    return out


def run_parallel(
    target: Union[ContextEnsemble, Sequence[SimulationContext]],
    *,
    dt: float,
    steps: int = 1,
    processes: Optional[int] = None,
    write_back: bool = True,
    include_history: bool = False,
    history_tail: Optional[int] = None,
    dispatcher: Optional[Callable[[int, SimulationContext], int]] = None,
    max_processes: int = 8,
    telemetry_sink: Optional[Callable[[int, List[Any]], None]] = None,
) -> List[SimulationContext]:
    """Execute steps of dt across contexts in parallel using checkpoints.

    Growth only. Management is a per-context policy run through
    :func:`~pyforestry.base.simulation.pipeline.run_pipeline`, and a policy is a
    live callable that cannot cross a process boundary in a checkpoint.
    """
    if isinstance(target, ContextEnsemble):
        ensemble = target
        contexts = list(ensemble.contexts)
    else:
        ensemble = None
        contexts = list(target)

    if write_back and ensemble is None:
        write_back = False
    if not contexts:
        return []

    model_obj = getattr(contexts[0], "model", None)
    if model_obj is None:
        raise ValueError("Contexts must carry a 'model' attribute for parallel execution.")

    procs = max(1, min(processes or mp.cpu_count(), len(contexts), max_processes))

    tasks: List[Task] = [
        (idx, ctx.checkpoint(include_history=include_history, history_tail=history_tail))
        for idx, ctx in enumerate(contexts)
    ]

    if dispatcher is not None:
        buckets: List[List[Task]] = [[] for _ in range(procs)]
        for idx, task in enumerate(tasks):
            worker_idx = dispatcher(idx, contexts[idx])
            worker_idx = int(worker_idx) % procs
            buckets[worker_idx].append(task)
        chunks = [b for b in buckets if b]
    else:
        chunks = [[] for _i in range(procs)]
        for i, task in enumerate(tasks):
            chunks[i % procs].append(task)
        chunks = [chunk for chunk in chunks if chunk]

    results: List[Result] = []
    if len(chunks) == 1:
        results.extend(_worker_run(chunks[0], model_obj, dt, steps, include_history, history_tail))
    else:
        try:
            with mp.Pool(processes=len(chunks)) as pool:
                for sub in pool.starmap(
                    _worker_run,
                    [
                        (chunk, model_obj, dt, steps, include_history, history_tail)
                        for chunk in chunks
                    ],
                ):
                    results.extend(sub)
        except (OSError, PermissionError):
            for chunk in chunks:
                results.extend(
                    _worker_run(chunk, model_obj, dt, steps, include_history, history_tail)
                )

    errors = [result for result in results if result[2] is not None]
    if errors:
        first = errors[0]
        message = first[2] or {}
        raise RuntimeError(f"Parallel simulation failed for context {first[0]}: {message}")

    restored_pairs: List[Tuple[int, SimulationContext]] = []
    for idx, cp, _err, telemetry in results:
        if telemetry_sink and telemetry:
            telemetry_sink(idx, telemetry)
        restored_pairs.append((idx, SimulationContext.from_checkpoint(model_obj, cp)))
    restored_pairs.sort(key=lambda pair: pair[0])
    restored = [ctx for (_idx, ctx) in restored_pairs]

    if write_back and ensemble is not None:
        ensemble.contexts = restored

    return restored


__all__ = ["run_parallel"]
