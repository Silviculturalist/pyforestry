import pytest

from pyforestry.base.helpers import Age, SiteIndexValue, TreeSpecies
from pyforestry.sweden.site.enums import Sweden, county_flags_syz_t_area
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970
from pyforestry.sweden.siteindex.translate.hagglund_1981_si_to_productivity import (
    hagglund_1981_SI_to_productivity,
)
from pyforestry.sweden.siteindex.translate.jonson_index import (
    jonson_index_from_m3sk,
    jonson_index_from_site_index,
)


def _make_h100(value: float, species):
    return SiteIndexValue(
        value,
        reference_age=Age.TOTAL(100),
        species={species},
        fn=Hagglund_1970.height_trajectory.pinus_sylvestris.sweden,
    )


def test_jonson_index_from_m3sk_bounds():
    assert jonson_index_from_m3sk(1.0) == 8
    assert jonson_index_from_m3sk(2.0) == 7
    assert jonson_index_from_m3sk(2.5) == 6
    assert jonson_index_from_m3sk(10.0) == 1


def test_jonson_index_from_site_index_matches_productivity():
    h100 = _make_h100(20.0, TreeSpecies.Sweden.pinus_sylvestris)
    main_species = TreeSpecies.Sweden.pinus_sylvestris
    vegetation = Sweden.FieldLayer.BILBERRY
    altitude = 100.0
    county = Sweden.County.VARMLAND

    expected_m3sk = hagglund_1981_SI_to_productivity(
        h100_input=h100,
        main_species=main_species,
        vegetation=vegetation,
        altitude=altitude,
        county=county,
    )
    expected = jonson_index_from_m3sk(expected_m3sk)

    assert (
        jonson_index_from_site_index(
            h100_input=h100,
            main_species=main_species,
            vegetation=vegetation,
            altitude=altitude,
            county=county,
        )
        == expected
    )


def test_jonson_index_requires_h100():
    h100 = SiteIndexValue(
        20.0,
        reference_age=Age.TOTAL(80),
        species={TreeSpecies.Sweden.pinus_sylvestris},
        fn=Hagglund_1970.height_trajectory.pinus_sylvestris.sweden,
    )
    with pytest.raises(ValueError):
        jonson_index_from_site_index(
            h100_input=h100,
            main_species=TreeSpecies.Sweden.pinus_sylvestris,
            vegetation=Sweden.FieldLayer.BILBERRY,
            altitude=100.0,
            county=Sweden.County.VARMLAND,
        )


def test_jonson_index_rejects_invalid_species():
    h100 = _make_h100(20.0, TreeSpecies.Sweden.betula_pendula)
    with pytest.raises(ValueError):
        jonson_index_from_site_index(
            h100_input=h100,
            main_species=TreeSpecies.Sweden.betula_pendula,
            vegetation=Sweden.FieldLayer.BILBERRY,
            altitude=100.0,
            county=Sweden.County.VARMLAND,
        )


def test_jonson_index_rejects_species_mismatch():
    h100 = _make_h100(20.0, TreeSpecies.Sweden.pinus_sylvestris)
    with pytest.raises(ValueError):
        jonson_index_from_site_index(
            h100_input=h100,
            main_species=TreeSpecies.Sweden.picea_abies,
            vegetation=Sweden.FieldLayer.BILBERRY,
            altitude=100.0,
            county=Sweden.County.VARMLAND,
        )


def test_jonson_index_rejects_unknown_fn():
    h100 = SiteIndexValue(
        20.0,
        reference_age=Age.TOTAL(100),
        species={TreeSpecies.Sweden.pinus_sylvestris},
        fn=lambda x: x,
    )
    with pytest.raises(ValueError):
        jonson_index_from_site_index(
            h100_input=h100,
            main_species=TreeSpecies.Sweden.pinus_sylvestris,
            vegetation=Sweden.FieldLayer.BILBERRY,
            altitude=100.0,
            county=Sweden.County.VARMLAND,
        )


def test_county_flags_syz_t_area():
    assert county_flags_syz_t_area(None) == (0, 0, 0)
    assert county_flags_syz_t_area(Sweden.County.GOTLAND) == (1, 0, 0)
    assert county_flags_syz_t_area(Sweden.County.OREBRO) == (0, 0, 1)

    gotland, syz, t_area = county_flags_syz_t_area(Sweden.County.VARMLAND)
    assert gotland == 0
    assert syz == 1
    assert t_area == 0

    _, syz, _ = county_flags_syz_t_area(Sweden.County.GAVLEBORG_HALSINGLANDS)
    assert syz == 0
    _, syz, _ = county_flags_syz_t_area(Sweden.County.GAVLEBORG_OVRIGA)
    assert syz == 0
