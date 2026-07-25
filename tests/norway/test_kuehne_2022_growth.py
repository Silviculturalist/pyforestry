import math

import pytest

from pyforestry.base.helpers import CircularPlot, Stand, Tree, TreeSpecies
from pyforestry.base.helpers.primitives import Age
from pyforestry.norway.blocks.kuehne_2022 import KuehnePineAdapterConfig, KuehnePineGrowthModel
from pyforestry.norway.growth.kuehne_2022 import (
    kuehne_2022_basal_area,
    kuehne_2022_basal_area_after_thinning_ratio,
    kuehne_2022_stand_volume,
    kuehne_2022_stem_density,
    kuehne_2022_stems_after_thinning_ratio,
)


def test_stem_density_matches_eq6_power_form():
    """Pin Kuehne Eq. 6; note it uses AGE2^b4 - AGE1^b4 (power), not forester's linear form."""
    b1, b2, b3, b4 = -1.56856, 0.00284, 4.14779, 4.87715
    n1, a1, a2, si40 = 2000.0, 40.0, 60.0, 11.0
    expected = (n1**b1 + b2 * 1.0 * (si40 / 10000.0) ** b3 * (a2**b4 - a1**b4)) ** (1.0 / b1)

    n2 = kuehne_2022_stem_density(n1, Age.TOTAL(a1), Age.TOTAL(a2), si40)
    assert float(n2) == pytest.approx(expected, rel=1e-12)
    assert float(n2) < n1  # competition mortality (the power form must give real mortality)

    # Thinning reduces competition mortality -> more survivors.
    n2_thin = float(
        kuehne_2022_stem_density(n1, Age.TOTAL(a1), Age.TOTAL(a2), si40, thinning_quotient=0.7)
    )
    assert n2_thin > float(n2)


def test_basal_area_matches_eq7():
    b1, b2, b3, b4 = 1.46553, 0.52449, 0.17701, 16.53755  # b5 term is 0 when unthinned
    g1, h1, h2, n1, n2, a1, a2 = 20.0, 12.0, 16.0, 2000.0, 1890.0, 40.0, 60.0
    ra = a1 / a2
    expected = math.exp(
        ra * math.log(g1)
        + b1 * (1.0 - ra)
        + b2 * (math.log(h2) - ra * math.log(h1))
        + b3 * (math.log(n2) - ra * math.log(n1))
        + b4 * ((math.log(n2) - math.log(n1)) / a2)
    )
    g2 = kuehne_2022_basal_area(g1, Age.TOTAL(a1), Age.TOTAL(a2), h1, h2, n1, n2)
    assert float(g2) == pytest.approx(expected, rel=1e-12)  # unthinned -> b5 term = 0

    # Thinning increases basal-area growth (as reported in the paper).
    g2_thin = float(
        kuehne_2022_basal_area(
            g1,
            Age.TOTAL(a1),
            Age.TOTAL(a2),
            h1,
            h2,
            n1,
            n2,
            thinning_quotient=0.75,
            age_thin=45.0,
        )
    )
    assert g2_thin > float(g2)


def test_volume_matches_eq8_and_monotonicity():
    b1, b2, b3, b4 = 0.65394, 0.96928, 0.91504, -2.05278
    g2, h2, a2 = 30.0, 16.0, 60.0
    expected = b1 * g2**b2 * h2**b3 * math.exp(b4 / a2)
    v = kuehne_2022_stand_volume(g2, h2, Age.TOTAL(a2))
    assert float(v) == pytest.approx(expected, rel=1e-12)  # unthinned -> factor = 1
    assert float(kuehne_2022_stand_volume(35.0, h2, Age.TOTAL(a2))) > float(v)
    assert float(kuehne_2022_stand_volume(g2, 20.0, Age.TOTAL(a2))) > float(v)


def test_thinning_reduction_eq9_and_inverse_eq10():
    # Eq. 9: TPH_after/TPH_before = exp(b1 + b2 * BA_after/BA_before)
    ratio = kuehne_2022_stems_after_thinning_ratio(0.75)
    assert ratio == pytest.approx(math.exp(-1.91239 + 1.94414 * 0.75), rel=1e-12)
    # Eq. 10 is the exact inverse of Eq. 9.
    assert kuehne_2022_basal_area_after_thinning_ratio(ratio) == pytest.approx(0.75, rel=1e-9)


def test_kuehne_growth_model_adapter_projects_full_stand():
    stand = Stand(
        plots=[
            CircularPlot(
                id="p1",
                area_m2=1000.0,
                trees=[
                    Tree(
                        species=TreeSpecies.Norway.pinus_sylvestris,
                        diameter_cm=16.0,
                        weight_n=120.0,
                    ),
                    Tree(
                        species=TreeSpecies.Norway.pinus_sylvestris,
                        diameter_cm=20.0,
                        weight_n=80.0,
                    ),
                ],
            )
        ]
    )
    adapter = KuehnePineGrowthModel(
        KuehnePineAdapterConfig(dominant_height_m=12.0, start_total_age_years=40.0)
    )
    ctx = adapter.build_context(stand)
    stems_before = float(ctx.metrics["Stems"]["TOTAL"])
    ba_before = float(ctx.metrics["BasalArea"]["TOTAL"])

    adapter.update_step(ctx, dt=5.0)

    assert float(ctx.state["t"]) == pytest.approx(45.0)
    assert float(ctx.attrs["kuehne_dominant_height_m"]) > 12.0
    assert ctx.attrs["kuehne_site_index_si40_m"] > 0.0
    assert float(ctx.metrics["Stems"]["TOTAL"]) <= stems_before
    assert float(ctx.metrics["BasalArea"]["TOTAL"]) >= ba_before
    assert ctx.attrs["stand_volume_m3_per_ha"] > 0.0
