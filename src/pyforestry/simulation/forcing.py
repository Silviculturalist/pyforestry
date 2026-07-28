"""Forcings: named values a run can read for the period it is in.

A forcing is something imposed on a projection from outside it — not anything a
published model predicts. A weather correction on growth, a windthrow rate, a
thinning intensity, a price index: the package provides the *mechanism* and
ships none of them, because every such number is a claim about the world and
this package has no basis for one.

**A forcing is just a named value the state can look up at a time.** Three things
vary, and the type is deliberately open on all three:

* **What it is called** — the ``name``. The shipped steps read four
  (:data:`GROWTH`, :data:`DISTURBANCE`, :data:`THINNING`, :data:`PRICE`); the set
  is open, and a step you write reads whatever name it likes.
* **Its resolution in time** — :class:`ConstantForcing` holds one value for the
  whole run; :class:`AnnualForcing` a value per calendar year::

      AnnualForcing(GROWTH, {2014: 1.04, 2015: 1.02, 2016: 0.98, 2019: 0.67},
                    source=SourceReference(...))

* **Its type** — the value at a year is whatever you put there. A float is the
  common case; a mapping is how a forcing varies by something else as well, most
  obviously species::

      AnnualForcing(
          GROWTH,
          {2014: {PICEA_ABIES: 1.06, PINUS_SYLVESTRIS: 1.01},
           2015: {PICEA_ABIES: 0.98, PINUS_SYLVESTRIS: 1.03}},
          source=SourceReference(...),
      )

  :meth:`ForcingSet.multiplier` takes an optional ``key`` and indexes into such a
  mapping, so a step asks for "the growth forcing for spruce in this period" and
  gets 1.0 if nothing forces it. Values that are neither -- a flag, a category, a
  list -- are read with :meth:`ForcingSet.value` and interpreted by whatever step
  asked for them.

Any forcing that is not exactly neutral must carry a :class:`SourceReference`.
The package shipped one that did not: a ``climate_rcp45`` scenario whose
multipliers arrived in the first commit with no source, under a name asserting a
specific IPCC pathway. Every forcing a run applies is written into its manifest
with its citation attached, which is what makes the run readable afterwards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Mapping, Optional, Protocol, runtime_checkable

from pyforestry.base.contracts import SourceReference
from pyforestry.base.simulation.core import SimulationContext

__all__ = [
    "CALENDAR_YEAR_KEY",
    "AnnualForcing",
    "ConstantForcing",
    "DISTURBANCE",
    "Forcing",
    "ForcingSet",
    "GROWTH",
    "PRICE",
    "THINNING",
    "is_neutral_value",
    "period_year",
]

#: Names the shipped steps read. Any string works; these are the ones with a
#: consumer, named so a caller does not have to guess the spelling.
GROWTH = "growth"
DISTURBANCE = "disturbance"
THINNING = "thinning"
PRICE = "price"

#: Where the period's calendar year is stamped on the context. A projection's own
#: clock is elapsed years from wherever the model started -- and some models start
#: it at the stand's age -- while a forcing series is keyed by calendar year. This
#: is where the two are reconciled.
CALENDAR_YEAR_KEY = "calendar_year"


def period_year(ctx: SimulationContext) -> float:
    """Return the calendar year of the period currently running.

    Stamped by :class:`~pyforestry.simulation.stages.CalendarStep`, which
    :func:`~pyforestry.simulation.stages.build_pipeline` puts first. A run without
    one has no calendar, and a year-keyed forcing would otherwise silently get
    whatever year ``0`` maps to.

    Raises:
        RuntimeError: If no calendar was stamped.
    """
    year = ctx.attrs.get(CALENDAR_YEAR_KEY)
    if year is None:
        raise RuntimeError(
            "This run has no calendar year, so a forcing keyed by year cannot be read. "
            "run_scenario installs a CalendarStep from its start_year; a hand-built "
            "pipeline needs one too."
        )
    return float(year)


#: What an :class:`AnnualForcing` does for a year its series does not cover.
#: ``"raise"`` is the default because a run that steps past the end of a weather
#: series is asking a question the series cannot answer, and the alternatives
#: answer it silently: ``"hold"`` extends the nearest year's value, ``"neutral"``
#: substitutes 1.0.
_OUTSIDE_SERIES = ("raise", "hold", "neutral")


def is_neutral_value(value: Any) -> bool:
    """Whether ``value`` leaves a model's own prediction exactly as it is.

    ``1.0``, or a mapping every one of whose values is neutral. Anything else --
    a different number, a flag, a category -- changes something, and so needs a
    citation.
    """
    if isinstance(value, Mapping):
        return all(is_neutral_value(item) for item in value.values())
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value) == 1.0
    return False


def _require_citation(name: str, values: Iterable[Any], source: Optional[SourceReference]) -> None:
    """Reject a forcing that changes the numbers without saying where it came from.

    Raises:
        ValueError: If any value is not neutral and no source is given.
    """
    if all(is_neutral_value(value) for value in values):
        return
    if source is None:
        raise ValueError(
            f"The forcing {name!r} is not neutral, so it changes what a published model "
            "predicts and must say where it comes from: pass source=SourceReference(...). "
            "An uncited forcing under a scenario's name reads as that scenario's finding. "
            "This package ships no forcings for exactly that reason."
        )


def _source_manifest(source: Optional[SourceReference]) -> Optional[dict[str, Any]]:
    """Render a citation for the manifest, or ``None``."""
    if source is None:
        return None
    return {
        "author": source.author,
        "year": source.year,
        "title": source.title,
        "note": source.note,
    }


def _jsonable(value: Any) -> Any:
    """Render a forcing value for the manifest, keeping mapping keys as strings."""
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    return str(value)


@runtime_checkable
class Forcing(Protocol):
    """A named value a run can read for the period it is in."""

    name: str
    source: Optional[SourceReference]

    def at(self, year: float) -> Any:
        """Return this forcing's value in ``year``. Any type."""
        ...

    def as_manifest(self) -> Mapping[str, Any]:
        """Return a JSON-serialisable record of this forcing, for the run manifest."""
        ...


