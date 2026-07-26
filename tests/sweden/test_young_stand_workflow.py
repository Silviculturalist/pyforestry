import math

from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.adapters.elfving_1982 import (
    NfiRegion,
    NyskogReconstruction,
    RegenerationType,
)
from pyforestry.sweden.site.enums import Sweden


def test_nyskog_reconstruct_summary_balances_stems():
    mean_height_main = 2.0
    result = NyskogReconstruction.reconstruct_summary(
        asinw=0.5,
        mean_height_main_m=mean_height_main,
        site_index_m=20.0,
        regeneration_type=RegenerationType.NATURAL,
        species_to_plant=TreeSpecies.Sweden.picea_abies,
        nfi_region=NfiRegion.REG3,
        field_layer=Sweden.FieldLayer.BILBERRY,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        deterministic=True,
    )

    total_stems = sum(result.stems_per_species.values())
    assert math.isclose(total_stems, result.stem_total, rel_tol=1e-6)
    assert math.isclose(
        result.mean_heights_m[result.main_species_key], mean_height_main, rel_tol=1e-9
    )
    assert result.qind >= 45.0
    for beta, shape in result.weibull_params.values():
        assert beta >= 0.0
        assert shape >= 0.0
