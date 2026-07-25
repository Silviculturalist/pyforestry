from __future__ import annotations

import pytest

from pyforestry.base.helpers.tree import Tree
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.blocks.elfving_1982 import (
    HuginCropTreeProbability,
    HuginMeanHeightModel,
    NfiRegion,
    NyskogReconstruction,
    RegenerationType,
)
from pyforestry.sweden.blocks.elfving_1982 import (
    nyskog_indicators_from_site as nyskog_indicators_model,
)
from pyforestry.sweden.regeneration.elfving_1982 import (
    HuginCropTreeProbabilityKernel,
    HuginMeanHeightKernel,
)
from pyforestry.sweden.regeneration.elfving_1982 import (
    _species_key as hugin_species_key,
)
from pyforestry.sweden.regeneration.elfving_1982 import (
    crop_tree_probability as hugin_crop_tree_probability_formula,
)
from pyforestry.sweden.regeneration.elfving_1982 import (
    dominant_conifer_share as nyskog_dominant_conifer_share_formula,
)
from pyforestry.sweden.regeneration.elfving_1982 import (
    height_variation as nyskog_height_variation_formula,
)
from pyforestry.sweden.regeneration.elfving_1982 import (
    mean_age as hugin_mean_age_formula,
)
from pyforestry.sweden.regeneration.elfving_1982 import (
    mean_height as hugin_mean_height_formula,
)
from pyforestry.sweden.regeneration.elfving_1982 import (
    nyskog_indicators_from_site as nyskog_indicators_formula,
)
from pyforestry.sweden.regeneration.elfving_1982 import (
    probabilities_from_tree_list as hugin_probabilities_from_tree_list_formula,
)
from pyforestry.sweden.regeneration.elfving_1982 import (
    production_potential_q as nyskog_production_potential_q_formula,
)
from pyforestry.sweden.regeneration.elfving_1982 import (
    proportion_conifer as nyskog_proportion_conifer_formula,
)
from pyforestry.sweden.regeneration.elfving_1982 import (
    reconstruct_summary as nyskog_reconstruct_summary_formula,
)
from pyforestry.sweden.regeneration.elfving_1982 import (
    secondary_mean_height as nyskog_secondary_mean_height_formula,
)
from pyforestry.sweden.regeneration.elfving_1982 import (
    stems_per_species as nyskog_stems_per_species_formula,
)
from pyforestry.sweden.regeneration.elfving_1982 import total_stems as nyskog_total_stems_formula
from pyforestry.sweden.regeneration.elfving_1982 import (
    udim_probability as nyskog_udim_probability_formula,
)
from pyforestry.sweden.regeneration.elfving_1982 import (
    weibull_parameters as nyskog_weibull_parameters_formula,
)
from pyforestry.sweden.site.enums import Sweden


def test_hugin_mean_height_wrapper_matches_formula() -> None:
    kwargs = {
        "age_years": 18.0,
        "species": TreeSpecies.Sweden.pinus_sylvestris,
        "site_index_pine_m": 22.0,
        "site_index_spruce_m": 24.0,
    }
    assert HuginMeanHeightModel.mean_height(**kwargs) == pytest.approx(
        hugin_mean_height_formula(**kwargs)
    )


def test_hugin_mean_age_wrapper_matches_formula() -> None:
    height = HuginMeanHeightModel.mean_height(
        age_years=18.0,
        species=TreeSpecies.Sweden.pinus_sylvestris,
        site_index_pine_m=22.0,
        site_index_spruce_m=24.0,
    )
    kwargs = {
        "mean_height_m": height,
        "species": TreeSpecies.Sweden.pinus_sylvestris,
        "site_index_pine_m": 22.0,
        "site_index_spruce_m": 24.0,
    }
    assert HuginMeanHeightModel.mean_age(**kwargs) == pytest.approx(
        hugin_mean_age_formula(**kwargs)
    )


