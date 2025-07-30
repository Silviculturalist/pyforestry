import importlib

import pytest

from pyforestry.sweden.siteindex import (
    elfving_kiviste_1997_height_trajectory_sweden_pine,
    eriksson_1997_height_trajectory_sweden_birch,
    hagglund_remrod_1977_height_trajectories_lodgepole_pine,
    johansson_1996_height_trajectory_sweden_aspen,
    johansson_1999_height_trajectory_sweden_alnus_glutinosa,
    johansson_1999_height_trajectory_sweden_alnus_incana,
    johansson_2011_height_trajectory_sweden_poplar,
    johansson_2013_height_trajectory_sweden_beech,
    johansson_2013_height_trajectory_sweden_hybrid_aspen,
    johansson_2013_height_trajectory_sweden_larch,
    johansson_2013_height_trajectory_sweden_oak,
)
from pyforestry.sweden.siteindex.translate import (
    Leijon_Pine_to_Spruce,
    Leijon_Spruce_to_Pine,
    agestam_1985_si_translation_pine_to_birch,
    agestam_1985_si_translation_spruce_to_birch,
    hagglund_1981_SI_to_productivity,
)


def test_siteindex_init_reexports():
    mod = importlib.import_module("pyforestry.sweden.siteindex")
    expected = {
        "elfving_kiviste_1997_height_trajectory_sweden_pine": (
            elfving_kiviste_1997_height_trajectory_sweden_pine
        ),
        "eriksson_1997_height_trajectory_sweden_birch": (
            eriksson_1997_height_trajectory_sweden_birch
        ),
        "hagglund_remrod_1977_height_trajectories_lodgepole_pine": (
            hagglund_remrod_1977_height_trajectories_lodgepole_pine
        ),
        "johansson_1996_height_trajectory_sweden_aspen": (
            johansson_1996_height_trajectory_sweden_aspen
        ),
        "johansson_1999_height_trajectory_sweden_alnus_glutinosa": (
            johansson_1999_height_trajectory_sweden_alnus_glutinosa
        ),
        "johansson_1999_height_trajectory_sweden_alnus_incana": (
            johansson_1999_height_trajectory_sweden_alnus_incana
        ),
        "johansson_2011_height_trajectory_sweden_poplar": (
            johansson_2011_height_trajectory_sweden_poplar
        ),
        "johansson_2013_height_trajectory_sweden_beech": (
            johansson_2013_height_trajectory_sweden_beech
        ),
        "johansson_2013_height_trajectory_sweden_hybrid_aspen": (
            johansson_2013_height_trajectory_sweden_hybrid_aspen
        ),
        "johansson_2013_height_trajectory_sweden_larch": (
            johansson_2013_height_trajectory_sweden_larch
        ),
        "johansson_2013_height_trajectory_sweden_oak": (
            johansson_2013_height_trajectory_sweden_oak
        ),
    }
    for name, fn in expected.items():
        assert name in mod.__all__
        assert getattr(mod, name) is fn


def test_translate_init_reexports():
    mod = importlib.import_module("pyforestry.sweden.siteindex.translate")
    expected = {
        "agestam_1985_si_translation_pine_to_birch": (agestam_1985_si_translation_pine_to_birch),
        "agestam_1985_si_translation_spruce_to_birch": (
            agestam_1985_si_translation_spruce_to_birch
        ),
        "hagglund_1981_SI_to_productivity": hagglund_1981_SI_to_productivity,
        "Leijon_Pine_to_Spruce": Leijon_Pine_to_Spruce,
        "Leijon_Spruce_to_Pine": Leijon_Spruce_to_Pine,
    }
    for name, fn in expected.items():
        assert name in mod.__all__
        assert getattr(mod, name) is fn


def test_site_attribute_error():
    mod = importlib.import_module("pyforestry.sweden.site")
    with pytest.raises(AttributeError):
        _ = mod.NonExistent
