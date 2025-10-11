"""Tests covering removal ledgers and volume conversion utilities."""

from __future__ import annotations

from math import pi

import pytest

from pyforestry.base.helpers import Tree
from pyforestry.base.helpers.tree_species import PINUS_SYLVESTRIS
from pyforestry.base.pricelist.pricelist import (
    LengthRange,
    Pricelist,
    TimberPriceForDiameter,
    TimberPricelist,
)
from pyforestry.base.taper.taper import Taper
from pyforestry.base.timber.timber_base import Timber
from pyforestry.base.timber_bucking.nasberg_1985 import BuckingConfig, QualityType
from pyforestry.simulation import StandComposite, StandPart
from pyforestry.simulation.growth_module import GrowthModule
from pyforestry.simulation.valuation import StandRemovalLedger, VolumeConnector


class ConstantTaper(Taper):
    """Simple taper returning a constant diameter up to tree height."""

    def __init__(self, timber: Timber):
        self.diameter = timber.diameter_cm
        self.height = timber.height_m
        super().__init__(timber, self)

    def get_diameter_at_height(self, height_m: float) -> float:  # type: ignore[override]
        return self.diameter if 0 <= height_m <= self.height else 0.0

    def get_height_at_diameter(self, diameter: float) -> float:  # type: ignore[override]
        return self.height

    def volume_section(self, h1_m: float, h2_m: float) -> float:  # type: ignore[override]
        radius = self.diameter / 200
        return max(0.0, h2_m - h1_m) * pi * radius * radius


def _make_pricelist() -> Pricelist:
    pricelist = Pricelist()
    table = TimberPricelist(15, 15, volume_type="m3fub")
    table.set_price_for_diameter(15, TimberPriceForDiameter(10, 10, 10))
    pricelist.Timber[PINUS_SYLVESTRIS.full_name] = table
    pricelist.PulpLogLength = LengthRange(2.0, 2.0)
    pricelist.TimberLogLength = LengthRange(2.0, 2.0)
    pricelist.Pulp._prices[PINUS_SYLVESTRIS.full_name] = 1
    pricelist.LogCullPrice = 0
    pricelist.FuelWoodPrice = 0
    return pricelist


def test_removal_ledger_tracks_metadata_and_weights() -> None:
    """Recording tree removals captures cohort metadata and weights."""

    ledger = StandRemovalLedger("stand-1", metadata={"region": "north"})
    ledger.add_cohort("thin-2024", species=PINUS_SYLVESTRIS, metadata={"treatment": "thin"})

    tree = Tree(species=PINUS_SYLVESTRIS, diameter_cm=15.0, height_m=6.0, weight_n=2.5)
    removal = ledger.record_tree("thin-2024", tree, metadata={"stump_height_m": 0.15})

    assert ledger.tree_count == 1
    assert ledger.total_weight == pytest.approx(2.5)
    assert removal.metadata["treatment"] == "thin"
    assert removal.stump_height_m == pytest.approx(0.15)
    assert removal.species_name == PINUS_SYLVESTRIS.full_name


def test_volume_connector_handles_empty_ledgers() -> None:
    """When no removals are present an empty descriptor is returned."""

    ledger = StandRemovalLedger()
    connector = VolumeConnector()
    result = connector.connect(object(), ledger)

    assert result.total_value == 0.0
    assert result.pieces == ()
    assert result.metadata.get("reason") == "empty"


def test_volume_connector_and_stage_produce_cash_flows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bucking conversion integrates with the valuation stage."""

    monkeypatch.setattr(
        Pricelist,
        "getPulpWoodWasteProportion",
        lambda self, species: 0.0,
        raising=False,
    )
    monkeypatch.setattr(
        Pricelist,
        "getPulpwoodFuelwoodProportion",
        lambda self, species: 0.0,
        raising=False,
    )

    ledger = StandRemovalLedger("stand-valuation")
    tree = Tree(species=PINUS_SYLVESTRIS, diameter_cm=15.0, height_m=6.0, weight_n=1.0)
    ledger.record_tree("thin-2024", tree, metadata={"stump_height_m": 0.0})

    class DummyView:
        removal_ledger = ledger
        pricelist = _make_pricelist()
        taper_class = ConstantTaper
        bucking_config = BuckingConfig(use_downgrading=True, save_sections=True)
        min_diam_dead_wood = 16

    view = DummyView()
    connector = VolumeConnector()
    expected = connector.connect(view, ledger)

    assert expected.total_value > 0.0
    assert len(expected.pieces) == 1
    piece = expected.pieces[0]
    assert piece.quality == QualityType.ButtLog
    assert piece.volume_m3 == pytest.approx(0.10603, rel=1e-4)
    assert piece.value == pytest.approx(expected.total_value, rel=1e-6)
    assert expected.volume_by_quality[QualityType.ButtLog] == pytest.approx(0.10603, rel=1e-4)

    part = StandPart("north", model_view=view, context={"cash": 1.0})
    composite = StandComposite([part])
    module = GrowthModule(composite)

    module.run_cycle()

    valuation_ctx = part.context["valuation"]
    assert valuation_ctx["total_value"] == pytest.approx(expected.total_value, rel=1e-6)
    assert valuation_ctx["pieces"][0].volume_m3 == pytest.approx(piece.volume_m3, rel=1e-6)
    assert part.context["cash"] == pytest.approx(1.0 + expected.total_value, rel=1e-6)
