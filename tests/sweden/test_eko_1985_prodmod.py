"""Validate the Eko 1985 engine against PRODMOD reference outputs.

The reference values below are the growth trajectories produced by PRODMOD (Eko's
own growth-and-yield program) for the example stands shipped in the ``PRODMOD
examples`` workbooks. Each case gives the per-species stand state at the start of
a five-year period and the state PRODMOD reports at the end; the engine is run
from the start state and its post-growth basal area, stems and QMD are compared.

The reproduce test runs with ``broadleaf_growth_prodmod`` on, because the workbooks
carry ProdMod2's own behaviour (broadleaf SI-class keyed off the stand spruce index,
diameter-limit clamps on the BAI inputs, and the +0.609667 oak constant). The
dissertation default is exercised in ``test_dissertation_defaults_differ_from_prodmod``.

Scope notes
-----------
* **Volume** in those workbooks is a form-height / Naslund-style volume, *not*
  Eko's aggregate volume function, so it is validated separately below against an
  independent transcription of the Tabell 10 coefficients (units: Dg in metres,
  SI in dm), rather than against the workbook.
* **Natural mortality** uses the HUGIN functions (Bengtsson 1979, cf. Hagglund
  1981a); stem counts are checked with a looser tolerance than basal area / QMD.
* **Site index** is a site property, per Ekö 1985: every non-pine function uses
  H100 spruce (dm) and pine uses H100 pine (dm). The ``site_dm`` entries in the case
  tuples are vestigial -- the cohorts read the site's spruce/pine index directly.
* ``oak`` is only exercised at a mature start (mix_1); at the synthetic age-10
  starts it sits well outside the fitting range of Eko's oak function.
"""

from math import exp, log

import pytest

from pyforestry.sweden.blocks.eko1985 import EkoStandSite, EngineStand
from pyforestry.sweden.blocks.eko1985.cohorts import (
    BeechEngineCohort,
    BirchEngineCohort,
    BroadleafEngineCohort,
    OakEngineCohort,
    PineEngineCohort,
    SpruceEngineCohort,
)

_COHORT_CLS = {
    "pinus_sylvestris": PineEngineCohort,
    "picea_abies": SpruceEngineCohort,
    "betula_pendula": BirchEngineCohort,
    "fagus_sylvatica": BeechEngineCohort,
    "quercus_robur": OakEngineCohort,
    "alnus_glutinosa": BroadleafEngineCohort,
}

# Default relative tolerances. Basal-area growth and QMD track PRODMOD closely;
# stems inherit the mortality approximation, hence a wider band.
_DEFAULT_TOL = {"ba": 0.05, "qmd": 0.03, "stems": 0.04}

