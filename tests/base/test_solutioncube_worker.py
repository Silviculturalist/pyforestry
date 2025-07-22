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
        "pyforestry.base.pricelist.solutioncube.SweTimber",
        lambda species, diameter_cm, height_m: object(),
    )
    monkeypatch.setattr(
        "pyforestry.base.pricelist.solutioncube.create_pricelist_from_data",
        lambda data, sp: {},
    )
    monkeypatch.setattr(
        "pyforestry.base.pricelist.solutioncube.Nasberg_1985_BranchBound",
        lambda t, p, taper_model_class: DummyOptimizer(),
    )

    out = _worker_buck_one_tree(("pine", 20, 150), {}, object)
    assert out["species"] == "pine"
    assert out["total_value"] == 100.0
    assert out["solution_sections"] == "[]"
