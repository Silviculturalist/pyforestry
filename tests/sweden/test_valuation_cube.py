"""Building and loading the valuation solution cube, as module functions.

These were classmethods and methods on the Elfving 2010 pipeline: a class whose
job is to step a stand also owned a multi-minute build, a ``mkdir`` and a
file-existence policy. The tests moved with the code.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforestry.sweden.simulation.presets import valuation_cube


def test_generate_cube_uses_the_recommended_species_and_the_given_grid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}
    fake_cube = object()

    def _fake_generate(
        *,
        pricelist_data,
        taper_model,
        timber_class,
        species_list,
        dbh_range,
        height_range,
        dbh_step,
        height_step,
        workers,
    ):  # noqa: ANN001, ANN202
        calls.update(
            pricelist_data=pricelist_data,
            taper_model=taper_model,
            timber_class=timber_class,
            species_list=species_list,
            dbh_range=dbh_range,
            height_range=height_range,
            dbh_step=dbh_step,
            height_step=height_step,
            workers=workers,
        )
        return fake_cube

    monkeypatch.setattr(valuation_cube.SolutionCube, "generate", staticmethod(_fake_generate))

    out = valuation_cube.generate_cube(
        workers=3,
        dbh_range_cm=(12.0, 32.0),
        height_range_m=(9.0, 25.0),
        dbh_step_cm=4,
        height_step_m=1.5,
    )

    assert out is fake_cube
    assert calls["timber_class"] is valuation_cube.SweTimber
    assert calls["species_list"] == ["pinus sylvestris", "picea abies"]
    assert calls["dbh_range"] == (12.0, 32.0)
    assert calls["height_range"] == (9.0, 25.0)
    assert calls["dbh_step"] == 4
    assert calls["height_step"] == 1.5
    assert calls["workers"] == 3


def test_ensure_cube_file_builds_and_saves(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: dict[str, object] = {}

    class _FakeCube:
        def save(self, path: str) -> None:
            calls["save_path"] = path
            Path(path).write_text("fake cube")

    def _fake_generate(**kwargs):  # noqa: ANN003, ANN202
        calls.update(kwargs)
        return _FakeCube()

    monkeypatch.setattr(valuation_cube, "generate_cube", _fake_generate)

    cube_path = tmp_path / "cube.nc"
    out = valuation_cube.ensure_cube_file(
        path=str(cube_path),
        overwrite=True,
        workers=3,
        dbh_range_cm=(12.0, 32.0),
        height_range_m=(9.0, 25.0),
        dbh_step_cm=4,
        height_step_m=1.5,
    )

    assert Path(out) == cube_path
    assert Path(calls["save_path"]) == cube_path
    assert calls["workers"] == 3
    assert calls["dbh_range_cm"] == (12.0, 32.0)
    assert calls["height_range_m"] == (9.0, 25.0)
    assert calls["dbh_step_cm"] == 4
    assert calls["height_step_m"] == 1.5


def test_ensure_cube_file_leaves_an_existing_cube_alone(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A multi-minute rebuild should not happen because a path already resolves."""
    cube_path = tmp_path / "cube.nc"
    cube_path.write_text("already here")

    def _must_not_run(**kwargs):  # noqa: ANN003, ANN202
        raise AssertionError("generate_cube should not have been called")

    monkeypatch.setattr(valuation_cube, "generate_cube", _must_not_run)

    assert Path(valuation_cube.ensure_cube_file(path=str(cube_path))) == cube_path
    assert cube_path.read_text() == "already here"


def test_load_cube_verifies_the_pricelist(monkeypatch: pytest.MonkeyPatch) -> None:
    """A cube holds values, so one built from another year's prices would price
    this pipeline's stands wrongly with nothing in the numbers looking off."""
    seen: dict[str, object] = {}

    def _fake_load(path, *, pricelist_to_verify):  # noqa: ANN001, ANN202
        seen["path"] = path
        seen["pricelist_to_verify"] = pricelist_to_verify
        return "cube"

    monkeypatch.setattr(valuation_cube.SolutionCube, "load", staticmethod(_fake_load))
    assert valuation_cube.load_cube("somewhere.nc") == "cube"
    assert seen["path"] == "somewhere.nc"
    assert seen["pricelist_to_verify"] is valuation_cube.MELLANSKOG_2013_PRICE_DATA
