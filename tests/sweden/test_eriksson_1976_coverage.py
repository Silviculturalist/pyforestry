import types

import pytest

from pyforestry.base.helpers import (
    Age,
    CircularPlot,
    SiteIndexValue,
    Stand,
    StandBasalArea,
    Stems,
    Tree,
    TreeSpecies,
)
from pyforestry.sweden.systems import eriksson_1976 as e
from pyforestry.sweden.systems.eriksson_1976 import (
    Eriksson1976ManagementSchedule,
    Eriksson1976Model,
    Eriksson1976Stand,
    StandInit,
    ThinningProgram,
    ThinningRequest,
)


def _si(value: float = 22.0) -> SiteIndexValue:
    return SiteIndexValue(
        value=value,
        reference_age=Age.TOTAL(100.0),
        species={TreeSpecies.Sweden.picea_abies},
        fn=_si,
    )


def _init(**kwargs) -> StandInit:
    params = dict(
        region="north",
        h100_m=22.0,
        start_bh_age=30.0,
        final_bh_age=50.0,
        stems=1800.0,
        basal_area=20.0,
    )
    params.update(kwargs)
    return StandInit(**params)


class _DummyContext:
    def __init__(self, ba_total: float = 30.0):
        self.state: dict[str, float] = {}
        self.metrics = {"BasalArea": {"TOTAL": ba_total}}
        self.calls: list[tuple[str, dict[str, float | str | None]]] = []

    def do(self, name: str, **kwargs):
        self.calls.append((name, kwargs))


