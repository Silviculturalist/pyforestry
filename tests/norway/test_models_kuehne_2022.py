import pytest

from pyforestry.base.helpers import CircularPlot, Stand, Tree, TreeSpecies
from pyforestry.base.helpers.primitives import Age
from pyforestry.norway.adapters import (
    KuehnePineAdapterConfig,
    KuehnePineGrowthModel,
    KuehnePineModel,
)
from pyforestry.norway.adapters.kuehne_2022 import (
    kuehne_2022_height_trajectory_and_si_scots_pine_norway,
)


def test_kuehne_model_thin_api():
    direct = kuehne_2022_height_trajectory_and_si_scots_pine_norway(
        18.0,
        Age.TOTAL(40),
        Age.TOTAL(60),
        output="height",
    )
    via_model = KuehnePineModel.height_trajectory_and_si(
        18.0,
        Age.TOTAL(40),
        Age.TOTAL(60),
        output="height",
    )
    assert float(direct) == float(via_model)


def test_kuehne_growth_model_adapter():
    stand = Stand(
        plots=[
            CircularPlot(
                id="p1",
                area_m2=400.0,
                trees=[
                    Tree(
                        species=TreeSpecies.Norway.pinus_sylvestris,
                        diameter_cm=18.0,
                        weight_n=90.0,
                    )
                ],
            )
        ]
    )
    model = KuehnePineGrowthModel(
        KuehnePineAdapterConfig(dominant_height_m=14.0, start_total_age_years=25.0)
    )
    ctx = model.build_context(stand)
    model.update_step(ctx, dt=5.0)

    assert float(ctx.state["t"]) == pytest.approx(30.0)
    assert float(ctx.attrs["kuehne_dominant_height_m"]) > 0.0
    assert float(ctx.attrs["kuehne_site_index_h100_m"]) > 0.0
