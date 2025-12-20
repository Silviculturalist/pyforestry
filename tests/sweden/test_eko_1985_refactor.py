import math

import pytest

from pyforestry.base.helpers import Age, Stand, TreeSpecies
from pyforestry.base.helpers.primitives import StandBasalArea, Stems
from pyforestry.sweden.models.eko_1985_refactor import (
    DominantHeightObservation,
    Eko1985Cohort,
    Eko1985Model,
    Eko1985SiteContext,
    Eko1985Stand,
    _coerce_age,
    _coerce_species,
    _safe_log,
    _safe_qmd,
    _safe_sum,
    _species_label,
    qmd_cm,
)


def _as_float(value) -> float:
    """Return a float for plain numbers or StandVolume-like objects."""
    try:
        return float(value)
    except TypeError:
        return value


def _make_simple_stand() -> Eko1985Stand:
    site_context = Eko1985SiteContext(
        latitude=62.0,
        longitude=18.0,
        altitude=120.0,
        vegetation=13,
        soil_moisture=3,
        spruce_site_index=20.0,
        pine_site_index=20.0,
    )
    cohorts = [
        Eko1985Cohort.from_values(TreeSpecies.Sweden.picea_abies, 10.0, 800.0, 40),
        Eko1985Cohort.from_values(TreeSpecies.Sweden.pinus_sylvestris, 8.0, 600.0, 45),
    ]
    return Eko1985Stand(cohorts, site_context)


def test_engine_cohorts_match_legacy_growth_south():
    site_kwargs = {
        "latitude": 55.0,
        "longitude": 13.0,
        "altitude": 120.0,
        "vegetation": 13,
        "soil_moisture": 3,
        "spruce_site_index": 24.0,
        "pine_site_index": 22.0,
        "fertilised": True,
        "thinned": True,
    }
    site_context = Eko1985SiteContext(**site_kwargs)
    cohorts = [
        Eko1985Cohort.from_values(TreeSpecies.Sweden.betula_pendula, 12.0, 800.0, 45),
        Eko1985Cohort.from_values(TreeSpecies.Sweden.alnus_glutinosa, 6.0, 520.0, 35),
        Eko1985Cohort.from_values(TreeSpecies.Sweden.fagus_sylvatica, 7.5, 410.0, 60),
        Eko1985Cohort.from_values(TreeSpecies.Sweden.quercus_robur, 6.0, 300.0, 70),
    ]
    stand = Eko1985Stand(cohorts, site_context)

    stand.grow(years=5)

    expected = {
        "betula pendula": {
            "basal_area": 14.387561292012318,
            "stems": 794.72,
            "qmd": 15.1824402754655,
            "volume": 4.471694711874658e-07,
            "bai5": 2.466761292012318,
            "volume_increment": -1.6445733006677021e-06,
        },
        "alnus glutinosa": {
            "basal_area": 5.9604,
            "stems": 516.568,
            "qmd": 12.120736576699848,
            "volume": 2530622898.3846,
            "bai5": 3.42332514593998e-60,
            "volume_increment": 43301124.12402272,
        },
        "fagus sylvatica": {
            "basal_area": 8.384518812705561,
            "stems": 407.294,
            "qmd": 16.189749343735564,
            "volume": 62.88541094427544,
            "bai5": 0.9340188127055613,
            "volume_increment": 9.02944568740834,
        },
        "quercus robur": {
            "basal_area": 6.150623530742213,
            "stems": 298.02,
            "qmd": 16.21033264230532,
            "volume": 62.18972591606505,
            "bai5": 0.1902235307422133,
            "volume_increment": 2.5924046193831813,
        },
    }

    for cohort in stand.cohorts:
        expected_vals = expected[cohort.species.full_name]
        assert float(cohort.basal_area) == pytest.approx(expected_vals["basal_area"])
        assert float(cohort.stems) == pytest.approx(expected_vals["stems"])
        assert float(cohort.qmd) == pytest.approx(expected_vals["qmd"])
        assert float(cohort.volume) == pytest.approx(expected_vals["volume"])
        assert cohort.bai5 == pytest.approx(expected_vals["bai5"])
        assert _as_float(cohort.volume_increment) == pytest.approx(
            expected_vals["volume_increment"]
        )

    snapshot = stand.snapshot()["stand"]
    assert float(snapshot["basal_area"]) == pytest.approx(34.883103635460095)
    assert float(snapshot["stems"]) == pytest.approx(2016.602)
    assert float(snapshot["qmd"]) == pytest.approx(14.840636289755377)
    assert float(snapshot["volume"]) == pytest.approx(2530623023.4597373)


