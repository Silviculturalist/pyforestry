"""Interfaces that were documentation, now enforced.

Each test here pins a defect where the package stated a rule and did not check
it, so the failure mode was silence: a model with no citation reporting a
plausible-looking one, a broken module vanishing from discovery, a step length
learnable only by triggering an exception.
"""

import pytest

from pyforestry.base.helpers import CircularPlot, Stand, Tree
from pyforestry.base.simulation import GrowthModel, Requirements


def _instantiate(model_cls):
    """Build a model with default configuration, supplying one where required."""
    try:
        return model_cls()
    except TypeError:
        # Bollandsas is the one adapter whose config is fully required.
        from pyforestry.norway.adapters.bollandsas_2008 import Bollandsas2008AdapterConfig

        return model_cls(
            Bollandsas2008AdapterConfig(
                site_index_by_species={"picea abies": 17.0},
                latitude_deg=60.0,
            )
        )


# ---------------------------------------------------------------------------
# C7: interface enforcement
# ---------------------------------------------------------------------------


def test_an_incomplete_model_cannot_be_constructed():
    class MissingBoth(GrowthModel):
        pass

    with pytest.raises(TypeError, match="abstract"):
        MissingBoth()


def test_a_model_without_a_citation_refuses_to_invent_one():
    """It returned ``SourceReference("unknown", 0, "unknown")``.

    That is a citation-shaped object, so it read like a real one in a catalog
    listing and a provenance report -- the two places a reader goes to find out
    where a number came from.
    """

    class Uncited(GrowthModel):
        def requirements(self):
            return Requirements()

        def update_step(self, ctx, dt):
            return None

    with pytest.raises(NotImplementedError, match="does not declare a source"):
        _ = Uncited().source


def test_every_shipped_model_declares_a_real_source():
    from pyforestry.norway import adapters as norway_adapters
    from pyforestry.sweden import adapters as sweden_adapters
    from pyforestry.sweden import systems as sweden_systems

    models = []
    for package in (sweden_adapters, sweden_systems, norway_adapters):
        for name in package.__all__:
            obj = getattr(package, name)
            if isinstance(obj, type) and issubclass(obj, GrowthModel):
                models.append(obj)
    assert models, "no GrowthModel subclasses found to check"

    for model_cls in models:
        source = _instantiate(model_cls).source
        assert source.author and source.author != "unknown", model_cls.__name__
        assert source.year and source.year != 0, model_cls.__name__


# ---------------------------------------------------------------------------
# D4: a model's step length is discoverable without triggering its exception
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("import_path", "class_name"),
    [
        ("pyforestry.sweden.adapters.elfving_2010", "Elfving2010Model"),
        ("pyforestry.sweden.adapters.soderberg_1986_growth", "Soderberg1986Model"),
        ("pyforestry.sweden.systems.eko1985.model", "Eko1985Model"),
        ("pyforestry.norway.adapters.bollandsas_2008", "Bollandsas2008GrowthModel"),
    ],
)
def test_five_year_models_declare_their_native_step(import_path, class_name):
    import importlib

    model = _instantiate(getattr(importlib.import_module(import_path), class_name))
    assert model.requirements().native_step_years == 5.0


def test_native_step_defaults_to_none_for_a_step_agnostic_model():
    class Agnostic(GrowthModel):
        def requirements(self):
            return Requirements()

        def update_step(self, ctx, dt):
            return None

    assert Agnostic().requirements().native_step_years is None


# ---------------------------------------------------------------------------
# C12: a broken model does not silently vanish from the catalog
# ---------------------------------------------------------------------------


def test_catalog_reports_what_it_could_not_import(monkeypatch):
    import importlib

    from pyforestry import catalog

    real_import = importlib.import_module
    broken = "pyforestry.sweden.volume.brandel_1990"

    def failing_import(name, *args, **kwargs):
        if name == broken:
            raise RuntimeError("simulated breakage")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(catalog.importlib, "import_module", failing_import)
    catalog.refresh()
    with pytest.warns(UserWarning, match="could not import"):
        catalog.list_models()

    errors = catalog.discovery_errors()
    assert broken in errors
    assert isinstance(errors[broken], RuntimeError)
    catalog.refresh()


def test_catalog_reports_no_errors_when_everything_imports():
    from pyforestry import catalog

    catalog.refresh()
    assert catalog.discovery_errors() == {}


# ---------------------------------------------------------------------------
# D3: the first line of code a new user runs is a property, not __getattr__
# ---------------------------------------------------------------------------


def test_total_is_a_real_property_on_the_accessor():
    from pyforestry.base.helpers.stand import StandMetricAccessor

    assert isinstance(StandMetricAccessor.__dict__["TOTAL"], property)


def test_the_readme_example_still_works():
    stand = Stand(
        plots=[
            CircularPlot(id=1, radius_m=5.0, trees=[Tree(species="picea abies", diameter_cm=20)])
        ]
    )
    assert stand.BasalArea.TOTAL.value > 0.0


def test_an_unknown_metric_attribute_still_raises():
    stand = Stand(
        plots=[
            CircularPlot(id=1, radius_m=5.0, trees=[Tree(species="picea abies", diameter_cm=20)])
        ]
    )
    with pytest.raises(AttributeError):
        _ = stand.BasalArea.NOT_A_METRIC


# ---------------------------------------------------------------------------
# C9: Tree validates what it stores raw
# ---------------------------------------------------------------------------


def test_tree_rejects_a_negative_diameter():
    with pytest.raises(ValueError, match="diameter_cm must not be negative"):
        Tree(species="picea abies", diameter_cm=-1.0)


def test_tree_rejects_a_negative_height():
    with pytest.raises(ValueError, match="height_m must not be negative"):
        Tree(species="picea abies", height_m=-1.0)


def test_tree_keeps_a_supplied_diameter_convention():
    """A plain float is not silently relabelled as over-bark DBH at 1.3 m."""
    from pyforestry.base.helpers.primitives import Diameter_cm

    plain = Tree(species="picea abies", diameter_cm=20.0)
    assert not isinstance(plain.diameter_cm, Diameter_cm)

    stated = Tree(
        species="picea abies",
        diameter_cm=Diameter_cm(20.0, over_bark=False, measurement_height_m=0.0),
    )
    assert stated.diameter_cm.over_bark is False
    assert stated.diameter_cm.measurement_height_m == 0.0
