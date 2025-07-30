from pyforestry.sweden.timber.swe_timber import SweTimber
from pyforestry.sweden.volume.naslund_1947 import NaslundFormFactor, NaslundVolume


def make_tree(species, region="southern", **kwargs):
    params = dict(
        diameter_cm=25, height_m=20, over_bark=True, crown_base_height_m=10, double_bark_mm=5
    )
    return SweTimber(species=species, region=region, **params, **kwargs)


def test_calculate_all_species():
    species_region = [
        ("pinus sylvestris", "southern"),
        ("picea abies", "southern"),
        ("betula", "southern"),
        ("pinus sylvestris", "northern"),
        ("picea abies", "northern"),
        ("betula", "northern"),
    ]
    for sp, reg in species_region:
        vol = NaslundVolume.calculate(make_tree(sp, region=reg))
        assert vol > 0


def test_form_factor_all_species():
    species_region = [
        ("pinus sylvestris", "southern"),
        ("picea abies", "southern"),
        ("betula", "southern"),
        ("pinus sylvestris", "northern"),
        ("picea abies", "northern"),
        ("betula", "northern"),
    ]
    for sp, reg in species_region:
        ff = NaslundFormFactor.calculate(
            sp, 20, 25, region=reg, over_bark=True, crown_base_height_m=10, double_bark_mm=5
        )
        assert isinstance(ff, float)