# Each case: cohorts are (species, BA m2/ha, stems/ha, breast-height age, SI dm);
# expected is species -> (BA, stems, QMD) at the end of a 5-year period.
CASES = [
    {
        "id": "pine_1: pine North, start->grow",
        "region": "North",
        "lat": 62.0,
        "alt": 536.0,
        "veg": None,
        "soil": 5,
        "site_pine_dm": 120.0,
        "site_spruce_dm": 280.0,
        "thinned": False,
        "tol": {"ba": 0.01, "qmd": 0.005, "stems": 0.01},
        "cohorts": [("pinus_sylvestris", 15.0, 600.0, 70.0, 120.0)],
        "expected": {
            "pinus_sylvestris": (16.337647594057636, 595.8, 18.685278353157315),
        },
    },
    {
        "id": "pine_1: pine North, thinned->grow",
        "region": "North",
        "lat": 62.0,
        "alt": 536.0,
        "veg": None,
        "soil": 5,
        "site_pine_dm": 120.0,
        "site_spruce_dm": 280.0,
        "thinned": True,
        "tol": {"ba": 0.01, "qmd": 0.005, "stems": 0.01},
        "cohorts": [("pinus_sylvestris", 11.436353315840345, 446.85, 75.0, 120.0)],
        "expected": {
            "pinus_sylvestris": (12.61160481032401, 443.72205, 19.02325067113161),
        },
    },
    {
        "id": "birch_1: birch South, start->grow",
        "region": "South",
        "lat": 56.0,
        "alt": 100.0,
        "veg": 1,
        "soil": 3,
        "site_pine_dm": 220.0,
        "site_spruce_dm": 220.0,
        "thinned": False,
        "cohorts": [("betula_pendula", 12.0, 3500.0, 15.0, 220.0)],
        "expected": {
            "betula_pendula": (16.958930782826027, 3412.5, 7.954592989197906),
        },
    },
    {
        "id": "mix_2: 6-species South mix, start->grow (oak excluded from asserts)",
        "region": "South",
        "lat": 56.0,
        "alt": 500.0,
        "veg": None,
        "soil": 3,
        "site_pine_dm": 220.0,
        "site_spruce_dm": 245.0,
        "thinned": False,
        "cohorts": [  # all six species present, for correct competition
            ("pinus_sylvestris", 5.0, 500.0, 10.0, 220.0),
            ("picea_abies", 5.0, 500.0, 10.0, 245.0),
            ("betula_pendula", 5.0, 500.0, 10.0, 169.0),
            ("fagus_sylvatica", 5.0, 500.0, 10.0, 170.0),
            ("quercus_robur", 5.0, 500.0, 10.0, 170.0),
            ("alnus_glutinosa", 5.0, 500.0, 10.0, 170.0),
        ],
        "expected": {
            "pinus_sylvestris": (6.9746147058084205, 484.7407, 13.535067534360259),
            "picea_abies": (8.033051087208548, 490.066558, 14.446671251115136),
            "betula_pendula": (7.290117357568037, 487.5, 13.798599487027724),
            "fagus_sylvatica": (7.083249296358994, 486.197175, 13.619623663443486),
            "alnus_glutinosa": (6.792376595735822, 486.197175, 13.337048245995318),
        },
    },
    {
        "id": "test4: 6-species North mix, thinned->grow",
        "region": "North",
        "lat": 61.52,
        "alt": 250.0,
        "veg": 13,
        "soil": 5,
        "site_pine_dm": 220.0,
        "site_spruce_dm": 256.0,
        "thinned": True,
        "cohorts": [  # all six species present, for correct competition
            ("pinus_sylvestris", 5.658815706737735, 141.28759945500002, 25.0, 220.0),
            ("picea_abies", 5.975525164219613, 149.1884085, 25.0, 256.0),
            ("betula_pendula", 5.309379085471553, 139.0120275, 25.0, 141.0),
            ("fagus_sylvatica", 6.274314608462733, 147.375, 25.0, 220.0),
            ("quercus_robur", 5.9700673403235545, 140.00625, 25.0, 220.0),
            ("alnus_glutinosa", 5.944643702459919, 147.375, 25.0, 220.0),
        ],
        "expected": {
            "pinus_sylvestris": (6.482029428319408, 139.853818438269, 24.292566165700045),
            "picea_abies": (6.820832494544323, 148.30128771788452, 24.199215686769325),
            "fagus_sylvatica": (7.542180343426765, 144.7959375, 25.75285171086628),
        },
    },
    {
        "id": "mix_1: mature oak North, start->grow",
        "region": "North",
        "lat": 62.0,
        "alt": 536.0,
        "veg": 1,
        "soil": 3,
        "site_pine_dm": 220.0,
        "site_spruce_dm": 280.0,
        "thinned": False,
        # The degenerate 'beech' cohort (1.5e6 stems, BA~1) is left out; its
        # basal area is negligible for oak's competition.
        "cohorts": [
            ("picea_abies", 5.0, 250.0, 20.0, 280.0),
            ("betula_pendula", 12.0, 1500.0, 15.0, 220.0),
            ("quercus_robur", 30.0, 70.0, 80.0, 180.0),
        ],
        "expected": {
            "quercus_robur": (31.498800598909686, 68.775, 76.36366581097366),
        },
    },
    {
        # First stand with dry soil, so the only test of the TORR mortality/growth
        # term. PRODMOD keys the region on the Omrade field (Nord), not climate zone.
        "id": "central_mix: North pine/spruce/birch, dry soil, start->grow",
        "region": "North",
        "lat": 61.0,
        "alt": 300.0,
        "veg": 1,
        "soil": 1,
        "site_pine_dm": 220.0,
        "site_spruce_dm": 245.0,
        "thinned": False,
        "cohorts": [
            ("pinus_sylvestris", 14.0, 700.0, 55.0, 220.0),
            ("picea_abies", 12.0, 900.0, 50.0, 245.0),
            ("betula_pendula", 6.0, 600.0, 45.0, 200.0),
        ],
        "expected": {
            "pinus_sylvestris": (15.549935417474776, 693.1304408, 16.900979223223604),
            "picea_abies": (13.749913991489105, 891.5709645, 14.01286996297643),
            "betula_pendula": (6.704000957623414, 584.98446, 12.079526989561575),
        },
    },
    {
        # Pure spruce at SI 28 m (the >=260 dm branch). Stems match PRODMOD exactly.
        "id": "pure_spruce: North SI28, start->grow",
        "region": "North",
        "lat": 61.5,
        "alt": 350.0,
        "veg": 13,
        "soil": 3,
        "site_pine_dm": 220.0,
        "site_spruce_dm": 280.0,
        "thinned": False,
        "tol": {"ba": 0.02, "qmd": 0.01, "stems": 0.005},
        "cohorts": [("picea_abies", 20.0, 750.0, 65.0, 280.0)],
        "expected": {"picea_abies": (22.184931147476966, 742.8279675, 19.500240993678407)},
    },
    {
        # Dense pure spruce (~2900 stems, BA ~37): high-density stress. The engine
        # tracks PRODMOD to <0.03%, so the birch high-density drift is birch-specific.
        "id": "pure_spruce: dense North (2900 st, BA 37), settled->grow",
        "region": "North",
        "lat": 64.0,
        "alt": 300.0,
        "veg": 13,
        "soil": 3,
        "site_pine_dm": 220.0,
        "site_spruce_dm": 260.0,
        "thinned": False,
        "tol": {"ba": 0.01, "qmd": 0.005, "stems": 0.005},
        "cohorts": [("picea_abies", 37.13314909549021, 2916.74021972182, 50.0, 260.0)],
        "expected": {"picea_abies": (40.7009932502416, 2887.785269448246, 13.395999257540625)},
    },
    {
        # The only Central-region validation (Omrade = Mellan). Exercises the spruce
        # Central 220<=SI<260 branch, whose constant had a sign error (+2.85518 ->
        # -2.85518) that only a Central spruce stand at this SI could expose. Spruce
        # here runs ~3.5% low (function fit at SI 24.5 m), still within tolerance.
        "id": "central_mellan: Central pine/spruce/birch, spruce SI24.5, start->grow",
        "region": "Central",
        "lat": 60.23,
        "alt": 300.0,
        "veg": 1,
        "soil": 1,
        "site_pine_dm": 220.0,
        "site_spruce_dm": 245.0,
        "thinned": False,
        "cohorts": [
            ("pinus_sylvestris", 14.0, 700.0, 55.0, 220.0),
            ("picea_abies", 12.0, 900.0, 50.0, 245.0),
            ("betula_pendula", 6.0, 600.0, 45.0, 200.0),
        ],
        "expected": {
            "pinus_sylvestris": (15.227177997156538, 679.7477428, 16.88849246670908),
            "picea_abies": (13.31651620983148, 881.9650332, 13.865153651970028),
            "betula_pendula": (6.71469109102788, 585.0, 12.088993530372772),
        },
    },
    {
        # Same Central stand at SI 16 m: exercises the spruce Central <180 branch,
        # where the engine matches PRODMOD to within 0.2%.
        "id": "central_mellan_160: Central, spruce SI16, start->grow",
        "region": "Central",
        "lat": 60.23,
        "alt": 300.0,
        "veg": 1,
        "soil": 1,
        "site_pine_dm": 160.0,
        "site_spruce_dm": 160.0,
        "thinned": False,
        "tol": {"ba": 0.03, "qmd": 0.02, "stems": 0.02},
        "cohorts": [
            ("pinus_sylvestris", 14.0, 700.0, 55.0, 160.0),
            ("picea_abies", 12.0, 900.0, 50.0, 160.0),
            ("betula_pendula", 6.0, 600.0, 45.0, 200.0),
        ],
        "expected": {
            "pinus_sylvestris": (15.004987465195416, 679.7477428, 16.76482370062798),
            "picea_abies": (12.932572270154525, 881.9650332, 13.663810577074836),
            "betula_pendula": (6.660312924938298, 585.0, 12.039943348492494),
        },
    },
]