def test_eriksson_core_helpers_and_schedules(monkeypatch):
    assert e._normalize_region("norr") == "north"
    assert e._normalize_region("s") == "south"
    with pytest.raises(ValueError):
        e._normalize_region("east")

    assert e._site_class_index_from_h100_dm(170.0) == 1
    assert e._site_class_index_from_h100_dm(345.0) == 6
    assert e._qmd_cm_from_basal_area_and_stems(0.0, 1000.0) == 0.0
    assert e._qmd_cm_from_basal_area_and_stems(10.0, 1000.0) > 0.0

    assert e.convert_basal_area_over_to_under_bark(0.0, 30.0, 15.0, 2) == 0.0
    assert e.convert_basal_area_over_to_under_bark_with_reference(0.0, 30.0, 15.0, 10.0, 2) == 0.0
    assert e.convert_basal_area_under_to_over_bark(0.0, 30.0, 15.0, 2) == 0.0
    assert e.convert_thinning_basal_area_under_to_over_bark(0.0, 30.0, 15.0, 10.0, 2) == 0.0
    assert e.compute_stand_volume_m3sk(0.0, 200.0, 15.0, 2) == 0.0
    assert e.compute_dry_weight_factor(0.0, 60.0) == 0.0
    assert e.compute_stand_volume_m3sk(20.0, 200.0, 15.0, 2) > 0.0

    program = ThinningProgram(
        interval_type="age",
        first_trigger=35.0,
        intervals=[5.0],
        outtakes=[20.0],
        use_diameter_factors=True,
        diameter_factors=[0.9],
    )
    assert e._thinning_qmd_under_bark_cm(10.0, 200.0, program, 0, diameter_factor=0.8) == 8.0
    assert e._thinning_qmd_under_bark_cm(10.0, 200.0, program, 0) == 9.0
    assert e._thinning_qmd_under_bark_cm(10.0, 200.0, program, 5) == 9.0
    assert e._thinning_qmd_under_bark_cm(10.0, 300.0, None, 0) == 10.0
    assert e._thinning_qmd_under_bark_cm(10.0, 200.0, None, 0) > 0.0

    init = _init(growth_scaling=1)
    assert e._apply_growth_scaling(1.0, init) == 1.0
    assert e._apply_growth_scaling(1.0, _init(growth_scaling=2, vg=120.0)) == 1.2
    assert e._apply_growth_scaling(1.1, _init(growth_scaling=3, culture_class=1)) == 1.0
    assert e._apply_growth_scaling(0.85, _init(growth_scaling=3, culture_class=2)) == 1.0
    assert e._apply_growth_scaling(0.7, _init(growth_scaling=3, culture_class=3)) == 1.0

    p, *_ = e._schedule_age(25.0, 120.0, 30.0, False, 0, 0, 0, [10.0])
    assert p == 5.0
    p, *_ = e._schedule_age(25.0, 120.0, 39.0, False, 0, 0, 0, [10.0])
    assert p == 6.0
    p, *_ = e._schedule_age(25.0, 120.0, 40.0, False, 0, 0, 0, [10.0])
    assert p == 6.0
    p, *_ = e._schedule_age(35.0, 120.0, 47.0, False, 0, 0, 0, [10.0])
    assert p == 6.0
    p, *_ = e._schedule_age(55.0, 120.0, 66.0, False, 0, 0, 0, [10.0])
    assert p == 5.0

    p, _, val, iidx, oidx, gidx = e._schedule_age(25.0, 120.0, 30.0, True, 0, 0, 0, [10.0])
    assert p == 5.0
    assert val is False
    assert (iidx, oidx, gidx) == (0, 0, 0)

    p, _, val, iidx, oidx, gidx = e._schedule_age(25.0, 120.0, 25.0, True, 0, 0, 0, [0.0])
    assert p == 6.0
    assert val is False
    assert (iidx, oidx, gidx) == (0, 0, 0)

    p, *_ = e._schedule_basal_area(
        t=55.0,
        sag=64.0,
        gmx=40.0,
        current_ba=30.0,
        val=False,
        interval_idx=0,
        outtake_idx=0,
        gf_idx=0,
        intervals=[5.0],
        outtakes=[10.0],
        gz1=1.0,
        gp=1.0,
        gs2=1.0,
        h_dm=200.0,
        gu2=10.0,
        sn1=1500.0,
        mc=2,
        vs=1.0,
    )
    assert p >= 1.0

    p, *_ = e._schedule_basal_area(
        t=45.0,
        sag=60.0,
        gmx=float("inf"),
        current_ba=30.0,
        val=False,
        interval_idx=0,
        outtake_idx=0,
        gf_idx=0,
        intervals=[5.0],
        outtakes=[10.0],
        gz1=1.0,
        gp=1.0,
        gs2=1.0,
        h_dm=200.0,
        gu2=10.0,
        sn1=1500.0,
        mc=2,
        vs=1.0,
    )
    assert p == 7

    def _fake_gyield(*args, **kwargs):  # noqa: ARG001
        p = float(args[5])
        return 0.0, 5.0 + p, 20.0 + p, 10.0, 10.0 * p

    monkeypatch.setattr(e, "project_growth_step", _fake_gyield)

    p, _, val, iidx, oidx, gidx = e._schedule_basal_area(
        t=20.0,
        sag=120.0,
        gmx=20.0,
        current_ba=15.0,
        val=False,
        interval_idx=0,
        outtake_idx=0,
        gf_idx=0,
        intervals=[5.0, 0.0],
        outtakes=[10.0, 10.0],
        gz1=1.0,
        gp=1.0,
        gs2=1.0,
        h_dm=200.0,
        gu2=10.0,
        sn1=1500.0,
        mc=2,
        vs=1.0,
    )
    assert p > 0.0
    assert val is True
    assert (iidx, oidx, gidx) == (1, 1, 1)

    p, _, val, *_ = e._schedule_basal_area(
        t=20.0,
        sag=120.0,
        gmx=200.0,
        current_ba=15.0,
        val=False,
        interval_idx=0,
        outtake_idx=0,
        gf_idx=0,
        intervals=[5.0],
        outtakes=[10.0, 10.0],
        gz1=1.0,
        gp=1.0,
        gs2=1.0,
        h_dm=200.0,
        gu2=10.0,
        sn1=1500.0,
        mc=2,
        vs=1.0,
    )
    assert p > 0.0
    assert val is False


