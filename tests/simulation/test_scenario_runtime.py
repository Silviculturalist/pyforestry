"""A scenario configuration is executed, not merely recorded.

``ScenarioConfig`` declared a seed strategy, an ordered list of stage names,
rulesets and a guard policy, and nothing ran any of them: the only consumer
filled the artifacts with a seeded random walk and stamped every file
``synthetic: true``. These tests assert that all four are now executed, and that
the manifest says truthfully how the run was constructed -- which is the reason
the artifacts exist.
"""

from __future__ import annotations

import json
from math import pi, sqrt

import pytest

from pyforestry.base.contracts import SourceReference
from pyforestry.base.helpers.primitives import StandBasalArea, Stems
from pyforestry.base.helpers.stand import Stand
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.base.pricelist.pricelist import (
    UNATTRIBUTED_PRICELIST_IDENTITY,
    LengthRange,
    Pricelist,
    PricelistIdentity,
    TimberPriceForDiameter,
    TimberPricelist,
)
from pyforestry.base.simulation.core import SimulationContext
from pyforestry.base.simulation.growth_model import GrowthModel, Requirements
from pyforestry.base.taper.taper import Taper
from pyforestry.base.timber.timber_base import Timber
from pyforestry.simulation.artifacts import (
    MANIFEST_REQUIRED_KEYS,
    QUALITY_REPORT_REQUIRED_KEYS,
    REQUIRED_ARTIFACTS,
    SCENARIO_SUMMARY_COLUMNS,
    check_value_consistency,
    check_volume_balance,
    load_scenario_summary,
    validate_artifact_contract,
)
from pyforestry.simulation.forcing import (
    CALENDAR_YEAR_KEY,
    DISCOUNT,
    GROWTH,
    AnnualForcing,
    ConstantForcing,
    ForcingSet,
    stated_choice,
)
from pyforestry.simulation.policy import ManagementPlan
from pyforestry.simulation.presets import ScenarioConfig
from pyforestry.simulation.scenario import StandUnit, run_scenario
from pyforestry.simulation.stages import MeanTree, StageContext, build_pipeline, known_stages
from pyforestry.simulation.valuation.volume import ValuationSettings

SPECIES = TreeSpecies.Sweden.picea_abies


class _DoublingModel(GrowthModel):
    """Adds a fixed basal-area increment per year, and reports a volume for it.

    Not science: a model whose arithmetic is obvious by inspection, so a test can
    say what the run's numbers must be.
    """

    VOLUME_PER_BA = 10.0
    BA_PER_YEAR = 0.5

    @property
    def component_id(self) -> str:
        return "test_doubling_model"

    @property
    def source(self) -> SourceReference:
        return SourceReference(author="(none)", year=0, title="Test fixture, not a model")

    def requirements(self) -> Requirements:
        return Requirements(inventory="aggregate", native_step_years=5.0)

    def update_step(self, ctx: SimulationContext, dt: float) -> None:
        ba = float(ctx.metrics["BasalArea"]["TOTAL"]) + self.BA_PER_YEAR * dt
        stems = float(ctx.metrics["Stems"]["TOTAL"])
        ctx.set_aggregate_metrics(ba_total=ba, stems_total=stems)


def _volume(ctx: SimulationContext) -> float:
    """Volume as a fixed multiple of the *current* basal area."""
    return float(ctx.metrics["BasalArea"]["TOTAL"]) * _DoublingModel.VOLUME_PER_BA


class _Config(ScenarioConfig):
    """A configuration whose stages and rulesets the test controls."""

    def stages(self):
        return ("management", "disturbance", "growth")

    def rulesets(self):
        return {"management": lambda: ManagementPlan(thinning_ratio=0.25)}


class _ValuingConfig(_Config):
    """The same, plus the stage that prices what the management stage removed."""

    def stages(self):
        return ("management", "disturbance", "growth", "valuation")


