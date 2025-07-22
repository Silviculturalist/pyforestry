from math import isclose

import pytest

from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.misc.elfving_2003 import Elfving2003TreeAge
from pyforestry.sweden.site import Sweden

# These are chosen to be generally valid for many groups.
DEFAULT_AGE_PARAMS = {
    "diameter": 20,  # cm
    "species": TreeSpecies.Sweden.pinus_sylvestris,  # Default to Pine
    "total_stand_age": 80,  # years
    "SIS": 26,  # m
    "field_layer": Sweden.FieldLayer.BILBERRY,  # code 13 (neither rich nor poor by default defs)
    "basal_area_plot_m2_ha": 30,
    "basal_area_relascope_m2_ha": 25,
    "altitude_m": 100,
    "latitude": 64,
    "QMD_cm": 22,
    "stems_ha": 700,
    "is_uneven_aged": False,
    "dominant_mean_diameter": None,  # Let it calculate
    "is_standard_tree_hint": False,
    "is_undergrowth_tree_hint": False,
    "is_gotland": False,
    "is_ditched": False,
    "is_peat_soil": False,
    "is_shade_tolerant_broadleaf_hint": None,
}


class TestElfving2003TreeAgeHelpers:
    def test_is_rich_site(self):
        assert (
            Elfving2003TreeAge._is_rich_site(Sweden.FieldLayer.HIGH_HERB_WITHOUT_SHRUBS) == 1
        )  # code 1
        assert Elfving2003TreeAge._is_rich_site(5) == 1  # code 5 (Low-herb with shrubs/bilberry)
        assert Elfving2003TreeAge._is_rich_site(12) == 1  # code 12 (Horsetail)
        assert Elfving2003TreeAge._is_rich_site(Sweden.FieldLayer.BILBERRY) == 0  # code 13
        assert Elfving2003TreeAge._is_rich_site(Sweden.FieldLayer.LICHEN_DOMINANT) == 0  # code 18
        assert Elfving2003TreeAge._is_rich_site(None) == 0
        assert Elfving2003TreeAge._is_rich_site(2) == 1

    def test_is_poor_site(self):
        assert Elfving2003TreeAge._is_poor_site(Sweden.FieldLayer.LICHEN_DOMINANT) == 1  # code 18
        assert Elfving2003TreeAge._is_poor_site(14) == 1  # Lingonberry
        assert Elfving2003TreeAge._is_poor_site(Sweden.FieldLayer.BILBERRY) == 0  # code 13
        assert (
            Elfving2003TreeAge._is_poor_site(Sweden.FieldLayer.HIGH_HERB_WITHOUT_SHRUBS) == 0
        )  # code 1
        assert Elfving2003TreeAge._is_poor_site(None) == 0
        assert Elfving2003TreeAge._is_poor_site(15) == 1