def test_estimate_initial_stand_all_resolution_paths(monkeypatch):
    calls = {"init": 0, "north_stems": 0, "south_stems": 0, "north_ba": 0, "south_ba": 0}

    monkeypatch.setattr(e._HagglundContext, "site_index_value", lambda self: _si())
    monkeypatch.setattr(e._HagglundContext, "time_to_breast_height", lambda self: 12.0)
    monkeypatch.setattr(e._HagglundContext, "height_dm", lambda self, bh_age: 180.0)

    def _init_stand(**kwargs):  # noqa: ARG001
        calls["init"] += 1
        return Stems(1900.0, species=TreeSpecies.Sweden.picea_abies), StandBasalArea(
            21.0, species=TreeSpecies.Sweden.picea_abies
        )

    def _north_stems(**kwargs):  # noqa: ARG001
        calls["north_stems"] += 1
        return Stems(1500.0, species=TreeSpecies.Sweden.picea_abies)

    def _south_stems(**kwargs):  # noqa: ARG001
        calls["south_stems"] += 1
        return Stems(1400.0, species=TreeSpecies.Sweden.picea_abies)

    def _north_ba(**kwargs):  # noqa: ARG001
        calls["north_ba"] += 1
        return StandBasalArea(19.0, species=TreeSpecies.Sweden.picea_abies)

    def _south_ba(**kwargs):  # noqa: ARG001
        calls["south_ba"] += 1
        return StandBasalArea(18.0, species=TreeSpecies.Sweden.picea_abies)

    monkeypatch.setattr(
        e.ElfvingHagglundInitialStand,
        "estimate_initial_spruce_stand",
        staticmethod(_init_stand),
    )
    monkeypatch.setattr(
        e.ElfvingHagglundInitialStand,
        "estimate_stems_young_spruce_north",
        staticmethod(_north_stems),
    )
    monkeypatch.setattr(
        e.ElfvingHagglundInitialStand,
        "estimate_stems_young_spruce_south",
        staticmethod(_south_stems),
    )
    monkeypatch.setattr(
        e.ElfvingHagglundInitialStand,
        "estimate_basal_area_young_spruce_north",
        staticmethod(_north_ba),
    )
    monkeypatch.setattr(
        e.ElfvingHagglundInitialStand,
        "estimate_basal_area_young_spruce_south",
        staticmethod(_south_ba),
    )

    h_dom_m, stems, basal_area, site_index, t13 = e.estimate_initial_stand(
        _init(stems=None, basal_area=None, region="north")
    )
    assert h_dom_m == 18.0
    assert stems == 1900.0
    assert basal_area == 21.0
    assert float(site_index) == 22.0
    assert t13 == 12.0

    _, stems, basal_area, _, _ = e.estimate_initial_stand(
        _init(stems=None, basal_area=17.0, region="north")
    )
    assert stems == 1500.0
    assert basal_area == 17.0

    _, stems, basal_area, _, _ = e.estimate_initial_stand(
        _init(stems=None, basal_area=16.0, region="south")
    )
    assert stems == 1400.0
    assert basal_area == 16.0

    _, stems, basal_area, _, _ = e.estimate_initial_stand(
        _init(stems=1700.0, basal_area=None, region="north")
    )
    assert stems == 1700.0
    assert basal_area == 19.0

    _, stems, basal_area, _, _ = e.estimate_initial_stand(
        _init(stems=1650.0, basal_area=None, region="south")
    )
    assert stems == 1650.0
    assert basal_area == 18.0

    assert calls == {
        "init": 1,
        "north_stems": 1,
        "south_stems": 1,
        "north_ba": 1,
        "south_ba": 1,
    }

    monkeypatch.setattr(
        e.ElfvingHagglundInitialStand,
        "estimate_initial_spruce_stand",
        staticmethod(lambda **kwargs: (None, None)),
    )
    with pytest.raises(TypeError):
        e.estimate_initial_stand(_init(stems=None, basal_area=None))


