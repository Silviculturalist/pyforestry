"""Sweden's packages resolve their contents lazily, and say so when they cannot.

``pyforestry.sweden`` and ``pyforestry.sweden.growth`` both use :pep:`562`
``__getattr__`` so that importing one model does not pull in the rest. That makes
attribute access a code path rather than a lookup, and it had no test: neither the
resolution, nor the caching, nor the ``AttributeError`` a typo must still raise.
"""

from __future__ import annotations

import importlib
import sys

import pytest

import pyforestry.sweden as sweden
import pyforestry.sweden.growth as growth


def test_every_advertised_subpackage_resolves() -> None:
    """``__all__`` is a promise about what attribute access will find.

    Each name is dropped from the package's globals first, so the loader really
    runs. Without that, any subpackage another test has already touched is a
    plain cached attribute and ``__getattr__`` is never reached -- which is how
    this module came to have no coverage of its one function despite being
    imported by the whole suite.
    """
    for name in sweden.__all__:
        vars(sweden).pop(name, None)
        module = getattr(sweden, name)
        assert module.__name__ == f"pyforestry.sweden.{name}"


def test_a_resolved_subpackage_is_cached_on_the_package() -> None:
    """Resolved once, then a plain attribute -- the point of the lazy import."""
    vars(sweden).pop("volume", None)

    first = sweden.volume
    assert vars(sweden)["volume"] is first
    assert sweden.volume is first


def test_dir_lists_the_subpackages_for_tab_completion() -> None:
    assert dir(sweden) == sorted(sweden.__all__)
    assert dir(growth) == sorted(growth.__all__)


def test_an_unknown_name_still_raises_attribute_error() -> None:
    """Lazy resolution must not turn a typo into an ImportError, or a None."""
    for package, missing in ((sweden, "volumee"), (growth, "ELFVING_2011")):
        with pytest.raises(AttributeError, match=f"has no attribute '{missing}'"):
            getattr(package, missing)


def test_the_growth_descriptors_resolve_to_their_models() -> None:
    """Each name reaches the descriptor its own subpackage publishes."""
    assert growth.ELFVING_2010.component_id.startswith("elfving_2010")
    assert growth.SODERBERG_1986.component_id.startswith("soderberg_1986")


def test_reaching_one_growth_model_does_not_import_the_other() -> None:
    """The reason these are lazy at all."""
    for name in [n for n in sys.modules if "sweden.growth" in n]:
        del sys.modules[name]
    reloaded = importlib.import_module("pyforestry.sweden.growth")

    assert reloaded.ELFVING_2010 is not None
    assert "pyforestry.sweden.growth.soderberg_1986" not in sys.modules
