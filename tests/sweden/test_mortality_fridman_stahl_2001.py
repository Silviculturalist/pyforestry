import pytest

from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.mortality.fridman_stahl_2001 import (
    FridmanStahl2001Model as _FridmanStahl2001Model,
)
from pyforestry.sweden.mortality.fridman_stahl_2001 import (
    _fridman_step3_probability,
)
from pyforestry.sweden.mortality.fridman_stahl_2001 import (
    fridman_stahl_2001_probabilities as _fridman_stahl_2001_probabilities,
)
from pyforestry.sweden.mortality.types import (
    MortalityContext,
    MortalityRealizationMode,
)
from pyforestry.sweden.mortality.types import (
    MortalityHistoryConditions as MortalityHistoryState,
)
from pyforestry.sweden.mortality.types import (
    MortalitySiteConditions as MortalitySiteState,
)
from pyforestry.sweden.mortality.types import (
    MortalityStandConditions as MortalityStandState,
)
from pyforestry.sweden.mortality.types import (
    MortalityTreeRecord as MortalityTreeState,
)
from pyforestry.sweden.site.enums import Sweden


class _FixedRandom:
    def __init__(self, uniform_value: float, gauss_value: float = 0.0) -> None:
        self._uniform_value = uniform_value
        self._gauss_value = gauss_value

    def random(self) -> float:
        return self._uniform_value

    def gauss(self, _mean: float, _sigma: float) -> float:
        return self._gauss_value


def _context(
    trees: list[MortalityTreeState],
    stand_state: MortalityStandState,
    site_state: MortalitySiteState,
    history_state: MortalityHistoryState | None = None,
) -> MortalityContext:
    return MortalityContext(
        trees=trees,
        stand=stand_state,
        site=site_state,
        history=history_state,
    )


def fridman_stahl_2001_probabilities(
    *,
    trees: list[MortalityTreeState],
    stand_state: MortalityStandState,
    site_state: MortalitySiteState,
    history_state: MortalityHistoryState | None = None,
    implementation_type: MortalityRealizationMode = MortalityRealizationMode.DETERMINISTIC,
    period_years: float = 5.0,
    rng: _FixedRandom | None = None,
    default_stems_per_tree: float = 1.0,
):
    return _fridman_stahl_2001_probabilities(
        context=_context(trees, stand_state, site_state, history_state),
        implementation_type=implementation_type,
        period_years=period_years,
        rng=rng,
        default_stems_per_tree=default_stems_per_tree,
    )


class FridmanStahl2001Model(_FridmanStahl2001Model):
    def predict_probabilities(
        self,
        *,
        trees: list[MortalityTreeState],
        stand_state: MortalityStandState,
        site_state: MortalitySiteState,
        history_state: MortalityHistoryState | None = None,
        period_years: float = 5.0,
        default_stems_per_tree: float = 1.0,
    ):
        return super().predict_probabilities(
            context=_context(trees, stand_state, site_state, history_state),
            period_years=period_years,
            default_stems_per_tree=default_stems_per_tree,
        )


def _states(
    plot_area_m2: float,
) -> tuple[list[MortalityTreeState], MortalityStandState, MortalitySiteState]:
    trees = [
        MortalityTreeState(
            species=TreeSpecies.Sweden.pinus_sylvestris,
            diameter_cm=24.0,
            bal=5.0,
            stems_per_tree=140.0,
        ),
        MortalityTreeState(
            species=TreeSpecies.Sweden.picea_abies,
            diameter_cm=22.0,
            bal=8.0,
            stems_per_tree=180.0,
        ),
        MortalityTreeState(
            species=TreeSpecies.Sweden.betula_pendula,
            diameter_cm=18.0,
            bal=12.0,
            stems_per_tree=220.0,
        ),
    ]
    stand = MortalityStandState(
        plot_area_m2=plot_area_m2,
        total_basal_area_m2_ha=30.0,
        total_stems_per_ha=2000.0,
        mean_diameter_arithmetic_cm=22.0,
        mean_age_total_years=65.0,
    )
    site = MortalitySiteState(
        latitude_deg=60.0,
        altitude_m=200.0,
        site_index_m=24.0,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        peat=False,
        temperature_sum=950.0,
        part_of_sweden="middle",
        field_layer=Sweden.FieldLayer.BILBERRY,
    )
    return trees, stand, site


