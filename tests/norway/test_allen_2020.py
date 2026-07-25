import math

import pytest

from pyforestry.base.helpers import CircularPlot, Stand, Tree, TreeSpecies
from pyforestry.base.helpers.primitives import Age
from pyforestry.norway.blocks.allen_2020 import (
    Allen2020Config,
    Allen2020GrowthModel,
    Allen2020Model,
)
from pyforestry.norway.growth.allen_2020 import (
    allen_2020_basal_area,
    allen_2020_basal_area_after_thinning_ratio,
    allen_2020_dominant_height,
    allen_2020_quadratic_mean_diameter,
    allen_2020_site_index,
    allen_2020_stand_volume,
    allen_2020_stem_survival,
    allen_2020_stems_after_thinning_ratio,
)


def _hd(h1, a1, a2):
    """Reference dominant-height projection, Allen (2020) Eq. 4, exponent (b2+b3)/X0."""
    b1, b2, b3 = 0.01605, 0.61208, 4.43722
    lg = math.log(1.0 - math.exp(-b1 * a1))
    base = math.log(h1) + b2 * lg
    x0 = 0.5 * (base + math.sqrt(base * base - 4.0 * b3 * lg))
    ratio = (1.0 - math.exp(-b1 * a2)) / (1.0 - math.exp(-b1 * a1))
    return h1 * ratio ** ((b2 + b3) / x0)


def test_dominant_height_matches_published_equation():
    """Pin Allen (2020) Eq. 4 with the published exponent (b2+b3)/X0 (as in sprucesim)."""
    h2 = allen_2020_dominant_height(12.0, Age.TOTAL(40), Age.TOTAL(60))
    assert h2 == pytest.approx(_hd(12.0, 40.0, 60.0), rel=1e-12)
    assert h2 > 12.0  # height increases with age
    # Monotonic in age.
    assert allen_2020_dominant_height(12.0, Age.TOTAL(40), Age.TOTAL(80)) > h2
    # A2 == A1 returns the input unchanged.
    assert allen_2020_dominant_height(12.0, Age.TOTAL(40), Age.TOTAL(40)) == pytest.approx(12.0)


def test_site_index_at_base_age_40():
    """Site index is dominant height projected to base age 40 (Eq. 4)."""
    si = allen_2020_site_index(17.0, Age.TOTAL(50))
    assert float(si) == pytest.approx(_hd(17.0, 50.0, 40.0), rel=1e-12)
    assert float(si.reference_age) == 40.0
    assert TreeSpecies.Norway.picea_abies in si.species


def test_stem_survival_matches_equation_and_responds_to_site_and_thinning():
    b1, b2, b3, b4, b5 = -1.0085, 0.03675, 3.76228, 2.55410, -1.0097
    n1, a1, a2, si = 1200.0, 40.0, 60.0, 17.0
    bracket = n1**b1 + b2 * 1.0 * (si / 1000.0) ** b3 * (a2**b4 - a1**b4)
    expected = bracket ** (1.0 / b5)

    n2 = allen_2020_stem_survival(n1, Age.TOTAL(a1), Age.TOTAL(a2), si)
    assert float(n2) == pytest.approx(expected, rel=1e-12)
    assert float(n2) < n1  # trees die over time

    # More productive sites have higher mortality (lower survival).
    n2_poor = float(allen_2020_stem_survival(n1, Age.TOTAL(a1), Age.TOTAL(a2), 10.0))
    n2_rich = float(allen_2020_stem_survival(n1, Age.TOTAL(a1), Age.TOTAL(a2), 24.0))
    assert n2_rich < n2_poor

    # Thinning (GA/GB < 1) reduces the mortality term -> more survivors than unthinned.
    n2_thin = float(
        allen_2020_stem_survival(n1, Age.TOTAL(a1), Age.TOTAL(a2), si, thinning_quotient=0.6)
    )
    assert n2_thin > float(n2)


