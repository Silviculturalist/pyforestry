"""Register the Norway regional species namespace."""

from pyforestry.base.helpers.tree_species import (
    BETULA_PENDULA,
    BETULA_PUBESCENS,
    PICEA_ABIES,
    PINUS_SYLVESTRIS,
    POPULUS_TREMULA,
    RegionalTreeSpecies,
    TreeSpecies,
)

TreeSpecies.Norway = RegionalTreeSpecies(
    "Norway",
    allowed_species=[
        PICEA_ABIES,
        PINUS_SYLVESTRIS,
        BETULA_PENDULA,
        BETULA_PUBESCENS,
        POPULUS_TREMULA,
    ],
)