def test_hugin_crop_probability_wrappers_match_formula() -> None:
    kwargs = {
        "height_m": 2.1,
        "mean_height_m": 1.6,
        "conifer_stems_per_100m2": 9.5,
        "rec_stems_per_ha": 1500.0,
        "coniferous": True,
    }
    assert HuginCropTreeProbability.crop_tree_probability(**kwargs) == pytest.approx(
        hugin_crop_tree_probability_formula(**kwargs)
    )

    trees = [
        Tree(
            species=TreeSpecies.Sweden.picea_abies,
            height_m=2.1,
            weight_n=50.0,
            diameter_cm=4.0,
        ),
        Tree(
            species=TreeSpecies.Sweden.betula_pendula,
            height_m=1.8,
            weight_n=35.0,
            diameter_cm=3.0,
        ),
    ]
    assert HuginCropTreeProbability.probabilities_from_tree_list(
        trees, rec_stems_per_ha=1500.0, expansion_factor=1.0
    ) == pytest.approx(
        hugin_probabilities_from_tree_list_formula(
            trees, rec_stems_per_ha=1500.0, expansion_factor=1.0
        )
    )


def test_nyskog_indicators_wrapper_matches_formula() -> None:
    kwargs = {
        "field_layer": Sweden.FieldLayer.BILBERRY,
        "soil_moisture": Sweden.SoilMoistureEnum.MESIC,
    }
    assert nyskog_indicators_model(**kwargs) == nyskog_indicators_formula(**kwargs)


def test_species_key_branch_mapping() -> None:
    assert hugin_species_key(TreeSpecies.Sweden.pinus_contorta) == "contorta"
    assert hugin_species_key(TreeSpecies.Sweden.larix_sibirica) == "larch"
    assert hugin_species_key(TreeSpecies.Sweden.pinus_sylvestris) == "pine"
    assert hugin_species_key(TreeSpecies.Sweden.picea_abies) == "spruce"
    assert hugin_species_key(TreeSpecies.Sweden.betula_pendula) == "birch"
    assert hugin_species_key(TreeSpecies.Sweden.populus_tremula) == "other_broadleaf"


def test_hugin_advanced_kernels_match_typed_wrappers() -> None:
    mean_inputs = {
        "age_years": 18.0,
        "species": TreeSpecies.Sweden.pinus_sylvestris,
        "site_index_pine_m": 22.0,
        "site_index_spruce_m": 24.0,
    }
    crop_inputs = {
        "height_m": 2.1,
        "mean_height_m": 1.6,
        "conifer_stems_per_100m2": 9.5,
        "rec_stems_per_ha": 1500.0,
        "coniferous": True,
    }

    mean_kernel = HuginMeanHeightKernel()
    crop_kernel = HuginCropTreeProbabilityKernel()

    assert mean_kernel.compute(mean_inputs)["mean_height_m"] == pytest.approx(
        HuginMeanHeightModel.mean_height(**mean_inputs)
    )
    assert crop_kernel.compute(crop_inputs)["crop_tree_probability"] == pytest.approx(
        HuginCropTreeProbability.crop_tree_probability(**crop_inputs)
    )


