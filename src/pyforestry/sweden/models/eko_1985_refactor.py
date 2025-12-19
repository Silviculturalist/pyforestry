"""Refactored Eko 1985 stand interface built on pyforestry primitives.

This module ports the original formulas inline while exposing:
 - primitive types such as ``StandBasalArea``, ``QuadraticMeanDiameter``, and ``SiteIndexValue``,
 - site handling that uses ``SwedishSite`` metadata when available,
 - site-index derivations routed through Hägglund (1970), Carbonnier (1975),
   and the Leijon (1979) translation helpers.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from enum import Enum
from math import exp, pi
from math import log as _math_log
from typing import Any, Mapping, MutableSequence, Sequence

from pyforestry.base.helpers import (
    Age,
    AgeMeasurement,
    QuadraticMeanDiameter,
    SiteIndexValue,
    SiteBase,
    Stand,
    StandBasalArea,
    StandVolume,
    Stems,
    TreeName,
    TreeSpecies,
    parse_tree_species,
)
from pyforestry.base.simulation import (
    ActionSpec,
    GrowthModel,
    Requirements,
    SimulationContext,
)
from pyforestry.sweden.site.enums import Sweden
from pyforestry.sweden.site.swedish_site import SwedishSite
from pyforestry.sweden.siteindex.carbonnier_1975 import CarbonnierHeightModel
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970, HagglundPineRegeneration
from pyforestry.sweden.siteindex.translate import Leijon_Pine_to_Spruce, Leijon_Spruce_to_Pine

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def qmd_cm(BA_m2_per_ha: float, stems_per_ha: float) -> float:
    """Quadratic mean diameter (cm) given basal area and stem count."""
    if BA_m2_per_ha <= 0.0 or stems_per_ha <= 0.0:
        return 0.0
    return (BA_m2_per_ha * 40000.0 / (pi * stems_per_ha)) ** 0.5


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


# ---------------------------------------------------------------------------
# Enums (ported for refactor)
# ---------------------------------------------------------------------------


class RegionSE(Enum):
    NORRA = "North"
    MELLERSTA = "Central"
    SÖDRA = "South"


def _engine_cohort_factory(cohort: Eko1985Cohort, site: "EkoStandSite"):
    """Return an engine cohort instance for the given species or None."""
    species = cohort.species
    if species in {TreeSpecies.Sweden.picea_abies}:
        return SpruceEngineCohort(
            float(cohort.basal_area),
            float(cohort.stems),
            float(cohort.age),
            stand=None,
            site=site,
            species=species,
        )
    if species in {TreeSpecies.Sweden.pinus_sylvestris, TreeSpecies.Sweden.pinus_contorta}:
        return PineEngineCohort(
            float(cohort.basal_area),
            float(cohort.stems),
            float(cohort.age),
            stand=None,
            site=site,
            species=species,
        )
    genus = species.genus.name.lower()
    if genus == "betula":
        return BirchEngineCohort(
            float(cohort.basal_area),
            float(cohort.stems),
            float(cohort.age),
            stand=None,
            site=site,
            species=species,
        )
    if genus == "fagus":
        return BeechEngineCohort(
            float(cohort.basal_area),
            float(cohort.stems),
            float(cohort.age),
            stand=None,
            site=site,
            species=species,
        )
    if genus == "quercus":
        return OakEngineCohort(
            float(cohort.basal_area),
            float(cohort.stems),
            float(cohort.age),
            stand=None,
            site=site,
            species=species,
        )
    return BroadleafEngineCohort(
        float(cohort.basal_area),
        float(cohort.stems),
        float(cohort.age),
        stand=None,
        site=site,
        species=species,
    )


def _species_label(species: TreeName) -> str:
    """Return the Swedish label used by the legacy engine for a tree species."""
    if species in {TreeSpecies.Sweden.picea_abies}:
        return "Gran"
    if species in {TreeSpecies.Sweden.pinus_sylvestris, TreeSpecies.Sweden.pinus_contorta}:
        return "Tall"
    if species.genus.name.lower() == "betula":
        return "Björk"
    if species.genus.name.lower() == "fagus":
        return "Bok"
    if species.genus.name.lower() == "quercus":
        return "Ek"
    return "Öv.löv"


# ---------------------------------------------------------------------------
# Data holders
# ---------------------------------------------------------------------------


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
    spruce_site_index: SiteIndexValue | float | None = None
    pine_site_index: SiteIndexValue | float | None = None
    spruce_height_obs: DominantHeightObservation | None = None
    pine_height_obs: DominantHeightObservation | None = None
    pine_regeneration: HagglundPineRegeneration = HagglundPineRegeneration.UNKNOWN
    beech_height_obs: DominantHeightObservation | None = None
    carbonnier_model: CarbonnierHeightModel | None = None
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
        self, value: SiteIndexValue | float | None, species: TreeName, fn
    ) -> SiteIndexValue | None:
        """Normalize site index values to ``SiteIndexValue`` instances."""
        if value is None:
            return None
        if isinstance(value, SiteIndexValue):
            return value
        return SiteIndexValue(
            float(value),
            reference_age=Age.TOTAL(100.0),
            species={species},
            fn=fn,
        )

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
            fn=lambda *_: None,
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
            fn=lambda *_: None,
        )

    def resolve_site_indices(
        self,
    ) -> tuple[SiteIndexValue | None, SiteIndexValue | None, SiteIndexValue | None]:
        """Return (spruce, pine, beech) site indices at H100."""
        spruce_si = self._ensure_site_index(
            self.spruce_site_index,
            species=TreeSpecies.Sweden.picea_abies,
            fn=Hagglund_1970.height_trajectory.picea_abies.northern_sweden,
        )
        pine_si = self._ensure_site_index(
            self.pine_site_index,
            species=TreeSpecies.Sweden.pinus_sylvestris,
            fn=Hagglund_1970.height_trajectory.pinus_sylvestris.sweden,
        )
        beech_si = self._ensure_site_index(
            None,  # filled below if observations exist
            species=TreeSpecies.Sweden.fagus_sylvatica,
            fn=lambda *_: None,
        )

        spruce_si = spruce_si or self._spruce_from_observation()
        pine_si = pine_si or self._pine_from_observation()
        beech_si = beech_si or self._beech_from_observation()

        spruce_si = spruce_si or self._spruce_from_swedish_site()
        pine_si = pine_si or self._pine_from_swedish_site()

        if spruce_si is None and pine_si is not None:
            spruce_value = Leijon_Pine_to_Spruce(float(pine_si))
            spruce_si = SiteIndexValue(
                spruce_value,
                reference_age=Age.TOTAL(100.0),
                species={TreeSpecies.Sweden.picea_abies},
                fn=Leijon_Pine_to_Spruce,
            )
        if pine_si is None and spruce_si is not None:
            pine_value = Leijon_Spruce_to_Pine(float(spruce_si))
            pine_si = SiteIndexValue(
                pine_value,
                reference_age=Age.TOTAL(100.0),
                species={TreeSpecies.Sweden.pinus_sylvestris},
                fn=Leijon_Spruce_to_Pine,
            )
        return spruce_si, pine_si, beech_si

    def to_site(self) -> "EkoStandSite":
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
            TAX77=self.tax77,
        )


@dataclass
class Eko1985Cohort:
    """State for a single species cohort using primitive containers."""

    species: TreeName
    basal_area: StandBasalArea
    stems: Stems
    age: AgeMeasurement
    qmd: QuadraticMeanDiameter = field(init=False)
    volume: StandVolume | None = None
    hk: float | None = None
    ba_other_species: float | None = None
    qmd_other_species: QuadraticMeanDiameter | None = None
    bai5: float | None = None
    volume_increment: StandVolume | float | None = None
    gross_volume_increment: StandVolume | float | None = None

    def __post_init__(self) -> None:
        """Compute derived cohort attributes after initialization."""
        self.qmd = _safe_qmd(float(self.basal_area), float(self.stems))

    @classmethod
    def from_values(
        cls,
        species: TreeName | str,
        basal_area_m2_per_ha: float,
        stems_per_ha: float,
        age_years: float | int | AgeMeasurement,
    ) -> Eko1985Cohort:
        """Build a cohort from primitive numeric inputs."""
        sp = _coerce_species(species)
        ba = StandBasalArea(basal_area_m2_per_ha, species=sp)
        stems = Stems(stems_per_ha, species=sp)
        age = _coerce_age(age_years)
        return cls(species=sp, basal_area=ba, stems=stems, age=age)

    def update_from_engine(self, part: "EngineStandPart") -> None:
        """Refresh cohort state from an in-file engine part."""
        self.basal_area = StandBasalArea(float(part.BA), species=self.species)
        self.stems = Stems(float(part.stems), species=self.species)
        self.age = Age.TOTAL(float(part.age))
        self.qmd = _safe_qmd(self.basal_area, self.stems)
        self.hk = getattr(part, "HK", None)
        self.ba_other_species = getattr(part, "BAOtherSpecies", None)
        qmd_other = getattr(part, "QMDOtherSpecies", None)
        self.qmd_other_species = (
            QuadraticMeanDiameter(float(qmd_other)) if qmd_other not in (None, 0) else None
        )
        volume_val = getattr(part, "VOL", None)
        if volume_val is None:
            volume_val = None
        self.volume = (
            StandVolume(volume_val, species=self.species) if volume_val is not None else None
        )
        bai = getattr(part, "BAI5", None)
        self.bai5 = float(bai) if bai is not None else None
        gvi = getattr(part, "gross_volume_increment", None)
        if gvi is None:
            self.gross_volume_increment = None
        elif float(gvi) >= 0:
            self.gross_volume_increment = StandVolume(float(gvi), species=self.species)
        else:
            self.gross_volume_increment = float(gvi)
        vi = getattr(part, "volume_increment", None)
        if vi is None:
            self.volume_increment = None
        elif float(vi) >= 0:
            self.volume_increment = StandVolume(float(vi), species=self.species)
        else:
            self.volume_increment = float(vi)


# ---------------------------------------------------------------------------
# Site definition (refactored)
# ---------------------------------------------------------------------------


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
        TAX77: bool = False,
    ) -> None:
        """Initialize site attributes required by the engine formulas."""
        self.latitude = float(latitude or 0.0)
        self.altitude = float(altitude or 0.0)
        self.fertilised = bool(fertilised)
        self.thinned_5y = bool(thinned_5y)
        self.thinned = bool(thinned)
        self.TAX77 = bool(TAX77)

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
        self._set_fieldlayer_and_vegcode(vegetation, self.latitude)

        sm = soil_moisture
        if isinstance(sm, Sweden.SoilMoistureEnum):
            sm = sm.value.code
        self.DrySoil = sm == 1
        self.WetSoil = sm == 5

        if H100_Spruce is None and H100_Pine is None:
            raise ValueError("At least one of H100_Spruce or H100_Pine must be provided.")
        if H100_Spruce is None:
            if H100_Pine is not None and (H100_Pine < 8 or H100_Pine > 30):
                warnings.warn("SI Pine may be outside underlying material", stacklevel=2)
            H100_Spruce = Leijon_Pine_to_Spruce(H100_Pine)
        if H100_Pine is None:
            if H100_Spruce is not None and (H100_Spruce < 8 or H100_Spruce > 33):
                warnings.warn("SI Spruce may be outside underlying material.", stacklevel=2)
            H100_Pine = Leijon_Spruce_to_Pine(H100_Spruce)
        self.H100_Spruce = H100_Spruce
        self.H100_Pine = H100_Pine

    def _set_fieldlayer_and_vegcode(
        self, vegetation_code: int | None, latitude: float | None
    ) -> None:
        """Populate vegetation flags and vegcode from the field-layer code."""
        if vegetation_code in (13, 14):
            self.Bilberry_or_Cowberry = True
            self.HerbsGrassesNoFieldLayer = False
        elif vegetation_code in (1, 2, 3, 4, 5, 6, 8, 9) or (
            vegetation_code == 7 and (latitude or 0) < 60
        ):
            self.Bilberry_or_Cowberry = False
            self.HerbsGrassesNoFieldLayer = True
        else:
            self.Bilberry_or_Cowberry = False
            self.HerbsGrassesNoFieldLayer = False

        mapping = {
            1: 4,
            2: 2.5,
            3: 2,
            4: 3,
            5: 2.5,
            6: 2,
            7: 3,
            8: 2.5,
            9: 1.5,
            10: -3,
            11: -3,
            12: 1,
            13: 0,
            14: -0.5,
            15: -3,
            16: -5,
            17: -0.5,
            18: -1,
        }
        if isinstance(vegetation_code, int):
            self.vegcode = mapping.get(vegetation_code, 0)
        else:
            self.vegcode = 0


# ---------------------------------------------------------------------------
# Stand wrapper
# ---------------------------------------------------------------------------


class Eko1985Stand:
    """pyforestry-primitive friendly wrapper over the refactored Eko 1985 model."""

    def __init__(self, cohorts: Sequence[Eko1985Cohort], site: Eko1985SiteContext):
        """Construct a stand wrapper from cohorts and site context."""
        if not cohorts:
            raise ValueError("At least one cohort is required to build a stand.")
        self.site = site
        self.cohorts: MutableSequence[Eko1985Cohort] = list(cohorts)
        self.period_history: list[Mapping[str, list[dict[str, Any]]]] = []

        engine_site = self.site.to_site()
        engine_parts = [_engine_cohort_factory(c, engine_site) for c in self.cohorts]
        self._engine_stand = EngineStand(parts=engine_parts, site=engine_site)
        self._engine_map = {
            id(part): cohort for cohort, part in zip(self.cohorts, engine_parts, strict=False)
        }
        self._sync_from_engine()

    # Public API -------------------------------------------------------------
    def grow(
        self, years: float = 5.0, apply_mortality: bool = True
    ) -> Mapping[str, list[dict[str, Any]]]:
        """Advance the stand, then return a summary snapshot."""
        period_raw = self._engine_stand.grow(years=years, apply_mortality=apply_mortality)
        self._sync_from_engine()
        period = self._convert_period(period_raw)
        self.period_history.append(period)
        return period

    def snapshot(self) -> Mapping[str, dict]:
        """Return primitive-rich snapshot of the current stand state."""
        per_species = {}
        for cohort in self.cohorts:
            per_species[cohort.species.full_name] = {
                "basal_area": cohort.basal_area,
                "stems": cohort.stems,
                "qmd": cohort.qmd,
                "age": cohort.age,
                "volume": cohort.volume,
                "hk": cohort.hk,
                "ba_other_species": cohort.ba_other_species,
                "qmd_other_species": cohort.qmd_other_species,
                "bai5": cohort.bai5,
                "volume_increment": cohort.volume_increment,
                "gross_volume_increment": cohort.gross_volume_increment,
            }

        stand_ba = self._engine_stand.StandBA
        stand_stems = self._engine_stand.StandStems
        stand_vol = self._engine_stand.StandVOL
        stand_qmd = _safe_qmd(stand_ba, stand_stems)
        return {
            "stand": {
                "basal_area": StandBasalArea(stand_ba),
                "stems": Stems(stand_stems),
                "qmd": stand_qmd,
                "volume": StandVolume(stand_vol),
            },
            "cohorts": per_species,
        }

    def thin(self, removals: Mapping[str | TreeName, float]) -> None:
        """Apply a constant-QMD thinning using the refactored rules.

        Keys may be TreeName instances, scientific-name strings, or legacy labels.
        """
        mapped: dict = {}
        for key, value in removals.items():
            if isinstance(key, TreeName):
                mapped[key] = value
                continue
            if isinstance(key, str):
                try:
                    mapped[parse_tree_species(key)] = value
                except ValueError:
                    mapped[key] = value
                continue
            mapped[str(key)] = value
        self._engine_stand.thin(mapped)
        self._sync_from_engine()

    def grow5(self, apply_mortality: bool = True) -> Mapping[str, list[dict[str, Any]]]:
        """Five-year convenience wrapper."""
        return self.grow(years=5, apply_mortality=apply_mortality)

    def stand_totals(self) -> dict:
        """Return stand-level totals as primitives."""
        snapshot = self.snapshot()["stand"]
        return {
            "basal_area": snapshot["basal_area"],
            "stems": snapshot["stems"],
            "qmd": snapshot["qmd"],
            "volume": snapshot["volume"],
        }

    def volume_for(
        self,
        cohort: Eko1985Cohort,
        *,
        basal_area: float | None = None,
        qmd: float | None = None,
        age: float | None = None,
        stems: float | None = None,
        hk: float | None = None,
    ) -> StandVolume:
        """Compute volume for a cohort with optional overrides."""
        idx = self.cohorts.index(cohort)
        part = self._engine_stand.parts[idx]
        vol = self._engine_stand._volume_for(
            part,
            BA=basal_area,
            QMD=qmd,
            age=age,
            stems=stems,
            HK=hk,
        )
        return StandVolume(vol, species=cohort.species)

    # Internal helpers ------------------------------------------------------
    def _sync_from_engine(self) -> None:
        """Pull updated values from the in-file engine."""
        for cohort, part in zip(self.cohorts, self._engine_stand.parts, strict=False):
            cohort.update_from_engine(part)

    def _convert_period(
        self, period_raw: Mapping[str, list[dict[str, Any]]]
    ) -> Mapping[str, list[dict[str, Any]]]:
        """Convert the in-file engine grow() payload into primitives."""
        by_species: dict[str, list] = {}
        for part in self._engine_stand.parts:
            cohort = self._engine_map.get(id(part))
            if cohort is None:
                continue
            by_species.setdefault(part.trädslag, []).append((cohort, part))

        output: dict[str, list[dict]] = {}
        for species_label, entries in period_raw.items():
            output[species_label] = []
            parts = by_species.get(species_label, [])
            for entry, pair in zip(entries, parts, strict=False):
                cohort, _part = pair
                output[species_label].append(
                    {
                        "stems": Stems(entry["N1"], species=cohort.species),
                        "basal_area": StandBasalArea(entry["BA1"], species=cohort.species),
                        "qmd": QuadraticMeanDiameter(entry["QMD1"])
                        if entry["QMD1"]
                        else QuadraticMeanDiameter(0.0),
                        "volume": StandVolume(entry["VOL1"], species=cohort.species),
                        "delta_volume": StandVolume(
                            entry["VOL1"] - entry["VOL0"], species=cohort.species
                        )
                        if entry["VOL1"] >= entry["VOL0"]
                        else entry["VOL1"] - entry["VOL0"],
                    }
                )
        return output


# ---------------------------------------------------------------------------
# Simulation adapter
# ---------------------------------------------------------------------------


class Eko1985Model(GrowthModel):
    """Simulation API adapter for the refactored Eko 1985 stand model."""

    def __init__(
        self,
        site_context: Eko1985SiteContext | None = None,
        *,
        default_age: float | None = None,
    ) -> None:
        self._site_context = site_context
        self._default_age = float(default_age) if default_age is not None else None

    def requirements(self) -> Requirements:
        """Declare aggregate inventory requirements."""
        return Requirements(inventory="aggregate")

    def build_context(
        self,
        stand: Stand,
        *,
        site_context: Eko1985SiteContext | None = None,
        cohort_ages: Mapping[TreeName | str, float] | None = None,
        default_age: float | None = None,
        **kwargs: Any,
    ) -> "SimulationContext":
        """Build an aggregate simulation context with site + cohort age metadata."""
        ctx = super().build_context(stand, mode_hint="aggregate", **kwargs)

        resolved_site = self._resolve_site_context(
            site_context=site_context,
            stand_site=stand.site,
            stand_attrs=stand.attrs,
        )
        ctx.attrs["eko_site_context"] = resolved_site

        resolved_default_age = float(default_age) if default_age is not None else self._default_age
        if resolved_default_age is not None:
            ctx.attrs["eko_default_age"] = resolved_default_age

        age_map = self._normalize_age_map(cohort_ages or stand.attrs.get("eko_1985_cohort_ages"))
        if not age_map and resolved_default_age is None:
            raise ValueError("Provide cohort_ages or default_age for Eko1985Model.")
        self._validate_age_map(ctx.metrics, age_map, resolved_default_age)
        ctx.state["cohort_ages"] = age_map
        return ctx

    def update_step(self, ctx: "SimulationContext", dt: float) -> None:
        """Advance cohorts using the Eko 1985 growth engine."""
        self._ensure_aggregate_context(ctx)
        if dt <= 0:
            raise ValueError("dt must be positive.")

        site_context = self._resolve_site_context(site_context=ctx.attrs.get("eko_site_context"))
        age_map = ctx.state.get("cohort_ages")
        if age_map is None:
            raise ValueError("cohort_ages missing; build the context with cohort ages.")

        default_age = ctx.attrs.get("eko_default_age", self._default_age)
        cohorts = self._cohorts_from_metrics(ctx.metrics, age_map, default_age)

        stand = Eko1985Stand(cohorts, site_context)
        stand.grow(years=dt)

        self._write_metrics(ctx, stand.cohorts)
        ctx.state["cohort_ages"] = self._ages_from_cohorts(stand.cohorts)
        ctx.state["years_since_thin"] = ctx.state.get("years_since_thin", 0.0) + dt

    def available_actions(self) -> dict[str, ActionSpec]:
        """Expose thinning actions compatible with aggregate inventory mode."""
        return {
            "thin_basal_area": ActionSpec(
                name="thin_basal_area",
                description="Remove basal area (m2/ha) per species or legacy label.",
                fn=self._act_thin_basal_area,
                params={"removals": "Mapping[TreeName|str, float]"},
                requires_modes=["aggregate"],
            )
        }

    def _act_thin_basal_area(
        self, ctx: "SimulationContext", removals: Mapping[str | TreeName, float]
    ) -> None:
        """Apply constant-QMD thinning to aggregate metrics."""
        self._ensure_aggregate_context(ctx)
        site_context = self._resolve_site_context(site_context=ctx.attrs.get("eko_site_context"))
        age_map = ctx.state.get("cohort_ages")
        if age_map is None:
            raise ValueError("cohort_ages missing; build the context with cohort ages.")

        default_age = ctx.attrs.get("eko_default_age", self._default_age)
        cohorts = self._cohorts_from_metrics(ctx.metrics, age_map, default_age)

        stand = Eko1985Stand(cohorts, site_context)
        stand.thin(removals)

        self._write_metrics(ctx, stand.cohorts)
        ctx.state["cohort_ages"] = self._ages_from_cohorts(stand.cohorts)
        ctx.state["years_since_thin"] = 0.0

    def _ensure_aggregate_context(self, ctx: "SimulationContext") -> None:
        if ctx.mode != "aggregate":
            raise RuntimeError("Eko1985Model requires aggregate inventory mode.")

    def _resolve_site_context(
        self,
        *,
        site_context: Eko1985SiteContext | SwedishSite | None,
        stand_site: SiteBase | Eko1985SiteContext | None = None,
        stand_attrs: Mapping[str, Any] | None = None,
    ) -> Eko1985SiteContext:
        if site_context is None and stand_attrs is not None:
            site_context = stand_attrs.get("eko_1985_site_context")
        if site_context is None and stand_site is not None:
            if isinstance(stand_site, (SwedishSite, Eko1985SiteContext)):
                site_context = stand_site
        if site_context is None:
            site_context = self._site_context

        if isinstance(site_context, Eko1985SiteContext):
            return site_context
        if isinstance(site_context, SwedishSite):
            return Eko1985SiteContext(swedish_site=site_context)
        raise ValueError("Eko1985Model requires an Eko1985SiteContext or SwedishSite.")

    def _normalize_age_map(
        self, age_map: Mapping[TreeName | str, float] | None
    ) -> dict[str, float]:
        normalized: dict[str, float] = {}
        if not age_map:
            return normalized
        for key, value in age_map.items():
            if isinstance(key, TreeName):
                normalized[key.full_name] = float(value)
                continue
            key_str = str(key)
            if key_str.upper() == "TOTAL":
                normalized["TOTAL"] = float(value)
                continue
            species = parse_tree_species(key_str)
            normalized[species.full_name] = float(value)
        return normalized

    def _validate_age_map(
        self,
        metrics: Mapping[str, Mapping[TreeName | str, Any]],
        age_map: Mapping[str, float],
        default_age: float | None,
    ) -> None:
        basals = metrics.get("BasalArea", {})
        species_keys = [key for key in basals if key != "TOTAL"]
        if not species_keys:
            if basals and ("TOTAL" in basals):
                self._single_species_from_age_map(age_map)
                return
            raise ValueError("Aggregate basal area metrics are required for Eko1985Model.")
        for key in species_keys:
            species = _coerce_species(key)
            self._resolve_age(age_map, species, default_age)

    def _resolve_age(
        self,
        age_map: Mapping[str, float],
        species: TreeName,
        default_age: float | None,
    ) -> float:
        for key in (species.full_name, species.full_name.lower(), species.code):
            if key in age_map:
                return float(age_map[key])
        if "TOTAL" in age_map:
            return float(age_map["TOTAL"])
        if default_age is not None:
            return float(default_age)
        raise ValueError(f"Missing cohort age for {species.full_name}.")

    def _metric_for_species(
        self, metrics: Mapping[TreeName | str, Any], species: TreeName
    ) -> Any | None:
        if species in metrics:
            return metrics[species]
        for key in (species.full_name, species.full_name.lower(), species.code):
            if key in metrics:
                return metrics[key]
        return None

    def _single_species_from_age_map(self, age_map: Mapping[str, float]) -> TreeName:
        species_names = [name for name in age_map if name != "TOTAL"]
        if len(species_names) != 1:
            raise ValueError(
                "Provide a single species in cohort_ages when only total metrics exist."
            )
        return parse_tree_species(species_names[0])

    def _cohorts_from_metrics(
        self,
        metrics: Mapping[str, Mapping[TreeName | str, Any]],
        age_map: Mapping[str, float],
        default_age: float | None,
    ) -> list[Eko1985Cohort]:
        basals = metrics.get("BasalArea", {})
        stems = metrics.get("Stems", {})
        if not basals or not stems:
            raise ValueError("Aggregate BasalArea and Stems metrics are required.")

        species_keys = [key for key in basals if key != "TOTAL"]
        if not species_keys:
            total_ba = basals.get("TOTAL")
            total_stems = stems.get("TOTAL")
            if total_ba is None or total_stems is None:
                raise ValueError("Aggregate totals are required to build cohorts.")
            species = self._single_species_from_age_map(age_map)
            age = self._resolve_age(age_map, species, default_age)
            return [
                Eko1985Cohort.from_values(
                    species,
                    float(total_ba),
                    float(total_stems),
                    age,
                )
            ]

        cohorts: list[Eko1985Cohort] = []
        for key in species_keys:
            species = _coerce_species(key)
            stems_val = self._metric_for_species(stems, species)
            if stems_val is None:
                raise ValueError(f"Missing stems metric for {species.full_name}.")
            age = self._resolve_age(age_map, species, default_age)
            ba_val = basals[key]
            if float(ba_val) <= 0 or float(stems_val) <= 0:
                continue
            cohorts.append(
                Eko1985Cohort.from_values(
                    species,
                    float(ba_val),
                    float(stems_val),
                    age,
                )
            )

        if not cohorts:
            raise ValueError("No cohorts with positive basal area and stem counts.")
        return cohorts

    def _ages_from_cohorts(self, cohorts: Sequence[Eko1985Cohort]) -> dict[str, float]:
        ages: dict[str, float] = {}
        for cohort in cohorts:
            if float(cohort.basal_area) <= 0 or float(cohort.stems) <= 0:
                continue
            ages[cohort.species.full_name] = float(cohort.age)
        return ages

    def _write_metrics(self, ctx: "SimulationContext", cohorts: Sequence[Eko1985Cohort]) -> None:
        stems_dict: dict[TreeName | str, Stems] = {}
        ba_dict: dict[TreeName | str, StandBasalArea] = {}
        qmd_dict: dict[TreeName | str, QuadraticMeanDiameter] = {}
        total_stems = 0.0
        total_ba = 0.0

        for cohort in cohorts:
            stems_val = float(cohort.stems)
            ba_val = float(cohort.basal_area)
            if stems_val <= 0 or ba_val <= 0:
                continue
            species = cohort.species
            stems_dict[species] = Stems(stems_val, species=species, precision=0.0)
            ba_dict[species] = StandBasalArea(ba_val, species=species, precision=0.0)
            qmd_dict[species] = QuadraticMeanDiameter(float(cohort.qmd), precision=0.0)
            total_stems += stems_val
            total_ba += ba_val

        stems_dict["TOTAL"] = Stems(total_stems, species=None, precision=0.0)
        ba_dict["TOTAL"] = StandBasalArea(total_ba, species=None, precision=0.0)
        qmd_dict["TOTAL"] = _safe_qmd(total_ba, total_stems)

        ctx._metrics = {"Stems": stems_dict, "BasalArea": ba_dict, "QMD": qmd_dict}


# ---------------------------------------------------------------------------
# In-file engine (starting with spruce)
# ---------------------------------------------------------------------------


class EngineStand:
    """Lightweight stand engine decoupled from the legacy module."""

    def __init__(self, parts, site):
        """Create the engine stand and attach cohorts to the site."""
        self.parts = parts
        self.Site = site
        self.volume_scale: float | None = None
        for p in self.parts:
            p.register_stand(self)
        self._assign_current_state_metrics()

    @staticmethod
    def getQMD(BA: float, stems: float) -> float:
        """Return quadratic mean diameter (cm) from basal area and stems."""
        if BA <= 0.0 or stems <= 0.0:
            return 0.0
        return (BA * 40000.0 / (pi * stems)) ** 0.5

    @staticmethod
    def getMAI(volume: float, total_age: float) -> float:
        """Return mean annual increment from volume and age."""
        return volume / total_age

    def _competition_metrics(self) -> None:
        """Compute competition metrics (QMD, HK) for all cohorts."""
        for p in self.parts:
            p.QMD = self.getQMD(p.BA, p.stems)
        for p in self.parts:
            BA_other = _safe_sum(q.BA for q in self.parts if q is not p)
            N_other = _safe_sum(q.stems for q in self.parts if q is not p)
            p.BAOtherSpecies = BA_other
            p.QMDOtherSpecies = self.getQMD(BA_other, N_other)
            denom = p.QMD if p.QMD > 0 else 1e-9
            p.HK = (p.QMDOtherSpecies / denom) * BA_other

    def _assign_current_state_metrics(self) -> None:
        """Recompute competition metrics, volumes, and stand totals."""
        self._competition_metrics()
        # Provide current totals before volume calls for species that reference StandBA.
        self.StandBA = _safe_sum(p.BA for p in self.parts)
        self.StandStems = _safe_sum(p.stems for p in self.parts)
        for p in self.parts:
            p.VOL = p.getVolume(BA=p.BA, QMD=p.QMD, age=p.age, stems=p.stems, HK=p.HK)
        self.StandBA = _safe_sum(p.BA for p in self.parts)
        self.StandStems = _safe_sum(p.stems for p in self.parts)
        self.StandVOL = _safe_sum(p.VOL for p in self.parts)

    def thin(self, removals: Mapping) -> None:
        """Apply constant-QMD thinning with basal-area removals."""
        for p in self.parts:
            key_variants = (
                p.species,
                p.species.full_name,
                p.species.full_name.lower(),
                p.species.code,
                p.trädslag,
                p.trädslag.lower(),
            )
            BA_out = 0.0
            for k in key_variants:
                if k in removals:
                    BA_out = float(removals[k])
                    break
            BA_out = max(0.0, min(BA_out, p.BA))
            if BA_out > 0.0 and p.QMD > 0:
                stems_out = BA_out / (pi * (p.QMD / 200.0) ** 2)
                p.BA -= BA_out
                p.stems = max(0.0, p.stems - stems_out)
        self._assign_current_state_metrics()

    def grow(self, years: float = 5.0, apply_mortality: bool = True):
        """Advance the stand by ``years`` using mortality and BAI."""
        self._assign_current_state_metrics()
        start_state = []
        for p in self.parts:
            start_state.append(
                {
                    "part": p,
                    "BA": p.BA,
                    "stems": p.stems,
                    "age": p.age,
                    "QMD": p.QMD,
                    "VOL": p.getVolume(BA=p.BA, QMD=p.QMD, age=p.age, stems=p.stems, HK=p.HK),
                }
            )
            p.VOL0 = start_state[-1]["VOL"]

        mortality = []
        for p in self.parts:
            if apply_mortality:
                BAQ_crowd, _dead_qmd_c, BAQ_other, _dead_qmd_o = p.getMortality(increment=years)
            else:
                BAQ_crowd = BAQ_other = 0.0
            p.getBAI5(
                ba_quotient_chronic_mortality=BAQ_crowd,
                ba_quotient_acute_mortality=BAQ_other,
            )
            mortality.append(
                {
                    "q_crowd": BAQ_crowd,
                    "q_other": BAQ_other,
                    "q_total": BAQ_crowd + BAQ_other,
                }
            )

        next_state = []
        for idx, p in enumerate(self.parts):
            q_total = mortality[idx]["q_total"] if apply_mortality else 0.0
            if apply_mortality:
                next_BA = (1.0 - q_total) * p.BA + p.BAI5
                next_stems = (1.0 - q_total) * p.stems
                next_age = p.age + years
            else:
                next_BA = p.BA
                next_stems = p.stems
                next_age = p.age
            next_QMD = self.getQMD(next_BA, next_stems)
            next_state.append(
                {
                    "part": p,
                    "BA": next_BA,
                    "stems": next_stems,
                    "age": next_age,
                    "QMD": next_QMD,
                }
            )

        for idx, _p in enumerate(self.parts):
            BA_other = _safe_sum(ns["BA"] for j, ns in enumerate(next_state) if j != idx)
            N_other = _safe_sum(ns["stems"] for j, ns in enumerate(next_state) if j != idx)
            QMD_other = self.getQMD(BA_other, N_other)
            HK_next = (QMD_other / (next_state[idx]["QMD"] or 1e-9)) * BA_other
            next_state[idx]["HK"] = HK_next

        for idx, p in enumerate(self.parts):
            ns = next_state[idx]
            ns["VOL"] = p.getVolume(
                BA=ns["BA"],
                QMD=ns["QMD"],
                age=ns["age"],
                stems=ns["stems"],
                HK=ns["HK"],
            )
            ns["volume_increment"] = ns["VOL"] - start_state[idx]["VOL"]

        period: dict[str, list[dict[str, float]]] = {}
        for idx, p in enumerate(self.parts):
            ns = next_state[idx]
            p.gross_volume_increment = ns["volume_increment"]
            p.volume_increment = ns["volume_increment"]
            p.BA = ns["BA"]
            p.stems = ns["stems"]
            p.QMD = ns["QMD"]
            p.age = ns["age"]
            p.HK = ns.get("HK", p.HK)
            p.VOL = ns["VOL"]
            key = p.trädslag
            period.setdefault(key, []).append(
                {
                    "N1": p.stems,
                    "BA1": p.BA,
                    "QMD1": p.QMD,
                    "VOL1": p.VOL,
                    "N0": start_state[idx]["stems"],
                    "BA0": start_state[idx]["BA"],
                    "QMD0": start_state[idx]["QMD"],
                    "VOL0": start_state[idx]["VOL"],
                }
            )

        self._assign_current_state_metrics()
        return period

    def grow5(self, apply_mortality: bool = True):
        """Five-year convenience wrapper around ``grow``."""
        return self.grow(years=5, apply_mortality=apply_mortality)

    def _volume_for(self, part, BA=None, QMD=None, age=None, stems=None, HK=None):
        """Compute a volume for a cohort with optional overrides."""
        BA = part.BA if BA is None else BA
        age = part.age if age is None else age
        stems = part.stems if stems is None else stems
        if QMD is None:
            QMD = self.getQMD(BA, stems)
        if HK is None:
            BA_other = sum(q.BA for q in self.parts if q is not part)
            N_other = sum(q.stems for q in self.parts if q is not part)
            QMD_other = self.getQMD(BA_other, N_other)
            HK = (QMD_other / QMD) * BA_other if QMD > 0 else 0.0
        return part.getVolume(BA=BA, QMD=QMD, age=age, stems=stems, HK=HK)


class EngineStandPart:
    """Minimal cohort base for the in-file engine."""

    def __init__(
        self, ba: float, stems: float, age: float, species: TreeName | str, site: EkoStandSite
    ):
        """Initialize engine cohort state."""
        self.BA = float(ba)
        self.stems = float(stems)
        self.age = float(age)
        self.species = _coerce_species(species)
        self.trädslag = _species_label(self.species)
        self.Site = site
        self.stand = None
        self.QMD = EngineStand.getQMD(self.BA, self.stems)
        self.QMDOtherSpecies = 0.0
        self.BAOtherSpecies = 0.0
        self.ba_quotient_acute_mortality = 0.0
        self.HK = 0.0
        self.VOL = 0.0
        self.BAI5 = 0.0
        self.volume_increment = 0.0
        self.gross_volume_increment = 0.0

    def register_stand(self, stand: EngineStand) -> None:
        """Attach the cohort to its parent stand."""
        self.stand = stand

    def getVolume(self, BA, QMD, age, stems, HK):  # pragma: no cover - overridden
        """Compute volume from basal area, QMD, age, stems, and HK."""
        raise NotImplementedError

    def getMortality(self, increment: int = 5):  # pragma: no cover - overridden
        """Return mortality fractions for crowding and other causes."""
        raise NotImplementedError

    def getBAI5(self, ba_quotient_chronic_mortality=0.0, ba_quotient_acute_mortality=0.0):
        """Compute basal-area increment over five years."""
        raise NotImplementedError


class SpruceEngineCohort(EngineStandPart):
    """Spruce cohort ported from the legacy EkoSpruce formulas."""

    def __init__(
        self,
        ba,
        stems,
        age,
        stand,
        site,
        species: TreeName | str | None = None,
    ):
        """Create a spruce cohort tied to the given site."""
        super().__init__(ba, stems, age, species or TreeSpecies.Sweden.picea_abies, site)
        if stand is not None:
            self.register_stand(stand)

    def getMortality(self, increment=5):
        """Return crowding and other mortality fractions for spruce."""
        if self.stand is None:
            raise ValueError("Mortality calculator requires stand connected.")
        if self.Site.region in ("North", "Central"):
            AKL = min((int(self.age) // 10) + 1, 17)
            crowding = (
                (-0.2748e-02 + 0.4493e-03 * self.BA + 0.2515e-04 * self.BA**2) * increment / 100.0
            )
            other = (-0.3150e-03 + 0.3337e-01 * AKL) / 100.0
        else:
            stems2 = min(self.stems, 2800)
            crowding = (
                (
                    0.1235e-01
                    + -0.2749e-02 * self.BA
                    + 0.8214e-04 * self.BA**2
                    + 0.2457e-04 * stems2
                    + -0.4498e-08 * stems2**2
                )
                * increment
                / 100.0
            )
            other = 0.36 / 100.0
        crowding = min(max(crowding, 0.0), 1.0)
        return crowding, 0.9 * self.QMD, other, self.QMD

    def getVolume(self, BA=None, QMD=None, age=None, stems=None, HK=None):
        """Compute spruce volume for the given stand state."""
        if self.stand is None:
            raise ValueError("Volume calculator requires stand connected.")
        BA = self.BA if BA is None else BA
        QMD = self.QMD if QMD is None else QMD
        age = self.age if age is None else age
        stems = self.stems if stems is None else stems
        HK = self.HK if HK is None else HK
        SIdm = float(self.Site.H100_Spruce or 0.0) * 10
        if self.Site.region == "North":
            b1 = -0.065
            b2 = -2.05
            F4age = 1 - exp(b1 * age)
            F4basal_area = 1 - exp(b2 * BA)
            lnVolume = (
                +0.362521e-02 * BA
                + 1.35682 * _safe_log(BA)
                - 1.47258 * QMD
                - 0.438770 * F4basal_area
                + 1.46910 * F4age
                - 0.314730 * _safe_log(stems)
                + 0.228700 * _safe_log(SIdm)
                + 0.118700e-01 * self.Site.thinned
                + 0.254896e-02 * HK
                + 1.970094
            )
            return exp(lnVolume + 0.0388)
        if self.Site.region == "Central":
            b1 = -0.065
            b2 = -2.05
            F4age = 1 - exp(b1 * age)
            F4basal_area = 1 - exp(b2 * BA)
            lnVolume = (
                +1.28359 * _safe_log(BA)
                - 0.380690 * F4basal_area
                + 1.21756 * F4age
                - 0.216690 * _safe_log(stems)
                + 0.350370 * _safe_log(SIdm)
                + 0.413000e-01 * self.Site.HerbsGrassesNoFieldLayer
                + 0.362100e-01 * self.Site.thinned
                + 0.268645e-02 * HK
                + 0.700490
            )
            return exp(lnVolume + 0.0563)
        b1 = -0.04
        b2 = -2.05
        F4age = 1 - exp(b1 * age)
        F4basal_area = 1 - exp(b2 * BA)
        lnVolume = (
            +1.22886 * _safe_log(BA)
            - 0.349820 * F4basal_area
            + 0.485170 * F4age
            - 0.152050 * _safe_log(stems)
            + 0.337640 * _safe_log(SIdm)
            + 0.129800e-01 * self.Site.thinned
            + 0.548055e-03 * HK
            + 0.584600
        )
        return exp(lnVolume + 0.0325)

    def getBAI5(self, ba_quotient_chronic_mortality=0.0, ba_quotient_acute_mortality=0.0):
        """Compute spruce basal-area increment over five years."""
        if self.stand is None:
            raise ValueError("BAI calculator requires stand connected.")
        SIdm = float(self.Site.H100_Spruce or 0.0) * 10
        if self.Site.region == "North":
            independent_vars = (
                -0.767477 * ba_quotient_chronic_mortality
                + -0.514297 * ba_quotient_acute_mortality
                + -1.43974 * self.QMD
                + -0.386338e-02 * self.HK
                + 0.204732 * self.Site.fertilised
                + 0.186343 * self.Site.vegcode
                + 0.392021e-01 * self.Site.Bilberry_or_Cowberry
                + -0.807207e-01 * self.Site.DrySoil
                + 0.833252
            )
            if SIdm < 160:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.736655e-02 * self.BA
                        + 0.875788 * _safe_log(self.BA)
                        - 0.642060e-04 * self.stems
                        + 0.125396 * _safe_log(self.stems)
                        + 0.159356e-02 * self.age
                        - 0.764340 * _safe_log(self.age)
                        - 0.594334e-02 * self.BAOtherSpecies
                    )
                else:
                    dependent_vars = (
                        -0.187226e-01 * self.BA
                        + 0.855970 * _safe_log(self.BA)
                        + 0.106942e-03 * self.stems
                        + 0.107612 * _safe_log(self.stems)
                        + 0.321033e-02 * self.age
                        - 0.737062 * _safe_log(self.age)
                        - 0.206053e-01 * self.BAOtherSpecies
                    )
            elif SIdm < 200:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.191493e-01 * self.BA
                        + 0.942389 * _safe_log(self.BA)
                        - 0.145476e-03 * self.stems
                        + 0.158511 * _safe_log(self.stems)
                        + 0.289628e-02 * self.age
                        - 0.804217 * _safe_log(self.age)
                        - 0.125949e-01 * self.BAOtherSpecies
                    )
                else:
                    dependent_vars = (
                        -0.255254e-01 * self.BA
                        + 0.955380 * _safe_log(self.BA)
                        - 0.642149e-04 * self.stems
                        + 0.164265 * _safe_log(self.stems)
                        + 0.554025e-02 * self.age
                        - 0.866520 * _safe_log(self.age)
                        - 0.889755e-02 * self.BAOtherSpecies
                    )
            else:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.210737e-01 * self.BA
                        + 0.932275 * _safe_log(self.BA)
                        - 0.572335e-04 * self.stems
                        + 0.152017 * _safe_log(self.stems)
                        + 0.342622e-02 * self.age
                        - 0.811183 * _safe_log(self.age)
                        - 0.905176e-02 * self.BAOtherSpecies
                    )
                else:
                    dependent_vars = (
                        -0.133941e-01 * self.BA
                        + 0.837783 * _safe_log(self.BA)
                        - 0.245946e-03 * self.stems
                        + 0.205142 * _safe_log(self.stems)
                        + 0.602419e-02 * self.age
                        - 0.862195 * _safe_log(self.age)
                        - 0.135941e-01 * self.BAOtherSpecies
                    )
            self.BAI5 = exp(dependent_vars + independent_vars + 0.0564)
            return
        if self.Site.region == "Central":
            independent_vars = (
                -1.16597 * ba_quotient_chronic_mortality
                + -0.299327 * ba_quotient_acute_mortality
                + 0.783806e-01 * self.Site.thinned_5y
                + 0.572131e-01 * self.Site.vegcode
                + -0.112938e-01 * self.Site.WetSoil
                + 0.546176e-01 * self.Site.latitude
                + 0.332621e-01 * self.Site.TAX77
            )
            if SIdm < 180:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.802837e-02 * self.BA
                        + 0.751220 * _safe_log(self.BA)
                        - 0.800241e-04 * self.stems
                        + 0.239814 * _safe_log(self.stems)
                        - 0.148757e-02 * self.age
                        - 0.476534 * _safe_log(self.age)
                        - 0.308451e-01 * self.BAOtherSpecies
                        - 4.02484
                    )
                else:
                    dependent_vars = (
                        -0.330623e-01 * self.BA
                        + 1.06539 * _safe_log(self.BA)
                        + 0.145290e-03 * self.stems
                        + 0.422450e-01 * _safe_log(self.stems)
                        + 0.110998e-01 * self.age
                        - 1.71468 * _safe_log(self.age)
                        - 0.236447e-01 * self.BAOtherSpecies
                        + 1.06383
                    )
            elif SIdm < 220:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.211171e-01 * self.BA
                        + 0.837241 * _safe_log(self.BA)
                        - 0.800241e-04 * self.stems
                        + 0.239814 * _safe_log(self.stems)
                        + 0.492578e-02 * self.age
                        - 0.839650 * _safe_log(self.age)
                        - 0.269523e-02 * self.BAOtherSpecies
                        - 2.91926
                    )
                else:
                    dependent_vars = (
                        -0.180419e-01 * self.BA
                        + 0.943986 * _safe_log(self.BA)
                        + 0.145290e-03 * self.stems
                        + 0.422450e-01 * _safe_log(self.stems)
                        + 0.525585e-02 * self.age
                        - 0.982261 * _safe_log(self.age)
                        - 0.786807e-02 * self.BAOtherSpecies
                        - 1.56544
                    )
            elif SIdm < 260:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.263745e-01 * self.BA
                        + 0.915196 * _safe_log(self.BA)
                        - 0.800241e-04 * self.stems
                        + 0.239814 * _safe_log(self.stems)
                        - 0.384471e-02 * self.age
                        - 0.847753 * _safe_log(self.age)
                        - 0.252559e-01 * self.BAOtherSpecies
                        + 2.85518
                    )
                else:
                    dependent_vars = (
                        -0.217674e-01 * self.BA
                        + 0.847682 * _safe_log(self.BA)
                        - 0.145290e-03 * self.stems
                        + 0.422450e-01 * _safe_log(self.stems)
                        + 0.101626e-01 * self.age
                        - 1.37782 * _safe_log(self.age)
                        - 0.268779e-01 * self.BAOtherSpecies
                        + 0.178428
                    )
            else:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.244742e-01 * self.BA
                        + 0.787195 * _safe_log(self.BA)
                        - 0.800241e-04 * self.stems
                        + 0.239814 * _safe_log(self.stems)
                        + 0.371613e-02 * self.age
                        - 0.561641 * _safe_log(self.age)
                        - 0.298097e-01 * self.BAOtherSpecies
                        - 3.17570
                    )
                else:
                    dependent_vars = (
                        -0.239679e-01 * self.BA
                        + 0.924765 * _safe_log(self.BA)
                        + 0.145290e-03 * self.stems
                        + 0.422450e-01 * _safe_log(self.stems)
                        + 0.631561e-03 * self.age
                        - 0.893401 * _safe_log(self.age)
                        - 0.908286e-02 * self.BAOtherSpecies
                        - 1.46143
                    )
            self.BAI5 = exp(dependent_vars + independent_vars + 0.0712)
            return
        independent_vars = (
            -0.780391 * ba_quotient_chronic_mortality
            + -0.252170 * ba_quotient_acute_mortality
            + -0.318464e-01 * self.Site.thinned_5y
            + 0.778093e-01 * self.Site.fertilised
            + 0.127135e-02 * SIdm
            + 0.262484e-01 * self.Site.vegcode
            + -0.736690e-01 * self.Site.DrySoil
            + -0.269193e-01 * self.Site.latitude
            + -0.959785e-01 * self.Site.TAX77
        )
        if SIdm < 220:
            if not self.Site.thinned:
                dependent_vars = (
                    -0.149200e-01 * self.BA
                    + 0.794859 * _safe_log(self.BA)
                    - 0.120956e-03 * self.stems
                    + 0.255053 * _safe_log(self.stems)
                    - 0.720252 * _safe_log(self.age)
                    - 0.229139e-01 * self.BAOtherSpecies
                    + 1.52732
                )
            else:
                dependent_vars = (
                    -0.227763e-01 * self.BA
                    + 0.838105 * _safe_log(self.BA)
                    + 0.519813e-03 * self.stems
                    + 0.141232 * _safe_log(self.stems)
                    - 0.722723 * _safe_log(self.age)
                    - 0.237689e-01 * self.BAOtherSpecies
                    + 1.93218
                )
        elif SIdm < 260:
            if not self.Site.thinned:
                dependent_vars = (
                    -0.167127e-01 * self.BA
                    + 0.794738 * _safe_log(self.BA)
                    - 0.923244e-04 * self.stems
                    + 0.279717 * _safe_log(self.stems)
                    - 0.790588 * _safe_log(self.age)
                    - 0.187801e-01 * self.BAOtherSpecies
                    + 1.67230
                )
            else:
                dependent_vars = (
                    -0.167448e-01 * self.BA
                    + 0.835811 * _safe_log(self.BA)
                    - 0.995431e-04 * self.stems
                    + 0.258612 * _safe_log(self.stems)
                    - 0.931549 * _safe_log(self.age)
                    - 0.167010e-01 * self.BAOtherSpecies
                    + 2.34225
                )
        elif SIdm < 300:
            if not self.Site.thinned:
                dependent_vars = (
                    -0.221875e-01 * self.BA
                    + 0.832287 * _safe_log(self.BA)
                    - 0.110872e-03 * self.stems
                    + 0.271386 * _safe_log(self.stems)
                    - 0.735989 * _safe_log(self.age)
                    - 0.196143e-01 * self.BAOtherSpecies
                    + 1.50310
                )
            else:
                dependent_vars = (
                    -0.203970e-01 * self.BA
                    + 0.836890 * _safe_log(self.BA)
                    - 0.755155e-04 * self.stems
                    + 0.248563 * _safe_log(self.stems)
                    - 0.716504 * _safe_log(self.age)
                    - 0.151436e-01 * self.BAOtherSpecies
                    + 1.50719
                )
        else:
            if not self.Site.thinned:
                dependent_vars = (
                    -0.243263e-01 * self.BA
                    + 0.902730 * _safe_log(self.BA)
                    - 0.706319e-04 * self.stems
                    + 0.198283 * _safe_log(self.stems)
                    - 0.713230 * _safe_log(self.age)
                    - 0.135840e-01 * self.BAOtherSpecies
                    + 1.71136
                )
            else:
                dependent_vars = (
                    -0.218319e-01 * self.BA
                    + 0.855200 * _safe_log(self.BA)
                    - 0.176554e-03 * self.stems
                    + 0.269091 * _safe_log(self.stems)
                    - 0.765104 * _safe_log(self.age)
                    - 0.180257e-01 * self.BAOtherSpecies
                    + 1.62508
                )
        self.BAI5 = exp(dependent_vars + independent_vars + 0.0737)


class PineEngineCohort(EngineStandPart):
    """Pine cohort ported from the legacy EkoPine formulas."""

    def __init__(
        self,
        ba,
        stems,
        age,
        stand,
        site,
        species: TreeName | str | None = None,
    ):
        """Create a pine cohort tied to the given site."""
        super().__init__(ba, stems, age, species or TreeSpecies.Sweden.pinus_sylvestris, site)
        if stand is not None:
            self.register_stand(stand)

    def getMortality(self, increment=5):
        """Return crowding and other mortality fractions for pine."""
        if self.stand is None:
            raise ValueError("Mortality calculator requires stand connected.")
        if self.Site.region in ("North", "Central"):
            stems2 = min(self.stems, 2700)
            crowding = (
                (
                    0.3143e-01
                    + -0.6877e-02 * self.BA
                    + 0.2056e-03 * self.BA**2
                    + 0.2684e-04 * stems2
                    + -0.5092e-08 * stems2**2
                )
                * increment
                / 100.0
            )
            other = 0.35 / 100.0
        else:
            stems2 = min(self.stems, 4000)
            crowding = (
                (
                    -0.6766e-01
                    + -0.1283e-02 * self.BA
                    + 0.7748e-04 * self.BA**2
                    + 0.1441e-03 * stems2
                    + -0.1839e-07 * stems2**2
                )
                * increment
                / 100.0
            )
            other = 0.38 / 100.0
        crowding = min(max(crowding, 0.0), 1.0)
        return crowding, 0.9 * self.QMD, other, self.QMD

    def getVolume(self, BA=None, QMD=None, age=None, stems=None, HK=None):
        """Compute pine volume for the given stand state."""
        if self.stand is None:
            raise ValueError("Volume calculator requires stand connected.")
        BA = self.BA if BA is None else BA
        QMD = self.QMD if QMD is None else QMD
        age = self.age if age is None else age
        stems = self.stems if stems is None else stems
        HK = self.HK if HK is None else HK
        SIdm = float(self.Site.H100_Pine or 0.0) * 10
        if self.Site.region == "North":
            b1 = -0.06
            b2 = -2.3
            F4age = 1 - exp(b1 * age)
            F4basal_area = 1 - exp(b2 * BA)
            lnVolume = (
                +1.24296 * _safe_log(BA)
                - 0.472530 * F4basal_area
                + 1.05864 * F4age
                - 0.170140 * _safe_log(stems)
                + 0.247550 * _safe_log(SIdm)
                + 0.213800e-01 * self.Site.thinned
                + 0.295300e-01 * self.Site.thinned_5y
                + 0.510332e-02 * HK
                + 1.08339
            )
            return exp(lnVolume + 0.0275)
        if self.Site.region == "Central":
            b1 = -0.06
            b2 = -2.2
            F4age = 1 - exp(b1 * age)
            F4basal_area = 1 - exp(b2 * BA)
            lnVolume = (
                +0.778157e-02 * BA
                + 1.14159 * _safe_log(BA)
                + 0.927460 * F4age
                - 0.166730 * _safe_log(stems)
                + 0.304900 * _safe_log(SIdm)
                + 0.270200e-01 * self.Site.thinned
                + 0.292836e-02 * HK
                + 0.910330
            )
            return exp(lnVolume + 0.0273)
        b1 = -0.075
        b2 = -2.2
        F4age = 1 - exp(b1 * age)
        F4basal_area = 1 - exp(b2 * BA)
        lnVolume = (
            +1.21272 * _safe_log(BA)
            - 0.299900 * F4basal_area
            + 1.01970 * F4age
            - 0.172300 * _safe_log(stems)
            + 0.369930 * _safe_log(SIdm)
            + 1.65136 * _safe_log(self.Site.latitude)
            + 0.349200e-01 * _safe_log(self.Site.altitude)
            - 0.197100e-01 * self.Site.HerbsGrassesNoFieldLayer
            + 0.229100e-01 * self.Site.thinned
            + 0.526017e-02 * HK
            - 6.46337
        )
        return exp(lnVolume + 0.0260)

    def getBAI5(self, ba_quotient_chronic_mortality=0.0, ba_quotient_acute_mortality=0.0):
        """Compute pine basal-area increment over five years."""
        if self.stand is None:
            raise ValueError("BAI calculator requires stand connected.")
        SIdm = float(self.Site.H100_Pine or 0.0) * 10
        if self.Site.region == "North":
            independent_vars = (
                -0.598419 * ba_quotient_chronic_mortality
                + -0.486198 * ba_quotient_acute_mortality
                + -0.952624e-02 * self.HK
                + 0.674527e-01 * self.Site.thinned_5y
                + 0.100135 * self.Site.vegcode
                + -0.104076 * self.Site.WetSoil
                + -0.329437e-01 * _safe_log(self.Site.altitude)
                + 0.526479e-01 * self.Site.TAX77
                + 0.164446
            )
            if SIdm < 160:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.342051e-01 * self.BA
                        + 0.757840 * _safe_log(self.BA)
                        - 0.161442e-03 * self.stems
                        + 0.367048 * _safe_log(self.stems)
                        + 0.313386e-02 * self.age
                        - 0.842335 * _safe_log(self.age)
                        - 0.157312e-01 * self.BAOtherSpecies
                    )
                else:
                    dependent_vars = (
                        -0.222808e-01 * self.BA
                        + 0.707173 * _safe_log(self.BA)
                        - 0.407064e-03 * self.stems
                        + 0.386522 * _safe_log(self.stems)
                        + 0.309020e-02 * self.age
                        - 0.840856 * _safe_log(self.age)
                        - 0.168721e-01 * self.BAOtherSpecies
                    )
            elif SIdm < 200:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.264194e-01 * self.BA
                        + 0.759517 * _safe_log(self.BA)
                        - 0.172838e-03 * self.stems
                        + 0.354319 * _safe_log(self.stems)
                        + 0.282339e-02 * self.age
                        - 0.830969 * _safe_log(self.age)
                        - 0.920265e-02 * self.BAOtherSpecies
                    )
                else:
                    dependent_vars = (
                        -0.215557e-01 * self.BA
                        + 0.678298 * _safe_log(self.BA)
                        - 0.223194e-03 * self.stems
                        + 0.345910 * _safe_log(self.stems)
                        + 0.230893e-02 * self.age
                        - 0.759426 * _safe_log(self.age)
                        - 0.129081e-01 * self.BAOtherSpecies
                    )
            else:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.242773e-01 * self.BA
                        + 0.743286 * _safe_log(self.BA)
                        - 0.127080e-03 * self.stems
                        + 0.328240 * _safe_log(self.stems)
                        + 0.203892e-02 * self.age
                        - 0.756105 * _safe_log(self.age)
                        - 0.136312e-01 * self.BAOtherSpecies
                    )
                else:
                    dependent_vars = (
                        -0.100435e-01 * self.BA
                        + 0.659451 * _safe_log(self.BA)
                        - 0.181913e-03 * self.stems
                        + 0.369130 * _safe_log(self.stems)
                        + 0.227817e-02 * self.age
                        - 0.793134 * _safe_log(self.age)
                        - 0.817145e-02 * self.BAOtherSpecies
                    )
            self.BAI5 = exp(dependent_vars + independent_vars + 0.0645)
            return
        if self.Site.region == "Central":
            independent_vars = (
                -0.757422 * ba_quotient_chronic_mortality
                + -0.819721 * ba_quotient_acute_mortality
                + -0.156937e-01 * self.HK
                + 0.657419e-01 * self.Site.fertilised
                + 0.208293e-02 * SIdm
                + 0.393424e-01 * self.Site.vegcode
                + -0.787040e-01 * self.Site.DrySoil
                + 0.952773e-01 * self.Site.TAX77
                - 0.466279
            )
            if SIdm < 180:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.247769e-01 * self.BA
                        + 0.739123 * _safe_log(self.BA)
                        - 0.724080e-04 * self.stems
                        + 0.307962 * _safe_log(self.stems)
                        + 0.213813e-02 * self.age
                        - 0.730167 * _safe_log(self.age)
                        - 0.304936e-02 * self.BAOtherSpecies
                    )
                else:
                    dependent_vars = (
                        -0.454216e-01 * self.BA
                        + 0.967594 * _safe_log(self.BA)
                        + 0.134748e-03 * self.stems
                        + 0.106405 * _safe_log(self.stems)
                        + 0.322181e-02 * self.age
                        - 0.559074 * _safe_log(self.age)
                        - 0.146382e-01 * self.BAOtherSpecies
                    )
            elif SIdm < 220:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.204976e-01 * self.BA
                        + 0.710569 * _safe_log(self.BA)
                        - 0.331436e-04 * self.stems
                        + 0.318007 * _safe_log(self.stems)
                        + 0.186999e-02 * self.age
                        - 0.732359 * _safe_log(self.age)
                        - 0.488064e-02 * self.BAOtherSpecies
                    )
                else:
                    dependent_vars = (
                        +0.144234e-01 * self.BA
                        + 0.304194 * _safe_log(self.BA)
                        - 0.111460e-02 * self.stems
                        + 0.628499 * _safe_log(self.stems)
                        + 0.545633e-02 * self.age
                        - 0.977317 * _safe_log(self.age)
                        - 0.126636e-01 * self.BAOtherSpecies
                    )
            else:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.242132e-01 * self.BA
                        + 0.746931 * _safe_log(self.BA)
                        - 0.120517e-03 * self.stems
                        + 0.327216 * _safe_log(self.stems)
                        + 0.254795e-02 * self.age
                        - 0.758639 * _safe_log(self.age)
                        - 0.978754e-02 * self.BAOtherSpecies
                    )
                else:
                    dependent_vars = (
                        -0.126617e-01 * self.BA
                        + 0.599420 * _safe_log(self.BA)
                        - 0.405408e-03 * self.stems
                        + 0.472836 * _safe_log(self.stems)
                        + 0.455547e-02 * self.age
                        - 0.895734 * _safe_log(self.age)
                        - 0.106365e-01 * self.BAOtherSpecies
                    )
            self.BAI5 = exp(dependent_vars + independent_vars + 0.0507)
            return
        independent_vars = (
            -1.04202 * ba_quotient_chronic_mortality
            + -0.637943 * ba_quotient_acute_mortality
            + -1.75160 * self.QMD
            + -0.592599e-02 * self.HK
            + 0.637421e-01 * self.Site.thinned_5y
            + 0.462966e-01 * self.Site.fertilised
            + 0.522489e-01 * self.Site.vegcode
            + -0.702839e-01 * self.Site.DrySoil
            + -0.111568e-01 * self.Site.latitude
            + -0.466973e-01 * self.Site.TAX77
        )
        if SIdm < 160:
            if not self.Site.thinned:
                dependent_vars = (
                    -0.497800e-01 * self.BA
                    + 1.19990 * _safe_log(self.BA)
                    + 0.114548e-04 * self.stems
                    + 0.164713 * _safe_log(self.stems)
                    - 0.884162e-03 * self.age
                    - 0.564604 * _safe_log(self.age)
                    - 0.153879e-01 * self.BAOtherSpecies
                    + 0.579562
                )
            else:
                dependent_vars = (
                    -0.302305e-01 * self.BA
                    + 0.938947 * _safe_log(self.BA)
                    + 0.563241e-03 * self.stems
                    + 0.148914 * _safe_log(self.stems)
                    + 0.419586e-02 * self.age
                    - 1.15586 * _safe_log(self.age)
                    - 0.138465e-01 * self.BAOtherSpecies
                    + 2.72773
                )
        elif SIdm < 200:
            if not self.Site.thinned:
                dependent_vars = (
                    -0.123212e-01 * self.BA
                    + 0.864851 * _safe_log(self.BA)
                    - 0.497769e-04 * self.stems
                    + 0.200066 * _safe_log(self.stems)
                    + 0.211976e-02 * self.age
                    - 0.821163 * _safe_log(self.age)
                    - 0.941390e-02 * self.BAOtherSpecies
                    + 1.59527
                )
            else:
                dependent_vars = (
                    -0.216126e-02 * self.BA
                    + 0.938131 * _safe_log(self.BA)
                    - 0.169034e-03 * self.stems
                    + 0.621225e-01 * _safe_log(self.stems)
                    + 0.305833e-02 * self.age
                    - 1.18279 * _safe_log(self.age)
                    - 0.439063e-03 * self.BAOtherSpecies
                    + 3.39954
                )
        elif SIdm < 240:
            if not self.Site.thinned:
                dependent_vars = (
                    -0.107718e-01 * self.BA
                    + 0.796896 * _safe_log(self.BA)
                    - 0.975686e-04 * self.stems
                    + 0.230066 * _safe_log(self.stems)
                    - 0.577520e-03 * self.age
                    - 0.570857 * _safe_log(self.age)
                    - 0.155230e-01 * self.BAOtherSpecies
                    + 0.784527
                )
            else:
                dependent_vars = (
                    -0.632941e-02 * self.BA
                    + 0.767710 * _safe_log(self.BA)
                    - 0.173551e-03 * self.stems
                    + 0.173044 * _safe_log(self.stems)
                    + 0.163026e-02 * self.age
                    - 0.945376 * _safe_log(self.age)
                    - 0.133437e-01 * self.BAOtherSpecies
                    + 2.49514
                )
        else:
            if not self.Site.thinned:
                dependent_vars = (
                    -0.738511e-02 * self.BA
                    + 0.809028 * _safe_log(self.BA)
                    - 0.207393e-03 * self.stems
                    + 0.199179 * _safe_log(self.stems)
                    + 0.259619e-03 * self.age
                    - 0.663161 * _safe_log(self.age)
                    - 0.142082e-01 * self.BAOtherSpecies
                    + 1.27892
                )
            else:
                dependent_vars = (
                    -0.207497e-01 * self.BA
                    + 1.00931 * _safe_log(self.BA)
                    - 0.653755e-05 * self.stems
                    + 0.851371e-01 * _safe_log(self.stems)
                    - 0.307386e-02 * self.age
                    - 0.635182 * _safe_log(self.age)
                    - 0.110970e-01 * self.BAOtherSpecies
                    + 1.57124
                )
        self.BAI5 = exp(dependent_vars + independent_vars + 0.0636)


class BirchEngineCohort(EngineStandPart):
    """Birch cohort ported from the legacy EkoBirch formulas."""

    def __init__(
        self,
        ba,
        stems,
        age,
        stand,
        site,
        species: TreeName | str | None = None,
    ):
        """Create a birch cohort tied to the given site."""
        super().__init__(ba, stems, age, species or TreeSpecies.Sweden.betula_pendula, site)
        if stand is not None:
            self.register_stand(stand)

    def getMortality(self, increment=5):
        """Return crowding and other mortality fractions for birch."""
        if self.stand is None:
            raise ValueError("Mortality calculator requires stand connected.")
        if self.Site.region in ("North", "Central"):
            crowding = (-0.2513e-01 + 0.5489e-02 * self.BA) * increment / 100.0
            other = 0.78 / 100.0
        else:
            crowding = 0.04 * increment / 100.0
            other = 0.46 / 100.0

        crowding = min(max(crowding, 0.0), 1.0)
        return crowding, 0.9 * self.QMD, other, self.QMD

    def getVolume(self, BA=None, QMD=None, age=None, stems=None, HK=None):
        """Compute birch volume for the given stand state."""
        if self.stand is None:
            raise ValueError("Volume calculator requires stand connected.")
        BA = self.BA if BA is None else BA
        QMD = self.QMD if QMD is None else QMD
        age = self.age if age is None else age
        stems = self.stems if stems is None else stems
        HK = self.HK if HK is None else HK
        SIdm = float(self.Site.H100_Spruce or 0.0) * 10

        if self.Site.region in ("North", "Central"):
            b1 = -0.035
            b2 = -2.05
            F4age = 1 - exp(b1 * age)
            F4basal_area = 1 - exp(b2 * BA)
            lnVolume = (
                +1.26244 * _safe_log(BA)
                - 0.459580 * F4basal_area
                + 0.540420 * F4age
                - 0.176040 * _safe_log(stems)
                + 0.201360 * _safe_log(SIdm)
                - 1.68251 * _safe_log(self.Site.latitude)
                - 0.404000e-01 * _safe_log(self.Site.altitude)
                + 0.757200e-01 * self.Site.fertilised
                + 0.301200e-01 * self.Site.thinned
                + 0.401844e-02 * HK
                + 8.44862
            )
            return exp(lnVolume + 0.0755)

        b1 = -0.07
        b2 = -2.1
        F4age = 1 - exp(b1 * age)
        F4basal_area = 1 - exp(b2 * BA)
        lnVolume = (
            -0.786906e-02 * BA
            + 1.35254 * _safe_log(BA)
            - 1.30862 * QMD
            - 0.524630 * F4basal_area
            + 1.01779 * F4age
            - 0.254630 * _safe_log(stems)
            + 0.204880 * _safe_log(SIdm)
            + 2.75025 * _safe_log(self.Site.latitude)
            + 0.774000e-01 * self.Site.fertilised
            + 0.434800e-01 * self.Site.thinned
            + 0.250449e-02 * HK
            - 9.38127
        )
        return exp(lnVolume + 0.0595)

    def getBAI5(self, ba_quotient_chronic_mortality=0.0, ba_quotient_acute_mortality=0.0):
        """Compute birch basal-area increment over five years."""
        if self.stand is None:
            raise ValueError("BAI calculator requires stand connected.")
        SIdm = float(self.Site.H100_Spruce or 0.0) * 10

        if self.Site.region in ("North", "Central"):
            independent_vars = (
                -0.474848 * ba_quotient_chronic_mortality
                + -0.207333 * ba_quotient_acute_mortality
                + -0.202362e-02 * self.HK
                + 0.914442e-01 * self.Site.thinned_5y
                + 0.176843 * self.Site.fertilised
                + 0.256714 * self.Site.vegcode
                + -0.488706e-01 * self.Site.WetSoil
                + -0.139928e-01 * self.Site.latitude
                + -0.462992 * self.Site.altitude
                + 0.189383 * self.Site.TAX77
            )
            if SIdm < 140:
                if not self.Site.thinned:
                    dependent_vars = (
                        +0.281210e-02 * self.BA
                        + 0.718062 * _safe_log(self.BA)
                        - 0.264120e-03 * self.stems
                        + 0.360947 * _safe_log(self.stems)
                        - 0.513560 * _safe_log(self.age)
                        - 0.146581e-01 * self.BAOtherSpecies
                        - 0.768510
                    )
                else:
                    dependent_vars = (
                        +0.856585e-01 * self.BA
                        + 0.488507 * _safe_log(self.BA)
                        - 0.549010e-03 * self.stems
                        + 0.467588 * _safe_log(self.stems)
                        - 0.618645 * _safe_log(self.age)
                        - 0.477226e-02 * self.BAOtherSpecies
                        - 0.768510
                    )
            elif SIdm < 180:
                if not self.Site.thinned:
                    dependent_vars = (
                        +0.831133e-02 * self.BA
                        + 0.660201 * _safe_log(self.BA)
                        - 0.161770e-03 * self.stems
                        + 0.361272 * _safe_log(self.stems)
                        - 0.609806 * _safe_log(self.age)
                        - 0.133204e-01 * self.BAOtherSpecies
                        - 0.355882
                    )
                else:
                    dependent_vars = (
                        +0.665931e-02 * self.BA
                        + 0.700295 * _safe_log(self.BA)
                        - 0.221485e-03 * self.stems
                        + 0.316196 * _safe_log(self.stems)
                        - 0.489888 * _safe_log(self.age)
                        - 0.246752e-01 * self.BAOtherSpecies
                        - 0.355882
                    )
            elif SIdm < 220:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.371203e-02 * self.BA
                        + 0.835899 * _safe_log(self.BA)
                        - 0.141238e-03 * self.stems
                        + 0.221611 * _safe_log(self.stems)
                        - 0.732659 * _safe_log(self.age)
                        - 0.131446e-01 * self.BAOtherSpecies
                        + 0.891049
                    )
                else:
                    dependent_vars = (
                        -0.134251e-02 * self.BA
                        + 0.838751 * _safe_log(self.BA)
                        - 0.237653e-03 * self.stems
                        + 0.192259 * _safe_log(self.stems)
                        - 0.707746 * _safe_log(self.age)
                        - 0.499067e-02 * self.BAOtherSpecies
                        + 0.891049
                    )
            else:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.281602e-01 * self.BA
                        + 0.800357 * _safe_log(self.BA)
                        + 0.673284e-04 * self.stems
                        + 0.205233 * _safe_log(self.stems)
                        - 0.631139 * _safe_log(self.age)
                        - 0.176494e-01 * self.BAOtherSpecies
                        + 0.731245
                    )
                else:
                    dependent_vars = (
                        -0.177526e-01 * self.BA
                        + 0.814686 * _safe_log(self.BA)
                        + 0.781625e-04 * self.stems
                        + 0.183532 * _safe_log(self.stems)
                        - 0.593656 * _safe_log(self.age)
                        - 0.211444e-01 * self.BAOtherSpecies
                        + 0.731245
                    )
            self.BAI5 = exp(dependent_vars + independent_vars + 0.1642)
            return

        independent_vars = (
            -0.617367 * ba_quotient_chronic_mortality
            + -0.350920 * ba_quotient_acute_mortality
            + -0.134245e-02 * self.HK
            + 0.277904 * self.Site.fertilised
            + 0.154562 * self.Site.vegcode
            + 0.554711e-01 * self.Site.TAX77
        )
        if SIdm < 220:
            if not self.Site.thinned:
                dependent_vars = (
                    -0.850224e-02 * self.BA
                    + 0.931518 * _safe_log(self.BA)
                    - 0.874696e-04 * self.stems
                    + 0.124964 * _safe_log(self.stems)
                    - 0.890226e-02 * self.age
                    - 0.498825 * _safe_log(self.age)
                    - 0.493910e-02 * self.BAOtherSpecies
                    - 0.135041
                )
            else:
                dependent_vars = (
                    +0.144427 * self.BA
                    + 0.332109 * _safe_log(self.BA)
                    - 0.457988e-03 * self.stems
                    + 0.474159 * _safe_log(self.stems)
                    + 0.922378e-02 * self.age
                    - 1.50315 * _safe_log(self.age)
                    - 0.116043e-01 * self.BAOtherSpecies
                    + 1.19213
                )
        elif SIdm < 260:
            if not self.Site.thinned:
                dependent_vars = (
                    +0.129783e-01 * self.BA
                    + 0.688150 * _safe_log(self.BA)
                    - 0.158067e-03 * self.stems
                    + 0.304149 * _safe_log(self.stems)
                    + 0.411176e-02 * self.age
                    - 0.864501 * _safe_log(self.age)
                    - 0.533730e-02 * self.BAOtherSpecies
                    - 0.135041
                )
            else:
                dependent_vars = (
                    -0.235447e-01 * self.BA
                    + 0.962877 * _safe_log(self.BA)
                    + 0.103737e-03 * self.stems
                    + 0.186790 * _safe_log(self.stems)
                    - 0.127109e-02 * self.age
                    - 1.02854 * _safe_log(self.age)
                    - 0.849201e-02 * self.BAOtherSpecies
                    + 1.19213
                )
        elif SIdm < 300:
            if not self.Site.thinned:
                dependent_vars = (
                    -0.110984e-01 * self.BA
                    + 0.748193 * _safe_log(self.BA)
                    - 0.434390e-04 * self.stems
                    + 0.270476 * _safe_log(self.stems)
                    + 0.823613e-03 * self.age
                    - 0.718419 * _safe_log(self.age)
                    - 0.174522e-01 * self.BAOtherSpecies
                    - 0.135041
                )
            else:
                dependent_vars = (
                    -0.438786e-03 * self.BA
                    + 0.818427 * _safe_log(self.BA)
                    - 0.304146e-03 * self.stems
                    + 0.241055 * _safe_log(self.stems)
                    + 0.106700e-01 * self.age
                    - 1.16385 * _safe_log(self.age)
                    - 0.1978220e-01 * self.BAOtherSpecies
                    + 1.19213
                )
        else:
            if not self.Site.thinned:
                dependent_vars = (
                    -0.204315e-01 * self.BA
                    + 0.792798 * _safe_log(self.BA)
                    - 0.179026e-03 * self.stems
                    + 0.316913 * _safe_log(self.stems)
                    + 0.262117e-02 * self.age
                    - 0.791796 * _safe_log(self.age)
                    - 0.146037e-01 * self.BAOtherSpecies
                    - 0.135041
                )
            else:
                dependent_vars = (
                    +0.255898e-02 * self.BA
                    + 0.730671 * _safe_log(self.BA)
                    + 0.256307e-04 * self.stems
                    + 0.256131 * _safe_log(self.stems)
                    + 0.126785e-01 * self.age
                    - 1.24005 * _safe_log(self.age)
                    - 0.341768e-02 * self.BAOtherSpecies
                    + 1.19213
                )
        self.BAI5 = exp(dependent_vars + independent_vars + 0.1590)


class BroadleafEngineCohort(EngineStandPart):
    """Implementation for the grouped 'other broadleaf' cohort."""

    def __init__(
        self,
        ba,
        stems,
        age,
        stand,
        site,
        species: TreeName | str | None = None,
    ):
        """Create an 'other broadleaf' cohort tied to the given site."""
        super().__init__(ba, stems, age, species or TreeSpecies.Sweden.alnus_glutinosa, site)
        if stand is not None:
            self.register_stand(stand)

    def getMortality(self, increment=5):
        """Return crowding and other mortality fractions for broadleaf."""
        if self.stand is None:
            raise ValueError("Mortality calculator requires stand connected.")
        if self.Site.region in ("North", "Central"):
            crowding = (
                (-0.7277e-02 - 0.2456e-02 * self.BA + 0.1923e-03 * self.BA**2) * increment / 100.0
            )
            other = 0.5 / 100.0
        else:
            crowding = 0.04 * increment / 100.0
            other = 0.46 / 100.0

        crowding = min(max(crowding, 0.0), 1.0)
        return crowding, 0.9 * self.QMD, other, self.QMD

    def getVolume(self, BA=None, QMD=None, age=None, stems=None, HK=None):
        """Compute broadleaf volume for the given stand state."""
        if self.stand is None:
            raise ValueError("Volume calculator requires stand connected.")
        BA = self.BA if BA is None else BA
        QMD = self.QMD if QMD is None else QMD
        age = self.age if age is None else age
        stems = self.stems if stems is None else stems
        HK = self.HK if HK is None else HK
        SIdm = float(self.Site.H100_Spruce or 0.0) * 10

        if self.Site.region in ("North", "Central"):
            b1 = -0.04
            b2 = -2.3
            F4age = 1 - exp(b1 * age)
            F4basal_area = 1 - exp(b2 * BA)
            ln_volume = (
                1.26649 * _safe_log(BA)
                - 0.580030 * F4basal_area
                + 0.486310 * F4age
                - 0.172050 * _safe_log(stems)
                + 0.174930 * _safe_log(SIdm)
                - 1.51968 * _safe_log(self.Site.latitude)
                - 0.368300e-01 * _safe_log(self.Site.altitude)
                + 0.547400e-01 * self.Site.thinned
                + 0.417126e-02 * HK
                + 7.79034
            )
            return exp(ln_volume + 0.0853)

        b1 = -0.075
        b2 = -2.1
        F4age = 1 - exp(b1 * age)
        F4basal_area = 1 - exp(b2 * BA)
        ln_volume = (
            -0.148700e-01 * BA
            + 1.29359 * _safe_log(BA)
            - 0.784820 * F4basal_area
            + 1.18741 * F4age
            - 0.135830 * _safe_log(stems)
            + 0.219890 * _safe_log(SIdm)
            + 2.02656 * _safe_log(self.Site.latitude)
            + 0.242500e-01 * self.Site.thinned
            + 0.859600e-01 * self.stand.StandBA
            + 0.509488e-03 * HK
            + 7.50102
        )
        return exp(ln_volume + 0.0671)

    def getBAI5(self, ba_quotient_chronic_mortality=0.0, ba_quotient_acute_mortality=0.0):
        """Compute broadleaf basal-area increment over five years."""
        if self.stand is None:
            raise ValueError("BAI calculator requires stand connected.")
        SIdm = float(self.Site.H100_Spruce or 0.0) * 10

        if self.Site.region in ("North", "Central"):
            independent_vars = (
                -0.345933 * ba_quotient_chronic_mortality
                - 0.138015 * self.Site.vegcode
                - 0.650878e-01 * self.Site.Bilberry_or_Cowberry
                - 0.175149e-01 * self.Site.latitude
                - 0.570035e-03 * self.Site.altitude
                + 0.151318 * self.Site.TAX77
            )
            if SIdm < 160:
                if not self.Site.thinned:
                    dependent_vars = (
                        +0.865166e-01 * self.BA
                        + 0.755603 * _safe_log(self.BA)
                        - 0.806548e-03 * self.stems
                        + 0.275974 * _safe_log(self.stems)
                        - 0.540881e-02 * self.age
                        - 0.117056 * _safe_log(self.age)
                        - 0.187866e-01 * self.BAOtherSpecies
                        - 1.18519
                    )
                else:
                    dependent_vars = (
                        +0.865166e-01 * self.BA
                        + 0.755603 * _safe_log(self.BA)
                        - 0.806548e-03 * self.stems
                        + 0.275974 * _safe_log(self.stems)
                        - 0.540881e-02 * self.age
                        - 0.117056 * _safe_log(self.age)
                        - 0.187866e-01 * self.BAOtherSpecies
                        - 0.952398
                    )
            elif SIdm < 200:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.129773e-01 * self.BA
                        + 0.989525 * _safe_log(self.BA)
                        - 0.715363e-04 * self.stems
                        + 0.490676e-01 * _safe_log(self.stems)
                        + 0.218728e-02 * self.age
                        - 0.944317 * _safe_log(self.age)
                        - 0.143834e-01 * self.BAOtherSpecies
                        + 2.78296
                    )
                else:
                    dependent_vars = (
                        -0.129773e-01 * self.BA
                        + 0.989525 * _safe_log(self.BA)
                        - 0.715363e-04 * self.stems
                        + 0.490676e-01 * _safe_log(self.stems)
                        + 0.218728e-02 * self.age
                        - 0.944317 * _safe_log(self.age)
                        - 0.143834e-01 * self.BAOtherSpecies
                        + 2.87671
                    )
            elif SIdm < 240:
                if not self.Site.thinned:
                    dependent_vars = (
                        +0.517826e-01 * self.BA
                        + 0.768565 * _safe_log(self.BA)
                        - 0.381320e-03 * self.stems
                        + 0.201267 * _safe_log(self.stems)
                        + 0.131078e-02 * self.age
                        - 0.831523 * _safe_log(self.age)
                        - 0.122796e-01 * self.BAOtherSpecies
                        + 1.65650
                    )
                else:
                    dependent_vars = (
                        +0.517826e-01 * self.BA
                        + 0.768565 * _safe_log(self.BA)
                        - 0.381320e-03 * self.stems
                        + 0.201267 * _safe_log(self.stems)
                        + 0.131078e-02 * self.age
                        - 0.831523 * _safe_log(self.age)
                        - 0.122796e-01 * self.BAOtherSpecies
                        + 1.59209
                    )
            else:
                if not self.Site.thinned:
                    dependent_vars = (
                        +0.243920e-02 * self.BA
                        + 0.857832 * _safe_log(self.BA)
                        - 0.949555e-04 * self.stems
                        + 0.192173 * _safe_log(self.stems)
                        - 0.292753e-02 * self.age
                        - 0.570009 * _safe_log(self.age)
                        - 0.240816e-01 * self.BAOtherSpecies
                        + 0.916942
                    )
                else:
                    dependent_vars = (
                        +0.243920e-02 * self.BA
                        + 0.857832 * _safe_log(self.BA)
                        - 0.949555e-04 * self.stems
                        + 0.192173 * _safe_log(self.stems)
                        - 0.292753e-02 * self.age
                        - 0.570009 * _safe_log(self.age)
                        - 0.240816e-01 * self.BAOtherSpecies
                        + 1.17865
                    )
            self.BAI5 = exp(dependent_vars + independent_vars + 0.1648)
            return

        independent_vars = (
            -1.20049 * ba_quotient_chronic_mortality
            - 0.367064 * ba_quotient_acute_mortality
            + 0.125048 * self.Site.thinned_5y
            + 0.246684 * self.Site.fertilised
            + 0.141955 * self.Site.vegcode
            + 0.354866e-01 * self.Site.latitude
            - 0.361988e-03 * self.Site.altitude
        )
        if SIdm < 240:
            if not self.Site.thinned:
                dependent_vars = (
                    +0.857153 * _safe_log(self.BA)
                    - 0.541853e-04 * self.stems
                    + 0.152684 * _safe_log(self.stems)
                    - 0.803085e-02 * self.age
                    - 0.570230 * _safe_log(self.age)
                    - 0.100518 * _safe_log(self.BAOtherSpecies)
                    - 1.93895
                )
            else:
                dependent_vars = (
                    +0.857153 * _safe_log(self.BA)
                    - 0.541853e-04 * self.stems
                    + 0.152684 * _safe_log(self.stems)
                    - 0.803085e-02 * self.age
                    - 0.570230 * _safe_log(self.age)
                    - 0.100518 * _safe_log(self.BAOtherSpecies)
                    - 2.01960
                )
        elif SIdm < 280:
            if not self.Site.thinned:
                dependent_vars = (
                    +0.794405 * _safe_log(self.BA)
                    - 0.247009 * self.stems
                    + 0.202344 * _safe_log(self.stems)
                    - 0.250423 * self.age
                    - 0.669629 * _safe_log(self.age)
                    - 0.101205 * _safe_log(self.BAOtherSpecies)
                    - 1.93895
                )
            else:
                dependent_vars = (
                    +0.794405 * _safe_log(self.BA)
                    - 0.247009 * self.stems
                    + 0.202344 * _safe_log(self.stems)
                    - 0.250423 * self.age
                    - 0.669629 * _safe_log(self.age)
                    - 0.101205 * _safe_log(self.BAOtherSpecies)
                    - 2.01960
                )
        elif SIdm < 320:
            if not self.Site.thinned:
                dependent_vars = (
                    +0.782374 * _safe_log(self.BA)
                    - 0.125111e-03 * self.stems
                    + 0.239626 * _safe_log(self.stems)
                    - 0.787146e-03 * self.age
                    - 0.733575 * _safe_log(self.age)
                    - 0.823802e-01 * _safe_log(self.BAOtherSpecies)
                    - 1.93895
                )
            else:
                dependent_vars = (
                    +0.782374 * _safe_log(self.BA)
                    - 0.125111e-03 * self.stems
                    + 0.239626 * _safe_log(self.stems)
                    - 0.787146e-03 * self.age
                    - 0.733575 * _safe_log(self.age)
                    - 0.823802e-01 * _safe_log(self.BAOtherSpecies)
                    - 2.01960
                )
        else:
            if not self.Site.thinned:
                dependent_vars = (
                    +0.771398 * _safe_log(self.BA)
                    + 0.427071e-04 * self.stems
                    + 0.167037 * _safe_log(self.stems)
                    - 0.190695e-02 * self.age
                    - 0.587696 * _safe_log(self.age)
                    - 0.113489 * _safe_log(self.BAOtherSpecies)
                    - 1.93895
                )
            else:
                dependent_vars = (
                    +0.771398 * _safe_log(self.BA)
                    + 0.427071e-04 * self.stems
                    + 0.167037 * _safe_log(self.stems)
                    - 0.190695e-02 * self.age
                    - 0.587696 * _safe_log(self.age)
                    - 0.113489 * _safe_log(self.BAOtherSpecies)
                    - 2.01960
                )
        self.BAI5 = exp(dependent_vars + independent_vars + 0.1734)


class BeechEngineCohort(EngineStandPart):
    """Beech cohort ported from the legacy EkoBeech formulas."""

    def __init__(
        self,
        ba,
        stems,
        age,
        stand,
        site,
        species: TreeName | str | None = None,
    ):
        """Create a beech cohort tied to the given site."""
        super().__init__(ba, stems, age, species or TreeSpecies.Sweden.fagus_sylvatica, site)
        if stand is not None:
            self.register_stand(stand)

    def getMortality(self, increment=5):
        """Return crowding and other mortality fractions for beech."""
        if self.stand is None:
            raise ValueError("Mortality calculator requires stand connected.")
        if self.Site.region in ("North", "Central"):
            crowding = (
                (-0.7277e-02 + -0.2456e-02 * self.BA + 0.1923e-03 * self.BA**2) * increment / 100.0
            )
            other = 0.5 / 100.0
        else:
            crowding = 0.04 * increment / 100.0
            other = 0.46 / 100.0

        crowding = min(max(crowding, 0.0), 1.0)
        return crowding, 0.9 * self.QMD, other, self.QMD

    def getVolume(self, BA=None, QMD=None, age=None, stems=None, HK=None):
        """Compute beech volume for the given stand state."""
        if self.stand is None:
            raise ValueError("Volume calculator requires stand connected.")
        BA = self.BA if BA is None else BA
        QMD = self.QMD if QMD is None else QMD
        age = self.age if age is None else age
        stems = self.stems if stems is None else stems
        HK = self.HK if HK is None else HK
        SIdm = float(self.Site.H100_Spruce or 0.0) * 10
        b1 = -0.02
        b2 = -2.3
        F4age = 1 - exp(b1 * age)
        F4basal_area = 1 - exp(b2 * BA)
        lnVolume = (
            -0.111600e-01 * BA
            + 1.30527 * _safe_log(BA)
            - 0.676190 * F4basal_area
            + 0.490740 * F4age
            - 0.151930 * _safe_log(stems)
            - 0.572600e-01 * _safe_log(SIdm)
            + 0.628000e-01 * self.Site.thinned
            + 0.203927e-02 * HK
            + 2.85509
        )
        return exp(lnVolume + 0.0392)

    def getBAI5(self, ba_quotient_chronic_mortality=0.0, ba_quotient_acute_mortality=0.0):
        """Compute beech basal-area increment over five years."""
        if self.stand is None:
            raise ValueError("BAI calculator requires stand connected.")
        SIdm = float(self.Site.H100_Spruce or 0.0) * 10

        independent_vars = -0.862301 * ba_quotient_acute_mortality + 0.162579e-02 * SIdm + 0.538943

        if SIdm < 310:
            if not self.Site.thinned:
                dependent_vars = (
                    +0.948126 * _safe_log(self.BA)
                    + 0.563620e-01 * _safe_log(self.stems)
                    - 0.751665 * _safe_log(self.age)
                    - 0.163302e-01 * self.BAOtherSpecies
                )
            else:
                dependent_vars = (
                    +0.948126 * _safe_log(self.BA)
                    + 0.563620e-01 * _safe_log(self.stems)
                    - 0.751665 * _safe_log(self.age)
                    - 0.163302e-01 * self.BAOtherSpecies
                    + 0.887110e-01
                )
        else:
            if not self.Site.thinned:
                dependent_vars = (
                    +0.821914 * _safe_log(self.BA)
                    + 0.102770 * _safe_log(self.stems)
                    - 0.753735 * _safe_log(self.age)
                    - 0.163641e-01 * self.BAOtherSpecies
                )
            else:
                dependent_vars = (
                    +0.821914 * _safe_log(self.BA)
                    + 0.102770 * _safe_log(self.stems)
                    - 0.753735 * _safe_log(self.age)
                    - 0.163641e-01 * self.BAOtherSpecies
                    + 0.887110e-01
                )

        self.BAI5 = exp(dependent_vars + independent_vars + 0.1379)


class OakEngineCohort(EngineStandPart):
    """Oak cohort ported from the legacy EkoOak formulas."""

    def __init__(
        self,
        ba,
        stems,
        age,
        stand,
        site,
        species: TreeName | str | None = None,
    ):
        """Create an oak cohort tied to the given site."""
        super().__init__(ba, stems, age, species or TreeSpecies.Sweden.quercus_robur, site)
        if stand is not None:
            self.register_stand(stand)

    def getMortality(self, increment=5):
        """Return crowding and other mortality fractions for oak."""
        if self.stand is None:
            raise ValueError("Mortality calculator requires stand connected.")
        if self.Site.region in ("North", "Central"):
            crowding = (
                (-0.7277e-02 + -0.2456e-02 * self.BA + 0.1923e-03 * self.BA**2) * increment / 100.0
            )
            other = 0.5 / 100.0
        else:
            crowding = 0.04 * increment / 100.0
            other = 0.46 / 100.0

        crowding = min(max(crowding, 0.0), 1.0)
        return crowding, 0.9 * self.QMD, other, self.QMD

    def getVolume(self, BA=None, QMD=None, age=None, stems=None, HK=None):
        """Compute oak volume for the given stand state."""
        if self.stand is None:
            raise ValueError("Volume calculator requires stand connected.")
        BA = self.BA if BA is None else BA
        QMD = self.QMD if QMD is None else QMD
        age = self.age if age is None else age
        stems = self.stems if stems is None else stems
        HK = self.HK if HK is None else HK
        SIdm = float(self.Site.H100_Spruce or 0.0) * 10
        b1 = -0.055
        b2 = -2.3
        F4age = 1 - exp(b1 * age)
        F4basal_area = 1 - exp(b2 * BA)
        lnVolume = (
            -0.106300e-01 * BA
            + 1.27353 * _safe_log(BA)
            - 0.463790 * F4basal_area
            + 0.801580 * F4age
            - 0.157080 * _safe_log(stems)
            + 0.159030 * _safe_log(SIdm)
            + 0.503200e-01 * self.Site.thinned
            + 0.188030e-02 * HK
            + 1.40608
        )
        return exp(lnVolume + 0.0756)

    def getBAI5(self, ba_quotient_chronic_mortality=0.0, ba_quotient_acute_mortality=0.0):
        """Compute oak basal-area increment over five years."""
        if self.stand is None:
            raise ValueError("BAI calculator requires stand connected.")
        SIdm = float(self.Site.H100_Spruce or 0.0) * 10

        independent_vars = -0.389169 * ba_quotient_acute_mortality - 0.609667
        if SIdm < 280:
            dependent_vars = (
                +0.896599 * _safe_log(self.BA)
                + 0.199354 * _safe_log(self.stems)
                - 0.842665 * _safe_log(self.age)
                - 0.146432e-01 * self.BAOtherSpecies
            )
        elif SIdm < 320:
            dependent_vars = (
                +0.847420 * _safe_log(self.BA)
                + 0.144495 * _safe_log(self.stems)
                - 0.727278 * _safe_log(self.age)
                - 0.222990e-01 * self.BAOtherSpecies
            )
        else:
            dependent_vars = (
                +0.851362 * _safe_log(self.BA)
                + 0.128100 * _safe_log(self.stems)
                - 0.667346 * _safe_log(self.age)
                - 0.199705e-01 * self.BAOtherSpecies
            )
        self.BAI5 = exp(dependent_vars + independent_vars + 0.1618)


__all__ = [
    "qmd_cm",
    "_safe_sum",
    "RegionSE",
    "DominantHeightObservation",
    "Eko1985Cohort",
    "Eko1985SiteContext",
    "Eko1985Stand",
    "Eko1985Model",
    "EngineStand",
    "EngineStandPart",
    "SpruceEngineCohort",
    "PineEngineCohort",
    "BirchEngineCohort",
    "BroadleafEngineCohort",
    "BeechEngineCohort",
    "OakEngineCohort",
]
