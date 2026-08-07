import importlib

import pytest

from pyforestry.sweden.volume import andersson_1954, brandel_1990

# -- Tests for andersson_1954 -------------------------------------------------


def test_andersson_1954_all_functions():
    assert pytest.approx(0.0059904746, rel=1e-6) == (
        andersson_1954.andersson_1954_volume_small_trees_birch_height_above_4_m(4.0, 10.0)
    )
    assert pytest.approx(0.002047568, rel=1e-6) == (
        andersson_1954.andersson_1954_volume_small_trees_birch_under_diameter_5_cm(3.0, 4.0)
    )
    assert pytest.approx(0.0044363, rel=1e-6) == (
        andersson_1954.andersson_1954_volume_small_trees_pine(4.0, 5.0)
    )
    assert pytest.approx(0.0042177, rel=1e-6) == (
        andersson_1954.andersson_1954_volume_small_trees_spruce(4.0, 5.0)
    )


# -- Tests for brandel_1990 ---------------------------------------------------

# Transcribed from Brandel (1990) Report 26, Appendix B (pp. 104-115): the V1 series,
# function type 01, keyed by the Appendix B table each set is published in.
APPENDIX_B_FUNCTION_01 = {
    # Function group 100 -- volume o.b. from D.B.H. o.b.
    "SouthPineCoeff": ("1111", [-1.38903, 1.84493, 0.06563, 2.02122, -1.01095]),
    "SouthSpruceCoeff": ("1121", [-1.02039, 2.00128, -0.47473, 2.87138, -1.61803]),
    "SouthBirchCoeff": ("1131", [-0.89359, 2.27954, -1.18672, 7.07362, -5.45175]),
    "NorthPineCoeff": ("1211", [-1.20914, 1.94740, -0.05947, 1.40958, -0.45810]),
    "NorthSpruceCoeff": ("1221", [-0.79783, 2.07157, -0.73882, 3.16332, -1.82622]),
    "NorthBirchCoeff": ("1231", [-0.44224, 2.47580, -1.40854, 5.16863, -3.77147]),
    # Function group 200 -- volume u.b. from D.B.H. u.b.
    "SouthPineUbCoeff": ("1112", [-1.23602, 1.94126, -0.11924, 1.80842, -0.74261]),
    "SouthSpruceUbCoeff": ("1122", [-1.07676, 1.97159, -0.42776, 2.84877, -1.58630]),
    "SouthBirchUbCoeff": ("1132", [-1.09667, 2.20855, -0.85821, 5.81764, -4.34685]),
    "NorthPineUbCoeff": ("1212", [-1.23242, 1.95242, -0.05839, 1.13440, -0.13476]),
    "NorthSpruceUbCoeff": ("1222", [-0.77561, 2.06126, -0.77713, 3.27580, -1.90707]),
    "NorthBirchUbCoeff": ("1232", [-0.72541, 2.36594, -1.10578, 4.76151, -3.40177]),
    # Function group 300 -- volume u.b. from D.B.H. o.b.
    "SouthPineUbFromObCoeff": ("1113", [-1.52761, 1.82928, 0.07454, 1.43792, -0.35559]),
    "SouthSpruceUbFromObCoeff": ("1123", [-1.06019, 2.04239, -0.54292, 2.80843, -1.52110]),
    "SouthBirchUbFromObCoeff": ("1133", [-0.93631, 2.30212, -1.40378, 8.01817, -6.18825]),
    "NorthPineUbFromObCoeff": ("1213", [-1.25246, 1.98244, -0.13118, 1.03781, -0.03482]),
    "NorthSpruceUbFromObCoeff": ("1223", [-0.82249, 2.11094, -0.89626, 3.51812, -2.05567]),
    "NorthBirchUbFromObCoeff": ("1233", [-0.35394, 2.52141, -1.54257, 4.88165, -3.47422]),
}


@pytest.mark.parametrize(
    ("attr", "table", "published"),
    [(attr, table, published) for attr, (table, published) in APPENDIX_B_FUNCTION_01.items()],
)
def test_coefficients_match_appendix_b(attr, table, published):
    assert getattr(brandel_1990.BrandelVolume, attr) == published, f"Appendix B Table {table}"


