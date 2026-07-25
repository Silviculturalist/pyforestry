"""Tests for the competition indices of Maleki, Kiviste & Korjus (2015) Table 2.

Every index is checked against a value computed by hand from the published
formula on a fixed three-competitor neighbourhood, so a transcription slip in
any single term shows up as a failure in exactly one test.
"""

from math import atan, exp, isclose, pi, radians, sqrt, tan

import pytest

from pyforestry.base.competition import (
    INDEX_REGISTRY,
    INDEX_SET_REVIEW,
    INDEX_SOURCES,
    NON_SPATIAL_INDICES,
    SELECTOR_SOURCES,
    SPATIAL_INDICES,
    BitterlichBAF,
    Candidates,
    FixedRadius,
    LeeGadowRadius,
    MeanHeightRadius,
    MissingNeighbourhoodData,
    NearestNeighbours,
    Neighbourhood,
    SearchCone,
    SelectionContext,
    circle_intersection_area,
    circle_overlap_length,
    competition_indices,
    compute_index,
    fraction_of_circle_inside_circle,
    hegyi,
    index_source,
    martin_ek_sdrl2,
    mean_spacing_m,
    selector_source,
)
from pyforestry.base.helpers import CircularPlot, Stand, Tree
from pyforestry.base.helpers.primitives import Position

# Subject 20 cm; competitors 30, 15 and 25 cm at 3, 5 and 4 m.
D_I = 20.0
D_J = (30.0, 15.0, 25.0)
L_IJ = (3.0, 5.0, 4.0)
PLOT_AREA_HA = 0.05


def _g(diameter_cm: float) -> float:
    """Basal area (m^2) of a stem, independently of the implementation."""
    return pi * (diameter_cm / 200.0) ** 2


@pytest.fixture
def neighbourhood() -> Neighbourhood:
    """A fully populated neighbourhood every index can be computed from."""
    return Neighbourhood(
        subject_dbh_cm=D_I,
        competitor_dbh_cm=D_J,
        distances_m=L_IJ,
        subject_crown_radius_m=2.5,
        competitor_crown_radius_m=(3.0, 2.0, 2.8),
        plot_area_ha=PLOT_AREA_HA,
        plot_basal_area_m2_ha=25.0,
        plot_qmd_cm=22.5,
        relative_spacing=0.25,
        competition_zone_radius_m=10.0,
    )


# ---------------------------------------------------------------------------
# Non-spatial indices
# ---------------------------------------------------------------------------


def test_ba_gj_sums_every_neighbour(neighbourhood):
    """BA-gj: sum(g_j)/S, all neighbours regardless of size (Steneker & Jarvis 1963)."""
    expected = sum(_g(d) for d in D_J) / PLOT_AREA_HA
    assert compute_index("BA-gj", neighbourhood) == pytest.approx(expected)


def test_bal_counts_only_larger_trees(neighbourhood):
    """BAL: only the 30 and 25 cm competitors exceed the 20 cm subject."""
    expected = (_g(30.0) + _g(25.0)) / PLOT_AREA_HA
    assert compute_index("BAL", neighbourhood) == pytest.approx(expected)


def test_bal_excludes_ties():
    """A competitor of exactly the subject's size is not 'larger'."""
    n = Neighbourhood(
        subject_dbh_cm=20.0,
        competitor_dbh_cm=(20.0, 20.0),
        plot_area_ha=0.1,
    )
    assert compute_index("BAL", n) == pytest.approx(0.0)


def test_sdr_and_bar(neighbourhood):
    """Sdr (Lorimer 1983) and its basal-area analogue BAr (Corona & Ferrara 1989)."""
    assert compute_index("Sdr", neighbourhood) == pytest.approx((sum(D_J) / D_I) / PLOT_AREA_HA)
    assert compute_index("BAr", neighbourhood) == pytest.approx(
        (sum(_g(d) for d in D_J) / _g(D_I)) / PLOT_AREA_HA
    )


def test_drg_is_subject_over_plot_qmd(neighbourhood):
    """drg (Hamilton 1986) rises when the subject dominates, unlike the others."""
    assert compute_index("drg", neighbourhood) == pytest.approx(20.0 / 22.5)


def test_balr_is_bal_over_plot_basal_area(neighbourhood):
    """BALr (Vanclay 1991) is a dimensionless share of stand basal area."""
    expected = ((_g(30.0) + _g(25.0)) / PLOT_AREA_HA) / 25.0
    assert compute_index("BALr", neighbourhood) == pytest.approx(expected)
    assert 0.0 <= compute_index("BALr", neighbourhood) <= 1.0


def test_balmod_divides_balr_by_relative_spacing(neighbourhood):
    """BALMOD (Schroder & Gadow 1999) = BALr / RS."""
    assert compute_index("BALMOD", neighbourhood) == pytest.approx(
        compute_index("BALr", neighbourhood) / 0.25
    )