class _ConstantTaper(Taper):
    """A stem of constant diameter, so a test's bucking has no science in it."""

    def __init__(self, timber: Timber):
        self.diameter = timber.diameter_cm
        self.height = timber.height_m
        super().__init__(timber, self)

    def get_diameter_at_height(self, height_m: float) -> float:  # type: ignore[override]
        return self.diameter if 0 <= height_m <= self.height else 0.0

    def get_height_at_diameter(self, diameter: float) -> float:  # type: ignore[override]
        return self.height

    def volume_section(self, h1_m: float, h2_m: float) -> float:  # type: ignore[override]
        radius = self.diameter / 200
        return max(0.0, h2_m - h1_m) * pi * radius * radius


def _valuation(*, identity: PricelistIdentity | None = None) -> ValuationSettings:
    """A price list flat enough that the money in a test is arithmetic, not forestry."""
    pricelist = Pricelist(identity=identity)
    table = TimberPricelist(10, 40, volume_type="m3fub")
    for diameter in range(10, 41):
        table.set_price_for_diameter(diameter, TimberPriceForDiameter(100, 100, 100))
    pricelist.Timber[SPECIES.full_name] = table
    pricelist.PulpLogLength = LengthRange(2.0, 2.0)
    pricelist.TimberLogLength = LengthRange(2.0, 2.0)
    pricelist.Pulp._prices[SPECIES.full_name] = 50
    pricelist.LogCullPrice = 0
    pricelist.FuelWoodPrice = 0
    return ValuationSettings(pricelist=pricelist, taper_class=_ConstantTaper)


def _mean_tree(ctx: SimulationContext, fraction: float) -> MeanTree:
    """The stand's quadratic mean stem, which is what an aggregate model can offer."""
    basal_area = float(ctx.metrics["BasalArea"]["TOTAL"])
    stems = float(ctx.metrics["Stems"]["TOTAL"])
    return MeanTree(
        species=SPECIES,
        diameter_cm=200.0 * sqrt(basal_area / (stems * pi)),
        height_m=16.0,
        stems_removed=stems * fraction,
    )


def _config(**kwargs) -> _Config:
    base = {
        "preset_id": "test",
        "scenario_id": "baseline",
        "region": "Testland",
        "required_artifacts_": REQUIRED_ARTIFACTS,
    }
    base.update(kwargs)
    return _Config(**base)


def _stands(n: int, *, ba: float = 20.0, stems: float = 1000.0) -> list[StandUnit]:
    return [
        StandUnit(
            stand_id=i,
            stand=Stand.from_aggregate_metrics(
                {
                    "BasalArea": {"TOTAL": StandBasalArea(ba, species=SPECIES)},
                    "Stems": {"TOTAL": Stems(stems, species=SPECIES)},
                },
                area_ha=1.0,
            ),
        )
        for i in range(1, n + 1)
    ]


def _run(tmp_path, **kwargs):
    params = {
        "build_model": _DoublingModel,
        "stands": _stands(2),
        "volume": _volume,
        "global_seed": 20260728,
        "n_steps": 4,
        "step_years": 5.0,
        "output_dir": tmp_path / "run",
        "start_year": 2020.0,
    }
    config = params.pop("config", None) or kwargs.pop("config", None) or _config()
    params.update(kwargs)
    return run_scenario(config, **params)


# --- the stages actually run -------------------------------------------------


def test_growth_runs_and_produces_the_model_s_numbers(tmp_path) -> None:
    """No random walk: the summary is the model's arithmetic."""
    result = _run(tmp_path)
    row = result.rows[0]
    # 20 m2/ha + 0.5 per year over 20 years = 30 m2/ha, at 10 m3 per m2.
    assert row["initial_volume_m3"] == pytest.approx(200.0)
    assert row["net_volume_m3"] == pytest.approx(300.0)
    assert row["gross_growth_m3"] == pytest.approx(100.0)


def test_management_stage_thins_and_is_reported_apart_from_growth(tmp_path) -> None:
    result = _run(tmp_path, thin_at_years=[10.0])
    row = result.rows[0]
    assert row["harvested_m3"] > 0.0
    assert row["disturbance_loss_m3"] == pytest.approx(0.0)
    assert row["net_volume_m3"] < 300.0


def test_disturbance_stage_removes_and_is_reported_apart_from_harvest(tmp_path) -> None:
    result = _run(tmp_path, disturbance_rate_per_year=0.01)
    row = result.rows[0]
    assert row["disturbance_loss_m3"] > 0.0
    assert row["harvested_m3"] == pytest.approx(0.0)


