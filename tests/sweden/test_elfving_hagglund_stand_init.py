import pytest

from pyforestry.base.helpers import Age, SiteIndexValue
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.models.elfving_hagglund_1975 import ElfvingHagglundInitialStand
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _si_pine() -> SiteIndexValue:
    return Hagglund_1970.height_trajectory.pinus_sylvestris.sweden(
        dominant_height_m=12.0,
        age=Age.DBH(40),
        age2=Age.TOTAL(100),
        regeneration=Hagglund_1970.regeneration.CULTURE,
    )


def _si_spruce() -> SiteIndexValue:
    return Hagglund_1970.height_trajectory.picea_abies.northern_sweden(
        dominant_height=12.0,
        age=Age.DBH(40),
        age2=Age.TOTAL(100),
        latitude=63.0,
    )


# ---------------------------------------------------------------------------
# Validation branch coverage
# ---------------------------------------------------------------------------


def test_validate_site_index_species_type_error():
    si = _si_pine()
    si.species = [TreeSpecies.Sweden.pinus_sylvestris]
    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand._validate_site_index(si, TreeSpecies.Sweden.pinus_sylvestris)


# ---------------------------------------------------------------------------
# Stem estimators
# ---------------------------------------------------------------------------


def test_stems_spruce_north():
    si = _si_spruce()
    stems = ElfvingHagglundInitialStand.estimate_stems_young_spruce_north(
        altitude=200.0,
        site_index=si,
    )
    assert stems.species == TreeSpecies.Sweden.picea_abies
    assert float(stems) > 0


def test_stems_pine_south_paths():
    si = _si_pine()
    with pytest.raises(NotImplementedError):
        ElfvingHagglundInitialStand.estimate_stems_young_pine_south(
            latitude=60.0,
            site_index=si,
            dominant_height=10.0,
        )

    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand.estimate_stems_young_pine_south(
            latitude=60.0,
            site_index=si,
            dominant_height=10.0,
            age_at_breast_height=Age.TOTAL(30),
        )

    stems = ElfvingHagglundInitialStand.estimate_stems_young_pine_south(
        latitude=60.0,
        site_index=si,
        dominant_height=10.0,
        age_at_breast_height=Age.DBH(30),
    )
    assert stems.species == TreeSpecies.Sweden.pinus_sylvestris
    assert float(stems) > 0


def test_stems_spruce_south():
    si = _si_spruce()
    stems = ElfvingHagglundInitialStand.estimate_stems_young_spruce_south(
        altitude=150.0,
        site_index=si,
        age_at_breast_height=Age.DBH(30),
    )
    assert stems.species == TreeSpecies.Sweden.picea_abies
    assert float(stems) > 0


# ---------------------------------------------------------------------------
# Basal area estimators - Pine north
# ---------------------------------------------------------------------------


def test_ba_pine_north_branches():
    si = _si_pine()
    stems = ElfvingHagglundInitialStand.estimate_stems_young_pine_north(
        latitude=64.0,
        altitude=200.0,
        dominant_height=8.0,
    )
    ba = ElfvingHagglundInitialStand.estimate_basal_area_young_pine_north(
        latitude=64.0,
        altitude=200.0,
        site_index=si,
        dominant_height=8.0,
        stems=stems,
    )
    assert ba.species == TreeSpecies.Sweden.pinus_sylvestris
    assert float(ba) > 0

    ba2 = ElfvingHagglundInitialStand.estimate_basal_area_young_pine_north(
        latitude=64.0,
        altitude=200.0,
        site_index=si,
        dominant_height=8.0,
    )
    assert float(ba2) > 0

    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand.estimate_basal_area_young_pine_north(
            latitude=64.0,
            altitude=200.0,
            site_index=si,
            dominant_height=8.0,
            stems="bad",
        )


# ---------------------------------------------------------------------------
# Basal area estimators - Spruce north
# ---------------------------------------------------------------------------