# ---------------------------------------------------------------------------
# Spatial indices
# ---------------------------------------------------------------------------


def test_hegyi_matches_hand_calculation(neighbourhood):
    """Heg (Hegyi 1974): sum(d_j / (d_i * l_ij))."""
    expected = 30 / (20 * 3) + 15 / (20 * 5) + 25 / (20 * 4)
    assert compute_index("Heg", neighbourhood) == pytest.approx(expected)


def test_martin_ek_exponent_is_negative(neighbourhood):
    """Sdrl2 decays with distance.

    Guards the one deliberate departure from Table 2 as printed: the paper (and
    Wang et al. 2012) show exp(+16*l/(d_i+d_j)). A positive exponent would make a
    distant competitor count for more than a near one, which is the opposite of
    what a distance-weighted index means.
    """
    expected = sum(
        (dj / D_I) * exp(-16.0 * lij / (D_I + dj)) for dj, lij in zip(D_J, L_IJ, strict=False)
    )
    assert compute_index("Sdrl2", neighbourhood) == pytest.approx(expected)

    near = Neighbourhood(subject_dbh_cm=20.0, competitor_dbh_cm=(20.0,), distances_m=(2.0,))
    far = Neighbourhood(subject_dbh_cm=20.0, competitor_dbh_cm=(20.0,), distances_m=(10.0,))
    assert martin_ek_sdrl2(near) > martin_ek_sdrl2(far)


def test_hegyi_and_sdrl2_fall_with_distance():
    """Every size-ratio index must weaken as the competitor moves away."""
    values = [
        hegyi(Neighbourhood(subject_dbh_cm=20.0, competitor_dbh_cm=(25.0,), distances_m=(d,)))
        for d in (2.0, 4.0, 8.0)
    ]
    assert values == sorted(values, reverse=True)


def test_angular_indices_use_consistent_units():
    """A 20 cm stem 5 m away subtends about 2.3 degrees, not 76.

    Table 2 prints d_j in cm against l_ij in m, which would give the larger,
    meaningless figure; the implementation converts diameters to metres.
    """
    n = Neighbourhood(subject_dbh_cm=20.0, competitor_dbh_cm=(20.0,), distances_m=(5.0,))
    degrees = compute_index("SAng2", n) * 180.0 / pi
    assert degrees == pytest.approx(2.29, abs=0.05)
    assert compute_index("SAng2", n) == pytest.approx(atan(0.20 / 5.0))


def test_sang1_is_the_full_subtended_angle():
    """SAng1 (Lin 1974) = 2*arctan(d_j/2 / l_ij), slightly under SAng2 for one stem."""
    n = Neighbourhood(subject_dbh_cm=20.0, competitor_dbh_cm=(30.0,), distances_m=(4.0,))
    assert compute_index("SAng1", n) == pytest.approx(2.0 * atan(0.15 / 4.0))
    # 2*arctan(x/2) exceeds arctan(x) for x > 0, so SAng1 sits just above SAng2.
    assert compute_index("SAng1", n) > compute_index("SAng2", n)


def test_sdrang_weights_the_angle_by_diameter_ratio(neighbourhood):
    """SdrAng (Rouvinen & Kuuluvainen 1997)."""
    expected = sum(
        (dj / D_I) * atan((dj / 100.0) / lij) for dj, lij in zip(D_J, L_IJ, strict=False)
    )
    assert compute_index("SdrAng", neighbourhood) == pytest.approx(expected)


def test_sbar_rewards_a_dominant_subject(neighbourhood):
    """SBAr (Daniels et al. 1986) = (d_i^2 * N_c) / sum(d_j^2)."""
    expected = (D_I**2 * 3) / sum(d * d for d in D_J)
    assert compute_index("SBAr", neighbourhood) == pytest.approx(expected)


def test_sdrl1_matches_hand_calculation(neighbourhood):
    """Sdrl1 (Lorimer 1983): sum((d_j/d_i) / sqrt(l_ij / CZR))."""
    expected = sum((dj / D_I) / sqrt(lij / 10.0) for dj, lij in zip(D_J, L_IJ, strict=False))
    assert compute_index("Sdrl1", neighbourhood) == pytest.approx(expected)


def test_alemdag_matches_hand_calculation(neighbourhood):
    """Almdg (Alemdag 1978): weighted sum of equal-influence circle areas."""
    ratios = [dj / lij for dj, lij in zip(D_J, L_IJ, strict=False)]
    total = sum(ratios)
    expected = sum(
        pi * ((lij * D_I) / (D_I + dj)) ** 2 * (r / total)
        for dj, lij, r in zip(D_J, L_IJ, ratios, strict=False)
    )
    assert compute_index("Almdg", neighbourhood) == pytest.approx(expected)


