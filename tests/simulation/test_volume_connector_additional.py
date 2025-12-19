from __future__ import annotations

import pytest

from pyforestry.base.helpers import Tree
from pyforestry.base.helpers.bucking import BuckingConfig, QualityType
from pyforestry.base.pricelist import Pricelist
from pyforestry.base.taper import Taper
from pyforestry.simulation.valuation.removals import StandRemovalLedger
from pyforestry.simulation.valuation.volume import (
    EmptyVolumeDescriptor,
    PieceRecord,
    TreeVolumeDescriptor,
    VolumeConnector,
    VolumeResult,
)


class DummyPricelist(Pricelist):
    pass


class DummyTaper(Taper):
    pass


class DummyBucker:
    def __init__(self, timber, pricelist, taper_class):  # noqa: ARG002
        pass

    def calculate_tree_value(self, min_diam_dead_wood, config):  # noqa: ARG002
        class Result:
            total_value = 10.0
            volume_per_quality = [1.0, 2.0, 3.0, 4.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            sections = []
            vol_sk_ub = 5.0

        return Result()


def _ledger_with_tree():
    ledger = StandRemovalLedger(stand_id="stand-1")
    tree = Tree(species="picea abies", diameter_cm=20.0, height_m=15.0, weight_n=1.0)
    ledger.record_tree("cohort-1", tree, species="picea abies")
    return ledger


def test_piece_record_and_volume_result_helpers():
    piece = PieceRecord(
        cohort_id="c1",
        species="picea abies",
        quality=QualityType.Undefined,
        length_m=1.0,
        top_diameter_cm=10.0,
        volume_m3=0.2,
        value=5.0,
        weight=1.0,
    )
    mapping = piece.as_mapping()
    assert mapping["quality"] == "Undefined"
    result = VolumeResult(
        descriptor=EmptyVolumeDescriptor(ledger=StandRemovalLedger()),
        pieces=(piece,),
        total_value=5.0,
        volume_by_quality={QualityType.Undefined: 0.2},
    )
    assert result.total_volume == pytest.approx(0.2)


def test_tree_volume_descriptor_empty_and_config_checks():
    empty_ledger = StandRemovalLedger()
    descriptor = TreeVolumeDescriptor(
        ledger=empty_ledger,
        removals=(),
        pricelist=DummyPricelist(),
        taper_class=DummyTaper,
    )
    result = descriptor.evaluate()
    assert result.pieces == ()

    ledger = _ledger_with_tree()
    removals = tuple(ledger.iter_tree_removals())
    with pytest.raises(TypeError):
        TreeVolumeDescriptor(
            ledger=ledger,
            removals=removals,
            pricelist=DummyPricelist(),
            taper_class=DummyTaper,
            bucking_config="bad",
            bucker_cls=DummyBucker,
        ).evaluate()

    descriptor = TreeVolumeDescriptor(
        ledger=ledger,
        removals=removals,
        pricelist=DummyPricelist(),
        taper_class=DummyTaper,
        bucking_config=BuckingConfig(save_sections=False),
        bucker_cls=DummyBucker,
    )
    result = descriptor.evaluate()
    assert result.pieces


def test_tree_volume_descriptor_fallback_piece_and_quality():
    ledger = _ledger_with_tree()
    removals = tuple(ledger.iter_tree_removals())
    descriptor = TreeVolumeDescriptor(
        ledger=ledger,
        removals=removals,
        pricelist=DummyPricelist(),
        taper_class=DummyTaper,
        bucker_cls=DummyBucker,
    )
    result = descriptor.evaluate()
    assert result.pieces
    assert result.volume_by_quality[QualityType.Undefined] >= 0.0


def test_volume_connector_resolution_errors():
    connector = VolumeConnector(bucker_cls=DummyBucker)

    with pytest.raises(TypeError):
        connector.describe(object(), "bad")

    class NoPricelist:
        pass

    with pytest.raises(AttributeError):
        connector.describe(NoPricelist(), _ledger_with_tree())

    class BadTaper:
        pricelist = DummyPricelist()
        taper_class = lambda self: None  # noqa: E731 - test hook

    with pytest.raises(AttributeError):
        connector.describe(BadTaper(), _ledger_with_tree())

    class BadBucking:
        pricelist = DummyPricelist()
        taper_class = DummyTaper
        bucking_config = "bad"

    with pytest.raises(TypeError):
        connector.describe(BadBucking(), _ledger_with_tree())

    class CallableBucking:
        pricelist = DummyPricelist()

        def taper_class(self):
            return DummyTaper

        def bucking_config(self):
            return None

    descriptor = connector.describe(CallableBucking(), _ledger_with_tree())
    assert isinstance(descriptor, TreeVolumeDescriptor)


def test_volume_connector_resolve_helpers():
    class PricelistCallable:
        def pricelist(self):
            return DummyPricelist()

    class PricelistAlias:
        price_list = DummyPricelist()

    assert isinstance(VolumeConnector._resolve_pricelist(PricelistCallable()), Pricelist)
    assert isinstance(VolumeConnector._resolve_pricelist(PricelistAlias()), Pricelist)

    class TaperCallable:
        def taper_class(self):
            return DummyTaper

    class TaperGetter:
        taper_class = None

        def get_taper_class(self):
            return DummyTaper

    assert VolumeConnector._resolve_taper_class(TaperCallable()) is DummyTaper
    assert VolumeConnector._resolve_taper_class(TaperGetter()) is DummyTaper

    class BuckingCallable:
        def bucking_config(self):
            return None

    class BuckingConfigValue:
        bucking_config = BuckingConfig(save_sections=False)

    config = VolumeConnector._resolve_bucking_config(BuckingCallable())
    assert isinstance(config, BuckingConfig)
    assert config.save_sections is True
    assert VolumeConnector._resolve_bucking_config(BuckingConfigValue()).save_sections is True