def test_eriksson_stand_paths_and_edge_conditions():
    program = ThinningProgram(
        interval_type="age",
        first_trigger=35.0,
        intervals=[10.0, 0.0],
        outtakes=[20.0, 0.0],
        outtake_type="percent",
        use_diameter_factors=True,
        diameter_factors=[0.8],
    )
    stand = Eriksson1976Stand(_init(), program=program, track_history=True)

    assert stand.done is False
    assert stand.bh_age > 0.0
    assert stand.total_age > stand.bh_age
    assert stand.stems_per_ha > 0.0
    assert stand.basal_area_m2_per_ha > 0.0
    assert stand.dominant_height_m > 0.0
    assert stand.qmd_cm > 0.0
    assert stand.volume_m3sk > 0.0
    assert stand.last_row is None
    assert stand.track_history is True
    assert stand.self_thinning_summary["stems_per_ha"] >= 0.0

    row = stand.grow(years=0.0)
    assert row is not None
    assert stand.done is True
    assert stand.grow(years=5.0) is None

    standalone = Eriksson1976Stand(_init(), program=None)
    with pytest.raises(ValueError):
        standalone.step()
    with pytest.raises(ValueError):
        standalone._coerce_thinning({"outtake": 10.0, "outtake_type": "bad"})

    with pytest.raises(ValueError):
        Eriksson1976Stand(_init(final_bh_age=None), program=program).step()

    thinning = standalone._coerce_thinning(
        {"outtake": 10.0, "outtake_type": "absolute", "diameter_factor": 0.75}
    )
    assert isinstance(thinning, ThinningRequest)
    assert thinning.outtake_type == "absolute"
    assert thinning.diameter_factor == 0.75

    stand._state.val = True
    stand._state.outtake_idx = 0
    stand._state.gf_idx = 10
    req = stand._resolve_program_thinning()
    assert req is not None
    assert req.diameter_factor == 0.8

    stand._state.val = False
    assert stand._resolve_program_thinning() is None
    stand._state.val = True
    stand._state.outtake_idx = 99
    assert stand._resolve_program_thinning() is None

    with pytest.raises(ValueError):
        Eriksson1976Stand(_init(stems=1200.0, basal_area=10.0), program=None).grow(
            years=5.0,
            thinning=ThinningRequest(outtake=100.0, diameter_factor=0.001),
        )

    stand_low_stems = Eriksson1976Stand(_init(stems=80.0, basal_area=2.0), program=None)
    assert stand_low_stems.grow(years=5.0, thinning=ThinningRequest(outtake=100.0)) is None
    assert stand_low_stems.done is True

    stand_abs = Eriksson1976Stand(_init(stems=1200.0, basal_area=15.0), program=None)
    row_abs = stand_abs.grow(
        years=1.0,
        thinning=ThinningRequest(outtake=2.0, outtake_type="absolute"),
    )
    assert row_abs is not None

    with pytest.raises(ValueError):
        stand_abs._advance(years=None, thinning=None, use_program=False)