def test_basal_area_matches_equation_with_and_without_thinning_response():
    b1, b2, b3 = 4.77696, 0.30957, -0.1479
    g1, h1, h2, n1, n2 = 25.0, 15.0, 20.0, 1200.0, 1050.0
    ratio_h, ratio_n = h1 / h2, n2 / n1
    core = g1**ratio_h * math.exp(b1 * (1.0 - ratio_h) * ratio_n**b2)

    g2 = allen_2020_basal_area(g1, Age.TOTAL(40), Age.TOTAL(60), h1, h2, n1, n2)
    assert float(g2) == pytest.approx(core, rel=1e-12)  # unthinned -> TR = 1

    # Thinned: TR = (GA/GB)^(b3 * HT/H2); with b3 < 0 and GA/GB < 1, TR > 1 (growth boost).
    # Eq. (2) places TR INSIDE the exp, scaling the exponent -- not as a factor on G2.
    tq, ht = 0.7, 15.0
    tr = tq ** (b3 * (ht / h2))
    expected_thin = g1**ratio_h * math.exp(b1 * ratio_n**b2 * (1.0 - ratio_h) * tr)
    g2_thin = allen_2020_basal_area(
        g1,
        Age.TOTAL(40),
        Age.TOTAL(60),
        h1,
        h2,
        n1,
        n2,
        thinning_quotient=tq,
        height_at_thinning=ht,
    )
    assert float(g2_thin) == pytest.approx(expected_thin, rel=1e-12)
    assert float(g2_thin) > float(g2)  # TR > 1 boosts growth
    # Regression guard against the old outside-exp placement (core * tr), which is
    # numerically distinct from the correct inside-exp form.
    assert float(g2_thin) != pytest.approx(core * tr, rel=1e-6)


def test_stand_volume_matches_equation_and_monotonicity():
    b1, b2, b3, b4 = 0.24961, 1.15036, 1.01153, 2.320398
    g2, h2, a2 = 30.0, 20.0, 60.0
    expected = b1 * g2**b2 * h2**b3 * math.exp(b4 / a2)
    v = allen_2020_stand_volume(g2, h2, Age.TOTAL(a2))
    assert float(v) == pytest.approx(expected, rel=1e-12)
    assert float(allen_2020_stand_volume(35.0, h2, Age.TOTAL(a2))) > float(v)  # rises with G
    assert float(allen_2020_stand_volume(g2, 25.0, Age.TOTAL(a2))) > float(v)  # rises with H


def test_quadratic_mean_diameter_and_thinning_ratio_inverse():
    assert float(allen_2020_quadratic_mean_diameter(30.0, 1000.0)) == pytest.approx(
        200.0 * math.sqrt(30.0 / (math.pi * 1000.0))
    )
    assert float(allen_2020_quadratic_mean_diameter(30.0, 0.0)) == 0.0

    # Eq. 5b is the algebraic inverse of Eq. 5a.
    na_nb = allen_2020_stems_after_thinning_ratio(0.65)
    assert allen_2020_basal_area_after_thinning_ratio(na_nb) == pytest.approx(0.65, rel=1e-9)


def _spruce_stand() -> Stand:
    return Stand(
        plots=[
            CircularPlot(
                id="p1",
                area_m2=1000.0,
                trees=[
                    Tree(species=TreeSpecies.Norway.picea_abies, diameter_cm=18.0, weight_n=90.0),
                    Tree(species=TreeSpecies.Norway.picea_abies, diameter_cm=22.0, weight_n=60.0),
                ],
            )
        ]
    )


def test_allen_growth_model_adapter_advances_state():
    adapter = Allen2020GrowthModel(
        Allen2020Config(h40_m=17.0, dominant_height_m=14.0, start_total_age_years=40.0)
    )
    ctx = adapter.build_context(_spruce_stand())
    stems_before = float(ctx.metrics["Stems"]["TOTAL"])
    ba_before = float(ctx.metrics["BasalArea"]["TOTAL"])

    adapter.update_step(ctx, dt=5.0)

    assert float(ctx.state["t"]) == pytest.approx(45.0)
    assert float(ctx.attrs["dominant_height_m"]) > 14.0  # height grew
    assert float(ctx.metrics["Stems"]["TOTAL"]) <= stems_before  # survival <= start
    assert float(ctx.metrics["BasalArea"]["TOTAL"]) >= ba_before  # BA grew
    assert ctx.attrs["stand_volume_m3_per_ha"] > 0.0
    assert ctx.attrs["quadratic_mean_diameter_cm"] > 0.0

    with pytest.raises(ValueError):
        adapter.update_step(ctx, dt=0.0)


def test_allen_model_facade():
    h2 = Allen2020Model.dominant_height(12.0, Age.TOTAL(40), Age.TOTAL(60))
    assert h2 > 12.0
    si = Allen2020Model.site_index(17.0, Age.TOTAL(50))
    assert float(si.reference_age) == 40.0
    assert float(Allen2020Model.stem_survival(1000.0, Age.TOTAL(40), Age.TOTAL(60), si)) < 1000.0
    assert float(Allen2020Model.stand_volume(30.0, 20.0, Age.TOTAL(60))) > 0.0
