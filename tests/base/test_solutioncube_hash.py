import json

import xarray as xr

from pyforestry.base.pricelist.solutioncube import SolutionCube, _hash_pricelist


def test_hash_pricelist_consistent():
    data = {"a": 1, "b": 2}
    h1 = _hash_pricelist(data)
    h2 = _hash_pricelist(json.loads(json.dumps(data)))
    assert h1 == h2


def test_lookup_error_handling():
    ds = xr.Dataset(
        {
            "total_value": ("species", [1.0]),
            "solution_sections": ("species", ["[]"]),
        },
        coords={"species": ["sp"], "dbh": [10], "height": [5]},
    )
    cube = SolutionCube(ds)
    val, secs = cube.lookup("other", 10, 5)
    assert val == 0.0 and secs == []