def _run_case(case, growth_prodmod=False):
    """Build the engine stand for ``case`` and advance it one five-year period."""
    site = EkoStandSite(
        latitude=case["lat"],
        altitude=case["alt"],
        vegetation=case["veg"],
        soil_moisture=case["soil"],
        region=case["region"],
        H100_Pine=case["site_pine_dm"] / 10.0,
        H100_Spruce=case["site_spruce_dm"] / 10.0,
        thinned=case["thinned"],
        thinned_5y=case["thinned"],
        broadleaf_growth_prodmod=growth_prodmod,
    )
    parts = {}
    for name, ba, stems, age, _si_dm in case["cohorts"]:
        # ``_si_dm`` (the per-species SI in the case tuples) is vestigial: Ekö 1985 keys
        # every non-pine function off the site's H100 spruce and pine off H100 pine.
        parts[name] = _COHORT_CLS[name](
            ba,
            stems,
            age,
            stand=None,
            site=site,
            species=name.replace("_", " "),
        )
    stand = EngineStand(list(parts.values()), site)
    stand.grow(years=5)
    return parts


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_prodmod_growth_reproduces_reference(case):
    """The engine reproduces PRODMOD's post-growth BA, stems and QMD per species.

    Run with ``broadleaf_growth_prodmod`` on: the reference workbooks were produced
    by ProdMod2, so reproducing them requires ProdMod2's own behaviour -- the
    broadleaf BAI SI-class keyed off the stand spruce index, the diameter-limit
    clamps on the BAI inputs, and ProdMod2's (buggy) +0.609667 oak constant. The
    dissertation default is exercised in ``test_dissertation_defaults_differ_from_prodmod``.
    """
    parts = _run_case(case, growth_prodmod=True)
    tol = {**_DEFAULT_TOL, **case.get("tol", {})}
    for species, (exp_ba, exp_stems, exp_qmd) in case["expected"].items():
        part = parts[species]
        assert part.ba == pytest.approx(exp_ba, rel=tol["ba"]), f"{species} BA"
        assert part.stems == pytest.approx(exp_stems, rel=tol["stems"]), f"{species} stems"
        assert part.qmd == pytest.approx(exp_qmd, rel=tol["qmd"]), f"{species} QMD"


