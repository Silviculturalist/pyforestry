from __future__ import annotations

import pytest

from pyforestry.simulation.services import RandomBundle
from pyforestry.simulation.stand_composite import (
    DispatchRecord,
    DispatchResult,
    StandAction,
    StandComposite,
    StandPart,
)


class DummyModel:
    def __init__(self, **attrs):
        self.__dict__.update(attrs)

    def total(self, name):
        raise KeyError(name)


def test_stand_action_analysis_and_execution():
    part = StandPart(name="p1", model_view=DummyModel(), context={})

    def handler_kwargs(part, *, rng, io=None):  # noqa: ARG001 - test hook
        return (rng, io)

    action = StandAction(name="kw", handler=handler_kwargs, target_parts="p1")
    rng = RandomBundle(123).rng_for("a")
    result = action.execute(part, rng)
    assert result[0] is rng
    assert action.requests_rng is True
    assert action.requests_io is True
    assert action.iter_targets() == ("p1",)

    def handler_positional(part, rng):  # noqa: ARG001 - test hook
        return rng

    action_pos = StandAction(name="pos", handler=handler_positional, target_parts=("p1", "p2"))
    result = action_pos.execute(part, rng)
    assert result is rng
    assert action_pos.iter_targets() == ("p1", "p2")

    def handler_generic(part, x=7):  # noqa: ARG001 - test hook
        return x

    # A parameter that is not called "rng" is not an RNG slot. This used to receive
    # the KeyedRNG object simply for being the second positional parameter, which
    # silently replaced whatever the handler actually wanted there.
    action_generic = StandAction(name="generic", handler=handler_generic)
    assert action_generic.requests_rng is False
    assert action_generic.execute(part, rng) == 7

    action_plain = StandAction(name="plain", handler=lambda p: p.name, target_parts=None)
    assert action_plain.execute(part, None) == "p1"
    assert action_plain.iter_targets() == ()

    def handler_varargs(part, *args, **kwargs):  # noqa: ARG001 - test hook
        return args, kwargs

    # A **kwargs catch-all can absorb rng=/io= by name, so injection is safe there.
    action_var = StandAction(name="var", handler=handler_varargs)
    result = action_var.execute(part, rng)
    assert result[0] == ()  # never passed positionally
    assert result[1]["rng"] is rng
    assert action_var.requests_rng is True
    assert action_var.requests_io is True

    def handler_starargs(part, *args):  # noqa: ARG001 - test hook
        return args

    # A bare *args is not a declaration: it cannot name what it receives, so
    # injecting into it is the same positional guess that broke handler_generic.
    action_star = StandAction(name="star", handler=handler_starargs)
    assert action_star.requests_rng is False
    assert action_star.execute(part, rng) == ()


def test_dispatch_result_grouping():
    result = DispatchResult(
        records=[
            DispatchRecord(part="a", action="cut", cost=1.0, harvest=2.0, result=None),
            DispatchRecord(part="b", action="cut", cost=2.0, harvest=3.0, result=None),
            DispatchRecord(part="a", action="thin", cost=0.5, harvest=1.0, result=None),
        ]
    )
    grouped = result.by_part()
    assert set(grouped) == {"a", "b"}
    assert len(grouped["a"]) == 2
    assert result.spent == pytest.approx(3.5)
    assert result.harvested == pytest.approx(6.0)


def test_stand_part_metric_resolution_and_validation():
    with pytest.raises(ValueError):
        StandPart(name="", model_view=DummyModel(), context={})
    with pytest.raises(TypeError):
        StandPart(name="x", model_view=DummyModel(), context=[])  # type: ignore[arg-type]

    view = DummyModel(basal_area=lambda: 12.0, Stems=[1, 2])
    part = StandPart(name="p1", model_view=view, context={"stems": 7})
    assert part.basal_area == pytest.approx(12.0)
    assert part.stems == pytest.approx(7.0)

    view_with_total = DummyModel(basal_area=[1, 2], BasalArea=[1, 2])

    def total_value(name):  # noqa: ARG001 - test helper
        return 9.0

    view_with_total.total = total_value
    part_total = StandPart(name="p2", model_view=view_with_total, context={})
    assert part_total.basal_area == pytest.approx(9.0)


def test_stand_part_apply_action_effect_checks():
    part = StandPart(name="p1", model_view=DummyModel(), context={})

    def handler_rng(part, rng):  # noqa: ARG001 - test hook
        return rng

    action = StandAction(name="needs_rng", handler=handler_rng)
    with pytest.raises(RuntimeError, match="requires RNG"):
        part.apply_action(action, effects=frozenset({"io"}))

    def handler_io(part, io=None):  # noqa: ARG001 - test hook
        return io

    action_io = StandAction(name="needs_io", handler=handler_io)
    with pytest.raises(RuntimeError, match="requests I/O"):
        part.apply_action(action_io, effects=frozenset({"rng"}))


def test_stand_composite_dispatch_policies_and_constraints():
    part = StandPart(name="p1", model_view=DummyModel(basal_area=10.0), context={})
    composite = StandComposite(parts=(part,), budget=1.0, harvest_cap=2.0)

    action = StandAction(name="a", handler=lambda p: None, cost=2.0, harvest=0.0)
    with pytest.raises(RuntimeError, match="shared budget"):
        composite.dispatch([action], policy="broadcast")

    action_harvest = StandAction(name="b", handler=lambda p: None, cost=0.5, harvest=3.0)
    with pytest.raises(RuntimeError, match="harvest cap"):
        composite.dispatch([action_harvest], policy="broadcast")

    empty = StandComposite()
    assert empty.dispatch([action], policy="largest_first").records == []

    with pytest.raises(ValueError, match="Targeted dispatch"):
        composite.dispatch([StandAction(name="c", handler=lambda p: None)], policy="target")

    with pytest.raises(ValueError, match="Unknown dispatch policy"):
        composite.dispatch([action], policy="unknown")

    def none_selector(action, parts):  # noqa: ARG001 - test helper
        return ()

    assert composite.dispatch([action], policy=none_selector).records == []


def test_stand_composite_duplicate_part_rejected():
    part = StandPart(name="p1", model_view=DummyModel(), context={})
    composite = StandComposite(parts=(part,))
    with pytest.raises(ValueError, match="Duplicate stand part"):
        composite.add_part(part)
