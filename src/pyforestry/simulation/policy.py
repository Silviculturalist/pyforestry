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
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, TypeVar

from pyforestry.base.contracts import SourceReference

__all__ = [
    "ManagementPlan",
    "ScenarioFactors",
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


@dataclass(frozen=True)
class ScenarioFactors:
    """Scenario overlays applied on top of the published models.

    Neither factor is part of any published model. They are scenario devices --
    the sort a climate projection applies over a growth model fitted on the
    historical record -- so both default to ``1.0``, both are recorded in the run
    manifest, and the step that applies each says so in its name.

    **A factor that is not 1.0 must cite where it comes from.** A multiplier on a
    published model's increment is a claim about the world, and a named scenario
    carrying one is a claim that the number belongs to that name. This package
    shipped ``climate_rcp45 = {growth 1.05, disturbance 1.2}`` from its first
    commit with no source anywhere: the name says IPCC RCP4.5 and the numbers came
    from nobody. Sweden had already deleted a ``storm_risk_high`` for exactly
    that, so requiring the citation is the rule that was being applied by hand.

    Attributes:
        growth_factor: Multiplier on the period's *increment*, not on the
            standing stock. ``1.0`` leaves the model's own prediction untouched.
        disturbance_factor: Multiplier on the scenario disturbance rate. The
            disturbance itself is an addition to the model, not a distortion of
            it: none of these growth models predicts windthrow or fire.
        source: Where the factors come from. Required whenever either differs
            from ``1.0``; ``None`` is only valid for the neutral overlay.
    """

    growth_factor: float = 1.0
    disturbance_factor: float = 1.0
    source: Optional[SourceReference] = None

    def __post_init__(self) -> None:
        """Reject a negative multiplier, or an uncited one.

        Raises:
            ValueError: If a factor is negative, or if a factor differs from 1.0
                without a :class:`~pyforestry.base.contracts.SourceReference`
                saying where it came from.
        """
        for name in ("growth_factor", "disturbance_factor"):
            value = getattr(self, name)
            if value < 0.0:
                raise ValueError(f"{name} must not be negative, got {value!r}.")

        if self.is_neutral:
            return
        if self.source is None:
            raise ValueError(
                f"ScenarioFactors(growth_factor={self.growth_factor!r}, "
                f"disturbance_factor={self.disturbance_factor!r}) changes a published "
                "model's numbers, so it must say where the factors come from: pass "
                "source=SourceReference(...). An uncited multiplier under a scenario "
                "name reads as that scenario's finding."
            )

    @property
    def is_neutral(self) -> bool:
        """Whether this overlay leaves the model's own prediction untouched."""
        return self.growth_factor == 1.0 and self.disturbance_factor == 1.0

    def as_mapping(self) -> Mapping[str, object]:
        """Return the factors as a plain mapping, for the run manifest."""
        payload: dict[str, object] = {
            "growth_factor": float(self.growth_factor),
            "disturbance_factor": float(self.disturbance_factor),
        }
        if self.source is not None:
            payload["source"] = {
                "author": self.source.author,
                "year": self.source.year,
                "title": self.source.title,
                "note": self.source.note,
            }
        return payload


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
