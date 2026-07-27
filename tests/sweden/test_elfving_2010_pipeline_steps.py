"""The composite pipeline's period is an ordered tuple of steps.

``Elfving2010Pipeline.step()`` used to hand-code eight phases in one method, so the
only way to test a phase in place was to run the whole period and infer. These check
the decomposition itself: that the order is the order the model needs, that each
phase does its own job and nothing else, that the record they write is per-period,
and that the tuple is a real
:class:`~pyforestry.base.simulation.pipeline.Step` sequence -- the generic runtime
can drive it and gets the same answer.
"""

from __future__ import annotations

import pytest

from pyforestry.base.helpers.primitives import SiteBase
from pyforestry.base.simulation.pipeline import run_pipeline
from pyforestry.sweden.adapters.elfving_2010 import Elfving2010Model
from pyforestry.sweden.simulation.presets import (
    Elfving2010Pipeline,
    Elfving2010PipelineConfig,
    Soderberg1986Pipeline,
    Soderberg1986PipelineConfig,
    build_elfving_2010_pipeline,
    build_soderberg_1986_pipeline,
)
from pyforestry.sweden.simulation.presets._composite import (
    CompositePipeline,
    CompositePipelineConfig,
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
            deterministic=True,
            dt_years=5.0,
            **overrides,
        )
    )


def test_period_is_an_ordered_tuple_of_named_phases() -> None:
    """The schedule is readable as data, and it is the order the model needs.

    Pinned rather than merely counted, because the order is scientific: mortality is
    predicted before growth so the Elfving stand calibration targets survived rather
    than gross basal area, the blend runs immediately after growth while both
    diameter trajectories still exist, and height/bark runs last because it is a
    function of the end-of-period stand.
    """
    pipeline = _make_pipeline()
    assert tuple(step.name for step in pipeline.steps) == (
        "begin_period",
        "young_stand_growth",
        "mortality_prediction",
        "sync_model_context",
        "mature_growth",
        "phase_over_blend",
        "mortality_realization",
        "age_advance",
        "ingrowth",
        "height_and_bark",
        "sync_model_context",
    )


def test_the_soderberg_pipeline_runs_the_same_phases() -> None:
    """The decomposition is an abstraction, not one model's method list.

    Söderberg 1986 swaps the mature growth model and everything a model that reads
    ``ctx.attrs`` instead of a typed ``Inputs`` needs -- and inherits the period
    whole. If the phases had to be restated to swap a model, they would be a
    private schedule with a protocol's name on it.
    """
    elfving = _make_pipeline()
    soderberg = build_soderberg_1986_pipeline(
        Soderberg1986PipelineConfig(sample_trees=24, random_seed=2026, deterministic=True)
    )

    assert [step.name for step in soderberg.steps] == [step.name for step in elfving.steps]
    assert [type(step) for step in soderberg.steps] == [type(step) for step in elfving.steps]
    # Each step is bound to its own pipeline, or Söderberg would step Elfving's stand.
    assert all(step.pipeline is soderberg for step in soderberg.steps)


def test_the_soderberg_pipeline_swaps_only_what_the_model_swap_needs() -> None:
    """Every override earns its place, and adding one is a decision, not a habit.

    Söderberg's override of ``_rebuild_context`` used to restate the whole
    plot/stand/context construction to change one dict. Pinning the list is what
    makes the next copy of a parent method visible in review rather than in a
    diff nobody reads.
    """
    reasons = {
        "__init__": "passes its own config type",
        "_build_model": "builds Soderberg1986Model; the hook exists for exactly this",
        "component_id": "its own identifier",
        "source": "its own citation",
        "components": "adds its growth model to the composite's",
        "_model_attrs": "Soderberg1986Model declares no typed Inputs, so it reads attrs",
        "_site_index_species_for_soderberg": "picks the pine or spruce curve by mixture",
        "value_standing_forest": "optional Soderberg form-height volume route",
        "_form_height_volume_under_bark_m3": (
            "form height is over bark and the price lists are not; the conversion "
            "is specific to this route"
        ),
    }
    overridden = {
        name
        for name in vars(Soderberg1986Pipeline)
        if not name.startswith("__") or name == "__init__"
    }
    assert overridden == set(reasons), (
        "Söderberg's overrides changed. Each one is a divergence from the shared "
        "composite workflow -- add it to `reasons` with why it cannot be inherited."
    )


