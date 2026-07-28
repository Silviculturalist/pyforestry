"""A price forcing moves the money; a discount rate moves it in time.

The two are kept apart on purpose. Folding them into one "real" rate hides which
half of a difference between two scenarios came from prices and which from time
preference, and the run manifest records both separately with their sources.
"""

from __future__ import annotations

import pytest

from pyforestry.base.contracts import SourceReference
from pyforestry.simulation.forcing import (
    DISCOUNT,
    PRICE,
    AnnualForcing,
    ConstantForcing,
    ForcingSet,
    stated_choice,
)
from pyforestry.simulation.valuation.cashflow import (
    CashFlow,
    discount_factor,
    net_present_value,
)

CITED = SourceReference(author="Test fixture", year=2026, title="Invented here, and saying so")


# --- discounting ---------------------------------------------------------------


def test_the_base_year_is_undiscounted() -> None:
    assert discount_factor(2025, 2025, discount_rate=0.03) == 1.0


def test_a_flat_rate_is_the_textbook_exponent() -> None:
    assert discount_factor(2035, 2025, discount_rate=0.03) == pytest.approx(1.03**-10)


def test_no_rate_leaves_money_where_it_is() -> None:
    assert discount_factor(2035, 2025) == 1.0


def test_a_year_varying_rate_compounds_year_by_year() -> None:
    """What a single exponent cannot express: a term structure.

    2% to 2030, 5% after -- so five years at each, not ten at some average.
    """
    rates = {year: (0.02 if year < 2030 else 0.05) for year in range(2025, 2036)}
    forcings = ForcingSet([AnnualForcing(DISCOUNT, rates, source=stated_choice("2% then 5%"))])

    assert discount_factor(2035, 2025, forcings=forcings) == pytest.approx(1.02**-5 * 1.05**-5)


def test_a_discount_forcing_overrides_a_flat_rate() -> None:
    forcings = ForcingSet([ConstantForcing(DISCOUNT, 0.05, source=stated_choice("5%"))])
    assert discount_factor(2035, 2025, discount_rate=0.03, forcings=forcings) == pytest.approx(
        1.05**-10
    )


def test_a_rate_that_makes_money_infinite_is_refused() -> None:
    with pytest.raises(ValueError, match="infinitely valuable"):
        discount_factor(2030, 2025, discount_rate=-1.0)


# --- net present value ---------------------------------------------------------


def test_npv_discounts_each_flow_from_its_own_year() -> None:
    flows = [CashFlow(2035, 100.0), CashFlow(2045, 100.0)]
    assert net_present_value(flows, base_year=2025, discount_rate=0.03) == pytest.approx(
        100.0 * 1.03**-10 + 100.0 * 1.03**-20
    )


def test_a_run_that_earned_nothing_is_worth_nothing() -> None:
    assert net_present_value([], base_year=2025, discount_rate=0.03) == 0.0


def test_inflation_and_discounting_compose_without_being_confused() -> None:
    """Prices move the money; the rate moves it in time; neither is the other.

    Two flows, the second inflated 21.9% by a price index. At a 3% discount rate
    the extra nominal revenue survives discounting in proportion.
    """
    flat = [CashFlow(2035, 100.0, price_factor=1.0)]
    inflated = [CashFlow(2035, 121.9, price_factor=1.219)]

    npv_flat = net_present_value(flat, base_year=2025, discount_rate=0.03)
    npv_inflated = net_present_value(inflated, base_year=2025, discount_rate=0.03)

    assert npv_inflated / npv_flat == pytest.approx(1.219)


def test_the_price_factor_travels_with_the_flow() -> None:
    """So a reader can separate a change in prices from a change in what was cut."""
    flow = CashFlow(2035, 121.9, price_factor=1.219, label="management")
    assert flow.as_mapping() == {
        "year": 2035.0,
        "amount": 121.9,
        "price_factor": 1.219,
        "label": "management",
    }


# --- the citation rule, for a value that is a choice ----------------------------


def test_a_discount_rate_is_cited_as_a_stated_choice() -> None:
    """It satisfies the rule, and says in the manifest that nobody published it."""
    forcing = ConstantForcing(DISCOUNT, 0.03, source=stated_choice("3% real"))
    record = forcing.as_manifest()
    assert record["source"]["author"] == "(none)"
    assert record["source"]["year"] == 0
    assert "3% real" in record["source"]["title"]
    assert "not a finding" in record["source"]["note"]


def test_an_uncited_discount_rate_is_still_refused() -> None:
    """One rule, no exemption -- the sentinel is how a choice satisfies it."""
    with pytest.raises(ValueError, match="where it comes from"):
        ConstantForcing(DISCOUNT, 0.03)


def test_a_price_index_is_a_forcing_like_any_other() -> None:
    index = AnnualForcing(PRICE, {2025: 1.0, 2030: 1.104, 2035: 1.219}, source=CITED)
    forcings = ForcingSet([index])
    assert forcings.multiplier(PRICE, 2035) == pytest.approx(1.219)
    assert forcings.multiplier(PRICE, 2025) == 1.0
