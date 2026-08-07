import numpy as np
import pytest

from pyforestry.base.helpers import Age, SiteIndexValue
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.mortality.types import (
    MortalityRealizationMode,
    MortalityTreeModel,
)
from pyforestry.sweden.mortality.types import (
    MortalityTreeRecord as MortalityTreeState,
)
from pyforestry.sweden.simulation.mortality import (
    MortalityConfig,
    MortalityContext,
    MortalityEngine,
    MortalityHistoryConditions,
    MortalitySiteConditions,
    MortalityStandConditions,
    MortalityTreeRecord,
)
from pyforestry.sweden.simulation.mortality.engine import (
    _apply_adjustment_factors,
    _assign_stochastic_mortality,
    _build_adjustment_lookup,
)
from pyforestry.sweden.site.enums import Sweden
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970


def _states() -> tuple[
    list[MortalityTreeRecord], MortalityStandConditions, MortalitySiteConditions
]:
    trees = [
        MortalityTreeRecord(
            species=TreeSpecies.Sweden.pinus_sylvestris,
            diameter_cm=24.0,
            bal=5.0,
            stems_per_tree=120.0,
            age_total_years=65.0,
        ),
        MortalityTreeRecord(
            species=TreeSpecies.Sweden.picea_abies,
            diameter_cm=20.0,
            bal=10.0,
            stems_per_tree=150.0,
            age_total_years=65.0,
        ),
    ]
    stand = MortalityStandConditions(
        plot_area_m2=300.0,
        total_basal_area_m2_ha=26.0,
        total_stems_per_ha=1_600.0,
        mean_diameter_arithmetic_cm=22.0,
        mean_diameter_dg_cm=22.0,
        mean_age_total_years=65.0,
        mean_age_excl_overstorey_years=65.0,
    )
    site = MortalitySiteConditions(
        latitude_deg=60.0,
        altitude_m=150.0,
        site_index_m=23.0,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        temperature_sum=930.0,
        field_layer=Sweden.FieldLayer.BILBERRY,
        part_of_sweden="middle",
    )
    return trees, stand, site


def test_engine_retained_override_precedes_core_model() -> None:
    trees, stand, site = _states()
    config = MortalityConfig(
        implementation_type=MortalityRealizationMode.DETERMINISTIC,
        tree_model=MortalityTreeModel.SIIPILEHTO_2020,
        retained_tree_mortality_years_1_to_5={TreeSpecies.Sweden.pinus_sylvestris: 0.09},
        retained_tree_mortality_years_6_to_10={TreeSpecies.Sweden.pinus_sylvestris: 0.045},
        use_retained_tree_override=True,
        calibrate_bengtsson=True,
        calibrate_soderberg=True,
    )
    result = MortalityEngine(config).run(
        MortalityContext(
            trees=trees,
            stand=stand,
            site=site,
            history=MortalityHistoryConditions(years_since_final_felling=2.0),
        )
    )

    assert result.diagnostics["tree_model"] == "retained_trees_override"
    assert result.tree_probabilities[0] == pytest.approx(0.09)
    assert result.tree_probabilities[1] == pytest.approx(0.0)


def test_engine_calibration_order_is_bengtsson_then_soderberg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trees, stand, site = _states()
    calls: list[str] = []

    def _fake_bengtsson(**kwargs):
        calls.append("bengtsson")
        probabilities = list(kwargs["tree_probabilities"])
        return probabilities, {"pine": 0.01}, {"pine": 1.0}, {}

    def _fake_soderberg(**kwargs):
        calls.append("soderberg")
        probabilities = list(kwargs["tree_probabilities"])
        return probabilities, {"pine": 0.02}, {"pine": 1.0}, {}

    import pyforestry.sweden.simulation.mortality.engine as engine_module

    monkeypatch.setattr(engine_module, "calibrate_bengtsson", _fake_bengtsson)
    monkeypatch.setattr(engine_module, "calibrate_soderberg", _fake_soderberg)

    config = MortalityConfig(
        implementation_type=MortalityRealizationMode.DETERMINISTIC,
        tree_model=MortalityTreeModel.ELFVING_2013,
        calibrate_bengtsson=True,
        calibrate_soderberg=True,
    )
    MortalityEngine(config).run(
        MortalityContext(
            trees=trees,
            stand=stand,
            site=site,
        )
    )

    assert calls == ["bengtsson", "soderberg"]