def test_neither_pipeline_is_the_other_s_base_class() -> None:
    """Two published models, two siblings, one shared workflow.

    ``Soderberg1986Pipeline`` used to subclass ``Elfving2010Pipeline``: one
    model's runner was the base class of another's. It constructed an
    ``Elfving2010Model`` that it then discarded, reached across a module boundary
    for two underscore-prefixed names, and its config inherited Elfving-only
    fields.
    """
    assert not issubclass(Soderberg1986Pipeline, Elfving2010Pipeline)
    assert not issubclass(Elfving2010Pipeline, Soderberg1986Pipeline)
    assert issubclass(Soderberg1986Pipeline, CompositePipeline)
    assert issubclass(Elfving2010Pipeline, CompositePipeline)

    assert not issubclass(Soderberg1986PipelineConfig, Elfving2010PipelineConfig)
    assert issubclass(Soderberg1986PipelineConfig, CompositePipelineConfig)
    assert issubclass(Elfving2010PipelineConfig, CompositePipelineConfig)


def test_the_composite_base_refuses_to_run_without_a_model() -> None:
    """A pipeline is defined by the mature model it drives; there is no default.

    ``source`` used to default to Elfving (2010) for whatever subclassed it,
    which is a citation that reads as real wherever provenance is reported.
    """
    with pytest.raises(NotImplementedError, match="_build_model"):
        CompositePipeline()


def test_mortality_is_predicted_before_growth_and_realised_after() -> None:
    """The one ordering the pipeline's own comment always called out.

    Growth must see the mortality fractions on the trees (the stand calibration
    multiplies by ``1 - tree.mortality``) and must run before any stem is removed.
    """
    pipeline = _make_pipeline()
    pipeline.initialize(site=_make_site())
    for tree in pipeline.tree_list:
        tree.diameter_cm = max(12.0, float(tree.diameter_cm or 0.0))

    seen: list[tuple[str, float, float]] = []
    original = Elfving2010Model.update_step

    def _record_state(self, ctx, dt):  # noqa: ANN001, ANN202
        seen.append(
            (
                "growth",
                sum(float(t.mortality or 0.0) for t in pipeline.tree_list),
                sum(float(t.weight_n or 0.0) for t in pipeline.tree_list),
            )
        )
        return original(self, ctx, dt)

    stems_before = sum(float(tree.weight_n or 0.0) for tree in pipeline.tree_list)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(Elfving2010Model, "update_step", _record_state)
        pipeline.step(dt_years=5.0)

    (_label, mortality_at_growth, stems_at_growth) = seen[0]
    assert mortality_at_growth > 0.0, "growth ran before mortality was predicted"
    assert stems_at_growth == pytest.approx(stems_before), "stems were removed before growth"
    assert sum(float(t.weight_n or 0.0) for t in pipeline.tree_list) < stems_before


def test_phase_over_blend_uses_the_young_diameter_growth_overwrote() -> None:
    """The blend interpolates the pre-growth young DBH, which only the record holds."""
    pipeline = _make_pipeline()
    pipeline.initialize(site=_make_site())
    for tree in pipeline.tree_list:
        tree.diameter_cm = 6.0

    steps = {step.name: step for step in pipeline.steps}
    ctx = pipeline._ctx
    steps["begin_period"].run(ctx, 5.0)
    steps["young_stand_growth"].run(ctx, 5.0)

    record = pipeline._record
    assert record.young_uids, "no trees classed as young in a 6 cm stand"
    assert set(record.young_dbh_after_nystrom) == set(record.young_uids)

    # Stand in for the mature step with a diameter the blend cannot mistake.
    for tree in pipeline.tree_list:
        tree.diameter_cm = 100.0
    record.phase_over_weight = 0.25
    steps["phase_over_blend"].run(ctx, 5.0)

    for tree in pipeline.tree_list:
        expected = 0.75 * record.young_dbh_after_nystrom[tree.uid] + 0.25 * 100.0
        assert float(tree.diameter_cm) == pytest.approx(expected)


