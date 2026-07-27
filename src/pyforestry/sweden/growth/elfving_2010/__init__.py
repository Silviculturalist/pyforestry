"""Elfving 2010 growth equations (kernels and feature transforms)."""

from __future__ import annotations

from pyforestry.base.contracts import FormulaDescriptor, SourceReference

from .features import *  # noqa: F401, F403
from .features import (
    ASPEN_SPECIES,
    BEECH_SPECIES,
    BIRCH_SPECIES,
    OAK_SPECIES,
    PINE_SPECIES,
    PRECIOUS_SPECIES,
    SPRUCE_SPECIES,
)
from .kernels import __all__ as _kernel_names
from .thinning_response import (  # noqa: F401
    ThinningEvent,
    elfving_2009_thinning_response_factor,
    residual_release_effect,
)

DESCRIPTOR = FormulaDescriptor(
    component_id="elfving_2010_growth",
    source=SourceReference(
        author="Elfving, B.",
        year=2010,
        title="Growth modelling in the Heureka system",
        appendix="Appendix 3",
    ),
    species_groups={
        "pine": frozenset(s.full_name for s in PINE_SPECIES),
        "spruce": frozenset(s.full_name for s in SPRUCE_SPECIES),
        "birch": frozenset(s.full_name for s in BIRCH_SPECIES),
        "aspen": frozenset(s.full_name for s in ASPEN_SPECIES),
        "beech": frozenset(s.full_name for s in BEECH_SPECIES),
        "oak": frozenset(s.full_name for s in OAK_SPECIES),
        "precious": frozenset(s.full_name for s in PRECIOUS_SPECIES),
        "trivial": frozenset(),
    },
    units={
        "diameter_cm": "cm",
        "age_bh_years": "years",
        "basal_area_m2_ha": "m²/ha",
        "temperature_sum_dd": "degree-days",
        "site_index_m": "m",
        "distance_to_coast_km": "km",
        "altitude_m": "m",
        "latitude_deg": "degrees",
        "return": "ln(cm²)",
    },
    kernel_names=list(_kernel_names),
)
