"""Tests for model discovery: the catalog and the region front doors."""

from __future__ import annotations

import pathlib

import pytest

import pyforestry
from pyforestry import catalog
from pyforestry.base.contracts import SourceReference
from pyforestry.catalog import ModelEntry


def test_catalog_accessible_from_top_level():
    """The catalog is reachable via the lazy top-level package."""
    assert hasattr(pyforestry, "catalog")
    assert callable(catalog.find)


def test_list_models_returns_entries():
    """Discovery returns ModelEntry objects with populated core fields."""
    models = catalog.list_models()
    assert models, "expected at least one discoverable model"
    assert all(isinstance(m, ModelEntry) for m in models)
    by_id = {m.component_id for m in models}
    assert "brandel_1990_volume" in by_id
    assert "elfving_2010_growth" in by_id  # DESCRIPTOR lives in a package __init__


def test_find_by_domain_and_region():
    """Domain/region filters restrict results to matching entries."""
    volume = catalog.find(domain="volume")
    assert volume
    assert all(m.domain == "volume" for m in volume)  # both regions publish volume models
    assert {"brandel_1990_volume", "naslund_1947_volume"} <= {m.component_id for m in volume}
    # combined region + domain filter narrows to one region
    swe_volume = catalog.find(region="sweden", domain="volume")
    assert swe_volume and all(m.region == "sweden" and m.domain == "volume" for m in swe_volume)
    assert all(m.region == "sweden" for m in catalog.find(region="Sweden"))


def test_find_species_filter_best_effort():
    """The species substring filter matches identifiers (best-effort)."""
    pine_growth = catalog.find(domain="growth", species="pinus")
    assert "elfving_2010_growth" in {m.component_id for m in pine_growth}
    # species_groups use full scientific names, so exact names match too
    exact = catalog.find(domain="growth", species="Pinus sylvestris")
    assert "elfving_2010_growth" in {m.component_id for m in exact}


def test_search_by_id_and_author():
    """Search matches component id, module, and citation fields."""
    assert "brandel_1990_volume" in {m.component_id for m in catalog.search("brandel")}
    assert catalog.search("naslund"), "expected an author/id match for naslund"
    assert catalog.search("NONEXISTENT_QUERY_XYZ") == []


def test_find_units_filter():
    """The units filter matches unit names or values (substring, case-insensitive)."""
    cm_models = catalog.find(units="cm")
    assert "elfving_2010_growth" in {m.component_id for m in cm_models}  # has diameter_cm


def test_describe_exact_substring_and_errors():
    """describe resolves exact ids, module paths, unique substrings, and raises otherwise."""
    entry = catalog.describe("brandel_1990_volume")
    assert entry.source.author.startswith("Brandel")
    # exact match on the dotted module path
    assert catalog.describe(entry.module).component_id == "brandel_1990_volume"
    # unique substring fallback
    assert catalog.describe("brandel_1990").component_id == "brandel_1990_volume"
    with pytest.raises(KeyError):
        catalog.describe("does_not_exist")
    with pytest.raises(KeyError):
        catalog.describe("elfving")  # ambiguous: matches several ids


def test_domains_and_regions():
    """Helper enumerations expose the discovered domains and regions."""
    assert "volume" in catalog.domains()
    assert "growth" in catalog.domains()
    assert {"base", "sweden", "norway"} <= set(catalog.regions())


def test_base_region_models_are_discovered():
    """``base`` holds region-independent science and is scanned like the regions."""
    base = catalog.find(region="base")
    ids = {m.component_id for m in base}
    # Naslund's height curve, Garcia's top height, Bitterlich sampling, Nasberg bucking.
    assert {
        "naslund_1936_height_curve",
        "garcia_1998_top_height",
        "bitterlich_1948_angle_count",
        "nasberg_1985_bucking",
    } <= ids
    assert all(m.region == "base" for m in base)
    assert all(m.source.author and m.source.year for m in base)


def test_geo_climate_models_are_discovered():
    """``geo`` is scanned too: Odin 1983 and Eriksson 1986 publish descriptors."""
    climate = {m.component_id for m in catalog.find(domain="climate")}
    assert {"odin_1983_temperature_sum", "eriksson_1986_humidity"} <= climate


def test_discovery_does_not_import_geopandas_eagerly():
    """Scanning the geo modules must not pay the multi-second geopandas import.

    ``eriksson_1986`` defers it into the function for exactly this reason; a
    module-level import there would make every ``catalog`` call slow.
    """
    source = (
        pathlib.Path(__file__).resolve().parents[1]
        / "src"
        / "pyforestry"
        / "sweden"
        / "geo"
        / "humidity"
        / "eriksson_1986.py"
    ).read_text(encoding="utf-8")
    module_level = source.split("def eriksson_1986_humidity", 1)[0]
    assert "import geopandas" not in module_level


