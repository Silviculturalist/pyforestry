import pytest

from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.mortality.retained_trees import retained_tree_mortality_by_species


def test_retained_tree_mortality_year_windows() -> None:
    year1_5 = {TreeSpecies.Sweden.pinus_sylvestris: 0.09}
    year6_10 = {TreeSpecies.Sweden.pinus_sylvestris: 0.045}

    not_applicable = retained_tree_mortality_by_species(
        years_since_final_felling=10.0,
        mortality_year1_5=year1_5,
        mortality_year6_10=year6_10,
    )
    early = retained_tree_mortality_by_species(
        years_since_final_felling=2.0,
        mortality_year1_5=year1_5,
        mortality_year6_10=year6_10,
    )
    late = retained_tree_mortality_by_species(
        years_since_final_felling=7.0,
        mortality_year1_5=year1_5,
        mortality_year6_10=year6_10,
    )

    assert not_applicable is None
    assert early["pinus sylvestris"] == pytest.approx(0.09)
    assert late["pinus sylvestris"] == pytest.approx(0.045)


def test_retained_tree_mortality_handles_none_and_group_keys() -> None:
    assert (
        retained_tree_mortality_by_species(
            years_since_final_felling=None,
            mortality_year1_5={"pine": 0.2},
            mortality_year6_10={"pine": 0.1},
        )
        is None
    )
    grouped = retained_tree_mortality_by_species(
        years_since_final_felling=4.0,
        mortality_year1_5={"pine": 1.2},
        mortality_year6_10={"pine": -0.1},
    )
    assert grouped is not None
    assert grouped["pine"] == pytest.approx(1.0)