def test_birch_engine_matches_legacy_north():
    site_kwargs = {
        "latitude": 64.5,
        "longitude": 18.0,
        "altitude": 200.0,
        "vegetation": 14,
        "soil_moisture": 3,
        "spruce_site_index": 18.0,
        "pine_site_index": 18.0,
        "thinned_5y": True,
    }
    site_context = Eko1985SiteContext(**site_kwargs)
    cohort = Eko1985Cohort.from_values(TreeSpecies.Sweden.betula_pubescens, 8.0, 1200.0, 30)
    stand = Eko1985Stand([cohort], site_context)

    stand.grow(years=5)

    cohort_updated = stand.cohorts[0]
    assert float(cohort_updated.basal_area) == pytest.approx(7.9300872)
    assert float(cohort_updated.stems) == pytest.approx(1189.51308)
    assert float(cohort_updated.qmd) == pytest.approx(9.213177319235614)
    assert float(cohort_updated.volume) == pytest.approx(37.89618831125041)
    assert cohort_updated.bai5 == pytest.approx(1.2675470841550272e-40)
    assert _as_float(cohort_updated.volume_increment) == pytest.approx(0.7810252416708963)


def test_helper_functions_and_species_labels():
    assert qmd_cm(0.0, 100.0) == 0.0
    assert qmd_cm(10.0, 100.0) > 0.0
    assert _safe_sum([1, 2.5, 3]) == pytest.approx(6.5)
    assert float(_safe_qmd(0.0, 100.0)) == 0.0
    assert float(_safe_qmd(10.0, 100.0)) > 0.0

    assert _coerce_age(Age.TOTAL(10)) == Age.TOTAL(10)
    assert _coerce_age(10).code == Age.TOTAL.value

    assert _coerce_species(TreeSpecies.Sweden.picea_abies) == TreeSpecies.Sweden.picea_abies
    assert _coerce_species("Pinus sylvestris") == TreeSpecies.Sweden.pinus_sylvestris

    assert _safe_log(None) == pytest.approx(math.log(1e-9))
    assert _safe_log("bad") == pytest.approx(math.log(1e-9))
    assert _safe_log(-1.0) == pytest.approx(math.log(1e-9))
    assert _safe_log(1.0) == pytest.approx(0.0)

    assert _species_label(TreeSpecies.Sweden.picea_abies) == "Gran"
    assert _species_label(TreeSpecies.Sweden.pinus_sylvestris) == "Tall"
    assert _species_label(TreeSpecies.Sweden.betula_pendula) == "Björk"
    assert _species_label(TreeSpecies.Sweden.fagus_sylvatica) == "Bok"
    assert _species_label(TreeSpecies.Sweden.quercus_robur) == "Ek"
    assert _species_label(TreeSpecies.Sweden.alnus_glutinosa) == "Öv.löv"

    obs = DominantHeightObservation.from_values(12.5, 30)
    assert obs.age == Age.TOTAL(30.0)


def test_cohort_update_from_engine_handles_missing_values():
    class DummyPart:
        BA = 12.0
        stems = 900.0
        age = 40.0
        HK = None
        BAOtherSpecies = None
        QMDOtherSpecies = None
        VOL = None
        BAI5 = None
        gross_volume_increment = None
        volume_increment = None

    cohort = Eko1985Cohort.from_values(TreeSpecies.Sweden.picea_abies, 10.0, 800.0, 40)
    cohort.update_from_engine(DummyPart())

    assert cohort.volume is None
    assert cohort.gross_volume_increment is None
    assert cohort.volume_increment is None