# Indicator-variable functions, Brandel (1990) Appendix C, section 1 (V1), function
# 100-01. Each entry is the shared b..e coefficients and the per-class constants, keyed
# by the Appendix C table. The class breaks are asserted separately in the region tests.
APPENDIX_C_FUNCTION_100_01 = {
    "PineSouthWithLatitude": (
        "1.3",
        [1.83182, 0.07275, 2.12777, -1.09439],
        [-1.40718, -1.41955, -1.41472],
    ),
    "BirchSouthWithLatitude": (
        "1.5",
        [2.23818, -1.06930, 6.02015, -4.51472],
        [-0.89363, -0.85480, -0.84627],
    ),
    "PineNorthWithLatitude": (
        "1.6",
        [1.93867, -0.04966, 1.81528, -0.80910],
        [-1.30052, -1.29068, -1.28297, -1.28213],
    ),
    "SpruceSouthWithfieldlayerType": (
        "1.9",
        [1.99915, -0.46351, 2.84571, -1.59871],
        [-1.01862, -1.02745, -1.02651, -1.03775],
    ),
}


@pytest.mark.parametrize(
    ("stem", "table", "bcde", "constants"),
    [
        (stem, table, bcde, constants)
        for stem, (table, bcde, constants) in APPENDIX_C_FUNCTION_100_01.items()
    ],
)
def test_indicator_coefficients_match_appendix_c(stem, table, bcde, constants):
    """b..e and the published per-class constants match Appendix C, function 100-01."""
    coeff = getattr(brandel_1990.BrandelVolume, f"{stem}Coeff")
    const = getattr(brandel_1990.BrandelVolume, f"{stem}Constant")
    assert coeff == [0.0, *bcde], f"Appendix C Table {table} b..e"
    # The published table lists distinct constants; the code may pad the tail with
    # repeats of the last class, so compare only the published span.
    assert const[: len(constants)] == constants, f"Appendix C Table {table} constants"


def test_spruce_north_indicator_matrix_matches_appendix_c():
    """Table 1.11: Spruce North constants are altitude (rows) x latitude (cols)."""
    b = brandel_1990.BrandelVolume
    assert b.SpruceNorthWithLatitudeAndAltitudeCoeff == [0.0, 2.11123, -0.76342, 3.07608, -1.78237]
    assert b.SpruceNorthWithLatitudeAndAltitudeConstant == [
        [-0.74910, -0.75384, -0.75549, -0.76640],  # HH 0-199
        [-0.75208, -0.75682, -0.75847, -0.76938],  # HH 200-499
        [-0.76488, -0.76962, -0.77127, -0.78218],  # HH 500-
    ]


def test_get_coefficients_south_under_bark_from_under_bark_diameter():
    """An under-bark diameter selects Brandel's function group 200."""
    coeffs = brandel_1990.BrandelVolume.get_coefficients(
        part_of_sweden="south",
        latitude=55,
        altitude=None,
        fieldlayer_type=None,
        over_bark=False,
        diameter_over_bark=False,
    )
    assert coeffs["Pine"] == brandel_1990.BrandelVolume.SouthPineUbCoeff
    assert coeffs["Spruce"] == brandel_1990.BrandelVolume.SouthSpruceUbCoeff
    assert coeffs["Birch"] == brandel_1990.BrandelVolume.SouthBirchUbCoeff


def test_get_coefficients_south_under_bark_from_over_bark_diameter():
    """An over-bark diameter selects function group 300, which is the default."""
    coeffs = brandel_1990.BrandelVolume.get_coefficients(
        part_of_sweden="south",
        latitude=55,
        altitude=None,
        fieldlayer_type=None,
        over_bark=False,
    )
    assert coeffs["Pine"] == brandel_1990.BrandelVolume.SouthPineUbFromObCoeff
    assert coeffs["Spruce"] == brandel_1990.BrandelVolume.SouthSpruceUbFromObCoeff
    assert coeffs["Birch"] == brandel_1990.BrandelVolume.SouthBirchUbFromObCoeff


