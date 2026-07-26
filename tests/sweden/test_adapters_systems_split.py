"""The ``adapters``/``systems`` boundary, asserted from inside the package.

``scripts/check_architecture_lint.py`` (AL001) enforces the coefficient rule over
the source text. These tests assert the consequences a caller can observe: that
the two packages export different things, and that neither re-exports the
equation kernels the domain packages own.
"""

import pyforestry.sweden.adapters as adapters
import pyforestry.sweden.systems as systems

# Kernel functions belong to the domain packages (sweden/growth, sweden/height,
# sweden/ingrowth). A model package re-exporting them would give the same
# function two import paths, one of which hides where it was published.
KERNEL_NAMES = {
    "pine_ln_d2_growth",
    "spruce_ln_d2_growth",
    "soderberg_1986_tree_diameter_growth_cm",
    "soderberg_1992_height_tree_age_m",
    "sapling_height_growth_m",
    "ingrowth_predict",
}


def test_adapters_do_not_re_export_equation_kernels() -> None:
    assert KERNEL_NAMES.isdisjoint(set(adapters.__all__))


def test_systems_do_not_re_export_equation_kernels() -> None:
    assert KERNEL_NAMES.isdisjoint(set(systems.__all__))


def test_adapters_and_systems_export_disjoint_names() -> None:
    """A name resolves to one package, so the import path says which tier it is.

    ``sweden/blocks`` held both tiers behind one ``__all__``, so nothing in the
    name told you whether you had imported science or glue.
    """
    assert set(adapters.__all__).isdisjoint(set(systems.__all__))


def test_every_exported_name_resolves() -> None:
    for name in adapters.__all__:
        assert hasattr(adapters, name), f"pyforestry.sweden.adapters.{name} is missing"
    for name in systems.__all__:
        assert hasattr(systems, name), f"pyforestry.sweden.systems.{name} is missing"