def test_a_growth_forcing_scales_the_increment(tmp_path) -> None:
    """The forcing is applied, and only to the increment."""
    warmer = ForcingSet(
        [
            ConstantForcing(
                GROWTH,
                1.5,
                source=SourceReference(
                    author="Test fixture",
                    year=2026,
                    title="A forcing invented by this test, and saying so",
                ),
            )
        ]
    )
    baseline = _run(tmp_path / "a")
    forced = _run(tmp_path / "b", forcings=warmer)

    assert forced.rows[0]["gross_growth_m3"] == pytest.approx(
        baseline.rows[0]["gross_growth_m3"] * 1.5
    )
    assert forced.rows[0]["initial_volume_m3"] == baseline.rows[0]["initial_volume_m3"]


def test_a_growth_forcing_refuses_a_representation_it_cannot_scale() -> None:
    """Scaling 'the increment' is only defined for aggregate metrics."""
    from pyforestry.base.helpers.plot import CircularPlot
    from pyforestry.base.helpers.tree import Tree
    from pyforestry.base.simulation.growth_model import ExampleStandGeneralModel
    from pyforestry.simulation.stages import ScenarioGrowthStep

    stand = Stand(
        area_ha=1.0,
        plots=[
            CircularPlot(
                id=1,
                area_m2=10_000.0,
                trees=[Tree(species=SPECIES, diameter_cm=20.0, height_m=15.0, weight_n=1.0)],
            )
        ],
    )
    ctx = ExampleStandGeneralModel().build_context(stand, mode_hint="tree_list")
    ctx.attrs[CALENDAR_YEAR_KEY] = 2020.0
    forcings = ForcingSet(
        [
            ConstantForcing(
                GROWTH,
                1.2,
                source=SourceReference(author="Test fixture", year=2026, title="Says so"),
            )
        ]
    )
    with pytest.raises(ValueError, match="growth forcing"):
        ScenarioGrowthStep(forcings=forcings).run(ctx, 5.0)


# --- the manifest says how the run was constructed ---------------------------


def test_manifest_records_the_construction(tmp_path) -> None:
    """The artifact's reason to exist: reading a run back without rerunning it."""
    result = _run(tmp_path, thin_at_years=[10.0], disturbance_rate_per_year=0.02)
    manifest = json.loads(result.artifacts.run_manifest_path.read_text(encoding="utf-8"))

    for key in MANIFEST_REQUIRED_KEYS:
        assert key in manifest, key

    assert manifest["stages"] == ["management", "disturbance", "growth"]
    assert manifest["rulesets_applied"]["management"] == {"thinning_ratio": 0.25}
    assert manifest["forcings_applied"] == [], "this package ships no forcings"
    assert manifest["guard_policy"]["clamp_net_volume_to_zero"] is True
    assert manifest["thin_at_years"] == [10.0]
    assert manifest["disturbance_rate_per_year"] == pytest.approx(0.02)
    assert manifest["scenario_seed"] != manifest["global_seed"]
    assert "synthetic" not in manifest, "nothing here is synthetic any more"


def test_manifest_carries_the_citation_of_every_model_that_ran(tmp_path) -> None:
    result = _run(tmp_path)
    manifest = json.loads(result.artifacts.run_manifest_path.read_text(encoding="utf-8"))
    ids = {entry["component_id"] for entry in manifest["models_run"]}
    assert ids == {"test_doubling_model"}
    assert all("author" in entry and "year" in entry for entry in manifest["models_run"])


def test_quality_report_and_contract(tmp_path) -> None:
    result = _run(tmp_path)
    validate_artifact_contract(result.artifacts.output_dir)
    quality = json.loads(result.artifacts.quality_report_path.read_text(encoding="utf-8"))
    for key in QUALITY_REPORT_REQUIRED_KEYS:
        assert key in quality
    assert quality["volume_balance_checked"] is True
    assert quality["row_count"] == 2


# --- the numbers are self-consistent and reproducible ------------------------


def test_volume_balance_closes_for_every_row(tmp_path) -> None:
    result = _run(tmp_path, thin_at_years=[10.0], disturbance_rate_per_year=0.01)
    check_volume_balance(result.rows)  # raises if it does not