def test_dissertation_defaults_differ_from_prodmod():
    """The default (dissertation) engine diverges from ProdMod2 where ProdMod2 deviates.

    The broadleaf SI source (H100 spruce for every non-pine species) is the
    dissertation itself, so it is the default, not part of the flag. What
    ``broadleaf_growth_prodmod`` still gates is the genuinely ProdMod2-only behaviour:

    * the oak BAI constant -- Ekö 1985 Tabell 4i gives K = -0.609667; ProdMod2 stores
      +0.60966656 (a sign bug), so on the dissertation default mix_1 oak grows less and
      sits ~4.5% below the ProdMod2 workbook, while the flag reproduces it;
    * the BAI diameter clamps + the boundary convention -- birch_1 (3500 stems, spruce
      SI exactly on the 220 dm class boundary) is clamped to 2400 stems and drops into
      the lower SI-class only under the flag.
    """
    # Oak: the dissertation constant grows less than ProdMod2's; only the flag matches.
    mix_1 = next(c for c in CASES if c["id"].startswith("mix_1"))
    ref_oak = mix_1["expected"]["quercus_robur"][0]
    diss_oak = _run_case(mix_1, growth_prodmod=False)["quercus_robur"].ba
    pm_oak = _run_case(mix_1, growth_prodmod=True)["quercus_robur"].ba
    assert diss_oak < pm_oak  # K = -0.609667 (dissertation) grows less than ProdMod2's +
    assert pm_oak == pytest.approx(ref_oak, rel=0.01)  # ProdMod2 reproduces the workbook
    assert abs(diss_oak - ref_oak) / ref_oak > 0.03  # dissertation is ~4.5% off that ref

    # Diameter caps + boundary: birch_1 changes only under the flag, which matches.
    birch_1 = next(c for c in CASES if c["id"].startswith("birch_1"))
    ref_b1 = birch_1["expected"]["betula_pendula"][0]
    diss_b1 = _run_case(birch_1, growth_prodmod=False)["betula_pendula"].ba
    pm_b1 = _run_case(birch_1, growth_prodmod=True)["betula_pendula"].ba
    assert pm_b1 == pytest.approx(ref_b1, rel=0.01)  # ProdMod2 (caps+boundary) reproduces it
    assert pm_b1 != pytest.approx(diss_b1, rel=1e-3)  # flag is not a no-op here


