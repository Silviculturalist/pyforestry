import pyforestry.sweden.blocks as sweden_blocks


def test_sweden_blocks_package_excludes_formula_kernel_exports() -> None:
    """Equation-level kernel functions must not leak into blocks/ __all__."""
    banned = {
        "pine_ln_d2_growth",
        "spruce_ln_d2_growth",
        "soderberg_1986_tree_diameter_growth_cm",
        "soderberg_1992_height_tree_age_m",
        "sapling_height_growth_m",
        "ingrowth_predict",
    }
    assert banned.isdisjoint(set(sweden_blocks.__all__))
