"""Typed model inputs: resolved once, at build time, or named as missing there.

``ctx.attrs`` was the real input contract for every model and it was an untyped
dict read with ``.get(key, default)`` at the point of use. That has three failure
modes and these tests pin the fix for each: a required input that is absent
surfaces as a default instead of an error; a mistyped key is indistinguishable
from an absent one; and when it *does* raise, it raises from inside a growth
kernel, twenty frames from the mistake.
"""

import dataclasses

import pytest

from pyforestry.base.helpers import CircularPlot, Stand, Tree
from pyforestry.base.helpers.primitives import SiteBase
from pyforestry.base.simulation.growth_model import ExampleStandGeneralModel
from pyforestry.sweden.adapters.elfving_2010 import Elfving2010Inputs, Elfving2010Model


class _PlainSite(SiteBase):
    """A site that is not a ``SwedishSite``, so every input comes from ``attrs``."""

    def compute_attributes(self) -> None:  # pragma: no cover - stub
        return None


def _stand() -> Stand:
    return Stand(
        site=_PlainSite(latitude=64.0, longitude=19.0),
        plots=[
            CircularPlot(
                id=1,
                area_m2=10_000.0,
                trees=[Tree(species="Picea abies", diameter_cm=20.0, height_m=15.0)],
            )
        ],
    )


REQUIRED_ATTRS = {
    "site_index_m": 22.0,
    "temperature_sum_dd": 1100.0,
    "latitude_deg": 64.0,
    "altitude_m": 200.0,
}


def test_inputs_are_resolved_during_build_context():
    ctx = Elfving2010Model().build_context(_stand(), mode_hint="tree_list", attrs=REQUIRED_ATTRS)
    assert isinstance(ctx.inputs, Elfving2010Inputs)
    assert ctx.inputs.site_index_m == pytest.approx(22.0)
    assert ctx.inputs.temperature_sum_dd == pytest.approx(1100.0)


def test_a_missing_required_input_fails_at_build_and_names_the_model():
    """Not twenty frames into a step, and not as a silently substituted default."""
    incomplete = {k: v for k, v in REQUIRED_ATTRS.items() if k != "temperature_sum_dd"}
    with pytest.raises(ValueError, match="Elfving2010Model cannot resolve its inputs"):
        Elfving2010Model().build_context(_stand(), mode_hint="tree_list", attrs=incomplete)


def test_a_mistyped_key_is_reported_rather_than_read_as_absent():
    mistyped = dict(REQUIRED_ATTRS)
    mistyped["temperature_sum_ddd"] = mistyped.pop("temperature_sum_dd")
    with pytest.raises(ValueError, match="Temperature sum is required"):
        Elfving2010Model().build_context(_stand(), mode_hint="tree_list", attrs=mistyped)


def test_supplying_inputs_directly_skips_resolution():
    """A caller that built the stand knows its site; it should not have to spell
    that knowledge as string keys and have the model parse them back out."""
    inputs = Elfving2010Inputs(
        site_index_m=30.0,
        temperature_sum_dd=1300.0,
        latitude_deg=57.0,
        altitude_m=50.0,
        distance_to_coast_km=25.0,
    )
    # No attrs at all: resolution would raise, so this proves it did not run.
    ctx = Elfving2010Model().build_context(_stand(), mode_hint="tree_list", inputs=inputs)
    assert ctx.inputs is inputs


def test_inputs_are_frozen():
    ctx = Elfving2010Model().build_context(_stand(), mode_hint="tree_list", attrs=REQUIRED_ATTRS)
    with pytest.raises(dataclasses.FrozenInstanceError):
        ctx.inputs.site_index_m = 1.0


def test_run_state_is_not_frozen_into_inputs():
    """A thinning performed during the run must still reach the model.

    ``thinning_simulated`` is state, not an input. Freezing it at build time
    would leave the model responding to the stand's pre-run history forever,
    which is how a model stops reacting to its own management.
    """
    model = Elfving2010Model()
    ctx = model.build_context(_stand(), mode_hint="tree_list", attrs=REQUIRED_ATTRS)
    assert not hasattr(ctx.inputs, "thinning_simulated")

    before = model._thinning_flags(ctx, ctx.inputs)
    ctx.attrs["thinning_simulated"] = True
    after = model._thinning_flags(ctx, ctx.inputs)
    assert after == (0, 0)
    assert before == (0, 0)  # no pre-run history declared either


def test_pre_run_thinning_history_is_an_input():
    model = Elfving2010Model()
    ctx = model.build_context(
        _stand(),
        mode_hint="tree_list",
        attrs={**REQUIRED_ATTRS, "thinned_0_10_years": True},
    )
    assert ctx.inputs.thinned_0_10_years is True
    assert model._thinning_flags(ctx, ctx.inputs) == (1, 0)


def test_a_model_declaring_no_inputs_still_builds():
    """``Inputs`` is opt-in; a model that reads attrs directly is unaffected."""
    ctx = ExampleStandGeneralModel().build_context(_stand(), mode_hint="tree_list")
    assert ExampleStandGeneralModel.Inputs is None
    assert ctx.inputs is None


def test_attrs_passed_to_build_context_are_merged_over_model_defaults():
    model = Elfving2010Model()
    ctx = model.build_context(_stand(), mode_hint="tree_list", attrs=REQUIRED_ATTRS)
    # The build's own provenance attribute survives the caller's attrs.
    assert ctx.attrs["inventory_origin"] == "tree_list"
    assert ctx.attrs["site_index_m"] == pytest.approx(22.0)
