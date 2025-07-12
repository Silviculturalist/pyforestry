import pytest
import xarray as xr
import numpy as np
import json
import copy

# Imports from your project
from munin.pricelist.solutioncube import SolutionCube
from munin.taper.sweden.edgren_nylinder_1949 import EdgrenNylinder1949
from munin.pricelist.data.mellanskog_2013 import Mellanskog_2013_price_data
from munin.helpers.tree_species import TreeSpecies

@pytest.fixture(scope="module")
def mini_cube():
    """
    A pytest fixture that generates a very small SolutionCube for testing.
    This runs only once per test module, making tests fast.
    """
    # Define minimal parameters for a tiny, fast-to-generate cube
    species_list = [TreeSpecies.Sweden.picea_abies.full_name]
    dbh_range = (20, 22)  # Will compute for DBH 20 and 22
    height_range = (15, 15.2)  # Will compute for Height 15.0 and 15.2
    
    # This will generate a cube for just 2x2 = 4 trees.
    cube = SolutionCube.generate(
        pricelist_data=Mellanskog_2013_price_data,
        taper_model=EdgrenNylinder1949,
        species_list=species_list,
        dbh_range=dbh_range,
        height_range=height_range,
        dbh_step=2,
        height_step=0.2,
        workers=1  # No need for parallel processing for just 4 trees
    )
    return cube

def test_generate_cube(mini_cube):
    """
    Tests the basic structure and metadata of the generated cube.
    """
    assert isinstance(mini_cube, SolutionCube)
    assert isinstance(mini_cube.dataset, xr.Dataset)

    # Check for correct dimensions
    assert "species" in mini_cube.dataset.dims
    assert "height" in mini_cube.dataset.dims
    assert "dbh" in mini_cube.dataset.dims

    # Check that the coordinates match our small test case
    assert len(mini_cube.dataset.coords["species"]) == 1
    assert len(mini_cube.dataset.coords["height"]) == 2
    assert len(mini_cube.dataset.coords["dbh"]) == 2
    np.testing.assert_array_equal(mini_cube.dataset.coords["dbh"].values, [20, 22])

    # Check for the expected data variables
    assert "total_value" in mini_cube.dataset.data_vars
    assert "solution_sections" in mini_cube.dataset.data_vars
    
    # Check that metadata attributes were written correctly
    assert "pricelist_hash" in mini_cube.dataset.attrs
    assert mini_cube.dataset.attrs["taper_model"] == "EdgrenNylinder1949"

def test_save_load_roundtrip(mini_cube, tmp_path):
    """
    Ensures that a cube can be saved to disk and loaded back without data loss.
    Uses pytest's built-in `tmp_path` fixture for temporary file handling.
    """
    file_path = tmp_path / "test_cube.nc"

    # 1. Save the cube
    mini_cube.save(file_path)
    assert file_path.exists()

    # 2. Load the cube back
    loaded_cube = SolutionCube.load(file_path)

    # 3. Verify that the loaded dataset is identical to the original
    # xr.testing.assert_equal is a powerful tool for this
    xr.testing.assert_equal(mini_cube.dataset, loaded_cube.dataset)

def test_pricelist_hash_verification(mini_cube, tmp_path):
    """
    Tests that the pricelist hash verification works correctly on load.
    """
    file_path = tmp_path / "test_cube.nc"
    mini_cube.save(file_path)

    # 1. Test that loading with the CORRECT pricelist passes
    try:
        SolutionCube.load(file_path, pricelist_to_verify=Mellanskog_2013_price_data)
    except ValueError:
        pytest.fail("Hash verification failed unexpectedly with the correct pricelist.")

    # 2. Test that loading with an INCORRECT pricelist fails
    modified_pricelist = copy.deepcopy(Mellanskog_2013_price_data)
    modified_pricelist["Common"]["TopDiameter"] = 99  # Introduce a change

    with pytest.raises(ValueError, match="Pricelist hash mismatch!"):
        SolutionCube.load(file_path, pricelist_to_verify=modified_pricelist)

def test_lookup(mini_cube):
    """
    Tests the lookup method for both exact and nearest-neighbor matches.
    """
    species = TreeSpecies.Sweden.picea_abies.full_name
    
    # 1. Test an exact coordinate lookup
    value, sections = mini_cube.lookup(species=species, dbh=20.0, height=15.0)
    assert isinstance(value, float)
    assert value > 0  # Should have a positive value
    assert isinstance(sections, list)
    assert len(sections) > 0  # Should have at least one log section

    # 2. Test a nearest-neighbor lookup
    value_nearest, _ = mini_cube.lookup(species=species, dbh=20.4, height=15.0)
    assert value == value_nearest

    # Test another nearest-neighbor case
    value_nearest_2, _ = mini_cube.lookup(species=species, dbh=22.4, height=15.3)
    
    # Get the expected value for the corner case (22, 15.2)
    expected_value = mini_cube.dataset.sel(species=species, dbh=22, height=15.2)["total_value"].item()
    assert value_nearest_2 == expected_value

    # 3. Test a lookup for a non-existent species
    value_bad, sections_bad = mini_cube.lookup(species="non_existent_species", dbh=20, height=15)
    assert value_bad == 0.0
    assert sections_bad == []