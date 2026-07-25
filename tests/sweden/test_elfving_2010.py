import math

import pytest

import pyforestry.sweden.blocks.elfving_2010 as elfving_2010_module
from pyforestry.base.helpers import CircularPlot, Stand, Tree, TreeSpecies
from pyforestry.base.helpers.primitives import (
    Age,
    QuadraticMeanDiameter,
    SiteBase,
    StandBasalArea,
    Stems,
    basal_area_growth_cm2_to_diameter_growth_cm,
    diameter_growth_to_basal_area_growth_cm2,
)
from pyforestry.sweden.blocks.elfving_2010 import (
    Elfving2010Model,
    stand_basal_area_growth_elfving_2009,
)


class _DummySite(SiteBase):
    def compute_attributes(self) -> None:  # pragma: no cover - simple stub
        return None


def test_stand_basal_area_growth_fixture():
    # Reference vectors for the Elfving 2009/2010 stand basal-area growth model.
    # Columns:
    # Plot, Gt, Gc, Gg, Gb, G10, Gtot, N10, Berald, SIS1, barrdel, tdel, gdel, bdel,
    # thinned_0_10_years_flag, thinned_10_30_years_flag,
    # faltskik, veg, torv, moist, wet, dikat, kyl, iGber
    data = [
        [
            1,
            529,
            0,
            538,
            0,
            10.68,
            10.67,
            604.79,
            53.42,
            15,
            1,
            0.496,
            0.504,
            0,
            1,
            0,
            13,
            0,
            0,
            0,
            0,
            0,
            0.007,
            2.202,
        ],
        [
            2,
            128,
            0,
            1517,
            322,
            7.13,
            19.67,
            413.8,
            65.28,
            14,
            0.836,
            0.065,
            0.771,
            0.164,
            0,
            0,
            13,
            0,
            0,
            0,
            0,
            0,
            0.01,
            1.153,
        ],
        [
            3,
            1118,
            0,
            0,
            54,
            8.33,
            11.72,
            604.79,
            49.05,
            16,
            0.954,
            0.954,
            0,
            0.046,
            0,
            0,
            15,
            -3,
            0,
            0,
            0,
            0,
            0.006,
            1.568,
        ],
        [
            4,
            686,
            0,
            248,
            63,
            9.26,
            9.97,
            445.63,
            47.64,
            20,
            0.937,
            0.688,
            0.249,
            0.063,
            0,
            0,
            6,
            2,
            0,
            0,
            0,
            0,
            0.005,
            2.113,
        ],
        [
            5,
            121,
            0,
            541,
            120,
            6.91,
            7.82,
            286.48,
            51.29,
            19,
            0.847,
            0.155,
            0.692,
            0.153,
            0,
            0,
            9,
            1.5,
            0,
            0,
            0,
            0,
            0.006,
            1.56,
        ],
        [
            6,
            149,
            0,
            122,
            1090,
            13.55,
            13.61,
            827.61,
            46.52,
            22,
            0.199,
            0.109,
            0.09,
            0.801,
            0,
            0,
            9,
            1.5,
            0,
            0,
            0,
            0,
            0.005,
            2.022,
        ],
        [
            7,
            707,
            0,
            0,
            271,
            9.77,
            9.78,
            413.8,
            47.22,
            22,
            0.723,
            0.723,
            0,
            0.277,
            1,
            0,
            5,
            2.5,
            0,
            0,
            0,
            1,
            0.003,
            2.573,
        ],
        [
            8,
            1314,
            0,
            167,
            0,
            12.38,
            14.81,
            668.45,
            47.12,
            16,
            1,
            0.887,
            0.113,
            0,
            0,
            0,
            14,
            -0.5,
            0,
            0,
            0,
            0,
            0.002,
            2.19,
        ],
        [
            9,
            1753,
            0,
            0,
            0,
            17.53,
            17.53,
            572.96,
            85.54,
            21,
            1,
            1,
            0,
            0,
            0,
            1,
            13,
            0,
            0,
            0,
            0,
            1,
            0.002,
            1.961,
        ],
        [
            10,
            2509,
            0,
            0,
            0,
            25.09,
            25.09,
            413.8,
            131.4,
            19,
            1,
            1,
            0,
            0,
            0,
            0,
            14,
            -0.5,
            0,
            0,
            0,
            0,
            0.002,
            1.369,
        ],
        [
            11,
            0,
            0,
            1238,
            292,
            15.24,
            15.3,
            572.96,
            118.48,
            13,
            0.809,
            0,
            0.809,
            0.191,
            0,
            0,
            13,
            0,
            0,
            0,
            0,
            0,
            0.037,
            1.146,
        ],
        [
            12,
            0,
            0,
            1160,
            816,
            15.01,
            19.76,
            509.3,
            114.32,
            12,
            0.587,
            0,
            0.587,
            0.413,
            0,
            0,
            13,
            0,
            0,
            0,
            0,
            0,
            0.067,
            0.834,
        ],
        [
            13,
            0,
            0,
            2807,
            283,
            30.34,
            30.9,
            700.28,
            168.27,
            13,
            0.908,
            0,
            0.908,
            0.092,
            0,
            0,
            13,
            0,
            0,
            0,
            0,
            0,
            0.033,
            1.274,
        ],
        [
            14,
            2781,
            0,
            1147,
            248,
            35.71,
            41.76,
            891.27,
            124.11,
            19,
            0.941,
            0.666,
            0.275,
            0.059,
            0,
            0,
            13,
            0,
            0,
            0,
            0,
            0,
            0.005,
            1.741,
        ],
        [
            15,
            0,
            0,
            1510,
            0,
            21.27,
            21.28,
            827.61,
            135.06,
            14,
            0.71,
            0,
            0.71,
            0,
            0,
            0,
            13,
            0,
            0,
            0,
            0,
            0,
            0.006,
            1.384,
        ],
        [
            16,
            984,
            0,
            0,
            0,
            9.84,
            9.84,
            541.13,
            82.86,
            19,
            1,
            1,
            0,
            0,
            1,
            0,
            14,
            -0.5,
            0,
            0,
            0,
            0,
            0.007,
            1.543,
        ],
        [
            17,
            1141,
            0,
            1047,
            0,
            21.89,
            21.88,
            923.1,
            128.97,
            20,
            1,
            0.521,
            0.479,
            0,
            0,
            0,
            13,
            0,
            0,
            0,
            0,
            0,
            0.005,
            1.546,
        ],
        [
            18,
            1301,
            0,
            0,
            0,
            13.01,
            13.01,
            923.1,
            47.66,
            18,
            1,
            1,
            0,
            0,
            0,
            0,
            14,
            -0.5,
            0,
            0,
            0,
            0,
            0.005,
            2.383,
        ],
        [
            19,
            855,
            0,
            0,
            0,
            6.14,
            8.55,
            509.3,
            45.88,
            15,
            1,
            1,
            0,
            0,
            0,
            0,
            14,
            -0.5,
            0,
            0,
            0,
            0,
            0.005,
            1.552,
        ],
        [
            20,
            935,
            0,
            109,
            0,
            9.35,
            10.44,
            604.79,
            51.79,
            15,
            1,
            0.896,
            0.104,
            0,
            0,
            0,
            13,
            0,
            0,
            0,
            0,
            0,
            0.01,
            1.814,
        ],
        [
            21,
            0,
            0,
            3399,
            0,
            33.99,
            33.99,
            604.79,
            176.78,
            17,
            1,
            0,
            1,
            0,
            0,
            0,
            5,
            2.5,
            0,
            0,
            0,
            0,
            0.03,
            1.594,
        ],
        [
            22,
            0,
            0,
            1069,
            33,
            7.09,
            11.02,
            509.3,
            101.76,
            13,
            0.97,
            0,
            0.97,
            0.03,
            0,
            0,
            13,
            0,
            0,
            0,
            0,
            0,
            0.03,
            0.949,
        ],
        [
            23,
            0,
            0,
            1577,
            130,
            16.02,
            17.07,
            572.96,
            136.16,
            13,
            0.924,
            0,
            0.924,
            0.076,
            0,
            0,
            13,
            0,
            0,
            0,
            0,
            0,
            0.033,
            1.132,
        ],
        [
            24,
            1045,
            0,
            0,
            0,
            10.45,
            10.45,
            604.79,
            53.52,
            15,
            1,
            1,
            0,
            0,
            0,
            0,
            15,
            -3,
            0,
            0,
            0,
            0,
            0.014,
            1.66,
        ],
        [
            25,
            1329,
            0,
            214,
            0,
            15.43,
            15.43,
            350.14,
            130.77,
            16,
            1,
            0.861,
            0.139,
            0,
            0,
            0,
            13,
            0,
            0,
            0,
            0,
            0,
            0.183,
            1.097,
        ],
        [
            26,
            2067,
            0,
            0,
            0,
            20.67,
            20.67,
            668.45,
            102.98,
            15,
            1,
            1,
            0,
            0,
            0,
            0,
            14,
            -0.5,
            0,
            0,
            0,
            0,
            0.005,
            1.548,
        ],
        [
            27,
            1336,
            0,
            35,
            0,
            10.31,
            13.71,
            604.79,
            98.99,
            13,
            1,
            0.974,
            0.026,
            0,
            0,
            0,
            14,
            -0.5,
            0,
            0,
            0,
            0,
            0.005,
            1.132,
        ],
        [
            28,
            2014,
            0,
            0,
            144,
            20.14,
            21.58,
            190.99,
            153.08,
            19,
            0.933,
            0.933,
            0,
            0.067,
            1,
            0,
            13,
            0,
            0,
            0,
            0,
            0,
            0.003,
            1.105,
        ],
        [
            29,
            794,
            0,
            0,
            131,
            9.23,
            9.25,
            159.15,
            119.57,
            18,
            0.858,
            0.858,
            0,
            0.142,
            1,
            0,
            13,
            0,
            0,
            0,
            0,
            0,
            0.006,
            0.878,
        ],
        [
            30,
            1664,
            0,
            982,
            0,
            21.7,
            26.46,
            732.11,
            103.53,
            19,
            1,
            0.629,
            0.371,
            0,
            0,
            0,
            13,
            0,
            0,
            0,
            0,
            0,
            0.006,
            1.66,
        ],
        [
            31,
            360,
            0,
            135,
            0,
            4.66,
            4.95,
            286.48,
            50.97,
            14,
            1,
            0.727,
            0.273,
            0,
            0,
            0,
            14,
            -0.5,
            0,
            0,
            0,
            0,
            0.006,
            1.134,
        ],
        [
            32,
            139,
            0,
            707,
            258,
            6.89,
            11.04,
            381.97,
            58.49,
            13,
            0.766,
            0.126,
            0.64,
            0.234,
            0,
            0,
            13,
            0,
            0,
            0,
            0,
            0,
            0.006,
            1.241,
        ],
        [
            33,
            1709,
            0,
            0,
            0,
            17.09,
            17.09,
            572.96,
            60.2,
            19,
            1,
            1,
            0,
            0,
            1,
            0,
            13,
            0,
            0,
            0,
            0,
            0,
            0.006,
            2.502,
        ],
        [
            34,
            741,
            0,
            0,
            76,
            8.17,
            8.17,
            381.97,
            137.07,
            13,
            0.907,
            0.907,
            0,
            0.093,
            1,
            0,
            14,
            -0.5,
            0,
            0,
            0,
            0,
            0.007,
            0.887,
        ],
        [
            35,
            846,
            0,
            86,
            14,
            9.25,
            9.46,
            477.46,
            54.97,
            13,
            0.985,
            0.894,
            0.091,
            0.015,
            0,
            0,
            14,
            -0.5,
            0,
            0,
            0,
            0,
            0.007,
            1.6,
        ],
        [
            36,
            657,
            0,
            0,
            0,
            6.57,
            6.57,
            318.31,
            128.34,
            13,
            1,
            1,
            0,
            0,
            1,
            0,
            14,
            -0.5,
            0,
            0,
            0,
            0,
            0.007,
            0.816,
        ],
        [
            37,
            1952,
            0,
            544,
            74,
            11.64,
            25.7,
            859.44,
            64.33,
            17,
            0.971,
            0.76,
            0.212,
            0.029,
            0,
            0,
            14,
            -0.5,
            0,
            0,
            0,
            0,
            0.007,
            1.637,
        ],
        [
            38,
            29,
            0,
            1752,
            723,
            11.38,
            25.04,
            859.44,
            86.47,
            12,
            0.711,
            0.012,
            0.7,
            0.289,
            0,
            0,
            12,
            1,
            0,
            0,
            0,
            0,
            0.006,
            1.313,
        ],
        [
            39,
            1685,
            0,
            0,
            0,
            16.08,
            16.85,
            827.61,
            75.96,
            19,
            1,
            1,
            0,
            0,
            0,
            0,
            14,
            -0.5,
            0,
            0,
            0,
            0,
            0.007,
            1.844,
        ],
        [
            40,
            709,
            0,
            808,
            1550,
            19.05,
            30.67,
            572.96,
            134.64,
            17,
            0.495,
            0.231,
            0.263,
            0.505,
            0,
            0,
            13,
            0,
            0,
            0,
            0,
            0,
            0.037,
            0.906,
        ],
        [
            41,
            0,
            0,
            589,
            317,
            5.89,
            9.06,
            222.82,
            104.26,
            13,
            0.65,
            0,
            0.65,
            0.35,
            0,
            0,
            13,
            0,
            0,
            0,
            0,
            0,
            0.027,
            0.622,
        ],
        [
            42,
            2406,
            0,
            0,
            0,
            20.52,
            24.06,
            763.94,
            91.88,
            16,
            1,
            1,
            0,
            0,
            0,
            0,
            14,
            -0.5,
            0,
            0,
            0,
            0,
            0.027,
            1.675,
        ],
        [
            43,
            1157,
            0,
            0,
            0,
            11.47,
            11.57,
            381.97,
            166.36,
            16,
            1,
            1,
            0,
            0,
            0,
            0,
            14,
            -0.5,
            0,
            0,
            0,
            0,
            0.03,
            0.826,
        ],
        [
            44,
            1127,
            0,
            0,
            29,
            8.06,
            11.56,
            190.99,
            171.69,
            12,
            0.975,
            0.975,
            0,
            0.025,
            0,
            0,
            15,
            -3,
            0,
            0,
            0,
            0,
            0.027,
            0.494,
        ],
        [
            45,
            89,
            0,
            927,
            298,
            8.85,
            13.14,
            350.14,
            131.87,
            11,
            0.773,
            0.068,
            0.705,
            0.227,
            0,
            0,
            14,
            -0.5,
            0,
            0,
            0,
            0,
            0.05,
            0.682,
        ],
        [
            46,
            2215,
            0,
            0,
            30,
            20.59,
            22.45,
            636.62,
            117.07,
            15,
            0.987,
            0.987,
            0,
            0.013,
            0,
            0,
            14,
            -0.5,
            0,
            0,
            0,
            0,
            0.027,
            1.389,
        ],
        [
            47,
            951,
            0,
            0,
            0,
            6.72,
            9.51,
            477.46,
            78.35,
            14,
            1,
            1,
            0,
            0,
            1,
            0,
            14,
            -0.5,
            0,
            0,
            0,
            0,
            0.027,
            1.232,
        ],
        [
            48,
            2175,
            0,
            437,
            0,
            26.12,
            26.12,
            509.3,
            138.16,
            19,
            1,
            0.833,
            0.167,
            0,
            0,
            1,
            13,
            0,
            0,
            0,
            0,
            0,
            0.006,
            1.51,
        ],
        [
            49,
            1369,
            0,
            0,
            0,
            13.69,
            13.69,
            318.31,
            129.96,
            15,
            1,
            1,
            0,
            0,
            1,
            0,
            14,
            -0.5,
            0,
            0,
            0,
            0,
            0.008,
            1.142,
        ],
    ]

    for row in data:
        g10 = row[5]
        gtot = row[6]
        n10 = row[7]
        berald = row[8]
        sis1 = row[9]
        barrdel = row[10]
        tdel = row[11]
        gdel = row[12]
        bdel = row[13]
        thinned_0_10_years_flag = int(row[14])
        thinned_10_30_years_flag = int(row[15])
        veg = row[17]
        torv = int(row[18])
        moist = int(row[19])
        wet = int(row[20])
        dikat = int(row[21])
        kyl = row[22]
        igber = row[23]

        result = stand_basal_area_growth_elfving_2009(
            ln_mean_age=math.log(berald),
            conifer_share_per_age=barrdel / berald,
            pine_share_times_veg=tdel * veg,
            birch_share_sq=bdel**2,
            birch_share_cold=bdel * kyl,
            basal_area_survived_m2_ha=g10,
            basal_area_all_m2_ha=gtot,
            stem_number_factor=n10 / (n10 + 80.0),
            veg=veg,
            peat=torv,
            moist=moist,
            wet=wet,
            site_index_m=sis1,
            ditch=dikat,
            fertilized=0,
            edge=0,
            split=0,
            thinned_0_10_years_flag=thinned_0_10_years_flag,
            thinned_10_30_years_flag=thinned_10_30_years_flag,
            ln_relative_basal_area=0.0,
            pine_share=tdel,
            spruce_share=gdel,
            use_edge_effects=False,
        )
        assert result == pytest.approx(igber, abs=0.003)


