"""Composite Sweden stand-simulation preset using Söderberg (1986) mature growth.

This preset reuses the regeneration, NYSKOG reconstruction, young-stand growth,
mortality, and valuation workflow from ``Elfving2010Pipeline`` while
swapping the mature-tree growth model to ``Soderberg1986Model``.

Söderberg (1986) does not include Elfving's stand-level basal-area correction
function. Mature growth is therefore applied directly from the tree equations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from pyforestry.base.contracts import Describable, SourceReference
from pyforestry.base.helpers import CircularPlot, Stand, Tree
from pyforestry.base.helpers.tree_species import TreeName, TreeSpecies
from pyforestry.sweden.adapters.soderberg_1986_growth import (
    Soderberg1986Config,
    Soderberg1986Model,
)
from pyforestry.sweden.site import Sweden
from pyforestry.sweden.volume.soderberg_1986_form_height import soderberg_1986_volume_m3

from .elfving_2010_pipeline import Elfving2010Pipeline, Elfving2010PipelineConfig

_SPRUCE_SET = {
    TreeSpecies.Sweden.picea_abies,
    TreeSpecies.Sweden.picea_sitchensis,
    TreeSpecies.Sweden.picea_mariana,
}

_SOUTH_EAST_COUNTIES = {
    Sweden.County.KALMAR,
    Sweden.County.UPPSALA,
    Sweden.County.STOCKHOLM,
    Sweden.County.VASTMANLAND,
    Sweden.County.SODERMANLAND,
    Sweden.County.OSTERGOTLAND,
}

_REGION5_COUNTIES = {
    Sweden.County.VASTRA_GOTALANDS,
    Sweden.County.HALLAND,
    Sweden.County.KRISTIANSTAD,
    Sweden.County.MALMOHUS,
    Sweden.County.BLEKINGE,
    Sweden.County.GOTLAND,
}

_RICH_FIELD_LAYERS = {
    Sweden.FieldLayer.HIGH_HERB_WITHOUT_SHRUBS,
    Sweden.FieldLayer.HIGH_HERB_WITH_SHRUBS_BLUEBERRY,
    Sweden.FieldLayer.HIGH_HERB_WITH_SHRUBS_LINGON,
    Sweden.FieldLayer.LOW_HERB_WITHOUT_SHRUBS,
    Sweden.FieldLayer.LOW_HERB_WITH_SHRUBS_BLUEBERRY,
    Sweden.FieldLayer.LOW_HERB_WITH_SHRUBS_LINGON,
    Sweden.FieldLayer.NO_FIELD_LAYER,
    Sweden.FieldLayer.BROADLEAVED_GRASS,
    Sweden.FieldLayer.THINLEAVED_GRASS,
    Sweden.FieldLayer.HORSETAIL,
}


@dataclass(frozen=True)
class Soderberg1986PipelineConfig(Elfving2010PipelineConfig):
    """Configuration for the Söderberg 1986 composite preset."""

    soderberg_include_thinning_effect: bool = True
    use_soderberg_form_height_volume: bool = False


class Soderberg1986Pipeline(Elfving2010Pipeline):
    """Stateful composite stand simulation using Söderberg (1986) mature growth."""

    def __init__(self, config: Soderberg1986PipelineConfig | None = None) -> None:
        """Initialize preset and replace mature growth model with Söderberg 1986."""
        resolved_config = config or Soderberg1986PipelineConfig()
        super().__init__(config=resolved_config)
        self.config = resolved_config
        self._model = Soderberg1986Model(
            config=Soderberg1986Config(
                include_thinning_effect=bool(resolved_config.soderberg_include_thinning_effect)
            )
        )

    # --- Introspection (Describable) ---

    @property
    def component_id(self) -> str:
        """Stable identifier for the Söderberg 1986 composite preset."""
        return "soderberg_1986_composite"

    @property
    def source(self) -> SourceReference:
        """Bibliographic provenance for the Söderberg 1986 composite preset."""
        return SourceReference(
            author="Söderberg, U.",
            year=1986,
            title=(
                "Funktioner för skogliga produktionsprognoser: tillväxt och formhöjd "
                "för enskilda träd av inhemska trädslag i Sverige"
            ),
            note="Rapport nr 14, institutionen för biometri och skogsindelning, "
            "Sveriges lantbruksuniversitet, Umeå. Provenance of the growth model "
            "this preset projects with. The "
            "preset itself is a pyforestry composition and carries no separate "
            "publication: it reuses the Elfving 2010 composite workflow (Elfving "
            "1982/NYSKOG reconstruction, Nyström 2000 young-stand, Elfving 2013 "
            "mortality, valuation) and swaps mature growth to Söderberg (1986). "
            "See `components` for each model's own provenance.",
        )

    @property
    def components(self) -> Sequence[Describable]:
        """Describable components composed by this preset."""
        return (self._model,)  # Soderberg1986Model (Describable)

    def value_standing_forest(self, tree_list: list[Tree] | None = None) -> dict[str, float]:
        """Estimate standing value/volume, optionally using Söderberg form height.

        When ``use_soderberg_form_height_volume`` is True, uses Söderberg (1986)
        form-height equations for volume instead of Brandel (1990). Falls back
        to the inherited Brandel-based method otherwise.
        """
        if not self.config.use_soderberg_form_height_volume:
            return super().value_standing_forest(tree_list)

        trees = tree_list if tree_list is not None else self._trees
        if not trees or self._site is None:
            return {
                "standing_value_sek_per_ha": 0.0,
                "standing_volume_m3_per_ha": 0.0,
                "value_per_m3_sek": 0.0,
                "timber_valued_stems_per_ha": 0.0,
            }

        site = self._site
        structure = self._stand_structure()
        ba_total = float(structure["ba_total"])
        max_d = float(structure["max_diameter_cm"])
        dominant_sp = structure["dominant_species"]
        si_dominant = self._site_index_for_species(dominant_sp)
        part = self._infer_part_of_sweden()
        lat = float(site.latitude)
        alt = float(site.altitude or 0.0)
        county = getattr(site, "county", None)
        maritime_flag, _ = self._climate_flags()

        total_volume_m3 = 0.0
        total_value_sek = 0.0

        for tree in trees:
            d = float(tree.diameter_cm or 0.0)
            w = float(tree.weight_n or 0.0)
            if d <= 0.0 or w <= 0.0:
                continue

            age_bh = float(tree.age or 0.0)
            sp = tree.species or TreeSpecies.Sweden.pinus_sylvestris

            try:
                vol = soderberg_1986_volume_m3(
                    species=sp,
                    diameter_cm=d,
                    age_bh_years=max(age_bh, 1.0),
                    max_diameter_cm=max(max_d, d),
                    stand_basal_area_m2_ha=max(ba_total, 0.1),
                    dominant_species=dominant_sp,
                    site_index_dominant_m=si_dominant,
                    latitude_deg=lat,
                    altitude_m=alt,
                    part_of_sweden=part,
                    maritime=bool(maritime_flag),
                    south_east=bool(county in _SOUTH_EAST_COUNTIES),
                    region5=bool(county in _REGION5_COUNTIES),
                    prop_pine=float(structure.get("prop_pine", 0.0)),
                    prop_spruce=float(structure.get("prop_spruce", 0.0)),
                    prop_birch=float(structure.get("prop_birch", 0.0)),
                    prop_beech=float(structure.get("prop_beech", 0.0)),
                )
            except (ValueError, ZeroDivisionError):
                continue

            total_volume_m3 += vol * w

            # Simple pulpwood valuation fallback
            valuation_sp = str(sp.full_name if hasattr(sp, "full_name") else sp)
            pulp_price = float(self._pricelist.Pulp.get_pulpwood_price(valuation_sp))
            total_value_sek += vol * pulp_price * w

        valued_stems = sum(
            float(t.weight_n or 0.0) for t in trees if float(t.diameter_cm or 0.0) > 0.0
        )
        return {
            "standing_value_sek_per_ha": total_value_sek,
            "standing_volume_m3_per_ha": total_volume_m3,
            "value_per_m3_sek": (
                total_value_sek / total_volume_m3 if total_volume_m3 > 0 else 0.0
            ),
            "timber_valued_stems_per_ha": valued_stems,
        }

    def _site_index_species_for_soderberg(
        self,
        *,
        dominant_species: TreeName,
        stand_structure: dict[str, object],
    ) -> str:
        """Resolve canonical ``site_index_species`` dynamically from conifer composition."""
        prop_pine = float(stand_structure.get("prop_pine", 0.0) or 0.0)
        prop_spruce = float(stand_structure.get("prop_spruce", 0.0) or 0.0)

        if prop_spruce > prop_pine:
            return "spruce"
        if prop_pine > prop_spruce:
            return "pine"
        if prop_pine <= 0.0 and prop_spruce <= 0.0:
            return "spruce" if self.config.species_to_plant in _SPRUCE_SET else "pine"
        return "spruce" if dominant_species in _SPRUCE_SET else "pine"

    def _rebuild_context(self) -> None:
        """Rebuild Söderberg canonical context from the current in-memory tree list."""
        if self._site is None:
            raise RuntimeError("site is not set")

        stand_structure = self._stand_structure()
        dominant_species = (
            stand_structure["dominant_species"] if self._trees else self.config.species_to_plant
        )
        site_index_species = self._site_index_species_for_soderberg(
            dominant_species=dominant_species,
            stand_structure=stand_structure,
        )

        county = getattr(self._site, "county", None)
        maritime, _continental = self._climate_flags()
        soil_texture = getattr(self._site, "soil_texture", None)
        peat = bool(soil_texture in {Sweden.SoilTextureSediment.PEAT, Sweden.SoilTextureTill.PEAT})

        plot = CircularPlot(id=1, area_m2=10000.0, trees=self._trees)
        stand = Stand(site=self._site, plots=[plot])
        ctx = self._model.build_context(stand, mode_hint="tree_list")
        ctx.attrs.update(
            {
                "part_of_sweden": self._infer_part_of_sweden(),
                "latitude_deg": float(self._site.latitude),
                "altitude_m": float(self._site.altitude or 0.0),
                "site_index_species": site_index_species,
                "site_index_pine_m": float(self.config.site_index_pine_m),
                "site_index_spruce_m": float(self.config.site_index_spruce_m),
                "maritime": bool(maritime),
                "south_east": bool(county in _SOUTH_EAST_COUNTIES),
                "region5": bool(county in _REGION5_COUNTIES),
                "rich": bool(self._site.field_layer in _RICH_FIELD_LAYERS),
                "split": False,
                "soil_moisture": self._site.soil_moisture or Sweden.SoilMoistureEnum.MESIC,
                "peat": peat,
                "fertilized_within_10_years": False,
                "thinned_0_5_years": False,
                "thinned_6_25_years": False,
                "thinning_simulated": False,
                "dominant_species": dominant_species,
                "field_estimated_basal_area_m2_ha": self._basal_area_m2_ha(self._trees),
            }
        )
        ctx.state["t"] = float(self._years_elapsed)
        self._ctx = ctx


def build_soderberg_1986_pipeline(
    config: Soderberg1986PipelineConfig | None = None,
) -> Soderberg1986Pipeline:
    """Build the Söderberg 1986 composite Sweden preset for hybrid projection."""
    return Soderberg1986Pipeline(config=config)


__all__ = [
    "Soderberg1986PipelineConfig",
    "Soderberg1986Pipeline",
    "build_soderberg_1986_pipeline",
]
