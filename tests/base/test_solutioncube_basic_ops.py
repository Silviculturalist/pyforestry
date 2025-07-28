import json

import pytest
import xarray as xr

from pyforestry.base.pricelist.solutioncube import SolutionCube, _hash_pricelist


def test_hash_deterministic():
    price = {"a": 1, "b": 2}
    assert _hash_pricelist(price) == _hash_pricelist(json.loads(json.dumps(price)))


def test_save_load_lookup_roundtrip(tmp_path):
    price_data = {"common": 1}
    h = _hash_pricelist(price_data)
    ds = xr.Dataset(
        {
            "total_value": ("species", [1.0]),
            "solution_sections": ("species", ["[]"]),
        },
        coords={"species": ["sp"], "dbh": [10], "height": [5.0]},
        attrs={"pricelist_hash": h, "taper_model": "Dummy"},
    )
    cube = SolutionCube(ds)
    path = tmp_path / "cube.nc"
    cube.save(path)
    loaded = SolutionCube.load(path, pricelist_to_verify=price_data)
    val, sec = loaded.lookup("sp", 10, 5.0)
    assert val == 1.0
    assert sec == []

    with pytest.raises(ValueError):
        SolutionCube.load(path, pricelist_to_verify={"a": 2})