def _build_simple_stand():
    site = _DummySite(latitude=60.0, longitude=15.0)
    plot = CircularPlot(
        id=1,
        area_m2=200.0,
        trees=[
            Tree(species="Pinus sylvestris", diameter_cm=20.0, age=Age.DBH(30), weight_n=1.0),
            Tree(species="Picea abies", diameter_cm=18.0, age=Age.DBH(28), weight_n=1.0),
        ],
    )
    return Stand(site=site, plots=[plot])


def test_elfving_model_scales_with_dt():
    model = Elfving2010Model()
    stand_5 = _build_simple_stand()
    ctx_5 = model.build_context(stand_5, mode_hint="tree_list")
    ctx_5.attrs.update(
        {
            "site_index_m": 20.0,
            "temperature_sum_dd": 1200.0,
            "latitude_deg": 60.0,
            "altitude_m": 100.0,
            "vegetation_index": 1.5,
            "field_estimated_basal_area_m2_ha": 20.0,
        }
    )
    model.update_step(ctx_5, 5.0)
    inc_5 = ctx_5.plots[0].trees[0].diameter_cm - 20.0

    stand_10 = _build_simple_stand()
    ctx_10 = model.build_context(stand_10, mode_hint="tree_list")
    ctx_10.attrs.update(ctx_5.attrs)
    model.update_step(ctx_10, 10.0)
    inc_10 = ctx_10.plots[0].trees[0].diameter_cm - 20.0

    assert inc_10 == pytest.approx(inc_5 * 2.0, rel=1e-6)


