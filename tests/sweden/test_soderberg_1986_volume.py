import math

import pytest

from pyforestry.base.helpers import Age, SiteIndexValue
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970
from pyforestry.sweden.volume.soderberg_1986_form_height import (
    soderberg_1986_form_height_m,
    soderberg_1986_volume_m3,
)


@pytest.mark.parametrize(
    ("kwargs", "expected_form_height", "expected_volume"),
    [
        (
            dict(
                species=TreeSpecies.Sweden.pinus_sylvestris,
                diameter_cm=30.0,
                age_bh_years=40.0,
                max_diameter_cm=45.0,
                stand_basal_area_m2_ha=25.0,
                dominant_species=TreeSpecies.Sweden.pinus_sylvestris,
                site_index_dominant_m=20.0,
                latitude_deg=60.0,
                altitude_m=100.0,
                part_of_sweden="north",
                distance_to_coast_lt_50km=True,
                split_plot=False,
                crowberry=True,
                south_slope=False,
                wet_soil=False,
                fertilized=False,
                herbs=False,
                maritime=False,
                region5=False,
                continental=False,
                north_slope=False,
                dry_soil=False,
                south_east=False,
                groundwater_never=False,
                prop_pine=0.6,
                prop_spruce=0.3,
                prop_birch=0.1,
                prop_beech=0.0,
                prop_oak=0.0,
                gotland=False,
            ),
            6.881162794364282,
            0.48640073586593036,
        ),
        (
            dict(
                species=TreeSpecies.Sweden.picea_abies,
                diameter_cm=28.0,
                age_bh_years=35.0,
                max_diameter_cm=40.0,
                stand_basal_area_m2_ha=20.0,
                dominant_species=TreeSpecies.Sweden.picea_abies,
                site_index_dominant_m=22.0,
                latitude_deg=57.5,
                altitude_m=30.0,
                part_of_sweden="gotland",
                distance_to_coast_lt_50km=False,
                split_plot=True,
                crowberry=False,
                south_slope=False,
                wet_soil=False,
                fertilized=False,
                herbs=True,
                maritime=False,
                region5=False,
                continental=False,
                north_slope=False,
                dry_soil=False,
                south_east=False,
                groundwater_never=False,
                prop_pine=0.2,
                prop_spruce=0.7,
                prop_birch=0.1,
                prop_beech=0.0,
                prop_oak=0.0,
                gotland=False,
            ),
            7.58477590249802,
            0.46703421458648836,
        ),
        (
            dict(
                species=TreeSpecies.Sweden.pinus_contorta,
                diameter_cm=25.0,
                age_bh_years=30.0,
                max_diameter_cm=40.0,
                stand_basal_area_m2_ha=22.0,
                dominant_species=TreeSpecies.Sweden.pinus_sylvestris,
                site_index_dominant_m=20.0,
                latitude_deg=58.0,
                altitude_m=80.0,
                part_of_sweden="south",
                distance_to_coast_lt_50km=False,
                split_plot=False,
                crowberry=False,
                south_slope=False,
                wet_soil=False,
                fertilized=False,
                herbs=False,
                maritime=False,
                region5=False,
                continental=False,
                north_slope=False,
                dry_soil=False,
                south_east=False,
                groundwater_never=False,
                prop_pine=0.6,
                prop_spruce=0.3,
                prop_birch=0.1,
                prop_beech=0.0,
                prop_oak=0.0,
                gotland=False,
            ),
            8.729343409112266,
            0.4285006425738996,
        ),
    ],
)
def test_soderberg_1986_form_height_and_volume(kwargs, expected_form_height, expected_volume):
    form_height = soderberg_1986_form_height_m(**kwargs)
    volume = soderberg_1986_volume_m3(**kwargs)
    assert form_height == pytest.approx(expected_form_height, rel=1e-6)
    assert volume == pytest.approx(expected_volume, rel=1e-6)


