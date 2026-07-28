"""Pricing removals as a step in a simulation pipeline.

This is what gives :mod:`pyforestry.simulation.valuation` a runtime. The ledger,
the connector and the piece records were a complete design with no caller,
because nothing harvested *through* a runtime; a pipeline that thins and then
prices what it removed is that caller.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pyforestry.base.simulation import SimulationContext
from pyforestry.simulation.forcing import PRICE, ForcingSet, period_year

from .removals import StandRemovalLedger
from .volume import ValuationSettings, VolumeConnector, VolumeResult

__all__ = ["ValuationStep"]


@dataclass
class ValuationStep:
    """Price whatever the run has removed, and add it to the run's cash.

    The price list, taper and bucking config are constructor arguments, because
    they are properties of the *pipeline* a caller assembles and do not change
    between periods. Only the ledger comes off the context, at
    ``ctx.attrs["removal_ledger"]`` -- the one place -- and the priced result goes
    back to ``ctx.attrs["valuation"]``.

    They used to be looked for on ``ctx.attrs["valuation_settings"]``, falling
    back to "the context itself", which could not work: a
    :class:`~pyforestry.base.simulation.core.SimulationContext` has no price list,
    so the documented default raised ``AttributeError`` the first time a run
    removed anything. A required argument cannot be forgotten.

    Does nothing when there is no ledger or it is empty, which is the ordinary
    case for a step that did not thin.
    """

    settings: ValuationSettings
    connector: VolumeConnector = field(default_factory=VolumeConnector)
    forcings: ForcingSet = field(default_factory=ForcingSet)
    name: str = "valuation"

    #: Where the ledger is read from and the result is written to.
    LEDGER_KEY = "removal_ledger"
    RESULT_KEY = "valuation"
    CASH_KEY = "cash"

    def run(self, ctx: SimulationContext, dt: float) -> None:
        """Price *this period's* removals into ``ctx.attrs``, then clear the ledger.

        Clearing is what makes the step correct over more than one period. The
        ledger accumulates as steps remove stems; pricing it without emptying it
        re-prices every earlier period's removals again, so ``cash`` compounds
        what was already banked and the bucking cost grows with the square of the
        run length. Nothing ran this step for two periods until the scenario
        runtime did, so neither showed.
        """
        ledger = ctx.attrs.get(self.LEDGER_KEY)
        if not isinstance(ledger, StandRemovalLedger) or ledger.is_empty:
            return
        result: VolumeResult = self.connector.connect(self.settings, ledger)
        ctx.attrs[self.LEDGER_KEY] = StandRemovalLedger(
            stand_id=ledger.stand_id, metadata=dict(ledger.metadata)
        )
        # A price forcing is inflation, or any other index on what a cubic metre
        # fetches in the year this period falls in. 1.0 with none declared.
        price_factor = self.forcings.multiplier(PRICE, period_year(ctx)) if self.forcings else 1.0
        total_value = float(result.total_value) * price_factor
        ctx.attrs[self.RESULT_KEY] = {
            "ledger": ledger,
            "result": result,
            "pieces": result.pieces,
            "volume_by_quality": result.volume_by_quality,
            "total_value": total_value,
            "price_factor": price_factor,
            "metadata": result.metadata,
        }
        ctx.attrs[self.CASH_KEY] = float(ctx.attrs.get(self.CASH_KEY, 0.0)) + total_value