def test_ba_spruce_north_branches():
    si = _si_spruce()
    stems = ElfvingHagglundInitialStand.estimate_stems_young_spruce_north(
        altitude=200.0,
        site_index=si,
    )
    ba = ElfvingHagglundInitialStand.estimate_basal_area_young_spruce_north(
        altitude=200.0,
        site_index=si,
        dominant_height=8.0,
        stems=stems,
    )
    assert ba.species == TreeSpecies.Sweden.picea_abies
    assert float(ba) > 0

    ba2 = ElfvingHagglundInitialStand.estimate_basal_area_young_spruce_north(
        altitude=200.0,
        site_index=si,
        dominant_height=8.0,
    )
    assert float(ba2) > 0

    with pytest.raises(ValueError):
        ElfvingHagglundInitialStand.estimate_basal_area_young_spruce_north(
            altitude=200.0,
            site_index=si,
            dominant_height=8.0,
            spatial_distribution=4,
        )

    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand.estimate_basal_area_young_spruce_north(
            altitude=200.0,
            site_index=si,
            dominant_height=8.0,
            stems="bad",
        )


# ---------------------------------------------------------------------------
# Basal area estimators - Pine south
# ---------------------------------------------------------------------------


def test_ba_pine_south_branches():
    si = _si_pine()
    stems = ElfvingHagglundInitialStand.estimate_stems_young_pine_south(
        latitude=60.0,
        site_index=si,
        dominant_height=10.0,
        age_at_breast_height=Age.DBH(30),
    )
    ba = ElfvingHagglundInitialStand.estimate_basal_area_young_pine_south(
        latitude=60.0,
        altitude=150.0,
        site_index=si,
        dominant_height=10.0,
        stems=stems,
    )
    assert ba.species == TreeSpecies.Sweden.pinus_sylvestris
    assert float(ba) > 0

    with pytest.raises(NotImplementedError):
        ElfvingHagglundInitialStand.estimate_basal_area_young_pine_south(
            latitude=60.0,
            altitude=150.0,
            site_index=si,
            dominant_height=10.0,
        )


# ---------------------------------------------------------------------------
# Basal area estimators - Spruce south
# ---------------------------------------------------------------------------


def test_ba_spruce_south_branches():
    si = _si_spruce()
    stems = ElfvingHagglundInitialStand.estimate_stems_young_spruce_south(
        altitude=150.0,
        site_index=si,
        age_at_breast_height=Age.DBH(30),
    )
    ba = ElfvingHagglundInitialStand.estimate_basal_area_young_spruce_south(
        altitude=150.0,
        site_index=si,
        dominant_height=10.0,
        age_at_breast_height=Age.DBH(30),
        stems=stems,
    )
    assert ba.species == TreeSpecies.Sweden.picea_abies
    assert float(ba) > 0

    ba2 = ElfvingHagglundInitialStand.estimate_basal_area_young_spruce_south(
        altitude=150.0,
        site_index=si,
        dominant_height=10.0,
        age_at_breast_height=Age.DBH(30),
    )
    assert float(ba2) > 0

    with pytest.raises(ValueError):
        ElfvingHagglundInitialStand.estimate_basal_area_young_spruce_south(
            altitude=150.0,
            site_index=si,
            dominant_height=10.0,
            age_at_breast_height=Age.DBH(30),
            spatial_distribution=4,
        )

    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand.estimate_basal_area_young_spruce_south(
            altitude=150.0,
            site_index=si,
            dominant_height=10.0,
            age_at_breast_height=Age.DBH(30),
            stems="bad",
        )


# ---------------------------------------------------------------------------
# Combined estimator
# ---------------------------------------------------------------------------


def test_combined_spruce_stand_paths():
    si = _si_spruce()
    age = Age.DBH(30)
    stems_n, ba_n = ElfvingHagglundInitialStand.estimate_initial_spruce_stand(
        dominant_height=10.0,
        age_bh=age,
        site_index=si,
        altitude=150.0,
        northern_sweden=True,
    )
    assert float(stems_n) > 0 and float(ba_n) > 0

    stems_s, ba_s = ElfvingHagglundInitialStand.estimate_initial_spruce_stand(
        dominant_height=10.0,
        age_bh=age,
        site_index=si,
        altitude=150.0,
        northern_sweden=False,
    )
    assert float(stems_s) > 0 and float(ba_s) > 0

    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand.estimate_initial_spruce_stand(
            dominant_height=10,
            age_bh=age,
            site_index=si,
            altitude=150.0,
        )

    with pytest.raises(ValueError):
        ElfvingHagglundInitialStand.estimate_initial_spruce_stand(
            dominant_height=10.0,
            age_bh=Age.TOTAL(30),
            site_index=si,
            altitude=150.0,
        )


