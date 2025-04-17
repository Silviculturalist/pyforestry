import pytest
import math
from Munin.SiteIndex.norway.Kuehne_2022 import Kuehne2022 as KuehneSiteIndex
from Munin.Models.norway.Kuehne_2022 import KuehnePineModel as KuehneStandModels
from Munin.Helpers.Base import Age, AgeMeasurement, SiteIndexValue, StandBasalArea, Stems, StandVolume

# --- Site Index Tests ---

def test_kuehne_height_trajectory_output_height():
    """ Test Kuehne height trajectory outputting height (default). """
    # Example: H=20m @ Age.TOTAL(50) -> Predict H @ Age.TOTAL(100)
    result = KuehneSiteIndex.height_trajectory.pinus_sylvestris(
        age=Age.TOTAL(50),
        age2=Age.TOTAL(100),
        dominant_height=20.0
    )
    assert isinstance(result, SiteIndexValue)
    assert not math.isnan(float(result))
    # Calculate expected value manually or from reliable source
    # For H=20 @ 50 -> H @ 100:
    # b1=68.4, b2=-24.0, b3=1.47
    # X = (20 - 68.4) / (1 - (-24.0)*20*(50^-1.47)) = -48.4 / (1 + 480 * (1/341.8)) = -48.4 / (1 + 1.404) = -48.4 / 2.404 = -20.133
    # H100 = (68.4 - 20.133) / (1 + (-24.0)*(-20.133)*(100^-1.47)) = 48.267 / (1 + 483.19 * (1/825.4)) = 48.267 / (1 + 0.585) = 48.267 / 1.585 = 30.45
    expected_h100 = 30.45
    assert float(result) == pytest.approx(expected_h100, abs=0.01)
    assert result.reference_age == Age.TOTAL(100)
    assert result.fn is KuehneSiteIndex.height_trajectory.pinus_sylvestris # Check fn points to the callable wrapper

def test_kuehne_height_trajectory_output_sih100():
    """ Test Kuehne height trajectory outputting SIH100. """
    result = KuehneSiteIndex.height_trajectory.pinus_sylvestris(
        age=Age.TOTAL(50),
        age2=Age.TOTAL(100), # age2 value doesn't matter for SIH100 output itself
        dominant_height=20.0,
        output="SIH100"
    )
    assert isinstance(result, float)
    assert not math.isnan(result)
    expected_sih100 = 30.45 # Same calculation as above
    assert result == pytest.approx(expected_sih100, abs=0.01)

def test_kuehne_height_trajectory_output_both():
    """ Test Kuehne height trajectory outputting Both height and SIH100. """
    result_h, result_si = KuehneSiteIndex.height_trajectory.pinus_sylvestris(
        age=Age.TOTAL(50),
        age2=Age.TOTAL(100),
        dominant_height=20.0,
        output="Both"
    )
    assert isinstance(result_h, SiteIndexValue)
    assert isinstance(result_si, float)
    assert not math.isnan(float(result_h))
    assert not math.isnan(result_si)
    expected_h100 = 30.45
    assert float(result_h) == pytest.approx(expected_h100, abs=0.01)
    assert result_si == pytest.approx(expected_h100, abs=0.01)
    assert result_h.fn is KuehneSiteIndex.height_trajectory.pinus_sylvestris # Check fn


def test_kuehne_height_trajectory_requires_total_age():
    """ Test TypeError if non-TOTAL age used. """
    with pytest.raises(TypeError, match="must be specified as Age.TOTAL"):
        KuehneSiteIndex.height_trajectory.pinus_sylvestris(
            age=Age.DBH(40), # Incorrect
            age2=Age.TOTAL(100),
            dominant_height=20.0
        )
    with pytest.raises(TypeError, match="must be specified as Age.TOTAL"):
        KuehneSiteIndex.height_trajectory.pinus_sylvestris(
            age=Age.TOTAL(50),
            age2=Age.DBH(90), # Incorrect
            dominant_height=20.0
        )

# --- Stand Model Tests (Add more as needed) ---

# Need example values consistent with the model to test properly.
# These are placeholder tests demonstrating the structure.

def test_kuehne_volume_prediction():
    """ Placeholder test for volume prediction. """
    # Example values - replace with realistic ones if available
    result = KuehneStandModels.volume.pinus_sylvestris(
        basal_area=25.0,
        dominant_height=22.0,
        age=Age.TOTAL(60)
        # Add thinning params if testing that aspect
    )
    assert isinstance(result, StandVolume)
    assert not math.isnan(float(result))
    # Add approx check if expected value is known
    assert result.fn is KuehneStandModels.volume.pinus_sylvestris

def test_kuehne_stems_quotient():
    """ Test stems quotient calculation. """
    result = KuehneStandModels.stems_quotient.pinus_sylvestris(
        ba_before=30.0,
        ba_after=20.0 # BA reduced by 1/3
    )
    assert isinstance(result, float)
    assert not math.isnan(result)
    # Calculate expected: exp(-1.91239 + 1.94414 * (20/30)) = exp(-1.91239 + 1.29609) = exp(-0.6163) = 0.5399
    assert result == pytest.approx(0.5399, abs=1e-4)

def test_kuehne_ba_quotient():
    """ Test BA quotient calculation. """
    result = KuehneStandModels.ba_quotient.pinus_sylvestris(
        stems_before=1000.0,
        stems_after=700.0 # Stems reduced to 70%
    )
    assert isinstance(result, float)
    assert not math.isnan(result)
    # Calculate expected: (ln(700/1000) + 1.91239) / 1.94414 = (ln(0.7) + 1.91239) / 1.94414 = (-0.35667 + 1.91239) / 1.94414 = 1.55572 / 1.94414 = 0.8002
    assert result == pytest.approx(0.8002, abs=1e-4)