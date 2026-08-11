"""County-tree site-category predictor backed by fitted decision-tree tables.

The fitted decision trees (one per categorical SIS target) are stored in the
sibling ``site_category_trees.json`` data asset and loaded at import via
:mod:`importlib.resources`. This module exposes them under their historical
names (``CAT_TARGETS``, ``SPECIES_CATEGORIES``, ``SPECIES_FILL_VALUE``,
``NUMERIC_DEFAULTS``, ``TARGET_MODELS``) and provides
:func:`predict_site_categories_county_tree`.

The JSON tables are generated, not hand-edited: re-fit them in
``docs/source/notebooks/_archive/SIS_test.ipynb`` and re-export the data file.
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

from pyforestry.base.helpers import enum_code
from pyforestry.sweden.site.enums import Sweden

_DATA = json.loads(
    (resources.files(__package__) / "site_category_trees.json").read_text(encoding="utf-8")
)

CAT_TARGETS: list[str] = _DATA["CAT_TARGETS"]
SPECIES_CATEGORIES: list[str] = _DATA["SPECIES_CATEGORIES"]
SPECIES_FILL_VALUE: str = _DATA["SPECIES_FILL_VALUE"]
NUMERIC_DEFAULTS: dict[str, float] = _DATA["NUMERIC_DEFAULTS"]
TARGET_MODELS: dict[str, Any] = _DATA["TARGET_MODELS"]

_SPECIES_CANONICAL = {category.casefold(): category for category in SPECIES_CATEGORIES}

__all__ = ["predict_site_categories_county_tree"]


def _coerce_float(value: Any, default: float) -> float:
    """Return ``value`` as a float, falling back to ``default`` for invalid/NaN input."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return float(default)
    if v != v:
        return float(default)
    return v


def _coerce_species(value: Any) -> str:
    """Normalize a species input (string or ``TreeName``) to a canonical category label."""
    if value is None:
        return SPECIES_FILL_VALUE
    if hasattr(value, "full_name"):
        value = value.full_name
    species_value = str(value).strip()
    return _SPECIES_CANONICAL.get(species_value.casefold(), species_value)


def _predict_label_for_target(target_name: str, features: dict[str, float]) -> str:
    """Walk the fitted decision tree for ``target_name`` and return its best class label."""
    model = TARGET_MODELS[target_name]
    node = 0
    while model["tree_feature"][node] != -2:
        feature_idx = model["tree_feature"][node]
        feature_name = model["feature_names"][feature_idx]
        feature_value = features.get(feature_name, 0.0)
        if feature_value <= model["tree_threshold"][node]:
            node = model["tree_left"][node]
        else:
            node = model["tree_right"][node]

    scores = model["tree_values"][node]
    best_index = max(range(len(scores)), key=lambda i: scores[i])
    return model["class_labels"][best_index]


def _to_enum(enum_cls, label: str):
    """Resolve a predicted ``label`` to a member of ``enum_cls`` (or ``None`` if unmatched)."""
    if label in (None, "NA", "nan"):
        return None
    for member in enum_cls:
        inner = member.value
        for attr in (
            "label",
            "english_name",
            "english_description",
            "short_name",
            "swedish_name",
            "code",
        ):
            if hasattr(inner, attr) and str(getattr(inner, attr)) == str(label):
                return member
    return None


def _to_bool(label: str):
    """Convert a predicted ``label`` to a bool, or ``None`` when unavailable."""
    if label in (None, "NA", "nan"):
        return None
    return str(label).strip().lower() == "true"


def predict_site_categories_county_tree(
    *,
    sis_hagglund_1979: Any,
    species: Any,
    Direktlan: Any,
) -> dict[str, Any]:
    """Predict Sweden site-category enums from SIS, species, and county (Direktlän) inputs."""
    species_value = _coerce_species(species)

    features = {}
    for category in SPECIES_CATEGORIES:
        features[f"species_{category}"] = 1.0 if species_value == category else 0.0

    features["sis_hagglund_1979"] = _coerce_float(
        sis_hagglund_1979,
        NUMERIC_DEFAULTS["sis_hagglund_1979"],
    )
    features["Direktlan"] = _coerce_float(
        enum_code(Direktlan),
        NUMERIC_DEFAULTS["Direktlan"],
    )

    raw = {target: _predict_label_for_target(target, features) for target in CAT_TARGETS}

    return {
        "field_layer": _to_enum(Sweden.FieldLayer, raw["field_layer"]),
        "bottom_layer": _to_enum(Sweden.BottomLayer, raw["bottom_layer"]),
        "soil_texture": _to_enum(Sweden.SoilTextureTill, raw["soil_texture"])
        or _to_enum(Sweden.SoilTextureSediment, raw["soil_texture"]),
        "soil_moisture": _to_enum(Sweden.SoilMoistureEnum, raw["soil_moisture"]),
        "soil_depth": _to_enum(Sweden.SoilDepth, raw["soil_depth"]),
        "soil_water": _to_enum(Sweden.SoilWater, raw["soil_water"]),
        "ditched": _to_bool(raw["ditched"]),
    }
