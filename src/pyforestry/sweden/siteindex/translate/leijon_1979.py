"""Site index translations between pine and spruce from Leijon (1979)."""

import warnings

from numpy import exp, log

from pyforestry.base.contracts import FormulaDescriptor, SourceReference


def leijon_pine_to_spruce(H100_Pine):
    """
    Leijon 1979 function 7.2.
    """
    if H100_Pine < 8 or H100_Pine > 30:
        warnings.warn(
            "SI Pine may be outside underlying material",
            stacklevel=2,
        )

    return (
        exp(
            -0.9596 * log(H100_Pine * 10)
            + +0.01171 * (H100_Pine * 10)
            + +7.9209  # approximately corrected for logarithmic bias.
        )
        / 10
    )


def leijon_spruce_to_pine(H100_Spruce):
    """
    Leijon 1979 function 7.1.
    """
    if H100_Spruce < 8 or H100_Spruce > 33:
        warnings.warn(
            "SI Spruce may be outside underlying material.",
            stacklevel=2,
        )

    return (
        exp(
            1.6967 * log(H100_Spruce * 10)
            + -0.005179 * (H100_Spruce * 10)
            + -2.5397  # approximately corrected for logarithmic bias.
        )
        / 10
    )


DESCRIPTOR = FormulaDescriptor(
    component_id="leijon_1979_siteindex",
    source=SourceReference(
        author="Leijon, B.",
        year=1979,
        title="Site index translations between Scots pine and Norway spruce",
    ),
    species_groups={
        "pine": frozenset({"Pinus sylvestris"}),
        "spruce": frozenset({"Picea abies"}),
    },
    units={},
    kernel_names=("leijon_pine_to_spruce", "leijon_spruce_to_pine"),
)
