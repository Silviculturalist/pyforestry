"""Sweden's scenario runbook projects real stands.

It used to emit the artifact contract from a seeded random walk, warn on every
call, and stamp ``"synthetic": true`` into all three files. These tests assert
that what it writes now is a projection: the Elfving (2010) model over a real
tree list, priced through the valuation stage the configuration declares.
"""

from __future__ import annotations

import json

import pytest

from pyforestry.base.helpers.primitives import Age
from pyforestry.base.pricelist import create_pricelist_from_data
from pyforestry.simulation.artifacts import (
    REQUIRED_ARTIFACTS,
    load_scenario_summary,
    validate_artifact_contract,
)
from pyforestry.simulation.valuation.volume import ValuationSettings
from pyforestry.sweden.pricelist.data.mellanskog_2013 import (
    MELLANSKOG_2013_IDENTITY,
    MELLANSKOG_2013_PRICE_DATA,
)
from pyforestry.sweden.simulation.orchestration import (
    brandel_stand_volume,
    build_even_aged_stands,
    run_sweden_scenario,
    swedish_timber_factory,
)
from pyforestry.sweden.simulation.presets import get_scenario_config
from pyforestry.sweden.taper import EdgrenNylinder1949


@pytest.fixture(scope="module")
def valuation() -> ValuationSettings:
    """Sweden's example prices, with the identity that says whose they are."""
    return ValuationSettings(
        pricelist=create_pricelist_from_data(
            MELLANSKOG_2013_PRICE_DATA, identity=MELLANSKOG_2013_IDENTITY
        ),
        taper_class=EdgrenNylinder1949,
        timber_factory=swedish_timber_factory,
    )


def test_baseline_run_projects_a_real_stand(tmp_path, valuation) -> None:
    result = run_sweden_scenario(
        global_seed=20260728,
        output_dir=tmp_path / "run",
        stands=build_even_aged_stands(1),
        n_steps=3,
        valuation=valuation,
        discount_rate=0.0,
    )

    validate_artifact_contract(result.artifacts.output_dir)
    for artifact in REQUIRED_ARTIFACTS:
        assert (result.artifacts.output_dir / artifact).exists()

    row = result.rows[0]
    assert row["initial_volume_m3"] > 0.0
    assert row["gross_growth_m3"] > 0.0, "a spruce stand at site index 26 grows"
    assert row["net_volume_m3"] > row["initial_volume_m3"]

    manifest = json.loads(result.artifacts.run_manifest_path.read_text(encoding="utf-8"))
    assert manifest["region"] == "Sweden"
    assert manifest["stages"] == ["management", "disturbance", "growth", "valuation"]
    assert "synthetic" not in manifest
    assert [entry["component_id"] for entry in manifest["models_run"]] == ["elfving_2010"]
    assert manifest["models_run"][0]["year"] == 2010


def test_thinning_is_priced_through_the_valuation_stage(tmp_path, valuation) -> None:
    """The two halves of the valuation design, connected.

    A thinning records the stems it removed into the ledger, and the valuation
    stage prices them. Before the runtime existed the ledger was never
    populated, so a pipeline that declared a valuation stage valued nothing.
    """
    result = run_sweden_scenario(
        global_seed=20260728,
        output_dir=tmp_path / "run",
        stands=build_even_aged_stands(1),
        n_steps=3,
        valuation=valuation,
        discount_rate=0.0,
        thin_at_age=[Age.TOTAL(45.0)],
    )

    row = result.rows[0]
    assert row["harvested_m3"] > 0.0
    ctx = result.contexts[0]
    assert float(ctx.attrs["cash"]) > 0.0
    assert ctx.attrs["valuation"]["pieces"]


def test_disturbance_is_a_loss_not_a_harvest(tmp_path, valuation) -> None:
    """Storm-thrown wood must not be reported as income."""
    result = run_sweden_scenario(
        global_seed=20260728,
        output_dir=tmp_path / "run",
        stands=build_even_aged_stands(1),
        n_steps=3,
        valuation=valuation,
        discount_rate=0.0,
        disturbance_rate_per_year=0.01,
    )

    row = result.rows[0]
    assert row["disturbance_loss_m3"] > 0.0
    assert row["harvested_m3"] == pytest.approx(0.0)
    assert "cash" not in result.contexts[0].attrs


def test_the_volume_reporter_sees_a_thinning_immediately(tmp_path, valuation) -> None:
    """A live reporter, not a value the model cached at its last step.

    With a stale reporter every removal reads as zero and the volume it took
    reappears inside the growth column.
    """
    stands = build_even_aged_stands(1)
    model_ctx = run_sweden_scenario(
        global_seed=1,
        output_dir=tmp_path / "run",
        stands=stands,
        n_steps=1,
        valuation=valuation,
        discount_rate=0.0,
    ).contexts[0]

    before = brandel_stand_volume(model_ctx)
    for plot in model_ctx.plots:
        for tree in plot.trees:
            tree.weight_n = float(tree.weight_n) * 0.5
    assert brandel_stand_volume(model_ctx) == pytest.approx(before * 0.5, rel=1e-9)


def test_summary_is_loadable_and_keyed_by_stand(tmp_path, valuation) -> None:
    result = run_sweden_scenario(
        global_seed=20260728,
        output_dir=tmp_path / "run",
        stands=build_even_aged_stands(3),
        n_steps=2,
        valuation=valuation,
        discount_rate=0.0,
    )
    rows = load_scenario_summary(result.artifacts.scenario_summary_path)
    assert [row["stand_id"] for row in rows] == [1, 2, 3]
    assert {row["scenario_id"] for row in rows} == {"baseline"}


