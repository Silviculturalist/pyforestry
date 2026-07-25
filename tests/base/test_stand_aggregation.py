"""Regression tests for the stand plot-aggregation fixes.

Covers: the absent-species over-count fix, Lorey's mean height (HL), the
species-group query API, and the standard-error (not population-SD) precision
convention.
"""

import math
import statistics

import pytest

from pyforestry.base.helpers import CircularPlot, Stand, Tree
from pyforestry.base.helpers.tree_species import parse_tree_species

PINE = parse_tree_species("pinus sylvestris")
SPRUCE = parse_tree_species("picea abies")
BIRCH = parse_tree_species("betula pendula")


def _radius_for(area_m2: float) -> float:
    return (area_m2 / math.pi) ** 0.5


def _ba_per_ha(diameter_cm: float, plot_area_ha: float) -> float:
    """Basal area per hectare of a single tree alone on a plot of the given area."""
    return math.pi * ((diameter_cm / 100.0) / 2.0) ** 2 / plot_area_ha


# --------------------------------------------------------------------------- #
# 1. Absent-species over-count fix
# --------------------------------------------------------------------------- #
def test_total_not_double_counted_when_species_absent_from_plots():
    """A species absent from a plot must count as zero there, not be skipped.

    Two 0.01-ha plots, pine-only on one and spruce-only on the other, each with a
    single 20 cm tree. The stand-mean total is the mean of the two plot totals
    (one tree's worth), NOT the sum of two per-species means (two trees' worth).
    """
    r = _radius_for(100.0)  # 0.01 ha
    plot_a = CircularPlot(id="A", radius_m=r, trees=[Tree(species=PINE, diameter_cm=20.0)])
    plot_b = CircularPlot(id="B", radius_m=r, trees=[Tree(species=SPRUCE, diameter_cm=20.0)])
    stand = Stand(plots=[plot_a, plot_b])

    one_tree = _ba_per_ha(20.0, 0.01)
    assert math.isclose(float(stand.BasalArea.TOTAL), one_tree, rel_tol=1e-9)
    assert math.isclose(float(stand.BasalArea(PINE)), one_tree / 2, rel_tol=1e-9)
    assert math.isclose(float(stand.BasalArea(SPRUCE)), one_tree / 2, rel_tol=1e-9)
    assert math.isclose(float(stand.Stems.TOTAL), 100.0, rel_tol=1e-9)
    assert math.isclose(float(stand.Stems(PINE)), 50.0, rel_tol=1e-9)


# --------------------------------------------------------------------------- #
# 2. Lorey's mean height (HL)
# --------------------------------------------------------------------------- #
def test_lorey_mean_height_total_and_species():
    trees = [
        Tree(species=PINE, diameter_cm=20.0, height_m=18.0),
        Tree(species=PINE, diameter_cm=30.0, height_m=24.0),
        Tree(species=SPRUCE, diameter_cm=10.0, height_m=12.0),
    ]
    stand = Stand(plots=[CircularPlot(id="H", radius_m=_radius_for(500.0), trees=trees)])
    g = {d: d**2 for d in (10, 20, 30)}  # basal area ∝ d²
    hl_total = (g[20] * 18 + g[30] * 24 + g[10] * 12) / (g[20] + g[30] + g[10])
    hl_pine = (g[20] * 18 + g[30] * 24) / (g[20] + g[30])
    assert math.isclose(float(stand.HL.TOTAL), hl_total, rel_tol=1e-9)
    assert math.isclose(float(stand.HL(PINE)), hl_pine, rel_tol=1e-9)


def test_lorey_ignores_trees_without_height():
    """Trees lacking a measured height weight neither numerator nor denominator."""
    trees = [
        Tree(species=PINE, diameter_cm=20.0, height_m=18.0),
        Tree(species=PINE, diameter_cm=40.0),  # no height -> excluded from HL
    ]
    stand = Stand(plots=[CircularPlot(id="H", radius_m=_radius_for(500.0), trees=trees)])
    assert math.isclose(float(stand.HL.TOTAL), 18.0, rel_tol=1e-9)


# --------------------------------------------------------------------------- #
# 3. Species-group query API
# --------------------------------------------------------------------------- #
def _three_species_stand() -> Stand:
    trees = [
        Tree(species=PINE, diameter_cm=25.0, height_m=20.0),
        Tree(species=SPRUCE, diameter_cm=25.0, height_m=19.0),
        Tree(species=BIRCH, diameter_cm=25.0, height_m=22.0),
    ]
    return Stand(plots=[CircularPlot(id="G", radius_m=_radius_for(500.0), trees=trees)])


def test_group_predicate_matches_explicit_list():
    stand = _three_species_stand()
    by_predicate = stand.BasalArea.group(lambda s: s.tree_type == "Coniferous")
    by_list = stand.BasalArea.group(["pinus sylvestris", "picea abies"])
    assert math.isclose(float(by_predicate), float(by_list), rel_tol=1e-12)
    # Conifers are two of three equal-diameter trees -> 2/3 of the total.
    assert math.isclose(float(by_predicate), float(stand.BasalArea.TOTAL) * 2 / 3, rel_tol=1e-9)


def test_group_ratio_metrics_recomputed_from_components():
    stand = _three_species_stand()
    is_conifer = lambda s: s.tree_type == "Coniferous"  # noqa: E731
    # HL of conifers: equal basal-area weights -> mean of 20 and 19 = 19.5.
    assert math.isclose(float(stand.HL.group(is_conifer)), 19.5, rel_tol=1e-9)
    # QMD of the group (all 25 cm) is 25 cm.
    assert math.isclose(float(stand.QMD.group(is_conifer)), 25.0, rel_tol=1e-9)


def test_group_requires_a_selector():
    stand = _three_species_stand()
    with pytest.raises(ValueError):
        stand.BasalArea.group()


# --------------------------------------------------------------------------- #
# 4. Precision is the standard error of the mean (not the population SD)
# --------------------------------------------------------------------------- #
def test_precision_is_standard_error_of_the_mean():
    r = _radius_for(500.0)  # 0.05 ha
    diameters = [20.0, 25.0, 35.0]
    plots = [
        CircularPlot(id=i, radius_m=r, trees=[Tree(species=PINE, diameter_cm=d)])
        for i, d in enumerate(diameters)
    ]
    stand = Stand(plots=plots)
    ba_values = [_ba_per_ha(d, 0.05) for d in diameters]
    expected_se = math.sqrt(statistics.variance(ba_values) / len(ba_values))
    assert math.isclose(stand.BasalArea.TOTAL.precision, expected_se, rel_tol=1e-9)
    # It must NOT equal the plot-to-plot population SD (the previous behaviour).
    assert not math.isclose(
        stand.BasalArea.TOTAL.precision, statistics.pstdev(ba_values), rel_tol=1e-6
    )
