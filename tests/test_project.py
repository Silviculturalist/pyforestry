"""``pf.project`` -- one projection, one call.

Running a projection used to require seven concepts, one of which raised
``TypeError`` when used the way the repository's own worked example used it.
"""

from __future__ import annotations

import pytest

import pyforestry as pf
from pyforestry.base.helpers.primitives import Age, AgeMeasurement
from pyforestry.base.simulation import Action, GrowthStep, ManagementStep, when
from pyforestry.sweden.site import Sweden, SwedishSite

SITE_INDEX = {"site_index_m": 24.0}


class _Site(SwedishSite):
    def compute_attributes(self) -> None:
        SwedishSite.__post_init__(self)


def _site() -> _Site:
    return _Site(
        latitude=60.5,
        longitude=15.0,
        altitude=150.0,
        field_layer=Sweden.FieldLayer.BILBERRY,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        soil_texture=Sweden.SoilTextureTill.SANDY,
        ditched=False,
    )


def _stand() -> pf.Stand:
    return pf.Stand(
        area_ha=1.0,
        site=_site(),
        plots=[
            pf.CircularPlot(
                id=1,
                area_m2=10_000.0,
                trees=[
                    pf.Tree(
                        species="Picea abies", diameter_cm=18.0, height_m=14.0, weight_n=400.0
                    ),
                    pf.Tree(
                        species="Pinus sylvestris", diameter_cm=22.0, height_m=17.0, weight_n=300.0
                    ),
                ],
            )
        ],
    )


# ---------------------------------------------------------------------------
# The call
# ---------------------------------------------------------------------------


def test_project_runs_a_named_model_and_returns_a_table():
    result = pf.project(_stand(), model="elfving_2010", years=20, step=5, attrs=SITE_INDEX)
    assert len(result.table) == 4
    assert result.context.state["t"] == pytest.approx(20.0)
    assert float(result.table.iloc[-1]["ba_total"]) > float(result.table.iloc[0]["ba_total"])


def test_project_accepts_a_model_instance():
    from pyforestry.sweden.adapters.elfving_2010 import Elfving2010Model

    result = pf.project(_stand(), model=Elfving2010Model(), years=5, attrs=SITE_INDEX)
    assert result.model.component_id == "elfving_2010"


def test_the_step_defaults_to_the_models_native_period():
    """A caller should not have to know that Elfving was fitted for five years."""
    result = pf.project(_stand(), model="elfving_2010", years=10, attrs=SITE_INDEX)
    assert result.context.state["last_dt"] == pytest.approx(5.0)
    assert len(result.table) == 2


def test_project_reports_the_final_stand_and_its_provenance():
    result = pf.project(_stand(), model="elfving_2010", years=5, attrs=SITE_INDEX)
    assert result.stand is result.context.stand
    assert float(result.stand.BasalArea) > 0.0
    assert result.provenance["elfving_2010"].author.startswith("Elfving")
    assert result.provenance["elfving_2010"].year == 2010


# ---------------------------------------------------------------------------
# The caller's stand
# ---------------------------------------------------------------------------


def test_projecting_does_not_change_the_stand_it_was_given():
    """``build_context`` shares Tree objects so a model can grow them in place.

    That is right for a model and wrong for a front door: without a copy here,
    ``project(stand, ...)`` returns something different the second time it is
    called on the same stand.
    """
    stand = _stand()
    before = float(stand.BasalArea)
    pf.project(stand, model="elfving_2010", years=20, step=5, attrs=SITE_INDEX)
    stand._metric_estimates.clear()
    assert float(stand.BasalArea) == pytest.approx(before)


def test_the_same_stand_projects_identically_twice():
    stand = _stand()
    first = pf.project(stand, model="elfving_2010", years=20, step=5, attrs=SITE_INDEX)
    second = pf.project(stand, model="elfving_2010", years=20, step=5, attrs=SITE_INDEX)
    assert float(first.stand.BasalArea) == pytest.approx(float(second.stand.BasalArea))


