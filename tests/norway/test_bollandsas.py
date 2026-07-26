import numpy as np
import pytest

from pyforestry.base.helpers import CircularPlot, Stand, Tree, TreeSpecies
from pyforestry.base.helpers.primitives import StandBasalArea
from pyforestry.norway.adapters.bollandsas_2008 import (
    Bollandsas2008,
    Bollandsas2008AdapterConfig,
    Bollandsas2008GrowthModel,
)


def _model() -> Bollandsas2008:
    return Bollandsas2008(
        site_index_by_species={
            "spruce": 20.0,
            "pine": 18.0,
            "birch": 16.0,
            "other_broadleaves": 14.0,
        },
        latitude_deg=60.0,
    )


def test_bollandsas_constructor_validation_and_helpers():
    with pytest.raises(ValueError):
        Bollandsas2008({}, latitude_deg=60.0, n_classes=0)
    with pytest.raises(ValueError):
        Bollandsas2008({}, latitude_deg=60.0, class_width_mm=0.0)

    model = _model()
    assert model.logistic(0.0) == pytest.approx(0.5)
    assert model.logistic(2.0) > 0.5
    assert model.logistic(-2.0) < 0.5

    assert model._species_group(TreeSpecies.Sweden.picea_abies) == "spruce"
    assert model._species_group(TreeSpecies.Sweden.pinus_sylvestris) == "pine"
    assert model._species_group(TreeSpecies.Sweden.betula_pendula) == "birch"
    assert model._species_group(TreeSpecies.Sweden.fagus_sylvatica) == "other_broadleaves"
    assert model._species_group(TreeSpecies.Sweden.larix_sibirica) is None

    with pytest.raises(ValueError):
        model._validate_state({"spruce": np.zeros(4)})


def test_bollandsas_stand_to_state_and_basal_area():
    model = _model()
    empty = model.stand_to_state(Stand())
    assert all(np.all(v == 0.0) for v in empty.values())

    plot1 = CircularPlot(
        id="p1",
        area_m2=400.0,
        trees=[
            Tree(species=TreeSpecies.Sweden.picea_abies, diameter_cm=20.0, weight_n=10.0),
            Tree(species=TreeSpecies.Sweden.pinus_sylvestris, diameter_cm=24.0, weight_n=8.0),
            Tree(species=TreeSpecies.Sweden.betula_pendula, diameter_cm=4.0, weight_n=5.0),
            Tree(species=TreeSpecies.Sweden.larix_sibirica, diameter_cm=30.0, weight_n=3.0),
        ],
    )
    plot2 = CircularPlot(
        id="p2",
        area_m2=400.0,
        trees=[
            Tree(species=TreeSpecies.Sweden.picea_abies, diameter_cm=18.0, weight_n=12.0),
            Tree(species=TreeSpecies.Sweden.fagus_sylvatica, diameter_cm=22.0, weight_n=4.0),
            Tree(species=TreeSpecies.Sweden.pinus_sylvestris, diameter_cm=None, weight_n=5.0),
        ],
    )
    stand = Stand(plots=[plot1, plot2])
    state = model.stand_to_state(stand)
    assert state["spruce"].sum() > 0.0
    assert state["pine"].sum() > 0.0
    assert state["birch"].sum() == 0.0
    assert state["other_broadleaves"].sum() > 0.0

    ba = model.compute_stand_basal_area_by_species(state)
    assert all(isinstance(v, StandBasalArea) for v in ba.values())
    assert sum(float(v) for v in ba.values()) > 0.0


def test_bollandsas_step_and_simulation_with_harvest():
    model = _model()
    state = {
        "spruce": np.array([100.0] + [0.0] * 14, dtype=float),
        "pine": np.array([80.0] + [0.0] * 14, dtype=float),
        "birch": np.array([60.0] + [0.0] * 14, dtype=float),
        "other_broadleaves": np.array([30.0] + [0.0] * 14, dtype=float),
    }
    harvest = {
        "spruce": np.array([20.0] + [0.0] * 14, dtype=float),
        "pine": np.zeros(15, dtype=float),
        "birch": np.zeros(15, dtype=float),
        "other_broadleaves": np.zeros(15, dtype=float),
    }

    next_state = model.step_5y(state, harvest_by_species=harvest)
    assert next_state["spruce"][0] >= 0.0
    assert all(np.all(v >= 0.0) for v in next_state.values())

    zero_state = {sp: np.zeros(15, dtype=float) for sp in model.SPECIES}
    history_zero = model.simulate_years(zero_state, years=10)
    assert len(history_zero) == 3
    assert all(np.all(v >= 0.0) for v in history_zero[-1].values())

    history = model.simulate_years(state, years=10, harvest_schedule={5: harvest})
    assert len(history) == 3
    assert history[0]["spruce"][0] == pytest.approx(100.0)