@dataclass(frozen=True)
class ConstantForcing:
    """One value, held for the whole run.

    Args:
        name: What it is called -- :data:`GROWTH`, :data:`PRICE`, or any name a
            step of yours reads.
        value: The value. Any type; ``1.0`` is an exact no-op and needs no source.
        source: Where it comes from. Required unless the value is neutral.

    Raises:
        ValueError: If the value is not neutral and has no source.
    """

    name: str
    value: Any = 1.0
    source: Optional[SourceReference] = None

    def __post_init__(self) -> None:
        """Validate the value's citation."""
        _require_citation(self.name, (self.value,), self.source)

    def at(self, year: float) -> Any:
        """Return the value, which does not depend on the year."""
        return self.value

    def as_manifest(self) -> Mapping[str, Any]:
        """Return this forcing as a manifest record."""
        return {
            "name": self.name,
            "resolution": "constant",
            "value": _jsonable(self.value),
            "source": _source_manifest(self.source),
        }


@dataclass(frozen=True)
class AnnualForcing:
    """A value that changes from year to year.

    The weather-correction case: a value per calendar year, with the run's clock
    supplying the year. A period spanning several years takes the value at the
    year the period *starts*, which is the resolution a stepped projection has;
    use a shorter step if a single year matters.

    Args:
        name: What it is called.
        series: Calendar year to value. Need not be contiguous, and the values
            may be any type -- a float, or a mapping keyed by species.
        outside_series: What to do for a year the series does not cover --
            ``"raise"`` (the default), ``"hold"`` the nearest year's value, or
            ``"neutral"`` for 1.0.
        source: Where the series comes from. Required unless every value is
            neutral.

    Raises:
        ValueError: If the series is empty, is not neutral and has no source, or
            ``outside_series`` is not one of the three.
    """

    name: str
    series: Mapping[float, Any]
    outside_series: str = "raise"
    source: Optional[SourceReference] = None

    def __post_init__(self) -> None:
        """Validate the series, its citation and its extrapolation rule."""
        if not self.series:
            raise ValueError(
                f"The forcing {self.name!r} needs at least one year. Use ConstantForcing "
                "for a value that does not vary."
            )
        if self.outside_series not in _OUTSIDE_SERIES:
            raise ValueError(
                f"outside_series must be one of {_OUTSIDE_SERIES}, got {self.outside_series!r}."
            )
        object.__setattr__(self, "series", dict(sorted(self.series.items())))
        _require_citation(self.name, self.series.values(), self.source)

    def at(self, year: float) -> Any:
        """Return the value for ``year``.

        Raises:
            KeyError: If the series does not cover ``year`` and
                ``outside_series`` is ``"raise"``.
        """
        key = float(year)
        if key in self.series:
            return self.series[key]
        if self.outside_series == "neutral":
            return 1.0
        if self.outside_series == "hold":
            years = list(self.series)
            return self.series[years[0] if key < years[0] else years[-1]]
        covered = f"{min(self.series):g}-{max(self.series):g}"
        raise KeyError(
            f"The forcing {self.name!r} has no value for year {key:g}; its series covers "
            f"{covered}. Extend the series, or say what should happen outside it with "
            "outside_series='hold' or 'neutral'."
        )

    def as_manifest(self) -> Mapping[str, Any]:
        """Return this forcing as a manifest record."""
        return {
            "name": self.name,
            "resolution": "annual",
            "series": {f"{year:g}": _jsonable(value) for year, value in self.series.items()},
            "outside_series": self.outside_series,
            "source": _source_manifest(self.source),
        }