def test_a_stand_whose_trees_carry_ages_can_be_projected():
    """The copy has to survive the measurement types the models actually want.

    Every stand above holds bare floats, so the deep copy never met an
    ``AgeMeasurement`` -- and ``AgeMeasurement`` could not be deep-copied, which
    made ``project`` raise ``TypeError`` on precisely the stand the Elfving and
    Söderberg models read a tree age from.
    """
    stand = _stand()
    for tree in stand.plots[0].trees:
        tree.age = Age.DBH(45)
    ages_before = [float(tree.age) for tree in stand.plots[0].trees]

    result = pf.project(stand, model="elfving_2010", years=10, step=5, attrs=SITE_INDEX)

    assert len(result.table) == 2
    assert [float(tree.age) for tree in stand.plots[0].trees] == ages_before
    projected = result.stand.plots[0].trees
    assert all(isinstance(tree.age, AgeMeasurement) for tree in projected)
    assert all(tree.age.code == Age.DBH.value for tree in projected)


# ---------------------------------------------------------------------------
# Management and pipelines
# ---------------------------------------------------------------------------


def test_a_policy_runs_before_growth_in_each_period():
    seen: list[float] = []
    policy = when(
        lambda ctx: True,
        Action(name="observe", apply=lambda ctx: seen.append(float(ctx.state.get("t", 0.0)))),
    )
    pf.project(_stand(), model="elfving_2010", years=15, step=5, policy=policy, attrs=SITE_INDEX)
    assert seen == [0.0, 5.0, 10.0]


def test_an_explicit_pipeline_overrides_the_default():
    order: list[str] = []

    class _Recording:
        name = "recording"

        def run(self, ctx, dt):
            order.append("recorded")

    pf.project(
        _stand(),
        model="elfving_2010",
        years=5,
        step=5,
        pipeline=(_Recording(), GrowthStep()),
        attrs=SITE_INDEX,
    )
    assert order == ["recorded"]


def test_a_management_step_can_be_placed_after_growth():
    seen: list[float] = []
    policy = when(
        lambda ctx: True,
        Action(name="observe", apply=lambda ctx: seen.append(float(ctx.state.get("t", 0.0)))),
    )
    pf.project(
        _stand(),
        model="elfving_2010",
        years=10,
        step=5,
        pipeline=(GrowthStep(), ManagementStep(policy)),
        attrs=SITE_INDEX,
    )
    assert seen == [5.0, 10.0]


# ---------------------------------------------------------------------------
# Discovery, and errors that say what to do
# ---------------------------------------------------------------------------


def test_available_models_lists_both_spellings_of_a_catalog_id():
    names = pf.available_models()
    assert "elfving_2010" in names
    assert "elfving_2010_model" in names


def test_every_available_name_resolves_or_explains_why_not():
    from pyforestry.projection import _resolve_model

    for name in pf.available_models():
        try:
            _resolve_model(name)
        except ValueError as exc:
            assert "cannot be built from a name alone" in str(exc), name


def test_an_unknown_model_lists_the_known_ones():
    with pytest.raises(ValueError, match="Unknown model 'not_a_model'"):
        pf.project(_stand(), model="not_a_model", years=5)


def test_a_stand_that_cannot_run_the_model_says_what_is_missing():
    with pytest.raises(ValueError, match="it needs site"):
        pf.project(pf.Stand(area_ha=1.0, plots=[]), model="elfving_2010", years=5)


def test_a_missing_input_fails_before_any_time_is_simulated():
    with pytest.raises(ValueError, match="cannot resolve its inputs"):
        pf.project(_stand(), model="elfving_2010", years=5)


# ---------------------------------------------------------------------------
# The front door itself
# ---------------------------------------------------------------------------


def test_the_front_door_names_are_reachable_from_the_top_level():
    for name in (
        "project",
        "ProjectionResult",
        "available_models",
        "Stand",
        "Tree",
        "CircularPlot",
    ):
        assert hasattr(pf, name), name
        assert name in dir(pf), name


def test_an_unknown_top_level_name_still_raises():
    with pytest.raises(AttributeError, match="has no attribute"):
        _ = pf.not_a_thing
