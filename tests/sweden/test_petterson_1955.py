"""Tests for the Petterson (1955) coniferous-forest yield-table model.

The published production tables (Del XIV of Petterson 1955) are used as
numeric oracles.  Reference rows are transcribed as
``(total_age, stems_after, ba_after, volume_after)``.
"""

from __future__ import annotations

import math
from dataclasses import FrozenInstanceError

import pytest

from pyforestry.base.helpers import Stand
from pyforestry.sweden.blocks.petterson_1955 import (
    PETTERSON_VARIANTS,
    Petterson1955Model,
    Petterson1955Stand,
    PettersonSimulationResult,
    PettersonStandInit,
    PettersonThinningProgram,
    PettersonVariant,
    PettersonYieldRow,
    _f_sigma_s,
    _f_stems,
    _m31_ab,
    _naslund_volume_ub,
    _resolve_variant,
    _start_age_for_height,
    _u_prime_high,
    petterson_simulate,
    petterson_structure_factors,
    petterson_top_height,
)
from pyforestry.sweden.timber import SweTimber
from pyforestry.sweden.volume.naslund_1947 import NaslundVolume

# ═══════════════════════════════════════════════════════════════════════════════
# Published-table oracles: (age, stems_after, ba_after, volume_after)
# ═══════════════════════════════════════════════════════════════════════════════

# P.9  Tall, Norra Sverige, icke planterad.  H100=20.  L 5 G 6, 10.
P9_PINE_NORTH = [
    (38, 5954, 18.6, 53),
    (48, 3936, 18.3, 67),
    (58, 2661, 18.2, 81),
    (68, 1843, 17.9, 95),
    (78, 1304, 17.5, 105),
    (88, 937, 16.7, 114),
    (98, 690, 16.0, 118),
    (108, 513, 15.0, 120),
    (118, 387, 14.0, 120),
    (128, 294, 12.9, 116),
    (138, 225, 11.8, 112),
    (148, 173, 10.7, 106),
]
# P.58  Tall, Södra Sverige, icke planterad.  H100=20.  L 5 G 10, 10.
P58_PINE_SOUTH = [
    (31, 4461, 17.6, 47),
    (41, 2703, 18.3, 64),
    (51, 1675, 17.8, 76),
    (61, 1063, 16.9, 84),
    (71, 690, 15.8, 88),
    (81, 455, 14.6, 89),
    (91, 307, 13.4, 87),
    (101, 209, 12.0, 83),
    (111, 145, 10.7, 77),
]
# P.83  Gran, Södra Sverige, icke planterad.  H100=24.  L 5 G 10, 5.
P83_SPRUCE_SOUTH = [
    (29, 5327, 17.7, 53),
    (39, 3266, 22.0, 90),
    (49, 2050, 22.9, 119),
    (59, 1315, 22.7, 141),
    (69, 860, 22.0, 157),
    (79, 572, 21.1, 166),
    (89, 386, 19.9, 169),
    (99, 263, 18.4, 165),
    (109, 181, 16.7, 156),
]
# P.72  Gran, Norra Sverige, icke planterad.  H100=20.  L 5 G 4, 10.  (provisional)
P72_SPRUCE_NORTH = [
    (48, 2785, 7.6, 22),
    (58, 1920, 13.8, 53),
    (68, 1354, 16.4, 79),
    (78, 978, 18.0, 104),
    (88, 722, 18.2, 122),
    (98, 541, 17.5, 133),
    (108, 416, 16.5, 139),
    (118, 322, 15.2, 141),
    (128, 254, 13.8, 138),
    (138, 201, 12.4, 134),
    (148, 161, 11.2, 128),
]
# P.21  Tall, Norra Sverige, icke planterad.  H100=20.  H 3 G 10, 10.  (high thinning)
P21_PINE_NORTH_HIGH = [
    (38, 6764, 17.3, 48),
    (48, 5129, 16.1, 56),
    (58, 3889, 15.2, 63),
    (68, 2948, 14.3, 68),
    (88, 1696, 12.3, 72),
    (108, 975, 10.2, 70),
    (128, 562, 8.4, 65),
    (148, 323, 6.7, 56),
    (168, 186, 5.1, 47),
]


def _rows_by_age(result: PettersonSimulationResult):
    return {r.total_age: r for r in result.rows}


# ═══════════════════════════════════════════════════════════════════════════════
# Structure factors (Kap 9.3 / appendix M7)
# ═══════════════════════════════════════════════════════════════════════════════


