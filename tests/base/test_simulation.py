from dataclasses import dataclass

from pyforestry.base.helpers import Stand, TreeSpecies
from pyforestry.base.simulation import (
    CalamityModule,
    GrowthModule,
    IngrowthModule,
    MortalityModule,
    SimulationRuleset,
)


@dataclass
class DummyGrowth(GrowthModule):
    def apply(self, stand: Stand) -> None:
        stand.attrs.setdefault("order", []).append("growth")


@dataclass
class DummyIngrowth(IngrowthModule):
    def apply(self, stand: Stand) -> None:
        stand.attrs.setdefault("order", []).append("ingrowth")


@dataclass
class DummyMortality(MortalityModule):
    def apply(self, stand: Stand) -> None:
        stand.attrs.setdefault("order", []).append("mortality")


@dataclass
class DummyCalamity(CalamityModule):
    def apply(self, stand: Stand) -> None:
        stand.attrs.setdefault("order", []).append("calamity")


@dataclass
class DummyRuleset(SimulationRuleset):
    def grow(self, stand: Stand) -> None:
        self.growth.apply(stand)
        self.ingrowth.apply(stand)
        self.mortality.apply(stand)
        if self.calamity:
            self.calamity.apply(stand)


def test_supports_method() -> None:
    sp = TreeSpecies.Sweden.picea_abies

    class Module(DummyGrowth):
        pass

    m = Module(supported_species=[sp])
    assert m.supports(sp)
    assert not m.supports(TreeSpecies.Sweden.pinus_sylvestris)


def test_ruleset_grow_order_without_calamity() -> None:
    stand = Stand()
    ruleset = DummyRuleset(DummyGrowth(), DummyIngrowth(), DummyMortality())
    ruleset.grow(stand)
    assert stand.attrs["order"] == ["growth", "ingrowth", "mortality"]


def test_ruleset_grow_order_with_calamity() -> None:
    stand = Stand()
    ruleset = DummyRuleset(DummyGrowth(), DummyIngrowth(), DummyMortality(), DummyCalamity())
    ruleset.grow(stand)
    assert stand.attrs["order"] == [
        "growth",
        "ingrowth",
        "mortality",
        "calamity",
    ]