def test_volume_under_bark_is_less_than_over_bark():
    """The bark conventions must be ordered; group 200 fed a D o.b. inverted this."""
    for species in ("pine", "spruce", "birch"):
        for diameter, height in ((10.0, 10.0), (20.0, 18.0), (35.0, 26.0)):
            over = brandel_1990.BrandelVolume.get_volume(
                species, diameter, height, 56.0, None, None, over_bark=True
            )
            under = brandel_1990.BrandelVolume.get_volume(
                species, diameter, height, 56.0, None, None, over_bark=False
            )
            assert 0 < under < over, f"{species} D={diameter} H={height}"


def test_volume_over_bark_from_under_bark_diameter_is_rejected():
    with pytest.raises(ValueError, match="no function for volume over bark"):
        brandel_1990.BrandelVolume.get_volume(
            "pine", 20.0, 18.0, 56.0, None, None, over_bark=True, diameter_over_bark=False
        )


def test_region_splits_on_the_sixtieth_parallel():
    """Brandel's dividing line is latitude 60, in both the plain and detailed paths."""
    for altitude, field_layer in ((None, None), (200, 1)):
        south = brandel_1990.BrandelVolume.get_coefficients(
            part_of_sweden=None,
            latitude=59.5,
            altitude=altitude,
            fieldlayer_type=field_layer,
            over_bark=True,
        )
        north = brandel_1990.BrandelVolume.get_coefficients(
            part_of_sweden=None,
            latitude=60.5,
            altitude=altitude,
            fieldlayer_type=field_layer,
            over_bark=True,
        )
        assert south["Pine"][0] != north["Pine"][0]
    # Latitude 59.5 is South Sweden, so it must not use the northern set.
    plain = brandel_1990.BrandelVolume.get_coefficients(None, 59.5, None, None, over_bark=True)
    assert plain["Pine"] == brandel_1990.BrandelVolume.SouthPineCoeff


def test_explicit_part_of_sweden_overrides_latitude():
    """A site in Dalarna below 60 degrees can still be declared northern."""
    coeffs = brandel_1990.BrandelVolume.get_coefficients(
        part_of_sweden="north",
        latitude=59.8,
        altitude=None,
        fieldlayer_type=None,
        over_bark=True,
    )
    assert coeffs["Pine"] == brandel_1990.BrandelVolume.NorthPineCoeff


def test_get_coefficients_south_detailed_object_fieldlayer():
    class Dummy:
        code = 20

    coeffs = brandel_1990.BrandelVolume.get_coefficients(
        part_of_sweden="south",
        latitude=56,
        altitude=150,
        fieldlayer_type=Dummy(),
        over_bark=True,
    )
    assert coeffs["Birch"][0] == brandel_1990.BrandelVolume.BirchSouthWithLatitudeConstant[0]
    assert coeffs["Pine"][0] == brandel_1990.BrandelVolume.PineSouthWithLatitudeConstant[0]
    assert (
        coeffs["Spruce"][0] == brandel_1990.BrandelVolume.SpruceSouthWithfieldlayerTypeConstant[0]
    )


def test_get_coefficients_north_detailed_under_bark():
    """A northern site must keep northern coefficients under bark.

    The indicator-variable functions are over bark only, so this falls back to
    Appendix B -- but to the *northern* sets.
    """
    coeffs = brandel_1990.BrandelVolume.get_coefficients(
        part_of_sweden="north",
        latitude=66,
        altitude=300,
        fieldlayer_type=1,
        over_bark=False,
        diameter_over_bark=False,
    )
    assert coeffs["Pine"] == brandel_1990.BrandelVolume.NorthPineUbCoeff
    assert coeffs["Spruce"] == brandel_1990.BrandelVolume.NorthSpruceUbCoeff
    assert coeffs["Birch"] == brandel_1990.BrandelVolume.NorthBirchUbCoeff


def test_get_coefficients_south_lat_index_2_no_code():
    coeffs = brandel_1990.BrandelVolume.get_coefficients(
        part_of_sweden="south",
        latitude=59,
        altitude=200,
        fieldlayer_type=object(),
        over_bark=True,
    )
    assert coeffs["Pine"][0] == brandel_1990.BrandelVolume.PineSouthWithLatitudeConstant[2]


