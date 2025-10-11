# -*- coding: utf-8 -*-
"""Regression checks for the Eriksson (1976) spruce stand model."""

import pytest

from pyforestry.base.helpers.primitives import Age
from pyforestry.sweden.models.eriksson1976 import (
    ErikssonSpruceStand,
    ThinningProgram,
    _next_trigger_values,
    _step_size,
    qmd,
    run_program,
)
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970


def _nearest_row_by_bhage(df, target, tol_years=2.0):
    mask = (df["age_bh_years"] >= target - tol_years) & (df["age_bh_years"] <= target + tol_years)
    sub = df[mask]
    if sub.empty:
        return None
    sub = sub.copy()
    sub["d"] = (sub["age_bh_years"] - target).abs()
    return sub.sort_values("d").iloc[0]


def _count_thinnings(df):
    return int((df["BA_removed_m2ha"] > 0).sum())


def test_qmd_identity_roundtrip():
    # BA = (pi/4)*(Dq/100)^2 * N  -> Dq = 100*sqrt(4*BA/(pi*N))
    N = 2500
    Dq_cm_true = 20.0
    ba = (3.1415926535 / 4.0) * (Dq_cm_true / 100.0) ** 2 * N
    Dq_cm_model = qmd(ba, N)
    assert Dq_cm_model == pytest.approx(Dq_cm_true, rel=1e-12, abs=1e-12)


def test_north_G20_F1_31AR_FG_two_events_and_anchor():
    # AR-triggered FG schedule (two events). First recorded ~39 BH (8-yr chunk after AR=31).
    prog = ThinningProgram(
        trigger_kind="AR",
        first_trigger_value=31.0,
        intervals=[20.0],
        grade_kind="FG",
        grades=[18.0, 16.0],
        dq=None,
    )
    df = run_program(
        description="North_G20_N3500_F1(31AR)_FG",
        H100_m=20.0,
        N0=3500,
        region_north=True,
        planted=True,
        latitude=65.0,
        start_dominant_height_m=8.0,
        start_age_bh_years=None,
        program=prog,
    )
    assert _count_thinnings(df) == 2
    first_row = df[df["BA_removed_m2ha"] > 0].iloc[0]
    assert first_row["age_bh_years"] == pytest.approx(39, abs=3)


def test_south_G28_F1_30AR_PR_anchor_rows_H_only():
    # Without the original driver cards, reproduce the *timing* & Hdom at printed anchors.
    # BA/Vol in old tables came from specific operator settings; these are not verifiable here.
    prog = ThinningProgram(
        trigger_kind="AR",
        first_trigger_value=30.0,
        intervals=[10.0, 12.0, 11.0, 13.0, 13.0, 14.0, 15.0, 15.0],
        grade_kind="PR",
        grades=[28.0, 20.0, 21.0, 18.0, 15.0, 0.0, 0.0, 0.0],
        dq=None,
    )
    df = run_program(
        description="South_G28_N3500_F1(30AR)_PR",
        H100_m=28.0,
        N0=3500,
        region_north=False,
        planted=True,
        latitude=60.0,
        start_dominant_height_m=9.0,
        start_age_bh_years=None,
        program=prog,
    )
    # Check that rows near these BH ages exist and that Hdom matches printed anchors within 0.7 m.
    expected_H = {92: 28.0, 102: 29.1, 112: 29.9}
    for bh_age, H in expected_H.items():
        row = _nearest_row_by_bhage(df, bh_age, tol_years=2.0)
        assert row is not None, f"no row found near BH age {bh_age}"
        assert row["dominant_height_m"] == pytest.approx(H, abs=0.7)


def test_h100_derivation_matches_hagglund_helper():
    expected = Hagglund_1970.height_trajectory.picea_abies.southern_sweden(
        12.5,
        Age.DBH(45.0),
        Age.TOTAL(100.0),
    )
    stand = ErikssonSpruceStand(
        stems=3200,
        dominant_height_m=12.5,
        age_bh_years=45.0,
        northern_sweden=False,
        planted=False,
        latitude_deg=60.0,
    )
    assert stand.H100_m == pytest.approx(float(expected), rel=1e-6)


