"""Tests covering removal ledgers and volume conversion utilities."""

from __future__ import annotations

from math import pi
from types import SimpleNamespace

import pytest

from pyforestry.base.helpers import CircularPlot, Stand, Tree
from pyforestry.base.helpers.tree_species import PINUS_SYLVESTRIS
from pyforestry.base.pricelist.pricelist import (
    LengthRange,
    Pricelist,
    TimberPriceForDiameter,
    TimberPricelist,
)
from pyforestry.base.simulation import run_pipeline
from pyforestry.base.simulation.growth_model import ExampleStandGeneralModel
from pyforestry.base.taper.taper import Taper
from pyforestry.base.timber.timber_base import Timber
from pyforestry.base.timber_bucking.nasberg_1985 import BuckingConfig, QualityType
from pyforestry.simulation.valuation import (
    PieceRecord,
    StandRemovalLedger,
    TreeVolumeDescriptor,
    ValuationSettings,
    ValuationStep,
    VolumeConnector,
    VolumeResult,
)


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


def _make_settings(**overrides) -> ValuationSettings:
    kwargs = {
        "pricelist": _make_pricelist(),
        "taper_class": ConstantTaper,
        "bucking_config": BuckingConfig(use_downgrading=True, save_sections=True),
        "min_diam_dead_wood": 16.0,
    }
    kwargs.update(overrides)
    return ValuationSettings(**kwargs)


def test_volume_connector_handles_empty_ledgers() -> None:
    """When no removals are present an empty descriptor is returned.

    An empty ledger short-circuits before the settings are looked at, so nothing
    has to be supplied to price nothing.
    """

    ledger = StandRemovalLedger()
    connector = VolumeConnector()
    result = connector.connect(None, ledger)

    assert result.total_value == 0.0
    assert result.pieces == ()
    assert result.metadata.get("reason") == "empty"