def test_prodmod_mortality_fractions():
    """The ported ProdMod2 mortality reproduces the workbook's Dod langsamt/snabbt.

    Both the chronic (self-thinning) and acute five-year fractions are checked
    against the values PRODMOD reports for these single-species starts.
    """
    site_n = EkoStandSite(
        latitude=62.0,
        altitude=536.0,
        vegetation=None,
        soil_moisture=5,
        H100_Pine=12.0,
        region="North",
    )
    site_s = EkoStandSite(
        latitude=56.0,
        altitude=100.0,
        vegetation=1,
        soil_moisture=3,
        H100_Spruce=22.0,
        region="South",
    )
    # pine North (pine_1 start): chronic clamps to 0, acute = 0.05 * 0.14
    pine = _single_cohort(PineEngineCohort, 15.0, 600.0, 70.0, site_n)
    chronic, _, acute, _ = pine.get_mortality(increment=5)
    assert chronic == pytest.approx(0.0, abs=1e-9)
    assert acute == pytest.approx(0.007)
    # birch South (birch_1 start): chronic = 0.05 * 0.04, acute = 0.05 * 0.46
    birch = _single_cohort(BirchEngineCohort, 12.0, 3500.0, 15.0, site_s)
    chronic, _, acute, _ = birch.get_mortality(increment=5)
    assert chronic == pytest.approx(0.002)
    assert acute == pytest.approx(0.023)
    # spruce North is age-class sensitive: age 20 -> class 3
    spruce = _single_cohort(SpruceEngineCohort, 5.0, 500.0, 20.0, site_n)
    _, _, acute, _ = spruce.get_mortality(increment=5)
    assert acute == pytest.approx(0.05 * (-0.0002363 + 0.0250275 * 3))


# ---------------------------------------------------------------------------
# Standalone Eko volume tests: an independent transcription of the Tabell 10
# coefficients (Dg in metres, SI in dm) must agree with the engine. These guard
# the three volume bugs that were fixed: the Dg-in-cm unit error in spruce-North
# and birch-South, and the sign of the broadleaf-South constant.
# ---------------------------------------------------------------------------


def _spruce_north_volume(ba, Dg_cm, stems, age, SIdm, hk, thinned):
    """Eko 1985 Tabell 10b, omrade Nord (spruce). Dg in metres, SI in dm."""
    F4age = 1.0 - exp(-0.065 * age)
    F4ba = 1.0 - exp(-2.05 * ba)
    ln_v = (
        0.362521e-2 * ba
        + 1.35682 * log(ba)
        - 1.47258 * (Dg_cm / 100.0)
        - 0.438770 * F4ba
        + 1.46910 * F4age
        - 0.314730 * log(stems)
        + 0.228700 * log(SIdm)
        + 0.118700e-1 * thinned
        + 0.254896e-2 * hk
        + 1.970094
    )
    return exp(ln_v + 0.0388)


def _birch_south_volume(ba, Dg_cm, stems, age, SIdm, lat, hk, fert, thinned):
    """Eko 1985 Tabell 10c, omrade Syd (birch). Dg in metres, SI in dm."""
    F4age = 1.0 - exp(-0.07 * age)
    F4ba = 1.0 - exp(-2.1 * ba)
    ln_v = (
        -0.786906e-2 * ba
        + 1.35254 * log(ba)
        - 1.30862 * (Dg_cm / 100.0)
        - 0.524630 * F4ba
        + 1.01779 * F4age
        - 0.254630 * log(stems)
        + 0.204880 * log(SIdm)
        + 2.75025 * log(lat)
        + 0.774000e-1 * fert
        + 0.434800e-1 * thinned
        + 0.250449e-2 * hk
        - 9.38127
    )
    return exp(ln_v + 0.0595)


