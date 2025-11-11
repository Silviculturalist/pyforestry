import numpy as np
import pytest

from pyforestry.base.helpers import Age, Diameter_cm, SiteIndexValue, TreeSpecies
from pyforestry.sweden.biomass.petersson_1999 import Petersson1999
from pyforestry.sweden.siteindex import Hagglund_1970

# Helper functions mirroring the equations for expected values


def spruce_expected(**kwargs):
    d = float(kwargs["diameter_cm"])
    age = float(kwargs["age_at_breast_height"])
    si = float(kwargs["SI"])
    dom = kwargs["dominant_species"]
    inc = kwargs["five_years_radial_increment_mm"]
    peat = kwargs["peat"]
    lat = kwargs["latitude"]
    picea = dom is TreeSpecies.Sweden.picea_abies
    pinus = dom is TreeSpecies.Sweden.pinus_sylvestris
    mm = d * 10
    inc01 = inc * 10
    age_log = np.log(age)
    inc_log = np.log(inc01)
    return {
        "stem_above_bark": np.exp(
            -6.839310
            + 3.578450 * np.log(mm + 25)
            - 0.003042 * mm
            + 0.093033 * inc_log
            - 0.002763 * inc01
            + 0.111347 * age_log
            + 0.012148 * si * picea
            + 0.011586 * si * pinus
            - 0.000020194 * lat
            + (0.17069**2) / 2
        ),
        "bark": np.exp(
            -4.084706
            + 2.397166 * np.log(mm + 10)
            - 0.066053 * inc_log
            + 0.151696 * age_log
            + (0.22759**2) / 2
        ),
        "needles": np.exp(
            -1.130238
            + 1.485407 * np.log(mm)
            + 0.514648 * inc_log
            + 0.206901 * age_log
            + (0.30852**2) / 2
        ),
        "living_branches": np.exp(
            -0.718621
            + 1.740810 * np.log(mm)
            + 0.348379 * inc_log
            + 0.180503 * age_log
            + (0.28825**2) / 2
        ),
        "dead_branches": np.exp(
            -1.763738
            + 2.616200 * np.log(mm)
            - 0.745459 * inc_log
            - 0.359509 * age_log
            + (0.79373**2) / 2
        ),
        "stump_root_gt5": np.exp(
            -1.980469 + 2.339527 * np.log(mm) + 0.342786 * peat + (0.28283**2) / 2
        ),
        "above_stump": np.exp(
            -0.437361
            + 2.446692 * np.log(mm + 9)
            + 0.065779 * inc_log
            + 0.102290 * age_log
            - 0.000021633 * lat
            + (0.15492**2) / 2
        ),
        "total": np.exp(
            -0.614093
            + 2.425997 * np.log(mm + 8)
            + 0.081636 * inc_log
            + 0.128027 * age_log
            - 0.000015810 * lat
            + (0.15985**2) / 2
        ),
        "excluding_small_roots": np.exp(
            -0.766217
            + 2.491024 * np.log(mm + 8)
            + 0.070526 * inc_log
            + 0.113514 * age_log
            - 0.000017876 * lat
            + (0.16274**2) / 2
        ),
    }