def _build_tree_list_context(
    model: Elfving2010Model,
    stand: Stand | None = None,
    *,
    include_field_ba: bool = True,
):
    stand = stand or _build_simple_stand()
    ctx = model.build_context(stand, mode_hint="tree_list")
    attrs = {
        "site_index_m": 20.0,
        "temperature_sum_dd": 1200.0,
        "latitude_deg": 60.0,
        "altitude_m": 100.0,
        "vegetation_index": 1.5,
    }
    if include_field_ba:
        attrs["field_estimated_basal_area_m2_ha"] = 20.0
    ctx.attrs.update(attrs)
    return ctx


def _build_aggregate_context(model: Elfving2010Model):
    ctx = model.build_context(_build_simple_stand(), mode_hint="aggregate")
    ctx.attrs.update(
        {
            "site_index_m": 20.0,
            "temperature_sum_dd": 1200.0,
            "mean_age_total_years": 50.0,
            "vegetation_index": 1.5,
        }
    )
    return ctx


def _set_species_metrics(ctx) -> None:
    contorta = TreeSpecies.Sweden.pinus_contorta
    spruce = TreeSpecies.Sweden.picea_abies
    birch = TreeSpecies.Sweden.betula_pubescens
    ctx._metrics = {
        "BasalArea": {
            "TOTAL": StandBasalArea(20.0, species=None),
            contorta: StandBasalArea(6.0, species=contorta),
            spruce: StandBasalArea(9.0, species=spruce),
            birch: StandBasalArea(5.0, species=birch),
        },
        "Stems": {
            "TOTAL": Stems(500.0, species=None),
            contorta: Stems(150.0, species=contorta),
            spruce: Stems(250.0, species=spruce),
        },
        "QMD": {"TOTAL": QuadraticMeanDiameter(20.0)},
    }