def test_a_row_whose_balance_does_not_close_is_rejected() -> None:
    with pytest.raises(ValueError, match="Volume balance"):
        check_volume_balance(
            [
                {
                    "stand_id": 1,
                    "initial_volume_m3": 100.0,
                    "gross_growth_m3": 10.0,
                    "disturbance_loss_m3": 0.0,
                    "harvested_m3": 0.0,
                    "net_volume_m3": 999.0,
                }
            ]
        )


def test_the_run_is_reproducible_from_its_seed(tmp_path) -> None:
    one = _run(tmp_path / "one")
    two = _run(tmp_path / "two")
    assert one.rows == two.rows

    quality_one = json.loads(one.artifacts.quality_report_path.read_text(encoding="utf-8"))
    quality_two = json.loads(two.artifacts.quality_report_path.read_text(encoding="utf-8"))
    assert quality_one["determinism_hash"] == quality_two["determinism_hash"]


def test_each_stand_s_seed_derives_from_the_scenario_s(tmp_path) -> None:
    """Stand order cannot change a stand's numbers."""
    forwards = _run(tmp_path / "fwd", stands=_stands(3))
    backwards = _run(tmp_path / "rev", stands=list(reversed(_stands(3))))
    by_id = {row["stand_id"]: row for row in backwards.rows}
    for row in forwards.rows:
        assert by_id[row["stand_id"]]["stand_seed"] == row["stand_seed"]


def test_summary_columns_are_the_schema_s(tmp_path) -> None:
    result = _run(tmp_path)
    rows = load_scenario_summary(result.artifacts.scenario_summary_path)
    assert set(rows[0]) == set(SCENARIO_SUMMARY_COLUMNS)


# --- what a run was worth ----------------------------------------------------


def _valuing_run(tmp_path, *, price_identity: PricelistIdentity | None = None, **kwargs):
    kwargs.setdefault("thin_at_years", [10.0])
    return _run(
        tmp_path,
        config=_ValuingConfig(
            preset_id="test",
            scenario_id="baseline",
            region="Testland",
            required_artifacts_=REQUIRED_ARTIFACTS,
        ),
        valuation=_valuation(identity=price_identity),
        mean_tree=_mean_tree,
        **kwargs,
    )


def test_a_run_that_prices_nothing_says_so_rather_than_reporting_zero(tmp_path) -> None:
    """``valued`` is what keeps "earned nothing" apart from "never asked".

    This configuration has no valuation stage, so it removes wood and never asks
    what it fetched. A bare ``0`` beside a non-zero ``harvested_m3`` would read as
    a stand that sold its thinning for nothing.
    """
    result = _run(tmp_path, thin_at_years=[10.0])
    row = result.rows[0]

    assert row["harvested_m3"] > 0.0, "the wood came out"
    assert row["valued"] is False, "and nobody priced it"
    assert row["nominal_revenue"] == 0.0
    assert row["net_present_value"] == 0.0

    manifest = json.loads(result.artifacts.run_manifest_path.read_text(encoding="utf-8"))
    assert manifest["valuation"]["valued"] is False
    assert manifest["valuation"]["discount_rate"] is None
    # And no price list, for the reason there is no rate: naming one would say the
    # run priced its removals against it.
    assert manifest["valuation"]["price_list"] is None


def test_a_priced_run_writes_its_value_into_the_summary(tmp_path) -> None:
    """The point of the column: the number is in the artifact, not only in the result."""
    result = _valuing_run(tmp_path, discount_rate=0.03)
    row = result.rows[0]

    assert row["valued"] is True
    assert row["nominal_revenue"] > 0.0
    # The thinning falls in 2030, ten years after the run's first year.
    assert row["net_present_value"] == pytest.approx(row["nominal_revenue"] * 1.03**-10)
    assert result.net_present_value()[1] == pytest.approx(row["net_present_value"])

    rows = load_scenario_summary(result.artifacts.scenario_summary_path)
    assert rows[0]["net_present_value"] == pytest.approx(row["net_present_value"])


