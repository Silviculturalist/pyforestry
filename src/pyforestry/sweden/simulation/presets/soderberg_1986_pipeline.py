"""Composite Sweden stand-simulation preset using Söderberg (1986) mature growth.

This preset runs the same period as the Elfving pipeline -- the same eleven
phases in the same order, both inheriting them from
:class:`~pyforestry.sweden.simulation.presets._composite.CompositePipeline` --
and changes what the mature-growth phase steps with. Söderberg (1986) has no
equivalent of Elfving's stand-level basal-area correction, so mature growth comes
straight from the tree equations.

Everything else it declares is a consequence of that swap:

* the growth model reads ``ctx.attrs`` rather than a typed ``Inputs``, so
  :meth:`Soderberg1986Pipeline._model_attrs` supplies the canonical set and
  :meth:`Soderberg1986Pipeline._model_inputs` is left at the composite's ``None``;
* ``use_soderberg_form_height_volume`` swaps the reported volume for the Söderberg
  form height, which is over bark and so has to be converted before this package's
  under-bark price lists can touch it -- see
  :meth:`Soderberg1986Pipeline.value_standing_forest`.

That the eleven phases carry over unchanged is the check that the decomposition
is an abstraction rather than one model's method list; a test asserts the two
pipelines publish the same phases. Until recently the check was weaker than it
looked, because this class inherited them from ``Elfving2010Pipeline`` itself.
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
from pyforestry.sweden.bark.soderberg_1992 import soderberg_1992_bark_thickness_bh_mm
from pyforestry.sweden.site import Sweden
from pyforestry.sweden.volume.soderberg_1986_form_height import soderberg_1986_volume_m3

from ._composite import (
    SPRUCE_SET,
    CompositePipeline,
    CompositePipelineConfig,
    ValuationTotals,
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
class Soderberg1986PipelineConfig(CompositePipelineConfig):
    """Configuration for the Söderberg 1986 composite preset.

    Extends the composite workflow's config, not the Elfving pipeline's -- which
    it used to, and so carried whatever knobs Elfving added along with it.
    """

    soderberg_include_thinning_effect: bool = True
    #: Report volume from the Söderberg (1986) form-height equations instead of
    #: bucking each tree. Nothing is bucked, so everything is priced as pulpwood; and
    #: because a form-height volume is over bark while the price lists are under
    #: bark, it is converted first, by an approximation spelled out in
    #: :meth:`Soderberg1986Pipeline._form_height_volume_under_bark_m3`.
    use_soderberg_form_height_volume: bool = False


class Soderberg1986Pipeline(CompositePipeline):
    """Stateful composite stand simulation using Söderberg (1986) mature growth."""

    def __init__(self, config: Soderberg1986PipelineConfig | None = None) -> None:
        """Initialize the composite workflow with the Söderberg 1986 growth model."""
        super().__init__(config=config or Soderberg1986PipelineConfig())

    def _build_model(self) -> Soderberg1986Model:
        """Söderberg (1986) single-tree growth, with no stand-level calibration.

        Built by the composite's ``__init__`` through this hook. It used to be
        built *after* ``super().__init__()`` had already constructed an
        ``Elfving2010Model`` and handed it to the step tuple and the mortality
        config -- one model made and discarded on every run.
        """
        return Soderberg1986Model(
            config=Soderberg1986Config(
                include_thinning_effect=bool(self.config.soderberg_include_thinning_effect)
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
            "publication: it drives the shared composite workflow (Elfving "
            "1982/NYSKOG reconstruction, Nyström 2000 young-stand, Elfving 2013 "
            "mortality, valuation) with Söderberg (1986) as the mature growth "
            "model. See `components` for each model's own provenance.",
        )

    @property
    def components(self) -> Sequence[Describable]:
        """The growth model, plus everything the composite workflow composes."""
        return (self._model, *super().components)

    def value_standing_forest(self, tree_list: list[Tree] | None = None) -> dict[str, float]:
        """Estimate standing value and volume for the living trees.

        With ``use_soderberg_form_height_volume`` unset -- the default -- this is
        the inherited valuation: Näsberg (1985) bucking against the Mellanskog 2013
        price list, with a Brandel volume for stems too small to buck.

        Setting it swaps the volume function and, with it, the pricing. Volume comes
        from the Söderberg (1986) form-height equations, which give a whole-stem
        volume with no assortments to price, so nothing is bucked: no timber volume
        and no timber-valued stems are reported, and every cubic metre is priced as
        pulpwood.

        The form height multiplies the basal area implied by breast-height diameter
        *over* bark, so its volume is over bark, while every price list here is under
        bark (``m3to`` for timber, m³fub for pulpwood). Pricing the one with the
        other overstates value by the bark fraction. The volume is therefore
        converted to under bark first, with the Söderberg (1992) double bark this
        pipeline already carries on each tree -- see
        :meth:`_form_height_volume_under_bark_m3`, which is where the approximation
        that conversion involves is written down.
        """
        if not self.config.use_soderberg_form_height_volume:
            return super().value_standing_forest(tree_list)

        trees = tree_list if tree_list is not None else self._trees
        totals = ValuationTotals()
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
        mean_age_total = self._mean_age_total_years()

        for tree in trees:
            d = float(tree.diameter_cm or 0.0)
            w = float(tree.weight_n or 0.0)
            if d <= 0.0 or w <= 0.0:
                continue

            age_bh = float(tree.age or 0.0)
            sp = tree.species or TreeSpecies.Sweden.pinus_sylvestris

            try:
                volume_over_bark_m3 = soderberg_1986_volume_m3(
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

            volume_m3 = self._form_height_volume_under_bark_m3(
                tree=tree,
                species=sp,
                volume_over_bark_m3=volume_over_bark_m3,
                diameter_cm=d,
                structure=structure,
                mean_age_total_years=mean_age_total,
            )
            if volume_m3 <= 0.0:
                continue

            valuation_sp = str(sp.full_name if hasattr(sp, "full_name") else sp)
            pulp_price = float(self._pricelist.Pulp.get_pulpwood_price(valuation_sp))
            totals.volume_m3_per_ha += volume_m3 * w
            # All of it: this route sorts nothing, so everything it values is valued
            # at the pulpwood price.
            totals.pulp_volume_m3_per_ha += volume_m3 * w
            totals.value_sek_per_ha += volume_m3 * pulp_price * w

        # `timber_volume_m3_per_ha` and `timber_valued_stems_per_ha` stay zero:
        # nothing here is bucked. The latter used to report every stem with a
        # diameter, so one column meant "stems that produced sawtimber" under the
        # inherited route and "stems" under this one.
        return totals.as_row()

    def _form_height_volume_under_bark_m3(
        self,
        *,
        tree: Tree,
        species: TreeName,
        volume_over_bark_m3: float,
        diameter_cm: float,
        structure: dict[str, object],
        mean_age_total_years: float,
    ) -> float:
        """Convert a Söderberg (1986) form-height volume to under bark.

        **This is an approximation, not a published function.** Söderberg (1986)
        gives one form height, fitted on breast-height diameter over bark, and no
        under-bark counterpart. What is done here holds that form height fixed and
        rescales the cross-section it multiplies::

            V_ub = V_ob * (d_ub / d_ob)^2,   d_ub = d_ob - double_bark / 10

        with the double bark from Söderberg (1992), which this pipeline already puts
        on every tree.

        Two things it assumes, both worth knowing before comparing the result with a
        measured volume:

        * that bark takes the same share of the cross-section all the way up the
          stem as it does at breast height. It does not -- bark thins with height --
          so this over-deducts somewhat, and the more so for thick-barked pine.
        * that form height, ``V/g``, is unchanged by the deduction. Feeding the
          under-bark diameter to the form-height equation instead would be the other
          approximation, and a worse one: the equation's diameter terms are fitted on
          over-bark diameter, so it would answer for a genuinely smaller tree rather
          than for this one with its bark off. Heureka takes an under-bark diameter
          for its Brandel volumes, but with Brandel's own published under-bark
          coefficients -- a different function, not a rescaling, and no such pair
          exists here.

        Args:
            tree: The tree, read for the ``double_bark_mm`` the pipeline set on it.
            species: Its species, already defaulted by the caller.
            volume_over_bark_m3: The form-height volume to convert.
            diameter_cm: Breast-height diameter over bark.
            structure: The stand summary the bark function needs if the tree carries
                no bark of its own.
            mean_age_total_years: Basal-area-weighted stand age, likewise.

        Returns:
            Volume under bark in m³, or ``0.0`` if bark would consume the stem.
        """
        double_bark_mm = float(getattr(tree, "double_bark_mm", 0.0) or 0.0)
        if double_bark_mm <= 0.0:
            # Every tree the pipeline itself produces has been through the
            # height-and-bark phase. A tree list handed in from outside may not have
            # been, and leaving its bark at zero would quietly put one stem's
            # over-bark volume into an under-bark total -- so compute it here from
            # the same Söderberg (1992) function that phase uses.
            double_bark_mm = soderberg_1992_bark_thickness_bh_mm(
                species=species,
                diameter_cm=diameter_cm,
                max_diameter_cm=max(float(structure["max_diameter_cm"]), diameter_cm),
                mean_age_total_years=mean_age_total_years,
                site_index_pine_m=float(self.config.site_index_pine_m),
                latitude_deg=float(self._site.latitude),
                altitude_m=float(self._site.altitude or 0.0),
                prop_pine=float(structure.get("prop_pine", 0.0)),
                prop_spruce=float(structure.get("prop_spruce", 0.0)),
                prop_birch=float(structure.get("prop_birch", 0.0)),
                part_of_sweden=self._infer_part_of_sweden(),
            )

        diameter_under_bark_cm = diameter_cm - max(0.0, double_bark_mm) / 10.0
        if diameter_under_bark_cm <= 0.0:
            return 0.0
        return float(volume_over_bark_m3) * (diameter_under_bark_cm / diameter_cm) ** 2

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
            return "spruce" if self.config.species_to_plant in SPRUCE_SET else "pine"
        return "spruce" if dominant_species in SPRUCE_SET else "pine"

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