def test_bollandsas_recruitment_matches_published_coefficients():
    """Pin other-broadleaves recruitment to Bollandsas et al. (2008) Tables V/VI.

    Independently recomputes the two-part recruitment with the coefficients written
    out, so a regression of the site-index term back to the sitree value 0.0123
    (the published value is 0.123) would fail this test.
    """
    import math

    model = _model()  # other_broadleaves site index = 14.0
    state = {sp: np.zeros(15, dtype=float) for sp in model.SPECIES}
    state["other_broadleaves"][0] = 100.0  # 100 stems/ha in the smallest class

    ba_total = 100.0 * model._basal_area_per_tree_m2(model.class_mid[0])
    pba = 100.0  # only species present -> 100% of stand basal area
    si = 14.0

    # Table V (eq. 4) presence logistic + Table VI (eq. 5) conditional count:
    logit = -3.438 - 0.029 * ba_total + 0.123 * si + 0.048 * pba
    p_pos = 1.0 / (1.0 + math.exp(-logit))
    cond = 31.438 * ba_total ** (-0.1695) * si**0.442 * (1.0 + pba) ** 0.193
    expected = p_pos * cond

    recruits = model._predict_recruits(state)
    assert recruits["other_broadleaves"] == pytest.approx(expected, rel=1e-9)


def test_bollandsas_growth_model_adapter():
    stand = Stand(
        plots=[
            CircularPlot(
                id="p1",
                area_m2=400.0,
                trees=[
                    Tree(species=TreeSpecies.Sweden.picea_abies, diameter_cm=20.0, weight_n=40.0),
                    Tree(
                        species=TreeSpecies.Sweden.pinus_sylvestris,
                        diameter_cm=22.0,
                        weight_n=30.0,
                    ),
                ],
            )
        ]
    )
    adapter = Bollandsas2008GrowthModel(
        Bollandsas2008AdapterConfig(
            site_index_by_species={
                "spruce": 20.0,
                "pine": 18.0,
                "birch": 16.0,
                "other_broadleaves": 14.0,
            },
            latitude_deg=60.0,
        )
    )
    ctx = adapter.build_context(stand)
    # This is a transition-matrix model over diameter classes; the context must
    # hold that representation, not a tree list the model never reads back.
    assert ctx.mode == "diameter_class"
    stems_before = float(ctx.metrics["Stems"]["TOTAL"])
    ba_before = float(ctx.metrics["BasalArea"]["TOTAL"])

    adapter.update_step(ctx, dt=5.0)

    assert float(ctx.state["t"]) == pytest.approx(5.0)
    assert float(ctx.metrics["Stems"]["TOTAL"]) >= 0.0
    assert float(ctx.metrics["BasalArea"]["TOTAL"]) >= 0.0
    assert "bollandsas_basal_area_by_species" in ctx.attrs
    assert (float(ctx.metrics["Stems"]["TOTAL"]) != stems_before) or (
        float(ctx.metrics["BasalArea"]["TOTAL"]) != ba_before
    )

    with pytest.raises(ValueError):
        adapter.update_step(ctx, dt=1.0)


def test_bollandsas_growth_survives_the_context_metric_refresh():
    """Stepping through the context must not discard what the model computed.

    The adapter used to declare ``tree_list`` and publish its class vectors with
    ``set_aggregate_metrics``. ``SimulationContext.update_step`` refreshes the
    metrics after the model runs, and in tree-list mode that rebuilds them from
    the plots -- which this model never touches -- so a step driven through the
    documented runtime path silently reverted to the starting state.
    """
    stand = Stand(
        plots=[
            CircularPlot(
                id="p1",
                area_m2=400.0,
                trees=[
                    Tree(species=TreeSpecies.Sweden.picea_abies, diameter_cm=d, weight_n=1.0)
                    for d in (12.0, 18.0, 24.0, 30.0)
                ],
            )
        ]
    )
    config = Bollandsas2008AdapterConfig(site_index_by_species={"spruce": 17.0}, latitude_deg=60.0)

    direct = Bollandsas2008GrowthModel(config)
    ctx_direct = direct.build_context(stand)
    direct.update_step(ctx_direct, 5.0)

    through_runtime = Bollandsas2008GrowthModel(config)
    ctx_runtime = through_runtime.build_context(stand)
    ctx_runtime.update_step(5.0)

    assert float(ctx_runtime.metrics["BasalArea"]["TOTAL"]) == pytest.approx(
        float(ctx_direct.metrics["BasalArea"]["TOTAL"])
    )
    assert float(ctx_runtime.metrics["Stems"]["TOTAL"]) == pytest.approx(
        float(ctx_direct.metrics["Stems"]["TOTAL"])
    )