def test_fridman_stahl_stochastic_step1_gate_occurs_when_u_lt_p_plot() -> None:
    trees, stand, site = _states(plot_area_m2=300.0)
    history = MortalityHistoryState(thinned_within_0_5_years=False)

    probabilities_on, diagnostics_on = fridman_stahl_2001_probabilities(
        trees=trees,
        stand_state=stand,
        site_state=site,
        history_state=history,
        implementation_type=MortalityRealizationMode.STOCHASTIC,
        rng=_FixedRandom(uniform_value=0.0),
    )
    probabilities_off, diagnostics_off = fridman_stahl_2001_probabilities(
        trees=trees,
        stand_state=stand,
        site_state=site,
        history_state=history,
        implementation_type=MortalityRealizationMode.STOCHASTIC,
        rng=_FixedRandom(uniform_value=1.0),
    )

    assert diagnostics_on["event_occurred"] is True
    assert max(probabilities_on) > 0.0
    assert diagnostics_off["event_occurred"] is False
    assert probabilities_off == [0.0, 0.0, 0.0]


def test_fridman_stahl_uses_actual_plot_area() -> None:
    trees_a, stand_a, site_a = _states(plot_area_m2=100.0)
    trees_b, stand_b, site_b = _states(plot_area_m2=500.0)

    _prob_a, diagnostics_a = fridman_stahl_2001_probabilities(
        trees=trees_a,
        stand_state=stand_a,
        site_state=site_a,
    )
    _prob_b, diagnostics_b = fridman_stahl_2001_probabilities(
        trees=trees_b,
        stand_state=stand_b,
        site_state=site_b,
    )

    assert diagnostics_a["p_plot"] != pytest.approx(diagnostics_b["p_plot"])


def test_fridman_stahl_period_scaling_and_clamping() -> None:
    trees, stand, site = _states(plot_area_m2=300.0)

    probabilities_5, _ = fridman_stahl_2001_probabilities(
        trees=trees,
        stand_state=stand,
        site_state=site,
        period_years=5.0,
    )
    probabilities_10, _ = fridman_stahl_2001_probabilities(
        trees=trees,
        stand_state=stand,
        site_state=site,
        period_years=10.0,
    )

    assert len(probabilities_5) == len(probabilities_10) == len(trees)
    for probability_5, probability_10 in zip(probabilities_5, probabilities_10, strict=True):
        assert 0.0 <= probability_5 <= 1.0
        assert 0.0 <= probability_10 <= 1.0
        assert probability_10 >= probability_5


def test_fridman_step3_private_species_branches_and_domain_errors() -> None:
    base_kwargs = {
        "total_basal_area_m2_ha": 30.0,
        "log_total_basal_area": 3.4,
        "mdbh_m": 0.22,
        "mdbh2_m2": 0.018,
        "wet_indicator": 0,
        "pine_indicator": 0,
        "thinning_indicator": 0,
        "near_edge_indicator": 0,
        "edge_indicator": 0,
        "altitude_m": 200.0,
        "latitude_deg": 60.0,
    }

    assert (
        _fridman_step3_probability(
            tree=MortalityTreeState(species=TreeSpecies.Sweden.pinus_sylvestris, diameter_cm=3.9),
            **base_kwargs,
        )
        == 0.0
    )

    assert (
        _fridman_step3_probability(
            tree=MortalityTreeState(species=TreeSpecies.Sweden.picea_abies, diameter_cm=0.0),
            **base_kwargs,
        )
        == 0.0
    )
    assert (
        _fridman_step3_probability(
            tree=MortalityTreeState(species="alnus glutinosa", diameter_cm=0.0),
            **base_kwargs,
        )
        == 0.0
    )

    oak_low = _fridman_step3_probability(
        tree=MortalityTreeState(
            species=TreeSpecies.Sweden.quercus_robur,
            diameter_cm=20.0,
            bal=0.0,
        ),
        **base_kwargs,
    )
    oak_high = _fridman_step3_probability(
        tree=MortalityTreeState(
            species=TreeSpecies.Sweden.quercus_robur,
            diameter_cm=20.0,
            bal=100.0,
        ),
        **base_kwargs,
    )
    aspen = _fridman_step3_probability(
        tree=MortalityTreeState(
            species=TreeSpecies.Sweden.populus_tremula,
            diameter_cm=18.0,
            bal=5.0,
        ),
        **base_kwargs,
    )

    assert 0.0 < oak_low < 1.0
    assert 0.0 < oak_high < 1.0
    assert oak_high > oak_low
    assert 0.0 < aspen < 1.0


