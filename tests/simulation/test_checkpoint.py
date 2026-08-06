"""A checkpoint resumes a run, rather than merely describing one.

The property worth testing is not that ``capture`` returns something with the
right fields, but that a pipeline restored from a checkpoint advances exactly as
the pipeline it was taken from would have -- same trees, same diameters, same
stochastic draws. Everything else here guards the ways that can silently fail:
a checkpoint that shares objects with the live run, a restore that rewinds the
generator to the start of the run, and a checkpoint restored into the wrong model.
"""

from __future__ import annotations

import pytest

from pyforestry.base.helpers.primitives import SiteBase
from pyforestry.simulation.services import Checkpoint, CheckpointSerializer
from pyforestry.sweden.simulation.presets import (
    Elfving2010PipelineConfig,
    Soderberg1986PipelineConfig,
    build_elfving_2010_pipeline,
    build_soderberg_1986_pipeline,
)
from pyforestry.sweden.site import Sweden, SwedishSite


class _SiteDemo(SwedishSite):
    """Concrete site wrapper (implements the abstract SiteBase hook)."""

    def compute_attributes(self) -> None:
        """Populate the derived Swedish site attributes."""
        SwedishSite.__post_init__(self)

    def __post_init__(self) -> None:
        """Defer the Swedish derivation to :meth:`compute_attributes`."""
        SiteBase.__post_init__(self)


def _make_site() -> _SiteDemo:
    return _SiteDemo(
        latitude=60.5,
        longitude=15.0,
        altitude=150.0,
        field_layer=Sweden.FieldLayer.BILBERRY,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        soil_texture=Sweden.SoilTextureTill.SANDY,
        ditched=False,
    )


def _make_pipeline(**overrides: object):
    return build_elfving_2010_pipeline(
        Elfving2010PipelineConfig(
            sample_trees=24,
            random_seed=2026,
            deterministic=False,
            dt_years=5.0,
            **overrides,
        )
    )


def _stand_fingerprint(trees) -> list[tuple[str, float, float]]:
    """Reduce a tree list to the values a period is supposed to move."""
    return [
        (str(t.species), round(float(t.diameter_cm or 0.0), 9), round(float(t.height_m or 0.0), 9))
        for t in trees
    ]


def _advance(pipeline, periods: int) -> list[tuple[str, float, float]]:
    """Step ``periods`` times and fingerprint the resulting stand."""
    for _ in range(periods):
        pipeline.step()
    return _stand_fingerprint(pipeline._trees)


def test_restored_pipeline_advances_identically_to_the_one_captured_from() -> None:
    """The whole point: resume where a run left off and get its future.

    Both pipelines are stochastic (``deterministic=False``), so agreeing over
    three further periods means the generator state came across too -- a restore
    that re-seeded from ``config.random_seed`` would diverge on the first draw.
    """
    reference = _make_pipeline()
    reference.initialize(site=_make_site())
    reference.step()
    reference.step()

    checkpoint = CheckpointSerializer().capture(reference)

    resumed = _make_pipeline()
    CheckpointSerializer().restore(resumed, checkpoint)

    assert _advance(resumed, 3) == _advance(reference, 3)


def test_a_checkpoint_is_detached_from_the_run_it_came_from() -> None:
    """Advancing the live run must not edit the checkpoint underneath it."""
    pipeline = _make_pipeline()
    pipeline.initialize(site=_make_site())
    pipeline.step()

    checkpoint = CheckpointSerializer().capture(pipeline)
    captured_age = checkpoint.state["_current_age_years"]
    captured_trees = len(checkpoint.state["_ctx"].stand.plots[0].trees)

    for _ in range(3):
        pipeline.step()

    assert checkpoint.state["_current_age_years"] == captured_age
    assert len(checkpoint.state["_ctx"].stand.plots[0].trees) == captured_trees
    assert pipeline._current_age_years > captured_age


def test_one_checkpoint_can_seed_two_independent_runs() -> None:
    """A branching scenario restores the same checkpoint twice; the runs must not share trees."""
    origin = _make_pipeline()
    origin.initialize(site=_make_site())
    origin.step()
    checkpoint = CheckpointSerializer().capture(origin)

    left = _make_pipeline()
    right = _make_pipeline()
    CheckpointSerializer().restore(left, checkpoint)
    CheckpointSerializer().restore(right, checkpoint)

    left.step()

    assert left._trees is not right._trees
    assert _stand_fingerprint(left._trees) != _stand_fingerprint(right._trees)


def test_capture_leaves_the_phases_out_of_the_snapshot() -> None:
    """``_steps`` holds a back-reference to the pipeline and must not be copied.

    A blanket snapshot of ``__dict__`` would drag the model, the mortality engine
    and every phase into the checkpoint, and restore a pipeline whose phases
    advance its predecessor.
    """
    pipeline = _make_pipeline()
    pipeline.initialize(site=_make_site())

    state = pipeline.checkpoint_state()

    assert "_steps" not in state
    assert "_model" not in state
    assert "_mortality_engine" not in state
    assert "_rng_state" in state


def test_restore_rebuilds_the_mortality_engine_on_the_restored_generator() -> None:
    """The engine is built from the run's generator, so it cannot be carried across."""
    pipeline = _make_pipeline()
    pipeline.initialize(site=_make_site())
    checkpoint = CheckpointSerializer().capture(pipeline)
    before = pipeline._mortality_engine

    CheckpointSerializer().restore(pipeline, checkpoint)

    assert pipeline._mortality_engine is not before


def test_restore_refuses_a_checkpoint_from_a_different_model() -> None:
    """Two pipelines expose the same state names, so this would otherwise succeed."""
    elfving = _make_pipeline()
    elfving.initialize(site=_make_site())
    checkpoint = CheckpointSerializer().capture(elfving)

    soderberg = build_soderberg_1986_pipeline(
        Soderberg1986PipelineConfig(sample_trees=24, random_seed=2026, dt_years=5.0)
    )

    with pytest.raises(ValueError, match="cannot be restored into"):
        CheckpointSerializer().restore(soderberg, checkpoint)


def test_a_non_checkpointable_subject_is_refused_by_name() -> None:
    """Both halves of the protocol are required, and the error says which is missing."""
    serializer = CheckpointSerializer()

    with pytest.raises(TypeError, match="checkpoint_state, restore_checkpoint_state missing"):
        serializer.capture(object())

    with pytest.raises(TypeError, match="does not implement Checkpointable"):
        serializer.restore(object(), Checkpoint(component_id="x", state={}))


def test_restoring_a_mapping_that_did_not_come_from_capture_is_an_error() -> None:
    """A mapping without the generator state is not a checkpoint of this pipeline."""
    pipeline = _make_pipeline()
    pipeline.initialize(site=_make_site())

    with pytest.raises(KeyError):
        pipeline.restore_checkpoint_state({"_current_age_years": 40.0})