def pine_expected(**kwargs):
    d = float(kwargs["diameter_cm"])
    age = float(kwargs["age_at_breast_height"])
    si = float(kwargs["SI"])
    dom = kwargs["dominant_species"]
    inc = kwargs["five_years_radial_increment_mm"]
    peat = kwargs["peat"]
    lat = kwargs["latitude"]
    lon = kwargs["longitude"]
    alt = kwargs["altitude"]
    picea = dom is TreeSpecies.Sweden.picea_abies
    pinus = dom is TreeSpecies.Sweden.pinus_sylvestris
    mm = d * 10
    inc01 = inc * 10
    age_log = np.log(age)
    inc_log = np.log(inc01)
    return {
        "stem_above_bark": np.exp(
            -7.674621
            + 3.155671 * np.log(mm + 25)
            - 0.002197 * mm
            + 0.084427 * inc_log
            - 0.002665 * inc01
            + 0.253227 * age_log
            + 0.028478 * si * picea
            + 0.031435 * si * pinus
            + 0.000008342 * lat
            + (0.17803**2) / 2
        ),
        "bark": np.exp(
            -1.340149
            + 2.209719 * np.log(mm + 13)
            - 0.001986 * inc_log
            - 0.000024146 * lat
            + (0.26942**2) / 2
        ),
        "needles": np.exp(
            -2.597267
            + 1.506121 * np.log(mm)
            + 0.571366 * inc_log
            + 0.208130 * age_log
            + 0.000870 * alt
            + (0.35753**2) / 2
        ),
        "living_branches": np.exp(
            -2.533220
            + 1.989129 * np.log(mm)
            + 0.387203 * inc_log
            + 0.105215 * age_log
            + (0.34938**2) / 2
        ),
        "dead_branches": np.exp(
            1.596001
            + 2.441173 * np.log(mm)
            - 0.437497 * inc_log
            - 0.711616 * age_log
            - 0.001358 * alt
            - 0.000129 * lon
            + (0.76730**2) / 2
        ),
        "above_stump": np.exp(
            -2.032666
            + 2.413856 * np.log(mm + 6)
            + 0.130304 * age_log
            + 0.011834 * si * picea
            + 0.013668 * si * pinus
            + (0.15651**2) / 2
        ),
        "total": np.exp(
            -1.507568
            + 2.449121 * np.log(mm + 5)
            + 0.104243 * age_log
            - 0.000321 * alt
            + (0.16332**2) / 2
        ),
        "excluding_small_roots": np.exp(
            -1.756201
            + 2.483808 * np.log(mm + 5)
            + 0.107190 * age_log
            - 0.000325 * alt
            + (0.16086**2) / 2
        ),
        "stump_root_gt5": np.exp(
            -1.980469
            + 2.339527 * np.log(mm)
            + 0.342786 * peat
            - 0.224812 * True
            + (0.28283**2) / 2
        ),
    }


def birch_expected(**kwargs):
    d = float(kwargs["diameter_cm"])
    age = float(kwargs["age_at_breast_height"])
    si = float(kwargs["SI"])
    dom = kwargs["dominant_species"]
    inc = kwargs["five_years_radial_increment_mm"]
    lat = kwargs["latitude"]
    picea = dom is TreeSpecies.Sweden.picea_abies
    pinus = dom is TreeSpecies.Sweden.pinus_sylvestris
    mm = d * 10
    inc01 = inc * 10
    age_log = np.log(age)
    inc_log = np.log(inc01)
    return {
        "stem_above_bark": np.exp(
            -3.091932
            + 2.479648 * np.log(mm + 7)
            + 0.243747 * age_log
            + 0.022185 * si * picea
            + 0.022955 * si * pinus
            + (0.19827**2) / 2
        ),
        "bark": np.exp(
            -3.244490
            + 2.525420 * np.log(mm + 18)
            + 0.329744 * age_log
            - 0.000030180 * lat
            + (0.25483**2) / 2
        ),
        "living_branches": np.exp(
            -2.782537 + 2.276815 * np.log(mm) + 0.228528 * inc_log + (0.45153**2) / 2
        ),
        "dead_branches": np.exp(-2.059091 + 1.657683 * np.log(mm) + (1.12848**2) / 2),
        "above_stump": np.exp(
            -0.423749
            + 2.574575 * np.log(mm + 8)
            + 0.090419 * age_log
            - 0.000026862 * lat
            + (0.17071**2) / 2
        ),
    }


