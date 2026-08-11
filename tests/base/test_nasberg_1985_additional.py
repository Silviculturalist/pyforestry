import numpy as np
import pytest

from pyforestry.base.pricelist.pricelist import (
    LengthRange,
    Pricelist,
    TimberPriceForDiameter,
    TimberPricelist,
)
from pyforestry.base.taper.taper import Taper
from pyforestry.base.timber.timber_base import Timber
from pyforestry.base.timber_bucking import nasberg_1985
from pyforestry.base.timber_bucking.nasberg_1985 import (
    BuckingConfig,
    BuckingResult,
    Nasberg_1985_BranchBound,
    QualityType,
)


class ConstantTaper(Taper):
    """Very simple taper model returning constant diameters."""

    def __init__(self, timber: Timber):
        super().__init__(timber, self)

    def get_diameter_at_height(self, height_m: float) -> float:  # type: ignore[override]
        return 10

    def get_height_at_diameter(self, diameter: float) -> float:  # type: ignore[override]
        return 0

    def volume_section(self, h1_m: float, h2_m: float) -> float:  # type: ignore[override]
        return 0.0


class SimpleTaper(Taper):
    """Taper returning a fixed diameter and height."""

    def __init__(self, timber: Timber, diameter: float, height_at_diam: float):
        self.diameter = diameter
        self.had = height_at_diam
        super().__init__(timber, self)

    def get_diameter_at_height(self, height_m: float) -> float:  # type: ignore[override]
        return self.diameter

    def get_height_at_diameter(self, diameter: float) -> float:  # type: ignore[override]
        return self.had

    def volume_section(self, h1_m: float, h2_m: float) -> float:  # type: ignore[override]
        return max(0.0, h2_m - h1_m)


def make_pricelist(min_len: float = 1.0) -> Pricelist:
    """Create a minimal pricelist for tests."""
    pl = Pricelist()
    tp = TimberPricelist(min_diameter=10, max_diameter=10)
    tp.set_price_for_diameter(10, TimberPriceForDiameter(2, 3, 4))
    pl.Timber["pine"] = tp
    pl.PulpLogLength = LengthRange(min_len, 2.0)
    pl.TimberLogLength = LengthRange(min_len, 2.0)
    return pl


def test_init_requires_pricelist():
    t = Timber("pine", 10, 5)
    with pytest.raises(ValueError, match="Pricelist must be set"):
        Nasberg_1985_BranchBound(t, None, ConstantTaper)  # type: ignore[arg-type]


def test_init_missing_species_prices():
    t = Timber("pine", 10, 5)
    pl = Pricelist()  # no Timber entry
    with pytest.raises(ValueError, match="No prices for pine"):
        Nasberg_1985_BranchBound(t, pl, ConstantTaper)


def test_init_min_length_validation():
    t = Timber("pine", 10, 5)
    pl = make_pricelist(min_len=0.5)
    with pytest.raises(ValueError, match="Minimum log length"):
        Nasberg_1985_BranchBound(t, pl, ConstantTaper)


def test_build_value_table():
    t = Timber("pine", 10, 5)
    pl = make_pricelist()
    nb = Nasberg_1985_BranchBound(t, pl, ConstantTaper)
    # only one diameter and one module -> index 0
    tv = nb._timberValue
    assert tv.shape[0] >= 11
    # expected prices with volume factor for m3to
    vf = np.pi * ((10 / 100) * 0.5) ** 2 * (10 / 10)
    assert tv[10, 0, 1] == pytest.approx(2 * 100 * vf)
    assert tv[10, 0, 2] == pytest.approx(3 * 100 * vf)
    assert tv[10, 0, 3] == pytest.approx(4 * 100 * vf)


def test_build_value_table_no_prices():
    """_build_value_table should handle missing price tables."""
    t = Timber("pine", 10, 5)
    pl = make_pricelist()
    nb = Nasberg_1985_BranchBound(t, pl, ConstantTaper)
    nb._timber_prices = None  # type: ignore[assignment]
    tv = nb._build_value_table()
    assert tv.shape[0] >= 11
    assert np.all(tv == 0)


def _make_pl(min_diam: int, volume_type: str = "m3fub") -> Pricelist:
    pl = Pricelist()
    tp = TimberPricelist(min_diam, min_diam, volume_type=volume_type)
    tp.set_price_for_diameter(min_diam, TimberPriceForDiameter(5, 5, 5))
    pl.Timber["pine"] = tp
    pl.PulpLogLength = LengthRange(1.0, 2.0)
    pl.TimberLogLength = LengthRange(1.0, 2.0)
    return pl


class Weights:
    pulpwoodPercentage = 40.0
    fuelWoodPercentage = 40.0
    logCullPercentage = 40.0


