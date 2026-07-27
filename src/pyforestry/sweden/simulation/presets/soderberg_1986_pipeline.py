"""Composite Sweden stand-simulation preset using Söderberg (1986) mature growth.

This preset runs the same period as ``Elfving2010Pipeline`` -- the same eleven
phases in the same order, inherited rather than restated -- and changes what the
mature-growth phase steps with. Söderberg (1986) has no equivalent of Elfving's
stand-level basal-area correction, so mature growth comes straight from the tree
equations.

Everything else it overrides is a consequence of that swap:

* the growth model reads ``ctx.attrs`` rather than a typed ``Inputs``, so
  :meth:`Soderberg1986Pipeline._model_attrs` supplies the canonical set and
  :meth:`Soderberg1986Pipeline._model_inputs` returns ``None``;
* ``use_soderberg_form_height_volume`` swaps the reported volume for the Söderberg
  form height, which also means giving up bucking -- see
  :meth:`Soderberg1986Pipeline.value_standing_forest`.

That the eleven phases carried over unchanged is the check that the decomposition
is an abstraction rather than one model's method list; a test asserts the two
pipelines publish the same phases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from pyforestry.base.contracts import Describable, SourceReference
from pyforestry.base.helpers import Tree
from pyforestry.base.helpers.tree_species import TreeName, TreeSpecies
from pyforestry.sweden.adapters.soderberg_1986_growth import (
    Soderberg1986Config,
    Soderberg1986Model,
)
from pyforestry.sweden.site import Sweden
from pyforestry.sweden.volume.soderberg_1986_form_height import soderberg_1986_volume_m3

from .elfving_2010_pipeline import (
    _SPRUCE_SET,
    Elfving2010Pipeline,
    Elfving2010PipelineConfig,
    _ValuationTotals,
)

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
    #: Report volume from the Söderberg (1986) form-height equations instead of
    #: bucking each tree. This also replaces the valuation: a form height gives a
    #: whole-stem volume with no assortments to price, so everything is priced as
    #: pulpwood and nothing is reported as timber. See
    #: :meth:`Soderberg1986Pipeline.value_standing_forest`.
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
        """Estimate standing value and volume for the living trees.

        With ``use_soderberg_form_height_volume`` unset -- the default -- this is
        the inherited valuation: Näsberg (1985) bucking against the Mellanskog 2013
        price list, with a Brandel volume for stems too small to buck.

        Setting it swaps *both* halves, not just the volume function the name
        mentions. Volume comes from the Söderberg (1986) form-height equations, and
        because a form height gives a whole-stem volume with no assortments to price
        it, every cubic metre is then priced as pulpwood. So this route reports no
        timber volume and no timber-valued stems -- correctly, since it bucks
        nothing -- and its ``value_per_m3_sek`` is close to flat. It is a
        volume-comparison mode, not a second valuation.

        The bark bases also differ, and only one of them is stated: the inherited
        route is under bark throughout (see the base method), while the Söderberg
        form-height module does not record which basis its form heights are on.
        Comparing the two volumes assumes an answer this package does not have.
        """
        if not self.config.use_soderberg_form_height_volume:
            return super().value_standing_forest(tree_list)

        trees = tree_list if tree_list is not None else self._trees
        totals = _ValuationTotals()
        if not trees or self._site is None:
            return totals.as_row()

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

            valuation_sp = str(sp.full_name if hasattr(sp, "full_name") else sp)
            pulp_price = float(self._pricelist.Pulp.get_pulpwood_price(valuation_sp))
            totals.volume_m3_per_ha += vol * w
            # All of it, because all of it is priced as pulpwood. This used to be
            # left out of the result entirely, so the report said nought pulp volume
            # for a run that had nothing else.
            totals.pulp_volume_m3_per_ha += vol * w
            totals.value_sek_per_ha += vol * pulp_price * w

        # `timber_valued_stems_per_ha` stays zero: nothing here is bucked. It used
        # to report every stem with a diameter -- effectively `stems_per_ha` -- so
        # one column meant "stems that produced sawtimber" under the default route
        # and "stems" under this one.
        return totals.as_row()

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

    def _model_inputs(self) -> None:
        """Declare that this model has no typed inputs to resolve.

        Söderberg (1986) predates the ``Inputs`` contract in this package and reads
        ``ctx.attrs`` directly, so everything it needs is in :meth:`_model_attrs`
        instead. Returning ``None`` rather than the Elfving inputs is what stops the
        wrong model's site facts being bound to this context.
        """
        return None

    def _model_attrs(self) -> dict[str, object]:
        """The canonical attribute set the Söderberg 1986 kernels read.

        Re-read before every mature step because three of these follow the crop
        rather than the site: the dominant species, the field-estimated basal area,
        and ``site_index_species``, which picks the pine or the spruce curve from
        whichever conifer group currently carries more basal area.

        Raises:
            RuntimeError: If no site has been set.
        """
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

        return {
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