class TestStructureFactors:
    def test_phi3_matches_book(self):
        m, s, f = petterson_structure_factors(3.0)
        assert m / 3.0 == pytest.approx(0.264, abs=0.001)  # M'/phi (M31)
        assert s == pytest.approx(0.5894, abs=0.001)
        assert f == pytest.approx(0.49865, abs=0.0005)

    def test_phi6_is_full_normal(self):
        m, s, f = petterson_structure_factors(6.0)
        assert m == pytest.approx(3.0, abs=1e-6)
        assert f == pytest.approx(0.99730, abs=1e-4)

    def test_phi_gt6_continuation(self):
        # For phi > 6 the shape saturates while M' continues linearly (Kap 12.5).
        m, s, f = petterson_structure_factors(7.0)
        assert m == pytest.approx(4.0, abs=1e-6)
        _, s6, f6 = petterson_structure_factors(6.0)
        assert s == pytest.approx(s6)
        assert f == pytest.approx(f6)

    def test_retained_fraction_monotone(self):
        fs = [petterson_structure_factors(p)[2] for p in (3.0, 4.0, 5.0, 6.0)]
        assert fs == sorted(fs)  # F(phi) increases with phi


# ═══════════════════════════════════════════════════════════════════════════════
# Starting-state derivation (worked examples in M27/M28/M34)
# ═══════════════════════════════════════════════════════════════════════════════


class TestStartingState:
    def test_pine_north_p13(self):
        v = PETTERSON_VARIANTS["pine_north"]
        # M34/M28: Ms1=5.0, phi=3 -> sigma_s1=2.964, alpha0=1.021, L0=16.108, S1~8920
        sigma_s1 = _f_sigma_s(v, 5.0)
        assert sigma_s1 == pytest.approx(2.964, abs=0.005)
        m, s, _f = petterson_structure_factors(3.0)
        sigma_n0 = sigma_s1 / s
        alpha0 = 5.0 - m * sigma_n0
        assert sigma_n0 == pytest.approx(5.029, abs=0.01)
        assert alpha0 == pytest.approx(1.021, abs=0.01)
        assert alpha0 + 3.0 * sigma_n0 == pytest.approx(16.108, abs=0.02)
        assert _f_stems(v, 5.0) == pytest.approx(8920, rel=0.01)

    def test_spruce_south_f82_two_regimes(self):
        v = PETTERSON_VARIANTS["spruce_south"]
        assert _f_stems(v, 12.0) == pytest.approx(10 ** (5.245 - 1.613 * math.log10(12.0)))
        # regime II (Ms < 9): log10(7000 - S) = 1.633 + 2.363 log10(Ms-4)
        s = _f_stems(v, 5.704)
        assert s == pytest.approx(7000 - 10 ** (1.633 + 2.363 * math.log10(1.704)))

    def test_start_age_from_top_height_8m(self):
        v = PETTERSON_VARIANTS["pine_north"]
        age = _start_age_for_height(v, 20.0, 8.0, 1.0)
        assert round(age) == 38  # register: Tall N, H100=20 -> start age 38
        assert petterson_top_height(v, age, 20.0) == pytest.approx(8.0, abs=0.02)


# ═══════════════════════════════════════════════════════════════════════════════
# Top-height trajectory (Kap 7.5); the 7.6 worked example
# ═══════════════════════════════════════════════════════════════════════════════


class TestTopHeight:
    def test_worked_example_pine_north(self):
        v = PETTERSON_VARIANTS["pine_north"]
        # 7.6: h100=20, total age 50 -> h_3sigma = 10.9 m
        assert petterson_top_height(v, 50.0, 20.0) == pytest.approx(10.9, abs=0.1)

    def test_reaches_h100_at_age_100(self):
        v = PETTERSON_VARIANTS["spruce_south"]
        assert petterson_top_height(v, 100.0, 24.0) == pytest.approx(24.0, abs=0.05)

    def test_zero_age(self):
        v = PETTERSON_VARIANTS["pine_north"]
        assert petterson_top_height(v, 0.0, 20.0) == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# Full yield-table reproduction
# ═══════════════════════════════════════════════════════════════════════════════


