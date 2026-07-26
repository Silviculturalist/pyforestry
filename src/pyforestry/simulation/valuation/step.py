"""Pricing removals as a step in a simulation pipeline.

This is what gives :mod:`pyforestry.simulation.valuation` a runtime. The ledger,
the connector and the piece records were a complete design with no caller,
because nothing harvested *through* a runtime; a pipeline that thins and then
prices what it removed is that caller.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable

from pyforestry.base.simulation import SimulationContext

from .removals import StandRemovalLedger
from .volume import VolumeConnector, VolumeResult

__all__ = ["HasRemovalLedger", "ValuationStep"]


@runtime_checkable
class HasRemovalLedger(Protocol):
    """What a context must offer for :class:`ValuationStep` to price it.

    One declared method. The stage this replaced looked in six places --
    ``view.removal_ledger``, ``view.removals``, ``view.ledger``,
    ``view.get_removal_ledger()``, ``part.context["valuation"]["ledger"]`` and
    ``part.context["removal_ledger"]`` -- and returned ``None`` if none of them
    held one, which means a view that implemented the protocol under a seventh
    name was silently valued at zero and so was a view that implemented nothing.
    Six conventions is no convention.
    """

    def removal_ledger(self) -> Optional[StandRemovalLedger]:
        """Return the removals accumulated since the last valuation, if any."""
        ...


@dataclass
class ValuationStep:
    """Price whatever the run has removed, and add it to the run's cash.

    Reads the ledger from ``ctx.attrs["removal_ledger"]`` -- the one place -- and
    writes the priced result back to ``ctx.attrs["valuation"]``. Does nothing when
    there is no ledger or it is empty, which is the ordinary case for a step that
    did not thin.
    """

    connector: VolumeConnector = field(default_factory=VolumeConnector)
    name: str = "valuation"

    #: Where the ledger is read from and the result is written to.
    LEDGER_KEY = "removal_ledger"
    RESULT_KEY = "valuation"
    CASH_KEY = "cash"

    def run(self, ctx: SimulationContext, dt: float) -> None:
        """Price this period's removals into ``ctx.attrs``."""
        ledger = ctx.attrs.get(self.LEDGER_KEY)
        if not isinstance(ledger, StandRemovalLedger) or ledger.is_empty:
            return
        result: VolumeResult = self.connector.connect(self._descriptor_source(ctx), ledger)
        ctx.attrs[self.RESULT_KEY] = {
            "ledger": ledger,
            "result": result,
            "pieces": result.pieces,
            "volume_by_quality": result.volume_by_quality,
            "total_value": result.total_value,
            "metadata": result.metadata,
        }
        ctx.attrs[self.CASH_KEY] = float(ctx.attrs.get(self.CASH_KEY, 0.0)) + float(
            result.total_value
        )

    @staticmethod
    def _descriptor_source(ctx: SimulationContext) -> Any:
        """Return the object carrying the pricelist, taper and bucking settings.

        ``ctx.attrs["valuation_settings"]`` when supplied, else the context
        itself -- so a caller can hand over a settings object without the
        connector reaching into the run for it.
        """
        return ctx.attrs.get("valuation_settings", ctx)
