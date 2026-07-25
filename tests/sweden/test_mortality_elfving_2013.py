import json
from pathlib import Path

import pytest

from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.mortality.elfving_2013 import (
    Elfving2013MortalityModel as _Elfving2013MortalityModel,
)
from pyforestry.sweden.mortality.elfving_2013 import (
    _balddgp1,
)
from pyforestry.sweden.mortality.elfving_2013 import (
    elfving_2013_probabilities as _elfving_2013_probabilities,
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

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mortality" / "mortality_reference_cases.json"


def _fixture_data() -> dict:
    return json.loads(_FIXTURE_PATH.read_text())


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


def elfving_2013_probabilities(
    *,
    trees: list[MortalityTreeState],
    stand_state: MortalityStandState,
    site_state: MortalitySiteState,
    history_state: MortalityHistoryState | None = None,
    period_years: float = 5.0,
):
    return _elfving_2013_probabilities(
        context=_context(trees, stand_state, site_state, history_state),
        period_years=period_years,
    )


class Elfving2013MortalityModel(_Elfving2013MortalityModel):
    def predict_probabilities(
        self,
        *,
        trees: list[MortalityTreeState],
        stand_state: MortalityStandState,
        site_state: MortalitySiteState,
        history_state: MortalityHistoryState | None = None,
        period_years: float = 5.0,
    ):
        return super().predict_probabilities(
            context=_context(trees, stand_state, site_state, history_state),
            period_years=period_years,
        )


def test_elfving_reference_fixture_values_exist() -> None:
    fixture = _fixture_data()
    elfving = fixture["elfving_fixture"]
    assert len(elfving["unthinned"]) == 10
    assert len(elfving["recently_thinned"]) == 10
    assert len(elfving["thinned"]) == 10
    assert elfving["unthinned"][0] == pytest.approx(0.010661)
    assert elfving["thinned"][-1] == pytest.approx(0.0579312)


def test_elfving_single_pine_reference_case() -> None:
    fixture = _fixture_data()["elfving_fixture"]["single_pine_case"]
    trees = [
        MortalityTreeState(
            species=TreeSpecies.Sweden.pinus_sylvestris,
            diameter_cm=fixture["diameter_cm_small"],
            bal=0.0,
            stems_per_tree=fixture["stems_small"],
            age_total_years=66.0,
        ),
        MortalityTreeState(
            species=TreeSpecies.Sweden.pinus_sylvestris,
            diameter_cm=fixture["diameter_cm_large"],
            bal=95.31909010152295,
            stems_per_tree=fixture["stems_large"],
            age_total_years=66.0,
        ),
    ]
    stand = MortalityStandState(
        plot_area_m2=10_000.0,
        total_basal_area_m2_ha=36.57910068,
        total_stems_per_ha=fixture["stems_small"] + fixture["stems_large"],
        mean_diameter_arithmetic_cm=24.7874299150406,
        mean_diameter_dg_cm=24.7874299150406,
        mean_age_total_years=66.0,
        mean_age_excl_overstorey_years=66.0,
    )
    site = MortalitySiteState(
        latitude_deg=60.0,
        altitude_m=100.0,
        site_index_m=24.0,
        soil_moisture=Sweden.SoilMoistureEnum.DRY,
        peat=False,
        temperature_sum=900.0,
        field_layer=Sweden.FieldLayer.BILBERRY,
        part_of_sweden="middle",
    )

    probabilities, _diagnostics = elfving_2013_probabilities(
        trees=trees,
        stand_state=stand,
        site_state=site,
    )
    assert probabilities[1] == pytest.approx(
        fixture["expected_mortality_large_tree"],
        rel=2e-3,
        abs=1e-6,
    )


def test_elfving_contorta_has_higher_mortality_than_pine_same_state() -> None:
    trees = [
        MortalityTreeState(
            species=TreeSpecies.Sweden.pinus_sylvestris,
            diameter_cm=20.0,
            bal=20.0,
            age_total_years=70.0,
        ),
        MortalityTreeState(
            species=TreeSpecies.Sweden.pinus_contorta,
            diameter_cm=20.0,
            bal=20.0,
            age_total_years=70.0,
        ),
    ]
    stand = MortalityStandState(
        plot_area_m2=10_000.0,
        total_basal_area_m2_ha=30.0,
        total_stems_per_ha=1_500.0,
        mean_diameter_arithmetic_cm=20.0,
        mean_diameter_dg_cm=20.0,
        mean_age_total_years=70.0,
        mean_age_excl_overstorey_years=70.0,
    )
    site = MortalitySiteState(
        latitude_deg=60.0,
        altitude_m=120.0,
        site_index_m=22.0,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        field_layer=Sweden.FieldLayer.BILBERRY,
    )

    probabilities, _ = elfving_2013_probabilities(
        trees=trees,
        stand_state=stand,
        site_state=site,
    )
    assert probabilities[1] < probabilities[0]


def test_elfving_recent_thinning_changes_probability() -> None:
    trees = [
        MortalityTreeState(
            species=TreeSpecies.Sweden.picea_abies,
            diameter_cm=22.0,
            bal=15.0,
            age_total_years=65.0,
        )
    ]
    stand = MortalityStandState(
        plot_area_m2=10_000.0,
        total_basal_area_m2_ha=32.0,
        total_stems_per_ha=1_800.0,
        mean_diameter_arithmetic_cm=22.0,
        mean_diameter_dg_cm=22.0,
        mean_age_total_years=65.0,
        mean_age_excl_overstorey_years=65.0,
    )
    site = MortalitySiteState(
        latitude_deg=61.0,
        altitude_m=180.0,
        site_index_m=24.0,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        field_layer=Sweden.FieldLayer.BILBERRY,
        temperature_sum=920.0,
    )

    baseline, _ = elfving_2013_probabilities(
        trees=trees,
        stand_state=stand,
        site_state=site,
        history_state=MortalityHistoryState(),
    )
    recent_thinning, _ = elfving_2013_probabilities(
        trees=trees,
        stand_state=stand,
        site_state=site,
        history_state=MortalityHistoryState(
            thinned_within_0_2_years=True,
            thinning_intensity_fraction=0.3,
            thinning_form_q=0.4,
        ),
    )
    assert recent_thinning[0] != pytest.approx(baseline[0], rel=1e-12, abs=1e-12)


def test_elfving_validation_paths_and_empty_input() -> None:
    stand = MortalityStandState(
        plot_area_m2=10_000.0,
        total_basal_area_m2_ha=20.0,
        total_stems_per_ha=1_000.0,
        mean_diameter_arithmetic_cm=20.0,
        mean_age_total_years=60.0,
    )
    site = MortalitySiteState(
        latitude_deg=60.0,
        altitude_m=100.0,
        site_index_m=22.0,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
    )

    probabilities, diagnostics = elfving_2013_probabilities(
        trees=[],
        stand_state=stand,
        site_state=site,
    )
    assert probabilities == []
    assert diagnostics == {}

    with pytest.raises(ValueError):
        elfving_2013_probabilities(
            trees=[
                MortalityTreeState(
                    species=TreeSpecies.Sweden.pinus_sylvestris,
                    diameter_cm=20.0,
                )
            ],
            stand_state=stand,
            site_state=MortalitySiteState(
                latitude_deg=60.0,
                altitude_m=100.0,
                site_index_m=0.0,
                soil_moisture=Sweden.SoilMoistureEnum.MESIC,
            ),
        )
    with pytest.raises(ValueError):
        elfving_2013_probabilities(
            trees=[
                MortalityTreeState(
                    species=TreeSpecies.Sweden.pinus_sylvestris,
                    diameter_cm=20.0,
                )
            ],
            stand_state=MortalityStandState(plot_area_m2=10_000.0, total_basal_area_m2_ha=0.0),
            site_state=site,
        )
    with pytest.raises(ValueError):
        elfving_2013_probabilities(
            trees=[
                MortalityTreeState(
                    species=TreeSpecies.Sweden.pinus_sylvestris,
                    diameter_cm=0.0,
                )
            ],
            stand_state=stand,
            site_state=site,
        )


def test_elfving_additional_species_branches_warning_and_facade() -> None:
    trees = [
        MortalityTreeState(
            species=TreeSpecies.Sweden.populus_tremula,
            diameter_cm=18.0,
            bal=10.0,
            age_total_years=80.0,
            is_overstorey=True,
        ),
        MortalityTreeState(
            species="ulmus glabra",
            diameter_cm=16.0,
            bal=8.0,
            age_total_years=70.0,
        ),
        MortalityTreeState(
            species="alnus glutinosa",
            diameter_cm=14.0,
            bal=7.0,
            age_total_years=70.0,
        ),
    ]
    stand = MortalityStandState(
        plot_area_m2=10_000.0,
        total_basal_area_m2_ha=24.0,
        total_stems_per_ha=1_500.0,
        mean_age_total_years=70.0,
        mean_age_excl_overstorey_years=70.0,
        mean_age_overstorey_years=0.0,
    )
    site = MortalitySiteState(
        latitude_deg=62.0,
        altitude_m=260.0,
        site_index_m=24.0,
        soil_moisture=6,
        field_layer=Sweden.FieldLayer.BILBERRY,
        temperature_sum=900.0,
    )

    with pytest.warns(UserWarning):
        probabilities, diagnostics = elfving_2013_probabilities(
            trees=trees,
            stand_state=stand,
            site_state=site,
            history_state=MortalityHistoryState(thinned_within_2_20_years=True),
        )
    assert len(probabilities) == len(trees)
    assert diagnostics["thinned_within_2_20_years"] == 1

    model = Elfving2013MortalityModel()
    model_probabilities, _ = model.predict_probabilities(
        trees=trees,
        stand_state=stand,
        site_state=site,
    )
    assert len(model_probabilities) == len(trees)


def test_elfving_balddgp1_caps_by_species_group() -> None:
    tree = MortalityTreeState(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        diameter_cm=4.0,
        bal=500.0,
    )
    assert _balddgp1(tree, pine_cap=True) == pytest.approx(5.0)
    assert _balddgp1(tree, pine_cap=False) == pytest.approx(2.5)
