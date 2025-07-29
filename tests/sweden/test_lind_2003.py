import pytest

from pyforestry.sweden.misc.elfving_2003 import Lind2003MeanDiameterCodominantTrees


def test_estimate_dominant_mean_diameter():
    md = Lind2003MeanDiameterCodominantTrees.estimate(
        total_stand_age=80,
        stand_density_gf=25,
        site_index=26,
    )
    assert md == pytest.approx(24.6585, rel=1e-4)


@pytest.mark.parametrize(
    "age,gf,si",
    [
        (0, 25, 26),
        (80, 0, 26),
        (80, 25, 0),
        (-5, 25, 26),
    ],
)
def test_estimate_invalid_inputs(age, gf, si):
    with pytest.raises(ValueError):
        Lind2003MeanDiameterCodominantTrees.estimate(
            total_stand_age=age,
            stand_density_gf=gf,
            site_index=si,
        )
