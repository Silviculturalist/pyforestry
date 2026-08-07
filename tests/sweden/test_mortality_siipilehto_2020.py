import pytest

from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.mortality.siipilehto_2020 import (
    Siipilehto2020MortalityModel as _Siipilehto2020MortalityModel,
)
from pyforestry.sweden.mortality.siipilehto_2020 import (
    _log_one_plus_exp,
    _siipilehto_step3_probability,
)
from pyforestry.sweden.mortality.siipilehto_2020 import (
    siipilehto_2020_probabilities as _siipilehto_2020_probabilities,
)
from pyforestry.sweden.mortality.types import (
    MortalityContext,
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


def _states(
    plot_area_m2: float,
) -> tuple[list[MortalityTreeState], MortalityStandState, MortalitySiteState]:
    trees = [
        MortalityTreeState(
            species=TreeSpecies.Sweden.picea_abies,
            diameter_cm=24.0,
            bal=4.0,
            stems_per_tree=150.0,
        ),
        MortalityTreeState(
            species=TreeSpecies.Sweden.pinus_sylvestris,
            diameter_cm=20.0,
            bal=10.0,
            stems_per_tree=200.0,
        ),
        MortalityTreeState(
            species=TreeSpecies.Sweden.betula_pendula,
            diameter_cm=16.0,
            bal=14.0,
            stems_per_tree=250.0,
        ),
    ]
    stand = MortalityStandState(
        plot_area_m2=plot_area_m2,
        total_basal_area_m2_ha=28.0,
        total_stems_per_ha=1_900.0,
        mean_diameter_arithmetic_cm=20.0,
        mean_age_total_years=70.0,
        slope_percent=8.0,
        aspect_degrees=180.0,
    )
    site = MortalitySiteState(
        latitude_deg=60.5,
        altitude_m=220.0,
        site_index_m=22.0,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        peat=False,
        temperature_sum=930.0,
        field_layer=Sweden.FieldLayer.BILBERRY,
    )
    return trees, stand, site


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


def siipilehto_2020_probabilities(
    *,
    trees: list[MortalityTreeState],
    stand_state: MortalityStandState,
    site_state: MortalitySiteState,
    history_state: MortalityHistoryState | None = None,
    period_years: float = 5.0,
    default_stems_per_tree: float = 1.0,
):
    return _siipilehto_2020_probabilities(
        context=_context(trees, stand_state, site_state, history_state),
        period_years=period_years,
        default_stems_per_tree=default_stems_per_tree,
    )


class Siipilehto2020MortalityModel(_Siipilehto2020MortalityModel):
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


def test_siipilehto_probabilities_are_clamped_to_unit_interval() -> None:
    trees, stand, site = _states(plot_area_m2=300.0)
    probabilities, diagnostics = siipilehto_2020_probabilities(
        trees=trees,
        stand_state=stand,
        site_state=site,
        history_state=MortalityHistoryState(thinned_within_0_5_years=True),
    )
    assert len(probabilities) == len(trees)
    assert 0.0 <= diagnostics["p_plot"] <= 1.0
    assert 0.0 <= diagnostics["p_basal_area"] <= 1.0
    assert diagnostics["correction_factor"] >= 0.0
    for probability in probabilities:
        assert 0.0 <= probability <= 1.0


def test_siipilehto_uses_plot_area_in_step_functions() -> None:
    trees_a, stand_a, site_a = _states(plot_area_m2=100.0)
    trees_b, stand_b, site_b = _states(plot_area_m2=600.0)

    _prob_a, diagnostics_a = siipilehto_2020_probabilities(
        trees=trees_a,
        stand_state=stand_a,
        site_state=site_a,
    )
    _prob_b, diagnostics_b = siipilehto_2020_probabilities(
        trees=trees_b,
        stand_state=stand_b,
        site_state=site_b,
    )

    assert diagnostics_a["p_plot"] != pytest.approx(diagnostics_b["p_plot"])
    assert diagnostics_a["p_basal_area"] != pytest.approx(diagnostics_b["p_basal_area"])


def test_siipilehto_period_scaling_is_monotone() -> None:
    trees, stand, site = _states(plot_area_m2=300.0)
    probabilities_5, _ = siipilehto_2020_probabilities(
        trees=trees,
        stand_state=stand,
        site_state=site,
        period_years=5.0,
    )
    probabilities_10, _ = siipilehto_2020_probabilities(
        trees=trees,
        stand_state=stand,
        site_state=site,
        period_years=10.0,
    )

    for probability_5, probability_10 in zip(probabilities_5, probabilities_10, strict=True):
        assert probability_10 >= probability_5


def test_siipilehto_private_helpers_and_species_branch_errors() -> None:
    assert _log_one_plus_exp(10.0) == pytest.approx(10.000045398899216)
    assert _log_one_plus_exp(-10.0) == pytest.approx(0.00004539889921686)

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
        _siipilehto_step3_probability(
            tree=MortalityTreeState(species=TreeSpecies.Sweden.pinus_sylvestris, diameter_cm=3.0),
            **base_kwargs,
        )
        == 0.0
    )
    assert (
        _siipilehto_step3_probability(
            tree=MortalityTreeState(species=TreeSpecies.Sweden.picea_abies, diameter_cm=0.0),
            **base_kwargs,
        )
        == 0.0
    )
    assert (
        _siipilehto_step3_probability(
            tree=MortalityTreeState(species="alnus glutinosa", diameter_cm=0.0),
            **base_kwargs,
        )
        == 0.0
    )

    oak_high = _siipilehto_step3_probability(
        tree=MortalityTreeState(
            species=TreeSpecies.Sweden.quercus_robur,
            diameter_cm=20.0,
            bal=100.0,
        ),
        **base_kwargs,
    )
    other = _siipilehto_step3_probability(
        tree=MortalityTreeState(species="alnus glutinosa", diameter_cm=18.0, bal=5.0),
        **base_kwargs,
    )
    assert 0.0 < oak_high < 1.0
    assert 0.0 < other < 1.0