def test_staebler_sums_linear_overlap(neighbourhood):
    """Sl (Staebler 1951): only zones that actually meet contribute."""
    # (2.5+3.0-3.0) + max(0, 2.5+2.0-5.0) + (2.5+2.8-4.0) = 2.5 + 0 + 1.3
    assert compute_index("Sl", neighbourhood) == pytest.approx(3.8)


def test_gerrard_and_bella_use_the_overlap_area(neighbourhood):
    """SOr (Gerrard 1969) and SOdr (Bella 1971) share an overlap-area numerator."""
    zone = pi * 2.5**2
    overlaps = [
        circle_intersection_area(2.5, r, lij)
        for r, lij in zip((3.0, 2.0, 2.8), L_IJ, strict=False)
    ]
    assert compute_index("SOr", neighbourhood) == pytest.approx(sum(o / zone for o in overlaps))
    assert compute_index("SOdr", neighbourhood) == pytest.approx(
        sum((o * dj) / (zone * D_I) for o, dj in zip(overlaps, D_J, strict=False))
    )


# ---------------------------------------------------------------------------
# Registry and input validation
# ---------------------------------------------------------------------------


def test_registry_holds_all_eighteen():
    """Seven non-spatial plus eleven spatial, as in Table 2."""
    assert len(NON_SPATIAL_INDICES) == 7
    assert len(SPATIAL_INDICES) == 11
    assert len(INDEX_REGISTRY) == 18


def test_every_registered_index_is_computable(neighbourhood):
    """A fully populated neighbourhood supports all eighteen."""
    for name in INDEX_REGISTRY:
        assert isinstance(compute_index(name, neighbourhood), float)


def test_compute_index_is_case_insensitive_and_rejects_unknown(neighbourhood):
    """Names may be given in any case; an unknown name lists the valid ones."""
    assert compute_index("heg", neighbourhood) == compute_index("Heg", neighbourhood)
    with pytest.raises(KeyError, match="Unknown competition index"):
        compute_index("NotAnIndex", neighbourhood)


def test_missing_inputs_name_the_missing_field():
    """A spatial index without distances says so rather than failing obscurely."""
    n = Neighbourhood(subject_dbh_cm=20.0, competitor_dbh_cm=(25.0,))
    with pytest.raises(MissingNeighbourhoodData, match="distances_m"):
        compute_index("Heg", n)


def test_misaligned_sequences_are_rejected():
    """Per-competitor sequences must all have the same length."""
    with pytest.raises(ValueError, match="must align"):
        Neighbourhood(subject_dbh_cm=20.0, competitor_dbh_cm=(25.0, 30.0), distances_m=(3.0,))


def test_zero_distance_is_rejected():
    """A competitor at zero distance is the subject itself and divides by zero."""
    with pytest.raises(ValueError, match="positive"):
        Neighbourhood(subject_dbh_cm=20.0, competitor_dbh_cm=(25.0,), distances_m=(0.0,))


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------


def test_circle_intersection_area_limits():
    """Disjoint, nested and equal-circle cases."""
    assert circle_intersection_area(2.0, 3.0, 10.0) == 0.0
    assert circle_intersection_area(2.0, 3.0, 5.0) == 0.0  # externally tangent
    assert circle_intersection_area(2.0, 5.0, 1.0) == pytest.approx(pi * 4.0)  # nested
    assert circle_intersection_area(3.0, 3.0, 0.0) == pytest.approx(pi * 9.0)  # coincident


def test_circle_intersection_area_half_overlap():
    """Two unit circles whose centres are one radius apart share a known lens."""
    # Classic result: 2r^2*acos(d/2r) - (d/2)*sqrt(4r^2-d^2) with r=1, d=1.
    expected = 2 * 1.0 * (pi / 3) - (sqrt(3) / 2)
    assert circle_intersection_area(1.0, 1.0, 1.0) == pytest.approx(expected)


def test_overlap_length_clamps_at_zero():
    """Zones that do not reach each other overlap by nothing, never negatively."""
    assert circle_overlap_length(2.0, 3.0, 4.0) == pytest.approx(1.0)
    assert circle_overlap_length(2.0, 3.0, 9.0) == 0.0


def test_edge_fraction_is_one_when_zone_fits_inside():
    """A zone tangent to the plot boundary from inside is still wholly observed."""
    assert fraction_of_circle_inside_circle(4.0, 6.0, 10.0) == pytest.approx(1.0)
    assert fraction_of_circle_inside_circle(0.0, 5.0, 10.0) == pytest.approx(1.0)


