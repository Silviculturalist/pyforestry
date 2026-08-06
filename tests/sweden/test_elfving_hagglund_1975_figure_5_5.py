"""Figur 5.5 of Elfving & Hägglund (1975) as an oracle for the stems functions.

    Elfving, B. & Hägglund, B. (1975). Utgångslägen för produktionsprognoser:
    tall och gran i Sverige. Rapporter och Uppsatser 38. Figur 5.5, p. 47:
    "Stamantal per ha i likåldriga bestånd utan lövträd enligt funktionerna
    f5.1-f5.4" -- stems per ha against stand density (*slutenhet*) 0.4 to 1.0.

The coefficients themselves are checked against the printed table (p. 42) by
reading it; this checks the functions against the curves the authors drew *from*
those coefficients, which is an independent artefact of the same publication.

**Why ratios, and not levels.** The figure fixes inputs it does not print --
dominant height for pine north, the cleaning and spatial-distribution dummies
everywhere -- so no curve's absolute height can be reproduced without guessing
them, and a test that guessed would be fitting rather than checking. Two curves
in one panel differ *only* in what their labels say, so their **ratio** cancels
every unstated input exactly. That is what is asserted here, and it is a real
constraint: it pins the coefficients of the labelled variables, including the
unit conversions folded into them, and it is what would catch the latitude
coefficient being written as the table's printed -0.0033 per 0.1 degree instead
of -0.033 per degree.

Only two of the four panels can do this. Pine northern (f5.1) and spruce northern
(f5.3) carry no age term, so a label that names latitude, altitude or site index
maps onto those coefficients and nothing else. Pine southern (f5.2) has no site
index term at all and spruce southern (f5.4) has both a site-index dummy and an
age term, so in those two panels an ``h100`` label acts partly or wholly through
an age the figure does not state; their curves are checked for order, not ratio.

Values were read off the printed curves at density 0.4 and 1.0, so they carry the
precision of a 1975 line drawing -- hence a 3% tolerance, against ratios that
differ from one another by 5% and more.
"""

from __future__ import annotations

import pytest

from pyforestry.base.helpers import Age, SiteIndexValue
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970
from pyforestry.sweden.systems.elfving_hagglund_1975 import ElfvingHagglundInitialStand

#: The density range the figure's x-axis spans.
DENSITIES = (0.4, 0.6, 0.8, 1.0)

#: Read off Figur 5.5 at densities 0.4 and 1.0. A printed curve read by eye.
FIGURE_TOLERANCE = 0.03


def _spruce_si(h100_m: float) -> SiteIndexValue:
    """A northern-spruce site index of ``h100_m``, as f5.3's dummy reads it."""
    return Hagglund_1970.height_trajectory.picea_abies.northern_sweden(
        dominant_height=h100_m / 2.0,
        age=Age.DBH(40),
        age2=Age.TOTAL(100),
        latitude=63.0,
    )


def _pine_north(density: float, *, latitude: float, altitude: float) -> float:
    return float(
        ElfvingHagglundInitialStand.estimate_stems_young_pine_north(
            latitude=latitude,
            altitude=altitude,
            dominant_height=8.0,
            stand_density_factor=density,
        )
    )


def _spruce_north(density: float, *, altitude: float, si: SiteIndexValue) -> float:
    return float(
        ElfvingHagglundInitialStand.estimate_stems_young_spruce_north(
            altitude=altitude,
            site_index=si,
            stand_density_factor=density,
        )
    )


# --- the ratios the figure fixes ---------------------------------------------


class TestFigure55Ratios:
    """Two curves in a panel, divided -- which cancels every unstated input."""

    def test_pine_north_latitude_and_altitude(self) -> None:
        """62°N/200 m over 66°N/400 m: 1.29 off the figure at both ends.

        Four degrees of latitude and 200 m of altitude, and nothing else: f5.1
        has no age and no site-index term, so this ratio is exactly
        ``exp(-0.033*(62-66) - 0.062*(2-4))``.
        """
        for density in DENSITIES:
            warm_low = _pine_north(density, latitude=62.0, altitude=200.0)
            cold_high = _pine_north(density, latitude=66.0, altitude=400.0)
            assert warm_low / cold_high == pytest.approx(1.29, rel=FIGURE_TOLERANCE)

    def test_spruce_north_site_index_dummy(self) -> None:
        """h100 < 22 m over h100 > 22 m at 200 m: 1.20 off the figure.

        The two curves share an altitude, so the only term between them is the
        ``h100 > 22 m`` dummy.
        """
        poor, rich = _spruce_si(18.0), _spruce_si(26.0)
        for density in DENSITIES:
            below = _spruce_north(density, altitude=200.0, si=poor)
            above = _spruce_north(density, altitude=200.0, si=rich)
            assert below / above == pytest.approx(1.20, rel=FIGURE_TOLERANCE)

    def test_spruce_north_altitude(self) -> None:
        """200 m over 500 m at h100 < 22 m: 1.27 off the figure.

        Both altitude terms at once -- f5.3 carries a linear and a squared one --
        and they pull against each other, so this catches a sign or a unit on
        either that the linear-only pine function could not.
        """
        poor = _spruce_si(18.0)
        for density in DENSITIES:
            low = _spruce_north(density, altitude=200.0, si=poor)
            high = _spruce_north(density, altitude=500.0, si=poor)
            assert low / high == pytest.approx(1.27, rel=FIGURE_TOLERANCE)

    def test_the_ratios_do_not_depend_on_the_inputs_the_figure_omits(self) -> None:
        """The premise of every assertion above, stated as its own test.

        If a ratio moved with dominant height or with the cleaning dummy, the
        figure could not constrain it and these tests would be measuring the
        background instead of the coefficients.
        """
        plain = ElfvingHagglundInitialStand.estimate_stems_young_pine_north
        for dominant_height, pct in ((4.0, False), (12.0, True)):
            warm_low = float(
                plain(
                    latitude=62.0,
                    altitude=200.0,
                    dominant_height=dominant_height,
                    stand_density_factor=0.7,
                    pct=pct,
                )
            )
            cold_high = float(
                plain(
                    latitude=66.0,
                    altitude=400.0,
                    dominant_height=dominant_height,
                    stand_density_factor=0.7,
                    pct=pct,
                )
            )
            assert warm_low / cold_high == pytest.approx(1.29, rel=FIGURE_TOLERANCE)