def test_get_coefficients_north_altitude_edges():
    coeffs_low = brandel_1990.BrandelVolume.get_coefficients(
        part_of_sweden="north",
        latitude=62,
        altitude=100,
        fieldlayer_type=1,
        over_bark=True,
    )
    assert coeffs_low["Pine"][0] == brandel_1990.BrandelVolume.PineNorthWithLatitudeConstant[0]

    coeffs_high = brandel_1990.BrandelVolume.get_coefficients(
        part_of_sweden="north",
        latitude=68,
        altitude=600,
        fieldlayer_type=1,
        over_bark=True,
    )
    assert (
        coeffs_high["Spruce"][0]
        == brandel_1990.BrandelVolume.SpruceNorthWithLatitudeAndAltitudeConstant[2][3]
    )


def test_get_coefficients_north_lat_index_one():
    coeffs = brandel_1990.BrandelVolume.get_coefficients(
        part_of_sweden="north",
        latitude=64,
        altitude=250,
        fieldlayer_type=1,
        over_bark=True,
    )
    assert coeffs["Pine"][0] == brandel_1990.BrandelVolume.PineNorthWithLatitudeConstant[1]


def test_internal_get_tree_volume_branches(monkeypatch):
    monkeypatch.setattr(brandel_1990.BrandelVolume, "get_volume_log", lambda *_, **__: 100)
    coeff = {"Pine": [], "Spruce": [], "Birch": []}
    assert brandel_1990.BrandelVolume._internal_get_tree_volume(
        10,
        5,
        "pinus sylvestris",
        coeff,
    ) == pytest.approx(0.1)
    assert brandel_1990.BrandelVolume._internal_get_tree_volume(
        10,
        5,
        "picea abies",
        coeff,
    ) == pytest.approx(0.1)
    assert brandel_1990.BrandelVolume._internal_get_tree_volume(
        10,
        5,
        "betula pendula",
        coeff,
    ) == pytest.approx(0.1)
    with pytest.raises(ValueError):
        brandel_1990.BrandelVolume._internal_get_tree_volume(10, 4, "pine", coeff)
    with pytest.raises(ValueError):
        brandel_1990.BrandelVolume._internal_get_tree_volume(10, 5, "unknown", coeff)


def test_get_volume_wrapper(monkeypatch):
    coeffs = {"Pine": [], "Spruce": [], "Birch": []}
    monkeypatch.setattr(
        brandel_1990.BrandelVolume,
        "get_coefficients",
        lambda *args, **kwargs: coeffs,
    )
    monkeypatch.setattr(
        brandel_1990.BrandelVolume,
        "_internal_get_tree_volume",
        lambda *a, **k: 0.5,
    )
    result = brandel_1990.BrandelVolume.get_volume(
        species="pine",
        diameter_cm=10,
        height_m=15,
        latitude=56,
        altitude=100,
        field_layer=1,
        over_bark=True,
    )
    assert result == 0.5


def test_get_volume_north_branch(monkeypatch):
    monkeypatch.setattr(
        brandel_1990.BrandelVolume,
        "get_coefficients",
        lambda *args, **kwargs: {"Pine": [], "Spruce": [], "Birch": []},
    )
    monkeypatch.setattr(
        brandel_1990.BrandelVolume,
        "_internal_get_tree_volume",
        lambda *a, **k: 1.0,
    )
    result = brandel_1990.BrandelVolume.get_volume(
        species="pine",
        diameter_cm=10,
        height_m=15,
        latitude=65,
        altitude=None,
        field_layer=None,
        over_bark=True,
    )
    assert result == 1.0


# -- Tests for volume package __init__ ---------------------------------------


def test_volume_module_lazy_loading_and_dir():
    volume = importlib.reload(importlib.import_module("pyforestry.sweden.volume"))
    from pyforestry.sweden.volume.naslund_1947 import NaslundVolume

    assert volume.__dir__() == sorted(volume.__all__)
    assert volume.NaslundVolume is NaslundVolume
    with pytest.raises(AttributeError):
        volume.does_not_exist  # noqa: B018