def test_eriksson_management_schedule_and_model_adapter():
    age_program = ThinningProgram(
        interval_type="age",
        first_trigger=30.0,
        intervals=[10.0, 0.0],
        outtakes=[20.0, 10.0, 0.0],
        outtake_type="residual",
        use_diameter_factors=True,
        diameter_factors=[0.9],
    )
    schedule = Eriksson1976ManagementSchedule(program=age_program)
    ctx = _DummyContext(ba_total=40.0)
    schedule.initialize(ctx)
    assert ctx.state[schedule._key("outtake_idx")] == 0
    assert ctx.state[schedule._key("interval_idx")] == 0
    assert ctx.state[schedule._key("gf_idx")] == 0

    assert schedule._diameter_factor(0) == 0.9
    assert schedule._diameter_factor(5) == 0.9
    events = schedule._age_events()
    assert len(events) == 2

    # A zero outtake proposes nothing; a real one proposes one thinning action.
    assert schedule._thinning_actions(0.0, None, "noop") == ()
    proposed = schedule._thinning_actions(10.0, 0.9, "thin")
    assert len(proposed) == 1
    assert proposed[0].params["outtake"] == 10.0
    assert proposed[0].params["diameter_factor"] == 0.9

    policy = schedule.policy()
    ctx.state["t"] = 29.0
    assert policy(ctx) == ()
    ctx.state["t"] = 30.0
    fired = policy(ctx)
    assert len(fired) == 1
    for action in fired:
        action(ctx)
    assert len(ctx.calls) == 1

    ba_program = ThinningProgram(
        interval_type="basal_area",
        first_trigger=35.0,
        intervals=[5.0, 0.0],
        outtakes=[10.0, 5.0],
        outtake_type="percent",
        use_diameter_factors=True,
        diameter_factors=[0.85],
    )
    ba_schedule = Eriksson1976ManagementSchedule(program=ba_program)
    ba_ctx = _DummyContext(ba_total=40.0)
    ba_schedule.initialize(ba_ctx)
    ba_policy = ba_schedule.policy()
    assert len(ba_policy(ba_ctx)) == 1
    assert ba_ctx.state[ba_schedule._key("outtake_idx")] == 1
    assert ba_ctx.state[ba_schedule._key("interval_idx")] == 1
    assert ba_ctx.state[ba_schedule._key("gf_idx")] == 1
    assert ba_ctx.state[ba_schedule._key("ba_trigger")] > 0.0

    # With the outtakes exhausted, the next time the threshold is reached the
    # schedule disarms itself instead of thinning again. The basal area has to
    # clear the new threshold for the policy to look at all -- the old
    # ``TriggerSpec`` test called the action directly and skipped its predicate.
    ba_ctx.state[ba_schedule._key("outtake_idx")] = 10
    ba_ctx.metrics["BasalArea"]["TOTAL"] = 1000.0
    assert ba_policy(ba_ctx) == ()
    assert ba_ctx.state[ba_schedule._key("ba_trigger")] == float("inf")

    assert ba_schedule._residual_ba(30.0, 10.0, "percent") == 27.0
    assert ba_schedule._residual_ba(30.0, 10.0, "residual") == 10.0
    assert ba_schedule._residual_ba(30.0, 10.0, "absolute") == 20.0

    stand = Stand(
        plots=[
            CircularPlot(
                id="p1",
                area_m2=400.0,
                trees=[
                    Tree(
                        species=TreeSpecies.Sweden.picea_abies,
                        diameter_cm=20.0,
                        weight_n=120.0,
                    )
                ],
            )
        ]
    )
    init = _init(stems=None, basal_area=None, latitude=None, altitude_m=0.0)
    model = Eriksson1976Model(init=init, program=age_program, track_history=True)
    assert model.requirements().inventory == "aggregate"

    stand.attrs["eriksson_1976_program"] = age_program
    stand.site = types.SimpleNamespace(latitude=61.5, altitude=210.0)
    ctx_model = model.build_context(stand)
    assert "eriksson_1976_stand" in ctx_model.attrs
    assert "eriksson_1976_program" in ctx_model.attrs
    assert ctx_model.state["years_since_thin"] == 0.0

    actions = model.available_actions()
    assert "schedule_thinning" in actions
    model._act_schedule_thinning(ctx_model, outtake=15.0, outtake_type="percent")
    model.update_step(ctx_model, dt=5.0)
    assert ctx_model.state["years_since_thin"] == 0.0
    model.update_step(ctx_model, dt=2.0)
    assert ctx_model.state["years_since_thin"] == 2.0

    with pytest.raises(ValueError):
        model._act_schedule_thinning(ctx_model, outtake=10.0, outtake_type="unknown")

    with pytest.raises(ValueError):
        Eriksson1976Model()._resolve_init(stand, init=None)
    with pytest.raises(ValueError):
        Eriksson1976Model._stand_from_ctx(types.SimpleNamespace(attrs={}))