def test_thinning_response_boosts_aggregate_basal_area_growth():
    from pyforestry.sweden.growth.elfving_2010.thinning_response import ThinningEvent

    model = Elfving2010Model()

    ctx_unmanaged = _build_aggregate_context(model)
    _set_species_metrics(ctx_unmanaged)
    ba_before = float(ctx_unmanaged.metrics["BasalArea"]["TOTAL"])
    model.update_step(ctx_unmanaged, 5.0)
    growth_unmanaged = float(ctx_unmanaged.metrics["BasalArea"]["TOTAL"]) - ba_before

    ctx_thinned = _build_aggregate_context(model)
    _set_species_metrics(ctx_thinned)
    ctx_thinned.attrs["thinning_simulated"] = True
    ctx_thinned.attrs["thinning_history"] = [
        ThinningEvent(years_since_thinning=0.0, proportion_basal_area_removed=0.3)
    ]
    model.update_step(ctx_thinned, 5.0)
    growth_thinned = float(ctx_thinned.metrics["BasalArea"]["TOTAL"]) - ba_before

    assert growth_unmanaged > 0.0
    assert growth_thinned > growth_unmanaged


def test_thinning_response_inactive_without_simulated_thinning():
    from pyforestry.sweden.growth.elfving_2010.thinning_response import ThinningEvent

    model = Elfving2010Model()

    ctx_ref = _build_aggregate_context(model)
    _set_species_metrics(ctx_ref)
    ba_before = float(ctx_ref.metrics["BasalArea"]["TOTAL"])
    model.update_step(ctx_ref, 5.0)
    growth_ref = float(ctx_ref.metrics["BasalArea"]["TOTAL"]) - ba_before

    # History present but no `thinning_simulated` flag -> multiplier stays 1.0.
    ctx_history = _build_aggregate_context(model)
    _set_species_metrics(ctx_history)
    ctx_history.attrs["thinning_history"] = [
        ThinningEvent(years_since_thinning=0.0, proportion_basal_area_removed=0.3)
    ]
    model.update_step(ctx_history, 5.0)
    growth_history = float(ctx_history.metrics["BasalArea"]["TOTAL"]) - ba_before

    assert growth_history == pytest.approx(growth_ref)