def _broadleaf_south_volume(ba, stems, age, SIdm, lat, stand_ba, hk, thinned):
    """Eko 1985 Tabell 10f, omrade Syd (other broadleaf). SI in dm; K is negative."""
    F4age = 1.0 - exp(-0.075 * age)
    F4ba = 1.0 - exp(-2.1 * ba)
    ln_v = (
        -0.148700e-1 * ba
        + 1.29359 * log(ba)
        - 0.784820 * F4ba
        + 1.18741 * F4age
        - 0.135830 * log(stems)
        + 0.219890 * log(SIdm)
        + 2.02656 * log(lat)
        + 0.242500e-1 * thinned
        + 0.859600e-1 * stand_ba
        + 0.509488e-3 * hk
        - 7.50102
    )
    return exp(ln_v + 0.0671)


def _single_cohort(cls, ba, stems, age, site):
    part = cls(ba, stems, age, stand=None, site=site)
    EngineStand([part], site)
    return part


def test_spruce_north_volume_matches_transcription():
    """Engine spruce-North volume equals the Tabell 10b transcription (Dg in metres)."""
    site = EkoStandSite(
        latitude=64.0,
        altitude=200.0,
        vegetation=None,
        soil_moisture=3,
        H100_Spruce=26.0,
        region="North",
    )
    part = _single_cohort(SpruceEngineCohort, 20.0, 700.0, 60.0, site)
    got = part.get_volume(ba=20.0, qmd=part.qmd, age=60.0, stems=700.0, hk=0.0)
    want = _spruce_north_volume(20.0, part.qmd, 700.0, 60.0, 260.0, 0.0, False)
    assert got == pytest.approx(want)
    # Physically sane form height (the Dg-in-cm bug collapsed this to ~1e-9).
    assert 5.0 < got / 20.0 < 30.0


def test_birch_south_volume_matches_transcription():
    """Engine birch-South volume equals the Tabell 10c transcription (Dg in metres)."""
    site = EkoStandSite(
        latitude=56.0,
        altitude=100.0,
        vegetation=None,
        soil_moisture=3,
        H100_Spruce=24.0,
        region="South",
    )
    part = _single_cohort(BirchEngineCohort, 18.0, 900.0, 45.0, site)
    got = part.get_volume(ba=18.0, qmd=part.qmd, age=45.0, stems=900.0, hk=0.0)
    want = _birch_south_volume(18.0, part.qmd, 900.0, 45.0, 240.0, 56.0, 0.0, False, False)
    assert got == pytest.approx(want)
    assert 3.0 < got / 18.0 < 20.0


def test_broadleaf_south_volume_matches_transcription():
    """Engine broadleaf-South volume equals the Tabell 10f transcription (K negative)."""
    site = EkoStandSite(
        latitude=56.0,
        altitude=100.0,
        vegetation=None,
        soil_moisture=3,
        H100_Spruce=24.0,
        region="South",
    )
    part = _single_cohort(BroadleafEngineCohort, 8.0, 500.0, 30.0, site)
    got = part.get_volume(ba=8.0, qmd=part.qmd, age=30.0, stems=500.0, hk=0.0)
    # SI = H100 spruce (240 dm) -- Ekö keys every non-pine function off H100 spruce.
    want = _broadleaf_south_volume(8.0, 500.0, 30.0, 240.0, 56.0, part.stand.stand_ba, 0.0, False)
    assert got == pytest.approx(want)
    # The +K sign bug inflated this to ~1e9 m3/ha; a sane form height guards it.
    assert 2.0 < got / 8.0 < 25.0


