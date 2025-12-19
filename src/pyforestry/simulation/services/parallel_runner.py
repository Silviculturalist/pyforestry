"""Multiprocessing runner for stand simulations with checkpoint hand-off."""

from __future__ import annotations

import multiprocessing as mp
import traceback
from typing import Any, Callable, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Union

from pyforestry.base.simulation import ContextEnsemble, SimulationContext

Task = Tuple[int, Mapping[str, Any], Optional[Mapping[str, Any]]]
Result = Tuple[int, Mapping[str, Any], Optional[MutableMapping[str, Any]], Optional[List[Any]]]


def _worker_run(
    tasks: Sequence[Task],
    model: Any,
    dt: float,
    steps: int,
    include_history: bool,
    history_tail: Optional[int],
) -> List[Result]:
    """Worker: restore contexts, run update steps, return checkpoints with telemetry."""

    out: List[Result] = []
    for idx, cp, mgmt in tasks:
        telemetry_payload: Optional[List[Any]] = None
        try:
            ctx = SimulationContext.from_checkpoint(model, cp)
            for _ in range(steps):
                ctx.update_step(dt, management=mgmt)
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
    management: Optional[Sequence[Optional[Mapping[str, Any]]]] = None,
    write_back: bool = True,
    include_history: bool = False,
    history_tail: Optional[int] = None,
    dispatcher: Optional[Callable[[int, SimulationContext], int]] = None,
    max_processes: int = 8,
    telemetry_sink: Optional[Callable[[int, List[Any]], None]] = None,
) -> List[SimulationContext]:
    """
    Execute ``steps`` of ``dt`` across contexts in parallel using checkpoints.

    ``target`` can be a :class:`ContextEnsemble` or a sequence of contexts. If
    ``write_back`` is True, the supplied ensemble's contexts are replaced with the
    updated instances; otherwise updated contexts are returned without mutation.

    Extra controls:
      • ``management``: per-context management payloads forwarded to update_step.
      • ``include_history``/``history_tail``: include recent history entries in checkpoints.
      • ``dispatcher``: function mapping context index -> worker index for custom sharding.
      • ``telemetry_sink``: optional callback receiving (index, telemetry events) per context.
      • ``max_processes``: safety cap on worker count (default 8).
    """

    if isinstance(target, ContextEnsemble):
        ensemble = target
        contexts = list(ensemble.contexts)
    else:
        ensemble = None
        contexts = list(target)

    # When given a plain sequence of contexts, fall back to non-mutating mode.
    if write_back and ensemble is None:
        write_back = False

    if not contexts:
        return []
    model_obj = getattr(contexts[0], "model", None)
    if model_obj is None:
        raise ValueError("Contexts must carry a 'model' attribute for parallel execution.")

    if management is None:
        mgmt = [None] * len(contexts)
    else:
        mgmt = list(management)
        if len(mgmt) != len(contexts):  # pragma: no cover - defensive
            raise ValueError("management list must match number of contexts.")

    # Determine process count with a conservative cap
    procs = max(1, min(processes or mp.cpu_count(), len(contexts), max_processes))

    # Build indexed tasks (index preserved for deterministic reordering)
    tasks: List[Task] = []
    for idx, (ctx, mg) in enumerate(zip(contexts, mgmt, strict=False)):
        tasks.append(
            (idx, ctx.checkpoint(include_history=include_history, history_tail=history_tail), mg)
        )

    # Optional dispatcher to control worker placement
    if dispatcher is not None:
        buckets: List[List[Task]] = [[] for _ in range(procs)]
        for idx, task in enumerate(tasks):
            worker_idx = dispatcher(idx, contexts[idx])
            worker_idx = int(worker_idx) % procs
            buckets[worker_idx].append(task)
        chunks = [b for b in buckets if b]
    else:
        chunks: List[List[Task]] = [[] for _ in range(procs)]
        for i, task in enumerate(tasks):
            chunks[i % procs].append(task)
        chunks = [c for c in chunks if c]

    results: List[Result] = []

    if len(chunks) == 1:
        # Avoid multiprocessing/pickling overhead when only one worker is needed.
        results.extend(
            _worker_run(
                chunks[0],
                model_obj,
                dt,
                steps,
                include_history,
                history_tail,
            )
        )
    else:
        with mp.Pool(processes=len(chunks)) as pool:
            for sub in pool.starmap(
                _worker_run,
                [(chunk, model_obj, dt, steps, include_history, history_tail) for chunk in chunks],
            ):
                results.extend(sub)

    # Handle errors and rebuild contexts ordered by original index
    errors = [r for r in results if r[2] is not None]
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
    restored: List[SimulationContext] = [ctx for (_idx, ctx) in restored_pairs]

    if write_back and ensemble is not None:
        ensemble.contexts = restored

    return restored


__all__ = ["run_parallel"]
