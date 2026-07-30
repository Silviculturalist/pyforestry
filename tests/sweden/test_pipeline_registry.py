"""The two lookups Sweden's preset package offers, and what they refuse.

``get_pipeline`` and ``get_scenario_config`` reach two unrelated kinds of thing --
a stateful simulator and a frozen declaration -- which is why there is no single
"get a preset". Both were reachable only through their happy path; the names they
reject, and the rename they explain, had never been exercised.
"""

from __future__ import annotations

import pytest

from pyforestry.sweden.simulation.presets import (
    PIPELINE_BUILDERS,
    CompositePipeline,
    Elfving2010PipelineConfig,
    available_pipelines,
    get_pipeline,
    get_scenario_config,
)


def test_every_advertised_pipeline_can_be_built() -> None:
    """The registry's keys are the names that work, with nothing left over."""
    assert available_pipelines() == sorted(PIPELINE_BUILDERS)
    assert available_pipelines() == ["elfving_2010_composite", "soderberg_1986_composite"]

    for name in available_pipelines():
        assert isinstance(get_pipeline(name), CompositePipeline)


def test_a_pipeline_can_be_built_with_its_own_config() -> None:
    """The config reaches the pipeline rather than being taken and dropped."""
    pipeline = get_pipeline("elfving_2010_composite", Elfving2010PipelineConfig(sample_trees=17))

    assert pipeline.config.sample_trees == 17


def test_the_old_pipeline_names_explain_what_they_became() -> None:
    """``elfving_2010`` names a growth model now, and a pipeline no longer.

    One string used to mean two different things through two entry points:
    ``project(model="elfving_2010")`` steps trees with Elfving (2010) alone, while
    ``get_pipeline("elfving_2010")`` reconstructed a stand and ran nine more models
    around it. The rename is only useful if the error says so.
    """
    for old, new in (
        ("elfving_2010", "elfving_2010_composite"),
        ("soderberg_1986", "soderberg_1986_composite"),
    ):
        with pytest.raises(ValueError, match=new) as raised:
            get_pipeline(old)
        assert "single-tree" in str(raised.value)


def test_an_unknown_pipeline_lists_the_known_ones() -> None:
    """A name that was never a pipeline gets no rename hint, only the list."""
    with pytest.raises(ValueError, match="Unknown pipeline") as raised:
        get_pipeline("eko1985_composite")

    message = str(raised.value)
    assert "elfving_2010_composite" in message
    assert "Did you mean" not in message


def test_the_scenario_lookup_answers_only_for_what_it_defines() -> None:
    assert get_scenario_config("baseline").scenario_id == "baseline"
    with pytest.raises(ValueError, match="Unsupported scenario_id"):
        get_scenario_config("baseline_v2")