def test_eriksson_northern_error_toggle_and_height_intervals():
    # --- A: local Hagglund 8.4 (GRANN) error toggle ---
    # The corrected and FORTRAN-listing coefficient sets diverge.
    assert e._solve_northern_spruce_8_4(24.0, False, False) != e._solve_northern_spruce_8_4(
        24.0, False, True
    )
    # ctx routing: north honours the flag (the txt coefficients read higher), south ignores it.
    ctx_n_c = e._HagglundContext(24.0, "north", None, False, False)
    ctx_n_e = e._HagglundContext(24.0, "north", None, False, True)
    assert ctx_n_e.height_dm(40.0) > ctx_n_c.height_dm(40.0)
    assert ctx_n_c.time_to_breast_height() != ctx_n_e.time_to_breast_height()
    ctx_s_c = e._HagglundContext(32.0, "south", None, False, False)
    ctx_s_e = e._HagglundContext(32.0, "south", None, False, True)
    assert ctx_s_c.height_dm(40.0) == ctx_s_e.height_dm(40.0)
    assert ctx_s_c.time_to_breast_height() == ctx_s_e.time_to_breast_height()

    # --- B: height -> breast-height-age inversion round-trips ---
    round_trip_age = ctx_s_c.bh_age_for_height_dm(200.0)
    assert abs(ctx_s_c.height_dm(round_trip_age) - 200.0) < 0.5

    # --- B: dominant_height program converts to the expected age schedule ---
    prog_h = ThinningProgram(
        interval_type="dominant_height",
        first_trigger=14.0,
        intervals=[3.0, 3.0],
        outtake_type="percent",
        outtakes=[25.0, 20.0, 20.0],
    )
    age_prog = e._height_program_to_age(prog_h, ctx_s_c, 60.0)
    assert age_prog.interval_type == "age"
    assert age_prog.first_trigger == 24.0
    assert list(age_prog.intervals) == [7.0, 7.0]
    # A height increment below 0.1 m terminates the schedule (FORTRAN GIV(K) < 1 dm).
    prog_stop = ThinningProgram(
        interval_type="dominant_height",
        first_trigger=14.0,
        intervals=[3.0, 0.0, 3.0],
        outtake_type="percent",
        outtakes=[25.0, 20.0],
    )
    assert list(e._height_program_to_age(prog_stop, ctx_s_c, 60.0).intervals) == [7.0]
    # A target at/beyond the final age is dropped.
    assert list(e._height_program_to_age(prog_h, ctx_s_c, 28.0).intervals) == []

    # --- B: a dominant_height run equals its equivalent age run ---
    init = StandInit(
        region="south",
        h100_m=32.0,
        start_bh_age=15.0,
        final_bh_age=60.0,
        stems=2200.0,
        basal_area=18.0,
    )
    rows_h = e.simulate(init, prog_h).rows
    age_equiv = ThinningProgram(
        interval_type="age",
        first_trigger=24.0,
        intervals=[7.0, 7.0],
        outtake_type="percent",
        outtakes=[25.0, 20.0, 20.0],
    )
    rows_a = e.simulate(init, age_equiv).rows
    assert len(rows_h) == len(rows_a)
    assert rows_h[-1]["fore_gallring"]["V_m3sk"] == rows_a[-1]["fore_gallring"]["V_m3sk"]

    # A dominant_height program with no final age still constructs (final_age -> inf).
    stand_nf = Eriksson1976Stand(
        StandInit(region="south", h100_m=32.0, start_bh_age=15.0, stems=2200.0, basal_area=18.0),
        program=prog_h,
    )
    assert stand_nf.program.interval_type == "age"

    # The simulation-framework adapter rejects dominant_height (no site context to invert).
    with pytest.raises(NotImplementedError):
        Eriksson1976ManagementSchedule(program=prog_h).policy()


def test_eriksson_initial_stand_auto_generation():
    # No stems/basal_area -> Elfving & Hagglund (1975) generation, north and south.
    for region, h100 in (("north", 22.0), ("south", 30.0)):
        stand = Eriksson1976Stand(
            StandInit(
                region=region,
                h100_m=h100,
                start_bh_age=17.0,
                final_bh_age=50.0,
                altitude_m=200.0,
                stems=None,
                basal_area=None,
            ),
            track_history=True,
        )
        assert stand.stems_per_ha > 0.0
        assert stand.basal_area_m2_per_ha > 0.0
    # Stems supplied, basal area generated.
    stand_ba = Eriksson1976Stand(
        StandInit(
            region="north",
            h100_m=24.0,
            start_bh_age=20.0,
            final_bh_age=45.0,
            altitude_m=150.0,
            stems=2000.0,
            basal_area=None,
        )
    )
    assert stand_ba.basal_area_m2_per_ha > 0.0
