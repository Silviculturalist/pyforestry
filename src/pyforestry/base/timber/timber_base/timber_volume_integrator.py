"""Timber Volume Integrator utilities and interfaces."""

import numpy as np
from scipy.integrate import quad


class TimberVolumeIntegrator:
    """Numerically integrate a taper curve into a stem volume.

    Given any :class:`~pyforestry.base.taper.Taper` that can report a diameter at
    a height, this treats the stem as a stack of discs and integrates
    ``pi * (d/2)**2`` over a height interval with :func:`scipy.integrate.quad`.
    It carries no science of its own: the shape comes entirely from the taper
    function passed in, which is where the published coefficients live.

    Use it for a section volume between two heights, or for the whole stem
    between the stump and the tip.
    """

    @staticmethod
    def cylinder_volume_integrand(height, taper_instance):
        """
        Calculate the cross-sectional area. Now takes a taper instance.
        """
        # timber object is no longer needed here
        diameter = taper_instance.get_diameter_at_height(height_m=height)
        if diameter is None:
            return 0.0
        radius = diameter / 200  # cm to m
        return np.pi * (radius**2)

    @staticmethod
    def integrate_volume(height1, height2, taper_instance):
        """
        Integrate the volume of the cylinder between two heights.
        """
        if height2 <= height1:
            return 0.0

        # The 'args' tuple now only contains the taper_instance
        volume, _ = quad(
            TimberVolumeIntegrator.cylinder_volume_integrand,
            height1,
            height2,
            # ``quad`` expects a tuple of extra arguments.  Passing the taper
            # instance without a trailing comma would attempt to iterate over
            # it, raising ``TypeError`` since ``Taper`` does not implement
            # iteration.
            args=(taper_instance,),
            epsabs=1e-3,
            limit=50,
        )
        return volume
