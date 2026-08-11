"""The stand and the simulation context must report the same numbers.

:class:`~pyforestry.base.helpers.stand.Stand` and
:class:`~pyforestry.base.simulation.core.SimulationContext` used to carry an
estimator each. The context's averaged a species over only the plots where that
species occurred, rather than over every plot, so the two disagreed by a factor
that grew with the number of species: for a two-plot, two-species stand,
``Stand`` reported 1.0 stems/ha and the context 2.0.
"""

import pytest

from pyforestry.base.aggregation import aggregate_plots
from pyforestry.base.helpers import CircularPlot, Stand, Tree, TreeSpecies
from pyforestry.base.simulation import ExampleStandGeneralModel

SPRUCE = TreeSpecies.Sweden.picea_abies
PINE = TreeSpecies.Sweden.pinus_sylvestris
BIRCH = TreeSpecies.Sweden.betula_pendula


def _segregated_stand() -> Stand:
    """Three one-hectare plots, each holding a single stem of a different species."""
    return Stand(
        plots=[
            CircularPlot(
                id=name,
                area_m2=10_000.0,
                trees=[Tree(species=species, diameter_cm=20.0, weight_n=1.0)],
            )
            for name, species in (("a", SPRUCE), ("b", PINE), ("c", BIRCH))
        ]
    )


def _context_metrics(stand: Stand):
    """Build a tree-list context over ``stand`` and return its metrics."""
    return ExampleStandGeneralModel().build_context(stand, mode_hint="tree_list").metrics


def test_absent_species_count_as_zero_not_as_missing():
    """A species absent from a plot divides by all plots, not just its own."""
    stand = _segregated_stand()
    # One stem per hectare in each of three plots: the stand mean is 1/3 per
    # species and 1.0 in total, not 1.0 per species and 3.0 in total.
    assert float(stand.Stems(SPRUCE)) == pytest.approx(1.0 / 3.0)
    assert float(stand.Stems) == pytest.approx(1.0)


def test_context_and_stand_agree_on_a_segregated_stand():
    """The context reports exactly what the stand does."""
    stand = _segregated_stand()
    metrics = _context_metrics(stand)

    assert float(metrics["Stems"]["TOTAL"]) == pytest.approx(float(stand.Stems))
    assert float(metrics["BasalArea"]["TOTAL"]) == pytest.approx(float(stand.BasalArea))
    assert float(metrics["QMD"]["TOTAL"]) == pytest.approx(float(stand.QMD))
    for species in (SPRUCE, PINE, BIRCH):
        assert float(metrics["Stems"][species]) == pytest.approx(float(stand.Stems(species)))
        assert float(metrics["BasalArea"][species]) == pytest.approx(
            float(stand.BasalArea(species))
        )


def test_context_and_stand_agree_on_a_mixed_stand():
    """Agreement is not an artefact of the segregated layout."""
    stand = Stand(
        plots=[
            CircularPlot(
                id="a",
                area_m2=400.0,
                trees=[
                    Tree(species=SPRUCE, diameter_cm=18.0, weight_n=2.0),
                    Tree(species=PINE, diameter_cm=25.0, weight_n=1.0),
                ],
            ),
            CircularPlot(
                id="b",
                area_m2=400.0,
                occlusion=0.25,
                trees=[
                    Tree(species=SPRUCE, diameter_cm=22.0, weight_n=3.0),
                    Tree(species=BIRCH, diameter_cm=14.0, weight_n=1.0),
                ],
            ),
        ]
    )
    metrics = _context_metrics(stand)
    assert float(metrics["Stems"]["TOTAL"]) == pytest.approx(float(stand.Stems))
    assert float(metrics["BasalArea"]["TOTAL"]) == pytest.approx(float(stand.BasalArea))
    assert float(metrics["QMD"]["TOTAL"]) == pytest.approx(float(stand.QMD))


def test_occlusion_expands_over_the_area_actually_searched():
    """A half-occluded plot represents twice the stems of an identical open plot."""
    open_plot = aggregate_plots(
        [
            CircularPlot(
                id="open",
                area_m2=10_000.0,
                trees=[Tree(species=SPRUCE, diameter_cm=20.0, weight_n=1.0)],
            )
        ]
    )
    half = aggregate_plots(
        [
            CircularPlot(
                id="half",
                area_m2=10_000.0,
                occlusion=0.5,
                trees=[Tree(species=SPRUCE, diameter_cm=20.0, weight_n=1.0)],
            )
        ]
    )
    assert float(half.stems["TOTAL"]) == pytest.approx(2.0 * float(open_plot.stems["TOTAL"]))


def test_undiametered_stems_count_but_carry_no_basal_area():
    """A record with no diameter is a stem, and stays out of the QMD denominator."""
    with pytest.warns(UserWarning, match="no diameter_cm"):
        result = aggregate_plots(
            [
                CircularPlot(
                    id="a",
                    area_m2=10_000.0,
                    trees=[
                        Tree(species=SPRUCE, diameter_cm=20.0, weight_n=1.0),
                        Tree(species=SPRUCE, diameter_cm=None, weight_n=1.0),
                    ],
                )
            ]
        )
    assert result.missing_diameter == 1
    assert float(result.stems["TOTAL"]) == pytest.approx(2.0)
    # QMD describes the one tree that has a diameter, not a 20 cm and a 0 cm tree.
    assert float(result.qmd) == pytest.approx(20.0)


def test_the_refresh_path_does_not_re_warn_every_step():
    """The context suppresses the missing-diameter warning it would emit per step."""
    result = aggregate_plots(
        [
            CircularPlot(
                id="a",
                area_m2=10_000.0,
                trees=[Tree(species=SPRUCE, diameter_cm=None, weight_n=1.0)],
            )
        ],
        warn_missing_diameter=False,
    )
    assert result.missing_diameter == 1