def test_elfving_model_rejects_non_positive_dt():
    model = Elfving2010Model()
    ctx = model.build_context(_build_simple_stand(), mode_hint="tree_list")
    with pytest.raises(ValueError, match="dt must be positive"):
        model.update_step(ctx, 0.0)


def test_update_step_tree_list_handles_empty_tree_inventory():
    model = Elfving2010Model()
    stand = Stand(
        site=_DummySite(latitude=60.0, longitude=15.0),
        plots=[CircularPlot(id=1, area_m2=100.0, trees=[])],
    )
    ctx = model.build_context(stand, mode_hint="tree_list")
    model.update_step(ctx, 5.0)
    assert ctx.state["years_since_thin"] == pytest.approx(5.0)


def test_update_tree_list_returns_when_basal_area_is_zero():
    model = Elfving2010Model()
    ctx = _build_tree_list_context(model)
    ctx._metrics["BasalArea"]["TOTAL"] = StandBasalArea(0.0, species=None)
    model._update_tree_list(ctx, None, 1.0)


@pytest.mark.parametrize("group", ["birch", "aspen", "beech", "oak", "precious", "trivial"])
def test_group_dispatch_covers_remaining_tree_kernels(group: str):
    model = Elfving2010Model()
    group_ba = {
        "pine": 10.0,
        "spruce": 10.0,
        "birch": 5.0,
        "aspen": 2.0,
        "beech": 2.0,
        "oak": 2.0,
        "precious": 2.0,
        "trivial": 1.0,
    }
    value = model._ln_d2_growth_for_group(
        group=group,
        diameter_cm=20.0,
        bal_over_dbh=1.0,
        age_bh_years=40.0,
        overstorey=1,
        bawad_total=25.0,
        qmd_total=20.0,
        basal_area_total=30.0,
        group_ba=group_ba,
        gotland=0,
        temperature_sum_dd=1100.0,
        site_index_m=22.0,
        rich=1,
        herb=1,
        fertilized=0,
        thinned_0_10_years_flag=0,
        thinned_11_25_years_flag=0,
        split=0,
        edge=0,
        field_ba=25.0,
        distance_to_coast_km=30.0,
        latitude_deg=59.0,
        altitude_m=120.0,
    )
    assert math.isfinite(value)