def test_m2_thinning_with_custom_dq_records_removed_stats():
    stand = ErikssonSpruceStand(
        stems=3200,
        age_bh_years=40.0,
        H100_m=24.0,
        northern_sweden=True,
        planted=True,
        latitude_deg=64.0,
    )
    start_age = stand.age_bh_years
    start_stems = stand.stems
    start_qmd_ub = stand.qmd_cm_ub

    stand.grow(
        years=6,
        thinning={"mode": "M2", "value": 2.5, "dq": 0.9},
        self_thinning=False,
    )

    df = stand.as_dataframe()
    recent = df[df["age_bh_years"] > start_age].iloc[-1]
    assert bool(recent["THIN_APPLIED"]) is True
    assert recent["BA_removed_m2ha"] > 0
    assert recent["BA_removed_ub_m2ha"] > 0
    assert recent["QMD_removed_cm"] == pytest.approx(start_qmd_ub * 0.9, abs=0.2)
    assert stand.stems < start_stems


def test_trigger_helpers_cover_padding_and_step_sizes():
    program = ThinningProgram(
        trigger_kind="AR",
        first_trigger_value=30.0,
        intervals=[5.0, 10.0],
        grade_kind="PR",
        grades=[0.0, 0.0, 0.0, 0.0],
    )
    assert _next_trigger_values(program, 4) == [30.0, 35.0, 45.0, 55.0]

    assert _step_size(10.0) == 6
    assert _step_size(30.0) == 8
    assert _step_size(55.0) == 10


def test_qmd_handles_non_positive_inputs():
    assert qmd(0.0, 2500) == 0.0
    assert qmd(10.0, 0) == 0.0


def test_stand_initialisation_requires_inputs():
    with pytest.raises(ValueError, match="either dominant_height_m or age_bh_years"):
        ErikssonSpruceStand(stems=2500)


def test_stand_initialisation_validates_stems():
    with pytest.raises(ValueError, match="stems must be a positive integer"):
        ErikssonSpruceStand(stems=0, age_bh_years=30.0, H100_m=20.0)


def test_stand_initialisation_requires_h100_when_missing_age():
    with pytest.raises(ValueError, match="H100_m must be provided"):
        ErikssonSpruceStand(stems=2500, dominant_height_m=10.0)


def test_basal_area_override_and_accessors_expose_quantities():
    stand = ErikssonSpruceStand(
        stems=2800,
        age_bh_years=42.0,
        H100_m=24.0,
        northern_sweden=True,
        ba_m2_per_ha_over_bark=25.0,
    )
    assert stand.ba_m2_per_ha == pytest.approx(25.0)
    assert stand.basal_area_ob.value == pytest.approx(25.0)
    assert stand.basal_area_ub.value == pytest.approx(stand.ba_m2_per_ha_ub)
    assert stand.volume_ob.value == pytest.approx(stand.volume_m3sk_per_ha)
    assert stand.qmd_ob.value == pytest.approx(stand.qmd_cm)
    assert stand.qmd_ub.value == pytest.approx(stand.qmd_cm_ub)
    assert stand.age_bh.value == pytest.approx(stand.age_bh_years)
    assert stand.stems_per_ha.value == stand.stems


def test_grow_rejects_invalid_inputs_and_modes():
    stand = ErikssonSpruceStand(stems=3000, age_bh_years=38.0, H100_m=22.0)
    with pytest.raises(ValueError, match="years must be >= 1"):
        stand.grow(years=0)
    with pytest.raises(ValueError, match="mode"):
        stand.grow(years=5, thinning={"mode": "BAD", "value": 10.0})


