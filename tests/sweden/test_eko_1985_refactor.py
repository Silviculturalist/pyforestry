import math

import pytest

from pyforestry.base.helpers import Age, Stand, TreeSpecies
from pyforestry.base.helpers.primitives import StandBasalArea, Stems
from pyforestry.sweden.blocks.eko1985 import (
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

    # Corrected Eko 1985 output after the Dg-units, vegetation-indicator, birch
    # altitude, broadleaf-South volume-constant, ProdMod2 mortality, and the
    # South-broadleaf SI 240-280 dm BAI-scaling fixes.
    #
    # The alnus ("Others") volume (998.5 m3/ha, form height ~141 m) is the faithful
    # Eko 1985 Tabell 10f Syd output, NOT a transcription bug: its TG (total stand
    # basal area) term, exp(0.859600e-01 * TG), extrapolates far above the physical
    # range for a small broadleaf cohort in this dense (35.5 m2/ha) mixed stand. This
    # is the canonical default; set broadleaf_volume_prodmod=True for the physical
    # ProdMod2 remap -- see test_broadleaf_volume_prodmod_makes_south_physical.
    expected = {
        "betula pendula": {
            "basal_area": 14.150884903465201,
            "stems": 780.0,
            "qmd": 15.198459036298637,
            "volume": 153.93748857865685,
            "bai5": 2.4508849034652025,
            "volume_increment": 29.168871777949107,
        },
        "alnus glutinosa": {
            "basal_area": 7.059392467029466,
            "stems": 508.04,
            "qmd": 13.301167705664586,
            "volume": 998.5046349063624,
            "bai5": 1.1973924670294656,
            "volume_increment": 143.11782323876378,
        },
        "fagus sylvatica": {
            "basal_area": 8.246816300105099,
            "stems": 400.57,
            "qmd": 16.19045334219603,
            "volume": 61.94898386390469,
            "bai5": 0.9193163001050999,
            "volume_increment": 8.093018607037585,
        },
        "quercus robur": {
            "basal_area": 6.050866260587777,
            "stems": 293.1,
            "qmd": 16.212721671833187,
            "volume": 61.272424561044275,
            "bai5": 0.18886626058777747,
            "volume_increment": 1.6751032643624058,
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
    assert float(snapshot["basal_area"]) == pytest.approx(35.50795993118754)
    assert float(snapshot["stems"]) == pytest.approx(1981.71)
    assert float(snapshot["qmd"]) == pytest.approx(15.104204931467352)
    assert float(snapshot["volume"]) == pytest.approx(1275.6635319099682)


def test_broadleaf_volume_prodmod_makes_south_physical():
    """The ``broadleaf_volume_prodmod`` flag remaps birch + 'Others' South volumes.

    Ekö 1985 Tabell 10c/10f publish region-specific Syd functions for birch and
    övrigt löv; ProdMod2 instead pools both to the Nord+Mellan function in every
    region (its coefficient table is region-identical at INDEX_BIRCH / INDEX_OTHER).
    Setting ``broadleaf_volume_prodmod=True`` opts into that. It notably rescues the
    non-physical "Others" Syd volume (~141 m form height, pinned in
    ``test_engine_cohorts_match_legacy_growth_south``) to a physical ~7.5 m. Beech and
    oak have a single volume function each and are untouched by the flag.
    """
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
        "broadleaf_volume_prodmod": True,
    }
    cohorts = [
        Eko1985Cohort.from_values(TreeSpecies.Sweden.betula_pendula, 12.0, 800.0, 45),
        Eko1985Cohort.from_values(TreeSpecies.Sweden.alnus_glutinosa, 6.0, 520.0, 35),
        Eko1985Cohort.from_values(TreeSpecies.Sweden.fagus_sylvatica, 7.5, 410.0, 60),
        Eko1985Cohort.from_values(TreeSpecies.Sweden.quercus_robur, 6.0, 300.0, 70),
    ]
    stand = Eko1985Stand(cohorts, Eko1985SiteContext(**site_kwargs))
    stand.grow(years=5)

    by_name = {c.species.full_name: c for c in stand.cohorts}
    # "Others" (alnus): Nord+Mellan -> physical (the canonical Syd default is ~141 m).
    alnus = by_name["alnus glutinosa"]
    assert float(alnus.volume) == pytest.approx(53.201907666719514)
    assert 4.0 < float(alnus.volume) / float(alnus.basal_area) < 12.0
    assert _as_float(alnus.volume_increment) == pytest.approx(11.47132845801616)
    # Birch (betula) also switches to its Nord+Mellan function (birch Syd is physical
    # too, so this only nudges the value).
    betula = by_name["betula pendula"]
    assert float(betula.volume) == pytest.approx(154.85712879385426)
    assert 5.0 < float(betula.volume) / float(betula.basal_area) < 15.0
    assert _as_float(betula.volume_increment) == pytest.approx(32.42429519075557)
    # Beech and oak use a single volume function -> unchanged from the canonical run.
    assert float(by_name["fagus sylvatica"].volume) == pytest.approx(61.94898386390469)
    assert float(by_name["quercus robur"].volume) == pytest.approx(61.272424561044275)
    assert float(stand.snapshot()["stand"]["volume"]) == pytest.approx(331.28044488552274)


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

    # These coordinates (lat 64.5, lon 18) resolve to climate zone K1 = the Central
    # region, where the ProdMod2 mortality groups with South (localisation != 0).
    # Value reflects the altitude-coefficient fix (-0.462992 -> -0.462992e-03) and
    # the ProdMod2 mortality port.
    cohort_updated = stand.cohorts[0]
    assert float(cohort_updated.basal_area) == pytest.approx(9.947239911784541)
    assert float(cohort_updated.stems) == pytest.approx(1170.0)
    assert float(cohort_updated.qmd) == pytest.approx(10.40431337928945)
    assert float(cohort_updated.volume) == pytest.approx(50.59589247078843)
    assert cohort_updated.bai5 == pytest.approx(2.1472399117845415)
    assert _as_float(cohort_updated.volume_increment) == pytest.approx(13.480729401208912)


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
        ba = 12.0
        stems = 900.0
        age = 40.0
        hk = None
        ba_other_species = None
        qmd_other_species = None
        vol = None
        bai5 = None
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
    assert stand._engine_stand.get_mai(10.0, 5.0) == pytest.approx(2.0)


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


def _eko_site_context() -> Eko1985SiteContext:
    return Eko1985SiteContext(
        latitude=62.0,
        longitude=18.0,
        altitude=120.0,
        vegetation=13,
        soil_moisture=3,
        spruce_site_index=20.0,
        pine_site_index=20.0,
    )


def _eko_stand_with_metrics(cohorts) -> Stand:
    stand = Stand()
    ba_metrics, stems_metrics = {}, {}
    total_ba = total_stems = 0.0
    for cohort in cohorts:
        sp = cohort.species
        ba_metrics[sp] = StandBasalArea(float(cohort.basal_area), species=sp, precision=0.0)
        stems_metrics[sp] = Stems(float(cohort.stems), species=sp, precision=0.0)
        total_ba += float(cohort.basal_area)
        total_stems += float(cohort.stems)
    ba_metrics["TOTAL"] = StandBasalArea(total_ba, species=None, precision=0.0)
    stems_metrics["TOTAL"] = Stems(total_stems, species=None, precision=0.0)
    stand._metric_estimates = {"BasalArea": ba_metrics, "Stems": stems_metrics}
    return stand


def test_eko1985_model_describable_metadata():
    model = Eko1985Model(site_context=_eko_site_context())
    assert model.component_id == "eko_1985"
    # Ekö with the diaeresis: the author is Per-Magnus Ekö, not "Eko".
    assert model.source.author == "Ekö, P.-M."
    assert model.source.year == 1985
    assert model.source.title.startswith("En produktionsmodell för skog i Sverige")
    assert model.requirements().inventory == "aggregate"


def test_eko1985_model_thinning_action_reduces_basal_area():
    cohorts = [
        Eko1985Cohort.from_values(TreeSpecies.Sweden.picea_abies, 12.0, 800.0, 40),
        Eko1985Cohort.from_values(TreeSpecies.Sweden.pinus_sylvestris, 8.0, 600.0, 45),
    ]
    model = Eko1985Model(site_context=_eko_site_context())
    ctx = model.build_context(
        _eko_stand_with_metrics(cohorts),
        cohort_ages={
            TreeSpecies.Sweden.picea_abies: 40.0,
            TreeSpecies.Sweden.pinus_sylvestris: 45.0,
        },
    )
    ctx.state["years_since_thin"] = 10.0
    actions = model.available_actions()
    assert "thin_basal_area" in actions

    ba_before = float(ctx.metrics["BasalArea"][TreeSpecies.Sweden.picea_abies])
    actions["thin_basal_area"].fn(ctx, removals={TreeSpecies.Sweden.picea_abies: 3.0})
    ba_after = float(ctx.metrics["BasalArea"][TreeSpecies.Sweden.picea_abies])
    assert ba_after < ba_before
    assert ctx.state["years_since_thin"] == 0.0


def test_eko1985_model_default_age_without_cohort_ages():
    cohorts = [Eko1985Cohort.from_values(TreeSpecies.Sweden.picea_abies, 12.0, 800.0, 40)]
    model = Eko1985Model(site_context=_eko_site_context(), default_age=40.0)
    ctx = model.build_context(_eko_stand_with_metrics(cohorts))  # no cohort_ages -> default
    ctx.update_step(5.0)
    assert ctx.metrics["BasalArea"][TreeSpecies.Sweden.picea_abies] is not None


def test_eko1985_model_total_only_metrics_use_single_species():
    stand = Stand()
    stand._metric_estimates = {
        "BasalArea": {"TOTAL": StandBasalArea(20.0, species=None, precision=0.0)},
        "Stems": {"TOTAL": Stems(1400.0, species=None, precision=0.0)},
    }
    model = Eko1985Model(site_context=_eko_site_context())
    ctx = model.build_context(stand, cohort_ages={TreeSpecies.Sweden.picea_abies: 40.0})
    ctx.update_step(5.0)
    assert ctx.metrics["BasalArea"]["TOTAL"] is not None


def test_eko1985_model_requires_age_information():
    cohorts = [Eko1985Cohort.from_values(TreeSpecies.Sweden.picea_abies, 12.0, 800.0, 40)]
    model = Eko1985Model(site_context=_eko_site_context())
    with pytest.raises(ValueError):
        model.build_context(_eko_stand_with_metrics(cohorts))  # no ages, no default


def test_eko1985_model_requires_a_site_context():
    model = Eko1985Model()
    with pytest.raises(ValueError):
        model._resolve_site_context(site_context=None)