def test_update_tree_list_validates_negative_diameter_increment(monkeypatch):
    model = Elfving2010Model()
    ctx = _build_tree_list_context(model)
    monkeypatch.setattr(elfving_2010_module, "exp", lambda _x: -1.0)
    with pytest.raises(ValueError, match="non-negative"):
        model._update_tree_list(ctx, None, 1.0)


def test_update_tree_list_validates_unrealistic_diameter_increment(monkeypatch):
    model = Elfving2010Model()
    ctx = _build_tree_list_context(model)
    monkeypatch.setattr(elfving_2010_module, "exp", lambda _x: 5_000_000.0)
    with pytest.raises(ValueError, match="> 1000"):
        model._update_tree_list(ctx, None, 1.0)


def test_update_tree_list_uses_total_basal_area_when_field_value_missing(monkeypatch):
    model = Elfving2010Model()
    stand = Stand(
        site=_DummySite(latitude=60.0, longitude=15.0),
        plots=[
            CircularPlot(
                id=1,
                area_m2=200.0,
                trees=[
                    Tree(
                        species="Pinus sylvestris", diameter_cm=0.0, age=Age.DBH(20), weight_n=1.0
                    ),
                    Tree(species="Picea abies", diameter_cm=18.0, age=Age.DBH(25), weight_n=1.0),
                ],
            )
        ],
    )
    ctx = _build_tree_list_context(model, stand, include_field_ba=False)
    captured = {}

    def _capture_apply(self, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(Elfving2010Model, "_apply_stand_calibration", _capture_apply)
    model._update_tree_list(ctx, None, 1.0)
    assert captured["field_ba"] == pytest.approx(float(ctx.metrics["BasalArea"]["TOTAL"]))
    assert captured["base_increments"][0] == 0.0


def test_apply_stand_calibration_returns_when_no_positive_diameters():
    model = Elfving2010Model()
    ctx = _build_tree_list_context(model)
    zero_tree = Tree(species="Pinus sylvestris", diameter_cm=0.0, age=Age.DBH(20), weight_n=1.0)
    model._apply_stand_calibration(
        ctx=ctx,
        trees=[zero_tree],
        expansions=[1.0],
        base_increments=[1.0],
        site=None,
        site_index_m=20.0,
        mean_age_total=30.0,
        field_ba=20.0,
        scale=1.0,
    )
    assert zero_tree.diameter_cm == pytest.approx(0.0)


def test_apply_stand_calibration_covers_layer_and_species_branches():
    model = Elfving2010Model()
    ctx = _build_tree_list_context(model)
    trees = [
        Tree(species="Pinus contorta", diameter_cm=20.0, age=Age.DBH(30), weight_n=1.0),
        Tree(species="Betula pubescens", diameter_cm=12.0, age=Age.DBH(25), weight_n=1.0),
        Tree(species="Picea abies", diameter_cm=8.0, age=Age.DBH(20), weight_n=1.0),
        Tree(species="Pinus sylvestris", diameter_cm=0.0, age=Age.DBH(15), weight_n=1.0),
    ]
    trees[0].is_overstorey = True
    trees[1].is_overstorey = False
    trees[2].is_overstorey = False
    trees[3].is_overstorey = False
    before = trees[0].diameter_cm
    model._apply_stand_calibration(
        ctx=ctx,
        trees=trees,
        expansions=[1.0, 1.0, 1.0, 1.0],
        base_increments=[1.0, 1.0, 0.0, 1.0],
        site=None,
        site_index_m=20.0,
        mean_age_total=35.0,
        field_ba=25.0,
        scale=1.0,
    )
    assert trees[0].diameter_cm > before


def test_apply_stand_calibration_uses_per_tree_expansion_for_layer_growth(monkeypatch):
    model = Elfving2010Model()
    ctx = _build_tree_list_context(model)
    trees = [
        Tree(species="Pinus sylvestris", diameter_cm=20.0, age=Age.DBH(30), weight_n=1.0),
        Tree(species="Picea abies", diameter_cm=20.0, age=Age.DBH(30), weight_n=1.0),
    ]
    for tree in trees:
        tree.is_overstorey = False
        tree.mortality = 0.0

    monkeypatch.setattr(
        elfving_2010_module,
        "stand_basal_area_growth_elfving_2009",
        lambda **_kwargs: 0.5,
    )

    model._apply_stand_calibration(
        ctx=ctx,
        trees=trees,
        expansions=[1.0, 3.0],
        base_increments=[1.0, 1.0],
        site=None,
        site_index_m=20.0,
        mean_age_total=35.0,
        field_ba=25.0,
        scale=1.0,
    )

    ba_growth_cm2 = diameter_growth_to_basal_area_growth_cm2(20.0, 1.0)
    expected_tree_growth = ba_growth_cm2 * (1.0 + 3.0) * 1.0e-4
    expected_ratio = min(2.0, 0.5 / expected_tree_growth)
    expected_adj_inc = basal_area_growth_cm2_to_diameter_growth_cm(
        20.0,
        ba_growth_cm2 * expected_ratio,
    )
    expected_dbh = 20.0 + expected_adj_inc

    assert trees[0].diameter_cm == pytest.approx(expected_dbh)
    assert trees[1].diameter_cm == pytest.approx(expected_dbh)


def test_update_step_routes_to_aggregate_mode():
    model = Elfving2010Model()
    ctx = _build_aggregate_context(model)
    _set_species_metrics(ctx)
    model.update_step(ctx, 5.0)
    assert ctx.state["years_since_thin"] == pytest.approx(5.0)


def test_update_aggregate_returns_when_totals_are_not_positive():
    model = Elfving2010Model()
    ctx = _build_aggregate_context(model)
    ctx._metrics = {
        "BasalArea": {"TOTAL": StandBasalArea(0.0, species=None)},
        "Stems": {"TOTAL": Stems(100.0, species=None)},
        "QMD": {},
    }
    model._update_aggregate(ctx, None, 1.0)


def test_update_aggregate_requires_species_level_metrics():
    model = Elfving2010Model()
    ctx = _build_aggregate_context(model)
    ctx._metrics = {
        "BasalArea": {"TOTAL": StandBasalArea(20.0, species=None)},
        "Stems": {"TOTAL": Stems(500.0, species=None)},
        "QMD": {},
    }
    with pytest.raises(ValueError, match="species-level"):
        model._update_aggregate(ctx, None, 1.0)


def test_update_aggregate_requires_mean_age_attribute():
    model = Elfving2010Model()
    ctx = _build_aggregate_context(model)
    _set_species_metrics(ctx)
    ctx.attrs.pop("mean_age_total_years", None)
    with pytest.raises(ValueError, match="mean_age_total_years"):
        model._update_aggregate(ctx, None, 1.0)


def test_update_aggregate_updates_metrics_with_species_mix():
    model = Elfving2010Model()
    ctx = _build_aggregate_context(model)
    _set_species_metrics(ctx)
    model._update_aggregate(ctx, None, 1.0)
    assert float(ctx._metrics["BasalArea"]["TOTAL"]) > 0.0
    assert "TOTAL" in ctx._metrics["QMD"]


def test_update_aggregate_clamps_negative_basal_area(monkeypatch):
    model = Elfving2010Model()
    ctx = _build_aggregate_context(model)
    _set_species_metrics(ctx)
    monkeypatch.setattr(
        elfving_2010_module,
        "stand_basal_area_growth_elfving_2009",
        lambda **_kwargs: -1_000_000.0,
    )
    model._update_aggregate(ctx, None, 1.0)
    assert float(ctx._metrics["BasalArea"]["TOTAL"]) == pytest.approx(0.0)
