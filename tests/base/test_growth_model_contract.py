"""Regression tests for the :class:`GrowthModel.build_context` contract.

Two defects are guarded here:

* every shipped adapter used to pass ``mode_hint`` to ``super().build_context``,
  so the base class's own ``mode_hint`` parameter raised ``TypeError`` for any
  caller that supplied it -- including the worked example in ``example_api.md``;
* ``inventory_origin`` was set by an inverted branch that labelled every
  non-angle-count stand as reconstructed from angle-count tallies.
"""

import warnings

import pytest

from pyforestry.base.helpers import AngleCount, CircularPlot, Stand, Tree, TreeSpecies
from pyforestry.base.simulation import GrowthModel, Requirements, SimulationContext

SPRUCE = TreeSpecies.Sweden.picea_abies


def _tree_stand() -> Stand:
    """A one-plot stand of measured trees, no angle-count tallies."""
    return Stand(
        plots=[
            CircularPlot(
                id=1,
                area_m2=400.0,
                trees=[Tree(species=SPRUCE, diameter_cm=d, weight_n=1.0) for d in (18.0, 24.0)],
            )
        ]
    )


def _angle_count_stand() -> Stand:
    """An angle-count stand whose tallies carry diameters, so stems/ha is derivable."""
    return Stand(
        plots=[
            CircularPlot(
                id=1,
                area_m2=400.0,
                AngleCount=[
                    AngleCount(
                        ba_factor=2.0,
                        value=[3.0],
                        species=[SPRUCE],
                        diameters_cm=[[18.0, 24.0, 30.0]],
                    )
                ],
            )
        ]
    )


def _angle_count_stand_without_diameters() -> Stand:
    """An angle-count stand that can report basal area but not stems/ha."""
    return Stand(
        plots=[
            CircularPlot(
                id=1,
                area_m2=400.0,
                AngleCount=[AngleCount(ba_factor=2.0, value=[3.0], species=[SPRUCE])],
            )
        ]
    )


class _AggregateModel(GrowthModel):
    """A model that declares a concrete aggregate inventory requirement."""

    def requirements(self) -> Requirements:
        """Aggregate metrics are all this model consumes."""
        return Requirements(inventory="aggregate")

    def update_step(self, ctx: SimulationContext, dt: float) -> None:
        """No-op; these tests only exercise context construction."""


class _TreeListModel(GrowthModel):
    """A model that genuinely needs individual stems."""

    def requirements(self) -> Requirements:
        """Per-tree records are required."""
        return Requirements(inventory="tree_list")

    def update_step(self, ctx: SimulationContext, dt: float) -> None:
        """No-op; these tests only exercise context construction."""


class _EitherModel(GrowthModel):
    """A model that can work from whichever representation is available."""

    def requirements(self) -> Requirements:
        """Either representation is acceptable."""
        return Requirements(inventory="either")

    def update_step(self, ctx: SimulationContext, dt: float) -> None:
        """No-op; these tests only exercise context construction."""


def test_mode_hint_is_accepted_not_a_type_error():
    """Passing the base class's own keyword must not raise (example_api.md:979)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ctx = _AggregateModel().build_context(_tree_stand(), mode_hint="aggregate")
    assert ctx.mode == "aggregate"


def test_requirements_win_over_a_conflicting_hint():
    """A concrete requirement is authoritative; a conflicting hint warns and loses."""
    with pytest.warns(UserWarning, match="requires inventory mode 'tree_list'"):
        ctx = _TreeListModel().build_context(_tree_stand(), mode_hint="aggregate")
    assert ctx.mode == "tree_list"


def test_hint_selects_the_mode_when_the_model_accepts_either():
    """``mode_hint`` is the caller's knob for an 'either' model."""
    ctx = _EitherModel().build_context(_tree_stand(), mode_hint="aggregate")
    assert ctx.mode == "aggregate"


def test_angle_count_does_not_silently_downgrade_a_tree_list_model():
    """An angle-count stand must not hand a tree-list model aggregate metrics unannounced."""
    ctx = _TreeListModel().build_context(_angle_count_stand())
    origin = ctx.attrs["inventory_origin"]
    if ctx.mode == "aggregate":
        # The tallies carried no diameters, so no adapter could produce stems.
        assert origin == "angle_count_aggregate"
    else:
        assert ctx.mode == "tree_list"
        assert origin.startswith("angle_count_")
        assert ctx.attrs["inventory_adapter"].startswith("angle_count_")


def test_measured_stand_is_not_labelled_as_angle_count_derived():
    """A stand of measured trees must not claim pseudo-tree provenance."""
    ctx = _EitherModel().build_context(_tree_stand())
    assert ctx.attrs["inventory_origin"] == "tree_list"
    assert "inventory_adapter" not in ctx.attrs


def test_aggregate_mode_on_a_measured_stand_reports_aggregate():
    """The aggregate representation of a measured stand is 'aggregate', not a pseudo list."""
    ctx = _AggregateModel().build_context(_tree_stand())
    assert ctx.attrs["inventory_origin"] == "aggregate"
    assert "inventory_adapter" not in ctx.attrs


def test_angle_count_aggregate_is_distinguishable_from_measured_aggregate():
    """Aggregates from tallies and from measured stems must be told apart."""
    ctx = _AggregateModel().build_context(_angle_count_stand())
    assert ctx.attrs["inventory_origin"] == "angle_count_aggregate"


def test_a_stand_that_cannot_supply_stems_says_so():
    """A tally without diameters yields no stems/ha, and must fail with an explanation.

    The aggregate metrics used to be read through ``dict.get(name, {...default...})``,
    whose default argument is evaluated eagerly -- so this case surfaced as a bare
    ``KeyError: 'Stems metric unavailable for angle-count data'`` raised from inside
    a dictionary lookup that had in fact succeeded.
    """
    stand = _angle_count_stand_without_diameters()
    assert _AggregateModel().can_build(stand)[0] is False
    with pytest.raises(ValueError, match="does not supply Stems"):
        _AggregateModel().build_context(stand)


def test_every_tree_gets_a_stable_identifier():
    """A tree record must be trackable without falling back to id().

    ``Tree.uid`` existed but was never populated, so the Elfving composite keyed
    its per-step bookkeeping on CPython object identity -- which is meaningless
    across a checkpoint, a serialisation round trip, or a separate process.
    """
    a, b = Tree(species=SPRUCE, diameter_cm=20.0), Tree(species=SPRUCE, diameter_cm=20.0)
    assert a.uid and b.uid
    assert a.uid != b.uid

    # A caller's own inventory keys win, and cannot collide with the automatic
    # ones, which are always "t" followed by a serial number.
    assert Tree(species=SPRUCE, uid="plot7-stem3").uid == "plot7-stem3"
    assert Tree(species=SPRUCE, uid=1).uid == 1
    assert str(a.uid).startswith("t")

    # A copy is the same tree in a later state, so it keeps its identity.
    import copy

    assert copy.deepcopy(a).uid == a.uid