def _broadleaf_nordmellan_volume(ba, stems, age, SIdm, lat, alt, hk, thinned):
    """Eko 1985 Tabell 10f, omrade Nord+Mellan (other broadleaf). SI in dm."""
    F4age = 1.0 - exp(-0.04 * age)
    F4ba = 1.0 - exp(-2.3 * ba)
    ln_v = (
        1.26649 * log(ba)
        - 0.580030 * F4ba
        + 0.486310 * F4age
        - 0.172050 * log(stems)
        + 0.174930 * log(SIdm)
        - 1.51968 * log(lat)
        - 0.368300e-1 * log(alt)
        + 0.547400e-1 * thinned
        + 0.417126e-2 * hk
        + 7.79034
    )
    return exp(ln_v + 0.0853)


def test_broadleaf_volume_prodmod_uses_nordmellan_transcription():
    """With ``broadleaf_volume_prodmod`` the South 'Others' volume follows ProdMod2.

    ProdMod2 applies the Tabell 10f Nord+Mellan function to every region for övrigt
    löv (its recovered coefficient table is region-identical at INDEX_OTHER). The
    flag opts into that: the engine's South broadleaf volume then equals the
    Nord+Mellan transcription (physical), not the canonical Syd function.
    """
    site = EkoStandSite(
        latitude=56.0,
        altitude=100.0,
        vegetation=None,
        soil_moisture=3,
        H100_Spruce=24.0,
        region="South",
        broadleaf_volume_prodmod=True,
    )
    part = _single_cohort(BroadleafEngineCohort, 8.0, 500.0, 30.0, site)
    got = part.get_volume(ba=8.0, qmd=part.qmd, age=30.0, stems=500.0, hk=0.0)
    # SI = H100 spruce (240 dm) -- Ekö keys every non-pine function off H100 spruce.
    want = _broadleaf_nordmellan_volume(8.0, 500.0, 30.0, 240.0, 56.0, 100.0, 0.0, False)
    assert got == pytest.approx(want)
    # Physical form height, and distinct from the canonical Syd function it replaces.
    assert 2.0 < got / 8.0 < 20.0
    syd = _broadleaf_south_volume(8.0, 500.0, 30.0, 240.0, 56.0, part.stand.stand_ba, 0.0, False)
    assert got != pytest.approx(syd)


def _birch_nordmellan_volume(ba, stems, age, SIdm, lat, alt, hk, fert, thinned):
    """Eko 1985 Tabell 10c, omrade Nord+Mellan (birch). SI in dm."""
    F4age = 1.0 - exp(-0.035 * age)
    F4ba = 1.0 - exp(-2.05 * ba)
    ln_v = (
        1.26244 * log(ba)
        - 0.459580 * F4ba
        + 0.540420 * F4age
        - 0.176040 * log(stems)
        + 0.201360 * log(SIdm)
        - 1.68251 * log(lat)
        - 0.404000e-1 * log(alt)
        + 0.757200e-1 * fert
        + 0.301200e-1 * thinned
        + 0.401844e-2 * hk
        + 8.44862
    )
    return exp(ln_v + 0.0755)


def test_birch_volume_prodmod_uses_nordmellan_transcription():
    """With ``broadleaf_volume_prodmod`` the South birch volume follows ProdMod2.

    ProdMod2 pools birch to the Tabell 10c Nord+Mellan function in every region (its
    recovered coefficient table is region-identical at INDEX_BIRCH). The flag opts
    into that: the engine's South birch volume then equals the Nord+Mellan
    transcription, not the canonical Syd function.
    """
    site = EkoStandSite(
        latitude=56.0,
        altitude=100.0,
        vegetation=None,
        soil_moisture=3,
        H100_Spruce=24.0,
        region="South",
        broadleaf_volume_prodmod=True,
    )
    part = _single_cohort(BirchEngineCohort, 18.0, 900.0, 45.0, site)
    got = part.get_volume(ba=18.0, qmd=part.qmd, age=45.0, stems=900.0, hk=0.0)
    want = _birch_nordmellan_volume(18.0, 900.0, 45.0, 240.0, 56.0, 100.0, 0.0, False, False)
    assert got == pytest.approx(want)
    # Physical form height, and distinct from the canonical Syd function it replaces.
    assert 3.0 < got / 18.0 < 20.0
    syd = _birch_south_volume(18.0, part.qmd, 900.0, 45.0, 240.0, 56.0, 0.0, False, False)
    assert got != pytest.approx(syd)