def test_a_priced_run_that_never_harvested_is_valued_at_zero(tmp_path) -> None:
    """``(True, 0)``: it was priced, and it earned nothing. Not the same as unpriced."""
    result = _valuing_run(tmp_path, discount_rate=0.03, thin_at_years=[])
    row = result.rows[0]
    assert row["harvested_m3"] == 0.0
    assert row["valued"] is True
    assert row["nominal_revenue"] == 0.0
    assert row["net_present_value"] == 0.0


def test_a_zero_rate_is_a_stated_preference_and_leaves_the_money_where_it_fell(
    tmp_path,
) -> None:
    result = _valuing_run(tmp_path, discount_rate=0.0)
    row = result.rows[0]
    assert row["net_present_value"] == pytest.approx(row["nominal_revenue"])

    manifest = json.loads(result.artifacts.run_manifest_path.read_text(encoding="utf-8"))
    assert manifest["valuation"]["discount_rate"] == 0.0


def test_the_manifest_records_the_rate_as_the_choice_it_is(tmp_path) -> None:
    """A discount rate is nobody's finding, and the manifest must not imply it is."""
    result = _valuing_run(tmp_path, discount_rate=0.03)
    manifest = json.loads(result.artifacts.run_manifest_path.read_text(encoding="utf-8"))
    valuation = manifest["valuation"]

    assert valuation["valued"] is True
    assert valuation["discount_rate"] == pytest.approx(0.03)
    assert valuation["base_year"] == 2020.0
    assert valuation["discount_from_forcing"] is False
    assert valuation["discount_source"]["author"] == "(none)"
    assert valuation["discount_source"]["year"] == 0
    assert "0.03" in valuation["discount_source"]["title"]
    assert valuation["discount_source"]["note"] == stated_choice("x").note


def test_the_manifest_records_which_price_list_the_money_is_in(tmp_path) -> None:
    """A revenue figure is a figure in a currency, against somebody's prices.

    Without this the summary's money columns are bare numbers: two runs' figures
    are comparable only under the same price list, and nothing said which one
    either used.
    """
    result = _valuing_run(
        tmp_path,
        discount_rate=0.03,
        price_identity=PricelistIdentity(
            name="Test fixture prices",
            currency="SEK",
            source=SourceReference(
                author="Test fixture",
                year=2026,
                title="A price list invented by this test, and saying so",
            ),
        ),
    )
    manifest = json.loads(result.artifacts.run_manifest_path.read_text(encoding="utf-8"))
    price_list = manifest["valuation"]["price_list"]

    assert result.rows[0]["nominal_revenue"] > 0.0
    assert price_list["name"] == "Test fixture prices"
    assert price_list["currency"] == "SEK"
    assert price_list["source"]["author"] == "Test fixture"
    assert price_list["source"]["year"] == 2026


def test_a_run_priced_against_its_own_table_says_so_in_the_manifest(tmp_path) -> None:
    """Unattributed prices are recorded as unattributed, not left to be assumed."""
    result = _valuing_run(tmp_path, discount_rate=0.03)
    manifest = json.loads(result.artifacts.run_manifest_path.read_text(encoding="utf-8"))
    price_list = manifest["valuation"]["price_list"]

    assert price_list["name"] == UNATTRIBUTED_PRICELIST_IDENTITY.name
    assert price_list["currency"] == UNATTRIBUTED_PRICELIST_IDENTITY.currency
    # The same sentinel the discount rate uses, and for the same reason: the
    # figures are the analyst's, and no publication says they are so.
    assert price_list["source"]["author"] == "(none)"
    assert price_list["source"]["year"] == 0


def test_a_discount_forcing_supplies_a_rate_that_varies_by_year(tmp_path) -> None:
    """A term structure is a forcing, because one exponent cannot express it."""
    term_structure = AnnualForcing(
        DISCOUNT,
        {2020 + n: 0.02 if n < 5 else 0.05 for n in range(21)},
        source=SourceReference(author="Test fixture", year=2026, title="A rate path, and says so"),
    )
    forced = _valuing_run(tmp_path / "forced", forcings=ForcingSet([term_structure]))
    flat = _valuing_run(tmp_path / "flat", discount_rate=0.02)

    # Five years at 2%, then five at 5%: less than ten years at 2% is worth.
    assert 0.0 < forced.rows[0]["net_present_value"] < flat.rows[0]["net_present_value"]
    assert forced.rows[0]["nominal_revenue"] == pytest.approx(flat.rows[0]["nominal_revenue"])

    manifest = json.loads(forced.artifacts.run_manifest_path.read_text(encoding="utf-8"))
    assert manifest["valuation"]["discount_from_forcing"] is True
    assert manifest["valuation"]["discount_rate"] is None
    # The citation is in forcings_applied rather than copied into two places.
    assert manifest["valuation"]["discount_source"] is None
    assert manifest["forcings_applied"][0]["source"]["year"] == 2026