# --- the shape and order the figure shows ------------------------------------


class TestFigure55Shape:
    """What the curves do, in the panels whose labels a ratio cannot isolate."""

    def test_every_curve_rises_with_density(self) -> None:
        """All four panels climb from left to right across 0.4 to 1.0."""
        curves = [
            [_pine_north(d, latitude=62.0, altitude=200.0) for d in DENSITIES],
            [_pine_north(d, latitude=66.0, altitude=400.0) for d in DENSITIES],
            [_spruce_north(d, altitude=200.0, si=_spruce_si(18.0)) for d in DENSITIES],
            [_spruce_north(d, altitude=500.0, si=_spruce_si(18.0)) for d in DENSITIES],
        ]
        for curve in curves:
            assert curve == sorted(curve)
            assert curve[-1] > curve[0]

    def test_spruce_north_curves_are_ordered_as_drawn(self) -> None:
        """Three curves, and the middle pair are within 5% -- the figure shows it.

        ``h100 > 22 m`` at 200 m sits just above ``h100 < 22 m`` at 500 m; a sign
        error on either altitude term would swap them.
        """
        poor, rich = _spruce_si(18.0), _spruce_si(26.0)
        top = _spruce_north(0.8, altitude=200.0, si=poor)
        middle = _spruce_north(0.8, altitude=200.0, si=rich)
        bottom = _spruce_north(0.8, altitude=500.0, si=poor)

        assert top > middle > bottom
        assert middle / bottom == pytest.approx(1.05, rel=0.05)

    def test_spruce_south_richer_sites_carry_fewer_stems(self) -> None:
        """h100 = 20 m above h100 = 32 m, as drawn.

        Not a ratio test: f5.4 has an age term as well as its site-index dummy,
        and the figure states neither age, so the two curves differ by an amount
        this cannot reconstruct. The order is still the figure's.
        """
        estimate = ElfvingHagglundInitialStand.estimate_stems_young_spruce_south

        def stems(h100_m: float) -> float:
            site_index = Hagglund_1970.height_trajectory.picea_abies.southern_sweden(
                dominant_height=h100_m / 2.0,
                age=Age.DBH(40),
                age2=Age.TOTAL(100),
            )
            return float(
                estimate(
                    altitude=150.0,
                    site_index=site_index,
                    age_at_breast_height=Age.DBH(30),
                    stand_density_factor=0.8,
                )
            )

        assert stems(20.0) > stems(32.0)

    def test_pine_south_younger_stands_carry_more_stems(self) -> None:
        """The h100 labels in that panel act through age, which is all f5.2 has.

        f5.2 carries no site-index term at all, so its two curves can only differ
        through the age at which a stand of the given site index reaches the
        figure's stand state -- and its age coefficient is negative.
        """
        estimate = ElfvingHagglundInitialStand.estimate_stems_young_pine_south
        site_index = Hagglund_1970.height_trajectory.pinus_sylvestris.sweden(
            dominant_height_m=10.0,
            age=Age.DBH(40),
            age2=Age.TOTAL(100),
            regeneration=Hagglund_1970.regeneration.CULTURE,
        )

        def stems(age_bh: int) -> float:
            # latitude, site index and dominant height are taken only to resolve
            # an age this supplies directly; f5.2 reads none of the three.
            return float(
                estimate(
                    latitude=58.0,
                    site_index=site_index,
                    dominant_height=8.0,
                    age_at_breast_height=Age.DBH(age_bh),
                    stand_density_factor=0.8,
                )
            )

        assert stems(20) > stems(40)