def test_edge_fraction_is_half_on_the_boundary():
    """A tree exactly on the plot edge has half its zone outside, for a small zone."""
    # With plot radius 1000 m the boundary is locally straight, so a tree sitting
    # on it sees half of a 1 m zone.
    assert fraction_of_circle_inside_circle(1000.0, 1.0, 1000.0) == pytest.approx(0.5, abs=1e-3)


def test_mean_spacing():
    """1000 stems/ha sit sqrt(10) m apart on a square lattice."""
    assert mean_spacing_m(1000.0) == pytest.approx(sqrt(10.0))
    with pytest.raises(ValueError):
        mean_spacing_m(0.0)


# ---------------------------------------------------------------------------
# Competitor selection
# ---------------------------------------------------------------------------

DIAMS = (20.0, 30.0, 15.0, 25.0, 5.0)
DISTS = (0.0, 3.0, 5.0, 4.0, 2.0)
# Bearings put every neighbour on its own ray from the subject, so the default
# tests are unaffected by the elimination angle.
BEARINGS = (0.0, 0.0, pi / 2, pi, 3 * pi / 2)
HEIGHTS = (18.0, 24.0, 12.0, 20.0, 6.0)
CAND = Candidates(
    diameters_cm=DIAMS,
    distances_m=DISTS,
    bearings_rad=BEARINGS,
    heights_m=HEIGHTS,
    crown_base_heights_m=(8.0, None, None, None, None),
)
CTX = SelectionContext(stems_per_ha=1000.0, mean_height_m=20.0)


def test_fixed_radius_excludes_the_subject_and_distant_trees():
    """The subject never competes with itself."""
    sel = FixedRadius(4.5).select(0, CAND, CTX)
    assert sel.indices == (1, 3, 4)
    assert sel.zone_radius_m == 4.5


def test_min_size_ratio_screens_suppressed_neighbours():
    """d_j >= 0.3 * d_i drops the 5 cm stem next to a 20 cm subject."""
    sel = FixedRadius(10.0, min_size_ratio=0.3).select(0, CAND, CTX)
    assert 4 not in sel.indices
    assert sel.indices == (1, 2, 3)


def test_mean_height_radius_scales_with_the_stand():
    """CZR = 0.4 * mean height = 8 m here."""
    sel = MeanHeightRadius(0.4).select(0, CAND, CTX)
    assert sel.zone_radius_m == pytest.approx(8.0)
    with pytest.raises(ValueError, match="mean_height_m"):
        MeanHeightRadius().select(0, CAND, SelectionContext())


def test_lee_gadow_radius_is_a_multiple_of_mean_spacing():
    """CZR = k * sqrt(10000/N)."""
    sel = LeeGadowRadius(k=2.0).select(0, CAND, CTX)
    assert sel.zone_radius_m == pytest.approx(2.0 * sqrt(10.0))
    with pytest.raises(ValueError, match="stems_per_ha"):
        LeeGadowRadius().select(0, CAND, SelectionContext())


def test_bitterlich_limiting_distance_grows_with_the_subject():
    """l_ij <= 50 * d_i(m) / sqrt(BAF), the angle-count limiting distance.

    A 20 cm subject at BAF 2 reaches 7.07 m. Reading the paper's ``d_i`` as cm
    without converting would give 1.0 m and silently drop most competitors.
    """
    sel = BitterlichBAF(basal_area_factor=2.0).select(0, CAND, CTX)
    assert sel.zone_radius_m == pytest.approx(7.0711, abs=1e-4)
    assert sel.zone_radius_m == pytest.approx(20.0 / (2.0 * sqrt(2.0)))
    assert sel.indices == (1, 2, 3, 4)  # every neighbour is inside 7.07 m

    # The limit is exactly where the angle-count relation puts the tree on the edge.
    limit = sel.zone_radius_m
    assert 10000.0 * (0.20 / (2.0 * limit)) ** 2 == pytest.approx(2.0)

    # A larger subject reaches further; a larger BAF reaches less far.
    bigger = BitterlichBAF(2.0).select(3, CAND, CTX).zone_radius_m
    assert bigger > limit
    coarser = BitterlichBAF(4.0).select(0, CAND, CTX).zone_radius_m
    assert coarser < limit

    with pytest.raises(ValueError):
        BitterlichBAF(basal_area_factor=0.0)


def test_nearest_neighbours_takes_the_closest_n():
    """The two closest qualifying stems, in input order."""
    sel = NearestNeighbours(n=2).select(0, CAND, CTX)
    assert sel.indices == (1, 4)  # 3 m and 2 m
    assert sel.zone_radius_m == pytest.approx(3.0)
    with pytest.raises(ValueError):
        NearestNeighbours(n=0)


# ---------------------------------------------------------------------------
# The Tree / Plot API
# ---------------------------------------------------------------------------


