from typing import cast

import pytest

from pyforestry.base.helpers import Age, SiteIndexValue, TreeSpecies
from pyforestry.sweden.blocks.eko1985 import (
    DominantHeightObservation,
    Eko1985SiteContext,
    EkoStandSite,
    EngineStand,
    EngineStandPart,
    RegionSE,
)
from pyforestry.sweden.blocks.eko1985 import (
    Eko1985SiteContext as ExtractedEko1985SiteContext,
)
from pyforestry.sweden.blocks.eko1985 import EkoStandSite as ExtractedEkoStandSite
from pyforestry.sweden.blocks.eko1985 import EngineStand as ExtractedEngineStand
from pyforestry.sweden.blocks.eko1985 import EngineStandPart as ExtractedEngineStandPart
from pyforestry.sweden.site.enums import Sweden
from pyforestry.sweden.site.swedish_site import SwedishSite
from pyforestry.sweden.siteindex.carbonnier_1971 import CarbonnierHeightModel
from pyforestry.sweden.siteindex.hagglund_1970 import Hagglund_1970


def test_model_site_context_exports_use_extracted_formula_types():
    assert Eko1985SiteContext is ExtractedEko1985SiteContext
    assert EkoStandSite is ExtractedEkoStandSite
    assert EngineStand is ExtractedEngineStand
    assert EngineStandPart is ExtractedEngineStandPart


class DummySwedishSite:
    def __init__(
        self,
        *,
        latitude: float,
        longitude: float,
        altitude: float | None = None,
        field_layer: Sweden.FieldLayer | None = None,
        soil_moisture: Sweden.SoilMoistureEnum | None = None,
        climate_zone: Sweden.ClimateZone | None = None,
        sis_spruce_100: float | None = None,
        sis_pine_100: float | None = None,
    ) -> None:
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude
        self.field_layer = field_layer
        self.soil_moisture = soil_moisture
        self.climate_zone = climate_zone
        self.sis_spruce_100 = sis_spruce_100
        self.sis_pine_100 = sis_pine_100


def test_site_context_requires_coordinates_for_region():
    context = Eko1985SiteContext(
        latitude=60.0,
        altitude=120.0,
        vegetation=Sweden.FieldLayer.BILBERRY,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC_MOIST,
        spruce_site_index=20.0,
        pine_site_index=20.0,
    )

    with pytest.raises(ValueError, match="latitude and longitude"):
        context.resolved_region()


def test_site_context_region_uses_coordinates():
    context = Eko1985SiteContext(
        latitude=64.0,
        longitude=20.0,
        altitude=150.0,
        vegetation=Sweden.FieldLayer.BILBERRY,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC_MOIST,
        spruce_site_index=18.0,
        pine_site_index=18.0,
    )

    assert context.resolved_region() == "North"
    site = context.to_site()
    assert site.region == "North"
    assert context.vegetation_code() == Sweden.FieldLayer.BILBERRY.value.code
    assert context.soil_moisture_code() == Sweden.SoilMoistureEnum.MESIC_MOIST.value.code


def test_site_context_accepts_integer_codes():
    context = Eko1985SiteContext(
        latitude=60.5,
        longitude=18.0,
        altitude=110.0,
        vegetation=13,
        soil_moisture=3,
        spruce_site_index=20.0,
        pine_site_index=20.0,
    )

    assert context.vegetation_code() == 13
    assert context.soil_moisture_code() == 3


def test_site_context_enum_helpers_return_none():
    context = Eko1985SiteContext(vegetation=999, soil_moisture=999)
    assert context._as_field_layer() is None
    assert context._as_soil_moisture() is None


def test_site_context_uses_swedish_site_metadata():
    dummy = DummySwedishSite(
        latitude=61.0,
        longitude=17.0,
        altitude=120.0,
        field_layer=Sweden.FieldLayer.BILBERRY,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC_MOIST,
        climate_zone=Sweden.ClimateZone.K1,
    )
    context = Eko1985SiteContext(swedish_site=cast(SwedishSite, dummy))

    assert context._resolved_latitude() == 61.0
    assert context._resolved_altitude() == 120.0
    assert context.resolved_region() == "Central"
    assert context.vegetation_code() == Sweden.FieldLayer.BILBERRY.value.code
    assert context.soil_moisture_code() == Sweden.SoilMoistureEnum.MESIC_MOIST.value.code


