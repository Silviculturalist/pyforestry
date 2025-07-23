from pyforestry.base.timber import Timber, TimberVolumeIntegrator
from pyforestry.base.timber.timber_base import Timber as BaseTimber
from pyforestry.base.timber.timber_base import TimberVolumeIntegrator as BaseIntegrator


def test_reexports():
    assert Timber is BaseTimber
    assert TimberVolumeIntegrator is BaseIntegrator