def _demo_plot() -> CircularPlot:
    """A 10 m plot with one central tree, three neighbours and one near the edge."""
    trees = [
        Tree(position=(0.0, 0.0), diameter_cm=20.0, height_m=18.0, crown_radius_m=2.5, uid="c"),
        Tree(position=(3.0, 0.0), diameter_cm=30.0, height_m=22.0, crown_radius_m=3.0, uid="a"),
        Tree(position=(0.0, 5.0), diameter_cm=15.0, height_m=15.0, crown_radius_m=2.0, uid="b"),
        Tree(position=(-4.0, 0.0), diameter_cm=25.0, height_m=20.0, crown_radius_m=2.8, uid="d"),
        Tree(position=(9.0, 0.0), diameter_cm=28.0, height_m=21.0, crown_radius_m=2.9, uid="e"),
    ]
    return CircularPlot(id=1, position=Position(0.0, 0.0), radius_m=10.0, trees=trees)


def test_api_computes_per_tree_values():
    """One result per tree, in input order, with the requested indices."""
    results = competition_indices(_demo_plot(), indices=["Heg"], selector=FixedRadius(6.0))
    assert [r.tree.uid for r in results] == ["c", "a", "b", "d", "e"]
    centre = results[0]
    assert centre.indices["Heg"] == pytest.approx(30 / (20 * 3) + 15 / (20 * 5) + 25 / (20 * 4))
    assert centre.n_competitors == 3


def test_api_edge_correction_scales_by_observed_fraction():
    """The corrected value is the raw value divided by the observed share."""
    raw = competition_indices(
        _demo_plot(), indices=["Heg"], selector=FixedRadius(6.0), edge_correction=None
    )
    corrected = competition_indices(_demo_plot(), indices=["Heg"], selector=FixedRadius(6.0))
    edge_raw, edge_corr = raw[-1], corrected[-1]
    assert edge_raw.tree.uid == "e"
    assert edge_raw.observed_zone_fraction < 1.0
    assert edge_raw.edge_corrected is False
    assert edge_corr.edge_corrected is True
    assert edge_corr.indices["Heg"] == pytest.approx(
        edge_raw.indices["Heg"] / edge_raw.observed_zone_fraction
    )
    # The central tree is untouched either way.
    assert raw[0].indices["Heg"] == pytest.approx(corrected[0].indices["Heg"])


def test_api_does_not_edge_correct_non_spatial_indices():
    """BAL is a plot-level sum and does not depend on where the subject sits."""
    raw = competition_indices(
        _demo_plot(), indices=["BAL"], selector=FixedRadius(6.0), edge_correction=None
    )
    corrected = competition_indices(_demo_plot(), indices=["BAL"], selector=FixedRadius(6.0))
    for a, b in zip(raw, corrected, strict=False):
        assert a.indices["BAL"] == pytest.approx(b.indices["BAL"])


def test_api_skips_spatial_indices_without_positions():
    """A bare tree list still yields every distance-independent index."""
    trees = [Tree(diameter_cm=d) for d in (20.0, 30.0, 15.0)]
    result = competition_indices(trees, plot_area_ha=0.05)[0]
    assert set(result.indices) == set(NON_SPATIAL_INDICES) - {"BALMOD"} | {"SBAr"}
    assert "Heg" in result.skipped
    assert "distances_m" in result.skipped["Heg"]


def test_api_crown_radius_from_callable_overrides_the_attribute():
    """crown_radius may be a constant or a callable; both beat the attribute."""
    plot = _demo_plot()
    from_attribute = competition_indices(plot, indices=["SOr"], selector=FixedRadius(6.0))
    from_callable = competition_indices(
        plot, indices=["SOr"], selector=FixedRadius(6.0), crown_radius=lambda t: 4.0
    )
    assert from_callable[0].indices["SOr"] != pytest.approx(from_attribute[0].indices["SOr"])
    from_constant = competition_indices(
        plot, indices=["SOr"], selector=FixedRadius(6.0), crown_radius=4.0
    )
    assert from_constant[0].indices["SOr"] == pytest.approx(from_callable[0].indices["SOr"])


def test_api_overlap_indices_skipped_without_a_crown_radius():
    """No crown radius anywhere means the influence-zone indices are unavailable."""
    trees = [
        Tree(position=(0.0, 0.0), diameter_cm=20.0),
        Tree(position=(3.0, 0.0), diameter_cm=30.0),
    ]
    result = competition_indices(trees, indices=["SOr", "Heg"], plot_area_ha=0.05)[0]
    assert "Heg" in result.indices
    assert "SOr" in result.skipped


def test_api_rejects_unknown_edge_correction():
    """Only 'proportional_area' and None are accepted."""
    with pytest.raises(ValueError, match="Unknown edge_correction"):
        competition_indices(_demo_plot(), edge_correction="magic")