@dataclass(frozen=True)
class ForcingSet:
    """The forcings a run applies, looked up by name and year.

    Several forcings may share a name -- a weather correction and a nitrogen
    response both act on growth -- so :meth:`multiplier` composes them by
    multiplication, in the order given. A name with no forcing multiplies by
    ``1.0``, so a run that declares none gets exactly what the models predict.
    """

    forcings: tuple[Forcing, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Normalise whatever iterable was passed into a tuple."""
        object.__setattr__(self, "forcings", tuple(self.forcings))

    def __iter__(self) -> Iterator[Forcing]:
        """Iterate the forcings, in the order they were given."""
        return iter(self.forcings)

    def __len__(self) -> int:
        """Return how many forcings this set holds."""
        return len(self.forcings)

    def __bool__(self) -> bool:
        """Whether this set holds any forcing at all."""
        return bool(self.forcings)

    def names(self) -> frozenset[str]:
        """Return every name this set forces."""
        return frozenset(forcing.name for forcing in self.forcings)

    def values(self, name: str, year: float) -> tuple[Any, ...]:
        """Return each forcing of ``name`` evaluated at ``year``, in order.

        The general accessor: the values may be of any type, and it is the
        caller's business what they mean. :meth:`multiplier` is the numeric
        special case.
        """
        return tuple(f.at(year) for f in self.forcings if f.name == name)

    def value(self, name: str, year: float, *, default: Any = None) -> Any:
        """Return the last value declared for ``name`` in ``year``, or ``default``.

        For a forcing that is not a multiplier -- a flag, a category, a list --
        where composing several makes no sense and the last declaration wins.
        """
        found = self.values(name, year)
        return found[-1] if found else default

    def multiplier(self, name: str, year: float, *, key: Any = None) -> float:
        """Return the combined multiplier for ``name`` in ``year``.

        Args:
            name: The forcing's name.
            year: The calendar year of the period being run.
            key: Index into a forcing whose value is a mapping -- a species, most
                often. A mapping that does not hold the key contributes ``1.0``,
                so a per-species forcing that names only spruce leaves pine
                alone.

        Returns:
            The product of every forcing of that name, or ``1.0`` if there is
            none.

        Raises:
            TypeError: If a value is neither a number nor a mapping, since it
                cannot be multiplied by. Read it with :meth:`value` instead.
        """
        product = 1.0
        for value in self.values(name, year):
            if isinstance(value, Mapping):
                resolved = value.get(key, 1.0) if key is not None else 1.0
            else:
                resolved = value
            if isinstance(resolved, bool) or not isinstance(resolved, (int, float)):
                raise TypeError(
                    f"The forcing {name!r} is {type(resolved).__name__}, which cannot be "
                    "multiplied by. Read it with ForcingSet.value() and interpret it in "
                    "the step that wants it."
                )
            product *= float(resolved)
        return product

    def merge(self, other: "ForcingSet") -> "ForcingSet":
        """Return a set holding this set's forcings followed by ``other``'s."""
        return ForcingSet((*self.forcings, *other.forcings))

    def as_manifest(self) -> list[Mapping[str, Any]]:
        """Return every forcing as a manifest record, in order."""
        return [forcing.as_manifest() for forcing in self.forcings]
