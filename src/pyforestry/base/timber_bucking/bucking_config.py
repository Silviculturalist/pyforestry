"""Configuration options for the Nä sberg bucker."""

from dataclasses import dataclass

from pyforestry.base.helpers.bucking import BuckingConfigBase


@dataclass(frozen=True)
class BuckingConfig(BuckingConfigBase):
    """Optional settings affecting the bucking algorithm."""

    pass
