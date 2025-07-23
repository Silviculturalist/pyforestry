from dataclasses import FrozenInstanceError, dataclass, field

import pytest

from pyforestry.base.helpers.primitives import SiteBase


@dataclass(frozen=True)
class DummySite(SiteBase):
    """Concrete implementation used for testing `SiteBase`."""

    sum_lat_long: float = field(init=False)

    def compute_attributes(self) -> None:
        object.__setattr__(self, "sum_lat_long", self.latitude + self.longitude)


def test_post_init_computes_attributes() -> None:
    site = DummySite(latitude=1.0, longitude=2.0)
    assert site.sum_lat_long == 3.0


def test_frozen_behavior() -> None:
    site = DummySite(latitude=1.0, longitude=2.0)
    with pytest.raises(FrozenInstanceError):
        site.latitude = 5.0
