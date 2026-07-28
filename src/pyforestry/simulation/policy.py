"""What a scenario's rulesets return, and what the numbers in them mean.

A ruleset maps a scenario id to the knobs that scenario turns. The *values* are
regional policy and live in ``<region>/simulation/policy/``; the *contract* --
what the fields mean, in what units, and what happens when a scenario id is
unknown -- is here, because the two regions had answered both questions
differently:

* ``management_plan("bogus")`` raised ``ValueError`` in Sweden and silently
  returned the baseline in Norway;
* ``scenario_factors("bogus")`` likewise;
* and ``thinning_ratio`` was ``0.20`` in Sweden -- a *fraction of stems removed*
  -- against ``1.0`` in Norway, which was an *intensity multiplier* wearing the
  same name. A run configured for Norway's "intensive" scenario would have been
  read as thinning 120% of the stand.

An unknown scenario id now raises in both. Defaulting to baseline turns a typo
into a full run of plausible numbers under a scenario nobody chose, which is the
failure this package's artifacts exist to make impossible.

This module used to also hold ``ScenarioFactors``, a frozen pair of
``growth_factor`` and ``disturbance_factor``. Those were two instances of one
idea -- an external factor imposed on the run -- hard-coded as two fields, which
is why there was no way to express a third (a price index), or a factor that
changes from year to year, or one that differs by species. The general form is
:mod:`pyforestry.simulation.forcing`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, TypeVar

__all__ = [
    "ManagementPlan",
    "lookup_scenario",
]

_T = TypeVar("_T")


@dataclass(frozen=True)
class ManagementPlan:
    """What management a scenario prescribes.

    Attributes:
        thinning_ratio: Fraction of standing stems removed at a thinning event,
            in ``[0, 1]``. This is a *fraction*, not a multiplier: a region whose
            scenarios differ by intensity expresses that as a different fraction,
            not as a factor applied to an unstated base.
    """

    thinning_ratio: float

    def __post_init__(self) -> None:
        """Reject a thinning ratio that is not a fraction."""
        if not 0.0 <= self.thinning_ratio <= 1.0:
            raise ValueError(
                f"thinning_ratio must be a fraction of stems in [0, 1], got "
                f"{self.thinning_ratio!r}. A scenario multiplier is not a ratio."
            )

    def as_mapping(self) -> Mapping[str, float]:
        """Return the plan as a plain mapping, for the run manifest."""
        return {"thinning_ratio": float(self.thinning_ratio)}


def lookup_scenario(table: Mapping[str, _T], scenario_id: str, *, what: str) -> _T:
    """Look ``scenario_id`` up in ``table``, naming the alternatives if it is absent.

    Args:
        table: The region's scenario table.
        scenario_id: The scenario asked for.
        what: What is being looked up, for the error message.

    Returns:
        The table's entry for ``scenario_id``.

    Raises:
        ValueError: If ``scenario_id`` is not in ``table``.
    """
    try:
        return table[scenario_id]
    except KeyError:
        known = ", ".join(sorted(table)) or "(none)"
        raise ValueError(
            f"Unsupported scenario_id {scenario_id!r} for {what}. Known scenarios: {known}."
        ) from None