@pytest.mark.parametrize(
    "species,expected_func",
    [
        (TreeSpecies.Sweden.picea_abies, spruce_expected),
        (TreeSpecies.Sweden.pinus_sylvestris, pine_expected),
        (TreeSpecies.Sweden.betula_pendula, birch_expected),
    ],
)
def test_dispatch_matches_individual(species, expected_func):
    args = {
        "diameter_cm": Diameter_cm(20),
        "height_m": 18,
        "age_at_breast_height": Age.DBH(40),
        "SI": SiteIndexValue(
            25,
            Age.TOTAL(100),
            {TreeSpecies.Sweden.picea_abies},
            Hagglund_1970.height_trajectory.picea_abies.northern_sweden,
        ),
        "five_years_radial_increment_mm": 4,
        "peat": False,
        "latitude": 60,
        "longitude": 15,
        "altitude": 200,
    }
    result = Petersson1999.biomass(species, **args)
    expected = expected_func(dominant_species=TreeSpecies.Sweden.picea_abies, **args)
    for key, val in expected.items():
        assert result[key] == pytest.approx(val)


def test_invalid_species():
    with pytest.raises(ValueError):
        Petersson1999.biomass(
            "invalid",
            Diameter_cm(20),
            18,
            Age.DBH(40),
            SiteIndexValue(
                25,
                Age.TOTAL(100),
                {TreeSpecies.Sweden.picea_abies},
                Hagglund_1970.height_trajectory.picea_abies.northern_sweden,
            ),
            4,
            False,
            60,
            15,
            200,
        )


def test_site_index_validation():
    with pytest.raises(ValueError):
        Petersson1999.biomass(
            TreeSpecies.Sweden.picea_abies,
            Diameter_cm(20),
            18,
            Age.DBH(40),
            SiteIndexValue(
                25,
                Age.TOTAL(50),
                {TreeSpecies.Sweden.picea_abies},
                Hagglund_1970.height_trajectory.picea_abies.northern_sweden,
            ),
            five_years_radial_increment_mm=4,
            peat=False,
            latitude=60,
            longitude=15,
            altitude=200,
        )

    with pytest.raises(ValueError):
        Petersson1999.biomass(
            TreeSpecies.Sweden.picea_abies,
            Diameter_cm(20),
            18,
            Age.DBH(40),
            SiteIndexValue(
                25,
                Age.TOTAL(100),
                {TreeSpecies.Sweden.betula_pendula},
                Hagglund_1970.height_trajectory.picea_abies.northern_sweden,
            ),
            five_years_radial_increment_mm=4,
            peat=False,
            latitude=60,
            longitude=15,
            altitude=200,
        )

    with pytest.raises(ValueError):
        Petersson1999.biomass(
            TreeSpecies.Sweden.picea_abies,
            Diameter_cm(20),
            18,
            Age.DBH(40),
            SiteIndexValue(
                25,
                Age.TOTAL(100),
                {TreeSpecies.Sweden.picea_abies},
                lambda: None,
            ),
            five_years_radial_increment_mm=4,
            peat=False,
            latitude=60,
            longitude=15,
            altitude=200,
        )


def test_numeric_si_with_string_species():
    args = {
        "diameter_cm": Diameter_cm(20),
        "height_m": 18,
        "age_at_breast_height": Age.DBH(40),
        "SI": 25.0,
        "dominant_species": "Picea abies",
        "five_years_radial_increment_mm": 4,
        "peat": False,
        "latitude": 60,
        "longitude": 15,
        "altitude": 200,
    }
    result = Petersson1999.biomass(TreeSpecies.Sweden.picea_abies, **args)
    args_for_expected = args.copy()
    args_for_expected["dominant_species"] = TreeSpecies.Sweden.picea_abies
    expected = spruce_expected(**args_for_expected)
    for key, val in expected.items():
        assert result[key] == pytest.approx(val)


def test_numeric_si_requires_dominant_species():
    with pytest.raises(TypeError):
        Petersson1999.biomass(
            TreeSpecies.Sweden.picea_abies,
            Diameter_cm(20),
            18,
            Age.DBH(40),
            25.0,
            five_years_radial_increment_mm=4,
            peat=False,
            latitude=60,
            longitude=15,
            altitude=200,
        )


def _si_spruce():
    return SiteIndexValue(
        25,
        Age.TOTAL(100),
        {TreeSpecies.Sweden.picea_abies},
        Hagglund_1970.height_trajectory.picea_abies.northern_sweden,
    )