def test_a_priced_run_must_say_what_it_discounts_at(tmp_path) -> None:
    """Otherwise the artifact carries a net present value with nothing behind it."""
    with pytest.raises(ValueError, match="needs a rate to discount at"):
        _valuing_run(tmp_path)


def test_a_rate_without_anything_to_discount_is_refused(tmp_path) -> None:
    """Recording it would say the run applied it."""
    with pytest.raises(ValueError, match="declares no 'valuation' stage"):
        _run(tmp_path, discount_rate=0.03)


# --- the money identities ----------------------------------------------------


def _money_row(**overrides) -> dict:
    row = {
        "stand_id": 1,
        "harvested_m3": 10.0,
        "valued": True,
        "nominal_revenue": 100.0,
        "net_present_value": 90.0,
    }
    row.update(overrides)
    return row


def test_value_consistency_accepts_all_three_states() -> None:
    check_value_consistency(
        [
            _money_row(valued=False, nominal_revenue=0.0, net_present_value=0.0),
            _money_row(harvested_m3=0.0, nominal_revenue=0.0, net_present_value=0.0),
            _money_row(),
        ]
    )


def test_revenue_on_a_row_nothing_priced_is_rejected() -> None:
    with pytest.raises(ValueError, match="not valued"):
        check_value_consistency([_money_row(valued=False)])


def test_revenue_without_a_harvest_is_rejected() -> None:
    """Only a merchantable removal reaches the ledger, so this cannot happen."""
    with pytest.raises(ValueError, match="harvested nothing"):
        check_value_consistency([_money_row(harvested_m3=0.0)])


def test_a_money_figure_that_is_not_a_number_is_rejected() -> None:
    with pytest.raises(ValueError, match="finite"):
        check_value_consistency([_money_row(net_present_value=float("nan"))])


def test_a_summary_from_the_previous_schema_is_named_rather_than_diffed(tmp_path) -> None:
    """A 2.0 artifact does not load, and the reader is told what it is holding."""
    import pandas as pd

    path = tmp_path / "old_summary.parquet"
    pd.DataFrame.from_records(
        [{column: 0.0 for column in SCENARIO_SUMMARY_COLUMNS[:8]}],
        columns=SCENARIO_SUMMARY_COLUMNS[:8],
    ).to_parquet(path, index=False)

    with pytest.raises(ValueError, match="schema 2.0 summary"):
        load_scenario_summary(path)


# --- failure modes -----------------------------------------------------------


def test_an_unknown_stage_is_named_rather_than_skipped() -> None:
    with pytest.raises(ValueError, match="Unknown stage"):
        build_pipeline(("growth", "teleport"), StageContext(volume=_volume))


def test_the_calendar_step_is_prepended_and_not_a_declared_stage() -> None:
    """Which years a run covers belongs to the run, not to the scenario."""
    steps = build_pipeline(("growth",), StageContext(volume=_volume), start_year=2020)
    assert [step.name for step in steps] == ["calendar", "growth"]
    assert "calendar" not in known_stages()


def test_known_stages_are_the_registry_s() -> None:
    assert known_stages() == ("disturbance", "growth", "management", "valuation")


def test_a_valuation_stage_without_settings_is_an_error() -> None:
    """Skipping it would report a run as having valued its removals at nothing."""
    with pytest.raises(ValueError, match="ValuationSettings"):
        build_pipeline(("valuation",), StageContext(volume=_volume))


def test_a_run_needs_stands_and_periods(tmp_path) -> None:
    with pytest.raises(ValueError, match="n_steps must be > 0"):
        _run(tmp_path, n_steps=0)
    with pytest.raises(ValueError, match="at least one stand"):
        _run(tmp_path, stands=[])