class TestYieldTableReproduction:
    def _check(self, result, oracle, ba_tol, vol_rel_tol, n_rel_tol=0.02):
        by_age = _rows_by_age(result)
        for age, n_ref, ba_ref, v_ref in oracle:
            row = by_age[age]
            assert abs(row.stems_after - n_ref) / n_ref < n_rel_tol, f"stems @ {age}"
            assert abs(row.ba_after_m2 - ba_ref) < ba_tol, f"ba @ {age}"
            assert abs(row.volume_after_m3sk - v_ref) <= vol_rel_tol * v_ref + 1.5, (
                f"vol @ {age}: {row.volume_after_m3sk} vs {v_ref}"
            )

    def test_pine_north_p9(self):
        result = petterson_simulate(
            PettersonStandInit("pine", "north", 20.0, max_total_age=148),
            PettersonThinningProgram(low=5.0, through=6.0, interval=10.0),
        )
        self._check(result, P9_PINE_NORTH, ba_tol=0.3, vol_rel_tol=0.02)

    def test_pine_south_p58(self):
        result = petterson_simulate(
            PettersonStandInit("pine", "south", 20.0, start_total_age=31, max_total_age=111),
            PettersonThinningProgram(low=5.0, through=10.0, interval=10.0),
        )
        self._check(result, P58_PINE_SOUTH, ba_tol=0.2, vol_rel_tol=0.02)

    def test_spruce_south_p83(self):
        result = petterson_simulate(
            PettersonStandInit("spruce", "south", 24.0, start_total_age=29, max_total_age=109),
            PettersonThinningProgram(low=5.0, through=10.0, interval=5.0),
        )
        self._check(result, P83_SPRUCE_SOUTH, ba_tol=0.2, vol_rel_tol=0.02)

    def test_spruce_north_p72_provisional(self):
        # Gran N is a provisional M31 reconstruction; looser tolerances.
        result = petterson_simulate(
            PettersonStandInit("spruce", "north", 20.0, start_total_age=48, max_total_age=148),
            PettersonThinningProgram(low=5.0, through=4.0, interval=10.0),
        )
        self._check(result, P72_SPRUCE_NORTH, ba_tol=1.5, vol_rel_tol=0.07)

    def test_pine_north_high_thinning_p21(self):
        # High thinning is a provisional M26 "överslag"; validated to ~1 %.
        result = petterson_simulate(
            PettersonStandInit("pine", "north", 20.0, max_total_age=168),
            PettersonThinningProgram(low=0.0, high=3.0, through=10.0, interval=10.0),
        )
        self._check(result, P21_PINE_NORTH_HIGH, ba_tol=0.4, vol_rel_tol=0.03)

    def test_high_thinning_removes_coarse_end(self):
        # High thinning yields a SMALLER mean diameter than low thinning
        # (it removes the largest trees).
        low = petterson_simulate(
            PettersonStandInit("pine", "north", 20.0, max_total_age=98),
            PettersonThinningProgram(low=5.0, through=6.0, interval=10.0),
        )
        high = petterson_simulate(
            PettersonStandInit("pine", "north", 20.0, max_total_age=98),
            PettersonThinningProgram(low=0.0, high=3.0, through=10.0, interval=10.0),
        )
        assert high.rows[-1].qmd_after_cm < low.rows[-1].qmd_after_cm

    def test_row_invariants(self):
        result = petterson_simulate(PettersonStandInit("pine", "north", 20.0, max_total_age=98))
        rows = result.rows
        # stems before at row N == stems after at row N-1
        for prev, cur in zip(rows, rows[1:], strict=False):
            assert cur.stems_before == pytest.approx(prev.stems_after, rel=1e-6)
        # volume before - removed == after
        for r in rows:
            assert r.volume_before_m3sk - r.volume_removed_m3sk == pytest.approx(
                r.volume_after_m3sk, abs=0.11
            )
        # first row has no current increment
        assert rows[0].cai_m3sk is None
        assert rows[1].cai_m3sk is not None


# ═══════════════════════════════════════════════════════════════════════════════
# M31 (Gran N) special growth
# ═══════════════════════════════════════════════════════════════════════════════


class TestM31:
    def test_identity_anchor_at_start(self):
        a, b = _m31_ab(0.0, 30.0, 20.0)
        assert (a, b) == pytest.approx((0.0, 1.0))

    def test_growth_increases_with_age(self):
        _, b0 = _m31_ab(0.0, 30.0, 20.0)
        _, b50 = _m31_ab(50.0, 30.0, 20.0)
        assert b50 > b0


# ═══════════════════════════════════════════════════════════════════════════════
# Thinning helpers + volume delegation
# ═══════════════════════════════════════════════════════════════════════════════


