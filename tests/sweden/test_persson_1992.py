"""Tests for the Persson (1992) Scots Pine production model."""

from __future__ import annotations

import pytest

from pyforestry.sweden.systems.persson_1992 import (
    Persson1992Model,
    Persson1992Stand,
    PerssonSimulationResult,
    PerssonStandInit,
    PerssonThinningProgram,
    PerssonThinningRequest,
    _qmd_cm,
    average_basal_area,
    ba_increment_annual_ub,
    ba_ob_to_ub,
    ba_ub_to_ob,
    bark_area,
    mortality_diameter_ratio,
    natural_mortality_ba_annual,
    persson_estimate_initial_stand,
    persson_simulate,
    volume_m3sk,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _rel_error(sim: float, ref: float) -> float:
    return abs(sim - ref) / max(abs(ref), 1e-9)


# ═══════════════════════════════════════════════════════════════════════════════
# Regression function tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestRegressionFunctions:
    """Verify individual regression equations from Persson (1992)."""

    # Reference conditions: T28:1N first period
    BA_OB = 28.5  # m²/ha
    HDOM = 10.0  # m
    STEMS = 4887.0  # stems/ha
    LAT = 64.0  # degrees
    H100 = 28.0  # m

    def test_volume_positive(self):
        vol = volume_m3sk(self.BA_OB, self.HDOM, self.STEMS, self.LAT)
        assert vol > 100.0
        assert vol < 200.0

    def test_volume_at_reference_point(self):
        """Volume at T28:1N period 1 should be ~134 m³sk (PDF Table)."""
        vol = volume_m3sk(self.BA_OB, self.HDOM, self.STEMS, self.LAT)
        assert abs(vol - 134.0) < 2.0

    def test_volume_zero_ba(self):
        assert volume_m3sk(0.0, self.HDOM, self.STEMS, self.LAT) == 0.0

    def test_volume_increases_with_ba(self):
        v1 = volume_m3sk(20.0, self.HDOM, self.STEMS, self.LAT)
        v2 = volume_m3sk(30.0, self.HDOM, self.STEMS, self.LAT)
        assert v2 > v1

    def test_bark_area_positive(self):
        ba = bark_area(self.BA_OB, self.H100, self.STEMS, self.LAT)
        assert 3.0 < ba < 8.0

    def test_bark_fraction_reasonable(self):
        """Bark should be roughly 15-25% of BA over bark."""
        ba = bark_area(self.BA_OB, self.H100, self.STEMS, self.LAT)
        fraction = ba / self.BA_OB
        assert 0.10 < fraction < 0.30

    def test_average_basal_area_positive(self):
        avg = average_basal_area(self.H100, self.HDOM)
        assert 15.0 < avg < 35.0

    def test_ba_increment_positive(self):
        ba_ub = ba_ob_to_ub(self.BA_OB, self.H100, self.STEMS, self.LAT)
        ig = ba_increment_annual_ub(ba_ub, 16.0, self.H100, self.LAT)
        assert ig > 0.5
        assert ig < 3.0

    def test_ba_increment_decreases_with_age(self):
        ba_ub = 20.0
        ig_young = ba_increment_annual_ub(ba_ub, 20.0, self.H100, self.LAT)
        ig_old = ba_increment_annual_ub(ba_ub, 80.0, self.H100, self.LAT)
        assert ig_young > ig_old

    def test_natural_mortality_non_negative(self):
        mort = natural_mortality_ba_annual(self.BA_OB, self.HDOM, self.H100, self.STEMS, self.LAT)
        assert mort >= 0.0

    def test_mortality_dense_vs_sparse(self):
        """Dense stands should have higher mortality."""
        mort_dense = natural_mortality_ba_annual(35.0, 15.0, self.H100, 3000.0, self.LAT)
        mort_sparse = natural_mortality_ba_annual(15.0, 15.0, self.H100, 1000.0, self.LAT)
        assert mort_dense > mort_sparse

    def test_mortality_diameter_ratio_below_one(self):
        """Dead trees are typically smaller than the mean."""
        ratio = mortality_diameter_ratio(self.HDOM, self.STEMS, False)
        assert 0.2 < ratio < 1.0

    def test_mortality_diameter_ratio_higher_when_thinned(self):
        ratio_unthinned = mortality_diameter_ratio(self.HDOM, self.STEMS, False)
        ratio_thinned = mortality_diameter_ratio(self.HDOM, self.STEMS, True)
        assert ratio_thinned > ratio_unthinned

    def test_qmd(self):
        """QMD from known BA and stems."""
        qmd = _qmd_cm(self.BA_OB, self.STEMS)
        assert abs(qmd - 8.62) < 0.05


# ═══════════════════════════════════════════════════════════════════════════════
# Bark conversion tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestBarkConversion:
    """Verify over-bark / under-bark conversions."""

    def test_ob_to_ub_reduces(self):
        ub = ba_ob_to_ub(28.5, 28.0, 4887.0, 64.0)
        assert 0.0 < ub < 28.5

    def test_round_trip(self):
        """Converting ob→ub→ob should return the original value."""
        ba_ob = 28.5
        ba_ub = ba_ob_to_ub(ba_ob, 28.0, 4887.0, 64.0)
        ba_ob_back = ba_ub_to_ob(ba_ub, 28.0, 4887.0, 64.0)
        assert abs(ba_ob_back - ba_ob) < 0.01

    def test_zero_ba(self):
        assert ba_ob_to_ub(0.0, 28.0, 4887.0, 64.0) == 0.0
        assert ba_ub_to_ob(0.0, 28.0, 4887.0, 64.0) == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# Initial stand estimation
# ═══════════════════════════════════════════════════════════════════════════════


class TestInitialStand:
    """Verify initial stand estimation with Elfving-Hägglund (1975)."""

    def test_given_stems_and_ba(self):
        """When stems and BA are provided, they are returned unchanged."""
        init = PerssonStandInit(
            h100_m=28.0,
            start_bh_age=16,
            stems=4887.0,
            basal_area=28.5,
            latitude=64.0,
        )
        hdom, stems, ba, si, t13 = persson_estimate_initial_stand(init)
        assert stems == 4887.0
        assert ba == 28.5
        assert abs(hdom - 10.0) < 0.1
        assert t13 > 5.0
        assert t13 < 15.0

    def test_auto_estimation_north(self):
        """When stems/BA are None, Elfving-Hägglund estimates them."""
        init = PerssonStandInit(
            h100_m=28.0,
            start_bh_age=16,
            latitude=64.0,
            altitude_m=200.0,
        )
        hdom, stems, ba, si, t13 = persson_estimate_initial_stand(init)
        assert stems > 500
        assert stems < 10000
        assert ba > 5.0
        assert ba < 50.0

    def test_auto_estimation_south(self):
        init = PerssonStandInit(
            h100_m=28.0,
            start_bh_age=16,
            latitude=58.0,
            altitude_m=100.0,
        )
        hdom, stems, ba, si, t13 = persson_estimate_initial_stand(init)
        assert stems > 500
        assert ba > 5.0


# ═══════════════════════════════════════════════════════════════════════════════
# Stand simulator – basic grow()
# ═══════════════════════════════════════════════════════════════════════════════


class TestPersson1992StandGrow:
    """Test manual growth steps with .grow()."""

    def _make_stand(self, **kwargs) -> Persson1992Stand:
        defaults = dict(
            h100_m=28.0,
            start_bh_age=16,
            stems=4887.0,
            basal_area=28.5,
            latitude=64.0,
            regeneration="culture",
        )
        defaults.update(kwargs)
        return Persson1992Stand(PerssonStandInit(**defaults), track_history=True)

    def test_grow_increases_ba(self):
        stand = self._make_stand()
        stand.grow(10)
        assert stand.basal_area_m2_per_ha > 28.5

    def test_grow_advances_age(self):
        stand = self._make_stand()
        stand.grow(10)
        assert stand.bh_age == pytest.approx(26.0, abs=0.1)

    def test_grow_preserves_stems_during_growth(self):
        """Growth projection does not subtract mortality (discrete event)."""
        stand = self._make_stand()
        stand.grow(5)
        assert stand.stems_per_ha == pytest.approx(4887.0)

    def test_grow_with_thinning_reduces_stems(self):
        stand = self._make_stand()
        stand.grow(5, thinning=PerssonThinningRequest(outtake=20.0))
        assert stand.stems_per_ha < 4887.0

    def test_grow_with_thinning_reduces_ba(self):
        stand = self._make_stand()
        row = stand.grow(5, thinning=PerssonThinningRequest(outtake=20.0))
        assert row is not None
        assert row["gallring"]["G_m2"] > 0.0
        assert row["kvarv_bestand"]["G_m2"] < row["fore_gallring"]["G_m2"]

    def test_second_step_has_self_thinning(self):
        """After first grow(), second grow() should apply mortality."""
        stand = self._make_stand()
        stand.grow(7)
        row2 = stand.grow(7)
        assert row2 is not None
        # self_thinning_summary should show some mortality
        st = stand.self_thinning_summary
        assert st["stems_per_ha"] > 0.0

    def test_grow_output_row_structure(self):
        stand = self._make_stand()
        row = stand.grow(5)
        assert row is not None
        for key in [
            "alder",
            "fore_gallring",
            "kvarv_bestand",
            "gallring",
            "g_proc",
            "total_prod",
            "med_tillv",
            "lop_tillv",
        ]:
            assert key in row

    def test_history_tracking(self):
        stand = self._make_stand()
        stand.grow(5)
        stand.grow(5)
        assert len(stand.rows) == 2

    def test_residual_thinning(self):
        """Residual outtake leaves target BA."""
        stand = self._make_stand()
        row = stand.grow(5, thinning=PerssonThinningRequest(outtake=20.0, outtake_type="residual"))
        assert row is not None
        assert row["kvarv_bestand"]["G_m2"] == pytest.approx(20.0, rel=0.1)


# ═══════════════════════════════════════════════════════════════════════════════
# Stand simulator – scheduled simulation
# ═══════════════════════════════════════════════════════════════════════════════


class TestPersson1992StandScheduled:
    """Test scheduled simulation with thinning programs."""

    def test_age_based_program(self):
        init = PerssonStandInit(
            h100_m=28.0,
            start_bh_age=16,
            final_bh_age=82,
            stems=4887.0,
            basal_area=28.5,
            latitude=64.0,
        )
        prog = PerssonThinningProgram(
            interval_type="age",
            first_trigger=16,
            intervals=[9, 8, 4, 4, 5, 4, 6],
            outtake_type="percent",
            outtakes=[20, 15, 15, 15, 15, 15, 15],
        )
        result = persson_simulate(init, prog)
        assert len(result.rows) >= 5
        # First row should match initial conditions
        r0 = result.rows[0]
        assert r0["fore_gallring"]["N_st"] == 4887.0
        assert r0["fore_gallring"]["G_m2"] == pytest.approx(28.5, abs=0.01)

    def test_ba_based_program(self):
        init = PerssonStandInit(
            h100_m=28.0,
            start_bh_age=16,
            final_bh_age=82,
            stems=4887.0,
            basal_area=28.5,
            latitude=64.0,
        )
        prog = PerssonThinningProgram(
            interval_type="basal_area",
            first_trigger=28.0,
            intervals=[6.0, 6.0, 6.0],
            outtake_type="percent",
            outtakes=[20, 20, 20, 20],
        )
        result = persson_simulate(init, prog)
        assert len(result.rows) >= 3

    def test_simulation_terminates(self):
        init = PerssonStandInit(
            h100_m=28.0,
            start_bh_age=16,
            final_bh_age=82,
            stems=4887.0,
            basal_area=28.5,
            latitude=64.0,
        )
        prog = PerssonThinningProgram(
            interval_type="age",
            first_trigger=25,
            intervals=[10, 10, 10],
            outtake_type="percent",
            outtakes=[20, 15, 15, 0],
        )
        result = persson_simulate(init, prog)
        # Should have terminated at or after BH age 82
        last = result.rows[-1]
        assert last["alder"]["BRH_AR"] >= 60

    def test_volume_increases_over_time(self):
        """Total production volume should monotonically increase."""
        init = PerssonStandInit(
            h100_m=24.0,
            start_bh_age=20,
            final_bh_age=80,
            stems=3000.0,
            basal_area=20.0,
            latitude=64.0,
        )
        prog = PerssonThinningProgram(
            interval_type="age",
            first_trigger=30,
            intervals=[10, 10, 10],
            outtake_type="percent",
            outtakes=[15, 15, 15, 0],
        )
        result = persson_simulate(init, prog)
        tot_vols = [r["total_prod"]["V_m3sk"] for r in result.rows]
        for i in range(1, len(tot_vols)):
            assert tot_vols[i] >= tot_vols[i - 1] - 0.1


# ═══════════════════════════════════════════════════════════════════════════════
# Yield table validation – T28:1N first period
# ═══════════════════════════════════════════════════════════════════════════════


class TestYieldTableT28_1N_FirstPeriod:
    """Validate against Persson (1992) yield table T28:1N (p. 151).

    Reference conditions: Site Index 28.0 m, Latitude 64.0, Northern Sweden.
    First period: BH age 16, 4887 stems, BA 28.5 m²/ha.

    Only values readable with confidence from the published table are checked.
    """

    def test_first_period_before_thinning(self):
        """Verify initial state matches the reference table."""
        init = PerssonStandInit(
            h100_m=28.0,
            start_bh_age=16,
            final_bh_age=82,
            stems=4887.0,
            basal_area=28.5,
            latitude=64.0,
        )
        prog = PerssonThinningProgram(
            interval_type="age",
            first_trigger=16,
            intervals=[9],
            outtake_type="percent",
            outtakes=[20],
        )
        result = persson_simulate(init, prog)
        r0 = result.rows[0]

        fg = r0["fore_gallring"]
        assert fg["DG_cm"] == pytest.approx(8.6, abs=0.1)
        assert fg["N_st"] == 4887
        assert fg["G_m2"] == pytest.approx(28.5, abs=0.01)
        assert fg["V_m3sk"] == pytest.approx(134.0, abs=3.0)

    def test_first_period_thinning_removal(self):
        """Verify thinning removal matches the reference table."""
        init = PerssonStandInit(
            h100_m=28.0,
            start_bh_age=16,
            final_bh_age=82,
            stems=4887.0,
            basal_area=28.5,
            latitude=64.0,
        )
        prog = PerssonThinningProgram(
            interval_type="age",
            first_trigger=16,
            intervals=[9],
            outtake_type="percent",
            outtakes=[20],
        )
        result = persson_simulate(init, prog)
        r0 = result.rows[0]

        ga = r0["gallring"]
        assert ga["N_st"] == pytest.approx(1527, abs=5)
        assert ga["G_m2"] == pytest.approx(5.7, abs=0.1)
        assert ga["DG_cm"] == pytest.approx(6.9, abs=0.2)

    def test_first_period_remaining_stand(self):
        """Verify remaining stand after thinning."""
        init = PerssonStandInit(
            h100_m=28.0,
            start_bh_age=16,
            final_bh_age=82,
            stems=4887.0,
            basal_area=28.5,
            latitude=64.0,
        )
        prog = PerssonThinningProgram(
            interval_type="age",
            first_trigger=16,
            intervals=[9],
            outtake_type="percent",
            outtakes=[20],
        )
        result = persson_simulate(init, prog)
        r0 = result.rows[0]

        kv = r0["kvarv_bestand"]
        assert kv["N_st"] == pytest.approx(3360, abs=5)
        assert kv["G_m2"] == pytest.approx(22.8, abs=0.2)

    def test_self_thinning_summary_reasonable(self):
        """Self-thinning totals should be in a reasonable range.

        Reference: ~222 stems, ~1.9 m² BA, ~18 m³sk volume.
        We use wide tolerances as exact thinning program is approximate.
        """
        init = PerssonStandInit(
            h100_m=28.0,
            start_bh_age=16,
            final_bh_age=82,
            stems=4887.0,
            basal_area=28.5,
            latitude=64.0,
        )
        prog = PerssonThinningProgram(
            interval_type="age",
            first_trigger=16,
            intervals=[9, 8, 4, 4, 5, 4, 6, 4, 8, 8, 6],
            outtake_type="percent",
            outtakes=[20, 15, 15, 15, 15, 15, 15, 15, 0, 0, 0],
        )
        result = persson_simulate(init, prog)
        st = result.self_thinning_summary

        # Self-thinning should be positive
        assert st["stems_per_ha"] > 50
        assert st["basal_area_m2_per_ha"] > 0.5
        assert st["volume_m3sk_per_ha"] > 5.0

        # Should be in the right ballpark (reference: 222/1.9/18)
        assert st["stems_per_ha"] < 600
        assert st["basal_area_m2_per_ha"] < 5.0
        assert st["volume_m3sk_per_ha"] < 40.0


# ═══════════════════════════════════════════════════════════════════════════════
# Southern Sweden (T28:1S)
# ═══════════════════════════════════════════════════════════════════════════════


class TestMultiPeriodDrift:
    """Ensure the model does not drift versus Persson (1992) reference values.

    These tests verify structural invariants and equation-level consistency
    across the full rotation, independent of the exact thinning program.
    """

    @staticmethod
    def _run_full_rotation(lat: float = 64.0) -> PerssonSimulationResult:
        init = PerssonStandInit(
            h100_m=28.0,
            start_bh_age=16,
            final_bh_age=82,
            stems=4887.0,
            basal_area=28.5,
            latitude=lat,
        )
        prog = PerssonThinningProgram(
            interval_type="age",
            first_trigger=16,
            intervals=[3, 6, 12, 4, 5, 4, 6],
            outtake_type="percent",
            outtakes=[20, 20, 20, 20, 20, 20, 20, 20],
        )
        return persson_simulate(init, prog)

    def test_hdom_tracks_hagglund_at_every_period(self):
        """Dominant height must follow the Hägglund (1974) curve at each age.

        This is the single most important anti-drift check: if Hdom is wrong,
        all derived variables (volume, increment) will compound the error.
        """
        from pyforestry.base.helpers import Age
        from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970

        result = self._run_full_rotation()
        regen = Hagglund_1970.regeneration.CULTURE

        for row in result.rows:
            bh_age = row["alder"]["BRH_AR"]
            sim_h = row["alder"]["HDOM_m"]
            ref_si = Hagglund_1970.height_trajectory.pinus_sylvestris.sweden(
                dominant_height_m=28.0,
                age=Age.TOTAL(100),
                age2=Age.DBH(bh_age),
                regeneration=regen,
            )
            ref_h = round(float(ref_si), 1)
            assert sim_h == pytest.approx(ref_h, abs=0.15), (
                f"Hdom mismatch at BRH={bh_age}: sim={sim_h}, ref={ref_h}"
            )

    def test_total_production_monotonically_increases(self):
        """Cumulative BA and volume production must never decrease."""
        result = self._run_full_rotation()
        prev_g = prev_v = 0.0
        for row in result.rows:
            g = row["total_prod"]["G_m2"]
            v = row["total_prod"]["V_m3sk"]
            assert g >= prev_g - 0.01, f"Total BA decreased at BRH={row['alder']['BRH_AR']}"
            assert v >= prev_v - 0.01, f"Total Vol decreased at BRH={row['alder']['BRH_AR']}"
            prev_g, prev_v = g, v

    def test_stems_never_increase(self):
        """Stems before thinning at period N+1 ≤ stems after thinning at period N."""
        result = self._run_full_rotation()
        prev_remaining = float("inf")
        for row in result.rows:
            n_before = row["fore_gallring"]["N_st"]
            n_remaining = row["kvarv_bestand"]["N_st"]
            assert n_before <= prev_remaining + 0.5, (
                f"Stems increased at BRH={row['alder']['BRH_AR']}: "
                f"before={n_before}, prev_remaining={prev_remaining}"
            )
            prev_remaining = n_remaining

    def test_volume_consistent_with_ba_and_height(self):
        """Volume from the output row must match the volume regression."""
        result = self._run_full_rotation()
        for row in result.rows:
            ba = row["fore_gallring"]["G_m2"]
            hdom = row["alder"]["HDOM_m"]
            stems = row["fore_gallring"]["N_st"]
            vol_sim = row["fore_gallring"]["V_m3sk"]
            vol_eq = volume_m3sk(ba, hdom, stems, 64.0)
            assert vol_sim == pytest.approx(vol_eq, rel=0.01), (
                f"Volume inconsistency at BRH={row['alder']['BRH_AR']}: "
                f"row={vol_sim:.1f}, eq={vol_eq:.1f}"
            )

    def test_ba_increment_reasonable_across_rotation(self):
        """Annual BA increment should stay within physically plausible bounds.

        For SI=28 pine in northern Sweden, typical BA increment is 0.3–2.0 m²/ha/yr.
        """
        result = self._run_full_rotation()
        for row in result.rows:
            cai_g = row["lop_tillv"]["G_m2_per_yr"]
            if cai_g > 0:
                assert 0.1 < cai_g < 3.0, (
                    f"BA CAI out of range at BRH={row['alder']['BRH_AR']}: {cai_g:.3f}"
                )

    def test_mean_annual_increment_peaks_and_declines(self):
        """MAI-volume should eventually decline (classic growth curve)."""
        result = self._run_full_rotation()
        mai_values = [
            r["med_tillv"]["V_m3sk_per_yr"]
            for r in result.rows
            if r["med_tillv"]["V_m3sk_per_yr"] > 0
        ]
        assert len(mai_values) >= 5
        peak = max(mai_values)
        last = mai_values[-1]
        # MAI should peak and then decline (or plateau)
        assert last <= peak * 1.05  # allow small tolerance

    def test_self_thinning_accumulates_correctly(self):
        """Gallring removals + final stems = initial stems.

        At non-thinning rows, Gallring shows self-thinning.  At thinning
        rows, Gallring shows only the scheduled removal (hidden
        self-thinning is accumulated to the summary but not subtracted
        from the state).  So sum(Gallring) + final == initial.
        """
        result = self._run_full_rotation()
        initial_n = result.rows[0]["fore_gallring"]["N_st"]
        final_n = result.rows[-1]["kvarv_bestand"]["N_st"]
        all_removed = sum(r["gallring"]["N_st"] for r in result.rows)

        balance = initial_n - final_n - all_removed
        assert abs(balance) < 1.0, (
            f"Stem balance error: {initial_n} - {final_n} - {all_removed} = {balance}"
        )

    def test_multiperiod_growth_not_diverging(self):
        """Grow for 10 steps of 7 years; BA should not diverge.

        This tests that the under-bark/over-bark conversion cycle
        doesn't cause numerical drift over many periods.
        """
        stand = Persson1992Stand(
            PerssonStandInit(
                h100_m=28.0,
                start_bh_age=20,
                stems=2000.0,
                basal_area=22.0,
                latitude=64.0,
            ),
            track_history=True,
        )
        for _ in range(10):
            stand.grow(7)

        # After 70 years of growth from age 20 → age 90 (BH)
        assert stand.bh_age == pytest.approx(90.0, abs=0.1)
        # BA should be plausible (not exploding or collapsing)
        assert 20.0 < stand.basal_area_m2_per_ha < 80.0
        # Volume should be plausible
        assert 200.0 < stand.volume_m3sk < 1000.0
        # Stems decreased by mortality
        assert stand.stems_per_ha < 2000.0
        assert stand.stems_per_ha > 200.0

    def test_north_vs_south_growth_difference(self):
        """Southern Sweden should produce more volume at same site index.

        The BA increment has a negative latitude coefficient, so lower
        latitude → higher growth.
        """
        res_n = self._run_full_rotation(lat=64.0)
        res_s = self._run_full_rotation(lat=58.0)
        vol_n = res_n.rows[-1]["total_prod"]["V_m3sk"]
        vol_s = res_s.rows[-1]["total_prod"]["V_m3sk"]
        assert vol_s > vol_n

    def test_t28_1n_brh33_checkpoint(self):
        """At BRH=33 the model's Hdom and growth must track the PDF.

        From the PDF T28:1N right half (p. 151): at BRH 33,
        Hdom ≈ 17.0 m and Before-thin N ≈ 1713, G ≈ 29.0.

        We test that at this age the *equations* produce reference-quality
        output by initialising at a PDF-like state and verifying volume.
        """
        # Initialise a stand at the PDF state for BRH=33
        stand = Persson1992Stand(
            PerssonStandInit(
                h100_m=28.0,
                start_bh_age=33,
                stems=1713.0,
                basal_area=29.0,
                latitude=64.0,
            ),
            track_history=True,
        )
        row = stand.grow(7)
        assert row is not None
        # Hdom must match Hägglund
        assert row["alder"]["HDOM_m"] == pytest.approx(17.0, abs=0.1)
        # Volume regression at this state: ~218 m³sk (from PDF)
        assert row["fore_gallring"]["V_m3sk"] == pytest.approx(218, rel=0.05)

    def test_t28_1s_self_thinning_in_range(self):
        """T28:1S self-thinning: PDF shows N≈279, G≈3.1, V≈26."""
        init = PerssonStandInit(
            h100_m=28.0,
            start_bh_age=16,
            final_bh_age=82,
            stems=4887.0,
            basal_area=28.5,
            latitude=58.0,
        )
        prog = PerssonThinningProgram(
            interval_type="age",
            first_trigger=16,
            intervals=[3, 6, 12, 4, 5, 4, 6],
            outtake_type="percent",
            outtakes=[25, 25, 20, 20, 20, 20, 20, 20],
        )
        result = persson_simulate(init, prog)
        st = result.self_thinning_summary
        # Self-thinning should be positive and in the right order
        assert st["stems_per_ha"] > 50
        assert st["stems_per_ha"] < 600
        assert st["basal_area_m2_per_ha"] > 0.5
        assert st["volume_m3sk_per_ha"] > 3.0


# ═══════════════════════════════════════════════════════════════════════════════
# Yield table replication — T28:1N
# ═══════════════════════════════════════════════════════════════════════════════


class TestYieldTableT28_1N:
    """Validate the model against the published T28:1N yield table.

    Reference: Persson (1992), page 11 — Scots Pine, H100=28m,
    thinning program 1, northern Sweden (lat 64).
    """

    T28_1N_REF = [
        # BRH, Fore_N, Fore_BA, Fore_Vol, Kvarv_N, Kvarv_BA, Gal_N, Gal_BA
        (16, 4887, 28.5, 134, 3360, 22.8, 1527, 5.7),
        (19, 3360, 26.4, 139, 2310, 21.1, 1050, 5.3),
        (25, 2310, 27.4, 173, 1713, 21.9, 597, 5.5),
        (33, 1713, 29.0, 218, 1677, 28.8, 36, 0.3),
        (38, 1677, 33.0, 269, 1263, 26.4, 414, 6.6),
        (46, 1263, 32.3, 292, 1244, 32.1, 19, 0.3),
        (48, 1244, 33.5, 310, 937, 26.8, 307, 6.7),
        (56, 937, 31.9, 319, 926, 31.7, 11, 0.2),
        (60, 926, 34.2, 353, 754, 29.1, 171, 5.1),
        (68, 754, 33.7, 367, 747, 33.5, 7, 0.2),
        (76, 747, 38.1, 433, 739, 37.8, 8, 0.2),
        (82, 739, 41.2, 482, 734, 41.0, 6, 0.2),
    ]

    @pytest.fixture()
    def result(self):
        init = PerssonStandInit(
            h100_m=28.0,
            start_bh_age=16,
            latitude=64.0,
            final_bh_age=82,
            stems=4887,
            basal_area=28.5,
            regeneration="culture",
        )
        program = PerssonThinningProgram(
            interval_type="age",
            first_trigger=16.0,
            intervals=[3, 6, 13, 10, 12],
            outtake_type="percent",
            outtakes=[20, 20, 20, 20, 20, 15],
        )
        stand = Persson1992Stand(init, program, track_history=True)
        stand.run()
        return stand

    def test_correct_number_of_rows(self, result):
        assert len(result.rows) == 12

    def test_brh_ages_match(self, result):
        expected = [r[0] for r in self.T28_1N_REF]
        actual = [r["alder"]["BRH_AR"] for r in result.rows]
        assert actual == expected

    def test_fore_stems_match(self, result):
        for row, (brh, ref_n, *_) in zip(result.rows, self.T28_1N_REF, strict=False):
            assert row["fore_gallring"]["N_st"] == pytest.approx(ref_n, abs=3), (
                f"BRH={brh}: Fore N"
            )

    def test_fore_ba_match(self, result):
        for row, (brh, _, ref_ba, *_) in zip(result.rows, self.T28_1N_REF, strict=False):
            assert row["fore_gallring"]["G_m2"] == pytest.approx(ref_ba, abs=0.2), (
                f"BRH={brh}: Fore BA"
            )

    def test_fore_volume_match(self, result):
        for row, (brh, _, _, ref_vol, *_) in zip(result.rows, self.T28_1N_REF, strict=False):
            assert row["fore_gallring"]["V_m3sk"] == pytest.approx(ref_vol, rel=0.02), (
                f"BRH={brh}: Fore Vol"
            )

    def test_kvarv_stems_match(self, result):
        for row, (brh, _, _, _, ref_kn, *_) in zip(result.rows, self.T28_1N_REF, strict=False):
            assert row["kvarv_bestand"]["N_st"] == pytest.approx(ref_kn, abs=3), (
                f"BRH={brh}: Kvarv N"
            )

    def test_kvarv_ba_match(self, result):
        for row, (brh, _, _, _, _, ref_kba, *_) in zip(result.rows, self.T28_1N_REF, strict=False):
            assert row["kvarv_bestand"]["G_m2"] == pytest.approx(ref_kba, abs=0.3), (
                f"BRH={brh}: Kvarv BA"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# GrowthModel adapter
# ═══════════════════════════════════════════════════════════════════════════════


class TestPersson1992Model:
    """Test the GrowthModel adapter."""

    def test_component_id(self):
        model = Persson1992Model()
        assert model.component_id == "persson_1992"

    def test_source(self):
        model = Persson1992Model()
        src = model.source
        assert src.author == "Persson, O."
        assert src.year == 1992
        assert src.title.startswith("En produktionsmodell för tallskog i Sverige")
        assert "Rapport nr 31" in src.note

    def test_requirements_aggregate(self):
        model = Persson1992Model()
        req = model.requirements()
        assert req.inventory == "aggregate"


# ═══════════════════════════════════════════════════════════════════════════════
# Descriptor
# ═══════════════════════════════════════════════════════════════════════════════


class TestDescriptor:
    def test_descriptor_present(self):
        from pyforestry.sweden.systems.persson_1992 import DESCRIPTOR

        assert DESCRIPTOR.component_id == "persson_1992_model"
        assert DESCRIPTOR.kind == "model"
        assert DESCRIPTOR.domain == "growth"


# ═══════════════════════════════════════════════════════════════════════════════
# Edge cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Verify edge-case handling."""

    def test_final_age_must_exceed_start(self):
        with pytest.raises(ValueError, match="Final age"):
            Persson1992Stand(
                PerssonStandInit(
                    h100_m=28.0,
                    start_bh_age=50,
                    final_bh_age=30,
                    stems=2000,
                    basal_area=20.0,
                    latitude=64.0,
                )
            )

    def test_step_without_program_raises(self):
        stand = Persson1992Stand(
            PerssonStandInit(
                h100_m=28.0,
                start_bh_age=16,
                stems=4887,
                basal_area=28.5,
                latitude=64.0,
            )
        )
        with pytest.raises(ValueError, match="PerssonThinningProgram"):
            stand.step()

    def test_high_thinning_doesnt_crash(self):
        """Heavy thinning (50%) should still produce valid output."""
        stand = Persson1992Stand(
            PerssonStandInit(
                h100_m=28.0,
                start_bh_age=16,
                stems=4887,
                basal_area=28.5,
                latitude=64.0,
            ),
            track_history=True,
        )
        row = stand.grow(5, thinning=PerssonThinningRequest(outtake=50.0))
        assert row is not None
        assert row["kvarv_bestand"]["N_st"] > 0

    def test_different_site_indices(self):
        """Model should work for a range of site indices."""
        for si in [16, 20, 24, 28, 32]:
            stand = Persson1992Stand(
                PerssonStandInit(
                    h100_m=float(si),
                    start_bh_age=20,
                    stems=3000,
                    basal_area=20.0,
                    latitude=62.0,
                )
            )
            row = stand.grow(7)
            assert row is not None
            assert row["fore_gallring"]["V_m3sk"] > 0

    def test_run_method(self):
        """run() should complete and return the stand."""
        init = PerssonStandInit(
            h100_m=24.0,
            start_bh_age=20,
            final_bh_age=60,
            stems=3000,
            basal_area=20.0,
            latitude=64.0,
        )
        prog = PerssonThinningProgram(
            interval_type="age",
            first_trigger=30,
            intervals=[10],
            outtake_type="percent",
            outtakes=[15, 0],
        )
        stand = Persson1992Stand(init, program=prog, track_history=True).run()
        assert stand.done
        assert len(stand.rows) >= 2


# ═══════════════════════════════════════════════════════════════════════════════
# The GrowthModel adapter, driven
# ═══════════════════════════════════════════════════════════════════════════════


class TestPersson1992ModelRuns:
    """The adapter that plugs this system into the simulation runtime.

    Its identity and requirements were asserted, but nothing had ever built a
    context from it or stepped one, so the whole surface a runtime actually
    touches -- ``build_context``, ``update_step``, the thinning action -- was
    untested.
    """

    @staticmethod
    def _init(**kwargs) -> PerssonStandInit:
        base = {
            "h100_m": 24.0,
            "start_bh_age": 30.0,
            "latitude": 60.0,
            "stems": 2000.0,
            "basal_area": 20.0,
        }
        base.update(kwargs)
        return PerssonStandInit(**base)

    @staticmethod
    def _stand():
        from pyforestry.base.helpers.primitives import StandBasalArea, Stems
        from pyforestry.base.helpers.stand import Stand
        from pyforestry.base.helpers.tree_species import TreeSpecies

        pine = TreeSpecies.Sweden.pinus_sylvestris
        return Stand.from_aggregate_metrics(
            {
                "BasalArea": {"TOTAL": StandBasalArea(20.0, species=pine)},
                "Stems": {"TOTAL": Stems(2000.0, species=pine)},
            },
            area_ha=1.0,
        )

    def test_build_context_seeds_the_runtime_from_the_stand_model(self):
        model = Persson1992Model()
        ctx = model.build_context(self._stand(), init=self._init())

        stand_model = ctx.attrs["persson_1992_stand"]
        assert isinstance(stand_model, Persson1992Stand)
        # The clock starts at the stand's breast-height age, not at zero.
        assert ctx.state["t"] == pytest.approx(30.0)
        assert ctx.state["years_since_thin"] == 0.0
        assert float(ctx.metrics["BasalArea"]["TOTAL"]) == pytest.approx(
            stand_model.basal_area_m2_per_ha
        )
        assert float(ctx.metrics["Stems"]["TOTAL"]) == pytest.approx(stand_model.stems_per_ha)

    def test_stepping_grows_the_stand_and_publishes_the_row(self):
        model = Persson1992Model(track_history=True)
        ctx = model.build_context(self._stand(), init=self._init())
        before = float(ctx.metrics["BasalArea"]["TOTAL"])

        ctx.update_step(5.0)

        assert float(ctx.metrics["BasalArea"]["TOTAL"]) > before, "a pine stand grows"
        # The row is stamped with the breast-height age the period *started* at.
        assert ctx.attrs["persson_1992_last_row"]["alder"]["BRH_AR"] == 30
        assert len(ctx.attrs["persson_1992_rows"]) >= 1
        assert ctx.state["years_since_thin"] == pytest.approx(5.0)

    def test_a_scheduled_thinning_is_taken_on_the_next_step(self):
        model = Persson1992Model()
        ctx = model.build_context(self._stand(), init=self._init())
        ctx.update_step(5.0)
        thinned_from = float(ctx.metrics["BasalArea"]["TOTAL"])

        assert "schedule_thinning" in model.available_actions()
        ctx.do("schedule_thinning", outtake=30.0, outtake_type="percent")
        ctx.update_step(5.0)

        assert float(ctx.metrics["BasalArea"]["TOTAL"]) < thinned_from
        # The clock since the last thinning restarts, which is what a program
        # keyed on intervals reads.
        assert ctx.state["years_since_thin"] == 0.0

    def test_an_unknown_outtake_type_is_refused(self):
        model = Persson1992Model()
        ctx = model.build_context(self._stand(), init=self._init())
        with pytest.raises(ValueError, match="percent, residual, or absolute"):
            ctx.do("schedule_thinning", outtake=30.0, outtake_type="half")

    def test_the_init_can_come_from_the_stand_or_the_model(self):
        stand = self._stand()
        stand.attrs["persson_1992_init"] = self._init(start_bh_age=35.0)
        # From the stand, when the call gives none.
        assert Persson1992Model().build_context(stand).state["t"] == pytest.approx(35.0)
        # From the model's own default, when neither does.
        default = Persson1992Model(self._init(start_bh_age=40.0))
        assert default.build_context(self._stand()).state["t"] == pytest.approx(40.0)
        # The call wins over both.
        assert default.build_context(stand, init=self._init()).state["t"] == pytest.approx(30.0)

    def test_a_model_with_no_init_anywhere_says_so(self):
        with pytest.raises(ValueError, match="requires a PerssonStandInit"):
            Persson1992Model().build_context(self._stand())

    def test_stems_and_basal_area_fall_back_to_the_stand(self):
        """An init that leaves them out reads them off the inventory it is given."""
        model = Persson1992Model()
        ctx = model.build_context(self._stand(), init=self._init(stems=None, basal_area=None))
        stand_model = ctx.attrs["persson_1992_stand"]
        assert stand_model.stems_per_ha == pytest.approx(2000.0)
        assert stand_model.basal_area_m2_per_ha == pytest.approx(20.0)

    def test_a_context_without_a_stand_model_is_refused(self):
        model = Persson1992Model()
        ctx = model.build_context(self._stand(), init=self._init())
        del ctx.attrs["persson_1992_stand"]
        with pytest.raises(ValueError, match="missing stand model"):
            ctx.update_step(5.0)


class TestInitialStandPartialInputs:
    """One of stems or basal area given, the other estimated.

    Both-given and both-missing were covered; the two halves in between were the
    largest untested block in the module, and they are four different
    Elfving-Hägglund functions -- north and south, stems and basal area.
    """

    @pytest.mark.parametrize("latitude, altitude", [(64.0, 200.0), (58.0, 100.0)])
    def test_stems_are_estimated_when_only_basal_area_is_given(self, latitude, altitude):
        init = PerssonStandInit(
            h100_m=28.0,
            start_bh_age=16,
            latitude=latitude,
            altitude_m=altitude,
            basal_area=28.5,
        )
        _hdom, stems, ba, _si, _t13 = persson_estimate_initial_stand(init)
        assert ba == 28.5, "what was given is kept"
        assert 500 < stems < 10000

    @pytest.mark.parametrize("latitude, altitude", [(64.0, 200.0), (58.0, 100.0)])
    def test_basal_area_is_estimated_when_only_stems_are_given(self, latitude, altitude):
        init = PerssonStandInit(
            h100_m=28.0,
            start_bh_age=16,
            latitude=latitude,
            altitude_m=altitude,
            stems=4887.0,
        )
        _hdom, stems, ba, _si, _t13 = persson_estimate_initial_stand(init)
        assert stems == 4887.0, "what was given is kept"
        assert 5.0 < ba < 50.0
