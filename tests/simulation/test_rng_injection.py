"""One RNG, injected and keyed.

Before this, `KeyedRNG`/`RandomBundle` had no consumer outside their own package
while five modules constructed their own generators, and the Elfving composite
carried two -- numpy and stdlib -- seeded from the same scalar. These tests pin
the three properties that fixes: a run gets its streams from its seed, streams
reached by different keys are independent of each other's draw order, and a
stochastic kernel with no stream says so instead of quietly making one.
"""

import ast
import pathlib

import pytest

from pyforestry.base.helpers import CircularPlot, Stand, Tree
from pyforestry.base.simulation.growth_model import ExampleStandGeneralModel
from pyforestry.simulation.services import KeyedRNG, RandomBundle

SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "pyforestry"


def _stand() -> Stand:
    return Stand(
        area_ha=1.0,
        plots=[
            CircularPlot(
                id=1,
                area_m2=10_000.0,
                trees=[Tree(species="Picea abies", diameter_cm=20.0)],
            )
        ],
    )


# ---------------------------------------------------------------------------
# The seam
# ---------------------------------------------------------------------------


def test_build_context_seeds_the_runs_streams():
    ctx = ExampleStandGeneralModel().build_context(_stand(), mode_hint="tree_list", seed=42)
    assert isinstance(ctx.rng, KeyedRNG)


def test_the_same_seed_gives_the_same_draws():
    model = ExampleStandGeneralModel()
    first = model.build_context(_stand(), mode_hint="tree_list", seed=42)
    second = model.build_context(_stand(), mode_hint="tree_list", seed=42)
    assert [first.rng.random() for _ in range(5)] == [second.rng.random() for _ in range(5)]


def test_different_seeds_give_different_draws():
    model = ExampleStandGeneralModel()
    first = model.build_context(_stand(), mode_hint="tree_list", seed=1)
    second = model.build_context(_stand(), mode_hint="tree_list", seed=2)
    assert [first.rng.random() for _ in range(5)] != [second.rng.random() for _ in range(5)]


def test_a_context_without_a_seed_says_so_instead_of_drawing():
    """Not an unseeded default: that makes a run irreproducible without reporting it."""
    ctx = ExampleStandGeneralModel().build_context(_stand(), mode_hint="tree_list")
    with pytest.raises(RuntimeError, match="no random bundle"):
        _ = ctx.rng


def test_seed_and_random_bundle_are_mutually_exclusive():
    with pytest.raises(ValueError, match="not both"):
        ExampleStandGeneralModel().build_context(
            _stand(), mode_hint="tree_list", seed=1, random_bundle=RandomBundle(2)
        )


# ---------------------------------------------------------------------------
# Keying: why two generators from one scalar was the real defect
# ---------------------------------------------------------------------------


def test_streams_reached_by_different_keys_are_independent_of_draw_order():
    """This is what two generators seeded from one scalar could not give.

    Drawing from one stream must not change what another produces, or the order
    in which two subsystems happen to run becomes part of every result -- and
    reordering two calls that touch different streams silently moves the numbers.
    """
    ordered = RandomBundle(7)
    mortality_first = [ordered.rng_for("mortality").random() for _ in range(3)]
    ingrowth_second = [ordered.rng_for("ingrowth").random() for _ in range(3)]

    reordered = RandomBundle(7)
    ingrowth_first = [reordered.rng_for("ingrowth").random() for _ in range(3)]
    mortality_second = [reordered.rng_for("mortality").random() for _ in range(3)]

    assert mortality_first == mortality_second
    assert ingrowth_second == ingrowth_first


def test_a_streams_numpy_and_scalar_generators_are_both_keyed():
    bundle = RandomBundle(11)
    a = bundle.rng_for("a")
    b = bundle.rng_for("b")
    assert a.numpy.random() != b.numpy.random()
    # Same key, same bundle -> the same stream object, so the same generator.
    assert bundle.rng_for("a").numpy is a.numpy


def test_child_paths_compose():
    bundle = RandomBundle(3)
    direct = bundle.rng_for("mortality", "picea abies")
    composed = bundle.rng_for("mortality").child("picea abies")
    assert direct is composed


# ---------------------------------------------------------------------------
# Checkpointing both generators
# ---------------------------------------------------------------------------


def test_snapshot_and_restore_round_trip_the_scalar_stream():
    bundle = RandomBundle(5)
    bundle.rng_for("x").random()
    state = bundle.snapshot()
    expected = [bundle.rng_for("x").random() for _ in range(3)]

    bundle.restore(state)
    assert [bundle.rng_for("x").random() for _ in range(3)] == expected


def test_snapshot_and_restore_round_trip_the_numpy_stream():
    bundle = RandomBundle(5)
    bundle.rng_for("x").numpy.random()
    state = bundle.snapshot()
    expected = [float(bundle.rng_for("x").numpy.random()) for _ in range(3)]

    bundle.restore(state)
    assert [float(bundle.rng_for("x").numpy.random()) for _ in range(3)] == expected


def test_a_stream_that_never_drew_a_vector_is_not_forced_to_build_one():
    bundle = RandomBundle(5)
    bundle.rng_for("x").random()
    assert "numpy" not in bundle.snapshot()[("x",)]


# ---------------------------------------------------------------------------
# Kernels no longer make their own
# ---------------------------------------------------------------------------


def test_stochastic_ingrowth_requires_a_stream():
    from pyforestry.sweden.ingrowth.wikberg_2004 import Wikberg2004Ingrowth

    with pytest.raises(ValueError, match="Stochastic ingrowth needs a random stream"):
        Wikberg2004Ingrowth._resolve_rng(None, deterministic=False)


def test_deterministic_ingrowth_needs_no_stream():
    from pyforestry.sweden.ingrowth.wikberg_2004 import Wikberg2004Ingrowth

    assert Wikberg2004Ingrowth._resolve_rng(None, deterministic=True) is None


def test_no_source_module_outside_the_service_constructs_a_generator():
    """The in-process mirror of AL005.

    A generator built where it is used cannot be seeded by the run and cannot be
    checkpointed. The RNG service is the one place that builds them.
    """
    exempt = {"simulation/services/keyed_rng.py", "simulation/services/rng_bundle.py"}
    offenders = []
    for path in SRC.rglob("*.py"):
        relative = path.relative_to(SRC).as_posix()
        if relative in exempt:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr in ("Random", "default_rng", "RandomState"):
                offenders.append(f"{relative}:{node.lineno}")
    assert not offenders, f"generators constructed outside the RNG service: {offenders}"
