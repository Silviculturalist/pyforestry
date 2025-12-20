import pytest

from pyforestry.sweden.models.eko_1985_refactor import (
    BeechEngineCohort,
    BirchEngineCohort,
    BroadleafEngineCohort,
    EkoStandSite,
    EngineStand,
    OakEngineCohort,
    PineEngineCohort,
    SpruceEngineCohort,
)
from pyforestry.sweden.site.enums import Sweden


def _latitude_for_region(region: str) -> float:
    mapping = {"North": 64.0, "Central": 61.0, "South": 56.0}
    return mapping[region]


def _make_site(region: str, h100: float, *, thinned: bool) -> EkoStandSite:
    return EkoStandSite(
        latitude=_latitude_for_region(region),
        altitude=120.0,
        vegetation=Sweden.FieldLayer.BILBERRY,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC_MOIST,
        H100_Spruce=h100,
        H100_Pine=h100,
        region=region,
        fertilised=True,
        thinned_5y=True,
        thinned=thinned,
        TAX77=True,
    )


def _make_part(cohort_cls, site: EkoStandSite):
    part = cohort_cls(20.0, 1200.0, 50.0, stand=None, site=site)
    stand = EngineStand([part], site)
    return part, stand


def _add_cases(cases, cohort_cls, region, h100_values, thinned_values=(False, True)):
    for h100 in h100_values:
        for thinned in thinned_values:
            cases.append((cohort_cls, region, h100, thinned))


ENGINE_CASES: list[tuple] = []
_add_cases(ENGINE_CASES, SpruceEngineCohort, "North", [15.0, 18.0, 22.0])
_add_cases(ENGINE_CASES, SpruceEngineCohort, "Central", [17.0, 20.0, 24.0, 28.0])
_add_cases(ENGINE_CASES, SpruceEngineCohort, "South", [20.0, 24.0, 28.0, 32.0])
_add_cases(ENGINE_CASES, PineEngineCohort, "North", [15.0, 18.0, 22.0])
_add_cases(ENGINE_CASES, PineEngineCohort, "Central", [17.0, 20.0, 24.0])
_add_cases(ENGINE_CASES, PineEngineCohort, "South", [15.0, 18.0, 22.0, 26.0])
_add_cases(ENGINE_CASES, BirchEngineCohort, "North", [13.0, 16.0, 20.0, 24.0])
_add_cases(ENGINE_CASES, BirchEngineCohort, "South", [20.0, 24.0, 28.0, 32.0])
_add_cases(ENGINE_CASES, BroadleafEngineCohort, "North", [15.0, 18.0, 22.0, 26.0])
_add_cases(ENGINE_CASES, BroadleafEngineCohort, "South", [22.0, 26.0, 30.0, 34.0])
_add_cases(ENGINE_CASES, BeechEngineCohort, "South", [30.0, 32.0])
_add_cases(ENGINE_CASES, OakEngineCohort, "South", [26.0, 30.0, 34.0], thinned_values=(False,))


@pytest.mark.parametrize(
    "cohort_cls, region, h100, thinned",
    ENGINE_CASES,
)
def test_engine_formulas_cover_branches(cohort_cls, region, h100, thinned):
    site = _make_site(region, h100, thinned=thinned)
    part, _stand = _make_part(cohort_cls, site)

    crowding, _qmd_dead_c, other, _qmd_dead_o = part.getMortality(increment=5)
    volume = part.getVolume()
    part.getBAI5(
        ba_quotient_chronic_mortality=crowding,
        ba_quotient_acute_mortality=other,
    )

    assert 0.0 <= crowding <= 1.0
    assert 0.0 <= other <= 1.0
    assert volume >= 0.0
    assert part.BAI5 >= 0.0


@pytest.mark.parametrize(
    "cohort_cls",
    [
        SpruceEngineCohort,
        PineEngineCohort,
        BirchEngineCohort,
        BroadleafEngineCohort,
        BeechEngineCohort,
        OakEngineCohort,
    ],
)
@pytest.mark.parametrize("method_name", ["getMortality", "getVolume", "getBAI5"])
def test_engine_cohort_requires_stand(cohort_cls, method_name):
    site = _make_site("South", 22.0, thinned=False)
    part = cohort_cls(20.0, 1200.0, 50.0, stand=None, site=site)

    with pytest.raises(ValueError, match="stand connected"):
        getattr(part, method_name)()