def test_engine_stochastic_reproducibility_with_fixed_seed() -> None:
    trees, stand, site = _states()
    for tree in trees:
        tree.stems_per_tree = None
    config = MortalityConfig(
        implementation_type=MortalityRealizationMode.STOCHASTIC,
        tree_model=MortalityTreeModel.ELFVING_2013,
        calibrate_bengtsson=False,
        calibrate_soderberg=False,
        stochastic_seed=12345,
        default_stems_per_tree=1.0,
    )
    engine_a = MortalityEngine(config)
    engine_b = MortalityEngine(config)

    result_a = engine_a.run(
        MortalityContext(
            trees=trees,
            stand=stand,
            site=site,
        )
    )
    result_b = engine_b.run(
        MortalityContext(
            trees=trees,
            stand=stand,
            site=site,
        )
    )

    assert result_a.tree_realized_mortality == result_b.tree_realized_mortality


def test_engine_private_helper_validations_and_multistem_assignment() -> None:
    trees = [
        MortalityTreeState(
            species=TreeSpecies.Sweden.pinus_sylvestris,
            diameter_cm=24.0,
            bal=5.0,
            stems_per_tree=120.0,
            age_total_years=65.0,
        ),
        MortalityTreeState(
            species=TreeSpecies.Sweden.picea_abies,
            diameter_cm=20.0,
            bal=10.0,
            stems_per_tree=150.0,
            age_total_years=65.0,
        ),
    ]
    assert _build_adjustment_lookup({"PINE": 1.1, " spruce ": 0.9}) == {
        "pine": pytest.approx(1.1),
        "spruce": pytest.approx(0.9),
    }
    assert _build_adjustment_lookup(None) == {}

    with pytest.raises(ValueError):
        _apply_adjustment_factors(
            trees=trees,
            probabilities=[0.1],
            global_adjustment_factor=1.0,
            species_adjustments=None,
        )
    with pytest.raises(ValueError):
        _apply_adjustment_factors(
            trees=trees,
            probabilities=[0.1, 0.2],
            global_adjustment_factor=-1.0,
            species_adjustments=None,
        )
    with pytest.raises(ValueError):
        _apply_adjustment_factors(
            trees=trees,
            probabilities=[0.1, 0.2],
            global_adjustment_factor=1.0,
            species_adjustments={"pine": -0.5},
        )

    adjusted = _apply_adjustment_factors(
        trees=trees,
        probabilities=[0.2, 0.3],
        global_adjustment_factor=1.0,
        species_adjustments={"pine": 0.5, "spruce": 2.0},
    )
    assert adjusted[0] == pytest.approx(0.1)
    assert adjusted[1] == pytest.approx(0.6)

    multi_stem_trees = [
        MortalityTreeState(
            species=TreeSpecies.Sweden.pinus_sylvestris,
            diameter_cm=20.0,
            stems_per_tree=3.0,
        ),
        MortalityTreeState(
            species=TreeSpecies.Sweden.picea_abies,
            diameter_cm=20.0,
            stems_per_tree=1.0,
        ),
    ]
    realized = _assign_stochastic_mortality(
        trees=multi_stem_trees,
        probabilities=[0.5, 0.5],
        rng=np.random.default_rng(0),
        default_stems_per_tree=1.0,
    )
    # A 3-stem record realizes as Binomial(3, p) / 3 -> one of {0, 1/3, 2/3, 1};
    # a 1-stem record realizes all-or-nothing.
    assert any(realized[0] == pytest.approx(k / 3.0) for k in range(4))
    assert realized[1] == pytest.approx(0.0) or realized[1] == pytest.approx(1.0)
    # Deterministic given the seed.
    again = _assign_stochastic_mortality(
        trees=multi_stem_trees,
        probabilities=[0.5, 0.5],
        rng=np.random.default_rng(0),
        default_stems_per_tree=1.0,
    )
    assert realized == again


def test_engine_empty_input_and_model_routing_paths() -> None:
    trees, stand, site = _states()

    empty = MortalityEngine(MortalityConfig()).run(
        MortalityContext(
            trees=[],
            stand=stand,
            site=site,
        )
    )
    assert empty.tree_probabilities == []
    assert empty.diagnostics["tree_model"] == MortalityTreeModel.FRIDMAN_STAHL_2001.value

    fridman_result = MortalityEngine(
        MortalityConfig(
            implementation_type=MortalityRealizationMode.DETERMINISTIC,
            tree_model=MortalityTreeModel.FRIDMAN_STAHL_2001,
            calibrate_bengtsson=False,
            calibrate_soderberg=False,
        )
    ).run(
        MortalityContext(
            trees=trees,
            stand=stand,
            site=site,
        )
    )
    assert fridman_result.diagnostics["tree_model"] == MortalityTreeModel.FRIDMAN_STAHL_2001.value

    siipilehto_result = MortalityEngine(
        MortalityConfig(
            implementation_type=MortalityRealizationMode.DETERMINISTIC,
            tree_model=MortalityTreeModel.SIIPILEHTO_2020,
            calibrate_bengtsson=False,
            calibrate_soderberg=False,
        )
    ).run(
        MortalityContext(
            trees=trees,
            stand=stand,
            site=site,
        )
    )
    assert siipilehto_result.diagnostics["tree_model"] == MortalityTreeModel.SIIPILEHTO_2020.value

    config_with_invalid_model = MortalityConfig(
        implementation_type=MortalityRealizationMode.DETERMINISTIC,
        calibrate_bengtsson=False,
        calibrate_soderberg=False,
    )
    config_with_invalid_model.tree_model = "invalid-model"  # type: ignore[assignment]
    with pytest.raises(ValueError, match="Unsupported tree model"):
        MortalityEngine(config_with_invalid_model).run(
            MortalityContext(
                trees=trees,
                stand=stand,
                site=site,
            )
        )


