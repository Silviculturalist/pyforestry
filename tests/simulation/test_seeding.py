"""Regression tests for seed policy utilities."""

from __future__ import annotations

from pyforestry.simulation.seeding import (
    FixedSeedPolicy,
    PerModuleOffsetPolicy,
    RollingSeedPolicy,
)


def test_fixed_seed_policy_restores_state() -> None:
    policy = FixedSeedPolicy(123)
    policy.start_run()
    rng = policy.generator("stand", "module")
    rng.integers(0, 1000)
    snapshot = policy.snapshot()
    second = rng.integers(0, 1000)

    clone = FixedSeedPolicy(0)
    clone.restore(snapshot)
    restored_rng = clone.generator("stand", "module")
    assert restored_rng.integers(0, 1000) == second


def test_per_module_offset_policy_distinguishes_modules() -> None:
    policy = PerModuleOffsetPolicy(base_seed=10, offsets={"A": 1, "B": 99})
    policy.start_run()
    rng_a = policy.generator("stand", "A")
    rng_b = policy.generator("stand", "B")
    snapshot = policy.snapshot()
    assert snapshot["streams"]["stand::A"] != snapshot["streams"]["stand::B"]
    assert rng_a.integers(0, 10_000) != rng_b.integers(0, 10_000)


def test_rolling_seed_policy_snapshot_and_restore() -> None:
    policy = RollingSeedPolicy(5)
    policy.start_run()
    rng1 = policy.generator("stand", "M1")
    rng1.integers(0, 10_000)
    snapshot = policy.snapshot()
    next_value = rng1.integers(0, 10_000)
    rng2 = policy.generator("stand", "M2")
    second_value = rng2.integers(0, 10_000)

    restored = RollingSeedPolicy(0)
    restored.restore(snapshot)
    restored_rng1 = restored.generator("stand", "M1")
    assert restored_rng1.integers(0, 10_000) == next_value
    restored_rng2 = restored.generator("stand", "M2")
    assert restored_rng2.integers(0, 10_000) == second_value
