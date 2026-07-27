"""One projection, in one call.

Running a projection used to mean knowing ``Eriksson1976Model``, ``StandInit``,
``ThinningProgram``, ``build_context``, ``mode_hint``, ``SimulationSetup`` and
``Eriksson1976ManagementSchedule`` -- seven concepts, one of which raised
``TypeError`` when used the way the repository's own worked example used it.

::

    import pyforestry as pf

    result = pf.project(stand, model="elfving_2010", years=100, step=5, seed=42)

    result.table        # a DataFrame, one row per step
    result.stand        # the final state
    result.provenance   # what was cited, and by what

The typed constructors are all still there; this is the ninety-per-cent path, not
a replacement for them. ``model=`` resolves through
:mod:`pyforestry.catalog`, which is the payoff for having built a discovery layer:
the string a user finds with ``catalog.search("elfving")`` is the string they can
run.
"""

from __future__ import annotations

import copy
import importlib
import inspect
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Mapping, Optional, Sequence, Union

if TYPE_CHECKING:  # pragma: no cover - annotation only
    import pandas as pd

    from pyforestry.base.helpers.stand import Stand
    from pyforestry.base.simulation.core import SimulationContext
    from pyforestry.base.simulation.growth_model import GrowthModel
    from pyforestry.base.simulation.pipeline import Policy, Step

__all__ = ["ProjectionResult", "available_models", "available_pipelines", "project"]


@dataclass(frozen=True)
class ProjectionResult:
    """What a projection produced, and where it came from."""

    #: One row per step, including step 0. Columns follow the run's history.
    table: "pd.DataFrame"
    #: The stand as it stands at the end of the run.
    stand: "Stand"
    #: The full run context: history, state, resolved inputs, random streams.
    context: "SimulationContext"
    #: Every component that was cited, keyed by ``component_id``. A run's numbers
    #: and the papers behind them travel together rather than being reconstructed
    #: afterwards from the model you think you used.
    provenance: Mapping[str, Any] = field(default_factory=dict)

    @property
    def model(self) -> "GrowthModel":
        """The model that was stepped."""
        return self.context.model


def _growth_models_in(module_name: str) -> list[type]:
    """Return the :class:`GrowthModel` subclasses ``module_name`` itself defines."""
    from pyforestry.base.simulation.growth_model import GrowthModel

    module = importlib.import_module(module_name)
    return [
        obj
        for _attr, obj in inspect.getmembers(module, inspect.isclass)
        if issubclass(obj, GrowthModel)
        and obj is not GrowthModel
        and obj.__module__ == module_name
    ]


def _model_entries() -> Dict[str, Any]:
    """Return the catalog entries :func:`project` can step, keyed by name.

    Not every catalog entry with ``kind="model"`` is a runnable projection: the
    NYSKOG reconstruction, Nyström & Söderberg's young-stand functions and
    Elfving & Hägglund's initial-stand generator are all published models that
    produce a stand rather than advance one. Listing them here would be listing
    names ``project`` cannot run, so the filter is "does this module define a
    ``GrowthModel``".

    The catalog's ids end in ``_model`` (``"elfving_2010_model"``); both that and
    the short form (``"elfving_2010"``) resolve, because the short form is what a
    user would type and the long form is what ``catalog.search`` shows them.
    """
    from pyforestry import catalog

    entries: Dict[str, Any] = {}
    for entry in catalog.list_models():
        if entry.kind != "model" or not _growth_models_in(entry.module):
            continue
        entries[entry.component_id] = entry
        short = entry.component_id.removesuffix("_model")
        entries.setdefault(short, entry)
    return entries


def available_models() -> list[str]:
    """Return every name :func:`project` accepts for ``model=``, sorted.

    These are single-tree/stand growth models: give one a :class:`Stand` and it
    advances it. The *composite pipelines* -- which build their own stand from a
    site and run nine models around a growth model -- are a different shape and
    are not listed here; see :func:`available_pipelines`.
    """
    return sorted(_model_entries())


def available_pipelines() -> list[str]:
    """Return every composite pipeline name, sorted.

    A pipeline is not something :func:`project` can run: it reconstructs its own
    stand from a site rather than advancing one you supply. Build it with
    :func:`pyforestry.sweden.simulation.presets.get_pipeline` and drive it with
    ``initialize(site=...)`` / ``run_projection(...)``.
    """
    from pyforestry.sweden.simulation.presets import available_pipelines as _sweden_pipelines

    return sorted(_sweden_pipelines())


def _resolve_model(name: str) -> "GrowthModel":
    """Build the growth model the catalog publishes under ``name``.

    Raises:
        ValueError: If no model is registered under that name, or if the model
            needs configuration that has no default.
    """
    entries = _model_entries()
    entry = entries.get(name)
    if entry is None:
        known = ", ".join(available_models())
        pipelines = available_pipelines()
        hint = (
            f" {name!r} is a composite pipeline, not a growth model: it builds its own "
            f"stand from a site, so project() cannot drive it. Use "
            f"pyforestry.sweden.simulation.presets.get_pipeline({name!r}) instead."
            if name in pipelines
            else f" Composite pipelines ({', '.join(pipelines)}) are run through "
            f"pyforestry.sweden.simulation.presets.get_pipeline() rather than project()."
        )
        raise ValueError(f"Unknown model {name!r}. Available models: {known}.{hint}")

    candidates = _growth_models_in(entry.module)
    for model_cls in candidates:
        try:
            return model_cls()
        except TypeError:
            # A model whose configuration has no defaults cannot be built from a
            # name alone; try the next, and report it if none can.
            continue

    names = ", ".join(sorted(cls.__name__ for cls in candidates))
    raise ValueError(
        f"{name!r} ({names}) requires configuration that has no default, so it "
        f"cannot be built from a name alone. Construct it yourself and pass the "
        f"instance as model=."
    )