def test_self_thinning_dense_stands_issue_warning():
    stand = ErikssonSpruceStand(
        stems=6000,
        dominant_height_m=16.0,
        northern_sweden=True,
        age_bh_years=None,
        H100_m=24.0,
    )
    with pytest.warns(UserWarning, match="Ekö correction"):
        stand.grow(years=6)


def test_bark_conversion_helpers_return_positive_percentages():
    stand = ErikssonSpruceStand(stems=3200, age_bh_years=40.0, H100_m=24.0)
    add_pct = stand._bark_add_pct(stand.qmd_cm_ub, stand.ba_m2_per_ha_ub, stand.age_bh_years)
    sub_pct = stand._bark_sub_pct(stand.qmd_cm, stand.ba_m2_per_ha, stand.age_bh_years)
    assert add_pct > 0
    assert sub_pct > 0


def test_run_program_dm_trimming_and_padding_applies_dq_schedule():
    program = ThinningProgram(
        trigger_kind="DM",
        first_trigger_value=150.0,
        intervals=[300.0],
        grade_kind="PR",
        grades=[25.0, 20.0],
        dq_schedule=[0.95],
    )
    df = run_program(
        description="DM_trim_test",
        H100_m=24.0,
        N0=3500,
        region_north=True,
        planted=True,
        latitude=64.0,
        start_dominant_height_m=14.5,
        start_age_bh_years=None,
        program=program,
    )
    assert _count_thinnings(df) == 1
    thin_row = df[df["THIN_APPLIED"]].iloc[0]
    assert thin_row["THIN_DQ"] == pytest.approx(0.95, rel=1e-6)


def test_run_program_dm_phase_alignment_shortens_first_step(monkeypatch):
    recorded_steps = []
    original_grow = ErikssonSpruceStand.grow

    def _recording_grow(self, years: int, thinning=None, self_thinning=True):
        recorded_steps.append((self.age_bh_years, years))
        return original_grow(self, years, thinning=thinning, self_thinning=self_thinning)

    monkeypatch.setattr(ErikssonSpruceStand, "grow", _recording_grow)

    program = ThinningProgram(
        trigger_kind="DM",
        first_trigger_value=150.0,
        intervals=[],
        grade_kind="PR",
        grades=[20.0],
        dq=None,
    )
    run_program(
        description="DM_phase_alignment",
        H100_m=24.0,
        N0=3500,
        region_north=True,
        planted=True,
        latitude=64.0,
        start_dominant_height_m=14.5,
        start_age_bh_years=None,
        program=program,
    )

    assert recorded_steps, "grow should be called at least once"
    start_age, first_years = recorded_steps[0]
    assert first_years < _step_size(start_age)


def test_run_program_loop_guard_emits_warning(monkeypatch):
    def _stalling_grow(self, years: int, thinning=None, self_thinning=True):
        # Do not advance age so the AR trigger never fires.
        return None

    monkeypatch.setattr(ErikssonSpruceStand, "grow", _stalling_grow)

    program = ThinningProgram(
        trigger_kind="AR",
        first_trigger_value=500.0,
        intervals=[100.0],
        grade_kind="PR",
        grades=[0.0],
    )
    with pytest.warns(UserWarning, match="loop guard"):
        run_program(
            description="LoopGuard",
            H100_m=24.0,
            N0=3000,
            region_north=True,
            planted=True,
            latitude=64.0,
            start_dominant_height_m=12.0,
            start_age_bh_years=None,
            program=program,
        )


def test_run_program_m2_trigger_branch_executes():
    program = ThinningProgram(
        trigger_kind="M2",
        first_trigger_value=20.0,
        intervals=[],
        grade_kind="M2",
        grades=[2.0],
        dq=0.85,
    )
    df = run_program(
        description="M2_trigger",
        H100_m=24.0,
        N0=3200,
        region_north=True,
        planted=True,
        latitude=64.0,
        start_dominant_height_m=10.0,
        start_age_bh_years=None,
        program=program,
    )
    assert _count_thinnings(df) >= 1
