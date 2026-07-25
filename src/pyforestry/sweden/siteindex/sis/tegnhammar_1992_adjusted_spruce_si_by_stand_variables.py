"""Tegnhammar 1992 Adjusted Spruce Si By Stand Variables utilities and interfaces.

Source: Swedish forestry domain models and helper implementations curated in pyforestry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.sweden.site.enums import Sweden

from .tegnhammar_1992 import tegnhammar_1992_adjusted_spruce_si_by_stand_variables as _impl

if TYPE_CHECKING:  # pragma: no cover - for type checking only
    from pyforestry.base.helpers import SiteIndexValue


def tegnhammar_1992_adjusted_spruce_si_by_stand_variables(
    latitude: float,
    longitude: float,
    altitude: float,
    vegetation: int | Sweden.FieldLayer,
    ground_layer: int | Sweden.BottomLayer,
    aspect_main: int,
    soil_moisture: int | Sweden.SoilMoistureEnum,
    soil_depth: int | Sweden.SoilDepth,
    soil_texture: int | Sweden.SoilTextureTill | Sweden.SoilTextureSediment,
    humidity: float | None = None,
    ditched: bool = False,
    lateral_water: int | Sweden.SoilWater = 1,
    peat_humification: int | Sweden.PeatHumification = Sweden.PeatHumification.MEDIUM,
    epsg: str = "EPSG:4326",
) -> SiteIndexValue:
    """Wrapper for :func:`pyforestry.sweden.siteindex.sis.tegnhammar_1992`
    using explicit Sweden enums.
    """
    return _impl(
        latitude=latitude,
        longitude=longitude,
        altitude=altitude,
        vegetation=vegetation,
        ground_layer=ground_layer,
        aspect_main=aspect_main,
        soil_moisture=soil_moisture,
        soil_depth=soil_depth,
        soil_texture=soil_texture,
        humidity=humidity,
        ditched=ditched,
        lateral_water=lateral_water,
        peat_humification=peat_humification,
        epsg=epsg,
    )


DESCRIPTOR = FormulaDescriptor(
    component_id="tegnhammar_1992_adjusted_siteindex",
    source=SourceReference(
        author="Tegnhammar, L.",
        year=1992,
        title=(
            "Om skattningen av ståndortsindex för gran - adjusted spruce site index "
            "from stand variables"
        ),
    ),
    species_groups={"spruce": frozenset({"Picea abies"})},
    units={},
    kernel_names=("tegnhammar_1992_adjusted_spruce_si_by_stand_variables",),
)