def test_site_context_region_fallbacks_to_latitude():
    dummy = DummySwedishSite(
        latitude=61.5,
        longitude=17.0,
        altitude=100.0,
        climate_zone=None,
    )
    context = Eko1985SiteContext(swedish_site=cast(SwedishSite, dummy))

    assert context.resolved_region() == "Central"


def test_site_context_resolves_indices_from_swedish_site():
    dummy = DummySwedishSite(
        latitude=61.0,
        longitude=17.0,
        altitude=120.0,
        climate_zone=Sweden.ClimateZone.K1,
        sis_spruce_100=21.0,
        sis_pine_100=19.0,
    )
    context = Eko1985SiteContext(swedish_site=cast(SwedishSite, dummy))

    spruce_si, pine_si, _beech = context.resolve_site_indices()
    assert spruce_si is not None
    assert pine_si is not None
    assert float(spruce_si) == pytest.approx(21.0)
    assert float(pine_si) == pytest.approx(19.0)


def test_site_context_translates_missing_indices():
    pine_only = Eko1985SiteContext(pine_site_index=18.0)
    spruce_si, pine_si, _beech = pine_only.resolve_site_indices()
    assert spruce_si is not None
    assert pine_si is not None
    assert float(pine_si) == pytest.approx(18.0)

    spruce_value = SiteIndexValue(
        20.0,
        reference_age=Age.TOTAL(100.0),
        species={TreeSpecies.Sweden.picea_abies},
        fn=Hagglund_1970.height_trajectory.picea_abies.northern_sweden,
    )
    spruce_only = Eko1985SiteContext(spruce_site_index=spruce_value)
    spruce_si, pine_si, _beech = spruce_only.resolve_site_indices()
    assert spruce_si is spruce_value
    assert pine_si is not None


def test_site_context_rejects_non_hagglund_site_index_function():
    pine_value = SiteIndexValue(
        20.0,
        reference_age=Age.TOTAL(100.0),
        species={TreeSpecies.Sweden.pinus_sylvestris},
        fn=lambda *_: None,
    )
    context = Eko1985SiteContext(pine_site_index=pine_value)
    with pytest.raises(ValueError, match="site_index\\.fn"):
        context.resolve_site_indices()


def test_site_context_observation_paths():
    model = CarbonnierHeightModel(
        ages=[40, 60, 100],
        a_vals=[5.0, 6.0, 8.0],
        b_vals=[1.0, 1.1, 1.3],
    )
    context = Eko1985SiteContext(
        latitude=64.0,
        longitude=20.0,
        spruce_height_obs=DominantHeightObservation.from_values(12.0, 40),
        pine_height_obs=DominantHeightObservation.from_values(11.0, 35),
        beech_height_obs=DominantHeightObservation.from_values(10.0, 40),
        carbonnier_model=model,
    )

    spruce_si, pine_si, beech_si = context.resolve_site_indices()
    assert isinstance(spruce_si, SiteIndexValue)
    assert isinstance(pine_si, SiteIndexValue)
    assert isinstance(beech_si, SiteIndexValue)


def test_site_context_to_site_requires_site_index():
    context = Eko1985SiteContext(latitude=60.0, longitude=18.0)

    with pytest.raises(ValueError, match="spruce or pine site index"):
        context.to_site()


def test_eko_stand_site_region_and_warnings():
    with pytest.warns(UserWarning, match="SI Pine"):
        site = EkoStandSite(
            latitude=59.0,
            altitude=100.0,
            vegetation=None,
            soil_moisture=Sweden.SoilMoistureEnum.DRY,
            H100_Pine=40.0,
            region="NORRA",
        )

    assert site.region == "North"
    assert site.Bilberry_or_Cowberry is False
    assert site.herbs_grasses_no_field_layer is False


def test_eko_stand_site_requires_h100():
    with pytest.raises(ValueError, match="H100"):
        EkoStandSite(latitude=60.0, altitude=100.0, region=RegionSE.NORRA)


def test_eko_stand_site_warns_on_spruce_range():
    with pytest.warns(UserWarning, match="SI Spruce"):
        site = EkoStandSite(
            latitude=59.0,
            altitude=100.0,
            vegetation=13,
            soil_moisture=Sweden.SoilMoistureEnum.MESIC_MOIST,
            H100_Spruce=40.0,
            region=RegionSE.NORRA,
        )

    assert site.region == "North"
