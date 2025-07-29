"""Lazy-loading interface for Swedish volume models."""

# pyforestry/volume/__init__.py

import importlib
import typing
from typing import TYPE_CHECKING

__all__ = [
    "andersson_1954_volume_small_trees_birch_height_above_4_m",
    "andersson_1954_volume_small_trees_pine",
    "andersson_1954_volume_small_trees_spruce",
    "andersson_1954_volume_small_trees_birch_under_diameter_5_cm",
    "BrandelVolume",
    "carbonnier_1954_volume_larch",
    "johnsson_1953_volume_hybrid_aspen",
    "matern_1975_volume_sweden_beech",
    "matern_1975_volume_sweden_oak",
    "NaslundVolume",
    "NaslundFormFactor",
    "Eriksson_1973_volume_aspen_Sweden",
    "Eriksson_1973_volume_lodgepole_pine_Sweden",
]

if TYPE_CHECKING:  # pragma: no cover - imported only for type checking
    # imports only exist for the type checker—they are stripped at runtime
    from .andersson_1954 import (  # pragma: no cover - typing only
        andersson_1954_volume_small_trees_birch_height_above_4_m,  # pragma: no cover
        andersson_1954_volume_small_trees_birch_under_diameter_5_cm,  # pragma: no cover
        andersson_1954_volume_small_trees_pine,  # pragma: no cover
        andersson_1954_volume_small_trees_spruce,  # pragma: no cover
    )
    from .brandel_1990 import BrandelVolume  # pragma: no cover
    from .carbonnier_1954 import carbonnier_1954_volume_larch  # pragma: no cover
    from .eriksson_1973 import (  # pragma: no cover
        Eriksson_1973_volume_aspen_Sweden,  # pragma: no cover
        Eriksson_1973_volume_lodgepole_pine_Sweden,  # pragma: no cover
    )
    from .johnsson_1953 import johnsson_1953_volume_hybrid_aspen  # pragma: no cover
    from .matern_1975 import (  # pragma: no cover
        matern_1975_volume_sweden_beech,  # pragma: no cover
        matern_1975_volume_sweden_oak,  # pragma: no cover
    )
    from .naslund_1947 import NaslundFormFactor, NaslundVolume  # pragma: no cover

# Map of public name → submodule
_name_to_module: typing.Dict[str, str] = {
    "andersson_1954_volume_small_trees_birch_height_above_4_m": "andersson_1954",
    "andersson_1954_volume_small_trees_pine": "andersson_1954",
    "andersson_1954_volume_small_trees_spruce": "andersson_1954",
    "andersson_1954_volume_small_trees_birch_under_diameter_5_cm": "andersson_1954",
    "BrandelVolume": "brandel_1990",
    "carbonnier_1954_volume_larch": "carbonnier_1954",
    "johnsson_1953_volume_hybrid_aspen": "johnsson_1953",
    "matern_1975_volume_sweden_beech": "matern_1975",
    "matern_1975_volume_sweden_oak": "matern_1975",
    "NaslundVolume": "naslund_1947",
    "NaslundFormFactor": "naslund_1947",
    "Eriksson_1973_volume_aspen_Sweden": "eriksson_1973",
    "Eriksson_1973_volume_lodgepole_pine_Sweden": "eriksson_1973",
}


def __getattr__(name: str):
    """Load a volume model on demand."""
    if name in _name_to_module:
        module = importlib.import_module(f"{__name__}.{_name_to_module[name]}")
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    """Return available public names for ``dir()``."""
    return sorted(__all__)