def test_stand_requires_cohorts():
    site_context = Eko1985SiteContext(
        latitude=62.0,
        longitude=18.0,
        altitude=120.0,
        vegetation=13,
        soil_moisture=3,
        spruce_site_index=20.0,
        pine_site_index=20.0,
    )

    with pytest.raises(ValueError, match="cohort"):
        Eko1985Stand([], site_context)


def test_stand_thin_volume_and_growth_paths():
    stand = _make_simple_stand()

    stand.thin(
        {
            TreeSpecies.Sweden.picea_abies: 0.5,
            TreeSpecies.Sweden.pinus_sylvestris: 0.2,
            "Other": 0.0,
        }
    )

    totals = stand.stand_totals()
    assert float(totals["basal_area"]) >= 0.0

    volume = stand.volume_for(stand.cohorts[0])
    assert float(volume) >= 0.0

    stand.grow5(apply_mortality=False)
    stand._engine_stand.grow5()
    assert stand._engine_stand.getMAI(10.0, 5.0) == pytest.approx(2.0)


def test_eko1985_model_updates_aggregate_context():
    site_context = Eko1985SiteContext(
        latitude=62.0,
        longitude=18.0,
        altitude=120.0,
        vegetation=13,
        soil_moisture=3,
        spruce_site_index=20.0,
        pine_site_index=20.0,
    )
    cohorts = [
        Eko1985Cohort.from_values(TreeSpecies.Sweden.picea_abies, 10.0, 800.0, 40),
        Eko1985Cohort.from_values(TreeSpecies.Sweden.pinus_sylvestris, 8.0, 600.0, 45),
    ]

    stand = Stand()
    ba_metrics = {}
    stems_metrics = {}
    total_ba = 0.0
    total_stems = 0.0
    for cohort in cohorts:
        species = cohort.species
        ba_val = float(cohort.basal_area)
        stems_val = float(cohort.stems)
        ba_metrics[species] = StandBasalArea(ba_val, species=species, precision=0.0)
        stems_metrics[species] = Stems(stems_val, species=species, precision=0.0)
        total_ba += ba_val
        total_stems += stems_val
    ba_metrics["TOTAL"] = StandBasalArea(total_ba, species=None, precision=0.0)
    stems_metrics["TOTAL"] = Stems(total_stems, species=None, precision=0.0)
    stand._metric_estimates = {"BasalArea": ba_metrics, "Stems": stems_metrics}

    model = Eko1985Model(site_context=site_context)
    ctx = model.build_context(
        stand,
        cohort_ages={
            TreeSpecies.Sweden.picea_abies: 40.0,
            TreeSpecies.Sweden.pinus_sylvestris: 45.0,
        },
    )

    ctx.update_step(5.0)

    expected_site_context = Eko1985SiteContext(
        latitude=62.0,
        longitude=18.0,
        altitude=120.0,
        vegetation=13,
        soil_moisture=3,
        spruce_site_index=20.0,
        pine_site_index=20.0,
    )
    expected_stand = Eko1985Stand(
        [
            Eko1985Cohort.from_values(TreeSpecies.Sweden.picea_abies, 10.0, 800.0, 40),
            Eko1985Cohort.from_values(TreeSpecies.Sweden.pinus_sylvestris, 8.0, 600.0, 45),
        ],
        expected_site_context,
    )
    expected_stand.grow(years=5.0)

    for cohort in expected_stand.cohorts:
        assert float(ctx.metrics["BasalArea"][cohort.species]) == pytest.approx(
            float(cohort.basal_area)
        )
        assert float(ctx.metrics["Stems"][cohort.species]) == pytest.approx(float(cohort.stems))

    age_map = ctx.state["cohort_ages"]
    for cohort in expected_stand.cohorts:
        assert age_map[cohort.species.full_name] == pytest.approx(float(cohort.age))
    assert ctx.state["years_since_thin"] == pytest.approx(5.0)
