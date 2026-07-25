import json
from pathlib import Path

import pytest

from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.mortality.root_rot_thor_stahl_stenlid_2005 import (
    root_rot_risk_thor_stahl_stenlid_2005 as _root_rot_risk_thor_stahl_stenlid_2005,
)
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

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mortality" / "mortality_reference_cases.json"


def _fixture_vector() -> list[float]:
    data = json.loads(_FIXTURE_PATH.read_text())
    return data["root_rot_fixture"]["tree_vector"]


def root_rot_risk_thor_stahl_stenlid_2005(
    *,
    trees: list[MortalityTreeState],
    stand_state: MortalityStandState,
    site_state: MortalitySiteState,
    default_stems_per_tree: float = 1.0,
):
    return _root_rot_risk_thor_stahl_stenlid_2005(
        context=MortalityContext(
            trees=trees,
            stand=stand_state,
            site=site_state,
        ),
        default_stems_per_tree=default_stems_per_tree,
    )


def test_root_rot_thor_stahl_stenlid_2005_matches_reference_vector() -> None:
    diameters_cm = [30.0005, 30.0, 25.0, 25.0, 22.0, 22.0, 20.0, 15.0, 10.0, 5.0]
    stems = [50.0, 50.0, 80.0, 80.0, 100.0, 100.0, 80.0, 80.0, 50.0, 50.0]
    species = [
        TreeSpecies.Sweden.pinus_sylvestris,
        TreeSpecies.Sweden.picea_abies,
        TreeSpecies.Sweden.picea_abies,
        TreeSpecies.Sweden.picea_abies,
        TreeSpecies.Sweden.picea_abies,
        TreeSpecies.Sweden.picea_abies,
        TreeSpecies.Sweden.picea_abies,
        TreeSpecies.Sweden.picea_sitchensis,
        TreeSpecies.Sweden.picea_abies,
        TreeSpecies.Sweden.betula_pendula,
    ]
    trees = [
        MortalityTreeState(
            species=species_value,
            diameter_cm=diameter_cm,
            stems_per_tree=stems_per_tree,
        )
        for species_value, diameter_cm, stems_per_tree in zip(
            species,
            diameters_cm,
            stems,
            strict=True,
        )
    ]
    stand = MortalityStandState(
        plot_area_m2=10_000.0,
        mean_age_total_years=50.0,
        mean_age_excl_overstorey_years=50.0,
    )
    site = MortalitySiteState(
        latitude_deg=61.9,
        altitude_m=300.0,
        site_index_m=24.0,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        temperature_sum=900.0,
        texture_is_sand_medium=True,
    )

    result = root_rot_risk_thor_stahl_stenlid_2005(
        trees=trees,
        stand_state=stand,
        site_state=site,
    )
    expected = _fixture_vector()
    assert len(result.tree_risk_probabilities) == len(expected)
    for calculated, expected_value in zip(result.tree_risk_probabilities, expected, strict=True):
        assert calculated == pytest.approx(expected_value, abs=1e-6)

    assert result.stems_with_root_rot > 0.0
    assert result.basal_area_with_root_rot_m2_ha > 0.0