def project(
    stand: "Stand",
    *,
    model: Union[str, "GrowthModel"],
    years: float,
    step: Optional[float] = None,
    seed: Optional[int] = None,
    policy: Optional["Policy"] = None,
    attrs: Optional[Mapping[str, Any]] = None,
    inputs: Optional[Any] = None,
    pipeline: Optional[Sequence["Step"]] = None,
) -> ProjectionResult:
    """Project ``stand`` forward and return the result.

    Args:
        stand: The inventory to project. Deep-copied first, so the caller's stand
            is untouched and the same stand can be projected under several models
            or several seeds and compared. (``GrowthModel.build_context`` copies
            only the plot containers and shares the ``Tree`` objects, because a
            model grows diameters in place. That is right for a model and wrong
            for a front door: it would make ``project(stand, ...)`` return
            something different the second time you called it.)
        model: A name from :func:`available_models`, or a
            :class:`~pyforestry.base.simulation.growth_model.GrowthModel` you
            built yourself.
        years: Total length of the projection.
        step: Length of one period. Defaults to the model's declared
            ``native_step_years``, and to 5 years for a model that declares none,
            so the common case needs no argument and no guessing.
        seed: Root seed for every random stream the run uses. Required only if
            something in the run draws; without it, drawing raises rather than
            silently using an unseeded generator.
        policy: A management policy -- ``Callable[[ctx], Sequence[Action]]`` --
            run before growth in each period. Triggers, schedules and rulesets are
            all policies; see :mod:`pyforestry.base.simulation.pipeline`.
        attrs: Site and history values the stand does not carry typed. Resolved
            into the model's ``Inputs`` during the build, so a missing one is a
            named error before any time is simulated.
        inputs: An already-built ``Inputs`` instance, which skips resolution.
        pipeline: The ordered steps to run each period, overriding the default
            (management if a policy was given, then growth). Supply this to add a
            valuation step or reorder the phases.

    Returns:
        A :class:`ProjectionResult`.

    Raises:
        ValueError: If ``model`` names nothing, if the stand cannot supply what
            the model needs, or if the clock arguments are not positive.
    """
    from pyforestry.base.simulation.pipeline import GrowthStep, ManagementStep, run_pipeline

    growth_model = _resolve_model(model) if isinstance(model, str) else model
    stand = copy.deepcopy(stand)

    ok, missing = growth_model.can_build(stand)
    if not ok:
        raise ValueError(
            f"{type(growth_model).__name__} cannot run on this stand: it needs "
            f"{', '.join(missing)}. Check with model.can_build(stand) before projecting."
        )

    if step is None:
        step = growth_model.requirements().native_step_years or 5.0

    ctx = growth_model.build_context(
        stand,
        attrs=dict(attrs) if attrs else None,
        inputs=inputs,
        seed=seed,
    )

    if pipeline is None:
        steps: list["Step"] = []
        if policy is not None:
            steps.append(ManagementStep(policy))
        steps.append(GrowthStep())
        pipeline = tuple(steps)

    run_pipeline(ctx, pipeline, years=float(years), step=float(step))

    return ProjectionResult(
        table=ctx.to_pandas(),
        stand=ctx.stand,
        context=ctx,
        provenance=_provenance(growth_model),
    )


def _provenance(component: Any) -> Dict[str, Any]:
    """Collect the citations of a component and of everything it composes.

    ``components`` is ``Sequence[Describable]``: each entry declares its own
    ``component_id`` and ``source``, and each is descended into, so a composition
    of compositions reports the papers at the bottom.

    A component that declares ``components`` but whose entries are not
    :class:`~pyforestry.base.contracts.Describable` raises. Skipping them is how
    seven mortality citations went missing without a word -- the engine returned
    bare id strings, which have no ``source``, so every one was dropped and the
    run reported as citing only the composition itself.

    Raises:
        TypeError: If an entry of ``components`` does not describe itself.
    """
    provenance: Dict[str, Any] = {}
    _collect_provenance(component, provenance, seen=set())
    return provenance


def _collect_provenance(component: Any, into: Dict[str, Any], seen: set[int]) -> None:
    """Add ``component``'s citation to ``into``, then recurse into what it composes."""
    if id(component) in seen:
        return
    seen.add(id(component))

    component_id = getattr(component, "component_id", None)
    source = getattr(component, "source", None)
    if component_id is not None and source is not None:
        into[str(component_id)] = source

    for child in getattr(component, "components", ()) or ():
        if getattr(child, "component_id", None) is None or getattr(child, "source", None) is None:
            raise TypeError(
                f"{type(component).__name__}.components must yield Describable objects "
                f"(each with component_id and source), but one entry is "
                f"{child!r}. Returning ids alone loses the citations they stand for."
            )
        _collect_provenance(child, into, seen)