def _si_pine():
    return SiteIndexValue(
        25,
        Age.TOTAL(100),
        {TreeSpecies.Sweden.pinus_sylvestris},
        Hagglund_1970.height_trajectory.pinus_sylvestris.sweden,
    )


def test_validate_site_index_type_error():
    with pytest.raises(TypeError):
        Petersson1999._validate_site_index(5)


def test_validate_site_index_pine():
    si = _si_pine()
    assert Petersson1999._validate_site_index(si) is TreeSpecies.Sweden.pinus_sylvestris


def test_si_numeric_invalid_dominant_species():
    with pytest.raises(ValueError):
        Petersson1999.biomass(
            TreeSpecies.Sweden.picea_abies,
            Diameter_cm(20),
            18,
            Age.DBH(40),
            25.0,
            five_years_radial_increment_mm=4,
            peat=False,
            latitude=60,
            longitude=15,
            altitude=200,
            dominant_species=TreeSpecies.Sweden.betula_pendula,
        )


@pytest.mark.parametrize(
    "func,si",
    [
        (Petersson1999.spruce, _si_spruce()),
        (Petersson1999.pine, _si_spruce()),
        (Petersson1999.birch, _si_spruce()),
    ],
)
def test_measurement_height_warning(func, si):
    with pytest.warns(UserWarning):
        func(
            Diameter_cm(20, measurement_height_m=1.4),
            18,
            Age.DBH(40),
            si,
            five_years_radial_increment_mm=4,
            peat=False,
            latitude=60,
            longitude=15,
            altitude=200,
        )


@pytest.mark.parametrize(
    "func,si",
    [
        (Petersson1999.spruce, _si_spruce()),
        (Petersson1999.pine, _si_spruce()),
        (Petersson1999.birch, _si_spruce()),
    ],
)
def test_diameter_over_bark_required(func, si):
    with pytest.raises(ValueError):
        func(
            Diameter_cm(20, over_bark=False),
            18,
            Age.DBH(40),
            si,
            five_years_radial_increment_mm=4,
            peat=False,
            latitude=60,
            longitude=15,
            altitude=200,
        )


@pytest.mark.parametrize(
    "func,si",
    [
        (Petersson1999.spruce, _si_spruce()),
        (Petersson1999.pine, _si_spruce()),
        (Petersson1999.birch, _si_spruce()),
    ],
)
def test_age_measurement_code_check(func, si):
    with pytest.raises(TypeError):
        func(
            Diameter_cm(20),
            18,
            Age.TOTAL(40),
            si,
            five_years_radial_increment_mm=4,
            peat=False,
            latitude=60,
            longitude=15,
            altitude=200,
        )


def test_age_as_float():
    si = _si_spruce()
    result = Petersson1999.spruce(
        20.0,
        18,
        40.0,
        si,
        five_years_radial_increment_mm=4,
        peat=False,
        latitude=60,
        longitude=15,
        altitude=200,
    )
    expected = spruce_expected(
        diameter_cm=20.0,
        height_m=18,
        age_at_breast_height=40.0,
        SI=si,
        five_years_radial_increment_mm=4,
        peat=False,
        latitude=60,
        longitude=15,
        altitude=200,
        dominant_species=TreeSpecies.Sweden.picea_abies,
    )
    for k, v in expected.items():
        assert result[k] == pytest.approx(v)


def test_species_type_check():
    with pytest.raises(TypeError):
        Petersson1999.biomass(
            1,
            Diameter_cm(20),
            18,
            Age.DBH(40),
            _si_spruce(),
            five_years_radial_increment_mm=4,
            peat=False,
            latitude=60,
            longitude=15,
            altitude=200,
        )


def test_unsupported_species():
    with pytest.raises(ValueError):
        Petersson1999.biomass(
            TreeSpecies.Sweden.quercus_robur,
            Diameter_cm(20),
            18,
            Age.DBH(40),
            _si_spruce(),
            five_years_radial_increment_mm=4,
            peat=False,
            latitude=60,
            longitude=15,
            altitude=200,
        )