def test_api_handles_an_empty_and_diameterless_input():
    """No usable trees yields no results rather than an error."""
    assert competition_indices([]) == []
    assert competition_indices([Tree(diameter_cm=None), Tree(diameter_cm=0.0)]) == []


def test_api_is_discoverable_in_the_catalog():
    """The package publishes a DESCRIPTOR under region 'base', domain 'competition'."""
    from pyforestry import catalog

    entry = catalog.describe("competition_indices")
    assert entry.region == "base"
    assert entry.domain == "competition"
    # The package itself has no publication; it collects eighteen that do.
    assert entry.source.author == "(none)"
    assert entry.source.year == 0
    assert set(entry.composes) == set(INDEX_REGISTRY)


# ---------------------------------------------------------------------------
# Attribution
# ---------------------------------------------------------------------------


def test_every_index_cites_its_own_author_not_the_review():
    """Each index is attributed to the paper that proposed it."""
    assert len(INDEX_SOURCES) == 18
    for name in INDEX_REGISTRY:
        source = index_source(name)
        assert source.author and source.title
        assert 1900 < source.year < 2030
        # None of them may be credited to the review that tabulated the set.
        assert "Maleki" not in source.author


def test_index_sources_match_the_originals():
    """Spot-check the attributions against the primary literature."""
    expected = {
        "BA-gj": ("Steneker", 1963),
        "BAL": ("Wykoff", 1982),
        "Sdr": ("Lorimer", 1983),
        "drg": ("Hamilton", 1986),
        "BAr": ("Corona", 1989),
        "BALr": ("Vanclay", 1991),
        "BALMOD": ("Schroder", 1999),
        "Sl": ("Staebler", 1951),
        "SOr": ("Gerrard", 1969),
        "SOdr": ("Bella", 1971),
        "SBAr": ("Daniels", 1986),
        "Heg": ("Hegyi", 1974),
        "SAng1": ("Lin", 1974),
        "SAng2": ("Rouvinen", 1997),
        "SdrAng": ("Rouvinen", 1997),
        "Almdg": ("Alemdag", 1978),
        "Sdrl1": ("Lorimer", 1983),
        "Sdrl2": ("Martin", 1984),
    }
    for name, (surname, year) in expected.items():
        source = index_source(name)
        assert source.author.startswith(surname), name
        assert source.year == year, name


def test_rouvinen_kuuluvainen_year_is_corrected():
    """The 2015 table dates the work 1977; it is 1997."""
    for name in ("SAng2", "SdrAng"):
        assert index_source(name).year == 1997
        assert "1977" in index_source(name).note


def test_index_registry_entries_expose_formula_and_source():
    """A registry entry is callable and carries its own provenance and spatial flag."""
    entry = INDEX_REGISTRY["Heg"]
    assert entry.abbreviation == "Heg"
    assert entry.source.author.startswith("Hegyi")
    assert entry.spatial is True
    assert INDEX_REGISTRY["BAL"].spatial is False
    n = Neighbourhood(subject_dbh_cm=20.0, competitor_dbh_cm=(25.0,), distances_m=(4.0,))
    assert entry(n) == pytest.approx(compute_index("Heg", n))


def test_the_review_is_cited_only_as_the_source_of_the_set():
    """Maleki et al. (2015) is credited for assembling the comparison, nothing more."""
    assert INDEX_SET_REVIEW.author.startswith("Maleki")
    assert INDEX_SET_REVIEW.year == 2015
    assert "attributed to its own author" in INDEX_SET_REVIEW.note


def test_selectors_carry_their_own_sources():
    """Published selection rules cite their authors; plain geometry cites nobody."""
    assert selector_source(MeanHeightRadius()).author.startswith("Sims")
    assert selector_source(LeeGadowRadius()).author.startswith("Lee")
    assert selector_source(BitterlichBAF()).author.startswith("Bitterlich")
    assert selector_source(SearchCone()).author.startswith("Pretzsch")
    assert selector_source(FixedRadius(5.0)) is None
    assert selector_source(NearestNeighbours(3)) is None
    assert set(SELECTOR_SOURCES) == {
        "MeanHeightRadius",
        "LeeGadowRadius",
        "BitterlichBAF",
        "SearchCone",
    }


def test_crown_radius_round_trips_on_tree():
    """Tree carries the optional crown radius the overlap indices need."""
    assert Tree(diameter_cm=20.0).crown_radius_m is None
    assert isclose(Tree(diameter_cm=20.0, crown_radius_m=3.5).crown_radius_m, 3.5)


# ---------------------------------------------------------------------------
# Parameters are parameters, not constants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fraction,expected_radius", [(0.25, 5.0), (0.4, 8.0), (0.6, 12.0)])
def test_mean_height_fraction_is_settable(fraction, expected_radius):
    """0.4 is the value Sims et al. tested, not a fixed constant."""
    sel = MeanHeightRadius(fraction).select(0, CAND, CTX)
    assert sel.zone_radius_m == pytest.approx(expected_radius)


