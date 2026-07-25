"""Extracted site/context helpers for the Ekö 1985 model adapter.

Source:
    Ekö, P.-M. (1985). *En produktionsmodell för skog i Sverige, baserad på bestånd
    från riksskogstaxeringens provytor = A growth simulator for Swedish forests,
    based on data from the national forest survey.* Sveriges lantbruksuniversitet,
    institutionen för skogsskötsel, Rapport nr 16, Umeå.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from enum import Enum
from math import log as _math_log
from math import pi
from typing import Any

from pyforestry.base.helpers import (
    Age,
    AgeMeasurement,
    QuadraticMeanDiameter,
    SiteIndexValue,
    TreeName,
    TreeSpecies,
    parse_tree_species,
)
from pyforestry.sweden.site.enums import Sweden
from pyforestry.sweden.site.swedish_site import SwedishSite
from pyforestry.sweden.siteindex.carbonnier_1971 import (
    CarbonnierHeightModel,
    carbonnier_1971_beech_height_model,
)
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970, HagglundPineRegeneration
from pyforestry.sweden.siteindex.translate import leijon_pine_to_spruce, leijon_spruce_to_pine
from pyforestry.sweden.siteindex.validation import validate_hagglund_1970_h100_site_index


def qmd_cm(ba_m2_per_ha: float, stems_per_ha: float) -> float:
    """Quadratic mean diameter (cm) given basal area and stem count."""
    if ba_m2_per_ha <= 0.0 or stems_per_ha <= 0.0:
        return 0.0
    return (ba_m2_per_ha * 40000.0 / (pi * stems_per_ha)) ** 0.5


def _safe_sum(iterable) -> float:
    """Sum values in ``iterable`` as floats."""
    total = 0.0
    for value in iterable:
        total += float(value)
    return total


def _safe_qmd(basal_area_m2_per_ha: float, stems_per_ha: float) -> QuadraticMeanDiameter:
    """Compute QMD using the primitive class while tolerating empty cohorts."""
    if basal_area_m2_per_ha <= 0 or stems_per_ha <= 0:
        return QuadraticMeanDiameter(0.0)
    return QuadraticMeanDiameter.compute_from(
        basal_area_m2_per_ha=basal_area_m2_per_ha, stems_per_ha=stems_per_ha
    )


def _coerce_age(
    age: AgeMeasurement | float | int, default_code: Age = Age.TOTAL
) -> AgeMeasurement:
    """Normalise numeric ages to :class:`AgeMeasurement`."""
    if isinstance(age, AgeMeasurement):
        return age
    return default_code(float(age))


def _coerce_species(species: TreeName | str) -> TreeName:
    """Normalise species inputs to :class:`TreeName`."""
    if isinstance(species, TreeName):
        return species
    return parse_tree_species(species)


def _safe_log(x, eps: float = 1e-9) -> float:
    """Safe natural log that tolerates non-positive values."""
    if x is None:
        return _math_log(eps)
    try:
        x = float(x)
    except (TypeError, ValueError):
        return _math_log(eps)
    if x <= 0.0:
        x = eps
    return _math_log(x)


class _ConcreteSwedishSite(SwedishSite):
    """Concrete wrapper for environments where ``SwedishSite`` is abstract."""

    def compute_attributes(self) -> None:
        """Populate derived attributes using the SwedishSite implementation."""
        SwedishSite.__post_init__(self)


class RegionSE(Enum):
    """Swedish region categories used by the Eko 1985 model."""

    NORRA = "North"
    MELLERSTA = "Central"
    SÖDRA = "South"
    SODRA = "South"


@dataclass(frozen=True)
class DominantHeightObservation:
    """Observed dominant height at a given age."""

    height_m: float
    age: AgeMeasurement

    @classmethod
    def from_values(
        cls, height_m: float, age: AgeMeasurement | float | int
    ) -> DominantHeightObservation:
        """Create an observation from numeric inputs."""
        return cls(height_m=float(height_m), age=_coerce_age(age))


@dataclass
class Eko1985SiteContext:
    """Site inputs resolved to refactored ``EkoStandSite`` using pyforestry primitives."""

    latitude: float | None = None
    longitude: float | None = None
    altitude: float | None = None
    vegetation: Sweden.FieldLayer | int | None = None
    soil_moisture: Sweden.SoilMoistureEnum | int | None = None
    fertilised: bool = False
    thinned_5y: bool = False
    thinned: bool = False
    tax77: bool = False
    #: Use ProdMod2's broadleaf-volume behaviour (the Nord+Mellan function in every
    #: region) instead of the canonical Ekö 1985 region-specific Syd functions for
    #: birch (Tabell 10c) and 'other broadleaf' (Tabell 10f) in the South -- ProdMod2's
    #: volume table is region-identical for both. See ``BroadleafEngineCohort.get_volume``.
    broadleaf_volume_prodmod: bool = False
    #: Use ProdMod2's broadleaf-growth behaviour: key the birch/beech/oak/'other'
    #: basal-area-increment SI-class (and beech's linear SI term) off the stand's
    #: *spruce* site index (ProdMod2 reads ``species_values[1]`` for every broadleaf),
    #: and clamp the BAI basal-area/stem inputs to ProdMod2's diameter limits.
    #: False (default) keeps the canonical Ekö 1985 reading -- each cohort's own SI,
    #: no input clamping. See ``EngineStandPart._bai_class_si_dm`` / ``_bai_diameter_caps``.
    broadleaf_growth_prodmod: bool = False
    spruce_site_index: SiteIndexValue | float | None = None
    pine_site_index: SiteIndexValue | float | None = None
    spruce_height_obs: DominantHeightObservation | None = None
    pine_height_obs: DominantHeightObservation | None = None
    pine_regeneration: HagglundPineRegeneration = HagglundPineRegeneration.UNKNOWN
    beech_height_obs: DominantHeightObservation | None = None
    # Defaults to the published Carbonnier (1971) Table IV.1 coefficients. Before
    # those were transcribed this field had no usable default, so a beech height
    # observation could never yield a site index unless the caller built the
    # coefficient table themselves -- which nothing did.
    carbonnier_model: CarbonnierHeightModel | None = field(
        default_factory=carbonnier_1971_beech_height_model
    )
    swedish_site: SwedishSite | None = None

    def _as_field_layer(self) -> Sweden.FieldLayer | None:
        """Normalize field-layer input to a Sweden enum when possible."""
        if isinstance(self.vegetation, Sweden.FieldLayer):
            return self.vegetation
        if isinstance(self.vegetation, int):
            for member in Sweden.FieldLayer:
                if member.value.code == self.vegetation:
                    return member
        return None

    def _as_soil_moisture(self) -> Sweden.SoilMoistureEnum | None:
        """Normalize soil moisture input to a Sweden enum when possible."""
        if isinstance(self.soil_moisture, Sweden.SoilMoistureEnum):
            return self.soil_moisture
        if isinstance(self.soil_moisture, int):
            for member in Sweden.SoilMoistureEnum:
                if member.value.code == self.soil_moisture:
                    return member
        return None

    def _resolved_swedish_site(self) -> SwedishSite | None:
        """Return a SwedishSite built from coordinates when available."""
        if self.swedish_site is not None:
            return self.swedish_site
        if self.latitude is None or self.longitude is None:
            return None
        site_cls = _ConcreteSwedishSite
        altitude = float(self.altitude) if self.altitude is not None else None
        self.swedish_site = site_cls(
            latitude=float(self.latitude),
            longitude=float(self.longitude),
            altitude=altitude,
            field_layer=self._as_field_layer(),
            soil_moisture=self._as_soil_moisture(),
        )
        return self.swedish_site

    def _resolved_latitude(self) -> float | None:
        """Return the latitude resolved from coordinates or SwedishSite."""
        if self.latitude is not None:
            return self.latitude
        site = self._resolved_swedish_site()
        return site.latitude if site is not None else None

    def _resolved_altitude(self) -> float | None:
        """Return the altitude resolved from coordinates or SwedishSite."""
        if self.altitude is not None:
            return self.altitude
        site = self._resolved_swedish_site()
        return site.altitude if site is not None else None

    def _region_from_climate_zone(self, site: SwedishSite) -> str | None:
        """Map Swedish climate zones to model regions when possible."""
        climate_zone = site.climate_zone
        if climate_zone is None:
            return None
        label = climate_zone.value.label
        mapping = {
            "K2": "North",
            "K1": "Central",
            "K3": "South",
        }
        return mapping.get(label)

    def resolved_region(self) -> str:
        """Resolve model region from coordinates via SwedishSite."""
        site = self._resolved_swedish_site()
        if site is None:
            raise ValueError("Provide latitude and longitude or a SwedishSite to resolve region.")
        region = self._region_from_climate_zone(site)
        if region is not None:
            return region
        lat = site.latitude
        if lat >= 63:
            return "North"
        if lat >= 60:
            return "Central"
        return "South"

    def vegetation_code(self) -> int | None:
        """Return vegetation code compatible with the legacy model."""
        if isinstance(self.vegetation, Sweden.FieldLayer):
            return self.vegetation.value.code
        if isinstance(self.vegetation, int):
            return self.vegetation
        site = self._resolved_swedish_site()
        if site and site.field_layer:
            return site.field_layer.value.code
        return None

    def soil_moisture_code(self) -> int | None:
        """Return soil moisture code compatible with the legacy model."""
        if isinstance(self.soil_moisture, Sweden.SoilMoistureEnum):
            return self.soil_moisture.value.code
        if isinstance(self.soil_moisture, int):
            return self.soil_moisture
        site = self._resolved_swedish_site()
        if site and site.soil_moisture:
            return site.soil_moisture.value.code
        return None

    def _ensure_site_index(
        self,
        value: SiteIndexValue | float | None,
        species: TreeName,
        source_function: Any,
        *,
        validate_hagglund_1970: bool = True,
    ) -> SiteIndexValue | None:
        """Normalize site index values to ``SiteIndexValue`` instances."""
        if value is None:
            return None
        if isinstance(value, SiteIndexValue):
            if validate_hagglund_1970:
                validate_hagglund_1970_h100_site_index(
                    value,
                    param_name="site_index",
                    expected_species=species,
                )
            return value
        normalized_site_index = SiteIndexValue(
            float(value),
            reference_age=Age.TOTAL(100.0),
            species={species},
            fn=source_function,
        )
        if validate_hagglund_1970:
            validate_hagglund_1970_h100_site_index(
                normalized_site_index,
                param_name="site_index",
                expected_species=species,
            )
        return normalized_site_index

    def _spruce_from_observation(self) -> SiteIndexValue | None:
        """Infer spruce site index from dominant height observations."""
        if self.spruce_height_obs is None:
            return None
        lat = self._resolved_latitude() or 60.0
        target_age = Age.TOTAL(100.0)
        if self.resolved_region() == "South":
            model = Hagglund_1970.height_trajectory.picea_abies.southern_sweden
            return model(
                self.spruce_height_obs.height_m,
                self.spruce_height_obs.age,
                target_age,
            )
        model = Hagglund_1970.height_trajectory.picea_abies.northern_sweden
        return model(
            self.spruce_height_obs.height_m,
            self.spruce_height_obs.age,
            target_age,
            latitude=lat,
        )

    def _pine_from_observation(self) -> SiteIndexValue | None:
        """Infer pine site index from dominant height observations."""
        if self.pine_height_obs is None:
            return None
        target_age = Age.TOTAL(100.0)
        model = Hagglund_1970.height_trajectory.pinus_sylvestris.sweden
        return model(
            self.pine_height_obs.height_m,
            self.pine_height_obs.age,
            target_age,
            regeneration=self.pine_regeneration,
        )

    def _beech_from_observation(self) -> SiteIndexValue | None:
        """Infer beech site index from dominant height observations."""
        if self.beech_height_obs is None or self.carbonnier_model is None:
            return None
        return self.carbonnier_model.site_index_from_height(
            height=self.beech_height_obs.height_m,
            measurement_age=self.beech_height_obs.age,
            si_age=Age.TOTAL(100.0),
        )

    def _spruce_from_swedish_site(self) -> SiteIndexValue | None:
        """Return spruce site index derived from SwedishSite if available."""
        site = self._resolved_swedish_site()
        if site is None:
            return None
        spruce_si = getattr(site, "sis_spruce_100", None)
        if spruce_si is None:
            return None
        return self._ensure_site_index(
            spruce_si,
            species=TreeSpecies.Sweden.picea_abies,
            source_function=Hagglund_1970.height_trajectory.picea_abies.northern_sweden,
        )

    def _pine_from_swedish_site(self) -> SiteIndexValue | None:
        """Return pine site index derived from SwedishSite if available."""
        site = self._resolved_swedish_site()
        if site is None:
            return None
        pine_si = getattr(site, "sis_pine_100", None)
        if pine_si is None:
            return None
        return self._ensure_site_index(
            pine_si,
            species=TreeSpecies.Sweden.pinus_sylvestris,
            source_function=Hagglund_1970.height_trajectory.pinus_sylvestris.sweden,
        )

    def resolve_site_indices(
        self,
    ) -> tuple[SiteIndexValue | None, SiteIndexValue | None, SiteIndexValue | None]:
        """Return (spruce, pine, beech) site indices at H100."""
        spruce_si = self._ensure_site_index(
            self.spruce_site_index,
            species=TreeSpecies.Sweden.picea_abies,
            source_function=Hagglund_1970.height_trajectory.picea_abies.northern_sweden,
        )
        pine_si = self._ensure_site_index(
            self.pine_site_index,
            species=TreeSpecies.Sweden.pinus_sylvestris,
            source_function=Hagglund_1970.height_trajectory.pinus_sylvestris.sweden,
        )
        beech_si = None

        spruce_si = spruce_si or self._spruce_from_observation()
        pine_si = pine_si or self._pine_from_observation()
        beech_si = beech_si or self._beech_from_observation()

        spruce_si = spruce_si or self._spruce_from_swedish_site()
        pine_si = pine_si or self._pine_from_swedish_site()

        if spruce_si is None and pine_si is not None:
            spruce_value = leijon_pine_to_spruce(float(pine_si))
            spruce_si = SiteIndexValue(
                spruce_value,
                reference_age=Age.TOTAL(100.0),
                species={TreeSpecies.Sweden.picea_abies},
                fn=leijon_pine_to_spruce,
            )
        if pine_si is None and spruce_si is not None:
            pine_value = leijon_spruce_to_pine(float(spruce_si))
            pine_si = SiteIndexValue(
                pine_value,
                reference_age=Age.TOTAL(100.0),
                species={TreeSpecies.Sweden.pinus_sylvestris},
                fn=leijon_spruce_to_pine,
            )
        return spruce_si, pine_si, beech_si

    def to_site(self) -> EkoStandSite:
        """Create a refactored :class:`EkoStandSite` with derived site indices."""
        spruce_si, pine_si, _beech_si = self.resolve_site_indices()
        if spruce_si is None and pine_si is None:
            raise ValueError("Provide spruce or pine site index (directly or via observation).")

        return EkoStandSite(
            latitude=self._resolved_latitude(),
            altitude=self._resolved_altitude(),
            vegetation=self.vegetation_code(),
            soil_moisture=self.soil_moisture_code(),
            H100_Spruce=float(spruce_si) if spruce_si is not None else None,
            H100_Pine=float(pine_si) if pine_si is not None else None,
            region=self.resolved_region(),
            fertilised=self.fertilised,
            thinned_5y=self.thinned_5y,
            thinned=self.thinned,
            tax77=self.tax77,
            broadleaf_volume_prodmod=self.broadleaf_volume_prodmod,
            broadleaf_growth_prodmod=self.broadleaf_growth_prodmod,
        )


class EkoStandSite:
    """Replicates legacy EkoStandSite but uses translate helpers directly."""

    def __init__(
        self,
        latitude: float | None = None,
        altitude: float | None = None,
        vegetation: int | Sweden.FieldLayer | None = None,
        soil_moisture: int | Sweden.SoilMoistureEnum | None = None,
        H100_Spruce: float | None = None,
        region: str | RegionSE | None = None,
        H100_Pine: float | None = None,
        fertilised: bool = False,
        thinned_5y: bool = False,
        thinned: bool = False,
        tax77: bool = False,
        broadleaf_volume_prodmod: bool = False,
        broadleaf_growth_prodmod: bool = False,
    ) -> None:
        """Initialize site attributes required by the engine formulas.

        ``broadleaf_volume_prodmod`` selects how birch (Tabell 10c) and 'other
        broadleaf' (övrigt löv, Tabell 10f) volumes are estimated in the South. False
        (default) uses the canonical Ekö 1985 region-specific Syd functions; True
        reproduces the recovered ProdMod2 program, which applies the Nord+Mellan
        function to every region for both (its volume table is region-identical
        there). See
        :meth:`~pyforestry.sweden.blocks.eko1985.cohorts.BroadleafEngineCohort.get_volume`.
        """
        self.latitude = float(latitude or 0.0)
        self.altitude = float(altitude or 0.0)
        self.fertilised = bool(fertilised)
        self.thinned_5y = bool(thinned_5y)
        self.thinned = bool(thinned)
        self.tax77 = bool(tax77)
        self.broadleaf_volume_prodmod = bool(broadleaf_volume_prodmod)
        self.broadleaf_growth_prodmod = bool(broadleaf_growth_prodmod)

        if isinstance(region, RegionSE):
            self.region = region.value
        elif isinstance(region, str) and region in ("North", "Central", "South"):
            self.region = region
        elif isinstance(region, str) and region in ("NORRA", "MELLERSTA", "SÖDRA"):
            self.region = {"NORRA": "North", "MELLERSTA": "Central", "SÖDRA": "South"}[region]
        else:
            self.region = RegionSE.SÖDRA.value if region is None else str(region)

        if isinstance(vegetation, Sweden.FieldLayer):
            vegetation = vegetation.value.code
        self._set_fieldlayer_flags(vegetation, self.latitude)

        sm = soil_moisture
        if isinstance(sm, Sweden.SoilMoistureEnum):
            sm = sm.value.code
        self.dry_soil = sm == 1
        self.wet_soil = sm == 5

        if H100_Spruce is None and H100_Pine is None:
            raise ValueError("At least one of H100_Spruce or H100_Pine must be provided.")
        if H100_Spruce is None:
            if H100_Pine is not None and (H100_Pine < 8 or H100_Pine > 30):
                warnings.warn("SI Pine may be outside underlying material", stacklevel=2)
            H100_Spruce = leijon_pine_to_spruce(H100_Pine)
        if H100_Pine is None:
            if H100_Spruce is not None and (H100_Spruce < 8 or H100_Spruce > 33):
                warnings.warn("SI Spruce may be outside underlying material.", stacklevel=2)
            H100_Pine = leijon_spruce_to_pine(H100_Spruce)
        self.H100_Spruce = H100_Spruce
        self.H100_Pine = H100_Pine

    def _set_fieldlayer_flags(self, vegetation_code: int | None, latitude: float | None) -> None:
        """Populate the Eko 1985 vegetation indicators from the field-layer code.

        Eko 1985 (report p.98-99) collapses the Hagglund & Lundmark (1977) field
        layer into two 0/1 indicators used by the functions:

        - ``herbs_grasses_no_field_layer`` (Ö,GR): 1 for herb/grass types; in southern
          Sweden also for "no field layer".
        - ``Bilberry_or_Cowberry`` (BL,L): 1 for the bilberry/lingonberry shrub type.
        """
        if vegetation_code in (13, 14):
            self.Bilberry_or_Cowberry = True
            self.herbs_grasses_no_field_layer = False
        elif vegetation_code in (1, 2, 3, 4, 5, 6, 8, 9) or (
            vegetation_code == 7 and (latitude or 0) < 60
        ):
            self.Bilberry_or_Cowberry = False
            self.herbs_grasses_no_field_layer = True
        else:
            self.Bilberry_or_Cowberry = False
            self.herbs_grasses_no_field_layer = False


__all__ = [
    "DominantHeightObservation",
    "Eko1985SiteContext",
    "EkoStandSite",
    "RegionSE",
    "_coerce_age",
    "_coerce_species",
    "_safe_log",
    "_safe_qmd",
    "_safe_sum",
    "qmd_cm",
]