def test_refresh_rebuilds_cache():
    """refresh() clears the cache without changing the result."""
    before = catalog.list_models()
    catalog.refresh()
    after = catalog.list_models()
    assert {m.component_id for m in before} == {m.component_id for m in after}


def test_catalog_unifies_formula_and_model_tiers():
    """The catalog surfaces both formula kernels and composed model adapters."""
    models = catalog.find(kind="model")
    assert models, "expected composed-model entries"
    assert all(m.kind == "model" for m in models)
    assert {"elfving_2010_model", "eko_1985_model"} <= {m.component_id for m in models}

    # a growth-domain query returns both tiers
    growth_kinds = {m.kind for m in catalog.find(domain="growth")}
    assert growth_kinds == {"formula", "model"}

    # composes links point at real formula entries
    elfving_model = catalog.describe("elfving_2010_model")
    assert "elfving_2010_growth" in elfving_model.composes
    for composed_id in elfving_model.composes:
        assert catalog.describe(composed_id).kind == "formula"


def test_all_catalog_species_are_valid_names():
    """Every species identifier in every model resolves to a real species.

    Guards against descriptors storing raw enum labels or ``TreeName`` reprs
    instead of scientific names (which silently break the species filter).
    """
    from pyforestry.base.helpers import parse_tree_species

    for entry in catalog.list_models():
        for species in entry.species:
            parse_tree_species(species)  # raises ValueError on an unknown name


def test_model_entry_str_species_and_no_source():
    """ModelEntry renders a summary and flattens species; tolerates no source."""
    entry = ModelEntry(
        component_id="x_1999_volume",
        module="pyforestry.sweden.volume.x",
        region="sweden",
        domain="volume",
        source=SourceReference(author="X", year=1999, title="T"),
        species_groups={"pine": frozenset({"Pinus sylvestris"}), "spruce": frozenset()},
        units={"diameter": "cm"},
        kernel_names=("k",),
    )
    assert "x_1999_volume" in str(entry)
    assert entry.species == frozenset({"Pinus sylvestris"})

    no_source = ModelEntry("y", "m", "sweden", "volume", None, {}, {}, ())
    assert "y" in str(no_source)  # no citation, no crash


def test_sweden_front_door_lists_subpackages():
    """``dir(pyforestry.sweden)`` advertises its domains and lazy-loads them."""
    import pyforestry.sweden as sweden

    listing = dir(sweden)
    assert {"volume", "siteindex", "mortality", "growth"} <= set(listing)
    assert sweden.volume is not None  # triggers lazy __getattr__
    with pytest.raises(AttributeError):
        _ = sweden.not_a_subpackage


def test_norway_front_door_lists_subpackages():
    """``dir(pyforestry.norway)`` advertises its domains."""
    import pyforestry.norway as norway

    assert {"volume", "siteindex", "taper"} <= set(dir(norway))


def test_every_discoverable_model_declares_real_provenance():
    """No model may ship the placeholder provenance of the abstract base class.

    ``GrowthModel.source`` defaults to ``author="unknown", year=0`` so that the
    protocol is satisfiable, which means a model that forgets to override it is
    published with a citation nobody can follow. That default must never reach
    the catalog.

    ``author="(none)"`` with ``year=0`` is a different thing and is allowed: it is
    the deliberate marker for a module that holds no science to attribute (pure
    bookkeeping), and it has to say so in its note.
    """
    offenders = []
    for model in catalog.list_models():
        source = model.source
        author = (source.author or "").strip()
        if author.lower() == "unknown" or not author:
            offenders.append((model.component_id, "placeholder author"))
            continue
        if not (source.title or "").strip():
            offenders.append((model.component_id, "empty title"))
            continue
        if author == "(none)":
            # Allowed, but it must explain itself rather than look like an omission.
            if not (source.note or "").strip():
                offenders.append((model.component_id, "'(none)' author without a note"))
            continue
        if source.year <= 0:
            offenders.append((model.component_id, f"non-publication year {source.year}"))

    assert not offenders, f"models with unusable provenance: {offenders}"


def test_no_model_is_attributed_to_pyforestry_itself():
    """Presets cite the work they reproduce, not the package that composed them.

    A ``SourceReference`` is a bibliographic pointer to the science. Naming
    pyforestry as the author -- especially with a year borrowed from the model
    being composed -- produces a citation that leads nowhere.
    """
    offenders = [
        (m.component_id, m.source.author)
        for m in catalog.list_models()
        if "pyforestry" in (m.source.author or "").lower()
    ]
    assert not offenders, f"models attributed to pyforestry: {offenders}"