def test_fridman_stahl_validation_warnings_and_facade() -> None:
    trees, stand, site = _states(plot_area_m2=300.0)

    with pytest.raises(ValueError):
        fridman_stahl_2001_probabilities(
            trees=trees,
            stand_state=MortalityStandState(plot_area_m2=0.0, total_basal_area_m2_ha=30.0),
            site_state=site,
        )
    with pytest.raises(ValueError):
        fridman_stahl_2001_probabilities(
            trees=trees,
            stand_state=MortalityStandState(
                plot_area_m2=300.0,
                total_basal_area_m2_ha=0.0,
                total_stems_per_ha=2_000.0,
                mean_diameter_arithmetic_cm=22.0,
                mean_age_total_years=65.0,
            ),
            site_state=site,
        )
    with pytest.raises(ValueError):
        fridman_stahl_2001_probabilities(
            trees=trees,
            stand_state=MortalityStandState(
                plot_area_m2=300.0,
                total_basal_area_m2_ha=30.0,
                total_stems_per_ha=0.0,
                mean_diameter_arithmetic_cm=22.0,
                mean_age_total_years=65.0,
            ),
            site_state=site,
        )

    with pytest.warns(UserWarning):
        fridman_stahl_2001_probabilities(
            trees=trees,
            stand_state=MortalityStandState(
                plot_area_m2=10.0,
                total_basal_area_m2_ha=30.0,
                total_stems_per_ha=2_000.0,
                mean_diameter_arithmetic_cm=22.0,
                mean_age_total_years=65.0,
            ),
            site_state=MortalitySiteState(
                latitude_deg=60.0,
                altitude_m=200.0,
                site_index_m=24.0,
                soil_moisture=6,
            ),
        )

    model = FridmanStahl2001Model()
    probabilities, diagnostics = model.predict_probabilities(
        trees=trees,
        stand_state=stand,
        site_state=site,
    )
    assert len(probabilities) == len(trees)
    assert "p_plot" in diagnostics


def test_fridman_stahl_step2_clipping_and_variance_warning_paths() -> None:
    trees, _, site = _states(plot_area_m2=300.0)

    high_pba_stand = MortalityStandState(
        plot_area_m2=20.0,
        total_basal_area_m2_ha=20.0,
        total_stems_per_ha=50_000.0,
        mean_diameter_arithmetic_cm=80.0,
        mean_age_total_years=65.0,
    )
    _prob_high, diagnostics_high = fridman_stahl_2001_probabilities(
        trees=trees,
        stand_state=high_pba_stand,
        site_state=site,
    )
    assert diagnostics_high["p_basal_area"] == pytest.approx(1.0)

    low_pba_stand = MortalityStandState(
        plot_area_m2=2_000.0,
        total_basal_area_m2_ha=200.0,
        total_stems_per_ha=100.0,
        mean_diameter_arithmetic_cm=5.0,
        mean_age_total_years=80.0,
    )
    _prob_low, diagnostics_low = fridman_stahl_2001_probabilities(
        trees=trees,
        stand_state=low_pba_stand,
        site_state=site,
    )
    assert diagnostics_low["p_basal_area"] == pytest.approx(0.0)

    negative_variance_stand = MortalityStandState(
        plot_area_m2=50.0,
        total_basal_area_m2_ha=1.0,
        total_stems_per_ha=100_000.0,
        mean_diameter_arithmetic_cm=1.0,
        mean_age_total_years=20.0,
    )
    with pytest.warns(UserWarning, match="variance"):
        _probabilities, diagnostics = fridman_stahl_2001_probabilities(
            trees=trees,
            stand_state=negative_variance_stand,
            site_state=site,
            implementation_type=MortalityRealizationMode.STOCHASTIC,
            rng=_FixedRandom(uniform_value=0.0, gauss_value=0.0),
        )
    assert diagnostics["step2_variance"] == pytest.approx(0.0)