def test_calculate_tree_value_branches(monkeypatch):
    t = Timber("pine", 15, 6, stump_height_m=0)

    # Override the pulp downgrade proportions (which now exist on Pricelist and
    # default to 0.0) to exercise the waste+fuel>1 clamp. monkeypatch auto-restores
    # so the override does not leak into later tests.
    monkeypatch.setattr(
        Pricelist, "get_pulpwood_waste_proportion", lambda self, s: 0.7, raising=False
    )
    monkeypatch.setattr(
        Pricelist, "get_pulpwood_fuelwood_proportion", lambda self, s: 0.6, raising=False
    )

    # Timber branch with downgrading
    pl = _make_pl(10)
    nb = Nasberg_1985_BranchBound(t, pl, lambda timber: SimpleTaper(timber, 15, t.height_m))
    monkeypatch.setattr(nb._timber_prices, "get_timber_weight", lambda part: Weights())
    res1 = nb.calculate_tree_value(
        min_diam_dead_wood=9, config=BuckingConfig(use_downgrading=True, save_sections=True)
    )
    assert res1.volume_per_quality[0] >= 0

    # Pulp branch with downgrading
    pl2 = _make_pl(20)
    nb2 = Nasberg_1985_BranchBound(t, pl2, lambda timber: SimpleTaper(timber, 15, t.height_m))
    monkeypatch.setattr(nb2._timber_prices, "get_timber_weight", lambda part: Weights())
    res2 = nb2.calculate_tree_value(
        min_diam_dead_wood=9, config=BuckingConfig(use_downgrading=True)
    )
    assert res2.volume_per_quality[QualityType.Pulp.value] >= 0

    # Cull branch
    nb3 = Nasberg_1985_BranchBound(t, pl2, lambda timber: SimpleTaper(timber, 4, t.height_m))
    res3 = nb3.calculate_tree_value(min_diam_dead_wood=9)
    assert res3.volume_per_quality[QualityType.LogCull.value] >= 0


def test_calculate_tree_value_short_tree():
    """Degenerate (too-short) stem hits the ``total_dm <= 0`` guard.

    Regression: that guard used to build ``BuckingResult`` with only 10 of its 17
    required fields (passed positionally), so it raised ``TypeError`` on every
    degenerate stem. It must instead return a well-formed zero result. (The old test
    masked this by monkeypatching ``BuckingResult`` to a no-op lambda.)
    """

    class ZeroHeightTaper(ConstantTaper):
        def get_height_at_diameter(self, diameter: float) -> float:  # type: ignore[override]
            return 0

    t = Timber("pine", 10, 5)
    pl = make_pricelist()
    nb = Nasberg_1985_BranchBound(t, pl, ZeroHeightTaper)

    res = nb.calculate_tree_value(min_diam_dead_wood=9)

    assert isinstance(res, BuckingResult)
    assert res.total_value == 0
    assert res.species_group == "pine"
    assert res.volume_per_quality == [0.0] * len(QualityType)
    assert res.timber_price_by_quality == [0.0] * len(QualityType)
    # taper arrays are not built before this guard -> empty, and no sections
    assert res.taper_diameters_cm == []
    assert res.taper_heights_m == []
    assert res.sections is None
    # geometry known at the guard is carried through, not zeroed
    assert res.height_m == 5
    assert res.dbh_cm == pytest.approx(10)


def test_calculate_tree_value_no_profit_guard(monkeypatch):
    """The ``best <= 0`` fallback (no profitable endpoint) must also return a
    well-formed zero result carrying the stem geometry, not raise ``TypeError``.

    ``v[0]`` is seeded to 1e-5 so this branch is effectively unreachable in normal
    use; force ``argmax`` onto index 1 (below the shortest module, so it is never
    updated and stays ``-inf``) to drive ``best <= 0`` and exercise the guard.
    """
    t = Timber("pine", 20, 6, stump_height_m=0)
    pl = _make_pl(15)
    nb = Nasberg_1985_BranchBound(t, pl, lambda timber: SimpleTaper(timber, 15, t.height_m))
    monkeypatch.setattr(nasberg_1985.np, "argmax", lambda arr: 1)

    res = nb.calculate_tree_value(min_diam_dead_wood=9)

    assert isinstance(res, BuckingResult)
    assert res.total_value == 0
    assert res.species_group == "pine"
    assert res.volume_per_quality == [0.0] * len(QualityType)
    # the full stem geometry is known at this guard and is carried through
    assert res.height_m == 6
    assert res.vol_sk_ub > 0
    assert len(res.taper_diameters_cm) > 0


def test_pricelist_pulp_downgrade_hooks_present():
    """The pulp branch calls these on ``Pricelist``; they must exist in production
    (previously only monkeypatched onto the class by tests) and default to no
    downgrade (0.0)."""
    pl = Pricelist()
    assert pl.get_pulpwood_waste_proportion("pine") == 0.0
    assert pl.get_pulpwood_fuelwood_proportion("pine") == 0.0


def test_pulp_downgrading_without_monkeypatch_does_not_crash():
    """``use_downgrading=True`` on a pulp-producing stem must not raise.

    Regression: the pulp branch called ``Pricelist.get_pulpwood_waste_proportion`` /
    ``get_pulpwood_fuelwood_proportion``, which existed nowhere in production, so any
    real caller enabling downgrading hit ``AttributeError``. Uses the real (0.0)
    hooks - no monkeypatching.
    """
    t = Timber("pine", 15, 6, stump_height_m=0)
    pl = _make_pl(20)  # min timber diameter 20 -> 15 cm logs are pulp, not timber
    nb = Nasberg_1985_BranchBound(t, pl, lambda timber: SimpleTaper(timber, 15, t.height_m))

    res = nb.calculate_tree_value(min_diam_dead_wood=9, config=BuckingConfig(use_downgrading=True))

    assert isinstance(res, BuckingResult)
    assert res.total_value >= 0
    assert res.volume_per_quality[QualityType.Pulp.value] >= 0