def test_scenario_config_lookup_and_error_paths() -> None:
    assert get_scenario_config("baseline").scenario_id == "baseline"
    with pytest.raises(ValueError, match="Unsupported scenario_id"):
        get_scenario_config("storm_risk_high")
    with pytest.raises(ValueError, match="Unsupported scenario_id"):
        get_scenario_config("unknown")


def test_inflation_reaches_the_horizon_net_present_value(tmp_path, valuation) -> None:
    """A price forcing moves the money; the discount rate moves it in time.

    The composition the forcing mechanism exists for: a price index scales each
    period's revenue in the year it was earned, and the horizon NPV discounts
    those nominal flows back to the start of the run.
    """
    from pyforestry.base.contracts import SourceReference
    from pyforestry.simulation.forcing import PRICE, AnnualForcing, ForcingSet

    index = AnnualForcing(
        PRICE,
        {2025: 1.0, 2030: 1.104, 2035: 1.219, 2040: 1.346},
        source=SourceReference(
            author="Test fixture", year=2026, title="A price index, and says so"
        ),
    )

    def _run(name, forcings):
        return run_sweden_scenario(
            global_seed=7,
            output_dir=tmp_path / name,
            stands=build_even_aged_stands(1),
            n_steps=3,
            step_years=5.0,
            start_year=2025,
            valuation=valuation,
            discount_rate=0.03,
            thin_at_age=[Age.TOTAL(50.0)],
            forcings=forcings,
        )

    flat = _run("flat", ForcingSet())
    inflated = _run("inflated", ForcingSet([index]))

    # The thinning falls in 2035, where the index stands at 1.219.
    ((_stand_id, flat_flows),) = flat.cash_flows()
    ((_stand_id, inflated_flows),) = inflated.cash_flows()
    assert [f.year for f in flat_flows] == [2035.0]
    assert inflated_flows[0].price_factor == pytest.approx(1.219)
    assert inflated_flows[0].amount == pytest.approx(flat_flows[0].amount * 1.219)

    npv_flat = flat.net_present_value()[1]
    npv_inflated = inflated.net_present_value()[1]
    assert npv_inflated == pytest.approx(npv_flat * 1.219)
    # Discounted from 2035 back to the run's own first year, not to nothing.
    assert npv_flat == pytest.approx(flat_flows[0].amount * 1.03**-10)
    assert inflated.start_year == 2025.0

    # And it is in the artifact, which is the whole point of it being a column.
    assert flat.rows[0]["net_present_value"] == pytest.approx(npv_flat)
    assert flat.rows[0]["nominal_revenue"] == pytest.approx(flat_flows[0].amount)
    assert flat.rows[0]["net_present_value"] < flat.rows[0]["nominal_revenue"]


def test_a_run_that_never_harvested_is_worth_nothing(tmp_path, valuation) -> None:
    result = run_sweden_scenario(
        global_seed=7,
        output_dir=tmp_path / "run",
        stands=build_even_aged_stands(1),
        n_steps=2,
        start_year=2025,
        valuation=valuation,
        discount_rate=0.03,
    )
    assert result.net_present_value() == {1: 0.0}
    # Priced, and worth nothing -- which the row distinguishes from unpriced.
    assert result.rows[0]["valued"] is True
    assert result.rows[0]["net_present_value"] == 0.0


def test_the_baseline_writes_what_it_earned_into_its_artifact(tmp_path, valuation) -> None:
    """The summary is readable on its own: what came out, and what it was worth.

    A net present value was reachable through ``ScenarioRunResult`` before this,
    and reachable is not the same as recorded: the artifacts are how a run is read
    back without rerunning it, and the money was the one part of the balance that
    only existed in the process that produced it.
    """
    result = run_sweden_scenario(
        global_seed=20260728,
        output_dir=tmp_path / "run",
        stands=build_even_aged_stands(2),
        n_steps=4,
        start_year=2025,
        valuation=valuation,
        discount_rate=0.03,
        thin_at_age=[Age.TOTAL(45.0)],
    )

    rows = load_scenario_summary(result.artifacts.scenario_summary_path)
    assert len(rows) == 2
    for row in rows:
        assert bool(row["valued"]) is True
        assert row["harvested_m3"] > 0.0
        assert row["nominal_revenue"] > 0.0
        # The thinning falls in 2030, so discounting it back to 2025 costs something.
        assert 0.0 < row["net_present_value"] < row["nominal_revenue"]
        assert row["net_present_value"] == pytest.approx(row["nominal_revenue"] * 1.03**-5)

    # And the rate the column was discounted at is in the manifest, cited as the
    # decision it is rather than as a finding.
    manifest = json.loads(result.artifacts.run_manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "3.2"
    assert manifest["valuation"]["discount_rate"] == pytest.approx(0.03)
    assert manifest["valuation"]["base_year"] == 2025.0
    assert manifest["valuation"]["discount_source"]["author"] == "(none)"

    # The prices that earned it are cited too, and the currency they are quoted in
    # is what the two money columns above are in.
    price_list = manifest["valuation"]["price_list"]
    assert price_list["name"] == "Mellanskog 2013"
    assert price_list["currency"] == "SEK"
    assert price_list["source"]["author"] == "Mellanskog"
    assert price_list["source"]["year"] == 2013

    quality = json.loads(result.artifacts.quality_report_path.read_text(encoding="utf-8"))
    assert quality["value_consistency_checked"] is True
