"""What a run earned, when, and what that is worth at the start of it.

A projection that thins produces revenue in the year the thinning happened. Two
things then stand between those figures and a number an analyst can compare
against another scenario, and both are forcings:

* **What a cubic metre fetched that year.** A
  :data:`~pyforestry.simulation.forcing.PRICE` forcing scales each period's
  revenue where it is earned, so the flows this module receives are already
  nominal — in the money of their own year.
* **What a krona in that year is worth now.** Discounting, at a rate that may
  itself vary year by year, which is a
  :data:`~pyforestry.simulation.forcing.DISCOUNT` forcing.

Keeping them apart is the point. A single "real" rate folded together hides which
half of a difference between two scenarios came from prices and which from time
preference; the run manifest records both, separately, with their sources.

A discount rate is a *stated preference*, not a finding about the world, so it is
cited with the ``(none)``/year-0 sentinel this package already uses for anything
authored rather than published — :func:`~pyforestry.simulation.forcing.stated_choice`
builds one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional, Sequence

from pyforestry.simulation.forcing import DISCOUNT, ForcingSet

__all__ = [
    "CASH_FLOWS_KEY",
    "CashFlow",
    "discount_factor",
    "net_present_value",
]

#: Where a run's cash flows accumulate on the context, one entry per period that
#: earned anything.
CASH_FLOWS_KEY = "cash_flows"


@dataclass(frozen=True)
class CashFlow:
    """One period's revenue, in the money of the year it was earned.

    Attributes:
        year: The calendar year the revenue was earned in.
        amount: The revenue, nominal -- already scaled by whatever price forcing
            applied that year.
        price_factor: The price forcing that was applied, recorded so a reader
            can separate a change in prices from a change in what was cut.
        label: What produced it, e.g. the stage's name.
    """

    year: float
    amount: float
    price_factor: float = 1.0
    label: str = ""

    def as_mapping(self) -> Mapping[str, Any]:
        """Return this flow as a plain mapping, for reporting."""
        return {
            "year": float(self.year),
            "amount": float(self.amount),
            "price_factor": float(self.price_factor),
            "label": self.label,
        }


def _rate_at(year: float, *, discount_rate: Optional[float], forcings: ForcingSet) -> float:
    """Return the discount rate that applies to ``year``.

    A :data:`~pyforestry.simulation.forcing.DISCOUNT` forcing wins over a flat
    rate, so a term structure can be supplied for a run that has one.

    Raises:
        TypeError: If the forcing's value is not a number. A rate per species is
            not a thing a cash flow can be discounted at, and ``float()`` on a
            mapping says only that it is not a float.
    """
    if DISCOUNT not in forcings.names():
        return float(discount_rate or 0.0)
    value = forcings.value(DISCOUNT, year, default=discount_rate or 0.0)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(
            f"The discount forcing is {type(value).__name__} in {year:g}, and a cash "
            "flow is discounted at one rate. A rate that varies by year is an "
            "AnnualForcing whose values are numbers; a rate that varies by anything "
            "else is not something this discounts at."
        )
    return float(value)


def discount_factor(
    year: float,
    base_year: float,
    *,
    discount_rate: Optional[float] = None,
    forcings: Optional[ForcingSet] = None,
) -> float:
    """Return what one unit of money in ``year`` is worth in ``base_year``.

    With a flat rate this is the textbook ``1 / (1 + r) ** (year - base_year)``.
    With a :data:`~pyforestry.simulation.forcing.DISCOUNT` forcing it compounds
    year by year, so a rate that changes over the horizon discounts each year at
    its own -- which a single exponent cannot express.

    Args:
        year: The year the money falls in.
        base_year: The year to express it in. Usually the run's first.
        discount_rate: A flat annual rate, e.g. ``0.03``.
        forcings: The run's forcings; a ``DISCOUNT`` one overrides the flat rate.

    Returns:
        The factor to multiply a nominal amount by. ``1.0`` when the flow is in
        the base year, or when no rate applies at all.

    Raises:
        ValueError: If a rate of ``-1`` or below applies, which makes money in
            the following year infinitely valuable.
        KeyError: If a ``DISCOUNT`` series does not cover every year between
            ``base_year`` and ``year``. Compounding needs a rate for each of them,
            so a term structure has to be dense over the horizon it is used on.
    """
    resolved = forcings or ForcingSet()
    if year == base_year:
        return 1.0

    factor = 1.0
    step = 1 if year > base_year else -1
    whole_years = int(abs(year - base_year))
    # Compound across the years between, so a year-varying rate is applied to the
    # year it belongs to rather than averaged into one exponent. Each step covers
    # the interval [earlier, earlier + 1), and it is the *earlier* year's rate
    # that governs it -- which is `base_year + offset` going forwards and
    # `base_year - offset - 1` going back. Sampling `base_year - offset` for a
    # flow before the base year took the rate one year too late every step,
    # including `base_year`'s own, which governs no interval in that direction.
    for offset in range(whole_years):
        governing_year = base_year + offset if step > 0 else base_year - offset - 1
        rate = _rate_at(governing_year, discount_rate=discount_rate, forcings=resolved)
        if rate <= -1.0:
            raise ValueError(
                f"A discount rate of {rate!r} applies in {governing_year:g}, which makes "
                "money in the next year infinitely valuable. Rates must exceed -1."
            )
        factor *= 1.0 / (1.0 + rate) if step > 0 else (1.0 + rate)

    fractional = abs(year - base_year) - whole_years
    if fractional:
        # The part-year beyond the whole ones, governed by the year it falls in.
        governing_year = base_year + whole_years if step > 0 else base_year - whole_years - 1
        rate = _rate_at(governing_year, discount_rate=discount_rate, forcings=resolved)
        factor *= (1.0 + rate) ** (-fractional * step)
    return factor


def net_present_value(
    cash_flows: Iterable[CashFlow],
    *,
    base_year: float,
    discount_rate: Optional[float] = None,
    forcings: Optional[ForcingSet] = None,
) -> float:
    """Return the discounted value of ``cash_flows``, expressed in ``base_year``.

    Args:
        cash_flows: What the run earned, and when.
        base_year: The year to express the total in -- the run's first, usually.
        discount_rate: A flat annual rate.
        forcings: The run's forcings. A ``DISCOUNT`` forcing supplies a
            year-varying rate; a ``PRICE`` forcing has already been applied to the
            amounts, where they were earned.

    Returns:
        The sum of each flow times its discount factor. Zero for no flows, which
        is the ordinary case for a projection that never harvested.
    """
    resolved = forcings or ForcingSet()
    return float(
        sum(
            flow.amount
            * discount_factor(
                flow.year,
                base_year,
                discount_rate=discount_rate,
                forcings=resolved,
            )
            for flow in cash_flows
        )
    )


def cash_flows_of(attrs: Mapping[str, Any]) -> Sequence[CashFlow]:
    """Return the cash flows recorded on a context's attributes, if any."""
    return tuple(attrs.get(CASH_FLOWS_KEY, ()))