@pytest.mark.parametrize("k,expected", [(2.0, 2 * sqrt(10.0)), (3.0, 3 * sqrt(10.0))])
def test_lee_gadow_k_is_settable(k, expected):
    """The 2015 comparison tests k = 2 and k = 3."""
    assert LeeGadowRadius(k).select(0, CAND, CTX).zone_radius_m == pytest.approx(expected)


@pytest.mark.parametrize("baf,expected", [(1.0, 10.0), (2.0, 7.0711), (4.0, 5.0)])
def test_bitterlich_baf_is_settable(baf, expected):
    """BAF 1, 2 and 4 are the values the comparison tests."""
    got = BitterlichBAF(baf).select(0, CAND, CTX).zone_radius_m
    assert got == pytest.approx(expected, abs=1e-4)


def test_bitterlich_gauge_angles_match_the_published_table():
    """BAF 1, 2 and 4 are quoted as gauge angles of 1.15, 1.62 and 2.30 degrees.

    An independent check on the unit conversion in the limiting distance: the
    angles follow from 2*arcsin(sqrt(BAF/10000)) only if BAF is read the way
    BitterlichBAF reads it. Reading the diameter in cm without converting would
    be out by two orders of magnitude, so this pins the conversion tightly even
    at a loose tolerance.

    The relation gives 1.1459, 1.6206 and 2.2920 degrees. The paper's first two
    round to its quoted values; its third is quoted as 2.30 where 2.292 rounds
    to 2.29, so the tolerance allows that last digit.
    """
    assert BitterlichBAF(1.0).gauge_angle_deg == pytest.approx(1.15, abs=0.01)
    assert BitterlichBAF(2.0).gauge_angle_deg == pytest.approx(1.62, abs=0.01)
    assert BitterlichBAF(4.0).gauge_angle_deg == pytest.approx(2.30, abs=0.01)


# ---------------------------------------------------------------------------
# Competition elimination angle
# ---------------------------------------------------------------------------


def _stacked() -> Candidates:
    """Two neighbours nearly on the same bearing, one behind the other."""
    return Candidates(
        diameters_cm=(20.0, 25.0, 25.0, 25.0),
        distances_m=(0.0, 3.0, 6.0, 5.0),
        bearings_rad=(0.0, 0.0, radians(5.0), radians(90.0)),
        heights_m=(18.0, 20.0, 20.0, 20.0),
    )


def test_elimination_angle_drops_the_shadowed_neighbour():
    """At 30 degrees the far tree 5 degrees off the near tree's bearing goes."""
    cand = _stacked()
    assert FixedRadius(10.0).select(0, cand, CTX).indices == (1, 2, 3)
    assert FixedRadius(10.0, elimination_angle_deg=30.0).select(0, cand, CTX).indices == (1, 3)


def test_elimination_angle_keeps_the_nearer_of_a_shadowed_pair():
    """Shadowing is applied nearest-first, so the near tree always survives."""
    sel = FixedRadius(10.0, elimination_angle_deg=30.0).select(0, _stacked(), CTX)
    assert 1 in sel.indices and 2 not in sel.indices


def test_elimination_angle_zero_is_a_no_op():
    sel = FixedRadius(10.0, elimination_angle_deg=0.0).select(0, _stacked(), CTX)
    assert sel.indices == (1, 2, 3)


def test_elimination_angle_needs_bearings():
    cand = Candidates(diameters_cm=(20.0, 25.0), distances_m=(0.0, 3.0))
    with pytest.raises(ValueError, match="needs bearings"):
        FixedRadius(10.0, elimination_angle_deg=30.0).select(0, cand, CTX)


def test_elimination_angle_composes_with_the_size_screen():
    """Approaches 1 and 2 of the comparison apply both screens together."""
    cand = Candidates(
        diameters_cm=(20.0, 25.0, 25.0, 4.0),
        distances_m=(0.0, 3.0, 6.0, 1.0),
        bearings_rad=(0.0, 0.0, radians(5.0), radians(180.0)),
    )
    sel = FixedRadius(10.0, min_size_ratio=0.3, elimination_angle_deg=30.0).select(0, cand, CTX)
    assert sel.indices == (1,)  # 2 is shadowed, 3 is undersized


def test_elimination_angle_available_on_every_radius_selector():
    cand = _stacked()
    ctx = SelectionContext(stems_per_ha=1000.0, mean_height_m=30.0)
    assert MeanHeightRadius(0.4, elimination_angle_deg=30.0).select(0, cand, ctx).indices == (1, 3)
    assert LeeGadowRadius(3.0, elimination_angle_deg=30.0).select(0, cand, ctx).indices == (1, 3)


