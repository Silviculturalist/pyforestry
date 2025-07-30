from types import SimpleNamespace

import xarray as xr

import pyforestry.base.pricelist.solutioncube as sc


class DummyOptimizer:
    def __init__(self, *args, **kwargs):
        pass

    def calculate_tree_value(self, *args, **kwargs):
        return SimpleNamespace(total_value=1.0, sections=[SimpleNamespace(a=1)])


class FailingOptimizer(DummyOptimizer):
    def calculate_tree_value(self, *args, **kwargs):  # type: ignore[override]
        raise RuntimeError("boom")


class DummyPool:
    def __init__(self, processes):
        self.processes = processes
        self.tasks = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass

    def imap_unordered(self, func, tasks, chunksize=1):
        for t in tasks:
            yield func(t)


def test_worker_with_sections(monkeypatch):
    monkeypatch.setattr(sc, "SweTimber", lambda *args, **kwargs: object())
    monkeypatch.setattr(sc, "create_pricelist_from_data", lambda *a, **k: {})
    monkeypatch.setattr(sc, "Nasberg_1985_BranchBound", lambda *a, **k: DummyOptimizer())

    res = sc._worker_buck_one_tree(("pine", 10, 100), {}, object)
    assert res["solution_sections"] == '[{"a": 1}]'
    assert res["total_value"] == 1.0


def test_worker_error(monkeypatch):
    monkeypatch.setattr(sc, "SweTimber", lambda *a, **k: object())
    monkeypatch.setattr(sc, "create_pricelist_from_data", lambda *a, **k: {})
    monkeypatch.setattr(sc, "Nasberg_1985_BranchBound", lambda *a, **k: FailingOptimizer())

    out = sc._worker_buck_one_tree(("pine", 10, 100), {}, object)
    assert out["total_value"] != out["total_value"]  # NaN
    assert out["solution_sections"] == "[]"


def test_generate_custom_pool(monkeypatch):
    monkeypatch.setattr(
        sc,
        "_worker_buck_one_tree",
        lambda *a, **k: {
            "species": "pine",
            "dbh": 10,
            "height": 10.0,
            "total_value": 1.0,
            "solution_sections": "[]",
        },
    )
    monkeypatch.setattr(sc, "Pool", DummyPool)
    monkeypatch.setattr(sc, "cpu_count", lambda: 4)

    cube = sc.SolutionCube.generate(
        pricelist_data={},
        taper_model=object,
        species_list=["pine"],
        dbh_range=(10, 10),
        height_range=(10, 10),
        workers=-1,
    )
    assert isinstance(cube.dataset, xr.Dataset)
    assert cube.dataset.dims["dbh"] == 1
    assert cube.dataset.attrs["taper_model"] == "object"


def test_lookup_timber_pricelist_unknown_species(capsys):
    ds = xr.Dataset(
        {
            "total_value": (("species", "height", "dbh"), [[[1.0]]]),
            "solution_sections": (("species", "height", "dbh"), [[["[]"]]]),
        },
        coords={"species": ["known"], "height": [1.0], "dbh": [10]},
    )
    cube = sc.SolutionCube(ds)

    value, sections = cube.lookup_timber_pricelist("unknown-species")
    captured = capsys.readouterr()
    assert value == 0.0
    assert sections == []
    assert "not found" in captured.out.lower()