def test_soderberg_1986_volume_relation():
    kwargs = dict(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        diameter_cm=30.0,
        age_bh_years=40.0,
        max_diameter_cm=45.0,
        stand_basal_area_m2_ha=25.0,
        dominant_species=TreeSpecies.Sweden.pinus_sylvestris,
        site_index_dominant_m=20.0,
        latitude_deg=60.0,
        altitude_m=100.0,
        part_of_sweden="north",
        distance_to_coast_lt_50km=True,
        split_plot=False,
        crowberry=True,
        south_slope=False,
        wet_soil=False,
        fertilized=False,
        herbs=False,
        maritime=False,
        region5=False,
        continental=False,
        north_slope=False,
        dry_soil=False,
        south_east=False,
        groundwater_never=False,
        prop_pine=0.6,
        prop_spruce=0.3,
        prop_birch=0.1,
        prop_beech=0.0,
        prop_oak=0.0,
        gotland=False,
    )
    form_height = soderberg_1986_form_height_m(**kwargs)
    volume = soderberg_1986_volume_m3(**kwargs)
    basal_area_cm2 = math.pi * (kwargs["diameter_cm"] ** 2) / 4.0
    assert volume == pytest.approx(form_height * basal_area_cm2 / 10000.0, rel=1e-12)


def test_soderberg_1986_form_height_accepts_site_index_value():
    pine_site_index = SiteIndexValue(
        20.0,
        reference_age=Age.TOTAL(100),
        species={TreeSpecies.Sweden.pinus_sylvestris},
        fn=Hagglund_1970.height_trajectory.pinus_sylvestris.sweden,
    )
    kwargs = dict(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        diameter_cm=30.0,
        age_bh_years=40.0,
        max_diameter_cm=45.0,
        stand_basal_area_m2_ha=25.0,
        dominant_species=TreeSpecies.Sweden.pinus_sylvestris,
        site_index_dominant_m=pine_site_index,
        latitude_deg=60.0,
        altitude_m=100.0,
        part_of_sweden="north",
        distance_to_coast_lt_50km=True,
        split_plot=False,
        crowberry=True,
        south_slope=False,
        wet_soil=False,
        fertilized=False,
        herbs=False,
        maritime=False,
        region5=False,
        continental=False,
        north_slope=False,
        dry_soil=False,
        south_east=False,
        groundwater_never=False,
        prop_pine=0.6,
        prop_spruce=0.3,
        prop_birch=0.1,
        prop_beech=0.0,
        prop_oak=0.0,
        gotland=False,
    )
    form_height = soderberg_1986_form_height_m(**kwargs)
    assert form_height == pytest.approx(6.881162794364282, rel=1e-6)


def test_soderberg_1986_form_height_rejects_dominant_species_site_index_mismatch():
    spruce_site_index = SiteIndexValue(
        22.0,
        reference_age=Age.TOTAL(100),
        species={TreeSpecies.Sweden.picea_abies},
        fn=Hagglund_1970.height_trajectory.picea_abies.northern_sweden,
    )
    kwargs = dict(
        species=TreeSpecies.Sweden.pinus_sylvestris,
        diameter_cm=30.0,
        age_bh_years=40.0,
        max_diameter_cm=45.0,
        stand_basal_area_m2_ha=25.0,
        dominant_species=TreeSpecies.Sweden.pinus_sylvestris,
        site_index_dominant_m=spruce_site_index,
        latitude_deg=60.0,
        altitude_m=100.0,
        part_of_sweden="north",
        distance_to_coast_lt_50km=True,
        split_plot=False,
        crowberry=True,
        south_slope=False,
        wet_soil=False,
        fertilized=False,
        herbs=False,
        maritime=False,
        region5=False,
        continental=False,
        north_slope=False,
        dry_soil=False,
        south_east=False,
        groundwater_never=False,
        prop_pine=0.6,
        prop_spruce=0.3,
        prop_birch=0.1,
        prop_beech=0.0,
        prop_oak=0.0,
        gotland=False,
    )
    with pytest.raises(ValueError, match="site_index_dominant_m\\.species"):
        soderberg_1986_form_height_m(**kwargs)
