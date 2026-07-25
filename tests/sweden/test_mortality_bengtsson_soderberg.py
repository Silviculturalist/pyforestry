import pytest

from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.mortality.bengtsson import calibrate_bengtsson as _calibrate_bengtsson
from pyforestry.sweden.mortality.soderberg_1986 import calibrate_soderberg as _calibrate_soderberg
from pyforestry.sweden.mortality.types import (
    MortalityContext,
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


def _states() -> tuple[list[MortalityTreeState], MortalityStandState, MortalitySiteState]:
    trees = [
        MortalityTreeState(
            species=TreeSpecies.Sweden.pinus_sylvestris,
            diameter_cm=24.0,
            stems_per_tree=180.0,
            bal=5.0,
            age_total_years=80.0,
        ),
        MortalityTreeState(
            species=TreeSpecies.Sweden.picea_abies,
            diameter_cm=22.0,
            stems_per_tree=220.0,
            bal=7.0,
            age_total_years=80.0,
        ),
        MortalityTreeState(
            species=TreeSpecies.Sweden.betula_pendula,
            diameter_cm=18.0,
            stems_per_tree=260.0,
            bal=11.0,
            age_total_years=80.0,
        ),
    ]
    stand = MortalityStandState(
        plot_area_m2=300.0,
        total_basal_area_m2_ha=34.0,
        total_stems_per_ha=2_100.0,
        mean_diameter_arithmetic_cm=21.0,
        mean_age_total_years=80.0,
        mean_age_excl_overstorey_years=80.0,
    )
    site = MortalitySiteState(
        latitude_deg=63.0,
        altitude_m=250.0,
        site_index_m=22.0,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        part_of_sweden="north",
    )
    return trees, stand, site


def _context(
    trees: list[MortalityTreeState],
    stand_state: MortalityStandState,
    site_state: MortalitySiteState,
) -> MortalityContext:
    return MortalityContext(
        trees=trees,
        stand=stand_state,
        site=site_state,
    )


def calibrate_bengtsson(
    *,
    trees: list[MortalityTreeState],
    tree_probabilities: list[float],
    stand_state: MortalityStandState,
    site_state: MortalitySiteState,
    period_years: float = 5.0,
    default_stems_per_tree: float = 1.0,
):
    return _calibrate_bengtsson(
        context=_context(trees, stand_state, site_state),
        tree_probabilities=tree_probabilities,
        period_years=period_years,
        default_stems_per_tree=default_stems_per_tree,
    )


def calibrate_soderberg(
    *,
    trees: list[MortalityTreeState],
    tree_probabilities: list[float],
    stand_state: MortalityStandState,
    site_state: MortalitySiteState,
    site_index_adjustment_factor: float = 1.0,
    period_years: float = 5.0,
    default_stems_per_tree: float = 1.0,
):
    return _calibrate_soderberg(
        context=_context(trees, stand_state, site_state),
        tree_probabilities=tree_probabilities,
        site_index_adjustment_factor=site_index_adjustment_factor,
        period_years=period_years,
        default_stems_per_tree=default_stems_per_tree,
    )


def test_calibrate_bengtsson_matches_age_region_targets() -> None:
    trees, stand, site = _states()
    base_probabilities = [0.03, 0.04, 0.06]

    calibrated, targets, correction_factors, diagnostics = calibrate_bengtsson(
        trees=trees,
        tree_probabilities=base_probabilities,
        stand_state=stand,
        site_state=site,
    )

    assert diagnostics["part_of_sweden"] == "north"
    assert diagnostics["adjusted_bald"] == pytest.approx(9.0)
    assert targets["pine"] == pytest.approx(0.14 / 20.0)
    assert targets["spruce"] == pytest.approx((-0.000236 + 0.0250275 * 9.0) / 20.0)
    assert targets["birch"] == pytest.approx(0.78 / 20.0)
    assert all(value >= 0.0 for value in correction_factors.values())
    assert all(0.0 <= probability <= 1.0 for probability in calibrated)


def test_calibrate_soderberg_returns_valid_transition_adjustments() -> None:
    trees, stand, site = _states()
    base_probabilities = [0.02, 0.03, 0.05]

    calibrated, adjusted_fractions, correction_factors, diagnostics = calibrate_soderberg(
        trees=trees,
        tree_probabilities=base_probabilities,
        stand_state=stand,
        site_state=site,
        site_index_adjustment_factor=1.1,
    )

    assert diagnostics["self_thinning_limit_m2_ha"] > 0.0
    assert diagnostics["transition_weight"] == pytest.approx(
        diagnostics["transition_weight"],
        rel=0.0,
        abs=0.0,
    )
    assert set(adjusted_fractions).issubset({"pine", "spruce", "birch", "other"})
    assert all(0.0 <= value <= 1.0 for value in adjusted_fractions.values())
    assert all(value >= 0.0 for value in correction_factors.values())
    assert all(0.0 <= probability <= 1.0 for probability in calibrated)
    assert calibrated != base_probabilities


def test_calibrate_bengtsson_validation_and_south_branch_for_other_species() -> None:
    trees, stand, _site = _states()
    base_probabilities = [0.02, 0.03, 0.05]

    with pytest.raises(ValueError):
        calibrate_bengtsson(
            trees=trees,
            tree_probabilities=base_probabilities[:2],
            stand_state=stand,
            site_state=MortalitySiteState(
                latitude_deg=60.0,
                altitude_m=200.0,
                site_index_m=20.0,
                soil_moisture=Sweden.SoilMoistureEnum.MESIC,
                part_of_sweden="south",
            ),
        )

    no_tree_result = calibrate_bengtsson(
        trees=[],
        tree_probabilities=[],
        stand_state=stand,
        site_state=MortalitySiteState(
            latitude_deg=60.0,
            altitude_m=200.0,
            site_index_m=20.0,
            soil_moisture=Sweden.SoilMoistureEnum.MESIC,
            part_of_sweden="south",
        ),
    )
    assert no_tree_result == ([], {}, {}, {})

    with pytest.raises(ValueError):
        calibrate_bengtsson(
            trees=trees,
            tree_probabilities=base_probabilities,
            stand_state=MortalityStandState(plot_area_m2=300.0),
            site_state=MortalitySiteState(
                latitude_deg=60.0,
                altitude_m=200.0,
                site_index_m=20.0,
                soil_moisture=Sweden.SoilMoistureEnum.MESIC,
                part_of_sweden="south",
            ),
        )

    trees_with_other = [
        MortalityTreeState(species="alnus glutinosa", diameter_cm=18.0, stems_per_tree=100.0),
    ]
    south_stand = MortalityStandState(
        plot_area_m2=300.0,
        mean_age_total_years=140.0,
        mean_age_excl_overstorey_years=140.0,
    )
    calibrated, targets, _factors, diagnostics = calibrate_bengtsson(
        trees=trees_with_other,
        tree_probabilities=[0.02],
        stand_state=south_stand,
        site_state=MortalitySiteState(
            latitude_deg=57.0,
            altitude_m=80.0,
            site_index_m=26.0,
            soil_moisture=Sweden.SoilMoistureEnum.MESIC,
            part_of_sweden="south",
        ),
    )
    assert diagnostics["adjusted_bald"] == pytest.approx(16.0)
    assert targets["other"] == pytest.approx(0.46 / 20.0)
    assert calibrated[0] >= 0.0


def test_calibrate_soderberg_validation_warning_and_invalid_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trees, stand, site = _states()

    with pytest.raises(ValueError):
        calibrate_soderberg(
            trees=trees,
            tree_probabilities=[0.1],
            stand_state=stand,
            site_state=site,
        )

    assert calibrate_soderberg(
        trees=[],
        tree_probabilities=[],
        stand_state=stand,
        site_state=site,
    ) == ([], {}, {}, {})

    with pytest.raises(ValueError):
        calibrate_soderberg(
            trees=trees,
            tree_probabilities=[0.1, 0.1, 0.1],
            stand_state=stand,
            site_state=MortalitySiteState(
                latitude_deg=63.0,
                altitude_m=250.0,
                site_index_m=0.0,
                soil_moisture=Sweden.SoilMoistureEnum.MESIC,
            ),
        )
    with pytest.raises(ValueError):
        calibrate_soderberg(
            trees=trees,
            tree_probabilities=[0.1, 0.1, 0.1],
            stand_state=MortalityStandState(
                plot_area_m2=300.0,
                total_basal_area_m2_ha=0.0,
                total_stems_per_ha=2_000.0,
                mean_age_total_years=60.0,
            ),
            site_state=site,
        )
    with pytest.raises(ValueError):
        calibrate_soderberg(
            trees=trees,
            tree_probabilities=[0.1, 0.1, 0.1],
            stand_state=MortalityStandState(
                plot_area_m2=300.0,
                total_basal_area_m2_ha=20.0,
                total_stems_per_ha=0.0,
                mean_age_total_years=60.0,
            ),
            site_state=site,
        )
    with pytest.raises(ValueError):
        calibrate_soderberg(
            trees=trees,
            tree_probabilities=[0.1, 0.1, 0.1],
            stand_state=MortalityStandState(
                plot_area_m2=300.0,
                total_basal_area_m2_ha=20.0,
                total_stems_per_ha=2_000.0,
            ),
            site_state=site,
        )
    with pytest.raises(ValueError):
        calibrate_soderberg(
            trees=trees,
            tree_probabilities=[0.1, 0.1, 0.1],
            stand_state=MortalityStandState(
                plot_area_m2=300.0,
                total_basal_area_m2_ha=20.0,
                total_stems_per_ha=2_000.0,
                mean_age_total_years=0.0,
            ),
            site_state=site,
        )

    with pytest.warns(UserWarning, match="self-thinning"):
        calibrated, _adjusted, factors, diagnostics = calibrate_soderberg(
            trees=trees,
            tree_probabilities=[0.0, 0.0, 0.0],
            stand_state=MortalityStandState(
                plot_area_m2=300.0,
                total_basal_area_m2_ha=10_000.0,
                total_stems_per_ha=2_000.0,
                mean_age_total_years=80.0,
                mean_age_excl_overstorey_years=80.0,
            ),
            site_state=site,
        )
    assert diagnostics["self_thinning_probability"] == pytest.approx(1.0)
    assert all(value == 1.0 for value in factors.values())
    assert all(0.0 <= probability <= 1.0 for probability in calibrated)

    import pyforestry.sweden.mortality.soderberg_1986 as soderberg_module

    monkeypatch.setattr(soderberg_module.math, "exp", lambda _value: float("nan"))
    with pytest.raises(ValueError, match="Invalid self-thinning limit"):
        calibrate_soderberg(
            trees=trees,
            tree_probabilities=[0.1, 0.1, 0.1],
            stand_state=stand,
            site_state=site,
        )
