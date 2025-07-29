import warnings

import pytest

from pyforestry.base.helpers import Age, SiteIndexValue
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.models.elfving_hagglund_1975 import ElfvingHagglundInitialStand
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970


def test_validate_age_structure():
    with pytest.raises(ValueError):
        ElfvingHagglundInitialStand._validate_age_structure(True, True)

    # Should not raise
    ElfvingHagglundInitialStand._validate_age_structure(False, False)
    ElfvingHagglundInitialStand._validate_age_structure(True, False)


def test_validate_broadleaves():
    with warnings.catch_warnings(record=True) as rec:
        ElfvingHagglundInitialStand._validate_broadleaves(50)
        assert rec

    ElfvingHagglundInitialStand._validate_broadleaves(20)
    with pytest.raises(ValueError):
        ElfvingHagglundInitialStand._validate_broadleaves(-1)


def _create_valid_siteindex() -> SiteIndexValue:
    """Return a valid SiteIndexValue for Pinus sylvestris."""
    return Hagglund_1970.height_trajectory.pinus_sylvestris.sweden(
        dominant_height_m=12.0,
        age=Age.DBH(40),
        age2=Age.TOTAL(100),
        regeneration=Hagglund_1970.regeneration.CULTURE,
    )


def test_validate_site_index_valid():
    """Valid input passes and emits a warning from the heuristic check."""
    si = _create_valid_siteindex()
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        ElfvingHagglundInitialStand._validate_site_index(si, TreeSpecies.Sweden.pinus_sylvestris)
        assert rec


def test_validate_site_index_type_and_value_errors():
    si = _create_valid_siteindex()
    # Wrong type
    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand._validate_site_index(
            object(), TreeSpecies.Sweden.pinus_sylvestris
        )
    # Wrong reference age
    wrong_age_si = SiteIndexValue(
        float(si), reference_age=Age.TOTAL(90), species=si.species, fn=si.fn
    )
    with pytest.raises(ValueError):
        ElfvingHagglundInitialStand._validate_site_index(
            wrong_age_si, TreeSpecies.Sweden.pinus_sylvestris
        )
    # Wrong species
    wrong_species_si = SiteIndexValue(
        float(si),
        reference_age=si.reference_age,
        species={TreeSpecies.Sweden.picea_abies},
        fn=si.fn,
    )
    with pytest.raises(ValueError):
        ElfvingHagglundInitialStand._validate_site_index(
            wrong_species_si, TreeSpecies.Sweden.pinus_sylvestris
        )


def test_validate_site_index_warns_on_unknown_fn():
    """A warning is emitted if the function origin looks wrong."""
    si = _create_valid_siteindex()

    def dummy_fn():
        return None

    bad_fn_si = SiteIndexValue(
        float(si), reference_age=si.reference_age, species=si.species, fn=dummy_fn
    )
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        ElfvingHagglundInitialStand._validate_site_index(
            bad_fn_si, TreeSpecies.Sweden.pinus_sylvestris
        )
        assert rec


def test_estimate_stems_young_pine_north_numeric_and_errors():
    """Check numeric output and validation for Pine north function."""
    result = ElfvingHagglundInitialStand.estimate_stems_young_pine_north(
        latitude=64.0,
        altitude=200.0,
        dominant_height=8.0,
    )
    expected = float(
        ElfvingHagglundInitialStand.estimate_stems_young_pine_north(
            latitude=64.0,
            altitude=200.0,
            dominant_height=8.0,
        )
    )
    assert float(result) == pytest.approx(expected)
    assert result.species == TreeSpecies.Sweden.pinus_sylvestris

    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand.estimate_stems_young_pine_north(
            latitude=64.0,
            altitude=200.0,
            dominant_height=8,
        )

    with pytest.raises(ValueError):
        ElfvingHagglundInitialStand.estimate_stems_young_pine_north(
            latitude=64.0,
            altitude=200.0,
            dominant_height=8.0,
            stand_density_factor=2.0,
        )

    with warnings.catch_warnings(record=True) as rec:
        ElfvingHagglundInitialStand.estimate_stems_young_pine_north(
            latitude=64.0,
            altitude=200.0,
            dominant_height=8.0,
        )
        assert not rec