class TestHelpers:
    def test_u_prime_high_monotone(self):
        # Stronger high-thin grade => stronger (smaller) u', but still < 1.
        u3 = _u_prime_high(3.0)
        u5 = _u_prime_high(5.0)
        assert u5 < u3 < 1.0
        assert u3 == pytest.approx(0.990, abs=0.002)  # calibrated to P.21/P.22

    def test_volume_matches_naslund(self):
        # The per-class volume delegates to NaslundVolume (single source of truth).
        v = PETTERSON_VARIANTS["pine_north"]
        timber = SweTimber(
            species="pinus sylvestris",
            region="northern",
            diameter_cm=18.0,
            height_m=16.0,
            over_bark=False,
        )
        assert _naslund_volume_ub(v, 18.0, 16.0) == pytest.approx(
            max(0.0, NaslundVolume.calculate(timber))
        )

    def test_volume_zero_for_degenerate(self):
        v = PETTERSON_VARIANTS["spruce_south"]
        assert _naslund_volume_ub(v, 0.0, 10.0) == 0.0
        assert _naslund_volume_ub(v, 5.0, 1.3) == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# API / adapter / errors
# ═══════════════════════════════════════════════════════════════════════════════


class TestApi:
    def test_defaults_from_variant(self):
        stand = Petterson1955Stand(PettersonStandInit("pine", "north", 20.0)).run()
        assert stand.ms1 == 5.0 and stand.phi1 == 3.0
        assert stand.start_age == 38
        assert len(stand.rows) > 0
        assert all(isinstance(r, PettersonYieldRow) for r in stand.rows)

    def test_explicit_starting_state(self):
        stand = Petterson1955Stand(
            PettersonStandInit(
                "pine",
                "north",
                20.0,
                ms1=6.0,
                phi1=4.0,
                stems=5000.0,
                max_total_age=68,
            )
        ).run()
        assert stand.ms1 == 6.0 and stand.phi1 == 4.0 and stand.stems1 == 5000.0
        assert stand.rows[0].stems_before == pytest.approx(5000.0, rel=1e-6)

    def test_planted_uses_t_over(self):
        natural = Petterson1955Stand(PettersonStandInit("pine", "north", 20.0))
        planted = Petterson1955Stand(PettersonStandInit("pine", "north", 20.0, planted=True))
        assert planted.t_over == 0.7
        assert planted.start_age < natural.start_age  # planted reaches 8 m sooner

    def test_run_is_idempotent(self):
        stand = Petterson1955Stand(PettersonStandInit("pine", "north", 20.0))
        r1 = stand.run().rows
        r2 = stand.run().rows
        assert r1 is r2 and stand.done

    def test_bad_interval_raises(self):
        with pytest.raises(ValueError, match="multiple of five"):
            Petterson1955Stand(
                PettersonStandInit("pine", "north", 20.0),
                PettersonThinningProgram(interval=7.0),
            )

    def test_unknown_variant_raises(self):
        with pytest.raises(ValueError, match="Unknown Petterson variant"):
            _resolve_variant("larch", "north")

    def test_variant_dataclass_frozen(self):
        v = PETTERSON_VARIANTS["pine_north"]
        assert isinstance(v, PettersonVariant)
        with pytest.raises(FrozenInstanceError):
            v.f1_a = 0.0  # type: ignore[misc]

    def test_convenience_matches_stand(self):
        init = PettersonStandInit("spruce", "south", 24.0, max_total_age=59)
        result = petterson_simulate(init)
        stand = Petterson1955Stand(init).run()
        assert [r.total_age for r in result.rows] == [r.total_age for r in stand.rows]


class TestGrowthModelAdapter:
    def test_component_id_and_source(self):
        model = Petterson1955Model()
        assert model.component_id == "petterson_1955"
        assert model.source.year == 1955
        assert model.requirements().inventory == "aggregate"

    def test_build_context_and_step(self):
        init = PettersonStandInit("pine", "north", 20.0, max_total_age=78)
        model = Petterson1955Model(init)
        stand = Stand()
        ctx = model.build_context(stand)
        result = ctx.attrs["petterson_1955_result"]
        assert isinstance(result, PettersonSimulationResult)
        first_ba = result.rows[0].ba_after_m2
        assert float(ctx.metrics["BasalArea"]["TOTAL"]) == pytest.approx(first_ba)
        model.update_step(ctx, dt=10.0)
        assert ctx.state["occasion"] == 1
        assert ctx.attrs["petterson_1955_last_row"].total_age == result.rows[1].total_age
        # stepping past the end clamps to the last occasion
        for _ in range(50):
            model.update_step(ctx, dt=10.0)
        assert ctx.state["occasion"] == len(result.rows) - 1

    def test_build_context_requires_init(self):
        with pytest.raises(ValueError, match="requires a PettersonStandInit"):
            Petterson1955Model().build_context(Stand())

    def test_init_via_stand_attrs(self):
        init = PettersonStandInit("pine", "south", 20.0, start_total_age=31)
        stand = Stand()
        stand.attrs["petterson_1955_init"] = init
        ctx = Petterson1955Model().build_context(stand)
        assert ctx.attrs["petterson_1955_result"].variant == "pine_south"