def test_nyskog_reconstruction_wrappers_match_extracted_formulas() -> None:
    asinw = 0.75
    q = NyskogReconstruction.production_potential_q(asinw)
    assert q == pytest.approx(nyskog_production_potential_q_formula(asinw))

    udim_kwargs = {"q": q, "deterministic": False, "rng": 0.2}
    assert NyskogReconstruction.udim_probability(**udim_kwargs) == pytest.approx(
        nyskog_udim_probability_formula(**udim_kwargs)
    )

    stems_kwargs = {
        "regeneration_type": RegenerationType.NATURAL,
        "mean_height_main_m": 2.1,
        "q": q,
        "ln_q": 3.1,
        "ln_si": 3.0,
        "under_dimension_prob": 0.4,
        "wet": 1,
        "dry": 0,
        "height_indicator_dm": 21.0,
        "deterministic": False,
        "noise": 0.15,
    }
    assert NyskogReconstruction.total_stems(**stems_kwargs) == pytest.approx(
        nyskog_total_stems_formula(
            regeneration_type=stems_kwargs["regeneration_type"].value,
            mean_height_main_m=stems_kwargs["mean_height_main_m"],
            q=stems_kwargs["q"],
            ln_q=stems_kwargs["ln_q"],
            ln_si=stems_kwargs["ln_si"],
            under_dimension_prob=stems_kwargs["under_dimension_prob"],
            wet=stems_kwargs["wet"],
            dry=stems_kwargs["dry"],
            height_indicator_dm=stems_kwargs["height_indicator_dm"],
            deterministic=stems_kwargs["deterministic"],
            noise=stems_kwargs["noise"],
        )
    )

    prop_kwargs = {
        "regeneration_type": RegenerationType.NATURAL,
        "q": q,
        "ln_qind": 3.8,
        "stem_total": 1700.0,
        "ln_si": 3.0,
        "wet": 1,
        "dry": 0,
        "rich": 0,
        "poor": 1,
        "deterministic": False,
        "noise": 0.2,
    }
    assert NyskogReconstruction.proportion_conifer(**prop_kwargs) == pytest.approx(
        nyskog_proportion_conifer_formula(
            regeneration_type=prop_kwargs["regeneration_type"].value,
            q=prop_kwargs["q"],
            ln_qind=prop_kwargs["ln_qind"],
            stem_total=prop_kwargs["stem_total"],
            ln_si=prop_kwargs["ln_si"],
            wet=prop_kwargs["wet"],
            dry=prop_kwargs["dry"],
            rich=prop_kwargs["rich"],
            poor=prop_kwargs["poor"],
            deterministic=prop_kwargs["deterministic"],
            noise=prop_kwargs["noise"],
        )
    )

    dom_kwargs = {
        "regeneration_type": RegenerationType.PINE_PLANTATION,
        "qind": max(45.0, q),
        "ln_si": 3.0,
        "wet": 0,
        "dry": 1,
        "rich": 0,
        "poor": 0,
        "hwod": 1,
        "hwd": 0,
        "shrubs": 1,
        "lichen": 0,
        "deterministic": False,
        "noise": 0.2,
    }
    assert NyskogReconstruction.dominant_conifer_share(**dom_kwargs) == pytest.approx(
        nyskog_dominant_conifer_share_formula(
            regeneration_type=dom_kwargs["regeneration_type"].value,
            qind=dom_kwargs["qind"],
            ln_si=dom_kwargs["ln_si"],
            wet=dom_kwargs["wet"],
            dry=dom_kwargs["dry"],
            rich=dom_kwargs["rich"],
            poor=dom_kwargs["poor"],
            hwod=dom_kwargs["hwod"],
            hwd=dom_kwargs["hwd"],
            shrubs=dom_kwargs["shrubs"],
            lichen=dom_kwargs["lichen"],
            deterministic=dom_kwargs["deterministic"],
            noise=dom_kwargs["noise"],
        )
    )

    secondary_kwargs = {
        "regeneration_type": RegenerationType.PINE_PLANTATION,
        "secondary_species": TreeSpecies.Sweden.picea_abies,
        "site_index_m": 22.0,
        "mean_height_main_m": 2.5,
        "herb": 1,
        "dry": 0,
        "wet": 0,
        "deterministic": False,
        "noise": 0.1,
    }
    assert NyskogReconstruction.secondary_mean_height(**secondary_kwargs) == pytest.approx(
        nyskog_secondary_mean_height_formula(
            regeneration_type=secondary_kwargs["regeneration_type"].value,
            secondary_species=secondary_kwargs["secondary_species"],
            site_index_m=secondary_kwargs["site_index_m"],
            mean_height_main_m=secondary_kwargs["mean_height_main_m"],
            herb=secondary_kwargs["herb"],
            dry=secondary_kwargs["dry"],
            wet=secondary_kwargs["wet"],
            deterministic=secondary_kwargs["deterministic"],
            noise=secondary_kwargs["noise"],
        )
    )

    height_var_kwargs = {
        "species": TreeSpecies.Sweden.pinus_sylvestris,
        "species_height_m": 2.1,
        "q": q,
        "ln_q": 3.1,
        "self_rejuvenated": 1,
        "deterministic": False,
        "noise": 0.2,
    }
    assert NyskogReconstruction.height_variation(**height_var_kwargs) == pytest.approx(
        nyskog_height_variation_formula(**height_var_kwargs)
    )

    weibull_kwargs = {
        "species": TreeSpecies.Sweden.pinus_sylvestris,
        "cvh": 0.55,
        "mean_height_m": 2.4,
    }
    assert NyskogReconstruction.weibull_parameters(**weibull_kwargs) == pytest.approx(
        nyskog_weibull_parameters_formula(**weibull_kwargs)
    )

    stems_kwargs = {
        "regeneration_type": RegenerationType.NATURAL,
        "species_to_plant": TreeSpecies.Sweden.pinus_sylvestris,
        "stem_total": 1800.0,
        "prop_conifer": 0.7,
        "prop_dom_conifer": 0.8,
        "site_index_m": 20.0,
        "nfi_region": NfiRegion.REG3,
    }
    assert NyskogReconstruction.stems_per_species(**stems_kwargs) == pytest.approx(
        nyskog_stems_per_species_formula(
            regeneration_type=stems_kwargs["regeneration_type"].value,
            species_to_plant=stems_kwargs["species_to_plant"],
            stem_total=stems_kwargs["stem_total"],
            prop_conifer=stems_kwargs["prop_conifer"],
            prop_dom_conifer=stems_kwargs["prop_dom_conifer"],
            site_index_m=stems_kwargs["site_index_m"],
            nfi_region=stems_kwargs["nfi_region"].value,
        )
    )

    summary_kwargs = {
        "asinw": 0.75,
        "mean_height_main_m": 2.4,
        "site_index_m": 21.0,
        "regeneration_type": RegenerationType.NATURAL,
        "species_to_plant": TreeSpecies.Sweden.pinus_sylvestris,
        "nfi_region": NfiRegion.REG3,
        "field_layer": Sweden.FieldLayer.BILBERRY,
        "soil_moisture": Sweden.SoilMoistureEnum.MESIC,
        "deterministic": False,
        "noise": 0.2,
        "rng": 0.35,
    }
    model_summary = NyskogReconstruction.reconstruct_summary(**summary_kwargs)
    formula_summary = nyskog_reconstruct_summary_formula(
        asinw=summary_kwargs["asinw"],
        mean_height_main_m=summary_kwargs["mean_height_main_m"],
        site_index_m=summary_kwargs["site_index_m"],
        regeneration_type=summary_kwargs["regeneration_type"].value,
        species_to_plant=summary_kwargs["species_to_plant"],
        nfi_region=summary_kwargs["nfi_region"].value,
        field_layer=summary_kwargs["field_layer"],
        soil_moisture=summary_kwargs["soil_moisture"],
        deterministic=summary_kwargs["deterministic"],
        noise=summary_kwargs["noise"],
        rng=summary_kwargs["rng"],
    )
    assert model_summary.q == pytest.approx(formula_summary["q"])
    assert model_summary.qind == pytest.approx(formula_summary["qind"])
    assert model_summary.udim == pytest.approx(formula_summary["udim"])
    assert model_summary.stem_total == pytest.approx(formula_summary["stem_total"])
    assert model_summary.prop_conifer == pytest.approx(formula_summary["prop_conifer"])
    assert model_summary.prop_dom_conifer == pytest.approx(formula_summary["prop_dom_conifer"])
    assert model_summary.main_species_key == formula_summary["main_species_key"]
    assert model_summary.stems_per_species == pytest.approx(formula_summary["stems_per_species"])
    assert model_summary.mean_heights_m == pytest.approx(formula_summary["mean_heights_m"])
    assert model_summary.cvh == pytest.approx(formula_summary["cvh"])
    assert model_summary.weibull_params == pytest.approx(formula_summary["weibull_params"])