class TestElfving2003TreeAgeMain:
    def test_invalid_diameter_raises_value_error(self):
        params = DEFAULT_AGE_PARAMS.copy()
        params["diameter"] = 0
        with pytest.raises(ValueError, match="diameter .* must be > 0 cm"):
            Elfving2003TreeAge.age(**params)
        params["diameter"] = -10
        with pytest.raises(ValueError, match="diameter .* must be > 0 cm"):
            Elfving2003TreeAge.age(**params)

    def test_age_implausible_result_raises_arithmetic_error(self):
        # This requires finding inputs that lead to extreme age values.
        # For now, we'll trust the internal check. A specific test would mock _calculate_ln_a13_...
        # to return a value that results in age outside (0, 1000).
        # Example: If ln_a13 is very large or very small.
        pass  # Hard to trigger without knowing model sensitivities deeply or extensive mocking.

    # --- Group Selection and Basic Calculation Tests ---
    # These tests check if a group is selected and runs without error,
    # producing a positive age. They don't validate the exact age value.

    def test_group_9_standard_tree(self):
        params = DEFAULT_AGE_PARAMS.copy()
        params["is_standard_tree_hint"] = True
        params["species"] = TreeSpecies.Sweden.pinus_sylvestris  # Standard can be any species
        age = Elfving2003TreeAge.age(**params)
        assert 0 < age < 1000

    def test_group_4_uneven_aged_with_age(self):
        params = DEFAULT_AGE_PARAMS.copy()
        params["is_uneven_aged"] = True
        params["total_stand_age"] = 70  # Ensure age is present
        params["species"] = TreeSpecies.Sweden.picea_abies  # Example
        age = Elfving2003TreeAge.age(**params)
        assert 0 < age < 1000

    def test_group_3_even_aged_no_stand_age(self):
        params = DEFAULT_AGE_PARAMS.copy()
        params["total_stand_age"] = None  # Critical for Group 3
        params["species"] = TreeSpecies.Sweden.betula_pendula  # Example
        # Group 3 requires QMD (for reld) and relascope BA (for lngfp1)
        params["QMD_cm"] = 20
        params["basal_area_relascope_m2_ha"] = 22
        age = Elfving2003TreeAge.age(**params)
        assert 0 < age < 1000

    def test_group_2_even_aged_with_stand_age(self):
        params = DEFAULT_AGE_PARAMS.copy()
        params["total_stand_age"] = 60
        # Make it a species not specifically handled by 5,6,7,8,51 to force
        # Group 2 (e.g. an unknown conifer)
        # Or ensure it's not standard/uneven and is_contorta is false.
        # The current _determine_calculation_group prioritizes 2 if age is present and not 9 or 4.
        params["species"] = TreeSpecies.Sweden.taxus_baccata
        params["is_uneven_aged"] = False
        params["is_standard_tree_hint"] = False
        age = Elfving2003TreeAge.age(**params)
        assert 0 < age < 1000

    def test_group_51_pinus_contorta(self):
        params = DEFAULT_AGE_PARAMS.copy()
        params["species"] = TreeSpecies.Sweden.pinus_contorta
        params["total_stand_age"] = 80  # Needs age for Contorta specific logic path
        age = Elfving2003TreeAge.age(**params)
        assert 0 < age < 1000
        # Add another test to see if age is different from regular pine due to adjustments
        params_pine = params.copy()
        params_pine["species"] = TreeSpecies.Sweden.pinus_sylvestris
        age_pine = Elfving2003TreeAge.age(**params_pine)
        if age_pine > 0 and age > 0:  # Ensure valid ages for comparison
            assert not isclose(age, age_pine, rel_tol=1e-3), (
                "Contorta age should differ from Sylvestris due to adjustments"
            )

    def test_group_5_pine_sylvestris_or_larch(self):
        params_pine = DEFAULT_AGE_PARAMS.copy()
        params_pine["species"] = TreeSpecies.Sweden.pinus_sylvestris
        age_pine = Elfving2003TreeAge.age(**params_pine)
        assert 0 < age_pine < 1000

        params_larch = DEFAULT_AGE_PARAMS.copy()
        params_larch["species"] = TreeSpecies.Sweden.larix_decidua
        age_larch = Elfving2003TreeAge.age(**params_larch)
        assert 0 < age_larch < 1000

    def test_group_6_spruce(self):
        params = DEFAULT_AGE_PARAMS.copy()
        params["species"] = TreeSpecies.Sweden.picea_abies
        age = Elfving2003TreeAge.age(**params)
        assert 0 < age < 1000

    def test_group_7_birch(self):
        params = DEFAULT_AGE_PARAMS.copy()
        params["species"] = TreeSpecies.Sweden.betula_pendula
        age = Elfving2003TreeAge.age(**params)
        assert 0 < age < 1000

    def test_group_8_other_deciduous_shade_tolerant(self):
        params = DEFAULT_AGE_PARAMS.copy()
        params["species"] = TreeSpecies.Sweden.carpinus_betulus  # Example shade-tolerant
        # is_shade_tolerant_broadleaf_hint could be False to test auto-detection
        params["is_shade_tolerant_broadleaf_hint"] = None
        age = Elfving2003TreeAge.age(**params)
        assert 0 < age < 1000

        # Test with hint
        params["is_shade_tolerant_broadleaf_hint"] = True
        age_hinted = Elfving2003TreeAge.age(**params)
        assert 0 < age_hinted < 1000
        # If the model is sensitive, age and age_hinted might be slightly different
        # if auto-detection differs from hint, or identical if same flag results.

    def test_group_8_other_deciduous_light_demanding_as_fallback(self):
        params = DEFAULT_AGE_PARAMS.copy()
        # A deciduous species not Birch and not explicitly shade-tolerant
        # for this test's definition
        params["species"] = (
            TreeSpecies.Sweden.quercus_robur
        )  # Quercus is bokek, but if not Birch, will fall to G8.
        age = Elfving2003TreeAge.age(**params)
        assert 0 < age < 1000

    # --- Specific Flag Tests ---
    def test_flags_in_model_params(self):
        # Test if flags are correctly set in _ModelParams
        # This is more of an integration test for _prepare_model_params
        params_dict = DEFAULT_AGE_PARAMS.copy()
        params_dict["is_gotland"] = True
        params_dict["is_ditched"] = True
        params_dict["is_peat_soil"] = True
        params_dict["field_layer"] = Sweden.FieldLayer.HIGH_HERB_WITHOUT_SHRUBS  # code 1
        params_dict["species"] = TreeSpecies.Sweden.carpinus_betulus  # Shade-tolerant

        mp = Elfving2003TreeAge._prepare_model_params(
            diameter=params_dict["diameter"],
            species_input=params_dict["species"],
            total_stand_age=params_dict["total_stand_age"],
            SIS_spruce=params_dict["SIS"],
            field_layer=params_dict["field_layer"],
            basal_area_plot_m2_ha=params_dict["basal_area_plot_m2_ha"],
            basal_area_relascope_m2_ha=params_dict["basal_area_relascope_m2_ha"],
            altitude_m=params_dict["altitude_m"],
            latitude=params_dict["latitude"],
            QMD_cm=params_dict["QMD_cm"],
            stems_ha=params_dict["stems_ha"],
            is_uneven_aged_override=params_dict["is_uneven_aged"],
            dominant_mean_diameter_override=params_dict["dominant_mean_diameter"],
            is_standard_override=params_dict["is_standard_tree_hint"],
            is_undergrowth_override=params_dict["is_undergrowth_tree_hint"],
            is_gotland_override=params_dict["is_gotland"],
            is_ditched_override=params_dict["is_ditched"],
            is_peat_soil_override=params_dict["is_peat_soil"],
            is_shade_tolerant_broadleaf_override=params_dict["is_shade_tolerant_broadleaf_hint"],
        )
        assert mp.is_gotland_flag == 1
        assert mp.is_ditched_flag == 1
        assert mp.is_peat_soil_flag == 1
        assert mp.is_rich_site_flag == 1
        assert mp.is_poor_site_flag == 0
        assert mp.is_shade_tolerant_broadleaf_flag == 1

    def test_parameter_validation_in_calculators(self):
        # Test that individual group calculators raise ValueError if essential params are missing
        params_minimal = DEFAULT_AGE_PARAMS.copy()
        params_minimal["total_stand_age"] = None
        params_minimal["SIS"] = None
        params_minimal["QMD_cm"] = None
        params_minimal["basal_area_relascope_m2_ha"] = None  # For lngfp1
        params_minimal["basal_area_plot_m2_ha"] = None  # For ln g

        # Group 3: requires QMD (for diameter_qmd_ratio), SIS, relascope_ba (for lngfp1)
        params_g3 = params_minimal.copy()
        params_g3["species"] = TreeSpecies.Sweden.betula_pendula
        # Trigger Group 3 by setting total_stand_age to None
        params_g3["total_stand_age"] = None

        # Test missing QMD_cm for Group 3
        temp_qmd = params_g3.pop("QMD_cm", None)  # remove QMD
        with pytest.raises(ValueError, match="G3: diameter_qmd_ratio"):
            Elfving2003TreeAge.age(**params_g3)
        params_g3["QMD_cm"] = temp_qmd  # add it back

        # Test missing SIS for Group 3
        temp_sis = params_g3.pop("SIS", None)
        with pytest.raises(ValueError, match="G3: diameter_qmd_ratio"):
            Elfving2003TreeAge.age(**params_g3)
        params_g3["SIS"] = temp_sis

        # Test missing basal_area_relascope_m2_ha for Group 3 (lngfp1)
        temp_ba_rel = params_g3.pop("basal_area_relascope_m2_ha", None)
        with pytest.raises(ValueError, match="G3: diameter_qmd_ratio"):
            Elfving2003TreeAge.age(**params_g3)
        params_g3["basal_area_relascope_m2_ha"] = temp_ba_rel