# ---------------------------------------------------------------------------
# Search cone
# ---------------------------------------------------------------------------


def _cone_reach(height_m: float, beta_deg: float) -> float:
    """Horizontal reach of the cone for a competitor of the given height."""
    return height_m / tan(radians(90.0 - beta_deg / 2.0))


@pytest.mark.parametrize("height", [10.0, 20.0, 30.0])
def test_search_cone_reach_grows_with_competitor_height(height):
    """A taller neighbour competes from further away; that is the point of it."""
    cone = SearchCone(opening_angle_deg=80.0)
    reach = _cone_reach(height, 80.0)
    inside = Candidates(
        diameters_cm=(20.0, 20.0), distances_m=(0.0, reach - 0.01), heights_m=(18.0, height)
    )
    outside = Candidates(
        diameters_cm=(20.0, 20.0), distances_m=(0.0, reach + 0.01), heights_m=(18.0, height)
    )
    assert cone.select(0, inside, CTX).indices == (1,)
    assert cone.select(0, outside, CTX).indices == ()


@pytest.mark.parametrize("beta", [100.0, 80.0, 60.0])
def test_search_cone_opening_angle_is_settable(beta):
    """The comparison tests 100, 80 and 60 degrees."""
    cand = Candidates(diameters_cm=(20.0, 20.0), distances_m=(0.0, 15.0), heights_m=(18.0, 20.0))
    expected = (1,) if 15.0 < _cone_reach(20.0, beta) else ()
    assert SearchCone(opening_angle_deg=beta).select(0, cand, CTX).indices == expected


def test_search_cone_widening_only_ever_adds_competitors():
    cand = Candidates(
        diameters_cm=(20.0,) * 4,
        distances_m=(0.0, 5.0, 12.0, 20.0),
        heights_m=(18.0, 20.0, 20.0, 20.0),
    )
    counts = [
        len(SearchCone(opening_angle_deg=b).select(0, cand, CTX).indices)
        for b in (60.0, 80.0, 100.0)
    ]
    assert counts == sorted(counts)


def test_search_cone_crown_base_apex_is_stricter():
    """Raising the apex to the subject's crown base shortens the reach."""
    cand = Candidates(
        diameters_cm=(20.0, 20.0),
        # 12 m is inside the stem-base cone (16.8 m) but outside the
        # crown-base cone (10.1 m), which is what distinguishes the two.
        distances_m=(0.0, 12.0),
        heights_m=(18.0, 20.0),
        crown_base_heights_m=(8.0, None),
    )
    assert SearchCone(80.0, apex="stem_base").select(0, cand, CTX).indices == (1,)
    assert SearchCone(80.0, apex="crown_base").select(0, cand, CTX).indices == ()


def test_search_cone_requires_heights():
    cand = Candidates(diameters_cm=(20.0, 20.0), distances_m=(0.0, 5.0))
    with pytest.raises(ValueError, match="needs heights"):
        SearchCone().select(0, cand, CTX)


def test_search_cone_crown_base_apex_requires_a_crown_base():
    cand = Candidates(diameters_cm=(20.0, 20.0), distances_m=(0.0, 5.0), heights_m=(18.0, 20.0))
    with pytest.raises(ValueError, match="crown base"):
        SearchCone(apex="crown_base").select(0, cand, CTX)


def test_search_cone_rejects_bad_parameters():
    with pytest.raises(ValueError, match="between 0 and 180"):
        SearchCone(opening_angle_deg=0.0)
    with pytest.raises(ValueError, match="Unknown apex"):
        SearchCone(apex="canopy")


def test_search_cone_skips_neighbours_without_a_height():
    cand = Candidates(
        diameters_cm=(20.0, 20.0, 20.0),
        distances_m=(0.0, 4.0, 4.0),
        heights_m=(18.0, 20.0, None),
    )
    assert SearchCone(80.0).select(0, cand, CTX).indices == (1,)


def test_search_cone_uses_imputed_heights_through_the_api():
    """A neighbour whose height was imputed still competes."""
    trees = [
        Tree(position=(0.0, 0.0), diameter_cm=20.0, height_m=18.0, uid="c"),
        Tree(position=(4.0, 0.0), diameter_cm=30.0, height_m=24.0, uid="a"),
        Tree(position=(0.0, 4.0), diameter_cm=25.0, uid="b"),  # height imputed below
    ]
    stand = Stand(
        plots=[CircularPlot(id=1, position=Position(0.0, 0.0), radius_m=15.0, trees=trees)]
    )
    stand.impute("height_m")
    assert trees[2].value_of("height_m") is not None
    results = competition_indices(
        stand.plots[0], indices=["Heg"], selector=SearchCone(100.0), edge_correction=None
    )
    assert results[0].n_competitors == 2