def test_the_record_is_this_period_s_and_not_the_last_one_that_had_young_trees() -> None:
    """``begin_period`` is why a phase that does nothing reports zero, not last time."""
    pipeline = _make_pipeline()
    pipeline.initialize(site=_make_site())
    for tree in pipeline.tree_list:
        tree.diameter_cm = 4.0
    pipeline.step(dt_years=5.0)
    assert pipeline._record.damage_mortality_stems_per_ha > 0.0

    # Push the stand past the handover so the young phase has nothing to do.
    for tree in pipeline.tree_list:
        tree.diameter_cm = 30.0
        tree.height_m = 22.0
    pipeline.step(dt_years=5.0)

    assert pipeline._young_tree_ids(pipeline.tree_list) == set()
    assert pipeline._record.damage_mortality_stems_per_ha == 0.0
    assert pipeline._record.damage_index_mean == 0.0


def test_run_pipeline_drives_the_same_steps_to_the_same_numbers() -> None:
    """The tuple is a real ``Step`` sequence, not a look-alike.

    Two periods through the generic runtime and two through :meth:`step` have to
    land on the same stand, or the composite would be running a private schedule
    that merely resembles the package's one.
    """
    site = _make_site()
    by_step = _make_pipeline()
    by_step.initialize(site=site)
    by_step.step(dt_years=5.0)
    by_step.step(dt_years=5.0)

    by_runtime = _make_pipeline()
    by_runtime.initialize(site=site)
    run_pipeline(by_runtime._ctx, by_runtime.steps, years=10.0, step=5.0)

    assert by_runtime.years_elapsed == pytest.approx(by_step.years_elapsed)
    assert by_runtime.current_age_years == pytest.approx(by_step.current_age_years)
    assert len(by_runtime.tree_list) == len(by_step.tree_list)
    for left, right in zip(by_runtime.tree_list, by_step.tree_list, strict=True):
        assert float(left.diameter_cm or 0.0) == pytest.approx(float(right.diameter_cm or 0.0))
        assert float(left.height_m or 0.0) == pytest.approx(float(right.height_m or 0.0))
        assert float(left.weight_n or 0.0) == pytest.approx(float(right.weight_n or 0.0))


def test_the_context_survives_the_period_it_used_to_be_rebuilt_in() -> None:
    """One context per run, so its history -- its reason to exist -- accumulates.

    The pipeline used to build a ``CircularPlot``, a ``Stand`` and a
    ``SimulationContext`` three times per period and discard each.
    """
    pipeline = _make_pipeline()
    pipeline.initialize(site=_make_site())
    ctx = pipeline._ctx
    assert ctx.history == []

    pipeline.step(dt_years=5.0)
    pipeline.step(dt_years=5.0)

    assert pipeline._ctx is ctx, "the context was replaced mid-run"
    assert [entry.op for entry in ctx.history] == ["update_step", "update_step"]
    assert [entry.t for entry in ctx.history] == pytest.approx([5.0, 10.0])


def test_the_context_and_the_pipeline_hold_one_tree_list() -> None:
    """Adding or removing a tree cannot leave the two describing different stands."""
    pipeline = _make_pipeline(apply_ingrowth=True, ingrowth_min_mean_age_years=20.0)
    pipeline.initialize(site=_make_site())
    assert pipeline.tree_list is pipeline._ctx.stand.plots[0].trees

    pipeline.step(dt_years=5.0)
    assert pipeline.tree_list is pipeline._ctx.stand.plots[0].trees

    # The documented way to thin: assign a shorter list. It has to write through.
    kept = list(pipeline.tree_list[:3])
    pipeline._trees = kept
    assert pipeline._ctx.stand.plots[0].trees == kept
    assert pipeline.tree_list is pipeline._ctx.stand.plots[0].trees
