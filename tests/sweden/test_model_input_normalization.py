from __future__ import annotations

import warnings

import pytest

from pyforestry.base.helpers.primitives import Age, SiteIndexValue
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden._model_input_normalization import (
    coerce_species,
    normalize_hagglund_h100_site_index_m,
    normalize_part_of_sweden,
    species_group_for_soderberg,
    warn_proportion,
)
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970


def test_coerce_species_and_group_resolution() -> None:
    pine = coerce_species("Pinus sylvestris")
    assert pine == TreeSpecies.Sweden.pinus_sylvestris
    assert species_group_for_soderberg(pine, model_name="test model") == "pine"
    assert (
        species_group_for_soderberg(TreeSpecies.Sweden.populus_tremula, model_name="test model")
        == "other"
    )


def test_species_group_for_soderberg_rejects_unsupported_conifer() -> None:
    with pytest.raises(ValueError, match="Unsupported species"):
        species_group_for_soderberg(
            TreeSpecies.Sweden.pseudotsuga_menziesii,
            model_name="Soderberg",
        )


def test_normalize_part_of_sweden_variants() -> None:
    assert normalize_part_of_sweden("Northern") == "north"
    assert normalize_part_of_sweden("central") == "middle"
    assert normalize_part_of_sweden("southern") == "south"
    assert normalize_part_of_sweden("gotland", allow_gotland=True) == "gotland"

    with pytest.warns(UserWarning, match="mapped to south"):
        assert (
            normalize_part_of_sweden(
                "gotland",
                gotland_alias="south",
                gotland_warning="mapped to south",
            )
            == "south"
        )

    with pytest.raises(ValueError, match="part_of_sweden must be one of"):
        normalize_part_of_sweden("east")


def test_warn_proportion_emits_out_of_range_warning() -> None:
    with pytest.warns(UserWarning, match="outside \\[0, 1\\]"):
        warn_proportion("prop_pine", 1.2)

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        warn_proportion("prop_pine", 0.5)
    assert len(record) == 0


def test_normalize_hagglund_h100_site_index_m_validates_inputs() -> None:
    assert normalize_hagglund_h100_site_index_m(22.5, parameter_name="site_index_m") == 22.5

    pine_site_index = SiteIndexValue(
        20.0,
        reference_age=Age.TOTAL(100),
        species={TreeSpecies.Sweden.pinus_sylvestris},
        fn=Hagglund_1970.height_trajectory.pinus_sylvestris.sweden,
    )
    assert (
        normalize_hagglund_h100_site_index_m(
            pine_site_index,
            parameter_name="site_index_value",
            expected_species=TreeSpecies.Sweden.pinus_sylvestris,
        )
        == 20.0
    )


def test_normalize_hagglund_h100_site_index_m_rejects_dbh_reference_age() -> None:
    pine_site_index_dbh_100 = SiteIndexValue(
        20.0,
        reference_age=Age.DBH(100),
        species={TreeSpecies.Sweden.pinus_sylvestris},
        fn=Hagglund_1970.height_trajectory.pinus_sylvestris.sweden,
    )

    with pytest.raises(ValueError, match="Age.TOTAL\\(100\\)"):
        normalize_hagglund_h100_site_index_m(
            pine_site_index_dbh_100,
            parameter_name="site_index_value",
            expected_species=TreeSpecies.Sweden.pinus_sylvestris,
        )
