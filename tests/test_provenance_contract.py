"""``components`` means one thing: the Describables a composition is built from.

Three classes declared ``components -> Sequence[Describable]`` and one --
``MortalityEngine`` -- returned ``tuple[str, ...]``. Nothing caught it, because
the one consumer read ``component_id``/``source`` off each entry with ``getattr``
defaults and skipped whatever did not answer. A run driven through the mortality
engine therefore reported one citation, its own, and dropped the seven papers
that produced the numbers.
"""

from __future__ import annotations

import pytest

from pyforestry.projection import _provenance
from pyforestry.sweden.simulation.mortality.engine import MortalityEngine
from pyforestry.sweden.simulation.presets import (
    build_elfving_2010_pipeline,
    build_soderberg_1986_pipeline,
)

COMPOSITIONS = [
    pytest.param(MortalityEngine, id="mortality_engine"),
    pytest.param(build_elfving_2010_pipeline, id="elfving_2010_pipeline"),
    pytest.param(build_soderberg_1986_pipeline, id="soderberg_1986_pipeline"),
]


@pytest.mark.parametrize("build", COMPOSITIONS)
def test_components_are_describable(build) -> None:
    """Every entry declares its own id and citation."""
    for component in build().components:
        assert isinstance(getattr(component, "component_id", None), str)
        assert getattr(component, "source", None) is not None
        assert not isinstance(component, str), (
            "an id is not a Describable: it carries no source, so a consumer that "
            "reads citations off components silently loses this one"
        )


@pytest.mark.parametrize("build", COMPOSITIONS)
def test_provenance_reports_every_composed_source(build) -> None:
    """The composition and each thing it composes appear in the provenance map."""
    composition = build()
    provenance = _provenance(composition)

    assert composition.component_id in provenance
    for component in composition.components:
        assert component.component_id in provenance
        # `source` is a property returning a fresh frozen dataclass, so compare by
        # value rather than identity.
        assert provenance[component.component_id] == component.source


def test_mortality_engine_reports_all_seven_papers() -> None:
    """The regression this file exists for."""
    provenance = _provenance(MortalityEngine())
    assert {
        "elfving_2013_mortality",
        "fridman_stahl_2001_mortality",
        "siipilehto_2020_mortality",
        "soderberg_1986_mortality_calibration",
        "bengtsson_mortality_calibration",
        "naslund_1986_damage",
        "retained_trees_mortality",
    } <= set(provenance)


def test_components_of_ids_is_rejected() -> None:
    """Returning bare ids fails loudly instead of dropping the citations."""

    class IdsOnly:
        component_id = "composition"
        source = object()
        components = ("elfving_2013_mortality",)

    with pytest.raises(TypeError, match="Describable"):
        _provenance(IdsOnly())


def test_provenance_survives_a_cycle() -> None:
    """A composition that reaches itself terminates rather than recursing forever."""

    class Node:
        def __init__(self, name: str) -> None:
            self.component_id = name
            self.source = object()
            self.components: tuple = ()

    a, b = Node("a"), Node("b")
    a.components = (b,)
    b.components = (a,)

    assert set(_provenance(a)) == {"a", "b"}
