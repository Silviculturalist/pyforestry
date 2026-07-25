from pyforestry.base.pricelist.solutioncube import _worker_buck_one_tree


class DummyOptimizer:
    def __init__(self, *args, **kwargs):
        pass

    class Result:
        total_value = 100.0
        sections = None

    def calculate_tree_value(self, *args, **kwargs):
        return self.Result()


def test_worker_buck_one_tree_basic(monkeypatch):
    monkeypatch.setattr(
        "pyforestry.base.pricelist.solutioncube.create_pricelist_from_data",
        lambda data, sp: {},
    )
    # Patched at the source module: solutioncube imports the optimiser inside the
    # worker (the two modules are mutually importable), so there is no module-level
    # name on solutioncube to patch.
    monkeypatch.setattr(
        "pyforestry.base.timber_bucking.nasberg_1985.Nasberg_1985_BranchBound",
        lambda t, p, taper_model_class: DummyOptimizer(),
    )

    out = _worker_buck_one_tree(
        ("pine", 20, 150),
        {},
        object,
        timber_class=lambda species, diameter_cm, height_m: object(),
    )
    assert out["species"] == "pine"
    assert out["total_value"] == 100.0
    assert out["solution_sections"] == "[]"
