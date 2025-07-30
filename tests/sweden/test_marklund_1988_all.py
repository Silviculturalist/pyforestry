import inspect

import pytest

from pyforestry.sweden.biomass import marklund_1988 as m


def test_all_marklund_functions():
    default = {
        "diameter_cm": 20,
        "height_m": 15,
        "double_bark_mm": 3,
        "age": 40,
        "crown_base_height_m": 7,
        "relative_bark_thickness": 2,
        "form_quotient5": 1.2,
        "form_quotient3": 1.1,
        "altitude_m": 100,
    }
    for comp in m.species_map.values():
        for func_list in comp.values():
            for func in func_list:
                params = inspect.signature(func).parameters
                kwargs = {k: v for k, v in default.items() if k in params}
                res = func(**kwargs)
                assert isinstance(res, float)
                assert res > 0


def test_form_quotient_precedence(capsys):
    m.Marklund_1988_T4(20, 15, 3, 40, form_quotient5=1.2, form_quotient3=1.1)
    m.Marklund_1988_T8(20, 15, 3, 40, form_quotient5=1.2, form_quotient3=1.1)
    out = capsys.readouterr().out
    assert "form_quotient5 taking precedence." in out


def test_marklund_requires_species():
    with pytest.raises(ValueError, match="Species must be specified"):
        m.Marklund_1988()


def test_marklund_no_matching_function():
    with pytest.raises(ValueError, match="No function matched"):
        m.Marklund_1988(species="picea abies", component="stem", height_m=10)