def test_volume_connector_and_step_produce_cash_flows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bucking conversion integrates with the valuation step.

    This is what gives ``pyforestry.simulation.valuation`` a runtime consumer: a
    pipeline that runs a :class:`ValuationStep` prices whatever the run removed.
    """

    monkeypatch.setattr(
        Pricelist,
        "get_pulpwood_waste_proportion",
        lambda self, species: 0.0,
        raising=False,
    )
    monkeypatch.setattr(
        Pricelist,
        "get_pulpwood_fuelwood_proportion",
        lambda self, species: 0.0,
        raising=False,
    )

    ledger = StandRemovalLedger("stand-valuation")
    tree = Tree(species=PINUS_SYLVESTRIS, diameter_cm=15.0, height_m=6.0, weight_n=1.0)
    ledger.record_tree("thin-2024", tree, metadata={"stump_height_m": 0.0})

    settings = _make_settings()
    connector = VolumeConnector()
    expected = connector.connect(settings, ledger)

    assert expected.total_value > 0.0
    assert len(expected.pieces) == 1
    piece = expected.pieces[0]
    assert piece.quality == QualityType.ButtLog
    assert piece.volume_m3 == pytest.approx(0.10603, rel=1e-4)
    assert piece.value == pytest.approx(expected.total_value, rel=1e-6)
    assert expected.volume_by_quality[QualityType.ButtLog] == pytest.approx(0.10603, rel=1e-4)

    stand = Stand(area_ha=1.0, plots=[CircularPlot(id=1, area_m2=10_000.0, trees=[tree])])
    ctx = ExampleStandGeneralModel().build_context(stand, mode_hint="tree_list")
    ctx.attrs["removal_ledger"] = ledger
    ctx.attrs["cash"] = 1.0

    run_pipeline(ctx, (ValuationStep(settings),), years=5.0, step=5.0)

    valuation = ctx.attrs["valuation"]
    assert valuation["total_value"] == pytest.approx(expected.total_value, rel=1e-6)
    assert valuation["pieces"][0].volume_m3 == pytest.approx(piece.volume_m3, rel=1e-6)
    assert ctx.attrs["cash"] == pytest.approx(1.0 + expected.total_value, rel=1e-6)


def test_valuation_step_does_nothing_without_a_ledger() -> None:
    """The ordinary case for a step that did not thin."""
    stand = Stand(area_ha=1.0, plots=[CircularPlot(id=1, area_m2=10_000.0, trees=[])])
    ctx = ExampleStandGeneralModel().build_context(stand, mode_hint="tree_list")
    run_pipeline(ctx, (ValuationStep(_make_settings()),), years=5.0, step=5.0)
    assert "valuation" not in ctx.attrs
    assert "cash" not in ctx.attrs


def test_valuation_step_does_nothing_for_an_empty_ledger() -> None:
    stand = Stand(area_ha=1.0, plots=[CircularPlot(id=1, area_m2=10_000.0, trees=[])])
    ctx = ExampleStandGeneralModel().build_context(stand, mode_hint="tree_list")
    ctx.attrs["removal_ledger"] = StandRemovalLedger("empty")
    run_pipeline(ctx, (ValuationStep(_make_settings()),), years=5.0, step=5.0)
    assert "valuation" not in ctx.attrs


def test_valuation_step_requires_its_settings() -> None:
    """The settings are a constructor argument, so they cannot be forgotten.

    They used to be read from ``ctx.attrs["valuation_settings"]`` with a
    documented fallback to "the context itself" -- which has no price list, so a
    run that removed anything raised ``AttributeError`` on the default path.
    """
    with pytest.raises(TypeError):
        ValuationStep()  # type: ignore[call-arg]


def test_piece_record_mapping_and_total_volume() -> None:
    piece = PieceRecord(
        cohort_id="c1",
        species=PINUS_SYLVESTRIS.full_name,
        quality=QualityType.Undefined,
        length_m=2.0,
        top_diameter_cm=10.0,
        volume_m3=0.5,
        value=2.0,
        weight=1.0,
    )
    mapping = piece.as_mapping()
    assert mapping["quality"] == "Undefined"

    result = VolumeResult(
        descriptor=SimpleNamespace(),
        pieces=(piece,),
        total_value=2.0,
        volume_by_quality={quality: 0.0 for quality in QualityType},
    )
    assert result.total_volume == pytest.approx(0.5)


def test_tree_volume_descriptor_empty_and_config_validation() -> None:
    ledger = StandRemovalLedger("stand-empty")
    descriptor = TreeVolumeDescriptor(
        ledger=ledger,
        removals=(),
        pricelist=_make_pricelist(),
        taper_class=ConstantTaper,
    )
    empty = descriptor.evaluate()
    assert empty.total_value == 0.0

    bad_descriptor = TreeVolumeDescriptor(
        ledger=ledger,
        removals=(),
        pricelist=_make_pricelist(),
        taper_class=ConstantTaper,
        bucking_config="bad",
    )
    with pytest.raises(TypeError):
        bad_descriptor.evaluate()


def test_tree_volume_descriptor_sections_fallback_and_quality_handling() -> None:
    ledger = StandRemovalLedger("stand-tree")
    tree = Tree(species=PINUS_SYLVESTRIS, diameter_cm=15.0, height_m=6.0, weight_n=1.0)
    ledger.record_tree("thin-2024", tree, metadata={"stump_height_m": 0.0})
    removals = tuple(ledger.iter_tree_removals())

    class DummyBucker:
        def __init__(self, *args, **kwargs):
            pass

        def calculate_tree_value(self, *args, **kwargs):
            volume_per_quality = [1.0 for _ in range(len(QualityType) + 1)]
            return SimpleNamespace(
                total_value=5.0,
                volume_per_quality=volume_per_quality,
                sections=[],
                vol_sk_ub=1.2,
            )

    descriptor = TreeVolumeDescriptor(
        ledger=ledger,
        removals=removals,
        pricelist=_make_pricelist(),
        taper_class=ConstantTaper,
        bucking_config=BuckingConfig(save_sections=False),
        bucker_cls=DummyBucker,
    )
    result = descriptor.evaluate()
    assert result.pieces
    assert result.pieces[0].quality == QualityType.Undefined


def test_connector_rejects_a_non_ledger() -> None:
    with pytest.raises(TypeError, match="StandRemovalLedger"):
        VolumeConnector().describe(_make_settings(), object())


def test_connector_rejects_settings_that_are_not_settings() -> None:
    """A duck that quacks is no longer enough.

    The connector used to accept any object and hunt for ``pricelist`` or
    ``price_list``, ``taper_class`` or ``get_taper_class()``, each optionally
    callable -- so an object spelling one of them a seventh way was read as
    supplying nothing at all.
    """
    ledger = StandRemovalLedger("stand-1")
    ledger.record_tree(
        "thin", Tree(species=PINUS_SYLVESTRIS, diameter_cm=15.0, height_m=6.0, weight_n=1.0)
    )

    class LooksRight:
        pricelist = _make_pricelist()
        taper_class = ConstantTaper

    with pytest.raises(TypeError, match="ValuationSettings"):
        VolumeConnector().describe(LooksRight(), ledger)


def test_settings_validate_their_fields() -> None:
    with pytest.raises(TypeError, match="pricelist"):
        ValuationSettings(pricelist=object(), taper_class=ConstantTaper)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="Taper"):
        ValuationSettings(pricelist=_make_pricelist(), taper_class=object)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="BuckingConfig"):
        ValuationSettings(
            pricelist=_make_pricelist(),
            taper_class=ConstantTaper,
            bucking_config="bad",  # type: ignore[arg-type]
        )


def test_settings_force_sections_on() -> None:
    """Piece records *are* the sections, so a config that drops them is corrected."""
    settings = ValuationSettings(
        pricelist=_make_pricelist(),
        taper_class=ConstantTaper,
        bucking_config=BuckingConfig(save_sections=False),
    )
    assert settings.bucking_config.save_sections
    assert isinstance(settings.min_diam_dead_wood, float)