def test_error_branches(monkeypatch):
    si_p = _si_pine()
    si_s = _si_spruce()
    monkeypatch.setattr(ElfvingHagglundInitialStand, "_validate_site_index", lambda *a, **k: None)

    with pytest.raises(ValueError):
        ElfvingHagglundInitialStand.estimate_stems_young_spruce_north(
            altitude=100.0,
            site_index=si_s,
            stand_density_factor=2.0,
        )
    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand.estimate_stems_young_spruce_north(
            altitude=100.0,
            site_index="bad",
        )

    with pytest.raises(ValueError):
        ElfvingHagglundInitialStand.estimate_stems_young_pine_south(
            latitude=60.0,
            site_index=si_p,
            dominant_height=10.0,
            stand_density_factor=0.0,
            age_at_breast_height=Age.DBH(30),
        )
    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand.estimate_stems_young_pine_south(
            latitude=60.0,
            site_index=si_p,
            dominant_height=10,
            age_at_breast_height=Age.DBH(30),
        )
    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand.estimate_stems_young_pine_south(
            latitude=60.0,
            site_index="bad",
            dominant_height=10.0,
            age_at_breast_height=Age.DBH(30),
        )

    with pytest.raises(ValueError):
        ElfvingHagglundInitialStand.estimate_stems_young_spruce_south(
            altitude=100.0,
            site_index=si_s,
            age_at_breast_height=Age.DBH(30),
            stand_density_factor=2.0,
        )
    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand.estimate_stems_young_spruce_south(
            altitude=100.0,
            site_index="bad",
            age_at_breast_height=Age.DBH(30),
        )
    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand.estimate_stems_young_spruce_south(
            altitude=100.0,
            site_index=si_s,
            age_at_breast_height=Age.TOTAL(30),
        )

    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand.estimate_basal_area_young_pine_north(
            latitude=64.0,
            altitude=200.0,
            site_index=si_p,
            dominant_height=8,
        )
    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand.estimate_basal_area_young_pine_north(
            latitude=64.0,
            altitude=200.0,
            site_index="bad",
            dominant_height=8.0,
        )

    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand.estimate_basal_area_young_spruce_north(
            altitude=200.0,
            site_index=si_s,
            dominant_height=8,
        )
    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand.estimate_basal_area_young_spruce_north(
            altitude=200.0,
            site_index="bad",
            dominant_height=8.0,
        )

    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand.estimate_basal_area_young_pine_south(
            latitude=60.0,
            altitude=150.0,
            site_index=si_p,
            dominant_height=10,
        )
    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand.estimate_basal_area_young_pine_south(
            latitude=60.0,
            altitude=150.0,
            site_index="bad",
            dominant_height=10.0,
        )
    ElfvingHagglundInitialStand.estimate_basal_area_young_pine_south(
        latitude=60.0,
        altitude=150.0,
        site_index=si_p,
        dominant_height=10.0,
        age_at_breast_height=Age.DBH(30),
    )
    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand.estimate_basal_area_young_pine_south(
            latitude=60.0,
            altitude=150.0,
            site_index=si_p,
            dominant_height=10.0,
            stems="bad",
            age_at_breast_height=Age.DBH(30),
        )

    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand.estimate_basal_area_young_spruce_south(
            altitude=150.0,
            site_index=si_s,
            dominant_height=10,
            age_at_breast_height=Age.DBH(30),
        )
    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand.estimate_basal_area_young_spruce_south(
            altitude=150.0,
            site_index="bad",
            dominant_height=10.0,
            age_at_breast_height=Age.DBH(30),
        )
    with pytest.raises(ValueError):
        ElfvingHagglundInitialStand.estimate_basal_area_young_spruce_south(
            altitude=150.0,
            site_index=si_s,
            dominant_height=10.0,
            age_at_breast_height=None,
        )

    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand.estimate_initial_spruce_stand(
            dominant_height=10.0,
            age_bh=30,
            site_index=si_s,
            altitude=100.0,
        )
    with pytest.raises(TypeError):
        ElfvingHagglundInitialStand.estimate_initial_spruce_stand(
            dominant_height=10.0,
            age_bh=Age.DBH(30),
            site_index=object(),
            altitude=100.0,
        )