def test_siipilehto_validation_paths_and_clipping_branches() -> None:
    trees, _, site = _states(plot_area_m2=300.0)

    probabilities, diagnostics = siipilehto_2020_probabilities(
        trees=[],
        stand_state=MortalityStandState(plot_area_m2=300.0),
        site_state=site,
    )
    assert probabilities == []
    assert diagnostics["p_plot"] == 0.0

    with pytest.raises(ValueError):
        siipilehto_2020_probabilities(
            trees=trees,
            stand_state=MortalityStandState(plot_area_m2=0.0, total_basal_area_m2_ha=30.0),
            site_state=site,
        )
    with pytest.raises(ValueError):
        siipilehto_2020_probabilities(
            trees=trees,
            stand_state=MortalityStandState(
                plot_area_m2=300.0,
                total_basal_area_m2_ha=0.0,
                total_stems_per_ha=1_900.0,
                mean_diameter_arithmetic_cm=20.0,
                mean_age_total_years=70.0,
            ),
            site_state=site,
        )
    with pytest.raises(ValueError):
        siipilehto_2020_probabilities(
            trees=trees,
            stand_state=MortalityStandState(
                plot_area_m2=300.0,
                total_basal_area_m2_ha=28.0,
                total_stems_per_ha=0.0,
                mean_diameter_arithmetic_cm=20.0,
                mean_age_total_years=70.0,
            ),
            site_state=site,
        )
    with pytest.raises(ValueError):
        siipilehto_2020_probabilities(
            trees=trees,
            stand_state=MortalityStandState(
                plot_area_m2=300.0,
                total_basal_area_m2_ha=28.0,
                total_stems_per_ha=1_900.0,
                mean_diameter_arithmetic_cm=20.0,
                mean_age_total_years=0.0,
            ),
            site_state=site,
        )

    high_pba_stand = MortalityStandState(
        plot_area_m2=1.0,
        total_basal_area_m2_ha=20.0,
        total_stems_per_ha=50_000.0,
        mean_diameter_arithmetic_cm=80.0,
        mean_age_total_years=65.0,
    )
    _probabilities_high, diagnostics_high = siipilehto_2020_probabilities(
        trees=trees,
        stand_state=high_pba_stand,
        site_state=site,
    )
    assert diagnostics_high["p_basal_area"] == pytest.approx(1.0)

    low_pba_stand = MortalityStandState(
        plot_area_m2=10_000_000.0,
        total_basal_area_m2_ha=5.0,
        total_stems_per_ha=200.0,
        mean_diameter_arithmetic_cm=20.0,
        mean_age_total_years=80.0,
    )
    _probabilities_low, diagnostics_low = siipilehto_2020_probabilities(
        trees=trees,
        stand_state=low_pba_stand,
        site_state=site,
    )
    assert diagnostics_low["p_basal_area"] == pytest.approx(0.0)

    with pytest.warns(UserWarning):
        siipilehto_2020_probabilities(
            trees=trees,
            stand_state=MortalityStandState(
                plot_area_m2=300.0,
                total_basal_area_m2_ha=28.0,
                total_stems_per_ha=1_900.0,
                mean_diameter_arithmetic_cm=20.0,
                mean_age_total_years=70.0,
            ),
            site_state=MortalitySiteState(
                latitude_deg=60.5,
                altitude_m=220.0,
                site_index_m=22.0,
                soil_moisture=6,
            ),
        )

    model = Siipilehto2020MortalityModel()
    model_probabilities, _ = model.predict_probabilities(
        trees=trees,
        stand_state=MortalityStandState(
            plot_area_m2=300.0,
            total_basal_area_m2_ha=28.0,
            total_stems_per_ha=1_900.0,
            mean_diameter_arithmetic_cm=20.0,
            mean_age_total_years=70.0,
        ),
        site_state=site,
    )
    assert len(model_probabilities) == len(trees)

    trees_with_implicit_stems = [
        MortalityTreeState(species=TreeSpecies.Sweden.pinus_sylvestris, diameter_cm=18.0, bal=8.0),
        MortalityTreeState(species=TreeSpecies.Sweden.picea_abies, diameter_cm=22.0, bal=6.0),
    ]
    stand_without_mean_diameter = MortalityStandState(
        plot_area_m2=300.0,
        total_basal_area_m2_ha=20.0,
        total_stems_per_ha=1_500.0,
        mean_age_total_years=60.0,
    )
    probabilities_derived_mean, _ = siipilehto_2020_probabilities(
        trees=trees_with_implicit_stems,
        stand_state=stand_without_mean_diameter,
        site_state=site,
    )
    assert len(probabilities_derived_mean) == 2
