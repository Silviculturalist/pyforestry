"""Refactored Eko 1985 stand interface built on pyforestry primitives.

This module ports the original formulas inline while exposing:
 - primitive types such as ``StandBasalArea``, ``QuadraticMeanDiameter``, and ``SiteIndexValue``,
 - site handling that uses ``SwedishSite`` metadata when available,
 - site-index derivations routed through Hägglund (1970), Carbonnier (1975),
   and the Leijon (1979) translation helpers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, MutableSequence, Sequence

from pyforestry.base.contracts import FormulaDescriptor
from pyforestry.base.helpers import (
    Age,
    AgeMeasurement,
    QuadraticMeanDiameter,
    SiteBase,
    Stand,
    StandBasalArea,
    StandVolume,
    Stems,
    TreeName,
    parse_tree_species,
)
from pyforestry.base.simulation import (
    ActionSpec,
    GrowthModel,
    Requirements,
    SimulationContext,
)
from pyforestry.simulation.contracts import SourceReference
from pyforestry.sweden.blocks.eko1985.cohorts import (
    BeechEngineCohort,
    BirchEngineCohort,
    BroadleafEngineCohort,
    OakEngineCohort,
    PineEngineCohort,
    SpruceEngineCohort,
    _engine_cohort_factory,
)
from pyforestry.sweden.blocks.eko1985.engine import (
    EngineStand,
    EngineStandPart,
)
from pyforestry.sweden.blocks.eko1985.engine import (
    _species_label as _engine_species_label,
)
from pyforestry.sweden.blocks.eko1985.site_context import (
    DominantHeightObservation,
    Eko1985SiteContext,
    EkoStandSite,
    RegionSE,
    _coerce_age,
    _coerce_species,
    _safe_log,  # noqa: F401 -- re-exported for tests
    _safe_qmd,
    _safe_sum,
    qmd_cm,
)
from pyforestry.sweden.site.swedish_site import SwedishSite

# Site/context and engine core helpers are extracted in formulas/eko1985/.
_species_label = _engine_species_label


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
        """Build a cohort from primitive numeric inputs.

        The site index used by the species' Ekö 1985 functions is a site property --
        H100 pine (dm) for pine, H100 spruce (dm) for every other species -- taken from
        the site context, not from the cohort.
        """
        sp = _coerce_species(species)
        ba = StandBasalArea(basal_area_m2_per_ha, species=sp)
        stems = Stems(stems_per_ha, species=sp)
        age = _coerce_age(age_years)
        return cls(species=sp, basal_area=ba, stems=stems, age=age)

    def update_from_engine(self, part: "EngineStandPart") -> None:
        """Refresh cohort state from an in-file engine part."""
        self.basal_area = StandBasalArea(float(part.ba), species=self.species)
        self.stems = Stems(float(part.stems), species=self.species)
        self.age = Age.TOTAL(float(part.age))
        self.qmd = _safe_qmd(self.basal_area, self.stems)
        self.hk = getattr(part, "hk", None)
        self.ba_other_species = getattr(part, "ba_other_species", None)
        qmd_other = getattr(part, "qmd_other_species", None)
        self.qmd_other_species = (
            QuadraticMeanDiameter(float(qmd_other)) if qmd_other not in (None, 0) else None
        )
        volume_val = getattr(part, "vol", None)
        if volume_val is None:
            volume_val = None
        self.volume = (
            StandVolume(volume_val, species=self.species) if volume_val is not None else None
        )
        bai = getattr(part, "bai5", None)
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

        stand_ba = self._engine_stand.stand_ba
        stand_stems = self._engine_stand.StandStems
        stand_vol = self._engine_stand.stand_vol
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
            ba=basal_area,
            qmd=qmd,
            age=age,
            stems=stems,
            hk=hk,
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
                        "basal_area": StandBasalArea(entry["ba1"], species=cohort.species),
                        "qmd": QuadraticMeanDiameter(entry["qmd1"])
                        if entry["qmd1"]
                        else QuadraticMeanDiameter(0.0),
                        "volume": StandVolume(entry["vol1"], species=cohort.species),
                        "delta_volume": StandVolume(
                            entry["vol1"] - entry["vol0"], species=cohort.species
                        )
                        if entry["vol1"] >= entry["vol0"]
                        else entry["vol1"] - entry["vol0"],
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
        """Initialize with optional site context and default cohort age."""
        self._site_context = site_context
        self._default_age = float(default_age) if default_age is not None else None

    @property
    def component_id(self) -> str:
        """Stable identifier for the Eko 1985 stand model."""
        return "eko_1985"

    @property
    def source(self) -> SourceReference:
        """Bibliographic provenance for the Eko 1985 stand model."""
        return SourceReference(
            author="Eko, P.M.",
            year=1985,
            title="En produktionsmodell for skog i Sverige",
        )

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
        """Ensure the simulation context uses aggregate inventory mode."""
        if ctx.mode != "aggregate":
            raise RuntimeError("Eko1985Model requires aggregate inventory mode.")

    def _resolve_site_context(
        self,
        *,
        site_context: Eko1985SiteContext | SwedishSite | None,
        stand_site: SiteBase | Eko1985SiteContext | None = None,
        stand_attrs: Mapping[str, Any] | None = None,
    ) -> Eko1985SiteContext:
        """Resolve a site context from explicit, stand, or default sources."""
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
        """Normalize cohort age keys to species full names."""
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
        """Validate that every cohort has an age or fallback default."""
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
        """Resolve an age for the species from the map or default."""
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
        """Fetch a metric keyed by species name, code, or TreeName."""
        if species in metrics:
            return metrics[species]
        for key in (species.full_name, species.full_name.lower(), species.code):
            if key in metrics:
                return metrics[key]
        return None

    def _single_species_from_age_map(self, age_map: Mapping[str, float]) -> TreeName:
        """Return the single species in the age map, raising on ambiguity."""
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
        """Build cohorts from aggregate metrics and age information."""
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
        """Extract cohort ages keyed by species name."""
        ages: dict[str, float] = {}
        for cohort in cohorts:
            if float(cohort.basal_area) <= 0 or float(cohort.stems) <= 0:
                continue
            ages[cohort.species.full_name] = float(cohort.age)
        return ages

    def _write_metrics(self, ctx: "SimulationContext", cohorts: Sequence[Eko1985Cohort]) -> None:
        """Write aggregate metrics to the context from cohorts."""
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


__all__ = [
    "qmd_cm",
    "_safe_sum",
    "RegionSE",
    "DominantHeightObservation",
    "Eko1985Cohort",
    "Eko1985SiteContext",
    "EkoStandSite",
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


DESCRIPTOR = FormulaDescriptor(
    component_id="eko_1985_model",
    source=SourceReference(
        author="Eko, P.M.",
        year=1985,
        title="En produktionsmodell for skog i Sverige",
    ),
    kind="model",
    domain="growth",
    composes=(),
    kernel_names=("Eko1985Model",),
)
