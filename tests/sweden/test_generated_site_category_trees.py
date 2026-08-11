from pyforestry.base.helpers import TreeSpecies
from pyforestry.sweden.site.enums import Sweden
from pyforestry.sweden.siteindex.sis import generated_site_category_trees as generated

EXPECTED_KEYS = {
    "field_layer",
    "bottom_layer",
    "soil_texture",
    "soil_moisture",
    "soil_depth",
    "soil_water",
    "ditched",
}


def _predict(species, county):
    return generated.predict_site_categories_county_tree(
        sis_hagglund_1979=23.0,
        species=species,
        Direktlan=county,
    )


def _assert_output_types(result):
    assert set(result) == EXPECTED_KEYS
    assert isinstance(result["field_layer"], Sweden.FieldLayer) or result["field_layer"] is None
    assert isinstance(result["bottom_layer"], Sweden.BottomLayer) or result["bottom_layer"] is None
    assert (
        isinstance(result["soil_texture"], Sweden.SoilTextureTill)
        or isinstance(result["soil_texture"], Sweden.SoilTextureSediment)
        or result["soil_texture"] is None
    )
    assert (
        isinstance(result["soil_moisture"], Sweden.SoilMoistureEnum)
        or result["soil_moisture"] is None
    )
    assert isinstance(result["soil_depth"], Sweden.SoilDepth) or result["soil_depth"] is None
    assert isinstance(result["soil_water"], Sweden.SoilWater) or result["soil_water"] is None
    assert isinstance(result["ditched"], bool) or result["ditched"] is None


def test_generated_site_category_tree_returns_sweden_types():
    result = _predict("Picea abies", Sweden.County.UPPSALA.value.code)
    _assert_output_types(result)


def test_generated_site_category_tree_accepts_county_enum():
    by_code = _predict("Pinus sylvestris", Sweden.County.UPPSALA.value.code)
    by_enum = _predict("Pinus sylvestris", Sweden.County.UPPSALA)
    assert by_enum == by_code


def test_generated_site_category_tree_normalizes_species_inputs():
    from_title = _predict("Picea abies", Sweden.County.UPPSALA)
    from_lower = _predict("picea abies", Sweden.County.UPPSALA)
    from_tree_name = _predict(TreeSpecies.Sweden.picea_abies, Sweden.County.UPPSALA)
    assert from_lower == from_title
    assert from_tree_name == from_title


def test_generated_site_category_tree_class_labels_map_to_enums():
    enum_targets = {
        "field_layer": Sweden.FieldLayer,
        "bottom_layer": Sweden.BottomLayer,
        "soil_moisture": Sweden.SoilMoistureEnum,
        "soil_depth": Sweden.SoilDepth,
        "soil_water": Sweden.SoilWater,
    }

    for target, enum_cls in enum_targets.items():
        labels = generated.TARGET_MODELS[target]["class_labels"]
        for label in labels:
            assert generated._to_enum(enum_cls, label) is not None

    soil_texture_labels = generated.TARGET_MODELS["soil_texture"]["class_labels"]
    for label in soil_texture_labels:
        converted = generated._to_enum(Sweden.SoilTextureTill, label) or generated._to_enum(
            Sweden.SoilTextureSediment,
            label,
        )
        assert converted is not None

    ditched_labels = generated.TARGET_MODELS["ditched"]["class_labels"]
    for label in ditched_labels:
        converted = generated._to_bool(label)
        assert isinstance(converted, bool) or converted is None


def test_generated_helpers_handle_edge_inputs():
    """Fallback branches of the prediction helpers behave sanely."""
    # _coerce_float: invalid and NaN inputs fall back to the default.
    assert generated._coerce_float("not-a-number", 1.5) == 1.5
    assert generated._coerce_float(float("nan"), 2.5) == 2.5
    assert generated._coerce_float("3.0", 0.0) == 3.0
    # _coerce_species: ``None`` maps to the configured fill value.
    assert generated._coerce_species(None) == generated.SPECIES_FILL_VALUE
    # _to_enum: NA-style labels and unmatched labels both yield ``None``.
    assert generated._to_enum(Sweden.FieldLayer, "NA") is None
    assert generated._to_enum(Sweden.FieldLayer, "no-such-label") is None
    # _to_bool: NA-style labels yield ``None``; explicit booleans round-trip.
    assert generated._to_bool("NA") is None
    assert generated._to_bool("True") is True
    assert generated._to_bool("false") is False
