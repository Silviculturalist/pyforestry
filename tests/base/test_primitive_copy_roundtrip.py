"""The measurement primitives survive being copied.

Several of them are ``float`` subclasses whose ``__new__`` takes required
arguments beyond the value. Python rebuilds a ``float`` subclass by calling
``__new__`` with whatever ``__getnewargs__`` returns, and ``float``'s own returns
only the value -- so without an override, ``copy.deepcopy`` of anything holding one
raised ``TypeError: __new__() missing 1 required positional argument``.

That is not a corner: ``pyforestry.project`` deep-copies the stand it is given so
the caller's inventory survives the projection, and
``SimulationContext.checkpoint`` deep-copies the plots. Both failed on any stand
whose trees carried an age -- which is every stand the Elfving and Söderberg growth
models read a tree age from.
"""

from __future__ import annotations

import copy
import pickle

import pytest

from pyforestry.base.helpers.primitives import (
    Age,
    AgeMeasurement,
    Diameter_cm,
    QuadraticMeanDiameter,
    SiteIndexValue,
    StandBasalArea,
    Stems,
    TopHeightDefinition,
    TopHeightMeasurement,
)
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970


def _cases():
    return {
        "AgeMeasurement": (Age.DBH(40), ("code",)),
        "Diameter_cm": (
            Diameter_cm(25.0, over_bark=False, measurement_height_m=1.3),
            ("over_bark", "measurement_height_m"),
        ),
        "StandBasalArea": (StandBasalArea(25.0, precision=1.5), ("precision",)),
        "Stems": (Stems(500.0, precision=10.0), ("precision",)),
        "QuadraticMeanDiameter": (QuadraticMeanDiameter(22.0, precision=0.5), ("precision",)),
        "TopHeightMeasurement": (
            TopHeightMeasurement(
                24.0,
                definition=TopHeightDefinition(),
                species=TreeSpecies.Sweden.pinus_sylvestris,
                precision=0.4,
                est_bias=0.1,
            ),
            ("species", "precision", "est_bias"),
        ),
        "SiteIndexValue": (
            SiteIndexValue(
                24.0,
                reference_age=Age.TOTAL(100),
                species={TreeSpecies.Sweden.pinus_sylvestris},
                fn=Hagglund_1970.height_trajectory.pinus_sylvestris.sweden,
            ),
            ("reference_age", "species", "fn"),
        ),
    }


@pytest.mark.parametrize("name", sorted(_cases()))
def test_deepcopy_preserves_value_and_metadata(name: str) -> None:
    """A deep copy is the same number carrying the same facts about it."""
    original, attributes = _cases()[name]
    clone = copy.deepcopy(original)

    assert type(clone) is type(original)
    assert float(clone) == pytest.approx(float(original))
    for attribute in attributes:
        assert getattr(clone, attribute) == getattr(original, attribute)


@pytest.mark.parametrize("name", sorted(set(_cases()) - {"SiteIndexValue"}))
def test_pickle_roundtrips(name: str) -> None:
    """The same, through pickle, which is what a parallel run uses."""
    original, attributes = _cases()[name]
    clone = pickle.loads(pickle.dumps(original))

    assert type(clone) is type(original)
    assert float(clone) == pytest.approx(float(original))
    for attribute in attributes:
        assert getattr(clone, attribute) == getattr(original, attribute)


def test_a_site_index_still_cannot_be_pickled_and_says_why() -> None:
    """Known gap, recorded so nobody assumes copying fixed it.

    ``SiteIndexValue`` carries the height trajectory that produced it, and those
    are attached to their model classes at import rather than defined on them, so
    ``pickle`` cannot find one by name. Deep copies work -- a function is atomic to
    ``deepcopy`` -- and that is what ``project`` and ``checkpoint`` need. Making
    them picklable means changing how the trajectories are registered.
    """
    site_index, _attributes = _cases()["SiteIndexValue"]
    with pytest.raises((pickle.PicklingError, AttributeError)):
        pickle.dumps(site_index)


def test_a_deep_copied_age_is_still_a_valid_measurement() -> None:
    """The reconstruction runs the real constructor, so its checks still apply."""
    clone = copy.deepcopy(Age.DBH(40))
    assert isinstance(clone, AgeMeasurement)
    assert clone.code == Age.DBH.value
    with pytest.raises(ValueError, match="non-negative"):
        AgeMeasurement(*(-1.0, Age.DBH.value))
