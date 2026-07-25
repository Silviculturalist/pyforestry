"""Norway bark-thickness equations."""

from .braastad_1966_birch_norway_bark_thickness import (
    braastad_1966_birch_norway_bark_thickness,
)
from .brantseg_1967_scots_pine_norway_bark_thickness import (
    brantseg_1967_scots_pine_norway_bark_thickness,
)
from .hansen_2023 import (
    hansen_2023_birch_norway_bark_thickness,
    hansen_2023_norway_spruce_norway_bark_thickness,
    hansen_2023_scots_pine_norway_bark_thickness,
)
from .vestjordet_1967_norway_spruce_norway_bark_thickness import (
    vestjordet_1967_norway_spruce_norway_bark_thickness,
)

__all__ = [
    "braastad_1966_birch_norway_bark_thickness",
    "brantseg_1967_scots_pine_norway_bark_thickness",
    "hansen_2023_norway_spruce_norway_bark_thickness",
    "hansen_2023_scots_pine_norway_bark_thickness",
    "hansen_2023_birch_norway_bark_thickness",
    "vestjordet_1967_norway_spruce_norway_bark_thickness",
]