def test_engine_accepts_site_index_value_input() -> None:
    trees, stand, site = _states()
    site.site_index_m = SiteIndexValue(
        23.0,
        reference_age=Age.TOTAL(100),
        species={TreeSpecies.Sweden.picea_abies},
        fn=Hagglund_1970.height_trajectory.picea_abies.northern_sweden,
    )
    result = MortalityEngine(
        MortalityConfig(
            implementation_type=MortalityRealizationMode.DETERMINISTIC,
            tree_model=MortalityTreeModel.ELFVING_2013,
            calibrate_bengtsson=False,
            calibrate_soderberg=False,
        )
    ).run(
        MortalityContext(
            trees=trees,
            stand=stand,
            site=site,
        )
    )
    assert len(result.tree_probabilities) == len(trees)


def test_engine_rejects_non_hagglund_site_index_value() -> None:
    trees, stand, site = _states()
    site.site_index_m = SiteIndexValue(
        23.0,
        reference_age=Age.TOTAL(100),
        species={TreeSpecies.Sweden.picea_abies},
        fn=lambda *_: None,
    )
    with pytest.raises(ValueError, match="site_index_m\\.fn"):
        MortalityEngine(
            MortalityConfig(
                implementation_type=MortalityRealizationMode.DETERMINISTIC,
                tree_model=MortalityTreeModel.ELFVING_2013,
                calibrate_bengtsson=False,
                calibrate_soderberg=False,
            )
        ).run(
            MortalityContext(
                trees=trees,
                stand=stand,
                site=site,
            )
        )


def test_a_stochastic_tree_model_follows_the_run_stream_across_engine_rebuilds():
    """A tree model that draws must take the run's stream, not reopen a seeded one.

    The composite pipeline rebuilds its :class:`MortalityEngine` every period, to
    put that period's length on the config. The engine passed its tree models only
    ``config.stochastic_seed``, so a stochastic Fridman-Stahl opened a *fresh*
    generator from that constant on every rebuild and drew the same number in every
    period of a run -- correlated mortality dressed as independent draws.

    Passing a ``KeyedRNG`` hands the model the run's stream itself, so a rebuild
    carries on rather than restarting. Only a ``KeyedRNG`` is accepted: a bare
    NumPy generator can seed the engine's own vectorised draws but not the scalar
    draws of the tree model it builds, so accepting one would leave the model on
    the config seed -- half the fix, silently.
    """
    from pyforestry.simulation.services import RandomBundle
    from pyforestry.sweden.mortality.types import MortalityRealizationMode, MortalityTreeModel
    from pyforestry.sweden.simulation.mortality.engine import MortalityEngine

    config = MortalityConfig(
        tree_model=MortalityTreeModel.FRIDMAN_STAHL_2001,
        implementation_type=MortalityRealizationMode.STOCHASTIC,
        stochastic_seed=7,
    )

    keyed = RandomBundle(2026).rng_for("mortality")
    with_stream = [
        MortalityEngine(config=config, rng=keyed)._tree_model._rng.random() for _ in range(4)
    ]
    assert len(set(with_stream)) == 4, "rebuilding the engine restarted the tree model's stream"
    assert MortalityEngine(config=config, rng=keyed)._tree_model._rng is keyed

    # Without a keyed stream the engine is reproducible on its own terms, which is
    # what a directly-constructed one relies on -- and is exactly why the pipeline
    # has to pass its stream in.
    seeded = [MortalityEngine(config=config)._tree_model._rng.random() for _ in range(4)]
    assert len(set(seeded)) == 1

    # A generator is not a stream. Refused, rather than used for the engine's own
    # draws while the tree model it builds quietly stays on the config seed.
    import numpy as np

    with pytest.raises(TypeError, match="takes a KeyedRNG"):
        MortalityEngine(config=config, rng=np.random.default_rng(3))
