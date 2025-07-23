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
from pyforestry.base.timber_bucking.nasberg_1985 import Nasberg_1985_BranchBound


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
