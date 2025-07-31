import importlib

from pyforestry.sweden.bark import (
    Hannrup_2004_bark_picea_abies_sweden,
    Hannrup_2004_bark_pinus_sylvestris_sweden,
)


def test_bark_init_exports_match():
    mod = importlib.import_module("pyforestry.sweden.bark")
    assert "Hannrup_2004_bark_picea_abies_sweden" in mod.__all__
    assert "Hannrup_2004_bark_pinus_sylvestris_sweden" in mod.__all__


def test_bark_functions_via_init_produce_same_result():
    pine_val_init = Hannrup_2004_bark_pinus_sylvestris_sweden(300, 60, 100)
    spruce_val_init = Hannrup_2004_bark_picea_abies_sweden(300, 350)

    from pyforestry.sweden.bark.hannrup_2004 import (
        Hannrup_2004_bark_picea_abies_sweden as spruce_direct,
    )
    from pyforestry.sweden.bark.hannrup_2004 import (
        Hannrup_2004_bark_pinus_sylvestris_sweden as pine_direct,
    )

    assert pine_val_init == pine_direct(300, 60, 100)
    assert spruce_val_init == spruce_direct(300, 350)
    assert pine_val_init > 0
    assert spruce_val_init > 0
